from json import load #, dump
#from os import mkdir, rename
#from machine import reset
from gc import collect
#from os import stat, listdir, remove, rmdir

"""
def _is_directory(path: str) -> bool:
    try:
        stat = stat(path)
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


def flash_rollback():
    print("rollback not implemented yet")


def flash_new_firmware():
    with open("version.json") as f:
        old_version_config = load(f)
    with open("remote-version.json", "r") as f:
        new_version_config = load(f)

    old_version_dir = "old_version"
    new_version_dir = "new_version"

    try:
        mkdir(old_version_dir)
    except:
        pass

    for directory in old_version_config["directories_included"]:
        if "laiska-frontend" in directory:
            directory = directory.replace("laiska-frontend/", "")
        try:
            mkdir(old_version_dir + "/" + directory)
        except:
            pass
    
    for elem in old_version_config["files_included"]:
        filename = elem[0]
        if "laiska-frontend" in filename:
            filename = filename.replace("laiska-frontend/", "")
        print(f"moving old file: {filename}")
        rename(filename, old_version_dir + "/" + filename)
    
    for directory in new_version_config["directories_included"]:
        try:
            if "laiska-frontend" in filename:
                directory = directory.replace("laiska-frontend/", "")
            mkdir(directory)
        except:
            pass
    
    for elem in new_version_config["files_included"]:
        filename = elem[0]
        print(f"moving new file: {filename}")
        rename(new_version_dir + "/" + filename, filename.replace("laiska-frontend/", ""))
    
    rename("version.json", "old-version.json")
    rename("remote-version.json", "version.json")

    with open("update.json", "w") as f:
        dump({
            "ok": False,
            "rollback": False,
        }, f)
    


    reset()
"""
    

    

def decide_action() -> None:
    update_ready = False
    with open("update.json", "r") as f:
        update_status = load(f)
        rollback = update_status.get("rollback", True)
        update_ready = update_status.get("ok", False)

    if rollback:
        pass
        #flash_rollback()

    if update_ready:
        pass
        #flash_new_firmware()

    collect()