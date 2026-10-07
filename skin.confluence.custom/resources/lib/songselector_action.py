# -*- coding: utf-8 -*-
from __future__ import absolute_import

import json
import sys
import time

import xbmc
import xbmcgui

from songpopup_controller import (
    close_dialog as controller_close_dialog,
    on_unload as controller_on_unload,
    open_dialog as controller_open_dialog,
)
from songselector_state import current, size

HOME_ID = 10000
DIALOG_ID = 1116
LIST_ID = 9110
TOUCH_PROP = "ConfluenceCustom.SongSelector.Touch"
MAIN_LIST_ID = 9000
CREDITS_VIEW_PROP = "ConfluenceCustom.SongSelector.CreditsView"
LYRICS_VIEW_PROP = "ConfluenceCustom.SongSelector.LyricsView"
LYRICS_TEXT_PROP = "ConfluenceCustom.SongSelector.LyricsText"
CULRC_STATUS_PROP = "culrc.jjsstatus"
CULRC_RUNNING_PROP = "culrc.running"
CULRC_ISLRC_PROP = "culrc.islrc"
LYRICS_SYNC_PROP = "ConfluenceCustom.SongSelector.LyricsSync"
CREDITS_NAV_ID = 9123
CREDITS_VISIBLE_ROWS = 13
CREDITS_SOURCE_COUNT_PROP = "ConfluenceCustom.Credits.LineCount"
CREDITS_DISPLAY_COUNT_PROP = "ConfluenceCustom.SongSelector.CreditsLineCount"
CREDITS_WINDOW_START_PROP = "ConfluenceCustom.SongSelector.CreditsWindowStart"
LYRICS_NAV_ID = 9143
LYRICS_VISIBLE_ROWS = 11
LYRICS_WINDOW_START_PROP = "ConfluenceCustom.SongSelector.LyricsWindowStart"
LYRICS_MANUAL_START_PROP = "ConfluenceCustom.SongSelector.LyricsManualStart"
LYRICS_LINE_COUNT_PROP = "ConfluenceCustom.SongSelector.LyricsLineCount"
SELECTION_TARGET_PROP = "ConfluenceCustom.SongSelector.SelectionTarget"
HIGHLIGHT_PROP = "ConfluenceCustom.SongSelector.Highlight"
PROGRAMMATIC_UNTIL_PROP = "ConfluenceCustom.SongSelector.ProgrammaticUntil"
NEUTRAL_CONTROL_ID = 9131
VISIBLE_ROWS = 13
HISTORY_ROWS = 4


def _home():
    return xbmcgui.Window(HOME_ID)


def _touch():
    _home().setProperty(TOUCH_PROP, "{:.3f}".format(time.time()))


def _selector_enabled():
    value = (xbmc.getInfoLabel("Skin.String(CCSongSelectorEnabled)") or "true").strip().lower()
    return value != "false"


def _set_highlight(enabled):
    home = _home()
    if enabled:
        home.setProperty(HIGHLIGHT_PROP, "1")
    else:
        home.clearProperty(HIGHLIGHT_PROP)


def _programmatic_focus_begin(seconds=0.8):
    _home().setProperty(PROGRAMMATIC_UNTIL_PROP, "{:.6f}".format(time.time() + float(seconds)))


def _programmatic_focus_end():
    _home().setProperty(PROGRAMMATIC_UNTIL_PROP, "{:.6f}".format(time.time() + 0.25))


def _set_credits_view(enabled):
    home = _home()
    if enabled:
        home.setProperty(CREDITS_VIEW_PROP, "1")
    else:
        home.clearProperty(CREDITS_VIEW_PROP)


def _set_lyrics_view(enabled):
    home = _home()
    if enabled:
        home.setProperty(LYRICS_VIEW_PROP, "1")
    else:
        home.clearProperty(LYRICS_VIEW_PROP)


def credits_view():
    return _home().getProperty(CREDITS_VIEW_PROP) == "1"


def lyrics_view():
    return _home().getProperty(LYRICS_VIEW_PROP) == "1"


def detail_view():
    return credits_view() or lyrics_view()


