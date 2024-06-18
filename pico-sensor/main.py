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
from os import remove
import ssl
import json
from machine import Pin, ADC, Timer, I2C, freq, reset
from gc import collect, mem_alloc, mem_free
import uos

# periodic_restart_timer = Timer()
# periodic_restart_timer.init(period=60*60*1000, mode=Timer.PERIODIC, callback=periodic_restart)


frequency_MHz = 64
freq(frequency_MHz * 1000000)
print("Current frequency: ", freq() / 1000000, "MHz")
AHT10_I2C_ADDRESS = 0x38
hostname = f"pico-plant-monitor"
network.hostname(hostname)
WIFI_CONFIG_FILE = "wifi_config.json"
CONFIG_FILE = "config.json"
led = Pin("LED", Pin.OUT)
led.value(1)
i2c = I2C(1, scl=Pin(3), sda=Pin(2), freq=100000)




class CloudUpdater:

    branch: str = "main"
    base_url: str = f"https://raw.githubusercontent.com/snuarrow/LaiskaJaakko/{branch}/pico-sensor/"
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
        self.version_config = self._load_file("version.json")
        for file in self.version_config["files_included"]:
            print(f"downloading {file}")
            self._download_file(file, file)
        self._install_update()

    def _download_file(self, remote_file_name, local_file_name):
        https_file_url = f"{self.base_url}{remote_file_name}"
        print(f"Downloading file.. {https_file_url}")
        _, _, host, path = https_file_url.split('/', 3)
        path = '/' + path

        addr = socket.getaddrinfo(host, 443)[0][-1]
        s = socket.socket()
        s.connect(addr)
        s = ssl.wrap_socket(s, server_hostname=host)
        request = 'GET {} HTTP/1.1\r\nHost: {}\r\nConnection: close\r\n\r\n'.format(path, host)
        s.write(request.encode('utf-8'))
        response = b""
        while b"\r\n\r\n" not in response:
            response += s.read(1)
        _, body = response.split(b'\r\n\r\n', 1)
        with open(local_file_name, 'wb') as file:
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


class SensorMonitor:  # Has MoistureSensor and SensorHistory, periodicaly reads data from MoistureSensor and stores it in SensorHistory
    def __init__(self, sensor, history):
        self.sensor = sensor
        self.history = history
        self.timer = Timer(-1)
        self._read_data()
        self.timer.init(period=60000, mode=Timer.PERIODIC, callback=self._read_data)

    def _read_data(self, timer=None):
        self.history.add(self.sensor.data_interface())

    def get_data(self):
        return self.history.get()


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
                print("NTP time is negative, defaulting to Jan 1 2000")  # TODO: this is a temporary fix, find out why NTP time is occasionally negative
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


class MoistureSensor:
    def __init__(self, voltage_0_percent, voltage_100_percent):
        self.adc_power_pin = Pin(20, Pin.OUT)
        self.adc = ADC(Pin(26))
        self.voltage_0_percent = voltage_0_percent
        self.voltage_100_percent = voltage_100_percent

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
        return aht10.get_temperature()


class AHT10HumiditySensor:
    def __init__(self, aht10):
        self.aht10 = aht10

    def data_interface(self):
        return self.read_temperature()

    def read_temperature(self):
        return aht10.get_humidity()


