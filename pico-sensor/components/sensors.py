from components.web_real_time_clock import WebRealTimeClock
from typing import Tuple, Any, Optional
from os import remove, rename
from machine import Timer, Pin, ADC, I2C
from json import load, dump
from uos import urandom
from ubinascii import hexlify
from time import sleep

HISTORY_LENGTH = 60
SAMPLING_FREQUENCY_SECONDS = 60
CONFIG_FILE = "config.json"

def save_config(updated_config: dict[str, Any]) -> None:  # TODO: relocate
    with open(CONFIG_FILE, "w") as f:
        dump(updated_config, f)

def generate_uuid() -> str:
    random_bytes = urandom(16)
    uuid = hexlify(random_bytes).decode()
    return f"{uuid[:8]}-{uuid[8:12]}-{uuid[12:16]}-{uuid[16:20]}-{uuid[20:]}"

class Sensor:
    def __init__(self) -> None:
        pass

    def data_interface(self) -> float:
        return 0.0
    
    def limits(self) -> Tuple[int, int]:
        return 0, 100

class MoistureSensor(Sensor):
    def __init__(
        self,
        power_pin: int,
        adc_pin: int,
        voltage_0_percent: float,
        voltage_100_percent: float,
        name: str,
        uuid: str,
    ):
        self.adc_power_pin = Pin(power_pin, Pin.OUT)
        print(f"adc_pin: {adc_pin}, adc_power_pin: {power_pin}")
        self.adc = ADC(Pin(adc_pin))
        self.voltage_0_percent = voltage_0_percent
        self.voltage_100_percent = voltage_100_percent
        self.name = name
        self.uuid = uuid

    def data_interface(self) -> float:
        return float(self.percentage())

    def voltage(self) -> float:
        self.adc_power_pin.value(1)
        sleep(0.01)
        adc_value = self.adc.read_u16()
        self.adc_power_pin.value(0)
        voltage = float(adc_value * 3.3 / 65535)
        return voltage

    def percentage(self) -> float:
        voltage = self.voltage()
        percentage = round(
            (
                1
                - (
                    (voltage - self.voltage_0_percent)
                    / (self.voltage_100_percent - self.voltage_0_percent)
                )
            )
            * 100
        )
        return percentage
    
    def limits(self) -> Tuple[int, int]:
        return 0, 100


class AHT10:
    def __init__(self, i2c_address, i2c_bus, i2c_sda_pin, i2c_scl_pin, power_pin):
        self.i2c_address = i2c_address
        self.power_pin = Pin(power_pin, Pin.OUT)
        self.power_pin.value(1)  # power on AHT10
        sleep(0.1)  # waith for AHT10 power up
        self.i2c = I2C(i2c_bus, scl=Pin(i2c_scl_pin), sda=Pin(i2c_sda_pin), freq=100000)
        self.init_sensor()

    def init_sensor(self):
        for i in range(10):
            try:
                print(f"self.i2c_address: {self.i2c_address}")
                self.i2c.writeto(int(self.i2c_address), b"\xE1\x08\x00")
                sleep(0.1)
                break
            except OSError as e:
                if i < 9:
                    continue
                raise e

    def read_data(self):
        for i in range(10):
            try:
                self.i2c.writeto(int(self.i2c_address), b"\xAC\x33\x00")
                sleep(0.1)
                data = self.i2c.readfrom(int(self.i2c_address), 6)
                sleep(0.1)
                return data
            except OSError as e:
                if i < 9:
                    continue
                raise e

    def get_temperature_and_humidity(self):
        data = self.read_data()
        humidity = ((data[1] << 16) | (data[2] << 8) | data[3]) >> 4
        temperature = ((data[3] & 0x0F) << 16) | (data[4] << 8) | data[5]

        humidity = (humidity * 100) / 1048576
        temperature = ((temperature * 200) / 1048576) - 53

        return temperature, humidity

    def get_temperature(self):
        data = self.read_data()
        temperature = ((data[3] & 0x0F) << 16) | (data[4] << 8) | data[5]
        temperature = ((temperature * 200) / 1048576) - 53
        return temperature

    def get_humidity(self):
        data = self.read_data()
        humidity = ((data[1] << 16) | (data[2] << 8) | data[3]) >> 4
        humidity = (humidity * 100) / 1048576
        return humidity


