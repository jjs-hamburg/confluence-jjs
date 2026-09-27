# -*- coding: utf-8 -*-
from __future__ import absolute_import

import json
import sys
import time

import xbmc
import xbmcgui

from songselector_state import close_popup, current, set_popup_open, size

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
CREDITS_SCROLL_ID = 9121
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


def _set_highlight(enabled):
    home = _home()
    if enabled:
        home.setProperty(HIGHLIGHT_PROP, "1")
    else:
        home.clearProperty(HIGHLIGHT_PROP)


def _programmatic_focus_begin(seconds=0.8):
    # The viewport setup deliberately focuses several rows. Mark that sequence so
    # the service never mistakes it for manual Up/Down navigation. The navigation
    # highlight itself stays visible permanently on the track page.
    _home().setProperty(PROGRAMMATIC_UNTIL_PROP, "{:.6f}".format(time.time() + float(seconds)))


def _programmatic_focus_end():
    # Leave a short grace period because the native list can report its final
    # position a few frames after Control.SetFocus returns.
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
    status = (home.getProperty(CULRC_STATUS_PROP) or '').strip().lower()
    if status == 'not_found':
        return False
    if status in ('searching', 'found'):
        return True
    # Before the first JJS status arrives, keep the page reachable only while
    # CU LRC's service is actually running or text is already present.
    return bool((home.getProperty(LYRICS_TEXT_PROP) or '').strip()) or home.getProperty(CULRC_RUNNING_PROP) == 'true'


def _focus(control_id):
    xbmc.executebuiltin("Control.SetFocus({})".format(int(control_id)))



def _container_num_items():
    try:
        return int(xbmc.getInfoLabel("Container({}).NumItems".format(LIST_ID)) or 0)
    except Exception:
        return 0


def _wait_for_list_visible(timeout_ms=1200):
    """Wait until Kodi has actually made the playlist control focusable.

    ActivateWindow and the detail-page visibility properties are asynchronous.
    Focusing 9110 one frame too early is the source of the repeated
    "asked to focus, but it can't" errors seen in kodi.log.
    """
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
    """Wait until the requested playlist row actually exists in the native list.

    playlistmusic:// is filled asynchronously. 5.0.59 returned as soon as the first
    row existed, so a later absolute target was clamped to row 0.
    """
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
    """Return the 13-row viewport requested for automatic playback following.

    Tracks 1-5 keep the first page unchanged. From track 6 onward the playing
    song sits on row 5 whenever possible, leaving four previous songs above it
    and up to eight upcoming songs below it. At the album end the final page is
    held steady, so the last track stays visible at the bottom.
    """
    count = max(0, int(count or 0))
    if count <= 0:
        return 0, -1
    playing = min(max(int(playing), 0), count - 1)
    maximum_start = max(0, count - VISIBLE_ROWS)
    start = min(max(playing - HISTORY_ROWS, 0), maximum_start)
    end = min(count - 1, start + VISIBLE_ROWS - 1)
    return start, end


def _native_list_control():
    """Return the active native playlist control without forcing GUI focus."""
    for window_id in (DIALOG_ID + 10000, DIALOG_ID):
        try:
            window = xbmcgui.Window(window_id)
            control = window.getControl(LIST_ID)
            if control is not None:
                return window, control
        except Exception:
            pass
    return None, None


def focus_current(take_focus=False):
    """Position the native playlist on the playing song without a visible focus jump.

    Kodi needs the short selectItem(start/end/current) sequence to build the wanted
    13-row viewport. While that purely programmatic sequence runs, suppress only the
    grey navigation tile; the separately coloured currently-playing row remains
    visible. The grey tile is restored on the final row afterwards.
    """
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

        window, control = _native_list_control()
        if control is None:
            return False
        try:
            control.selectItem(view_start)
            xbmc.sleep(20)
            control.selectItem(view_end)
            xbmc.sleep(80)
            control.selectItem(playing)
            xbmc.sleep(35)
            if take_focus:
                window.setFocus(control)
            else:
                _focus(NEUTRAL_CONTROL_ID)
        except Exception:
            return False
        return True
    finally:
        _programmatic_focus_end()
        if restore_highlight:
            _set_highlight(True)



def _focus_existing_track_selection():
    """Return from credits/lyrics to the already-positioned track list.

    The native list keeps its selected row and viewport while hidden. Reusing that
    state avoids replaying the slower viewport-positioning sequence and makes the
    grey navigation tile available on the first practical GUI frame.
    """
    window, control = _native_list_control()
    if control is not None:
        try:
            window.setFocus(control)
            if xbmc.getCondVisibility(
                    "Window.IsActive({}) + Control.HasFocus({})".format(DIALOG_ID, LIST_ID)):
                return True
        except Exception:
            pass

    deadline = time.time() + 0.35
    while time.time() < deadline:
        window, control = _native_list_control()
        if control is not None and xbmc.getCondVisibility(
                "Window.IsActive({}) + Control.IsVisible({})".format(DIALOG_ID, LIST_ID)):
            try:
                window.setFocus(control)
                if xbmc.getCondVisibility(
                        "Window.IsActive({}) + Control.HasFocus({})".format(DIALOG_ID, LIST_ID)):
                    return True
            except Exception:
                pass
        xbmc.sleep(5)
    return False