class AHT10:
    def __init__(self, i2c):
        self.i2c = i2c
        self.init_sensor()

    def init_sensor(self):
        for i in range(10):
            try:
                self.i2c.writeto(AHT10_I2C_ADDRESS, b"\xE1\x08\x00")
                time.sleep(0.05)
                break
            except OSError as e:
                if i < 9:
                    continue
                raise e

    def read_data(self):
        for i in range(10):
            try:
                self.i2c.writeto(AHT10_I2C_ADDRESS, b"\xAC\x33\x00")
                time.sleep(0.05)
                data = self.i2c.readfrom(AHT10_I2C_ADDRESS, 6)
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
    def __init__(self, filename, max_lines=None, tail_lines=10):
        self.filename = filename
        self.data = []
        self.max_lines = max_lines
        self.tail_lines = tail_lines
        self._load_from_file()

    def get_content(self):
        return self.data

    def _load_from_file(self):
        if self.max_lines is None:
            try:
                with open(self.filename, "r") as file:
                    self.data = [line.strip() for line in file]
            except FileNotFoundError:
                self.data = []
        else:
            try:
                with open(self.filename, "rb") as file:
                    self._read_last_n_lines(file)
            except:
                self.data = []

    def _read_last_n_lines(self, file):
        with open(self.filename, "r") as file:
            for line in file:
                self.data.append(float(line.strip()))
                if len(self.data) > self.max_lines:
                    self.data.pop(0)

    def append(self, item):
        self.data.append(item)
        if len(self.data) > self.max_lines:
            self.data.pop(0)
        with open(self.filename, "a") as file:
            file.write(f"{item}\n")
        if self._history_file_length() > self.max_lines + self.tail_lines:
            self._trim_history_file()

    def _trim_history_file(self):
        temporary_file_name = f"{self.filename}.tmp"
        with open(temporary_file_name, "wb") as temporary_file:
            print("trimming history:", self.filename)
            for elem in self.data:
                temporary_file.write(f"{elem}\n")
        os.remove(self.filename)
        os.rename(temporary_file_name, self.filename)

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

    def __init__(self, filename, length):
        self.persistent_history = PersistentList(filename=filename, max_lines=60)
        self.history = self.persistent_history.get_content().copy()
        print(f"Loaded {len(self.history)} values from {filename}")
        self.length = length
        self.history = buffer_list_with_zeros(self.history, 60)

    def add(self, value):
        self.history.append(value)
        self.persistent_history.append(value)
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


ap = network.WLAN(network.AP_IF)


# Function to start the Wi-Fi access point
def start_ap(ssid="iot", password="laiskajaakko"):
    ap.config(essid=ssid, password=password)
    ap.active(True)
    while ap.active() == False:
        pass
    print("Access point active")
    print(ap.ifconfig())


# Function to connect to an external Wi-Fi network
wlan = None