def lyrics_available():
    home = _home()
    status = (home.getProperty(CULRC_STATUS_PROP) or "").strip().lower()
    if status == "not_found":
        return False
    if status in ("searching", "found"):
        return True
    return bool((home.getProperty(LYRICS_TEXT_PROP) or "").strip()) or home.getProperty(CULRC_RUNNING_PROP) == "true"


def _focus(control_id):
    xbmc.executebuiltin("Control.SetFocus({})".format(int(control_id)))


def _container_num_items():
    try:
        return int(xbmc.getInfoLabel("Container({}).NumItems".format(LIST_ID)) or 0)
    except Exception:
        return 0


def _wait_for_list_visible(timeout_ms=1200):
    deadline = time.time() + (max(0, int(timeout_ms)) / 1000.0)
    while time.time() < deadline:
        if xbmc.getCondVisibility(
                "Window.IsActive({}) + Control.IsVisible({})".format(DIALOG_ID, LIST_ID)):
            return True
        xbmc.sleep(20)
    return xbmc.getCondVisibility(
        "Window.IsActive({}) + Control.IsVisible({})".format(DIALOG_ID, LIST_ID)
    )


def _wait_for_list(target_index, timeout_ms=2500):
    target_index = max(0, int(target_index))
    deadline = time.time() + (max(0, int(timeout_ms)) / 1000.0)
    while time.time() < deadline:
        if not xbmc.getCondVisibility("Window.IsActive({})".format(DIALOG_ID)):
            return False
        if _container_num_items() > target_index:
            return True
        xbmc.sleep(20)
    return _container_num_items() > target_index


def _desired_window(count, playing):
    count = max(0, int(count or 0))
    if count <= 0:
        return 0, -1
    playing = min(max(int(playing), 0), count - 1)
    maximum_start = max(0, count - VISIBLE_ROWS)
    start = min(max(playing - HISTORY_ROWS, 0), maximum_start)
    end = min(count - 1, start + VISIBLE_ROWS - 1)
    return start, end


def _native_list_control():
    for window_id in (DIALOG_ID + 10000, DIALOG_ID):
        try:
            window = xbmcgui.Window(window_id)
            control = window.getControl(LIST_ID)
            if control is not None:
                return window, control
        except Exception:
            pass
    return None, None


def _native_list_index():
    _window, control = _native_list_control()
    if control is not None:
        try:
            selected = int(control.getSelectedPosition())
            if selected >= 0:
                return selected
        except Exception:
            pass
    try:
        current_item = int(xbmc.getInfoLabel("Container({}).CurrentItem".format(LIST_ID)) or 0)
    except Exception:
        return None
    return current_item - 1 if current_item > 0 else None


def focus_current(take_focus=False):
    """Position the display-only playlist and leave input on proxy 9131."""
    home = _home()
    restore_highlight = home.getProperty(HIGHLIGHT_PROP) == "1"
    if restore_highlight:
        _set_highlight(False)
    _programmatic_focus_begin()
    try:
        if not _wait_for_list_visible():
            return False
        count = size()
        if count <= 0:
            return False
        playing = current()
        view_start, view_end = _desired_window(count, playing)
        if not _wait_for_list(view_end):
            return False
        _window, control = _native_list_control()
        if control is None:
            return False
        try:
            control.selectItem(view_start)
            xbmc.sleep(20)
            control.selectItem(view_end)
            xbmc.sleep(80)
            control.selectItem(playing)
            xbmc.sleep(35)
            _focus(NEUTRAL_CONTROL_ID)
        except Exception:
            return False
        return True
    finally:
        _programmatic_focus_end()
        if restore_highlight:
            _set_highlight(True)


def _focus_existing_track_selection():
    deadline = time.time() + 0.35
    while time.time() < deadline:
        if xbmc.getCondVisibility(
                "Window.IsActive({}) + Control.IsVisible({})".format(DIALOG_ID, LIST_ID)):
            _focus(NEUTRAL_CONTROL_ID)
            xbmc.sleep(5)
            if xbmc.getCondVisibility(
                    "Window.IsActive({}) + Control.HasFocus({})".format(DIALOG_ID, NEUTRAL_CONTROL_ID)):
                return True
        xbmc.sleep(5)
    return False


