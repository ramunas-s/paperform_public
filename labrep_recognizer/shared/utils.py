import hashlib
from pathlib import Path
from dotenv import find_dotenv, load_dotenv
import datetime


def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


def make_dirs(file_path: str) -> str:
    fpt = Path(file_path)
    if not fpt.exists():
        parent_pt = fpt.parent
        parent_pt.mkdir(parents=True, exist_ok=True)
    return file_path


def find_all_strings(p, s):
    i = s.find(p)
    while i != -1:
        yield i
        i = s.find(p, i + 1)


def load_environment():
    load_dotenv()
    # load_dotenv(find_dotenv(filename=".env.local"))


def split_cell(s, separator):
    found_at = s.find(separator)
    if found_at == -1:
        return s, ""
    else:
        part_1 = s[0:found_at]
        part_2 = s[found_at + len(separator) :]
        return part_1.rstrip(), part_2.lstrip()


def is_valid_iso_date_time_str(time_str):
    try:
        _ = datetime.datetime.fromisoformat(time_str)
        return True
    except ValueError:
        return False


def file_to_sha256(file_name):
    buf_size = 65536
    sha256 = hashlib.sha256()
    with open(file_name, "rb") as f:
        while True:
            data = f.read(buf_size)
            if not data:
                break
            sha256.update(data)
    return sha256.hexdigest()
