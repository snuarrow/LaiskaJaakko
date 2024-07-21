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

import network
import socket
import ure
import struct
import time
import utime
from time import sleep
import os
from os import remove, rename
import ssl
import json
from machine import Pin, ADC, Timer, I2C, freq, reset, PWM
from gc import collect, mem_alloc, mem_free
import uos
import ubinascii
import sys
from typing import Any, Tuple
import random

# periodic_restart_timer = Timer()
# periodic_restart_timer.init(period=60*60*1000, mode=Timer.PERIODIC, callback=periodic_restart)

frequency_MHz = 125
freq(frequency_MHz * 1000000)
print("Current frequency: ", freq() / 1000000, "MHz")
# AHT10_I2C_ADDRESS = 0x38
HISTORY_LENGTH = 60
SAMPLING_FREQUENCY_SECONDS = 60
hostname = f"pico-plant-monitor"
network.hostname(hostname)
WIFI_CONFIG_FILE = "wifi_config.json"
CONFIG_FILE = "config.json"
led = Pin("LED", Pin.OUT)
led.value(1)


def generate_uuid():
    random_bytes = uos.urandom(16)
    uuid = ubinascii.hexlify(random_bytes).decode()
    return f"{uuid[:8]}-{uuid[8:12]}-{uuid[12:16]}-{uuid[16:20]}-{uuid[20:]}"


class CloudUpdater:

    branch: str = "main"
    base_url: str = (
        f"https://raw.githubusercontent.com/snuarrow/LaiskaJaakko/{branch}/pico-sensor/"
    )
    current_version: int = 0
    updates_available: bool = False

    def __init__(self):
        self.updates_available = self.check_for_updates()

    def check_for_updates(self):
        print("checking for updates..")
        self.version_config = self._load_file("version.json")
        self.current_version = self.version_config["version"]
        self._download_file("version.json", "remote-version.json")
        self.remote_version_config = self._load_file("remote-version.json")
        self.remote_version = self.remote_version_config["version"]
        self.updates_available = self.remote_version > self.current_version
        return self.updates_available

    def pretty_current_version(self):
        return f"v.{self.current_version}"

    def update(self, timer=None):
        print("updating..")
        global update_mutex
        update_mutex = True
        sleep(3)
        self.version_config = self._load_file("version.json")
        for file in self.version_config["files_included"]:
            print(f"downloading {file}")
            self._download_file(file, file)
        self._install_update()

    def _download_file(self, remote_file_name, local_file_name):
        https_file_url = f"{self.base_url}{remote_file_name}"
        print(f"Downloading file.. {https_file_url}")
        _, _, host, path = https_file_url.split("/", 3)
        path = "/" + path

        addr = socket.getaddrinfo(host, 443)[0][-1]
        s = socket.socket()
        s.connect(addr)
        s = ssl.wrap_socket(s, server_hostname=host)
        request = "GET {} HTTP/1.1\r\nHost: {}\r\nConnection: close\r\n\r\n".format(
            path, host
        )
        s.write(request.encode("utf-8"))
        response = b""
        while b"\r\n\r\n" not in response:
            response += s.read(1)
        _, body = response.split(b"\r\n\r\n", 1)
        with open(local_file_name, "wb") as file:
            file.write(body)
            while True:
                data = s.read(1024)
                if not data:
                    break
                file.write(data)
        s.close()

    def _install_update(self):
        print("installing update..")
        sleep(1)
        reset()

    def _load_file(self, filename):
        with open(filename, "r") as f:
            version_config = json.load(f)
            return version_config


