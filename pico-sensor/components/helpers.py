from os import statvfs
from gc import mem_alloc, mem_free  #  type: ignore
from json import load
from typing import Tuple


CHUNK_SIZE = 1024
CONFIG_FILE = "config.json"


def get_flash_sizes() -> Tuple[int, int]:
    fs_stat = statvfs('/')
    total_flash = fs_stat[0] * fs_stat[2]
    free_flash = fs_stat[0] * fs_stat[3]
    total_flash_kb = total_flash / 1024
    free_flash_kb = free_flash / 1024
    return int(total_flash_kb), int(free_flash_kb)


def print_memory_usage() -> None:
    total_memory = mem_alloc() + mem_free()
    used_memory = mem_alloc()
    print(f"Memory usage: {used_memory / 1000} / {total_memory / 1000}")


def file_exists(filename: str) -> bool:
    try:
        open(filename, "r")
        return True
    except OSError:
        return False

def load_json(filename: str) -> Tuple[Any, str | None]:
    if ".json" not in filename:
        return None, f"file {filename} is not .json"
    if not file_exists(filename=filename):
        return None, f"file {filename} does not exist"
    try:
        with open(filename, "r") as f:
            version_config = load(f)
            return version_config, None
    except Exception as e:
        return None, f"error reading json file: {filename}, exception: {str(e)}"
