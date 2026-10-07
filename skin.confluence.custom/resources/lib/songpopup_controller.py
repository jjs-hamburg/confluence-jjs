# -*- coding: utf-8 -*-
"""Single owner for Song Popup window lifecycle.

Window 1116 is the authority. The legacy PopupOpen property is kept only as a
published compatibility mirror for existing skin expressions.
"""
from __future__ import absolute_import

import time

import xbmc
import xbmcgui

from songselector_state import current, set_popup_open
from worker_lock import worker_is_running

HOME_ID = 10000
DIALOG_ID = 1116
HIGHLIGHT_PROP = "ConfluenceCustom.SongSelector.Highlight"
SELECTION_TARGET_PROP = "ConfluenceCustom.SongSelector.SelectionTarget"
CREDITS_VIEW_PROP = "ConfluenceCustom.SongSelector.CreditsView"
LYRICS_VIEW_PROP = "ConfluenceCustom.SongSelector.LyricsView"
CREDITS_WINDOW_START_PROP = "ConfluenceCustom.SongSelector.CreditsWindowStart"
LYRICS_RUNNING_PROP = "ConfluenceCustom.Lyrics.ServiceRunning"
LYRICS_SCRIPT = "special://skin/resources/lib/culrc_runner.py"
FAST_STOP_SETTLE_SECONDS = 0.35


def _home():
    return xbmcgui.Window(HOME_ID)


def is_open():
    return xbmc.getCondVisibility("Window.IsActive({})".format(DIALOG_ID))


def _clear_lifecycle_state():
    home = _home()
    for prop in (
        HIGHLIGHT_PROP,
        SELECTION_TARGET_PROP,
        CREDITS_VIEW_PROP,
        LYRICS_VIEW_PROP,
        CREDITS_WINDOW_START_PROP,
    ):
        home.clearProperty(prop)
    set_popup_open(False)


def _start_lyrics_session():
    home = _home()
    if home.getProperty(LYRICS_RUNNING_PROP) == "1" or worker_is_running("lyrics"):
        return
    xbmc.executebuiltin("RunScript({})".format(LYRICS_SCRIPT), wait=False)


class _FastStopEvents(xbmc.Player):
    """Recognize an explicit Stop without reviving HasAudio timeout logic.

    Kodi may also emit onPlayBackStopped while changing tracks. A Song Popup
    selection publishes SelectionTarget before Player.GoTo, and other playlist
    navigation normally changes the playlist index. Both cases suppress this
    fast-close path. The popup service retains its longer callback-driven
    fallback for genuine playback-end cases.
    """

    def __init__(self):
        xbmc.Player.__init__(self)
        self.candidate_at = None
        self.playlist_index = None

    def reset(self):
        self.candidate_at = None
        self.playlist_index = None

    def _started(self):
        self.reset()

    def onPlayBackStarted(self):
        self._started()

    def onAVStarted(self):
        self._started()

    def onPlayBackStopped(self):
        home = _home()
        if home.getProperty(SELECTION_TARGET_PROP):
            self.reset()
            return
        self.candidate_at = time.monotonic()
        try:
            self.playlist_index = current()
        except Exception:
            self.playlist_index = None

    def onPlayBackEnded(self):
        # Natural end/advance stays on the popup service's conservative path.
        self.reset()

    def confirmed_explicit_stop(self):
        if self.candidate_at is None:
            return False
        if xbmc.getCondVisibility("Player.HasAudio"):
            self.reset()
            return False
        if _home().getProperty(SELECTION_TARGET_PROP):
            self.reset()
            return False
        if self.playlist_index is not None:
            try:
                if current() != self.playlist_index:
                    self.reset()
                    return False
            except Exception:
                pass
        if time.monotonic() - self.candidate_at < FAST_STOP_SETTLE_SECONDS:
            return False
        self.reset()
        return True


_FAST_STOP_EVENTS = _FastStopEvents()


def open_dialog():
    """Open window 1116 and start its popup-only data session."""
    _FAST_STOP_EVENTS.reset()
    set_popup_open(True)
    if not is_open():
        xbmc.executebuiltin("ActivateWindow({})".format(DIALOG_ID))
    _start_lyrics_session()


def close_dialog():
    """The only implementation that actively closes window 1116."""
    _FAST_STOP_EVENTS.reset()
    _clear_lifecycle_state()
    if is_open():
        xbmc.executebuiltin("Dialog.Close({},true)".format(DIALOG_ID))


def on_unload():
    """Mirror a dialog that Kodi has already unloaded; never closes it again."""
    _FAST_STOP_EVENTS.reset()
    _clear_lifecycle_state()


def reconcile():
    """Publish actual Kodi window state and keep popup-only data attached to it."""
    opened = is_open()
    if not opened:
        _FAST_STOP_EVENTS.reset()
        set_popup_open(False)
        return False

    if _FAST_STOP_EVENTS.confirmed_explicit_stop():
        close_dialog()
        return False

    set_popup_open(True)
    # Covers the close/reopen edge where the previous lyrics session is still
    # releasing its worker lock when the dialog is opened again.
    _start_lyrics_session()
    return True