class AHT10TemperatureSensor(Sensor):
    def __init__(self, aht10: AHT10) -> None:
        self.aht10 = aht10

    def data_interface(self) -> float:
        return self.read_temperature()

    def read_temperature(self) -> float:
        return self.aht10.get_temperature()
    
    def limits(self) -> Tuple[int, int]:
        return 0, 100


class AHT10HumiditySensor(Sensor):
    def __init__(self, aht10: AHT10):
        self.aht10 = aht10

    def data_interface(self) -> float:
        return self.read_humidity()

    def read_humidity(self) -> float:
        return self.aht10.get_humidity()
    
    def limits(self) -> Tuple[int, int]:
        return 0, 100


class PicoTemperatureSensor(Sensor):
    conversion_factor = 3.3 / (65535)
    temperature_sensor = ADC(4)

    def data_interface(self) -> float:
        return self.read_temperature()

    def read_temperature(self) -> float:
        raw_value = self.temperature_sensor.read_u16()
        voltage = raw_value * self.conversion_factor
        temperature_c = float(27 - (voltage - 0.706) / 0.001721)
        return temperature_c

    def limits(self) -> Tuple[int, int]:
        return 0, 100


class PersistentList:
    def __init__(self, filename: str, max_lines: int, tail_lines: int = 10) -> None:
        self.filename: str = filename
        self.data: list[Tuple[float, int]] = []
        self.max_lines: int = max_lines
        self.tail_lines: int = tail_lines
        self._load_from_file()

    def get_content(self) -> list[Tuple[float, int]]:
        return self.data

    def _load_from_file(self) -> None:
        try:
            self._read_last_n_lines()
        except:
            self.data = []

    def _read_last_n_lines(
        self,
    ) -> None:  # TODO: read in reverse order to speedup startup time
        with open(self.filename, "r") as file:
            for line in file:
                line_splits = line.split(",")
                item = float(line_splits[0])
                event_unix_time: int = int(line_splits[1])
                self.data.append((item, event_unix_time))
                if len(self.data) > self.max_lines:
                    self.data.pop(0)

    def append(self, item: float, event_unix_time: int) -> None:
        self.data.append((item, event_unix_time))
        if len(self.data) > self.max_lines:
            self.data.pop(0)
        with open(self.filename, "a") as file:
            file.write(f"{item},{event_unix_time}\n")
        if self._history_file_length() > self.max_lines + self.tail_lines:
            self._trim_history_file()

    def _trim_history_file(self) -> None:
        temporary_file_name = f"{self.filename}.tmp"
        with open(temporary_file_name, "wb") as temporary_file:
            print("trimming history:", self.filename)
            for item, event_unix_time in self.data:
                temporary_file.write(f"{item},{event_unix_time}\n")  # type: ignore
        remove(self.filename)
        rename(temporary_file_name, self.filename)

    def _history_file_length(self) -> int:
        with open(self.filename, "r") as file:
            return sum(1 for _ in file)


def buffer_list_with_zeros(
    input_list: list[Tuple[float, int]], n: int
) -> list[Tuple[float, int]]:  # TODO: bug here, does not work yet with timed elements
    if len(input_list) < n:
        num_zeros = n - len(input_list)
        zeros_list = [0] * num_zeros
        buffered_list = zeros_list + input_list
        return buffered_list  # type: ignore
    else:
        return input_list


class SensorHistory:
    def __init__(
        self, filename: str, length: int, rtc: WebRealTimeClock, sensor_type: str
    ):
        self.sensor_type = sensor_type
        self.rtc = rtc
        self.persistent_history = PersistentList(
            filename=filename, max_lines=HISTORY_LENGTH
        )
        self.history = self.persistent_history.get_content().copy()
        print(f"Loaded {len(self.history)} values from {filename}")
        self.length = length
        self.history = buffer_list_with_zeros(self.history, HISTORY_LENGTH)

    def add(self, value: float) -> list[Tuple[float, int]]:
        event_unix_time = self.rtc.get_current_unix_time()
        self.history.append((value, event_unix_time))
        self.persistent_history.append(value, event_unix_time)
        # remove the first element if the history is too long
        if len(self.history) > self.length:
            self.history.pop(0)
        return self.history

    def get(self) -> list[Tuple[float, int]]:
        return self.history


