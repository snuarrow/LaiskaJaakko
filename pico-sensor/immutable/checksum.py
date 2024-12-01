import hashlib


# Function to convert binary digest to a hexadecimal string manually
def to_hex(byte_array: bytes) -> str:
    return "".join("{:02x}".format(b) for b in byte_array)


# Define a function to calculate the checksum of a file
def calculate_checksum(file_path: str, chunk_size: int = 1024) -> str | None:
    # Create a SHA-256 hash object
    sha256 = hashlib.sha256()

    # Open the file in binary mode
    try:
        with open(file_path, "rb") as file:
            while True:
                # Read a chunk of the file
                chunk = file.read(chunk_size)
                if not chunk:
                    break
                # Update the hash with the chunk
                sha256.update(chunk)

        # Return the final hexadecimal digest (manually convert binary digest to hex)
        return to_hex(sha256.digest())

    except OSError as e:
        print(f"Error opening/reading file: {e}")
        return None
