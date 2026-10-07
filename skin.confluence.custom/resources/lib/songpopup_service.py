# -*- coding: utf-8 -*-
"""Song Popup runtime for Confluence-jjs.

This worker owns popup navigation follow plus credits/lyrics data while window
1116 is actually open. General Now Playing data/artwork is handled by
nowplaying_service.py. Window lifecycle itself is centralized in
songpopup_controller.py.
"""
from __future__ import absolute_import

import bisect
import time

import xbmc
import xbmcgui

from credits_runtime import CreditsRuntime, clear_properties as clear_credits_properties
from songpopup_controller import (
    close_dialog as controller_close_dialog,
    is_open as controller_is_open,
    reconcile as controller_reconcile,
)
from songselector_action import _native_list_index, detail_view, focus_current, lyrics_view, open_popup, show_credits
from songselector_service import (
    _build_credit_display_rows,
    _clean_and_time_culrc_lyrics,
    _clear_credits_window,
    _clear_lyrics_window,
    _int_property,
    _lyrics_scroll_window,
    _publish_credits_window,
    _publish_lyrics_window,
    _songselector_font_signature,
)
from songselector_state import current, size
from worker_lock import WorkerLock

HOME_ID = 10000
DIALOG_ID = 1116
NEUTRAL_CONTROL_ID = 9131
SERVICE_RUNNING_PROP = "ConfluenceCustom.SongPopup.ServiceRunning"
TOUCH_PROP = "ConfluenceCustom.SongSelector.Touch"
SELECTION_TIMEOUT_SETTING = "CCSongSelectorSelectionTimeout"
AUTO_OPEN_SETTING = "CCSongSelectorAutoOpen"
HIGHLIGHT_PROP = "ConfluenceCustom.SongSelector.Highlight"
PROGRAMMATIC_UNTIL_PROP = "ConfluenceCustom.SongSelector.ProgrammaticUntil"
SELECTION_TARGET_PROP = "ConfluenceCustom.SongSelector.SelectionTarget"
PLAYBACK_STOP_SETTLE_SECONDS = 1.0

LYRICS_TEXT_PROP = "ConfluenceCustom.SongSelector.LyricsText"
CULRC_LYRICS_PROP = "culrc.lyrics"
CULRC_ISLRC_PROP = "culrc.islrc"
CULRC_STATUS_PROP = "culrc.jjsstatus"
LYRICS_SYNC_PROP = "ConfluenceCustom.SongSelector.LyricsSync"
LYRICS_SYNC_DELAY_SETTING = "CCSongSelectorLyricsSyncDelay"
DEFAULT_LYRICS_SYNC_DELAY_SECONDS = 0.25
LYRICS_WINDOW_START_PROP = "ConfluenceCustom.SongSelector.LyricsWindowStart"
LYRICS_MANUAL_START_PROP = "ConfluenceCustom.SongSelector.LyricsManualStart"

CREDITS_SOURCE_COUNT_PROP = "ConfluenceCustom.Credits.LineCount"
CREDITS_SOURCE_UPDATED_PROP = "ConfluenceCustom.Credits.Updated"
CREDITS_WINDOW_START_PROP = "ConfluenceCustom.SongSelector.CreditsWindowStart"
CREDITS_DISPLAY_COUNT_PROP = "ConfluenceCustom.SongSelector.CreditsLineCount"


def _skin_string(name, default=""):
    value = xbmc.getInfoLabel("Skin.String({})".format(name))
    return value or default


def _seconds(name, default):
    try:
        return max(0, int(_skin_string(name, str(default))))
    except Exception:
        return default


def _selector_enabled():
    return _skin_string("CCSongSelectorEnabled", "true").strip().lower() != "false"


def _auto_open_enabled():
    return _skin_string(AUTO_OPEN_SETTING, "false").strip().lower() == "true"


def _audio_active():
    return xbmc.getCondVisibility("Player.HasAudio")


def _popup_context():
    return xbmc.getCondVisibility(
        "[Window.IsActive(Home) | Window.IsActive(1116)] + "
        "!String.IsEqual(Playlist.Length(music),0) + !Playlist.IsRandom + "
        "String.IsEmpty(Window(Videos).Property(PlayingBackgroundMedia))"
    )


