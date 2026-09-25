# -*- coding: utf-8 -*-
from __future__ import absolute_import

import hashlib
import json
import os

import xbmc
import xbmcgui
import xbmcvfs

HOME_ID = 10000
RUNNING_PROP = "ConfluenceCustom.ArtistCache.ServiceRunning"
SOURCE_ROOT = "special://musicartistsinfo/"
CACHE_ROOT = "special://profile/addon_data/skin.confluence.custom/artist_cache/"
STATE_FILE = "special://profile/addon_data/skin.confluence.custom/artist_cache_state.json"
CHECK_INTERVAL_SECONDS = 1800
IMAGE_NAMES = ("folder.jpg", "folder.jpeg", "thumb.jpg", "thumb.jpeg", "artist.jpg", "artist.jpeg")


def _log(message, level=xbmc.LOGINFO):
    xbmc.log("[ConfluenceCustom ArtistCache] " + str(message), level)


def _json_rpc(method, params=None):
    request = {"jsonrpc": "2.0", "id": 1, "method": method}
    if params is not None:
        request["params"] = params
    try:
        response = json.loads(xbmc.executeJSONRPC(json.dumps(request)))
        if "error" in response:
            _log("{} failed: {}".format(method, response["error"]), xbmc.LOGWARNING)
            return {}
        return response.get("result") or {}
    except Exception as exc:
        _log("{} failed: {}".format(method, exc), xbmc.LOGWARNING)
        return {}


def _artists_by_name():
    result = _json_rpc(
        "AudioLibrary.GetArtists",
        {
            "albumartistsonly": False,
            "allroles": True,
            "properties": [],
            "limits": {"start": 0, "end": 100000},
        },
    )
    mapping = {}
    for artist in result.get("artists", []):
        label = (artist.get("artist") or artist.get("label") or "").strip()
        artist_id = artist.get("artistid")
        if label and artist_id is not None:
            mapping.setdefault(label.casefold(), []).append(str(artist_id))
    return mapping


def _stat_signature(path):
    try:
        stat = xbmcvfs.Stat(path)
        return "{}:{}".format(int(stat.st_size()), int(stat.st_mtime()))
    except Exception:
        return ""


def _join(base, name):
    return base.rstrip("/\\") + "/" + name


def _walk_artist_images(root):
    found = {}
    stack = [root]
    while stack:
        directory = stack.pop()
        try:
            dirs, files = xbmcvfs.listdir(directory)
        except Exception as exc:
            _log("Cannot read {}: {}".format(directory, exc), xbmc.LOGWARNING)
            continue
        lower_files = {name.casefold(): name for name in files}
        selected = ""
        for candidate in IMAGE_NAMES:
            if candidate in lower_files:
                selected = lower_files[candidate]
                break
        if selected:
            artist_name = directory.rstrip("/\\").rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
            path = _join(directory, selected)
            signature = _stat_signature(path)
            if artist_name and signature:
                found[artist_name.casefold()] = {
                    "artist": artist_name,
                    "path": path,
                    "signature": signature,
                }
        for child in dirs:
            stack.append(_join(directory, child))
    return found


def _aggregate_hash(entries):
    digest = hashlib.sha256()
    for key in sorted(entries):
        item = entries[key]
        digest.update(key.encode("utf-8", "surrogatepass"))
        digest.update(b"\0")
        digest.update(item["signature"].encode("ascii", "ignore"))
        digest.update(b"\n")
    return digest.hexdigest()


def _load_state():
    try:
        handle = xbmcvfs.File(STATE_FILE)
        raw = handle.read()
        handle.close()
        return json.loads(raw) if raw else {}
    except Exception:
        return {}


def _save_state(state):
    try:
        handle = xbmcvfs.File(STATE_FILE, "w")
        handle.write(json.dumps(state, ensure_ascii=False, sort_keys=True))
        handle.close()
    except Exception as exc:
        _log("Cannot save state: {}".format(exc), xbmc.LOGWARNING)


def _ensure_cache_dir():
    if not xbmcvfs.exists(CACHE_ROOT):
        xbmcvfs.mkdirs(CACHE_ROOT)


def _copy_artist_image(source, artist_id):
    destination = _join(CACHE_ROOT, "{}.jpg".format(artist_id))
    tmp = destination + ".tmp"
    try:
        if xbmcvfs.exists(tmp):
            xbmcvfs.delete(tmp)
        if not xbmcvfs.copy(source, tmp):
            return False
        if xbmcvfs.exists(destination):
            xbmcvfs.delete(destination)
        if not xbmcvfs.rename(tmp, destination):
            xbmcvfs.delete(tmp)
            return False
        return True
    except Exception as exc:
        _log("Copy failed {} -> {}: {}".format(source, destination, exc), xbmc.LOGWARNING)
        try:
            if xbmcvfs.exists(tmp):
                xbmcvfs.delete(tmp)
        except Exception:
            pass
        return False


def _sync(force=False):
    root = SOURCE_ROOT
    try:
        translated = xbmcvfs.translatePath(root)
        if not translated:
            return
    except Exception:
        pass

    entries = _walk_artist_images(root)
    aggregate = _aggregate_hash(entries)
    old = _load_state()
    old_hash = old.get("aggregate", "")
    old_entries = old.get("entries", {})

    if not force and aggregate == old_hash:
        return

    artist_map = _artists_by_name()
    _ensure_cache_dir()
    copied = 0
    changed = 0

    for key, item in entries.items():
        old_item = old_entries.get(key, {})
        if force or item["signature"] != old_item.get("signature"):
            changed += 1
            for artist_id in artist_map.get(key, []):
                if _copy_artist_image(item["path"], artist_id):
                    copied += 1

    # Remove local display-cache files only for artists whose master image was deleted.
    removed_keys = set(old_entries) - set(entries)
    for key in removed_keys:
        for artist_id in artist_map.get(key, []):
            destination = _join(CACHE_ROOT, "{}.jpg".format(artist_id))
            if xbmcvfs.exists(destination):
                try:
                    xbmcvfs.delete(destination)
                except Exception:
                    pass

    state_entries = {
        key: {"signature": value["signature"], "artist": value["artist"]}
        for key, value in entries.items()
    }
    _save_state({"aggregate": aggregate, "entries": state_entries})
    _log("scan complete: {} artist images, {} changed, {} local copies updated".format(
        len(entries), changed, copied
    ))


class ArtistCacheMonitor(xbmc.Monitor):
    def __init__(self):
        super(ArtistCacheMonitor, self).__init__()
        self.scan_requested = True

    def onNotification(self, sender, method, data):
        if method == "AudioLibrary.OnScanFinished":
            self.scan_requested = True


if __name__ == "__main__":
    home = xbmcgui.Window(HOME_ID)
    if home.getProperty(RUNNING_PROP) == "1":
        raise SystemExit
    home.setProperty(RUNNING_PROP, "1")
    monitor = ArtistCacheMonitor()
    elapsed = CHECK_INTERVAL_SECONDS
    try:
        while not monitor.abortRequested():
            if monitor.scan_requested or elapsed >= CHECK_INTERVAL_SECONDS:
                monitor.scan_requested = False
                elapsed = 0
                try:
                    _sync()
                except Exception as exc:
                    _log("sync failed: {}".format(exc), xbmc.LOGERROR)
            if monitor.waitForAbort(1.0):
                break
            elapsed += 1
    finally:
        home.clearProperty(RUNNING_PROP)