def _audio_player_id():
    try:
        request = {"jsonrpc": "2.0", "method": "Player.GetActivePlayers", "id": 1}
        result = json.loads(xbmc.executeJSONRPC(json.dumps(request)))
        for player in result.get("result", []):
            if player.get("type") == "audio":
                return int(player.get("playerid", 0))
    except Exception:
        pass
    return 0


def open_popup():
    if not _selector_enabled() or size() <= 0:
        return
    _set_highlight(False)
    _set_credits_view(False)
    _set_lyrics_view(False)
    _home().clearProperty(SELECTION_TARGET_PROP)
    _home().clearProperty(CREDITS_WINDOW_START_PROP)
    _touch()
    controller_open_dialog()
    focus_current()
    _set_highlight(True)


def show_credits():
    _set_highlight(False)
    if not xbmc.getCondVisibility("Window.IsActive({})".format(DIALOG_ID)):
        return
    home = _home()
    _set_lyrics_view(False)
    _set_credits_view(True)
    if home.getProperty(CREDITS_WINDOW_START_PROP) == "":
        home.setProperty(CREDITS_WINDOW_START_PROP, "0")
    _touch()
    for _ in range(8):
        xbmc.sleep(30)
        _focus(CREDITS_NAV_ID)
        xbmc.sleep(20)
        if xbmc.getCondVisibility("Window.IsActive({}) + Control.HasFocus({})".format(DIALOG_ID, CREDITS_NAV_ID)):
            break


def show_lyrics():
    _set_highlight(False)
    if not xbmc.getCondVisibility("Window.IsActive({})".format(DIALOG_ID)):
        return
    if not lyrics_available():
        show_credits()
        return
    _set_credits_view(False)
    _set_lyrics_view(True)
    if not _home().getProperty(LYRICS_SYNC_PROP):
        _home().setProperty(LYRICS_SYNC_PROP, "1")
    _touch()
    for _ in range(8):
        xbmc.sleep(30)
        _focus(LYRICS_NAV_ID)
        xbmc.sleep(20)
        if xbmc.getCondVisibility("Window.IsActive({}) + Control.HasFocus({})".format(DIALOG_ID, LYRICS_NAV_ID)):
            break


def _int_home_property(name, default=0):
    try:
        return int(_home().getProperty(name) or default)
    except Exception:
        return int(default)


def scroll_lyrics_manual(delta):
    home = _home()
    if not lyrics_view() or home.getProperty(LYRICS_SYNC_PROP) != "0":
        return
    count = max(0, _int_home_property(LYRICS_LINE_COUNT_PROP, 0))
    maximum = max(0, count - LYRICS_VISIBLE_ROWS)
    current_start = _int_home_property(
        LYRICS_MANUAL_START_PROP, _int_home_property(LYRICS_WINDOW_START_PROP, 0)
    )
    target = min(max(current_start + int(delta), 0), maximum)
    home.setProperty(LYRICS_MANUAL_START_PROP, str(target))
    _touch()


def toggle_lyrics_sync():
    home = _home()
    if not lyrics_view() or not xbmc.getCondVisibility("Window.IsActive({})".format(DIALOG_ID)):
        return
    if (home.getProperty(CULRC_ISLRC_PROP) or "").strip().lower() != "true":
        return
    if home.getProperty(LYRICS_SYNC_PROP) == "0":
        home.setProperty(LYRICS_SYNC_PROP, "1")
    else:
        home.setProperty(LYRICS_MANUAL_START_PROP, home.getProperty(LYRICS_WINDOW_START_PROP) or "0")
        home.setProperty(LYRICS_SYNC_PROP, "0")
    _focus(LYRICS_NAV_ID)
    _touch()


