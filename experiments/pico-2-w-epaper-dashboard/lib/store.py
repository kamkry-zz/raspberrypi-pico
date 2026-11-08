"""Power-loss-safe JSON persistence on the board's LittleFS.

Writes go to ``<path>.tmp`` first and are then renamed over the target.
LittleFS commits a rename atomically, so a power cut leaves either the old
or the new file, never a half-written one.  Any unreadable or corrupt file
is treated as missing (and removed) so it can never block a boot.
"""

import json
import os


def save(path, value):
    tmp = path + ".tmp"
    try:
        with open(tmp, "w") as handle:
            json.dump(value, handle)
        try:
            os.rename(tmp, path)  # LittleFS replaces the target atomically
        except OSError:
            # FAT-style filesystems refuse to rename over a file.
            try:
                os.remove(path)
            except OSError:
                pass
            os.rename(tmp, path)
        return True
    except Exception as exc:
        print("store.save %s: %r" % (path, exc))
        try:
            os.remove(tmp)
        except OSError:
            pass
        return False


def load(path, default=None):
    try:
        with open(path) as handle:
            return json.load(handle)
    except OSError:
        pass
    except Exception as exc:  # ValueError from a corrupt/truncated file
        print("store.load %s corrupt: %r; removing" % (path, exc))
        try:
            os.remove(path)
        except OSError:
            pass
        return default
    # Recover from a power cut between remove() and rename() in save().
    try:
        with open(path + ".tmp") as handle:
            value = json.load(handle)
        os.rename(path + ".tmp", path)
        return value
    except Exception:
        return default