class SensorMonitor:
    def __init__(self, sensor: Sensor, history: SensorHistory) -> None:
        self.sensor = sensor
        self.history: SensorHistory = history
        self.timer: Timer = Timer(-1)
        self._record_data()
        self.timer.init(
            period=SAMPLING_FREQUENCY_SECONDS * 1000,
            mode=Timer.PERIODIC,
            callback=self._record_data,
        )

    def _record_data(self, timer: Timer = None) -> None:
        self.history.add(self.sensor.data_interface())

    def get_latest(self) -> Tuple[Any, int]:
        return self.history.get()[-1]

    def get_sensor(self) -> Sensor:
        return self.sensor

    def get_data(self) -> list[Tuple[Any, int]]:
        return self.history.get()


class Sensors:
    sensor_monitors: dict[str, SensorMonitor] = {}

    def get_sensor(
        self, uuid: Optional[str] = None, index: Optional[int] = None
    ) -> SensorMonitor:
        if index is not None:
            print(
                f"sensor_monitors.items() {list(self.sensor_monitors.keys())[int(index)]}"
            )
            return self.sensor_monitors[list(self.sensor_monitors.keys())[int(index)]]
        if uuid:
            return self.sensor_monitors[uuid]
        raise ValueError("uuid or index must be provided")

    def __init__(self, rtc: WebRealTimeClock) -> None:
        self.rtc = rtc
        with open("config.json", "r") as f:
            config = load(f)
        for configured_sensor in config.get("sensors"):
            if not configured_sensor.get("uuid"):
                configured_sensor.update({"uuid": generate_uuid()})
                save_config(config)
            sensor_type = configured_sensor.get("type")
            if sensor_type == "MH-Moisture":
                self.sensor_monitors[configured_sensor.get("uuid")] = SensorMonitor(
                    MoistureSensor(
                        power_pin=configured_sensor.get("power_pin"),
                        adc_pin=configured_sensor.get("adc_pin"),
                        voltage_0_percent=configured_sensor.get("min_voltage"),
                        voltage_100_percent=configured_sensor.get("max_voltage"),
                        name=configured_sensor.get("name"),
                        uuid=configured_sensor.get("uuid"),
                    ),
                    SensorHistory(
                        filename=configured_sensor.get("log_file"),
                        length=HISTORY_LENGTH,
                        rtc=self.rtc,
                        sensor_type=sensor_type,
                    ),
                )
                continue
            elif sensor_type == "AHT10Temperature":
                self.sensor_monitors[configured_sensor.get("uuid")] = SensorMonitor(
                    AHT10TemperatureSensor(
                        AHT10(
                            i2c_address=configured_sensor["i2c_address"],
                            i2c_bus=configured_sensor["i2c_bus"],
                            i2c_sda_pin=configured_sensor["i2c_sda_pin"],
                            i2c_scl_pin=configured_sensor["i2c_scl_pin"],
                            power_pin=configured_sensor["power_pin"],
                        )
                    ),
                    SensorHistory(
                        filename=configured_sensor.get("log_file"),
                        length=HISTORY_LENGTH,
                        rtc=self.rtc,
                        sensor_type=sensor_type,
                    ),
                )
                continue
            elif sensor_type == "AHT10Humidity":
                self.sensor_monitors[configured_sensor.get("uuid")] = SensorMonitor(
                    AHT10HumiditySensor(
                        AHT10(
                            i2c_address=configured_sensor["i2c_address"],
                            i2c_bus=configured_sensor["i2c_bus"],
                            i2c_sda_pin=configured_sensor["i2c_sda_pin"],
                            i2c_scl_pin=configured_sensor["i2c_scl_pin"],
                            power_pin=configured_sensor["power_pin"],
                        )
                    ),
                    SensorHistory(
                        filename=configured_sensor.get("log_file"),
                        length=HISTORY_LENGTH,
                        rtc=self.rtc,
                        sensor_type=sensor_type,
                    ),
                )
                continue
            elif sensor_type == "PicoTemperature":
                self.sensor_monitors[configured_sensor.get("uuid")] = SensorMonitor(
                    PicoTemperatureSensor(),
                    SensorHistory(
                        filename=configured_sensor.get("log_file"),
                        length=HISTORY_LENGTH,
                        rtc=self.rtc,
                        sensor_type=sensor_type,
                    ),
                )
                continue