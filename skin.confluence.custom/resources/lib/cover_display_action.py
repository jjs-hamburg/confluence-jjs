# -*- coding: utf-8 -*-
from __future__ import absolute_import

import xbmc
import xbmcgui
import xbmcvfs

SETTING = "CCMusicArtworkMode"
HOME_ID = 10000
BACK_PROP = "ConfluenceCustom.MusicBackArt"


def _home():
    return xbmcgui.Window(HOME_ID)


def _folder_back_art():
    try:
        playing_file = xbmc.Player().getPlayingFile() or ""
    except Exception:
        playing_file = ""
    if not playing_file:
        return ""
    normalized = playing_file.replace("\\", "/")
    if "/" not in normalized:
        return ""
    folder = normalized.rsplit("/", 1)[0] + "/"
    # back.jpg is the collection convention. The two fallbacks cost nothing and
    # make the feature tolerant of older folders without creating any files.
    for name in ("back.jpg", "back.jpeg", "back.png"):
        candidate = folder + name
        try:
            if xbmcvfs.exists(candidate):
                return candidate
        except Exception:
            pass
    return ""


def resolve_back_art():
    # The collection convention is back.jpg next to the music. Prefer that
    # exact album-local file; Kodi artwork remains a fallback.
    return (
        _folder_back_art()
        or xbmc.getInfoLabel("Player.Art(album.back)")
        or xbmc.getInfoLabel("Player.Art(back)")
        or ""
    )


def sync_back_art():
    art = resolve_back_art()
    home = _home()
    if art:
        home.setProperty(BACK_PROP, art)
    else:
        home.clearProperty(BACK_PROP)
    return art


def clear_back_art():
    _home().clearProperty(BACK_PROP)


def main():
    # Confluence Custom 5.0.124: the focused artwork has exactly three user
    # states: front, front+back, and no cover. If no back artwork exists, the
    # unavailable pair state is skipped, so Enter still toggles front <-> none.
    has_back = bool(sync_back_art())
    mode = (xbmc.getInfoLabel("Skin.String({})".format(SETTING)) or "front").strip().lower()
    if mode == "front":
        new_mode = "both" if has_back else "none"
    elif mode == "both":
        new_mode = "none"
    else:
        # Also normalizes the legacy back-only state from older versions.
        new_mode = "front"
    xbmc.executebuiltin("Skin.SetString({},{})".format(SETTING, new_mode))


if __name__ == "__main__":
    main()