def _set_navigation_highlight(home, enabled):
    if enabled:
        home.setProperty(HIGHLIGHT_PROP, "1")
    else:
        home.clearProperty(HIGHLIGHT_PROP)


def _close_popup_runtime(home):
    """Close through the single lifecycle controller."""
    _set_navigation_highlight(home, False)
    controller_close_dialog()


def _clear_popup_data(home):
    _set_navigation_highlight(home, False)
    home.clearProperty(SELECTION_TARGET_PROP)
    home.clearProperty(LYRICS_TEXT_PROP)
    home.clearProperty(LYRICS_SYNC_PROP)
    home.clearProperty(CREDITS_WINDOW_START_PROP)
    _clear_lyrics_window(home)
    _clear_credits_window(home)


def _track_navigation_focused():
    return xbmc.getCondVisibility(
        "Window.IsActive({}) + Control.HasFocus({})".format(DIALOG_ID, NEUTRAL_CONTROL_ID)
    )


def _container_position():
    if not _track_navigation_focused():
        return None
    return _native_list_index()


def _programmatic_focus_active(home):
    try:
        return float(home.getProperty(PROGRAMMATIC_UNTIL_PROP) or "0") > time.time()
    except Exception:
        return False


def _selection_target(home):
    raw = home.getProperty(SELECTION_TARGET_PROP)
    if raw == "":
        return None
    try:
        return int(raw)
    except Exception:
        home.clearProperty(SELECTION_TARGET_PROP)
        return None


def _lyrics_sync_delay_seconds():
    try:
        raw = xbmc.getInfoLabel("Skin.String({})".format(LYRICS_SYNC_DELAY_SETTING))
        value = float(raw or DEFAULT_LYRICS_SYNC_DELAY_SECONDS)
    except Exception:
        value = DEFAULT_LYRICS_SYNC_DELAY_SECONDS
    return max(0.0, min(1.0, value))


class PlaybackEvents(xbmc.Player):
    """Track real playback stop/end callbacks without classifying Player.GoTo.

    Kodi can emit a stop while switching tracks. A following start/AV-start
    simply cancels the pending stop. Only a stop/end that remains unmatched by
    a new start is considered the end of the music session.
    """

    def __init__(self):
        xbmc.Player.__init__(self)
        self.stop_candidate_at = None

    def _started(self):
        self.stop_candidate_at = None

    def _stopped(self):
        self.stop_candidate_at = time.monotonic()

    def onPlayBackStarted(self):
        self._started()

    def onAVStarted(self):
        self._started()

    def onPlayBackStopped(self):
        self._stopped()

    def onPlayBackEnded(self):
        self._stopped()

    def reset(self):
        self.stop_candidate_at = None

    def confirmed_stop(self, now, audio_active):
        if self.stop_candidate_at is None:
            return False
        if audio_active:
            self.stop_candidate_at = None
            return False
        if now - self.stop_candidate_at < PLAYBACK_STOP_SETTLE_SECONDS:
            return False
        self.stop_candidate_at = None
        return True


