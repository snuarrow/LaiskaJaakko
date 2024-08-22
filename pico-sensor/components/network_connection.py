from time import sleep
from machine import Timer  # type: ignore
import network  # type: ignore
import json
from typing import Optional, Tuple

def load_wifi_config() -> Tuple[Optional[str], Optional[str]]:
    try:
        with open("wifi_config.json", "r") as f:
            wifi_config = json.load(f)
            return wifi_config["ssid"], wifi_config["password"]
    except OSError as e:
        print("Error reading wifi config:", e)
        return None, None

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
