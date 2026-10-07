# -*- coding: utf-8 -*-
from pathlib import Path

ROOT = Path("skin.confluence.custom")


def replace_once(path, old, new, label):
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit("{}: expected block not found in {}".format(label, path))
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def replace_between(path, start_marker, end_marker, new_block, label):
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    start = text.find(start_marker)
    if start < 0:
        raise SystemExit("{}: start marker not found in {}".format(label, path))
    end = text.find(end_marker, start)
    if end < 0:
        raise SystemExit("{}: end marker not found in {}".format(label, path))
    path.write_text(text[:start] + new_block + text[end:], encoding="utf-8")


addon = ROOT / "addon.xml"
addon_text = addon.read_text(encoding="utf-8")
if 'version="5.0.192"' in addon_text:
    print("5.0.192 already applied")
    raise SystemExit(0)
if 'version="5.0.191"' not in addon_text:
    raise SystemExit("Unexpected source version; expected 5.0.191")

replace_once(
    addon,
    'version="5.0.191"',
    'version="5.0.192"',
    "version bump",
)
replace_once(
    addon,
    '<news>5.0.191: Preserve the immediate Stop fix, suppress unsupported glyphs in Song Popup credits, and keep explicit song selection focused without redundant follow-up UI actions.</news>',
    '<news>5.0.192: Keep artwork state stable across window changes and scans, skip unavailable back-cover modes only on mode/title change, tighten large front/back spacing for non-square artwork, and retain the 5.0.191 Song Popup fixes.</news>',
    "news",
)

home = ROOT / "1080p" / "Home.xml"
replace_once(
    home,
    '\t<onload condition="Skin.HasSetting(CCHomeMusicCoverDynamic)">RunScript(special://skin/resources/lib/live_home_adjust.py,apply)</onload>\n',
    "",
    "remove centered-cover Home reload",
)
replace_once(
    home,
    '\t<onload condition="Skin.HasSetting(CCHomeMusicInfoCoverDynamic)">RunScript(special://skin/resources/lib/cover_display_action.py,apply)</onload>\n',
    "",
    "remove info-cover Home reload",
)

geometry = ROOT / "resources" / "lib" / "home_geometry_action.py"
geometry.write_text(
    '''# -*- coding: utf-8 -*-
"""Foreground/event action for Home music artwork geometry.

The persistent Now Playing worker requests this action only when the actual
playing artwork or relevant skin settings change. Returning from another Kodi
window must not rebuild Home artwork geometry by itself.
"""
from __future__ import absolute_import

from cover_display_action import sync_info_cover_geometry
from live_home_adjust import apply_dynamic_cover


def main():
    # Centered and info-side geometry are applied together in one short-lived
    # foreground action. Neither operation is tied to Home onload anymore.
    apply_dynamic_cover()
    sync_info_cover_geometry()


if __name__ == "__main__":
    main()
''',
    encoding="utf-8",
)

cover = ROOT / "resources" / "lib" / "cover_display_action.py"
replace_once(
    cover,
    '''def _current_mode():
    return (_skin_string(SETTING, "front") or "front").strip().lower()


def _home_control(home, control_id):
''',
    '''def _current_mode():
    return (_skin_string(SETTING, "front") or "front").strip().lower()


def normalize_artwork_mode_for_back():
    """Skip an unavailable back-cover mode on a real title change only.

    The selected artwork mode is otherwise persistent across window changes,
    scans, Stop and restart. Explicit mode cycling already checks back artwork
    in _cycle_view(); this function provides the corresponding title-change
    check without coupling the mode to transient Home visibility.
    """
    mode = _current_mode()
    if _home().getProperty(BACK_PROP):
        return mode
    fallback = {
        "both": "infofront",
        "infoboth": "compact",
    }.get(mode)
    if fallback:
        xbmc.executebuiltin("Skin.SetString({},{})".format(SETTING, fallback))
        return fallback
    return mode


def _home_control(home, control_id):
''',
    "title-change back mode",
)

