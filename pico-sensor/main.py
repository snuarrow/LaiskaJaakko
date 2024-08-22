from machine import Pin, freq  # type: ignore
from components.status_led import StatusLed
from components.wifi_reset_button import WifiResetButton
from components.network_connection import NetworkConnection
from components.ap_web_server import start_ap_web_server
from components.web_real_time_clock import WebRealTimeClock
from components.cloud_updater import CloudUpdater
from components.sensors import Sensors
from components.helpers import get_flash_sizes
from microdot import Microdot, Response, Request  # type: ignore
from time import sleep
from json import dumps, load
from typing import Tuple, Optional

total_flash, free_flash = get_flash_sizes()
print(f"Total flash: {total_flash} KB, Free flash: {free_flash} KB")

frequency_MHz = 125
freq(frequency_MHz * 1000000)
CHUNK_SIZE = 1024
CONFIG_FILE = "config.json"

pico_led = Pin("LED", Pin.OUT)
pico_led.value(0)
status_led = StatusLed()
status_led.signal_power_on()
WifiResetButton(power_pin=5, signal_pin=3, status_led=status_led, pico_led=pico_led)
network_connection = NetworkConnection()

while True:
    if network_connection.ap_active():
        status_led.ap_mode_start()
        start_ap_web_server(status_led=status_led)

    if network_connection.wlan_active():
        status_led.disco_start()
        break

    sleep(5)

rtc = WebRealTimeClock()
print(f"time is: {rtc.get_pretty_time()}")

cloud_updater = CloudUpdater(status_led=status_led)
print(f"current version is: {cloud_updater.pretty_current_version()}")

sensors = Sensors(rtc=rtc)
print("starting app")
app = Microdot()


@app.route("/")  # type: ignore
def index(request: Request) -> Tuple[str, int, dict[str, str]]:
    print("type of request", type(request))
    with open("/dist/index.html") as f:
        return f.read(), 200, {"Content-Type": "text/html"}


@app.route("/api/v1/sensor_meta", methods=["GET"])  # type: ignore
def get_meta(request: Request) -> Tuple[str, int]:
    with open(CONFIG_FILE, "r") as f:
        sensor_meta = load(f)["sensors"]
    return dumps(sensor_meta), 200


@app.route("/api/v1/sensor_data", methods=["GET"])  # type: ignore
def get_data(request: Request) -> Tuple[str, int]:
    sensor_index = int(request.args.get("sensor_index", 0))
    sensor_monitor = sensors.get_sensor(index=sensor_index)
    try:
        name = sensor_monitor.sensor.name  # type: ignore
    except:
        name = sensor_monitor.history.sensor_type
    sensor_data = sensor_monitor.get_data()
    sensor = sensor_monitor.get_sensor()
    values = []
    times = []
    for elem in sensor_data:
        try:
            values.append(elem[0])
            times.append(elem[1])
        except:
            pass

    min, max = sensor.limits()

    response_data = {
        "index": sensor_index,
        "name": name,
        "type": sensor_monitor.history.sensor_type,
        "times": times,
        "values": values,
        "min": min,
        "max": max,
    }

    return dumps(response_data), 200


@app.route("/api/v1/led", methods=["GET"])  # type: ignore
def get_led(request: Request) -> Tuple[str, int]:
    return dumps({"value": int(status_led.lit)}), 200


@app.route("/api/v1/led", methods=["POST"])  # type: ignore
def set_led(request: Request) -> Tuple[str, int]:
    data = request.json
    value = data.get("value")
    if value == 0:
        status_led.disco_stop()
    elif value == 1:
        status_led.disco_start()
    return dumps({"led": status_led.lit}), 200


@app.route("/<path:path>")  # type: ignore
def static(request: Request, path: str) -> Optional[Response]:
    if "api/v1" in request.url:
        return None
    file_path = f"/dist/{path}"
    # Set correct MIME types for different files
    if path.endswith(".js"):
        content_type = "application/javascript"
    elif path.endswith(".css"):
        content_type = "text/css"
    elif path.endswith(".html"):
        content_type = "text/html"
    else:
        content_type = "application/octet-stream"

    return serve_file(file_path, content_type)


def serve_file(file_path: str, content_type: str) -> Response:
    def file_stream():  # type: ignore
        print(f"file_path {file_path}")
        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break
                yield chunk

    return Response(
        body=file_stream(), headers={"Content-Type": content_type}
    )  # type: ignore


print("all set")
app.run(host="0.0.0.0", port=80)