class PopupDataRuntime(object):
    """Property-only credits/lyrics model used only while the dialog is open."""

    def __init__(self, home):
        self.home = home
        self.credits_runtime = CreditsRuntime()
        self.credits_started = False
        self.active = False
        self.last_lyrics_file = None
        self.blocked_lyrics_raw = None
        self.last_lyrics_raw = None
        self.lyrics_sync_entries = []
        self.lyrics_sync_times = []
        self.lyrics_line_count = 0
        self.lyrics_lines = []
        self.last_lyrics_window_key = None
        self.last_lyrics_sync_enabled = None
        self.last_lyrics_font_signature = None
        self.last_credits_window_key = None
        self.last_credits_source_key = None
        self.credits_display_rows = []

    def start(self):
        self.active = True
        if not self.credits_started:
            self.credits_runtime.start()
            self.credits_started = True

    def clear(self, clear_source=False):
        if not self.active and not clear_source:
            return
        home = self.home
        home.clearProperty(LYRICS_TEXT_PROP)
        home.clearProperty(LYRICS_SYNC_PROP)
        _clear_lyrics_window(home)
        _clear_credits_window(home)
        home.clearProperty(CREDITS_WINDOW_START_PROP)
        self.last_lyrics_file = None
        self.blocked_lyrics_raw = None
        self.last_lyrics_raw = None
        self.lyrics_sync_entries = []
        self.lyrics_sync_times = []
        self.lyrics_line_count = 0
        self.lyrics_lines = []
        self.last_lyrics_window_key = None
        self.last_lyrics_sync_enabled = None
        self.last_lyrics_font_signature = None
        self.last_credits_window_key = None
        self.last_credits_source_key = None
        self.credits_display_rows = []
        self.active = False
        if clear_source:
            clear_credits_properties()

    def _update_credits(self):
        home = self.home
        try:
            self.credits_runtime.poll()
        except Exception as exc:
            xbmc.log("[ConfluenceCustom] Credits runtime: {!r}".format(exc), xbmc.LOGWARNING)

        credits_count = max(0, _int_property(home, CREDITS_SOURCE_COUNT_PROP, 0))
        credits_updated = home.getProperty(CREDITS_SOURCE_UPDATED_PROP) or ""
        font_signature = _songselector_font_signature()
        source_key = (credits_updated, credits_count, font_signature)
        if source_key != self.last_credits_source_key:
            self.credits_display_rows = _build_credit_display_rows(home, font_signature)
            if self.credits_display_rows:
                home.setProperty(CREDITS_DISPLAY_COUNT_PROP, str(len(self.credits_display_rows)))
            else:
                home.clearProperty(CREDITS_DISPLAY_COUNT_PROP)
            self.last_credits_source_key = source_key
            self.last_credits_window_key = None

        credits_start = _int_property(home, CREDITS_WINDOW_START_PROP, 0)
        key = (source_key, len(self.credits_display_rows), credits_start)
        if key != self.last_credits_window_key:
            actual_start = _publish_credits_window(home, self.credits_display_rows, credits_start)
            self.last_credits_window_key = (source_key, len(self.credits_display_rows), actual_start)

    def _update_lyrics_source(self, audio):
        home = self.home
        raw_lyrics = home.getProperty(CULRC_LYRICS_PROP) or ""
        lyrics_file = xbmc.getInfoLabel("Player.FilenameAndPath") or ""

        if audio and lyrics_file:
            if self.last_lyrics_file is None:
                self.last_lyrics_file = lyrics_file
            elif lyrics_file != self.last_lyrics_file:
                self.blocked_lyrics_raw = raw_lyrics or None
                self.last_lyrics_file = lyrics_file
                self.last_lyrics_raw = None
                home.clearProperty(LYRICS_TEXT_PROP)
                home.setProperty(LYRICS_SYNC_PROP, "1")
                self.lyrics_sync_entries = []
                self.lyrics_sync_times = []
                self.lyrics_line_count = 0
                self.lyrics_lines = []
                self.last_lyrics_window_key = None
                self.last_lyrics_sync_enabled = None
                self.last_lyrics_font_signature = None
                _clear_lyrics_window(home)

        if not audio:
            home.clearProperty(LYRICS_TEXT_PROP)
            home.clearProperty(LYRICS_SYNC_PROP)
            self.blocked_lyrics_raw = None
            self.last_lyrics_raw = None
            self.lyrics_sync_entries = []
            self.lyrics_sync_times = []
            self.lyrics_line_count = 0
            self.lyrics_lines = []
            self.last_lyrics_window_key = None
            self.last_lyrics_sync_enabled = None
            self.last_lyrics_font_signature = None
            _clear_lyrics_window(home)
            return

        if not raw_lyrics:
            home.clearProperty(LYRICS_TEXT_PROP)
            self.blocked_lyrics_raw = None
            self.last_lyrics_raw = ""
            self.lyrics_sync_entries = []
            self.lyrics_sync_times = []
            self.lyrics_line_count = 0
            self.lyrics_lines = []
            self.last_lyrics_window_key = None
            self.last_lyrics_font_signature = None
            _clear_lyrics_window(home)
            return

        if self.blocked_lyrics_raw is not None and raw_lyrics == self.blocked_lyrics_raw:
            home.clearProperty(LYRICS_TEXT_PROP)
            return

        self.blocked_lyrics_raw = None
        font_signature = _songselector_font_signature()
        if raw_lyrics == self.last_lyrics_raw and font_signature == self.last_lyrics_font_signature:
            return

        cleaned, entries, line_count = _clean_and_time_culrc_lyrics(raw_lyrics)
        self.lyrics_sync_entries = entries
        self.lyrics_sync_times = [entry[0] for entry in entries]
        self.lyrics_line_count = line_count
        self.lyrics_lines = cleaned.split("[CR]") if cleaned else []
        if cleaned:
            home.setProperty(LYRICS_TEXT_PROP, cleaned)
            home.setProperty(LYRICS_MANUAL_START_PROP, "0")
            _publish_lyrics_window(home, self.lyrics_lines, 0, None)
        else:
            home.clearProperty(LYRICS_TEXT_PROP)
            _clear_lyrics_window(home)
        if home.getProperty(LYRICS_SYNC_PROP) == "":
            home.setProperty(LYRICS_SYNC_PROP, "1")
        self.last_lyrics_window_key = None
        self.last_lyrics_sync_enabled = None
        self.last_lyrics_raw = raw_lyrics
        self.last_lyrics_font_signature = font_signature

    def _update_lyrics_window(self):
        home = self.home
        if lyrics_view() and home.getProperty(CULRC_STATUS_PROP) == "not_found":
            show_credits()

        sync_enabled = home.getProperty(LYRICS_SYNC_PROP) != "0"
        sync_ready = (
            lyrics_view()
            and (home.getProperty(CULRC_ISLRC_PROP) or "").strip().lower() == "true"
            and bool(self.lyrics_sync_entries)
            and self.lyrics_line_count > 0
        )
        if sync_enabled != self.last_lyrics_sync_enabled:
            self.last_lyrics_window_key = None
            self.last_lyrics_sync_enabled = sync_enabled

        active_first = -1
        active_last = -1
        if sync_ready and sync_enabled:
            try:
                lyric_time = max(0.0, float(xbmc.Player().getTime()) - _lyrics_sync_delay_seconds())
            except Exception:
                lyric_time = 0.0
            entry_pos = bisect.bisect_right(self.lyrics_sync_times, lyric_time) - 1
            if entry_pos >= 0:
                active_first = self.lyrics_sync_entries[entry_pos][1]
                active_last = self.lyrics_sync_entries[entry_pos][2]

        if lyrics_view() and self.lyrics_lines:
            if sync_enabled and active_first >= 0:
                window_start, _unused = _lyrics_scroll_window(self.lyrics_line_count, active_first)
            elif sync_enabled:
                window_start = 0
            else:
                window_start = _int_property(
                    home,
                    LYRICS_MANUAL_START_PROP,
                    _int_property(home, LYRICS_WINDOW_START_PROP, 0),
                )
                active_first = -1
                active_last = -1
            active_range = (active_first, active_last) if active_first >= 0 else None
            key = (window_start, active_first, active_last, len(self.lyrics_lines), sync_enabled)
            if key != self.last_lyrics_window_key:
                actual_start = _publish_lyrics_window(home, self.lyrics_lines, window_start, active_range)
                if not sync_enabled:
                    home.setProperty(LYRICS_MANUAL_START_PROP, str(actual_start))
                self.last_lyrics_window_key = (
                    actual_start,
                    active_first,
                    active_last,
                    len(self.lyrics_lines),
                    sync_enabled,
                )
        elif self.lyrics_lines:
            key = (0, -1, -1, len(self.lyrics_lines), True)
            if key != self.last_lyrics_window_key:
                _publish_lyrics_window(home, self.lyrics_lines, 0, None)
                self.last_lyrics_window_key = key

    def poll(self, audio):
        self.start()
        self._update_credits()
        self._update_lyrics_source(audio)
        self._update_lyrics_window()