live = ROOT / "resources" / "lib" / "live_home_adjust.py"
replace_once(
    live,
    '''import xbmc
import xbmcgui
import xbmcvfs

from worker_lock import WorkerLock
''',
    '''import xbmc
import xbmcgui
import xbmcvfs

from cover_display_action import BACK_PROP, _art_ratio
from worker_lock import WorkerLock
''',
    "live art-ratio import",
)
replace_once(
    live,
    "SOFT_SHADOW_LAYERS = 8\n",
    "SOFT_SHADOW_LAYERS = 8\nPAIR_GAP = 40\n",
    "pair gap",
)
replace_once(
    live,
    '''def _shadow_cover_rect(kind, size):
    selector_y = (600 - size) // 2
    if kind == "main":
        return 30, 495 - size
    if kind == "single":
        return (1920 - size) // 2, selector_y
    if kind == "pair_front":
        return 940 - size, selector_y
    return 980, selector_y
''',
    '''def _pair_cover_rects(size):
    """Place the visible pair, not two square placeholder boxes."""
    size = max(1, int(size))
    home = xbmcgui.Window(HOME_WINDOW_ID)
    front_art = xbmc.getInfoLabel("Player.Art(thumb)") or ""
    back_art = home.getProperty(BACK_PROP) or ""
    front_width = max(1, int(round(_art_ratio(front_art) * float(size))))
    back_width = max(1, int(round(_art_ratio(back_art) * float(size))))
    total_width = front_width + PAIR_GAP + back_width
    front_x = int(round((1920 - total_width) / 2.0))
    back_x = front_x + front_width + PAIR_GAP
    selector_y = (600 - size) // 2
    return (
        (front_x, selector_y, front_width, size),
        (back_x, selector_y, back_width, size),
    )


def _cover_rect(kind, size):
    selector_y = (600 - size) // 2
    if kind == "main":
        return 30, 495 - size, size, size
    if kind == "single":
        return (1920 - size) // 2, selector_y, size, size
    front_rect, back_rect = _pair_cover_rects(size)
    return front_rect if kind == "pair_front" else back_rect
''',
    "pair visible geometry helper",
)
replace_once(
    live,
    '''        cover_x, cover_y = _shadow_cover_rect(kind, size)
        hard = _control(window, hard_id)
        soft = tuple(_control(window, cid) for cid in soft_ids)
        if extent <= 0:
            _hide_shadow_control(hard)
            for control in soft:
                _hide_shadow_control(control)
            continue
        _set_geometry(hard, cover_x + extent, cover_y + extent, size, size)
        for index, control in enumerate(soft):
            if index < len(shifts):
                shift = shifts[index]
                _set_geometry(control, cover_x + shift, cover_y + shift, size, size)
            else:
                _hide_shadow_control(control)
''',
    '''        cover_x, cover_y, cover_width, cover_height = _cover_rect(kind, size)
        hard = _control(window, hard_id)
        soft = tuple(_control(window, cid) for cid in soft_ids)
        if extent <= 0:
            _hide_shadow_control(hard)
            for control in soft:
                _hide_shadow_control(control)
            continue
        _set_geometry(hard, cover_x + extent, cover_y + extent, cover_width, cover_height)
        for index, control in enumerate(soft):
            if index < len(shifts):
                shift = shifts[index]
                _set_geometry(control, cover_x + shift, cover_y + shift, cover_width, cover_height)
            else:
                _hide_shadow_control(control)
''',
    "pair shadow geometry",
)
replace_once(
    live,
    '''    front_x = 940 - size
    back_x = 980
    _set_geometry(_control(window, ID_SELECTOR_PAIR_FRAME_FRONT), front_x, selector_y, size, size)
    _set_geometry(_control(window, ID_SELECTOR_PAIR_FRAME_BACK), back_x, selector_y, size, size)
    _set_geometry(_control(window, ID_SELECTOR_PAIR_SHADOW_FRONT), front_x, selector_y, size, size)
    _set_geometry(_control(window, ID_SELECTOR_PAIR_SHADOW_BACK), back_x, selector_y, size, size)
''',
    '''    front_rect, back_rect = _pair_cover_rects(size)
    _set_geometry(_control(window, ID_SELECTOR_PAIR_FRAME_FRONT), *front_rect)
    _set_geometry(_control(window, ID_SELECTOR_PAIR_FRAME_BACK), *back_rect)
    _set_geometry(_control(window, ID_SELECTOR_PAIR_SHADOW_FRONT), *front_rect)
    _set_geometry(_control(window, ID_SELECTOR_PAIR_SHADOW_BACK), *back_rect)
''',
    "dynamic pair visible width",
)

