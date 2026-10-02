# -*- coding: utf-8 -*-
"""Small process-scoped singleton lock for long-lived skin workers."""

from __future__ import absolute_import

import os
import uuid

import xbmcvfs


_LOCK_PREFIX = "confluence-jjs-worker-"


def _safe_name(name):
    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in str(name or "worker"))


def _lock_path(name):
    return os.path.join(
        xbmcvfs.translatePath("special://temp/"),
        "{}{}.lock".format(_LOCK_PREFIX, _safe_name(name)),
    )


def _process_identity():
    """Return an identity stable for this Kodi process, including PID reuse on Linux/Android."""
    pid = os.getpid()
    try:
        # /proc/<pid>/stat field 22 is the process start time in clock ticks.
        # Split after the closing ')' because the command name itself may contain spaces.
        with open("/proc/{}/stat".format(pid), "r") as handle:
            rest = handle.read().rsplit(")", 1)[1].strip().split()
        start_ticks = rest[19]
        return "{}:{}".format(pid, start_ticks)
    except Exception:
        return str(pid)


def _read_owner(path):
    try:
        with open(path, "r") as handle:
            return (handle.read() or "").strip()
    except Exception:
        return ""


def _remove_stale(path, expected_owner):
    """Remove only the stale lock we just inspected."""
    try:
        if _read_owner(path) != expected_owner:
            return False
        os.remove(path)
        return True
    except Exception:
        return False


def worker_is_running(name):
    """Return True when this Kodi process already owns the worker lock.

    A lock left by an earlier Kodi process is removed as stale.
    """
    path = _lock_path(name)
    owner = _read_owner(path)
    if not owner:
        return False

    process_id = owner.split("|", 1)[0]
    if process_id == _process_identity():
        return True

    _remove_stale(path, owner)
    return False


class WorkerLock(object):
    def __init__(self, name):
        self.path = _lock_path(name)
        self.process_id = _process_identity()
        self.owner = "{}|{}".format(self.process_id, uuid.uuid4().hex)
        self.acquired = False

    def acquire(self):
        """Atomically acquire the worker lock.

        The exclusive create closes the check-then-start race between multiple
        Home.xml startup runs. A stale lock from an older Kodi process is
        discarded once and acquisition is retried.
        """
        for attempt in range(2):
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                try:
                    os.write(fd, self.owner.encode("utf-8"))
                finally:
                    os.close(fd)
                self.acquired = True
                return True
            except OSError:
                existing = _read_owner(self.path)
                if existing and existing.split("|", 1)[0] == self.process_id:
                    return False
                if attempt == 0 and existing and _remove_stale(self.path, existing):
                    continue
                return False
        return False

    def release(self):
        if not self.acquired:
            return
        try:
            if _read_owner(self.path) == self.owner:
                os.remove(self.path)
        except Exception:
            pass
        finally:
            self.acquired = False
