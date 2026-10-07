# -*- coding: utf-8 -*-
from __future__ import absolute_import

import math
import struct
import sys
import urllib.parse

import xbmc
import xbmcgui
import xbmcvfs

from worker_lock import WorkerLock

SETTING = "CCMusicArtworkMode"
HOME_ID = 10000
BACK_PROP = "ConfluenceCustom.MusicBackArt"
COMPACT_WIDTH_PROP = "ConfluenceCustom.NowPlaying.CompactCoverWidth"
INFO_FRONT_WIDTH_PROP = "ConfluenceCustom.NowPlaying.InfoFrontWidth"
INFO_BACK_WIDTH_PROP = "ConfluenceCustom.NowPlaying.InfoBackWidth"
INFO_BACK_SHIFT_PROP = "ConfluenceCustom.NowPlaying.InfoBackShift"
INFO_TEXT_SHIFT_PROP = "ConfluenceCustom.NowPlaying.InfoTextShift"
INFO_MARGIN_SETTING = "CCHomeMusicViewMargin"
INFO_MARGIN_DEFAULT = 10
INFO_DEFAULT_HEIGHT = 322
INFO_MAX_IMAGE_WIDTH = 1800
COVER_SIZE_SETTING = "CCHomeMusicCoverSize"
COVER_DYNAMIC_SETTING = "CCHomeMusicCoverDynamic"
INFO_COVER_SIZE_SETTING = "CCHomeMusicInfoCoverSize"
INFO_DYNAMIC_SETTING = "CCHomeMusicInfoCoverDynamic"
ABOVE_MENU_SETTING = "CCHomeMusicDisplayAboveMenu"
COVER_SIZE_STEP = 25
CENTER_COVER_SIZE_MIN = 300
INFO_COVER_SIZE_MIN = 115
INFO_TEXT_BASE_WIDTH = 1830
INFO_TEXT_MIN_WIDTH = 240
INFO_SINGLE_FRONT_ID = 9480
INFO_PAIR_FRONT_ID = 9481
INFO_PAIR_BACK_ID = 9482
INFO_TEXT_CONTROL_IDS = tuple(range(9500, 9512)) + (9140, 9141, 9104)
INFO_TEXT_WIDTH_PROP = "ConfluenceCustom.NowPlaying.InfoTextWidth"
INFO_DYNAMIC_GEOMETRY_PROP = "ConfluenceCustom.NowPlaying.InfoDynamicGeometry"
CENTER_COVER_RUNTIME_PROP = "ConfluenceCustom.NowPlaying.CenterCoverSize"
INFO_COVER_RUNTIME_PROP = "ConfluenceCustom.NowPlaying.InfoCoverSize"
RESIZE_LOCK_NAME = "music-view-resize"
RESIZE_LOCK_ATTEMPTS = 200
RESIZE_LOCK_SLEEP_MS = 10
COMPACT_HEIGHT = 115
COMPACT_WIDTH_STEP = 10
COMPACT_WIDTH_MIN = 30
COMPACT_WIDTH_MAX = 800
COMPACT_WIDTH_FALLBACK = 120
_COMPACT_WIDTH_CACHE = {}
_ART_RATIO_CACHE = {}


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


def _image_candidates(art):
    value = str(art or "").strip()
    if not value:
        return []
    candidates = [value]
    if value.lower().startswith("image://"):
        payload = urllib.parse.unquote(value[8:])
        candidates.extend([payload, payload.rstrip("/")])
    else:
        decoded = urllib.parse.unquote(value)
        if decoded != value:
            candidates.append(decoded)
    result = []
    for candidate in candidates:
        if candidate and candidate not in result:
            result.append(candidate)
    return result


def _read_image_header(path, limit=262144):
    handle = None
    try:
        handle = xbmcvfs.File(path)
        data = handle.readBytes(int(limit))
        if isinstance(data, str):
            data = data.encode("latin1", "ignore")
        return bytes(data or b"")
    except Exception:
        return b""
    finally:
        if handle is not None:
            try:
                handle.close()
            except Exception:
                pass