nowplaying = ROOT / "resources" / "lib" / "nowplaying_service.py"
replace_once(
    nowplaying,
    '''from cover_display_action import (
    BACK_PROP,
    INFO_TEXT_SHIFT_PROP,
    clear_back_art,
    sync_back_art,
    sync_compact_cover_width,
)
''',
    '''from cover_display_action import (
    BACK_PROP,
    INFO_TEXT_SHIFT_PROP,
    normalize_artwork_mode_for_back,
    sync_back_art,
    sync_compact_cover_width,
)
''',
    "nowplaying imports",
)
replace_between(
    nowplaying,
    "def _geometry_signature(home):\n",
    "\n\ndef _request_geometry_sync():\n",
    '''def _geometry_signature(home):
    # Home visibility is deliberately not part of the signature. Home is kept
    # in memory, so Videos/Music/scanners must not invalidate artwork geometry.
    return (
        xbmc.getInfoLabel("Player.FilenameAndPath") or "",
        xbmc.getInfoLabel("Player.Art(thumb)") or "",
        home.getProperty(BACK_PROP) or "",
        _skin_string("CCMusicArtworkMode", "front"),
        _skin_string("CCMainMenuYOffset", "0"),
        _skin_string("CCHomeMusicViewMargin", "10"),
        _skin_string("CCHomeMusicInfoCoverSize", ""),
        bool(xbmc.getCondVisibility("Skin.HasSetting(CCHomeMusicInfoCoverDynamic)")),
        bool(xbmc.getCondVisibility("Skin.HasSetting(CCHomeMusicDisplayAboveMenu)")),
        bool(xbmc.getCondVisibility("Skin.HasSetting(CCStandardConfluence)")),
    )
''',
    "geometry signature",
)
replace_between(
    nowplaying,
    "        if not standard and context:\n",
    "        if monitor.waitForAbort(0.15 if context else 0.50):\n",
    '''        if not standard:
            # Artwork belongs to the playing title, not to the current window.
            # Keep it stable while Videos/Music/scanners are active.
            if audio:
                playing_file = xbmc.getInfoLabel("Player.FilenameAndPath") or ""
                if playing_file and playing_file != last_art_file:
                    sync_back_art()
                    sync_compact_cover_width()
                    normalize_artwork_mode_for_back()
                    last_art_file = playing_file
                    last_geometry_signature = None

                geometry_signature = _geometry_signature(home)
                if (
                    xbmc.getCondVisibility("Window.IsActive(Home)")
                    and geometry_signature != last_geometry_signature
                ):
                    # One foreground action applies centered + info geometry.
                    # Returning to Home with the same title/settings is a no-op.
                    _request_geometry_sync()
                    last_geometry_signature = geometry_signature

            if context:
                count = size()
                playing = current() if count > 0 else -1
                if not meta or count != last_size:
                    meta = playlist_metadata()
                    last_size = count
                if audio:
                    if now - last_time_update >= 0.50:
                        _set_times(home, meta, playing)
                        last_time_update = now
                else:
                    _clear_times(home)
            else:
                _clear_times(home)
                # Playlist metadata can change while another window is open;
                # artwork/mode/geometry intentionally remain untouched.
                last_size = -1
                meta = []
        else:
            _clear_times(home)
            last_size = -1
            meta = []

''',
    "stable artwork runtime",
)

print("Applied Confluence-jjs 5.0.192 source changes")