class StatusLed:
    def __init__(self, brightness: float = 0.01) -> None:
        self.brightness = brightness
        with open("config.json", "r") as f:
            led_config = json.load(f)["rgb_led"]
        self.blue_pin_number = led_config["blue_pin"]
        self.red_pin_number = led_config["red_pin"]
        self.green_pin_number = led_config["green_pin"]
        self.disco_start()
        self.disco_stop()
        self.disco_start()

    def random_colour(self, timer=None):
        random_red = random.randint(0, int(65536 * self.brightness))
        random_green = random.randint(0, int(65536 * self.brightness))
        random_blue = random.randint(0, int(65536 * self.brightness))
        self.red.duty_u16(random_red)
        self.green.duty_u16(random_green)
        self.blue.duty_u16(random_blue)

    def disco_start(self):
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

        self.lit = 1
        self.timer = Timer(-1)
        self.timer.init(period=1000, mode=Timer.PERIODIC, callback=self.random_colour)

    def disco_stop(self):
        self.lit = 0
        self.timer.deinit()
        self.red_pin = Pin(self.red_pin_number, Pin.OUT)
        self.red_pin.value(0)
        self.green_pin = Pin(self.green_pin_number, Pin.OUT)
        self.green_pin.value(0)
        self.blue_pin = Pin(self.blue_pin_number, Pin.OUT)
        self.blue_pin.value(0)

    def value(self):
        return self.lit


class SensorMonitor:  # Has MoistureSensor and SensorHistory, periodicaly reads data from MoistureSensor and stores it in SensorHistory
    def __init__(self, sensor, history) -> None:
        self.sensor = sensor
        self.history: SensorHistory = history
        self.timer: Timer = Timer(-1)
        self._record_data()
        self.timer.init(period=SAMPLING_FREQUENCY_SECONDS * 1000, mode=Timer.PERIODIC, callback=self._record_data)

    def _record_data(self, timer=None) -> None:
        self.history.add(self.sensor.data_interface())

    def get_latest(self) -> Tuple[Any, int]:
        return self.history.get()[-1]

    def get_sensor(self):
        return self.sensor

    def get_data(self) -> list[Tuple[Any, int]]:
        return self.history.get()

    def toDict(self) -> dict:
        return {}


class CustomTimer:
    NTP_DELTA = 2208988800  # Time difference between 1900 and 1970 (in seconds)
    NTP_SERVER = "pool.ntp.org"

    def __init__(self):
        self.unix_time, _ = self.get_ntp_time()
        self.start_time = time.ticks_ms()
        self.timer = Timer(-1)
        self.update_time_from_ntp()
        self.timer.init(
            period=3600000, mode=Timer.PERIODIC, callback=self.update_time_from_ntp
        )

    def get_ntp_time(self):
        try:
            ntp_query = b"\x1b" + 47 * b"\0"
            addr = socket.getaddrinfo(self.NTP_SERVER, 123)[0][-1]
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(1)
            s.sendto(ntp_query, addr)
            msg = s.recv(48)
            s.close()
            val = struct.unpack("!I", msg[40:44])[0]
            return val - self.NTP_DELTA, False
        except:
            return 946684800, True  # Default to Jan 1, 2000

    def update_time_from_ntp(self, timer=None):
        try:
            new_unix_time, error = self.get_ntp_time()
            if error:
                print("Failed to update NTP time")
                return
            self.start_time = time.ticks_ms()
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

    def get_current_unix_time(self):
        elapsed_time = time.ticks_diff(time.ticks_ms(), self.start_time) // 1000
        current_unix_time = self.unix_time + elapsed_time
        return current_unix_time

    def get_pretty_time(self):
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


class StorageSensor:
    def data_interface(self):
        return self.used_kilobytes()

    def used_kilobytes(self):
        used_size, _ = get_flash_memory_usage()
        return used_size / 1000

    def total_kilobytes(self):
        _, total_size = get_flash_memory_usage()
        return total_size / 1000


class MemorySensor:
    def data_interface(self):
        return self.used_memory() / 1000  # convert to kilobytes

    def used_memory(self):
        used_memory = mem_alloc()
        return used_memory

    def free_memory(self):
        free_memory = mem_free()
        return free_memory


class MoistureSensor:
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

    def data_interface(self):
        return self.percentage()

    def voltage(self):
        self.adc_power_pin.value(1)
        sleep(0.01)
        adc_value = self.adc.read_u16()
        self.adc_power_pin.value(0)
        voltage = adc_value * 3.3 / 65535
        return voltage

    def percentage(self):
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


