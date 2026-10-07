# -*- coding: utf-8 -*-
"""Single owner for Song Popup window lifecycle.

Window 1116 is the authority. The legacy PopupOpen property is kept only as a
published compatibility mirror for existing skin expressions.
"""
from __future__ import absolute_import

import xbmc
import xbmcgui

from songselector_state import set_popup_open
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


def open_dialog():
    """Open window 1116 and start its popup-only data session."""
    set_popup_open(True)
    if not is_open():
        xbmc.executebuiltin("ActivateWindow({})".format(DIALOG_ID))
    _start_lyrics_session()


def close_dialog():
    """The only implementation that actively closes window 1116."""
    _clear_lifecycle_state()
    if is_open():
        xbmc.executebuiltin("Dialog.Close({},true)".format(DIALOG_ID))


def on_unload():
    """Mirror a dialog that Kodi has already unloaded; never closes it again."""
    _clear_lifecycle_state()


def reconcile():
    """Publish actual Kodi window state without making the property authoritative."""
    opened = is_open()
    set_popup_open(opened)
    return opened