def _jpeg_size(data):
    if len(data) < 4 or data[:2] != b"\xff\xd8":
        return None
    sof = {
        0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
        0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF,
    }
    pos = 2
    length = len(data)
    while pos + 4 <= length:
        while pos < length and data[pos] != 0xFF:
            pos += 1
        while pos < length and data[pos] == 0xFF:
            pos += 1
        if pos >= length:
            break
        marker = data[pos]
        pos += 1
        if marker in (0xD8, 0xD9):
            continue
        if marker == 0xDA:
            break
        if pos + 2 > length:
            break
        seglen = struct.unpack(">H", data[pos:pos + 2])[0]
        if seglen < 2 or pos + seglen > length:
            break
        if marker in sof and seglen >= 7:
            height = struct.unpack(">H", data[pos + 3:pos + 5])[0]
            width = struct.unpack(">H", data[pos + 5:pos + 7])[0]
            return (width, height) if width and height else None
        pos += seglen
    return None


def _image_size(data):
    if len(data) >= 24 and data[:8] == b"\x89PNG\r\n\x1a\n":
        width, height = struct.unpack(">II", data[16:24])
        return (width, height) if width and height else None
    if len(data) >= 10 and data[:6] in (b"GIF87a", b"GIF89a"):
        width, height = struct.unpack("<HH", data[6:10])
        return (width, height) if width and height else None
    if len(data) >= 26 and data[:2] == b"BM":
        width, height = struct.unpack("<ii", data[18:26])
        width, height = abs(width), abs(height)
        return (width, height) if width and height else None
    jpeg = _jpeg_size(data)
    if jpeg:
        return jpeg
    if len(data) >= 30 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        chunk = data[12:16]
        if chunk == b"VP8X" and len(data) >= 30:
            width = 1 + int.from_bytes(data[24:27], "little")
            height = 1 + int.from_bytes(data[27:30], "little")
            return (width, height) if width and height else None
        if chunk == b"VP8L" and len(data) >= 25 and data[20] == 0x2F:
            bits = int.from_bytes(data[21:25], "little")
            width = (bits & 0x3FFF) + 1
            height = ((bits >> 14) & 0x3FFF) + 1
            return (width, height) if width and height else None
        if chunk == b"VP8 " and len(data) >= 30:
            marker = data.find(b"\x9d\x01\x2a", 20, min(len(data), 80))
            if marker >= 0 and marker + 7 <= len(data):
                width = struct.unpack("<H", data[marker + 3:marker + 5])[0] & 0x3FFF
                height = struct.unpack("<H", data[marker + 5:marker + 7])[0] & 0x3FFF
                return (width, height) if width and height else None
    return None


def _art_ratio(art):
    """Return image width/height, cached from the existing lightweight header reader."""
    cache_key = str(art or "")
    if not cache_key:
        return 1.0
    if cache_key in _ART_RATIO_CACHE:
        return _ART_RATIO_CACHE[cache_key]

    ratio = 1.0
    for path in _image_candidates(art):
        size = _image_size(_read_image_header(path))
        if size:
            width, height = size
            if width and height:
                ratio = float(width) / float(height)
            break

    if len(_ART_RATIO_CACHE) >= 128:
        try:
            _ART_RATIO_CACHE.pop(next(iter(_ART_RATIO_CACHE)))
        except Exception:
            _ART_RATIO_CACHE.clear()
    _ART_RATIO_CACHE[cache_key] = ratio
    return ratio


def music_view_margin():
    try:
        value = int((xbmc.getInfoLabel("Skin.String({})".format(INFO_MARGIN_SETTING)) or str(INFO_MARGIN_DEFAULT)).strip())
    except Exception:
        value = INFO_MARGIN_DEFAULT
    return max(0, min(60, value))


def _info_cover_height():
    """Free height between submenu and screen edge using one shared margin."""
    try:
        offset = int((xbmc.getInfoLabel("Skin.String(CCMainMenuYOffset)") or "0").strip())
    except Exception:
        offset = 0
    margin = music_view_margin()
    return max(2, int(INFO_DEFAULT_HEIGHT - offset - (2 * margin)))


def _info_art_width(art, height):
    # Width is measured independently for every artwork from its own aspect
    # ratio. Front and back may therefore differ. Do not impose a square-cover
    # assumption: landscape artwork can legitimately be wider than its height.
    width = int(round(_art_ratio(art) * float(height)))
    return max(1, min(width, INFO_MAX_IMAGE_WIDTH))