class PicoTemperatureSensor:
    conversion_factor = 3.3 / (65535)
    temperature_sensor = ADC(4)

    def data_interface(self):
        return self.read_temperature()

    def read_temperature(self):
        raw_value = self.temperature_sensor.read_u16()
        voltage = raw_value * self.conversion_factor
        temperature_c = 27 - (voltage - 0.706) / 0.001721
        return temperature_c


class AHT10TemperatureSensor:
    def __init__(self, aht10):
        self.aht10 = aht10

    def data_interface(self):
        return self.read_temperature()

    def read_temperature(self):
        return self.aht10.get_temperature()


class AHT10HumiditySensor:
    def __init__(self, aht10):
        self.aht10 = aht10

    def data_interface(self):
        return self.read_temperature()

    def read_temperature(self):
        return self.aht10.get_humidity()


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
                time.sleep(0.05)
                break
            except OSError as e:
                if i < 9:
                    continue
                raise e

    def read_data(self):
        for i in range(10):
            try:
                self.i2c.writeto(int(self.i2c_address), b"\xAC\x33\x00")
                time.sleep(0.05)
                data = self.i2c.readfrom(int(self.i2c_address), 6)
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
        temperature = ((temperature * 200) / 1048576) - 50

        return temperature, humidity

    def get_temperature(self):
        data = self.read_data()
        temperature = ((data[3] & 0x0F) << 16) | (data[4] << 8) | data[5]
        temperature = ((temperature * 200) / 1048576) - 50
        return temperature

    def get_humidity(self):
        data = self.read_data()
        humidity = ((data[1] << 16) | (data[2] << 8) | data[3]) >> 4
        humidity = (humidity * 100) / 1048576
        return humidity


class PersistentList:
    def __init__(self, filename: str, max_lines: int, tail_lines: int = 10):
        self.filename = filename
        self.data = []
        self.max_lines = max_lines
        self.tail_lines = tail_lines
        self._load_from_file()

    def get_content(self):
        return self.data

    def _load_from_file(self):
        try:
            self._read_last_n_lines()
        except:
            self.data = []

    def _read_last_n_lines(self):  # TODO: read in reverse order to speedup startup time
        with open(self.filename, "r") as file:
            for line in file:
                line_splits = line.split(",")
                item = line_splits[0]
                event_unix_time: int = int(line_splits[1])
                self.data.append((item, event_unix_time))
                if len(self.data) > self.max_lines:
                    self.data.pop(0)

    def append(self, item, event_unix_time):
        self.data.append((item, event_unix_time))
        if len(self.data) > self.max_lines:
            self.data.pop(0)
        with open(self.filename, "a") as file:
            file.write(f"{item},{event_unix_time}\n")
        if self._history_file_length() > self.max_lines + self.tail_lines:
            self._trim_history_file()

    def _trim_history_file(self):
        temporary_file_name = f"{self.filename}.tmp"
        with open(temporary_file_name, "wb") as temporary_file:
            print("trimming history:", self.filename)
            for item, event_unix_time in self.data:
                temporary_file.write(f"{item},{event_unix_time}\n")
        remove(self.filename)
        rename(temporary_file_name, self.filename)

    def _history_file_length(self):
        with open(self.filename, "r") as file:
            return sum(1 for _ in file)

    def __getitem__(self, index):
        return self.data[index]

    def __len__(self):
        return len(self.data)

    def __repr__(self):
        return repr(self.data)


def buffer_list_with_zeros(input_list, n):
    if len(input_list) < n:
        # Calculate the number of zeros needed
        num_zeros = n - len(input_list)
        # Create a list of zeros
        zeros_list = [0] * num_zeros
        # Prepend the zeros to the input list
        buffered_list = zeros_list + input_list
        return buffered_list
    else:
        return input_list


