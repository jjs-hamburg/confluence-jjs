# -*- coding: utf-8 -*-
from __future__ import absolute_import

import json

import xbmc
import xbmcgui

HOME_ID = 10000
PREFIX = "ConfluenceCustom.SongSelector."
SELECTED_PROP = PREFIX + "Selected"
START_PROP = PREFIX + "PopupStart"
POPUP_OPEN_PROP = PREFIX + "PopupOpen"
SLOT_COUNT = 13
MID_SLOT = SLOT_COUNT // 2
SLOT_PROPS = tuple(PREFIX + "PopupSlot{}".format(i) for i in range(SLOT_COUNT))
SLOT_CURRENT_PROPS = tuple(PREFIX + "PopupSlot{}Current".format(i) for i in range(SLOT_COUNT))
TRACK_SETTING = "CCSongSelectorShowTrackNumbers"


def _home():
    return xbmcgui.Window(HOME_ID)


def playlist():
    return xbmc.PlayList(xbmc.PLAYLIST_MUSIC)


def size():
    try:
        return int(playlist().size())
    except Exception:
        return 0


def current():
    try:
        value = int(playlist().getposition())
    except Exception:
        value = 0
    count = size()
    if count <= 0:
        return 0
    return min(max(value, 0), count - 1)


def selected(default_current=True):
    raw = _home().getProperty(SELECTED_PROP)
    try:
        value = int(raw)
    except Exception:
        value = current() if default_current else 0
    count = size()
    if count <= 0:
        return 0
    return min(max(value, 0), count - 1)


def set_selected(index):
    count = size()
    if count <= 0:
        value = 0
    else:
        value = min(max(int(index), 0), count - 1)
    _home().setProperty(SELECTED_PROP, str(value))
    return value


def popup_start():
    raw = _home().getProperty(START_PROP)
    try:
        value = int(raw)
    except Exception:
        value = 0
    count = size()
    maximum = max(0, count - SLOT_COUNT)
    return min(max(value, 0), maximum)


def popup_open():
    return _home().getProperty(POPUP_OPEN_PROP) == "1"


def set_popup_open(opened):
    if opened:
        _home().setProperty(POPUP_OPEN_PROP, "1")
    else:
        _home().clearProperty(POPUP_OPEN_PROP)


def _show_track_numbers():
    value = xbmc.getInfoLabel("Skin.String({})".format(TRACK_SETTING)).strip().lower()
    return value in ("1", "true", "yes", "on")


def _get_items(start, end, properties=None):
    if end <= start:
        return []
    request = {
        "jsonrpc": "2.0",
        "method": "Playlist.GetItems",
        "params": {
            "playlistid": 0,
            "properties": properties or ["title", "track", "album", "duration"],
            "limits": {"start": int(start), "end": int(end)},
        },
        "id": 1,
    }
    try:
        result = json.loads(xbmc.executeJSONRPC(json.dumps(request))).get("result", {})
        return result.get("items", []) or []
    except Exception:
        return []


def playlist_metadata():
    count = size()
    if count <= 0:
        return []
    return _get_items(0, count, ["title", "track", "album", "duration"])


def _display_title(item):
    title = item.get("title") or item.get("label") or ""
    if not title:
        return ""
    if _show_track_numbers():
        try:
            track = int(item.get("track") or 0)
        except Exception:
            track = 0
        if track > 0:
            return "{}  {}".format(track, title)
    return title


def render(start=None, selected_index=None, current_index=None):
    count = size()
    home = _home()
    if count <= 0:
        for prop in SLOT_PROPS + SLOT_CURRENT_PROPS:
            home.clearProperty(prop)
        home.setProperty(SELECTED_PROP, "0")
        home.setProperty(START_PROP, "0")
        return 0

    maximum = max(0, count - SLOT_COUNT)
    if start is None:
        start = popup_start()
    start = min(max(int(start), 0), maximum)
    home.setProperty(START_PROP, str(start))

    if selected_index is not None:
        set_selected(selected_index)

    if current_index is None:
        current_index = current()
    current_index = min(max(int(current_index), 0), count - 1)

    end = min(count, start + SLOT_COUNT)
    items = _get_items(start, end, ["title", "track"])
    for slot in range(SLOT_COUNT):
        absolute = start + slot
        item = items[slot] if slot < len(items) else None
        value = _display_title(item) if item else ""
        if value:
            home.setProperty(SLOT_PROPS[slot], value)
        else:
            home.clearProperty(SLOT_PROPS[slot])
        if value and absolute == current_index:
            home.setProperty(SLOT_CURRENT_PROPS[slot], "1")
        else:
            home.clearProperty(SLOT_CURRENT_PROPS[slot])
    return start


def open_on_current():
    count = size()
    if count <= 0:
        set_popup_open(False)
        return 0
    playing = current()
    maximum = max(0, count - SLOT_COUNT)
    start = min(max(playing - MID_SLOT, 0), maximum)
    set_selected(playing)
    render(start, selected_index=playing, current_index=playing)
    set_popup_open(True)
    return playing - start


def close_popup():
    set_popup_open(False)
