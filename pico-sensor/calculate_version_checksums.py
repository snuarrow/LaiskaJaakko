from immutable.checksum import calculate_checksum
from json import load, dump


with open("version.json") as f:
    version_config = load(f)

checksummed_files_included = []

for elem in version_config["files_included"]:
    filename = elem["repository"]
    checksum = calculate_checksum(filename)
    if not checksum:
        raise Exception(f"ERROR: {filename}, probably missing")

    checksummed_files_included.append(
        {
            "repository": elem["repository"],
            "pico": elem["pico"],
            "check": checksum,
        }
    )

version_config["files_included"] = checksummed_files_included

with open("version.json", "w") as f:
    dump(version_config, f, indent=4)

print("Success: re-calculated checksums")