def scroll_credits(delta):
    home = _home()
    if not credits_view():
        return
    source_count = max(0, _int_home_property(CREDITS_SOURCE_COUNT_PROP, 0))
    count = max(0, _int_home_property(CREDITS_DISPLAY_COUNT_PROP, source_count))
    if count <= CREDITS_VISIBLE_ROWS:
        return
    maximum = max(0, count - CREDITS_VISIBLE_ROWS)
    current_start = _int_home_property(CREDITS_WINDOW_START_PROP, 0)
    target = min(max(current_start + int(delta), 0), maximum)
    if target != current_start:
        home.setProperty(CREDITS_WINDOW_START_PROP, str(target))
        _touch()


def next_from_credits():
    if lyrics_available():
        show_lyrics()
    else:
        show_tracks()


def show_tracks():
    _set_highlight(False)
    _set_credits_view(False)
    _set_lyrics_view(False)
    _touch()
    if not _focus_existing_track_selection():
        _focus(NEUTRAL_CONTROL_ID)
    _set_highlight(True)


def reactivate():
    if detail_view():
        return
    _set_highlight(True)
    _focus(NEUTRAL_CONTROL_ID)
    _touch()


def close_dialog():
    controller_close_dialog()
    _touch()


def closed():
    controller_on_unload()
    _touch()
    xbmc.sleep(40)
    if xbmc.getCondVisibility("Window.IsActive(Home)"):
        _focus(MAIN_LIST_ID)


def _playlist_index_for_path(target):
    if not target:
        return None
    request = {
        "jsonrpc": "2.0",
        "method": "Playlist.GetItems",
        "params": {"playlistid": 0},
        "id": 1,
    }
    try:
        result = json.loads(xbmc.executeJSONRPC(json.dumps(request))).get("result", {})
        items = result.get("items", []) or []
    except Exception:
        return None
    for index, item in enumerate(items):
        if (item.get("file") or "") == target:
            return index
    norm = target.replace("\\", "/")
    for index, item in enumerate(items):
        if (item.get("file") or "").replace("\\", "/") == norm:
            return index
    return None


def play_path(path):
    target = _playlist_index_for_path(path)
    if target is None:
        return
    request = {
        "jsonrpc": "2.0",
        "method": "Player.GoTo",
        "params": {"playerid": _audio_player_id(), "to": int(target)},
        "id": 1,
    }
    xbmc.executeJSONRPC(json.dumps(request))
    _touch()


def play_focused():
    """Start the selected row. Selection is never a popup-close event."""
    if not xbmc.getCondVisibility(
            "Window.IsActive({}) + Control.HasFocus({})".format(DIALOG_ID, NEUTRAL_CONTROL_ID)):
        return
    target = _native_list_index()
    if target is None:
        return
    count = size()
    if target < 0 or target >= count:
        return
    home = _home()
    home.setProperty(SELECTION_TARGET_PROP, str(target))
    request = {
        "jsonrpc": "2.0",
        "method": "Player.GoTo",
        "params": {"playerid": _audio_player_id(), "to": target},
        "id": 1,
    }
    try:
        result = json.loads(xbmc.executeJSONRPC(json.dumps(request)))
        if result.get("error"):
            home.clearProperty(SELECTION_TARGET_PROP)
            return
    except Exception:
        home.clearProperty(SELECTION_TARGET_PROP)
        return
    _touch()


def main():
    mode = (sys.argv[1] if len(sys.argv) > 1 else "").strip().lower()
    if mode == "open":
        open_popup()
    elif mode == "close":
        close_dialog()
    elif mode == "closed":
        closed()
    elif mode == "reactivate":
        reactivate()
    elif mode == "togglelyricsync":
        toggle_lyrics_sync()
    elif mode == "lyricsup":
        scroll_lyrics_manual(-1)
    elif mode == "lyricsdown":
        scroll_lyrics_manual(1)
    elif mode == "credits":
        show_credits()
    elif mode == "creditsup":
        scroll_credits(-1)
    elif mode == "creditsdown":
        scroll_credits(1)
    elif mode == "lyrics":
        show_lyrics()
    elif mode == "nextcredits":
        next_from_credits()
    elif mode == "tracks":
        show_tracks()
    elif mode == "playpath":
        play_path(sys.argv[2] if len(sys.argv) > 2 else "")
    elif mode == "playfocused":
        play_focused()


if __name__ == "__main__":
    main()