def connect_to_wifi(ssid, password):
    global wlan
    ap.active(False)
    print("shutting down ap")
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    print("waiting wifi to start")
    wlan.connect(ssid, password)
    print("connecting..")
    for i in range(10):
        if wlan.isconnected():
            break
        sleep(1)
    if not wlan.isconnected():
        delete_wifi_config()
        return
    print("Connected to", ssid)
    print(wlan.ifconfig())
    save_wifi_config(ssid, password)
    print("Saved wifi credentials")


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
    global moisture_sensor, moisture_sensor_history, pico_timer, moisture_monitor
    global pico_temperature_sensor, pico_temperature_sensor_history, pico_temperature_monitor
    global aht10_temperature_monitor
    global aht10_humidity_monitor
    global storage_sensor
    global version
    global pico_timer
    global cloud_updater
    request = conn.recv(1024)
    request = str(request)
    ssid = None
    password = None

    if "GET /updates_available" in request:
        conn.send("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n")
        updates_available = cloud_updater.check_for_updates()
        conn.send(json.dumps({"updates_available": updates_available}))
        conn.close()
        return

    if "POST /update_software" in request:
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

    if "GET /chart.js" in request:
        stream_file("chart.js", conn, "application/javascript")
        conn.close()
        return

    if "GET /pico-chart.js" in request:
        response = serve_file("pico-chart.js")
        query_string = request.split(" ")[1].split("?", 1)[1]
        query_params = parse_query_params(query_string)
        for key, value in query_params.items():
            response = response.replace(key, value)
        conn.send(f"HTTP/1.1 200 OK\r\nContent-Type: application/javascript\r\n\r\n")
        conn.send(response)
        conn.close()
        return

    if "POST /setup_wifi" in request:
        ssid_match = ure.search(r"ssid=([^&]*)", request)
        password_match = ure.search(r"password=([^&]*)", request)
        if ssid_match and password_match:
            ssid = ssid_match.group(1)
            password = password_match.group(1)

    if "POST /led" in request:
        led.toggle()
        conn.send("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n")
        conn.send(json.dumps({"led": led.value()}))
        conn.close()
        return

    if "POST /memory" in request:
        print_memory_usage()

    if "GET /time" in request:
        return get_ntp_time()

    if (
        "GET /data" in request
    ):  # TODO: read from history instead to avoid corrosive wear on moisture sensor
        return_data = json.dumps(
            {
                "moisture_sensor_voltage": moisture_sensor.voltage(),
                "moisture_sensor_percentage": moisture_sensor.percentage(),
                "pico_temperature": pico_temperature_sensor.read_temperature(),
            }
        )
        response = f"""HTTP/1.1 200 OK
Content-Type: text/plain

{return_data}"""
        conn.send(response)
        conn.close()
        return response

    if "GET /main.js" in request:
        stream_file("main.js", conn, "application/javascript")
        conn.close()
        return

    if "GET /moisture_data" in request:
        labels = list(range(60))
        labels.reverse()
        data = {"labels": labels, "values": moisture_monitor.get_data()}
        response = json.dumps(data)
        conn.send("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n")
        conn.send(response)
        conn.close()
        return

    if "GET /pico_temperature_data" in request:
        labels = list(range(60))
        labels.reverse()
        data = {"labels": labels, "values": pico_temperature_monitor.get_data()}
        response = json.dumps(data)
        conn.send("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n")
        conn.send(response)
        conn.close()
        return

    if "GET /aht10_temperature_data" in request:
        labels = list(range(60))
        labels.reverse()
        data = {"labels": labels, "values": aht10_temperature_monitor.get_data()}
        response = json.dumps(data)
        conn.send("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n")
        conn.send(response)
        conn.close()
        return

    if "GET /aht10_humidity_data" in request:
        labels = list(range(60))
        labels.reverse()
        data = {"labels": labels, "values": aht10_humidity_monitor.get_data()}
        response = json.dumps(data)
        conn.send("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n")
        conn.send(response)
        conn.close()
        return

    uuid, given_name = load_config()
    styles = """
        body {{ font-family: Arial, sans-serif; text-align: center; }}
        .switch {
          position: relative;
          display: inline-block;
          width: 60px;
          height: 34px;
        }

        /* Hide default HTML checkbox */
        .switch input {
          opacity: 0;
          width: 0;
          height: 0;
        }

        /* The slider */
        .slider {
          position: absolute;
          cursor: pointer;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background-color: #ccc;
          -webkit-transition: .4s;
          transition: .4s;
        }

        .slider:before {
          position: absolute;
          content: "";
          height: 26px;
          width: 26px;
          left: 4px;
          bottom: 4px;
          background-color: white;
          -webkit-transition: .4s;
          transition: .4s;
        }

        input:checked + .slider {
          background-color: #2196F3;
        }

        input:focus + .slider {
          box-shadow: 0 0 1px #2196F3;
        }

        input:checked + .slider:before {
          -webkit-transform: translateX(26px);
          -ms-transform: translateX(26px);
          transform: translateX(26px);
        }

        /* Rounded sliders */
        .slider.round {
          border-radius: 34px;
        }

        .slider.round:before {
          border-radius: 50%;
        }
        """
    response = f"""HTTP/1.1 200 OK
Content-Type: text/html

<!DOCTYPE html>
<html>
    <head>
        <title>{cloud_updater.pretty_current_version()} Plant Monitor</title>
        <style>
            {styles}
        </style>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <script src=main.js></script>
    </head>
    <body style="background-color: rgb(240, 240, 240);">
        <h1>{given_name}</h1>
        <p>Laiska-Jaakko Plant Monitor</p>
        <p>device-uuid: {uuid}</p>
        <h3>Wi-Fi Setup</h3>
        <form action="/setup_wifi" method="post">
            <label for="ssid">SSID:</label><br>
            <input type="text" id="ssid" name="ssid"><br>
            <label for="password">Password:</label><br>
            <input type="text" id="password" name="password"><br><br>
            <input type="submit" value="Submit">
        </form>
        <h3>Led Control</h3>
        <label class="switch">
            <input type="checkbox" id="toggle" {"checked" if led.value() else ""} onclick="toggleLed()">
            <span class="slider round"></span>
        </label>
        <h3>System</h3>
        <p>{cloud_updater.pretty_current_version()}</p>
        <p id=updates_available>{"Updates available" if cloud_updater.updates_available else "No updates available"}</p>
        {'<button id=update_button onclick="update_software()">Update</button>' if cloud_updater.updates_available else '<button id=update_button onclick="check_updates_available()">Check for available updates</button>'}
        <p>used storage: {storage_sensor.used_kilobytes()} / {storage_sensor.total_kilobytes()} KB</p>
        <form action="/memory" method="post">
            <button onclick="print_memory_usage()">Print memory usage</button>
        </form>
        <h1>Live Data Plot</h1>
        <canvas id="moistureChart" width="400" height="300"></canvas>
        <script src="pico-chart.js?chartName=moistureChart&chartPath=moisture_data&chartLabel=Moisture&initDelayMS=1000"></script>
        <canvas id="picoTemperatureChart" width="400" height="300"></canvas>
        <script src="pico-chart.js?chartName=picoTemperatureChart&chartPath=pico_temperature_data&chartLabel=PicoTemperature&initDelayMS=2000"></script>
        <canvas id="aht10TemperatureChart" width="400" height="300"></canvas>
        <script src="pico-chart.js?chartName=aht10TemperatureChart&chartPath=aht10_temperature_data&chartLabel=AHT10Temperature&initDelayMS=3000"></script>
        <canvas id="aht10HumidityChart" width="400" height="300"></canvas>
        <script src="pico-chart.js?chartName=aht10HumidityChart&chartPath=aht10_humidity_data&chartLabel=AHT10Humidity&initDelayMS=4000"></script>
    </body>
</html>
"""
    conn.send(response)
    conn.close()

    if ssid and password:
        ssid = ssid.replace("+", " ")
        password = password.replace("'", "")
        print("SSID:", ssid)
        print("Password:", password)
        connect_to_wifi(ssid, password)
        start_web_server()


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
            except Exception as e:
                print("while true error:", e)
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


