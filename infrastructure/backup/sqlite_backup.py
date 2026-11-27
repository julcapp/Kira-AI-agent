#!/usr/bin/env python3
"""Create a consistent local SQLite backup; verify integrity before publishing."""
import datetime
import fcntl
import os
from pathlib import Path
import sqlite3
import tempfile

source = Path("/opt/kiryusha/data/kiryusha.db")
target = Path("/var/backups/kiryusha")
os.umask(0o077)
target.mkdir(mode=0o700, parents=True, exist_ok=True)
with (target / ".backup.lock").open("a") as lock:
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    fd, temp = tempfile.mkstemp(prefix=".backup-", dir=target)
    os.close(fd)
    try:
        with sqlite3.connect(source.as_uri() + "?mode=ro", uri=True, timeout=15) as src:
            with sqlite3.connect(temp, timeout=15) as dst:
                src.backup(dst)
                if dst.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
                    raise RuntimeError("Backup integrity check failed")
        with open(temp, "rb") as handle:
            os.fsync(handle.fileno())
        final = target / ("hourly-" + stamp + ".db")
        os.replace(temp, final)
        dirfd = os.open(target, os.O_DIRECTORY)
        try:
            os.fsync(dirfd)
        finally:
            os.close(dirfd)
        print(f"Verified backup: {final.name} ({final.stat().st_size} bytes)")
        # Preserve older/manual backups. Retention will be enabled only after off-host restore is verified.
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
