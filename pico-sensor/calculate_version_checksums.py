from immutable.checksum import calculate_checksum
from json import load, dump


with open("version.json") as f:
    version_config = load(f)

checksummed_files_included = []

for file in version_config["files_included"]:
    filename = file[0]
    checksum = calculate_checksum(filename)
    if not checksum:
        print(f"ERROR: {filename}, probably missing")
    checksummed_files_included.append([filename, checksum])

version_config["files_included"] = checksummed_files_included

with open("version.json", "w") as f:
    dump(version_config, f, indent=4)

print("Success: re-calculated checksums")