def _info_cover_max_height(mode, front_art, back_art, margin):
    """Largest info-side cover height that still leaves usable music-info width."""
    pair = mode == "infoboth" and bool(back_art)
    ratio = max(0.01, _art_ratio(front_art))
    margin_cost = 2 * int(margin)
    if pair:
        ratio += max(0.01, _art_ratio(back_art))
        margin_cost = 3 * int(margin)
    available_art_width = INFO_TEXT_BASE_WIDTH - INFO_TEXT_MIN_WIDTH + 30 - margin_cost
    maximum = int(math.floor(max(1, available_art_width) / max(0.01, ratio)))
    return max(INFO_COVER_SIZE_MIN, maximum)


def _runtime_size(home, prop, setting, default):
    try:
        raw = home.getProperty(prop) or ""
        if raw:
            return int(raw)
    except Exception:
        pass
    return _skin_int(setting, default)


def _set_runtime_size(home, prop, setting, value):
    value = int(value)
    home.setProperty(prop, str(value))
    _set_skin_string(setting, value)


def _set_shift_digits(home, base, value):
    value = max(0, min(1999, int(value)))
    digits = (
        ("Thousands", value // 1000),
        ("Hundreds", (value // 100) % 10),
        ("Tens", (value // 10) % 10),
        ("Ones", value % 10),
    )
    for suffix, digit in digits:
        home.setProperty(base + suffix, str(digit))


def _skin_string(name, default=""):
    value = xbmc.getInfoLabel("Skin.String({})".format(name))
    return value if value else default


def _skin_int(name, default):
    try:
        return int(_skin_string(name, str(default)))
    except (TypeError, ValueError):
        return int(default)


def _set_skin_string(name, value):
    xbmc.executebuiltin("Skin.SetString({},{})".format(name, int(value)))


def _set_skin_bool(name):
    xbmc.executebuiltin("Skin.SetBool({})".format(name))


def _has_setting(name):
    return xbmc.getCondVisibility("Skin.HasSetting({})".format(name))


def _current_mode():
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
    try:
        return home.getControl(int(control_id))
    except Exception:
        return None


def _set_geometry(control, x, y, width, height):
    if control is None:
        return False
    try:
        control.setPosition(int(x), int(y))
        control.setWidth(max(1, int(width)))
        control.setHeight(max(1, int(height)))
        return True
    except Exception:
        return False


def _set_info_text_width(home, width):
    width = max(INFO_TEXT_MIN_WIDTH, min(INFO_TEXT_BASE_WIDTH, int(width)))
    cached = home.getProperty(INFO_TEXT_WIDTH_PROP) or ""
    if cached == str(width):
        return True
    changed = 0
    for control_id in INFO_TEXT_CONTROL_IDS:
        control = _home_control(home, control_id)
        if control is not None:
            try:
                control.setWidth(width)
                changed += 1
            except Exception:
                pass
    if changed == len(INFO_TEXT_CONTROL_IDS):
        home.setProperty(INFO_TEXT_WIDTH_PROP, str(width))
        return True
    home.clearProperty(INFO_TEXT_WIDTH_PROP)
    return False


def _apply_dynamic_info_art(home, mode, height, front_width, back_width, margin, back_art):
    key = "{}|{}|{}|{}|{}|{}".format(mode, int(height), int(front_width), int(back_width), int(margin), 1 if back_art else 0)
    if home.getProperty(INFO_DYNAMIC_GEOMETRY_PROP) == key:
        return True
    top = 115 - int(height)
    if mode == "infoboth" and back_art:
        ok_front = _set_geometry(_home_control(home, INFO_PAIR_FRONT_ID), -20, top, INFO_MAX_IMAGE_WIDTH, height)
        ok_back = _set_geometry(_home_control(home, INFO_PAIR_BACK_ID), -20 + front_width + margin, top, INFO_MAX_IMAGE_WIDTH, height)
        ok = ok_front and ok_back
    else:
        ok = _set_geometry(_home_control(home, INFO_SINGLE_FRONT_ID), -20, top, INFO_MAX_IMAGE_WIDTH, height)
    if ok:
        home.setProperty(INFO_DYNAMIC_GEOMETRY_PROP, key)
    else:
        home.clearProperty(INFO_DYNAMIC_GEOMETRY_PROP)
    return ok


def sync_info_cover_geometry(mode=None):
    """Publish artwork geometry and keep the footer text edge aligned.

    Static below-menu geometry remains untouched. Above the menu, a resized
    info-side cover uses one authoritative runtime height so the background
    service and key actions cannot bounce between stale Skin.String values.
    """
    home = _home()
    mode = (mode or _current_mode()).strip().lower()
    natural_height = _info_cover_height()
    front_art = xbmc.getInfoLabel("Player.Art(thumb)") or ""
    back_art = home.getProperty(BACK_PROP) or ""
    margin = music_view_margin()
    dynamic_info = (
        _has_setting(INFO_DYNAMIC_SETTING)
        and _has_setting(ABOVE_MENU_SETTING)
        and mode in ("infofront", "infoboth")
    )
    if dynamic_info:
        requested = _runtime_size(home, INFO_COVER_RUNTIME_PROP, INFO_COVER_SIZE_SETTING, natural_height)
        requested = max(INFO_COVER_SIZE_MIN, int(requested))
        maximum = _info_cover_max_height(mode, front_art, back_art, margin)
        height = min(maximum, requested)
        home.setProperty(INFO_COVER_RUNTIME_PROP, str(height))
    else:
        height = natural_height

    front_width = _info_art_width(front_art, height)
    back_width = _info_art_width(back_art, height) if back_art else 0

    single_shift = max(0, front_width + (2 * margin) - 30)
    pair_shift = max(0, front_width + back_width + (3 * margin) - 30)
    back_shift = max(0, front_width + margin)

    if mode == "infofront":
        text_shift = single_shift
    elif mode == "infoboth":
        text_shift = pair_shift if back_art else single_shift
    elif mode == "compact":
        try:
            compact_width = int(home.getProperty(COMPACT_WIDTH_PROP) or COMPACT_WIDTH_FALLBACK)
        except Exception:
            compact_width = COMPACT_WIDTH_FALLBACK
        text_shift = max(0, compact_width + (2 * margin) - 30)
    else:
        text_shift = 0

    home.setProperty(INFO_FRONT_WIDTH_PROP, str(front_width))
    if back_art:
        home.setProperty(INFO_BACK_WIDTH_PROP, str(back_width))
    else:
        home.clearProperty(INFO_BACK_WIDTH_PROP)
    home.setProperty(INFO_BACK_SHIFT_PROP, str(back_shift))
    home.setProperty(INFO_TEXT_SHIFT_PROP, str(text_shift))
    _set_shift_digits(home, INFO_BACK_SHIFT_PROP, back_shift)
    _set_shift_digits(home, INFO_TEXT_SHIFT_PROP, text_shift)

    if dynamic_info:
        _apply_dynamic_info_art(home, mode, height, front_width, back_width, margin, back_art)
        _set_info_text_width(home, max(INFO_TEXT_MIN_WIDTH, INFO_TEXT_BASE_WIDTH - text_shift))
    else:
        home.clearProperty(INFO_DYNAMIC_GEOMETRY_PROP)
        _set_info_text_width(home, INFO_TEXT_BASE_WIDTH)
    return text_shift

def compact_cover_width(art=None):
    art = art or xbmc.getInfoLabel("Player.Art(thumb)") or ""
    cache_key = str(art or "")
    if cache_key in _COMPACT_WIDTH_CACHE:
        return _COMPACT_WIDTH_CACHE[cache_key]

    size = None
    for path in _image_candidates(art):
        size = _image_size(_read_image_header(path))
        if size:
            break

    if not size:
        result = COMPACT_WIDTH_FALLBACK
        _COMPACT_WIDTH_CACHE[cache_key] = result
        return result

    width, height = size
    target = (float(width) / float(height)) * COMPACT_HEIGHT
    result = int(math.ceil(target / COMPACT_WIDTH_STEP) * COMPACT_WIDTH_STEP)
    result = max(COMPACT_WIDTH_MIN, min(COMPACT_WIDTH_MAX, result))

    if len(_COMPACT_WIDTH_CACHE) >= 128:
        try:
            _COMPACT_WIDTH_CACHE.pop(next(iter(_COMPACT_WIDTH_CACHE)))
        except Exception:
            _COMPACT_WIDTH_CACHE.clear()
    _COMPACT_WIDTH_CACHE[cache_key] = result
    return result


def sync_compact_cover_width():
    width = compact_cover_width()
    _home().setProperty(COMPACT_WIDTH_PROP, str(width))
    return width


def clear_back_art():
    home = _home()
    home.clearProperty(BACK_PROP)
    home.clearProperty(COMPACT_WIDTH_PROP)
    for prop in (
        INFO_FRONT_WIDTH_PROP, INFO_BACK_WIDTH_PROP, INFO_BACK_SHIFT_PROP, INFO_TEXT_SHIFT_PROP,
    ):
        home.clearProperty(prop)
    for base in (INFO_BACK_SHIFT_PROP, INFO_TEXT_SHIFT_PROP):
        for suffix in ("Thousands", "Hundreds", "Tens", "Ones"):
            home.clearProperty(base + suffix)


def _resize_cover_locked(direction, mode):
    home = _home()
    sync_back_art()
    delta = COVER_SIZE_STEP if direction > 0 else -COVER_SIZE_STEP

    if mode in ("front", "both"):
        raw = _runtime_size(home, CENTER_COVER_RUNTIME_PROP, COVER_SIZE_SETTING, CENTER_COVER_SIZE_MIN)
        if raw < CENTER_COVER_SIZE_MIN:
            value = CENTER_COVER_SIZE_MIN
        else:
            value = max(CENTER_COVER_SIZE_MIN, int(raw) + delta)
        if value == raw and _has_setting(COVER_DYNAMIC_SETTING):
            return
        _set_runtime_size(home, CENTER_COVER_RUNTIME_PROP, COVER_SIZE_SETTING, value)
        _set_skin_bool(COVER_DYNAMIC_SETTING)
        try:
            from live_home_adjust import apply_dynamic_cover
            apply_dynamic_cover(value)
        except Exception:
            pass
        return

    if mode in ("infofront", "infoboth") and _has_setting(ABOVE_MENU_SETTING):
        natural = _info_cover_height()
        front_art = xbmc.getInfoLabel("Player.Art(thumb)") or ""
        back_art = home.getProperty(BACK_PROP) or ""
        margin = music_view_margin()
        maximum = _info_cover_max_height(mode, front_art, back_art, margin)
        if _has_setting(INFO_DYNAMIC_SETTING):
            raw = _runtime_size(home, INFO_COVER_RUNTIME_PROP, INFO_COVER_SIZE_SETTING, natural)
        else:
            raw = natural
        current = max(INFO_COVER_SIZE_MIN, min(maximum, int(raw)))
        if raw != current:
            value = current
        else:
            value = max(INFO_COVER_SIZE_MIN, min(maximum, current + delta))
        if value == raw and _has_setting(INFO_DYNAMIC_SETTING):
            return
        _set_runtime_size(home, INFO_COVER_RUNTIME_PROP, INFO_COVER_SIZE_SETTING, value)
        _set_skin_bool(INFO_DYNAMIC_SETTING)
        home.clearProperty(INFO_DYNAMIC_GEOMETRY_PROP)
        sync_info_cover_geometry(mode)


def _resize_cover(direction):
    # Every key repeat starts a separate RunScript instance. Serialize those
    # instances so each step reads the size written by the previous step rather
    # than racing on a stale Skin.String value.
    requested_mode = _current_mode()
    lock = None
    for _ in range(RESIZE_LOCK_ATTEMPTS):
        candidate = WorkerLock(RESIZE_LOCK_NAME)
        if candidate.acquire():
            lock = candidate
            break
        xbmc.sleep(RESIZE_LOCK_SLEEP_MS)
    if lock is None:
        return
    try:
        # A delayed key repeat must never resize a view the user has already left.
        if _current_mode() != requested_mode:
            return
        _resize_cover_locked(direction, requested_mode)
    finally:
        lock.release()

def _cycle_view():
    # Proven 5.0.170 order: centered front -> centered front+back -> large
    # front beside info -> large front+back beside info -> compact -> none.
    has_back = bool(sync_back_art())
    sync_compact_cover_width()
    mode = _current_mode()
    if mode == "front":
        new_mode = "both" if has_back else "infofront"
    elif mode == "both":
        new_mode = "infofront"
    elif mode == "infofront":
        new_mode = "infoboth" if has_back else "compact"
    elif mode == "infoboth":
        new_mode = "compact"
    elif mode == "compact":
        new_mode = "none"
    else:
        new_mode = "front"
    xbmc.executebuiltin("Skin.SetString({},{})".format(SETTING, new_mode))
    sync_info_cover_geometry(mode=new_mode)


def main(action="change"):
    action = (action or "change").strip().lower()
    if action == "smaller":
        _resize_cover(-1)
    elif action == "larger":
        _resize_cover(1)
    elif action == "apply":
        sync_back_art()
        sync_compact_cover_width()
        sync_info_cover_geometry()
    else:
        _cycle_view()


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "change")