class SensorHistory:
    def __init__(
        self, filename: str, length: int, custom_timer: CustomTimer, sensor_type: str
    ):
        self.sensor_type = sensor_type
        self.custom_timer = custom_timer
        self.persistent_history = PersistentList(filename=filename, max_lines=HISTORY_LENGTH)
        self.history = self.persistent_history.get_content().copy()
        print(f"Loaded {len(self.history)} values from {filename}")
        self.length = length
        self.history = buffer_list_with_zeros(self.history, HISTORY_LENGTH)

    def add(self, value):
        event_unix_time = self.custom_timer.get_current_unix_time()
        self.history.append((value, event_unix_time))
        self.persistent_history.append(value, event_unix_time)
        # remove the first element if the history is too long
        if len(self.history) > self.length:
            self.history.pop(0)
        return self.history

    def get(self):
        return self.history


def get_ntp_time(host="pool.ntp.org"):  # TODO: make more robust
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
    return val - NTP_DELTA


def print_memory_usage():
    collect()
    total_memory = mem_alloc() + mem_free()
    used_memory = mem_alloc()
    free_memory = mem_free()

    print(f"Total memory: {total_memory} bytes")
    print(f"Used memory: {used_memory} bytes")
    print(f"Free memory: {free_memory} bytes")


def get_flash_memory_usage():
    statvfs = uos.statvfs("/")
    total_blocks = statvfs[2]
    block_size = statvfs[0]
    free_blocks = statvfs[3]

    total_size = total_blocks * block_size
    free_size = free_blocks * block_size
    used_size = total_size - free_size

    return used_size, total_size


def load_config():
    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
            return config["uuid"], config["givenName"]
    except:
        return "undefined-uuid", "undefined given name"


def save_config(updated_config: dict):
    with open(CONFIG_FILE, "w") as f:
        json.dump(updated_config, f)


def save_wifi_config(ssid, password):
    wifi_config = {"ssid": ssid, "password": password}
    with open(WIFI_CONFIG_FILE, "w") as f:
        json.dump(wifi_config, f)


# Function to load Wi-Fi configuration from a file
def load_wifi_config():
    try:
        with open(WIFI_CONFIG_FILE, "r") as f:
            wifi_config = json.load(f)
            return wifi_config["ssid"], wifi_config["password"]
    except:
        return None, None


def delete_wifi_config():
    try:
        remove(WIFI_CONFIG_FILE)
        print("Configuration file deleted successfully")
    except OSError as e:
        print("Error deleting configuration file:", e)


def load_chart(given_id: str):
    pass


# Function to stream files
def stream_file(path, client, content_type):
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


def serve_file(path):
    try:
        with open(path, "r") as file:
            return file.read()
    except:
        return None


def parse_query_params(query_string):
    params = {}
    if query_string:
        pairs = query_string.split("&")
        for pair in pairs:
            if "=" in pair:
                key, value = pair.split("=", 1)
                params[key] = value
            else:
                params[pair] = None
    return params


# Function to handle incoming HTTP requests
def handle_request(conn):
    global sensors, pico_timer
    global storage_sensor, storage_monitor
    global memory_sensor, memory_monitor
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
        if not cloud_updater.updates_available:
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

    elif "POST /setup_wifi" in request:
        ssid_match = ure.search(r"ssid=([^&]*)", request)
        password_match = ure.search(r"password=([^&]*)", request)
        if ssid_match and password_match:
            ssid = ssid_match.group(1)
            password = password_match.group(1)
            ssid = ssid.replace("+", " ")
            password = password.replace("'", "")
            print("SSID:", ssid)
            print("Password:", password)
            save_wifi_config(ssid, password)
            conn.send("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n")
            conn.send(json.dumps({"status": "ok"}))
            reset()

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

    elif "POST /memory" in request:
        print_memory_usage()

    elif "GET /time" in request:
        return get_ntp_time()

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
            sensor_index = query_params.get("sensor_index")
            sensor_monitor = sensors.get_sensor(index=sensor_index)
            labels = list(range(HISTORY_LENGTH))
            labels.reverse()
            sensor_data = sensor_monitor.get_data()
            try:
                name = sensor_monitor.sensor.name
            except:
                name = sensor_monitor.history.sensor_type
            values = []
            times = []
            for elem in sensor_data:
                values.append(elem[0])
                times.append(elem[1])
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


