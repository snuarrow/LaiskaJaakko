from os import statvfs
from gc import collect, mem_alloc, mem_free  #  type: ignore
from typing import Tuple


def get_flash_sizes() -> Tuple[int, int]:
    fs_stat = statvfs('/')
    total_flash = fs_stat[0] * fs_stat[2]
    free_flash = fs_stat[0] * fs_stat[3]
    total_flash_kb = total_flash / 1024
    free_flash_kb = free_flash / 1024
    return int(total_flash_kb), int(free_flash_kb)


def print_memory_usage() -> None:
    collect()
    total_memory = mem_alloc() + mem_free()
    used_memory = mem_alloc()
    print(f"Memory usage: {used_memory / 1000} / {total_memory / 1000}")
