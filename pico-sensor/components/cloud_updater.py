from gc import collect
from machine import Timer, reset  # type: ignore
from time import sleep
import socket, ssl
from json import load
from components.status_led import StatusLed
from components.typing import Any

class CloudUpdater:

    branch: str = "production"
    base_url: str = (
        f"https://raw.githubusercontent.com/snuarrow/LaiskaJaakko/{branch}/pico-sensor/"
    )
    current_version: int = 0
    updates_available: bool = False

    def __init__(self, status_led: StatusLed) -> None:
        self.status_led = status_led
        pass

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
        sleep(3)
        self.version_config = self._load_file("remote-version.json")
        for file in self.version_config["files_included"]:
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

    def _install_update(self) -> None:
        print("installing update..")
        sleep(1)
        self.status_led.signal_cloud_update()
        reset()

    def _load_file(self, filename: str) -> Any:
        with open(filename, "r") as f:
            version_config = load(f)
            return version_config
