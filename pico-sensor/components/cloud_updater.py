from gc import collect
from os import listdir, remove, rmdir, mkdir
import os
from machine import Timer, reset  # type: ignore
from time import sleep
import socket, ssl
from json import load
from components.helpers import print_memory_usage
from components.status_led import StatusLed
from typing import Any, Tuple
#import _thread
from immutable.checksum import calculate_checksum

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


def _load_file(filename: str) -> Any:
    with open(filename, "r") as f:
        version_config = load(f)
        return version_config


def _paraller_download(files_missing: list, base_url: str) -> None:
    print("downloading update..")
    remote_version_config = _load_file("remote-version.json")
    #for file in self.version_config.get("files_excluded", []):
    #    try:
    #        remove(file)
    #    except:
    #        pass
    #try:
    #    _delete_directory_recursively("dist")
    #except:
    #    pass
    #for directory in self.version_config["directories_included"]:
    #    mkdir(directory)
    #try:
    #    _delete_directory_recursively("new_version")
    #except:
    #    pass
    try:
        mkdir("new_version")
    except:
        pass
    for directory in remote_version_config["directories_included"]:
        new_directory = f"new_version/{directory}"
        print(f"creating new directory: {new_directory}")
        try:
            mkdir(new_directory)
        except:
            pass
    for elem in files_missing:
        file = elem[0]
        #collect()
        #print_memory_usage()
        for i in range(5):
            try:
                #collect()
                print(f"download_file(): {file}")
                _download_file(base_url, file, "new_version/" + file)
                break
            except Exception as e:
                if i == 4:
                    raise(e)
                print(f"download failed: {file} retrying..")
                sleep(3)
                pass
    print("download complete")
    collect()


def _download_file(base_url: str, remote_file_name: str, local_file_name: str) -> None:
        #print(f"local file: {local_file_name}")
        #if "laiska-frontend/" in local_file_name:
        #    local_file_name = local_file_name.replace("laiska-frontend/", "")
        https_file_url = f"{base_url}{remote_file_name}?raw=True"
        print(f"<- {local_file_name}")
        #sleep(1)
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
            #print(response)
            #sleep(0.1)
        _, body = response.split(b"\r\n\r\n", 1)
        #print(f"writing to local file: {local_file_name}")
        with open(local_file_name, "wb") as file:
            file.write(body)
            while True:
                collect()
                for i in range(10):  # retry 10 mem alloc times
                    try:
                        data = s.read(4096)  # type: ignore
                        break
                    except Exception as e:
                        if i == 9:
                            raise e
                        pass
                if not data:
                    break
                file.write(data)
        s.close()


def file_exists(filename) -> bool:
    try:
        open(filename, "r")
        return True
    except OSError:
        return False


def validate_files(remote_config_files) -> list[str]:
    invalid_files = []
    folder = "new_version/"
    for elem in remote_config_files:
        
        filename = folder + elem[0]
        #if not file_exists(filename):
        #    invalid_files.append(elem)
        #    continue
        expected_checksum = elem[1]
        actual_checksum = calculate_checksum(filename)

        if expected_checksum != actual_checksum:
            print(f"----------------------------------- {filename}")
            print(f"expected :{expected_checksum}")
            print(f"actual   :{actual_checksum}")
            invalid_files.append(elem)
            continue
    

    for elem in invalid_files:
        print(f"missing or corrupted: {elem}")
    
    return invalid_files


class CloudUpdater:

    branch: str = "update-button"
    base_url: str = (
        f"https://raw.githubusercontent.com/snuarrow/LaiskaJaakko/{branch}/pico-sensor/"
    )
    current_version: int = 0
    updates_available: bool = False

    def __init__(self, status_led: StatusLed) -> None:
        self.status_led = status_led
        pass

    def check_for_updates(self) -> Tuple[int, int, bool]:
        collect()
        print("checking for updates..")
        self.version_config = _load_file("version.json")
        self.current_version = int(self.version_config["version"])
        _download_file(self.base_url, "version.json", "remote-version.json")
        self.remote_version_config = _load_file("remote-version.json")
        self.remote_version: int = self.remote_version_config["version"]
        self.updates_available: bool = self.remote_version > self.current_version
        return self.current_version, self.remote_version, self.updates_available

    def pretty_current_version(self) -> str:
        return f"v.{self.current_version}"

    def download_update(self, timer: Timer = None) -> None:
        print("starting download")
        files_missing = validate_files(self.remote_version_config["files_included"])
        _paraller_download(files_missing, self.base_url)
        print("download done")
    

    def _install_update(self) -> None:
        print("installing update..")
        sleep(1)
        self.status_led.signal_cloud_update()
        
        print("resetting in 20sec ..")
        #sleep(20)
        #reset()

    
