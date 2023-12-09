import hashlib
import os


def sha1OfFile(filepath):
    sha = hashlib.sha1()
    with open(filepath, "rb") as f:
        while True:
            block = f.read(2**10)  # Magic number: one-megabyte blocks.
            if not block:
                break
            sha.update(block)
        return sha.hexdigest()


def hash_dir(dir_path):
    hashes = []
    for path, dirs, files in os.walk(dir_path):
        for file in sorted(
            files
        ):  # we sort to guarantee that files will always go in the same order
            hashes.append(sha1OfFile(os.path.join(path, file)))
        # we sort to guarantee that dirs will always go in the same order
        for _dir in sorted(dirs):
            hashes.append(hash_dir(os.path.join(path, _dir)))
        break  # we only need one iteration - to get files and dirs in current directory
    return str(hash("".join(hashes)))