def _close_dialog():
    xbmc.executebuiltin("Dialog.Close({},true)".format(DIALOG_ID))


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
    if size() <= 0:
        return
    # Keep the grey navigation tile hidden while Kodi creates and positions the
    # native list. This prevents the default/bottom row from flashing briefly.
    _set_highlight(False)
    _set_credits_view(False)
    _set_lyrics_view(False)
    _home().clearProperty(SELECTION_TARGET_PROP)
    _home().clearProperty(CREDITS_WINDOW_START_PROP)
    set_popup_open(True)
    _touch()
    xbmc.executebuiltin("ActivateWindow({})".format(DIALOG_ID))
    focus_current(take_focus=True)
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
    # Focus belongs to the visible credits page itself. 9123 is a transparent
    # full-area button covering that page, not an offscreen/tiny anchor. Retry
    # briefly while Kodi applies the visibility switch.
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
    # Keep the lyrics page reachable while CU LRC is fetching. Once CU LRC has
    # explicitly reported not_found, navigation skips this third page.
    _set_credits_view(False)
    _set_lyrics_view(True)
    # Synchronized LRC scrolling is on by default for a track. Enter/OK on the
    # lyrics page toggles it without affecting normal manual scrollbar use.
    if not _home().getProperty(LYRICS_SYNC_PROP):
        _home().setProperty(LYRICS_SYNC_PROP, "1")
    _touch()
    # Lyrics are rendered from Home properties, so one persistent proxy handles
    # horizontal navigation, Enter/OK and manual Up/Down without focusing a
    # conditional GUI list.
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
    """Move the property-backed lyrics viewport while sync is paused."""
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
    """Enter/OK toggles automatic LRC following on the lyrics page."""
    home = _home()
    if not lyrics_view() or not xbmc.getCondVisibility("Window.IsActive({})".format(DIALOG_ID)):
        return
    if (home.getProperty(CULRC_ISLRC_PROP) or "").strip().lower() != "true":
        return
    if home.getProperty(LYRICS_SYNC_PROP) == "0":
        home.setProperty(LYRICS_SYNC_PROP, "1")
    else:
        # Freeze manual browsing at the viewport currently shown by sync.
        home.setProperty(LYRICS_MANUAL_START_PROP,
                         home.getProperty(LYRICS_WINDOW_START_PROP) or "0")
        home.setProperty(LYRICS_SYNC_PROP, "0")
    _focus(LYRICS_NAV_ID)
    _touch()


def scroll_credits(delta):
    """Scroll the property-backed credits viewport without touching Kodi GUI controls."""
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
    # Credits/lyrics hide 9110 but do not destroy its native selection/viewport.
    # Reuse that state instead of rebuilding the 13-row viewport, so the grey
    # highlight is back essentially immediately when returning to the track page.
    _set_highlight(False)
    _set_credits_view(False)
    _set_lyrics_view(False)
    _touch()
    if not _focus_existing_track_selection():
        focus_current(take_focus=True)
    _set_highlight(True)


def reactivate():
    # Backwards-compatible entry point for older XML. The track page now keeps
    # its selection highlight active continuously.
    if detail_view():
        return
    _set_highlight(True)
    if focus_current(take_focus=True):
        _touch()


def close_dialog():
    _set_highlight(False)
    _set_credits_view(False)
    _set_lyrics_view(False)
    _home().clearProperty(SELECTION_TARGET_PROP)
    _home().clearProperty(CREDITS_WINDOW_START_PROP)
    close_popup()
    _touch()
    _close_dialog()


def closed():
    _set_highlight(False)
    _set_credits_view(False)
    _set_lyrics_view(False)
    _home().clearProperty(SELECTION_TARGET_PROP)
    _home().clearProperty(CREDITS_WINDOW_START_PROP)
    close_popup()
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
    """Play the row currently focused in Kodi's native playlist container.

    Kodi's Container.Position is the focused viewport position, not the absolute
    playlist index once the list has scrolled. Container.CurrentItem is the
    absolute current item (1-based), so convert it to the playlist's 0-based index.
    """
    if not xbmc.getCondVisibility("Window.IsActive({}) + Control.HasFocus({})".format(DIALOG_ID, LIST_ID)):
        return
    try:
        current_item = int(xbmc.getInfoLabel("Container({}).CurrentItem".format(LIST_ID)) or 0)
        target = current_item - 1
    except Exception:
        return
    count = size()
    if target < 0 or target >= count:
        return

    # Mark explicit OK/Select playback separately from a natural track change.
    # The service uses this marker to follow the newly playing row without
    # confusing that move with manual Up/Down navigation.
    home = _home()
    previous_playing = current()
    if target != previous_playing:
        home.setProperty(SELECTION_TARGET_PROP, str(target))
    else:
        home.clearProperty(SELECTION_TARGET_PROP)

    request = {
        "jsonrpc": "2.0",
        "method": "Player.GoTo",
        "params": {"playerid": _audio_player_id(), "to": target},
        "id": 1,
    }
    xbmc.log(
        "[CC-DIAG] playfocused before GoTo target={} previous={} dialog_active={} popup_prop={}".format(
            target,
            previous_playing,
            xbmc.getCondVisibility("Window.IsActive({})".format(DIALOG_ID)),
            popup_open(),
        ),
        xbmc.LOGINFO,
    )
    try:
        result = json.loads(xbmc.executeJSONRPC(json.dumps(request)))
        xbmc.log(
            "[CC-DIAG] playfocused after GoTo target={} result_error={} dialog_active={} popup_prop={}".format(
                target,
                bool(result.get("error")),
                xbmc.getCondVisibility("Window.IsActive({})".format(DIALOG_ID)),
                popup_open(),
            ),
            xbmc.LOGINFO,
        )
        if result.get("error"):
            home.clearProperty(SELECTION_TARGET_PROP)
            return
    except Exception:
        home.clearProperty(SELECTION_TARGET_PROP)
        return

    # Keep the popup open: selecting a song is now a playback action only.
    # The service detects the new playing index and performs one automatic
    # viewport follow for that track. Back remains the sole close action.
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
