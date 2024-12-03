from gc import collect
from os import listdir, remove, rmdir, mkdir
import os
from machine import Timer, reset  # type: ignore
from time import sleep
import socket, ssl
from json import load, dump
from components.helpers import file_exists
from components.status_led import StatusLed
from typing import Any, Tuple
from immutable.checksum import calculate_checksum
from components.flasher import (
    validate_new_version,
    delete_directory_recursively,
    NEW_VERSION_DIR,
)

BRANCH: str = "update-button"
BASE_URL: str = f"https://raw.githubusercontent.com/snuarrow/LaiskaJaakko/{BRANCH}/pico-sensor/"


def _load_file(filename: str) -> Any:
    with open(filename, "r") as f:
        version_config = load(f)
        return version_config


def _download_files(files_missing: list[str]) -> None:
    remote_version_config = _load_file("remote-version.json")
    try:
        delete_directory_recursively("old_version")
    except:
        pass
    try:
        mkdir(NEW_VERSION_DIR)
    except:
        pass
    for directory in remote_version_config["directories_included"]:
        new_directory = f"{NEW_VERSION_DIR}/{directory}"
        try:
            mkdir(new_directory)
        except:
            pass
    for elem in files_missing:
        for i in range(5):
            try:
                remote_file_name: str = str(elem["repository"])  # type: ignore
                relative_local_file_name: str = str(elem["pico"])  # type: ignore
                _download_file(
                    remote_file_name=remote_file_name,
                    local_file_name=NEW_VERSION_DIR + "/" + relative_local_file_name,
                )
                break
            except Exception as e:
                if i == 4:
                    raise (e)
                sleep(3)
                pass
    collect()


def _download_file(remote_file_name: str, local_file_name: str) -> None:
    collect()
    #try:
    #    remove(local_file_name)
    #except:
    #    pass
    https_file_url = f"{BASE_URL}{remote_file_name}?raw=True"
    _, _, host, path = https_file_url.split("/", 3)
    print(f"<- {https_file_url} as {local_file_name}")
    path = "/" + path
    addr = socket.getaddrinfo(host, 443)[0][-1]
    http_socket = socket.socket()
    http_socket.connect(addr)
    collect()
    ssl_socket = ssl.wrap_socket(http_socket, server_hostname=host)  # type: ignore
    request = "GET {} HTTP/1.1\r\nHost: {}\r\nConnection: close\r\n\r\n".format(
        path, host
    )
    ssl_socket.write(request.encode("utf-8"))
    response = b""
    while b"\r\n\r\n" not in response:
        response += ssl_socket.read(1)
    header, body = response.split(b"\r\n\r\n", 1)
    with open(local_file_name, "wb") as file:
        file.write(body)
        collect()
        while True:
            for i in range(10):  # retry 10 mem alloc times
                try:
                    data = ssl_socket.read(4096)
                    break
                except Exception as e:
                    if i == 9:
                        ssl_socket.close()
                        http_socket.close()
                        del ssl_socket
                        del http_socket
                        collect()
                    pass
            if not data:
                break
            file.write(data)
    ssl_socket.close()
    http_socket.close()
    del ssl_socket
    del http_socket
    collect()


def validate_files(remote_config_files: list[str]) -> list[str]:
    invalid_files = []
    folder = f"{NEW_VERSION_DIR}/"
    for elem in remote_config_files:

        filename = folder + elem["pico"]  # type: ignore
        if not file_exists(filename):
            invalid_files.append(elem)
            continue
        expected_checksum = elem["check"]  # type: ignore
        actual_checksum = calculate_checksum(filename)

        if expected_checksum != actual_checksum:
            invalid_files.append(elem)
            continue

    return invalid_files


def check_for_updates() -> Tuple[int, int, bool]:
    print("checking for updates..")
    version_config = _load_file("version.json")
    current_version = int(version_config["version"])
    _download_file("version.json", "remote-version.json")
    remote_version_config = _load_file("remote-version.json")
    remote_version: int = remote_version_config["version"]
    updates_available: bool = remote_version > current_version
    return current_version, remote_version, updates_available


def download_update() -> None:
    remote_version_config = _load_file("remote-version.json")
    files_missing = validate_files(remote_version_config["files_included"])
    _download_files(files_missing)


def get_download_status() -> str | None:
    err = validate_new_version()
    if err:
        return err
    with open("update.json", "w") as f:
        dump(
            {
                "ok": True,
                "rollback": False,
            },
            f,
        )
    return None
