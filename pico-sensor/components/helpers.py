import os


def get_flash_sizes():
    fs_stat = os.statvfs('/')
    total_flash = fs_stat[0] * fs_stat[2]
    free_flash = fs_stat[0] * fs_stat[3]
    total_flash_kb = total_flash / 1024
    free_flash_kb = free_flash / 1024
    return total_flash_kb, free_flash_kb
