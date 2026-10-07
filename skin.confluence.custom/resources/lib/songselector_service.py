# -*- coding: utf-8 -*-
"""Compatibility shim for the pre-5.0.189 Song Selector runtime.

The former all-in-one service mixed Now Playing, artwork geometry, popup
lifecycle, lyrics, credits and playback callbacks in one 150 ms loop. Runtime
ownership is now split between nowplaying_service.py and songpopup_service.py.

Keep the old module name only for internal compatibility while the remaining
callers are migrated. Importing this file performs no background work and never
touches Kodi GUI controls.
"""
from __future__ import absolute_import

import xbmc

from songpopup_data import (
    build_credit_display_rows as _build_credit_display_rows,
    clean_and_time_lyrics as _clean_and_time_culrc_lyrics,
    clear_credits_window as _clear_credits_window,
    clear_lyrics_window as _clear_lyrics_window,
    font_signature as _songselector_font_signature,
    int_property as _int_property,
    lyrics_scroll_window as _lyrics_scroll_window,
    publish_credits_window as _publish_credits_window,
    publish_lyrics_window as _publish_lyrics_window,
)


def _clean_culrc_lyrics(raw):
    return _clean_and_time_culrc_lyrics(raw)[0]


def run():
    """Compatibility entry point: start the isolated Song Popup controller."""
    xbmc.executebuiltin(
        "RunScript(special://skin/resources/lib/songpopup_service.py)",
        wait=False,
    )


if __name__ == "__main__":
    run()
