from json import load, dumps, dump
from os import mkdir, rename
from machine import reset
from gc import collect
from os import stat, listdir, remove, rmdir
from immutable.checksum import calculate_checksum
from time import sleep


backup_version_dir = "backup_version"
new_version_dir = "new_version"

def _is_directory(path: str) -> bool:
    try:
        stat_result = stat(path)
        # In MicroPython, a directory has the 0x4000 flag set in st_mode
        return stat_result[0] & 0x4000 == 0x4000
    except OSError:
        return False

def copy_file(src, dest) -> str | None:
    try:
        # Open the source file in read mode
        with open(src, 'rb') as source_file:
            # Open the destination file in write mode
            with open(dest, 'wb') as dest_file:
                # Read and write in chunks to avoid memory issues
                while True:
                    chunk = source_file.read(1024)  # Adjust chunk size if necessary
                    if not chunk:
                        break
                    dest_file.write(chunk)
    except:
        return f"Failed to copy: {src} to {dst}"


def _delete_directory_recursively(directory: str) -> str | None:
    if not _is_directory(path=directory):
        return None
    try:
        for file_or_dir in listdir(directory):
            full_path = directory + '/' + file_or_dir
            if _is_directory(full_path):
                _delete_directory_recursively(full_path)
            else:
                remove(full_path)
        rmdir(directory)
        return None
    except:
        return f"Failed to delete directory recursively: {directory}"


def validate_new_version() -> str | None:
    with open("remote-version.json", "r") as f:
        new_version_config = load(f)
    for file_included in new_version_config["files_included"]:
        calculated_checksum = calculate_checksum(file_path=new_version_dir + "/"+ file_included["pico"])
        if calculated_checksum != file_included["check"]:
            return f"Error: Checksum mismatch in new file: {file_included['pico']}"

    return None


def delete_backup_version() -> str | None:
    err = _delete_directory_recursively(directory=backup_version_dir)
    if err:
        return err

    return None


def move_files(files: list, origin_dir: str = "", dest_dir: str = "") -> str | None:
    try:
        for relative_path in files:
            absolute_origin_path = origin_dir + "/" + relative_path
            if dest_dir:
                absolute_dest_path = dest_dir + "/" + relative_path
            else:
                absolute_dest_path = relative_path
            try:
                print(f"trying to remove: {absolute_dest_path}")
                remove(absolute_dest_path)
            except Exception as e:
                pass
            print(f"moving: {absolute_origin_path} to {absolute_dest_path}")
            try:
                rename(absolute_origin_path, absolute_dest_path)
            except:
                pass
    except Exception as e:
        raise e
        return f"Failed to move files from {origin_dir} to {dest_dir}"

    return None

def make_new_backup_version() -> str | None:
    err = delete_backup_version()
    if err:
        return err

    with open("version.json") as f:
        current_version_config = load(f)
    dirs = current_version_config["directories_included"]
    err = create_directories(directories=dirs, subfolder=backup_version_dir)
    if err:
        return err

    current_version_files = [e["pico"] for e in current_version_config["files_included"]]
    err = move_files(files=current_version_files, dest_dir=backup_version_dir)
    if err:
        return err

    copy_file("version.json", backup_version_dir + "/version.json")

    return None


def install_new_version() -> str | None:
    with open("remote-version.json") as f:
        new_version_config = load(f)

    new_files = [e["pico"] for e in new_version_config["files_included"]]
    err = move_files(files=new_files, origin_dir=new_version_dir, dest_dir="")
    if err:
        return err

def create_directories(directories: list, subfolder: str = None) -> str:
    try:
        mkdir(subfolder)
    except:
        pass
    for directory in directories:
        if subfolder:
            new_absolute_dir = subfolder + "/" + directory
        else:
            new_absolute_dir = directory

        try:
            mkdir(new_absolute_dir)
        except:
            return f"Failed to create directory: {new_absolute_dir}"


def write_update_status(ok: bool, rollback: bool):
    try:
        with open("update.json", "w") as f:
            dump({
                "ok": False,
                "rollback": False,
            }, f)
    except:
        return f"Failed to write update status: ok:{ok}, rollback:{rollback}"


def flash_rollback():
    print("rollback not implemented yet")


def flash_new_firmware() -> str | None:
    #err = validate_new_version()
    #if err:
    #    return err
    #print("new version validated")
    
    err = delete_backup_version()
    if err:
        return err
    print("old backup deleted")
    err = make_new_backup_version()
    if err:
        return err
    print("new backup created")
    
    err = write_update_status(ok=False, rollback=True)
    if err:
        return err
    print("changed to rollback state in case of fail")

    err = install_new_version()
    if err:
        return err
    print("installed new version successfully")

    rename("remote-version.json", "version.json")
    print("version.json overwritten")

    err = write_update_status(ok=False, rollback=False)
    if err:
        return err
    print("update status set to false false")

    err = _delete_directory_recursively(new_version_dir)
    if err:
        return err
    print("new version download directory deleted")
    sleep(10)
    #reset()
    

def decide_action(status_led) -> None:
    update_ready = False
    try:
        with open("update.json", "r") as f:
            update_status = load(f)
            rollback = update_status.get("rollback", True)
            update_ready = update_status.get("ok", False)
    except (OSError, ValueError):
        collect()
        return

    if rollback:
        print(f"ERROR: rollback not implemented yet")
        pass
        #flash_rollback()

    if update_ready:
        status_led.signal_cloud_update()
        err = flash_new_firmware()
        status_led.signal_wifi_set()
        reset()
        # reset should have been excecuted at this point if all ok

        print(f"Flash new firmware Error: {err}")

    collect()