# Main function to start the web server
s = None
conn = None


def start_web_server():
    global s, conn, pico_timer
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
                print(pico_timer.get_pretty_time(), "Connection from", addr)
                handle_request(conn)
                conn.close()
                collect()
            except Exception as e:
                print("while true error:", e)
                sys.print_exception(e)
                conn.close()
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


def periodic_restart(timer=None):
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


def http_get(url, timeout=5):
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
        s = ssl.wrap_socket(s, server_hostname=host)
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
    response = response.decode("utf-8")
    header, body = response.split("\r\n\r\n", 1)
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

    def __init__(self):
        self.ssid, self.password = load_wifi_config()
        self.timer = Timer()
        self.timer.init(
            period=20000, mode=Timer.PERIODIC, callback=self.check_connectivity
        )
        if self.ssid and self.password:
            self.connect_to_wifi()
        else:
            self.start_ap()

    def ap_active(self):
        return self.ap and self.ap.active()

    def wlan_active(self):
        return self.wlan and self.wlan.isconnected()

    def start_ap(self):
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

    def connect_to_wifi(self):
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

    def check_connectivity(self, timer=None):
        if self.wlan and not self.wlan.isconnected():
            print("connection lost, reconnecting to wifi..")
            self.connect_to_wifi()
        elif self.ap:
            print(f"ap ok: {self.ap.ifconfig()}")
        else:
            print(f"wifi ok: {self.wlan.ifconfig()}")


class FriendFinder:
    friends = {}
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
        self.my_ip = self.network_connection.wlan.ifconfig()[0]
        self.gateway = self.network_connection.wlan.ifconfig()[2]
        self.timer = Timer()
        self.timer.init(
            period=10000, mode=Timer.PERIODIC, callback=self.find_friends
        )  # every 10 seconds

    def get_friends(self):
        friend_string = ""
        for friend_ip, status in self.friends.items():
            friend_string += f'<a href="{friend_ip}">{friend_ip}</a>: {status}\n'
        return friend_string

    def get_friends_with_health_check(self):
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

    def find_friends(self, timer=None):
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

    def get_sensor(self, uuid: str = None, index: int = None):
        if index is not None:
            print(
                f"sensor_monitors.items() {list(self.sensor_monitors.keys())[int(index)]}"
            )
            return self.sensor_monitors[list(self.sensor_monitors.keys())[int(index)]]
        if uuid:
            return self.sensor_monitors[uuid]
        raise ValueError("uuid or index must be provided")

    def toJSON(self) -> dict:
        all_sensor_data = {"undefined": 0}  # TODO: implement
        for uuid, sensor_monitor in self.sensor_monitors:
            for event, unix_time in sensor_monitor.get_data():
                pass

        return all_sensor_data

    def __init__(self):
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

network_connection = NetworkConnection()

while True:
    if network_connection.ap_active():
        start_web_server()
        break

    if network_connection.wlan_active():
        break

    sleep(5)

pico_timer = CustomTimer()
sensors = Sensors()
storage_sensor = StorageSensor()
storage_sensor_history = SensorHistory(
    "storage.log", HISTORY_LENGTH, pico_timer, sensor_type="storage"
)
storage_monitor = SensorMonitor(storage_sensor, storage_sensor_history)

memory_sensor = MemorySensor()
memory_sensor_history = SensorHistory(
    "memory.log", HISTORY_LENGTH, pico_timer, sensor_type="memory"
)
memory_monitor = SensorMonitor(memory_sensor, memory_sensor_history)
# cloud_updater = CloudUpdater()
# friend_finder = FriendFinder(network_connection)


periodic_restart_timer = Timer()
periodic_restart_timer.init(
    period=86400000, mode=Timer.PERIODIC, callback=periodic_restart
)
print(f"storage usage: {get_flash_memory_usage()}")
start_web_server()