def run():
    monitor = xbmc.Monitor()
    home = xbmcgui.Window(HOME_ID)
    data_runtime = PopupDataRuntime(home)
    playback_events = PlaybackEvents()

    last_touch = home.getProperty(TOUCH_PROP)
    last_user_activity = time.monotonic()
    last_list_position = None
    last_playing = -1
    was_open = False

    playback_session_active = _audio_active()
    last_auto_open_setting = _auto_open_enabled()
    auto_open_pending = bool(playback_session_active and last_auto_open_setting)
    dormant_cleaned = False

    while not monitor.abortRequested():
        standard = xbmc.getCondVisibility("Skin.HasSetting(CCStandardConfluence)")
        enabled = _selector_enabled()
        if standard or not enabled:
            if not dormant_cleaned:
                if controller_reconcile():
                    _close_popup_runtime(home)
                data_runtime.clear(clear_source=True)
                playback_events.reset()
                dormant_cleaned = True
            playback_session_active = _audio_active()
            auto_open_pending = False
            was_open = False
            last_playing = -1
            last_list_position = None
            if monitor.waitForAbort(0.50):
                break
            continue

        dormant_cleaned = False
        now = time.monotonic()
        audio = _audio_active()
        auto_open_enabled = _auto_open_enabled()

        # Stop/end handling is callback driven. A transient HasAudio gap by
        # itself is never a close reason, and Player.GoTo is never classified.
        if playback_events.confirmed_stop(now, audio):
            playback_session_active = False
            auto_open_pending = False
            if controller_is_open():
                _close_popup_runtime(home)
                was_open = False
        elif audio and not playback_session_active:
            playback_session_active = True
            if auto_open_enabled:
                auto_open_pending = True

        if auto_open_enabled and not last_auto_open_setting and audio:
            auto_open_pending = True
        last_auto_open_setting = auto_open_enabled

        if (
            auto_open_pending
            and auto_open_enabled
            and audio
            and xbmc.getCondVisibility("Window.IsActive(Home)")
            and _popup_context()
            and not controller_is_open()
        ):
            open_popup()
            auto_open_pending = False

        context = _popup_context()
        opened = controller_reconcile()

        if context:
            count = size()
            playing = current() if count > 0 else -1

            if opened:
                data_runtime.poll(audio)

                if not was_open:
                    last_user_activity = now
                    last_list_position = _container_position()

                touch = home.getProperty(TOUCH_PROP)
                if touch and touch != last_touch:
                    last_touch = touch
                    last_user_activity = now

                position = _container_position()
                if position is not None and position != last_list_position:
                    last_list_position = position
                    if not _programmatic_focus_active(home):
                        _set_navigation_highlight(home, True)
                        last_user_activity = now

                selected_target = _selection_target(home)

                # Explicit selection is a playback action only. It never closes
                # the popup. Once Kodi reports the requested row as playing, one
                # event-driven follow positions the visible list and clears the marker.
                if selected_target is not None and selected_target == playing:
                    if not detail_view():
                        focus_current()
                        last_list_position = playing
                    home.clearProperty(SELECTION_TARGET_PROP)
                    selected_target = None

                # Natural track changes follow when the user has not deliberately
                # browsed away from the playing row.
                if was_open and not detail_view() and last_playing >= 0 and playing != last_playing:
                    position = _container_position()
                    if position == last_playing or position == playing:
                        focus_current()
                        last_list_position = playing

                selection_timeout = _seconds(SELECTION_TIMEOUT_SETTING, 5)
                if (
                    not detail_view()
                    and selection_timeout
                    and _track_navigation_focused()
                    and now - last_user_activity >= selection_timeout
                ):
                    position = _container_position()
                    if position is not None and position != playing:
                        focus_current()
                        last_list_position = playing
                    _set_navigation_highlight(home, True)
                    last_user_activity = now
            elif was_open:
                data_runtime.clear(clear_source=False)
        else:
            data_runtime.clear(clear_source=False)
            if opened:
                _close_popup_runtime(home)
                opened = False
            last_list_position = None
            last_playing = -1

        was_open = opened
        if context:
            last_playing = current() if size() > 0 else -1

        if monitor.waitForAbort(0.15 if opened else 0.30):
            break

    data_runtime.clear(clear_source=True)


if __name__ == "__main__":
    _service_home = xbmcgui.Window(HOME_ID)
    _service_lock = WorkerLock("songpopup")
    if _service_lock.acquire():
        _service_home.setProperty(SERVICE_RUNNING_PROP, "1")
        try:
            run()
        finally:
            _service_home.clearProperty(SERVICE_RUNNING_PROP)
            _service_lock.release()
    else:
        xbmc.log("[ConfluenceCustom] Song Popup worker already running; duplicate start suppressed", xbmc.LOGINFO)
