"""
Copyright 2024 Hex-Software Oy

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import network  # type: ignore
import socket
import ure  # type: ignore
import struct
import time
import utime  # type: ignore
from time import sleep
import os
from os import remove, rename
import ssl
import json
from machine import Pin, ADC, Timer, I2C, freq, reset, PWM  # type: ignore
from gc import collect, mem_alloc, mem_free  # type: ignore
import uos  # type: ignore
import ubinascii  # type: ignore
import sys
from typing import Any, Tuple, Optional, Union
import random

frequency_MHz = 125
freq(frequency_MHz * 1000000)
print("Current frequency: ", freq() / 1000000, "MHz")
HISTORY_LENGTH = 50
SAMPLING_FREQUENCY_SECONDS = 600
hostname = f"pico-plant-monitor"
network.hostname(hostname)
WIFI_CONFIG_FILE = "wifi_config.json"
CONFIG_FILE = "config.json"
led = Pin("LED", Pin.OUT)
led.value(0)


def generate_uuid() -> str:
    random_bytes = uos.urandom(16)
    uuid = ubinascii.hexlify(random_bytes).decode()
    return f"{uuid[:8]}-{uuid[8:12]}-{uuid[12:16]}-{uuid[16:20]}-{uuid[20:]}"


class CloudUpdater:

    branch: str = "production"
    base_url: str = (
        f"https://raw.githubusercontent.com/snuarrow/LaiskaJaakko/{branch}/pico-sensor/"
    )
    current_version: int = 0
    updates_available: bool = False

    def __init__(self) -> None:
        self.check_for_updates()

    def check_for_updates(self) -> bool:
        print("checking for updates..")
        self.version_config = self._load_file("version.json")
        self.current_version = int(self.version_config["version"])
        self._download_file("version.json", "remote-version.json")
        self.remote_version_config = self._load_file("remote-version.json")
        self.remote_version = self.remote_version_config["version"]
        self.updates_available = self.remote_version > self.current_version
        return self.updates_available

    def pretty_current_version(self) -> str:
        return f"v.{self.current_version}"

    def update(self, timer: Timer = None) -> None:
        print("updating..")
        global update_mutex
        update_mutex = True
        sleep(3)
        self.version_config = self._load_file("version.json")
        for file in self.version_config["files_included"]:
            print(f"downloading {file}")
            self._download_file(file, file)
        self._install_update()

    def _download_file(self, remote_file_name: str, local_file_name: str) -> None:
        collect()
        https_file_url = f"{self.base_url}{remote_file_name}"
        print(f"Downloading file.. {https_file_url}")
        _, _, host, path = https_file_url.split("/", 3)
        path = "/" + path

        addr = socket.getaddrinfo(host, 443)[0][-1]
        s = socket.socket()
        s.connect(addr)
        s = ssl.wrap_socket(s, server_hostname=host)  # type: ignore
        request = "GET {} HTTP/1.1\r\nHost: {}\r\nConnection: close\r\n\r\n".format(
            path, host
        )
        s.write(request.encode("utf-8"))  # type: ignore
        response = b""
        while b"\r\n\r\n" not in response:
            response += s.read(1)  # type: ignore
        _, body = response.split(b"\r\n\r\n", 1)
        with open(local_file_name, "wb") as file:
            file.write(body)
            while True:
                data = s.read(1024)  # type: ignore
                if not data:
                    break
                file.write(data)
        s.close()

    def _install_update(self) -> None:
        print("installing update..")
        sleep(1)
        status_led.signal_cloud_update()
        reset()

    def _load_file(self, filename: str) -> Any:
        with open(filename, "r") as f:
            version_config = json.load(f)
            return version_config


class StatusLed:
    lit: bool = False

    def __init__(self, brightness: float = 0.01) -> None:
        self.brightness = brightness
        with open("config.json", "r") as f:
            led_config = json.load(f)["rgb_led"]
        self.blue_pin_number = led_config["blue_pin"]
        self.red_pin_number = led_config["red_pin"]
        self.green_pin_number = led_config["green_pin"]
        self.timer = Timer(-1)
        self.disco_start()
        self.disco_stop()
        self.disco_start()

    def _random_colour(self, timer: Timer = None) -> None:
        random_red = random.randint(0, int(65536 * self.brightness))
        random_green = random.randint(0, int(65536 * self.brightness))
        random_blue = random.randint(0, int(65536 * self.brightness))
        self.red.duty_u16(random_red)
        self.green.duty_u16(random_green)
        self.blue.duty_u16(random_blue)

    def signal_cloud_update(self) -> None:
        self.disco_stop()
        self.red_pin = Pin(self.red_pin_number)
        self.green_pin = Pin(self.green_pin)
        self.blue_pin = Pin(self.blue_pin)
        self.blue_pin.value(1)
        sleep(1)
        self.green_pin.value(1)
        sleep(1)
        self.red_pin.value(1)
        sleep(2)
        self.red_pin.value(0)
        self.green_pin.value(0)
        self.blue_pin.value(0)
        sleep(0.5)
        for i in range(3):
            self.red_pin.value(1)
            self.green_pin.value(1)
            self.blue_pin.value(1)
            sleep(0.1)
            self.red_pin.value(0)
            self.green_pin.value(0)
            self.blue_pin.value(0)

    def signal_wifi_reset(self) -> None:
        self.disco_stop()
        self.red_pin = Pin(self.red_pin_number)
        for _ in range(10):
            self.red_pin.value(1)
            sleep(0.05)
            self.red_pin.value(0)
            sleep(0.2)

    def signal_wifi_set(self) -> None:
        self.disco_stop()
        self.green_pin = Pin(self.green_pin_number)
        for _ in range(10):
            self.green_pin.value(1)
            sleep(0.05)
            self.green_pin.value(0)
            sleep(0.2)

    def _ap_mode_cycle(self, timer: Timer = None) -> None:
        if self.lit:
            self.red.duty_u16(0)
            self.green.duty_u16(0)
            self.blue.duty_u16(0)
            self.lit = False
        else:
            self.red.duty_u16(0)
            self.green.duty_u16(0)
            self.blue.duty_u16(1000)
            self.lit = True

    def ap_mode_start(self) -> None:
        self.blue_pin = Pin(self.blue_pin_number)
        self.blue_pin.value(0)
        self.blue = PWM(self.blue_pin)
        self.blue.freq(1000)

        self.red_pin = Pin(self.red_pin_number)
        self.red_pin.value(0)
        self.red = PWM(self.red_pin)
        self.red.freq(1000)

        self.green_pin = Pin(self.green_pin_number)
        self.green_pin.value(0)
        self.green = PWM(self.green_pin)
        self.green.freq(1000)

        self.lit = True
        if self.timer:
            self.timer.deinit()
        self.timer = Timer(-1)
        self.timer.init(period=1000, mode=Timer.PERIODIC, callback=self._ap_mode_cycle)

    def disco_start(self) -> None:
        self.blue_pin = Pin(self.blue_pin_number)
        self.blue_pin.value(0)
        self.blue = PWM(self.blue_pin)
        self.blue.freq(1000)

        self.red_pin = Pin(self.red_pin_number)
        self.red_pin.value(0)
        self.red = PWM(self.red_pin)
        self.red.freq(1000)

        self.green_pin = Pin(self.green_pin_number)
        self.green_pin.value(0)
        self.green = PWM(self.green_pin)
        self.green.freq(1000)

        self.lit = True
        if self.timer:
            self.timer.deinit()
        self.timer = Timer(-1)
        self.timer.init(period=1000, mode=Timer.PERIODIC, callback=self._random_colour)

    def disco_stop(self) -> None:
        self.lit = False
        self.timer.deinit()
        self.red_pin = Pin(self.red_pin_number, Pin.OUT)
        self.red_pin.value(0)
        self.green_pin = Pin(self.green_pin_number, Pin.OUT)
        self.green_pin.value(0)
        self.blue_pin = Pin(self.blue_pin_number, Pin.OUT)
        self.blue_pin.value(0)

    def value(self) -> bool:
        return self.lit


class Sensor:
    def __init__(self) -> None:
        pass

    def data_interface(self) -> float:
        return 0.0


class WifiResetButton(Sensor):
    def __init__(self, power_pin: int, signal_pin: int, status_led: StatusLed) -> None:
        self.wifi_reset_button_power_pin = Pin(power_pin, Pin.OUT)
        self.wifi_reset_button_power_pin.value(1)
        self.wifi_reset_button_signal_pin = Pin(signal_pin, Pin.IN, Pin.PULL_DOWN)
        self.debounced: bool = False
        self.pressed: bool = False
        self.DEBOUNCE_TIME = 70
        self.debounce_timer = Timer()
        self.wifi_reset_button_signal_pin.irq(
            trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING,
            handler=lambda pin: (
                self._handle_button_press()
                if pin.value() == 1
                else self._handle_button_release()
            ),
        )
        self.rising_time_ms = 0
        self.status_led = status_led

    def _reset_debounce(self) -> None:
        self.debounced = False

    def _handle_button_press(self) -> None:
        global led
        if not self.debounced and not self.pressed:
            self.debounced = True
            led.value(1)
            self.pressed = True
            self.rising_time_ms = time.ticks_ms()  # type: ignore
            self.debounce_timer.init(
                mode=Timer.ONE_SHOT,
                period=self.DEBOUNCE_TIME,
                callback=self._reset_debounce(),  # type: ignore
            )

    def _handle_button_release(self) -> None:
        global led
        if not self.debounced and self.pressed:
            self.debounced = True
            led.value(0)
            self.pressed = False
            elapsed_time_ms = time.ticks_diff(time.ticks_ms(), self.rising_time_ms)  # type: ignore
            if elapsed_time_ms > 3000:
                self.status_led.signal_wifi_reset()
                delete_wifi_config()
                reset()
            self.debounce_timer.init(
                mode=Timer.ONE_SHOT,
                period=self.DEBOUNCE_TIME,
                callback=self._reset_debounce(),  # type: ignore
            )


class CustomTimer:
    NTP_DELTA = 2208988800  # Time difference between 1900 and 1970 (in seconds)
    NTP_SERVER = "pool.ntp.org"

    def __init__(self) -> None:
        self.unix_time, _ = self.get_ntp_time()  # TODO: improve flow, this is ugly
        self.start_time = time.ticks_ms()  # type: ignore
        self.timer = Timer(-1)
        self.update_time_from_ntp()
        self.timer.init(
            period=3600000, mode=Timer.PERIODIC, callback=self.update_time_from_ntp
        )

    def get_ntp_time(self) -> Tuple[int, Optional[str]]:  # time, error
        try:
            ntp_query = b"\x1b" + 47 * b"\0"
            addr = socket.getaddrinfo(self.NTP_SERVER, 123)[0][-1]
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(1)
            s.sendto(ntp_query, addr)
            msg = s.recv(48)
            s.close()
            val = struct.unpack("!I", msg[40:44])[0]
            return val - self.NTP_DELTA, None
        except:
            return (
                946684800,
                "Failed to Update NTP time, defaulting to 1.1.2000",
            )  # Default to Jan 1, 2000

    def update_time_from_ntp(self, timer: Timer = None) -> None:
        try:
            new_unix_time, error = self.get_ntp_time()
            if error:
                print(error)
                return
            self.start_time = time.ticks_ms()  # type: ignore
            self.unix_time = new_unix_time
            print("NTP Time Updated:", new_unix_time)
            if new_unix_time < 0:
                print(
                    "NTP time is negative, defaulting to Jan 1 2000"
                )  # TODO: this is a temporary fix, find out why NTP time is occasionally negative
                self.unix_time = 946684800
        except Exception as e:
            print("Failed to update NTP time:", e)
            self.unix_time = 946684800  # Default to Jan 1, 2000

    def get_current_unix_time(self) -> int:
        elapsed_time = int(time.ticks_diff(time.ticks_ms(), self.start_time) // 1000)  # type: ignore
        current_unix_time = self.unix_time + elapsed_time
        return current_unix_time

    def get_pretty_time(self) -> str:
        try:
            current_unix_time = self.get_current_unix_time()
            adjusted_unix_time = current_unix_time + 3 * 3600
            datetime_tuple = utime.localtime(adjusted_unix_time)
            pretty_time = "{:04}-{:02}-{:02} {:02}:{:02}:{:02}".format(
                *datetime_tuple[:6]
            )
            return pretty_time
        except Exception as e:
            if "OverflowError" in str(e):
                print("OverflowError: overflow converting long int to machine word")
                return "2000-01-01 00:00:00"
            raise e


class AHT10:
    def __init__(self, i2c_address, i2c_bus, i2c_sda_pin, i2c_scl_pin, power_pin):
        self.i2c_address = i2c_address
        self.power_pin = Pin(power_pin, Pin.OUT)
        self.power_pin.value(1)  # power on AHT10
        time.sleep(0.1)  # waith for AHT10 power up
        self.i2c = I2C(i2c_bus, scl=Pin(i2c_scl_pin), sda=Pin(i2c_sda_pin), freq=100000)
        self.init_sensor()

    def init_sensor(self):
        for i in range(10):
            try:
                print(f"self.i2c_address: {self.i2c_address}")
                self.i2c.writeto(int(self.i2c_address), b"\xE1\x08\x00")
                time.sleep(0.1)
                break
            except OSError as e:
                if i < 9:
                    continue
                raise e

    def read_data(self):
        for i in range(10):
            try:
                self.i2c.writeto(int(self.i2c_address), b"\xAC\x33\x00")
                time.sleep(0.1)
                data = self.i2c.readfrom(int(self.i2c_address), 6)
                time.sleep(0.1)
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


class SensorHistory:
    def __init__(
        self, filename: str, length: int, custom_timer: CustomTimer, sensor_type: str
    ):
        self.sensor_type = sensor_type
        self.custom_timer = custom_timer
        self.persistent_history = PersistentList(
            filename=filename, max_lines=HISTORY_LENGTH
        )
        self.history = self.persistent_history.get_content().copy()
        print(f"Loaded {len(self.history)} values from {filename}")
        self.length = length
        self.history = buffer_list_with_zeros(self.history, HISTORY_LENGTH)

    def add(self, value: float) -> list[Tuple[float, int]]:
        event_unix_time = self.custom_timer.get_current_unix_time()
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


class StorageSensor(Sensor):
    def data_interface(self) -> int:
        return self.used_kilobytes()

    def used_kilobytes(self) -> int:
        used_size, _ = get_flash_memory_usage()
        return int(used_size / 1000)

    def total_kilobytes(self) -> int:
        _, total_size = get_flash_memory_usage()
        return int(total_size / 1000)


class MemorySensor(Sensor):
    def data_interface(self) -> int:
        return int(self.used_memory() / 1000)  # convert to kilobytes

    def used_memory(self) -> int:
        used_memory = mem_alloc()
        return int(used_memory)

    def free_memory(self) -> int:
        free_memory = mem_free()
        return int(free_memory)


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


class AHT10TemperatureSensor(Sensor):
    def __init__(self, aht10: AHT10) -> None:
        self.aht10 = aht10

    def data_interface(self) -> float:
        return self.read_temperature()

    def read_temperature(self) -> float:
        return self.aht10.get_temperature()


class AHT10HumiditySensor(Sensor):
    def __init__(self, aht10: AHT10):
        self.aht10 = aht10

    def data_interface(self) -> float:
        return self.read_humidity()

    def read_humidity(self) -> float:
        return self.aht10.get_humidity()


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


def get_ntp_time(host: str = "pool.ntp.org") -> int:  # TODO: make more robust
    # Reference time (Jan 1, 1970) in seconds since 1900 (NTP epoch)
    NTP_DELTA = 2208988800
    ntp_query = b"\x1b" + 47 * b"\0"
    addr = socket.getaddrinfo(host, 123)[0][-1]
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(1)
    res = s.sendto(ntp_query, addr)
    msg, addr = s.recvfrom(1024)
    s.close()
    val = struct.unpack("!I", msg[40:44])[0]
    print("time:", val - NTP_DELTA)
    return int(val - NTP_DELTA)


def print_memory_usage() -> None:
    collect()
    total_memory = mem_alloc() + mem_free()
    used_memory = mem_alloc()
    free_memory = mem_free()

    print(f"Total memory: {total_memory} bytes")
    print(f"Used memory: {used_memory} bytes")
    print(f"Free memory: {free_memory} bytes")


def get_flash_memory_usage() -> Tuple[int, int]:
    statvfs = uos.statvfs("/")
    total_blocks = statvfs[2]
    block_size = statvfs[0]
    free_blocks = statvfs[3]

    total_size = total_blocks * block_size
    free_size = free_blocks * block_size
    used_size = total_size - free_size

    return used_size, total_size


def save_config(updated_config: dict[str, Any]) -> None:
    with open(CONFIG_FILE, "w") as f:
        json.dump(updated_config, f)


def save_wifi_config(ssid: str, password: str) -> None:
    wifi_config = {"ssid": ssid, "password": password}
    with open(WIFI_CONFIG_FILE, "w") as f:
        json.dump(wifi_config, f)


def load_wifi_config() -> Tuple[Optional[str], Optional[str]]:
    try:
        with open(WIFI_CONFIG_FILE, "r") as f:
            wifi_config = json.load(f)
            return wifi_config["ssid"], wifi_config["password"]
    except:
        return None, None


def delete_wifi_config() -> None:
    try:
        remove(WIFI_CONFIG_FILE)
        print("Configuration file deleted successfully")
    except OSError as e:
        print("Error deleting configuration file:", e)


def stream_file(path: str, client: Any, content_type: str) -> None:
    try:
        with open(path, "r") as file:
            client.send(f"HTTP/1.1 200 OK\r\nContent-Type: {content_type}\r\n\r\n")
            while True:
                chunk = file.read(1024)  # Read file in chunks of 1024 bytes
                if not chunk:
                    break
                client.send(chunk)
    except:
        client.send("HTTP/1.1 404 Not Found\r\n\r\n")


def parse_query_params(query_string: str) -> dict[str, str]:
    params = {}
    if query_string:
        pairs = query_string.split("&")
        for pair in pairs:
            if "=" in pair:
                key, value = pair.split("=", 1)
                params[key] = value
            else:
                params[pair] = None  # type: ignore
    return params


# Function to handle incoming HTTP requests
def handle_request(conn: Any) -> None:
    global sensors, pico_timer
    # global storage_sensor, storage_monitor
    # global memory_sensor, memory_monitor
    global version
    global cloud_updater
    global friend_finder
    global status_led
    request = conn.recv(1024)
    request = str(request)
    ssid = None
    password = None

    if "GET /health" in request:
        conn.send("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n")
        conn.send(json.dumps({"type": "pico-health", "status": "ok"}))
        conn.close()
        return

    elif "GET /updates_available" in request:
        conn.send("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n")
        updates_available = cloud_updater.check_for_updates()
        conn.send(json.dumps({"updates_available": updates_available}))
        conn.close()
        return

    elif "POST /update_software" in request:
        updates_available = cloud_updater.check_for_updates()
        if not updates_available:
            conn.send("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n")
            conn.send(json.dumps({"status": "no updates available"}))
            conn.close()
            return
        conn.send("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n")
        conn.send(json.dumps({"status": "updating"}))
        conn.close()
        cloud_updater.update()
        return

    elif "GET /styles.css" in request:
        conn.send("HTTP/1.1 200 OK\r\nContent-Type: text/css\r\n\r\n")
        stream_file("styles.css", conn, "text/css")
        conn.close()
        return

    # TODO: find out why self hosted chart.js is not working
    # elif "GET /chart.js" in request:
    #    stream_file("chart.js", conn, "application/javascript")
    #    conn.close()
    #    return

    elif "POST /led" in request:
        # led.toggle()
        print(f"status_led: {status_led}")
        if status_led.value() == 1:
            status_led.disco_stop()
            print("disco stop")
        else:
            status_led.disco_start()
            print("disco start")
        conn.send("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n")
        conn.send(json.dumps({"led": status_led.value()}))
        conn.close()
        return

    elif "GET /time" in request:
        conn.send("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n")
        conn.send(json.dumps({"ntp_time": get_ntp_time()}))
        conn.close()
        return

    elif "GET /main.js" in request:
        stream_file("main.js", conn, "application/javascript")
        conn.close()
        return

    elif "GET /pico-charts.js" in request:
        stream_file("pico-charts.js", conn, "application/javascript")
        conn.close()
        return

    elif "GET /device_meta" in request:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
        device_meta = {
            "uuid": config["uuid"],
            "name": config["name"],
        }
        conn.send("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n")
        conn.send(json.dumps(device_meta))
        conn.close()
        return

    elif "GET /sensor_meta" in request:
        with open(CONFIG_FILE, "r") as f:
            sensor_meta = json.load(f)["sensors"]

        conn.send("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n")
        conn.send(json.dumps(sensor_meta))
        conn.close()
        return

    elif "GET /sensor_data" in request:
        print("request:", request)
        query_params = {}
        data = {}
        if "?sensor_index=" in request.split(" ")[1]:
            query_string = request.split(" ")[1].split("?", 1)[1]
            query_params = parse_query_params(query_string)
            sensor_index = int(query_params.get("sensor_index", 0))
            sensor_monitor = sensors.get_sensor(index=sensor_index)
            labels = list(range(HISTORY_LENGTH))
            labels.reverse()
            sensor_data = sensor_monitor.get_data()
            try:
                name = sensor_monitor.sensor.name  # type: ignore
            except:
                name = sensor_monitor.history.sensor_type
            values = []
            times = []
            for elem in sensor_data:
                try:
                    values.append(elem[0])
                    times.append(elem[1])
                except:
                    pass
            data = {
                # "labels": labels,
                # "values": sensor_monitor.get_data(),
                "index": sensor_index,
                "name": name,
                "type": sensor_monitor.history.sensor_type,
                "times": times,
                "values": values,
                "min": 0,
                "max": 100,
            }
        else:
            conn.send("HTTP/1.1 400 Bad Request\r\n\r\n")
            conn.close()
        conn.send("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n")
        conn.send(json.dumps(data))
        conn.close()
        return

    conn.send("HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n")
    stream_file("index.html", conn, "text/html")
    conn.close()


def handle_request_ap_mode(conn: Any) -> None:
    global status_led
    request = conn.recv(1024)
    request = str(request)
    if "POST /setup_wifi" in request:
        ssid_match = ure.search(r"ssid=([^&]*)", request)
        password_match = ure.search(r"password=([^&]*)", request)
        if ssid_match and password_match:
            ssid = ssid_match.group(1)
            password = password_match.group(1)
            ssid = ssid.replace("+", " ")
            password = password.replace("'", "")
            save_wifi_config(ssid, password)
            conn.send("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n")
            conn.send(json.dumps({"status": "ok"}))
            status_led.signal_wifi_set()
            reset()
    stream_file("ap_index.html", conn, "text/html")
    conn.close()


# Main function to start the web server
s = None
conn = None


def start_web_server() -> None:
    global s, conn, pico_timer, network_connection
    if s:
        s.close()
    addr = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
    print(socket.getaddrinfo("0.0.0.0", 80))
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.bind(addr)
        s.listen(1)
        print("Web server running on http://0.0.0.0:80")

        while True:
            try:
                if not s:
                    break
                conn, addr = s.accept()
                conn.settimeout(10.0)
                try:
                    print(pico_timer.get_pretty_time(), "Connection from", addr)
                except:
                    print("Connection from", addr)
                if network_connection.ap_active():
                    handle_request_ap_mode(conn)
                else:
                    handle_request(conn)
                conn.close()
                collect()
            except Exception as e:
                print("while true error:", e)
                sys.print_exception(e)  # type: ignore
                conn.close()  # type: ignore
                if "[Errno 110] ETIMEDOUT" in str(e):
                    continue
                raise e
    except Exception as e:
        print("Error: Address already in use")
        raise e
    finally:
        if conn:
            conn.close()
        s.close()


update_mutex = False


def periodic_restart(timer: Timer = None) -> None:
    print("periodic restart called")
    global update_mutex
    if update_mutex:
        print("cancelling periodic restart, update is running")
        return
    print("restarting in 10..")
    sleep(10)
    if not update_mutex:
        reset()
    print("periodic restart cancelled, update is running")


periodic_restart_timer = Timer()
periodic_restart_timer.init(
    period=60 * 60 * 1000, mode=Timer.PERIODIC, callback=periodic_restart
)


def http_get(url: str, timeout: int = 5) -> Any:
    if url.startswith("https://"):
        protocol = "https"
        port = 443
        url = url[8:]
    elif url.startswith("http://"):
        protocol = "http"
        port = 80
        url = url[7:]
    else:
        raise ValueError("URL must start with 'http://' or 'https://'")
    host, path = url.split("/", 1)
    path = "/" + path
    addr_info = socket.getaddrinfo(host, port)[0][-1]
    s = socket.socket()
    s.settimeout(timeout)
    s.connect(addr_info)
    if protocol == "https":
        s = ssl.wrap_socket(s, server_hostname=host)  # type: ignore
    s.sendall(
        bytes(
            "GET {} HTTP/1.1\r\nHost: {}\r\nConnection: close\r\n\r\n".format(
                path, host
            ),
            "utf-8",
        )
    )
    response = b""
    while True:
        data = s.recv(1024)
        if not data:
            break
        response += data
    s.close()
    response = response.decode("utf-8")  # type: ignore
    header, body = response.split("\r\n\r\n", 1)  # type: ignore
    status_code = int(header.split()[1])
    if status_code == 200:
        return json.loads(body)
    else:
        raise Exception("HTTP request failed with status code: {}".format(status_code))


class NetworkConnection:
    wlan = None
    ap = None
    ssid = None
    password = None
    ap_ssid = "iot"
    ap_password = "laiskajaakko"

    def __init__(self) -> None:
        self.ssid, self.password = load_wifi_config()
        self.timer = Timer()
        self.timer.init(
            period=20000, mode=Timer.PERIODIC, callback=self.check_connectivity
        )
        if self.ssid and self.password:
            self.connect_to_wifi()
        else:
            self.start_ap()

    def ap_active(self) -> bool:
        return bool(self.ap and self.ap.active())

    def wlan_active(self) -> bool:
        return bool(self.wlan and self.wlan.isconnected())

    def start_ap(self) -> None:
        if self.wlan:
            self.wlan.active(False)
            for _ in range(10):
                if not self.wlan.active():
                    break
                sleep(1)
        self.ap = network.WLAN(network.AP_IF)
        self.ap.config(essid=self.ap_ssid, password=self.ap_password)
        self.ap.active(True)
        for _ in range(10):
            if self.ap.active():
                break
            sleep(1)
        print(f"Access point active: {self.ap.ifconfig()}")

    def connect_to_wifi(self) -> None:
        if self.ap:
            self.ap.active(False)
        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(True)
        self.wlan.connect(self.ssid, self.password)
        print(f"Connecting to wifi: {self.ssid}")
        for _ in range(10):
            if self.wlan.isconnected():
                print(f"Connected to: {self.ssid}, {self.wlan.ifconfig()}")
                return
            sleep(1)
        print(f"Failed to connect to: {self.ssid}")

    def check_connectivity(self, timer: Timer = None) -> None:
        if self.wlan and not self.wlan.isconnected():
            print("connection lost, reconnecting to wifi..")
            self.connect_to_wifi()
        elif self.ap:
            print(f"ap ok: {self.ap.ifconfig()}")
        else:
            print(f"wifi ok: {self.wlan.ifconfig()}")  # type: ignore


class FriendFinder:
    friends: dict[str, str] = {}
    next_host_id = 14
    my_ip = ""
    gateway = ""

    def __init__(self, network_connection: NetworkConnection):
        try:
            with open("friends.json", "r") as f:
                self.friends = json.load(f)
        except:
            self.friends = {}
        self.network_connection = network_connection
        self.my_ip = self.network_connection.wlan.ifconfig()[0]  # type: ignore
        self.gateway = self.network_connection.wlan.ifconfig()[2]  # type: ignore
        self.timer = Timer()
        self.timer.init(
            period=10000, mode=Timer.PERIODIC, callback=self.find_friends
        )  # every 10 seconds

    def get_friends(self) -> str:
        friend_string = ""
        for friend_ip, status in self.friends.items():
            friend_string += f'<a href="{friend_ip}">{friend_ip}</a>: {status}\n'
        return friend_string

    def get_friends_with_health_check(self) -> dict[str, str]:
        for friend_ip in self.friends:
            url = f"http://{friend_ip}/health"
            try:
                response = http_get(url)
                if response["type"] == "pico-health":
                    self.friends[friend_ip] = "ok"
                    continue
            except:
                pass
            self.friends[friend_ip] = "error"
        return self.friends

    def find_friends(self, timer: Timer = None) -> None:
        if not self.network_connection.wlan_active():
            print("wifi not active, skipping friend finder")
            return
        octets = self.my_ip.split(".")
        if self.next_host_id > 255:
            self.next_host_id = 1
        ip = f"{octets[0]}.{octets[1]}.{octets[2]}.{self.next_host_id}"

        while ip == self.my_ip or ip == self.gateway:
            self.next_host_id += 1
            ip = f"{octets[0]}.{octets[1]}.{octets[2]}.{self.next_host_id}"
        url = f"http://{ip}/health"
        print(f"GET {url}")
        try:
            response = http_get(url, timeout=3)
            if response["type"] == "pico-health":
                print(f"found friend: {ip}")
                self.friends[ip] = "ok"
                with open("friends.json", "w") as f:
                    json.dump(self.friends, f)
        except:
            pass
        self.next_host_id += 1


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

    def __init__(self) -> None:
        with open("config.json", "r") as f:
            config = json.load(f)
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
                        custom_timer=pico_timer,
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
                        custom_timer=pico_timer,
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
                        custom_timer=pico_timer,
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
                        custom_timer=pico_timer,
                        sensor_type=sensor_type,
                    ),
                )
                continue


status_led = StatusLed()

WifiResetButton(power_pin=5, signal_pin=3, status_led=status_led)

network_connection = NetworkConnection()

while True:
    if network_connection.ap_active():
        status_led.ap_mode_start()
        start_web_server()
        break

    if network_connection.wlan_active():
        break

    sleep(5)

cloud_updater = CloudUpdater()
pico_timer = CustomTimer()
sensors = Sensors()
# storage_sensor = StorageSensor()
# storage_sensor_history = SensorHistory(
#    "storage.log", HISTORY_LENGTH, pico_timer, sensor_type="storage"
# )
# storage_monitor = SensorMonitor(storage_sensor, storage_sensor_history)

memory_sensor = MemorySensor()
# memory_sensor_history = SensorHistory(
#    "memory.log", HISTORY_LENGTH, pico_timer, sensor_type="memory"
# )
# memory_monitor = SensorMonitor(memory_sensor, memory_sensor_history)

# friend_finder = FriendFinder(network_connection)


periodic_restart_timer = Timer()
periodic_restart_timer.init(
    period=86400000, mode=Timer.PERIODIC, callback=periodic_restart
)
start_web_server()
