import socket
from components.typing import Any
import ure  # type: ignore
from json import dumps, dump
from machine import reset  # type: ignore
from gc import collect
from components.status_led import StatusLed

WIFI_CONFIG_FILE = "wifi_config.json"
s = None
conn = None

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

def save_wifi_config(ssid: str, password: str) -> None:
    wifi_config = {"ssid": ssid, "password": password}
    with open(WIFI_CONFIG_FILE, "w") as f:
        dump(wifi_config, f)

def handle_request_ap_mode(conn: Any, status_led: StatusLed) -> None:
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
            conn.send(dumps({"status": "ok"}))
            status_led.signal_wifi_set()
            reset()
    stream_file("ap_index.html", conn, "text/html")
    conn.close()

def start_ap_web_server(status_led: StatusLed) -> None:
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
                print("Connection from", addr)
                handle_request_ap_mode(conn, status_led)
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