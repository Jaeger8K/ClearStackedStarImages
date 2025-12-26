import sys
import string
from pathlib import Path


def get_storage_roots():
    """
    Yield filesystem roots depending on OS.
    """
    if sys.platform.startswith("win"):
        for letter in string.ascii_uppercase:
            drive = Path(f"{letter}:/")
            if drive.exists():
                yield drive
    else:
        yield Path("/")
        for mount in ("/Volumes", "/mnt", "/media"):
            p = Path(mount)
            if p.exists():
                yield from (x for x in p.iterdir() if x.is_dir())
