from gc import collect
from os import listdir, remove, rmdir, mkdir
import os
from machine import Timer, reset  # type: ignore
from time import sleep
import socket, ssl
from json import load
from components.status_led import StatusLed
from typing import Any, Tuple


def _is_directory(path: str) -> bool:
    try:
        stat = os.stat(path)
        # In MicroPython, a directory has the 0x4000 flag set in st_mode
        return stat[0] & 0x4000 == 0x4000
    except OSError:
        return False


def _delete_directory_recursively(directory: str) -> None:
    for file_or_dir in listdir(directory):
        full_path = directory + '/' + file_or_dir
        if _is_directory(full_path):
            _delete_directory_recursively(full_path)
        else:
            remove(full_path)
    rmdir(directory)


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

    def check_for_updates(self) -> Tuple[int, int, bool]:
        print("checking for updates..")
        self.version_config = self._load_file("version.json")
        self.current_version = int(self.version_config["version"])
        self._download_file("version.json", "remote-version.json")
        self.remote_version_config = self._load_file("remote-version.json")
        self.remote_version: int = self.remote_version_config["version"]
        self.updates_available: bool = self.remote_version > self.current_version
        return self.current_version, self.remote_version, self.updates_available

    def pretty_current_version(self) -> str:
        return f"v.{self.current_version}"

    def update(self, timer: Timer = None) -> None:
        print("updating..")
        self.version_config = self._load_file("remote-version.json")
        for file in self.version_config.get("files_excluded", []):
            try:
                remove(file)
            except:
                pass
        try:
            _delete_directory_recursively("dist")
        except:
            pass
        for directory in self.version_config["directories_included"]:
            mkdir(directory)
        for file in self.version_config["files_included"]:
            self._download_file(file, file)
        self._install_update()

    def _download_file(self, remote_file_name: str, local_file_name: str) -> None:
        collect()
        if "laiska-frontend/" in local_file_name:
            local_file_name = local_file_name.replace("laiska-frontend/", "")
        https_file_url = f"{self.base_url}{remote_file_name}?raw=True"
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
        print(f"writing to local file: {local_file_name}")
        with open(local_file_name, "wb") as file:
            file.write(body)
            while True:
                collect()
                data = s.read(1024)  # type: ignore
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