def ensure_connectivity(timer=None):  # timed function which keeps wifi connection alive
    collect()
    global wlan, s, conn, pico_timer
    if wlan and not wlan.isconnected():
        print("connection lost, restarting..")
        ssid, password = load_wifi_config()
        if s:
            s.close()
            s = None
            sleep(10)
        connect_to_wifi(ssid, password)
        start_web_server()
    else:
        print(pico_timer.get_pretty_time(), f"wifi ok: {wlan.ifconfig()}")


def periodic_restart(timer=None):
    print("restarting in 10..")
    sleep(10)
    reset()


# Start the access point and web server
ssid, password = load_wifi_config()
print(f"ssid: {ssid}")


if ssid and password:
    connect_to_wifi(ssid, password)
else:
    start_ap()

print("connecting to cloud..")
cloud_updater = CloudUpdater()

print("starting sensors..")
# Initialize the AHT10 sensor
aht10 = AHT10(i2c)

pico_timer = CustomTimer()
moisture_sensor = MoistureSensor(0.5, 3.3)
moisture_sensor_history = SensorHistory("moisture.log", 60)
moisture_monitor = SensorMonitor(moisture_sensor, moisture_sensor_history)

pico_temperature_sensor = PicoTemperatureSensor()
pico_temperature_sensor_history = SensorHistory("pico_temperature.log", 60)
pico_temperature_monitor = SensorMonitor(
    pico_temperature_sensor, pico_temperature_sensor_history
)

aht10_temperature_sensor = AHT10TemperatureSensor(aht10)
aht10_temperature_sensor_history = SensorHistory("aht10_temperature.log", 60)
aht10_temperature_monitor = SensorMonitor(
    aht10_temperature_sensor, aht10_temperature_sensor_history
)

aht10_humidity_sensor = AHT10HumiditySensor(aht10)
aht10_humidity_sensor_history = SensorHistory("aht10_humidity.log", 60)
aht10_humidity_monitor = SensorMonitor(
    aht10_humidity_sensor, aht10_humidity_sensor_history
)

storage_sensor = StorageSensor()

print("sensors initiated")

ensure_connectivity()
wifi_check_timer = Timer()
wifi_check_timer.init(period=60000, mode=Timer.PERIODIC, callback=ensure_connectivity)

start_web_server()
