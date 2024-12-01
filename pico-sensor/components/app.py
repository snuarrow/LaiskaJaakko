from components.helpers import print_memory_usage
print_memory_usage()
from components.flasher import decide_action
from components.status_led import StatusLed
status_led = StatusLed()
decide_action(status_led=status_led)
from machine import Pin, reset, #freq  # type: ignore
from components.wifi_reset_button import WifiResetButton
from components.network_connection import NetworkConnection
from components.web_real_time_clock import WebRealTimeClock
from components.cloud_updater import CloudUpdater
from components.sensors import Sensors, save_config
from components.helpers import get_flash_sizes
from components.microdot import Microdot, Response, Request
from time import sleep
from json import dumps, load
from typing import Tuple, Optional, Union
from gc import collect


total_flash, free_flash = get_flash_sizes()
print(f"Total flash: {total_flash} KB, Free flash: {free_flash} KB")
#frequency_MHz = 125
#freq(frequency_MHz * 1000000)
CHUNK_SIZE = 1024
CONFIG_FILE = "config.json"
pico_led = Pin("LED", Pin.OUT)
pico_led.value(0)
status_led.signal_power_on()
WifiResetButton(power_pin=5, signal_pin=3, status_led=status_led, pico_led=pico_led)
network_connection = NetworkConnection()
while True:
    if network_connection.ap_active():
        from components.ap_web_server import start_ap_web_server
        status_led.ap_mode_start()
        start_ap_web_server(status_led=status_led)
    if network_connection.wlan_active():
        status_led.disco_start()
        break
    sleep(5)
rtc = WebRealTimeClock()
cloud_updater = CloudUpdater(status_led=status_led)
current_version, remote_version, updates_available = cloud_updater.check_for_updates()
sensors = Sensors(rtc=rtc)
app = Microdot()  # type: ignore

updateRunning = False
def update_gate() -> Tuple[str, int]:
    return dumps({"error": "update running"}), 423


def reset_wrapper(timer: Timer = None):
    print("reset_wrapper() called")
    reset()


@app.route("/")  # type: ignore
def index(request: Request) -> Tuple[str, int, dict[str, str]]:
    collect()
    global updateRunning
    if updateRunning:
        return update_gate()
    with open("/dist/index.html") as f:
        return f.read(), 200, {"Content-Type": "text/html"}


@app.route("/api/v1/sensor_meta", methods=["GET"])  # type: ignore
def get_meta(request: Request) -> Tuple[str, int]:
    collect()
    global updateRunning
    if updateRunning:
        return update_gate()
    with open(CONFIG_FILE, "r") as f:
        sensor_meta = load(f)["sensors"]
    return dumps(sensor_meta), 200


@app.route("/api/v1/sensor_data", methods=["GET"])  # type: ignore
def get_data(request: Request) -> Tuple[str, int]:
    collect()
    global updateRunning
    if updateRunning:
        return update_gate()
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
        if elem[1] < 1282542159:
            continue
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


@app.route("/api/v1/sensor_name", methods=["POST"])  # type: ignore
def set_meta(request: Request) -> Tuple[str, int]:
    collect()
    global updateRunning
    if updateRunning:
        return update_gate()
    # changes the sensor given name based on query param sensor_index and json payload "given_name": "new_name"
    sensor_index = int(request.args.get("sensor_index", 0))
    data = request.json
    given_name = data.get("newName")
    with open(CONFIG_FILE, "r") as f:
        config = load(f)
        config["sensors"][sensor_index]["name"] = given_name
    save_config(updated_config=config)
    sensor_monitor = sensors.get_sensor(index=sensor_index)
    sensor_monitor.sensor.name = given_name  # type: ignore
    return dumps({"name": given_name}), 200



@app.route("/api/v1/led", methods=["GET"])  # type: ignore
def get_led(request: Request) -> Tuple[str, int]:
    collect()
    global updateRunning
    if updateRunning:
        return update_gate()
    return dumps({"value": int(status_led.lit)}), 200


@app.route("/api/v1/led", methods=["POST"])  # type: ignore
def set_led(request: Request) -> Tuple[str, int]:
    collect()
    global updateRunning
    if updateRunning:
        return update_gate()
    data = request.json
    value = data.get("value")
    if value == 0:
        status_led.disco_stop()
    elif value == 1:
        status_led.disco_start()
    return dumps({"led": status_led.lit}), 200


@app.route("/api/v1/updates_available", methods=["GET"])  # type: ignore
def get_updates_availalbe(request: Request) -> Tuple[str, int]:
    collect()
    print_memory_usage()
    current_version, remote_version, updates_available = cloud_updater.check_for_updates()
    return dumps({
        "currentVersion": current_version,
        "remoteVersion": remote_version,
        "updatesAvailable": updates_available,
    }), 200


@app.route("/api/v1/test", methods=["GET"])  # type: ignore
def get_test(request: Request):    
    return dumps({
        "test": "2"
    }), 200


@app.route("/api/v1/reset", methods=["POST"])
def post_reset(request: Request):
    from machine import Timer
    collect()
    Timer().init(mode=Timer.ONE_SHOT, period=1000, callback=reset_wrapper)
    return dumps({
        "status": "resetting"
    }), 200


@app.route("/api/v1/download_firmware", methods=["POST"])  # type: ignore
def post_update_firmware(request: Request) -> Tuple[str, int]:
    collect()
    force_update = request.args.get("force", 0)
    _, _, updates_available = cloud_updater.check_for_updates()
    global updateRunning
    if updates_available or force_update:
        updateRunning = True
        cloud_updater.download_update()
        updateRunning = False
        err = cloud_updater.get_download_status()
        return_elem = {"ready": True}
        if err:
            return_elem["error"] = err
            return_elem["ready"] = False
        return dumps(return_elem), 200
    return dumps({"error": "no updates available"}), 400


@app.route("/<path:path>")  # type: ignore
def static(request: Request, path: str) -> Optional[Union[Tuple[str, int], Response]]:
    collect()
    global updateRunning
    if updateRunning:
        return update_gate()
    if "api/v1" in request.url:
        return None
    accept_encoding = request.headers.get("Accept-Encoding", "")
    path = f"/dist/{path}"
    if path.endswith(".js"):
        if "gzip" in accept_encoding:
            return serve_file(f"{path}.gz", "application/javascript", "gzip")
        else:
            return dumps({"error": "gzip not supported on browser"}), 400
    elif path.endswith(".css"):
        return serve_file(f"{path}.gz", "text/css", "gzip")
    elif path.endswith(".html"):
        return serve_file(path, "text/html")
    elif path.endswith(".ico"):
        return serve_file(path, 'image/x-icon')
    return serve_file(path, "application/octet-stream")


def serve_file(file_path: str, content_type: str, encoding: str = "") -> Response:
    def file_stream():  # type: ignore
        try:
            with open(file_path, "rb") as f:
                while True:
                    chunk = f.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    yield chunk
        except OSError as e:
            print(f"File not found: {file_path}")
            raise e

    headers = {"Content-Type": content_type}
    if encoding:
        headers["Content-Encoding"] = encoding
    return Response(body=file_stream(), headers=headers)  # type: ignore

collect()
print("all set")
print_memory_usage()
try:
    app.run(host="0.0.0.0", port=80)  # type: ignore
except Exception as e:
    print("Exception in app.run", e)
    raise e
