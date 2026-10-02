# -*- coding: utf-8 -*-
from __future__ import absolute_import

import math
import struct
import urllib.parse

import xbmc
import xbmcgui
import xbmcvfs

SETTING = "CCMusicArtworkMode"
HOME_ID = 10000
BACK_PROP = "ConfluenceCustom.MusicBackArt"
COMPACT_WIDTH_PROP = "ConfluenceCustom.NowPlaying.CompactCoverWidth"
INFO_FRONT_WIDTH_PROP = "ConfluenceCustom.NowPlaying.InfoFrontWidth"
INFO_BACK_WIDTH_PROP = "ConfluenceCustom.NowPlaying.InfoBackWidth"
INFO_BACK_SHIFT_PROP = "ConfluenceCustom.NowPlaying.InfoBackShift"
INFO_TEXT_SHIFT_PROP = "ConfluenceCustom.NowPlaying.InfoTextShift"
INFO_MARGIN = 10
INFO_DEFAULT_HEIGHT = 302
INFO_MAX_IMAGE_WIDTH = 900
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


def _info_cover_height():
    """Free height between submenu and screen edge with the same 10 px margin top/bottom."""
    try:
        offset = int((xbmc.getInfoLabel("Skin.String(CCMainMenuYOffset)") or "0").strip())
    except Exception:
        offset = 0
    return max(2, int(INFO_DEFAULT_HEIGHT - offset))


def _info_art_width(art, height):
    # The XML image box is height x height with aspectratio=keep. Portrait/longbox
    # artwork therefore uses the full available height and becomes proportionally
    # narrower. Wider artwork is limited by that same box, matching Kodi's render.
    width = int(round(_art_ratio(art) * float(height)))
    return max(1, min(int(height), width, INFO_MAX_IMAGE_WIDTH))


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


def sync_info_cover_geometry(mode=None):
    """Publish exact rendered widths and equal-margin horizontal shifts."""
    home = _home()
    height = _info_cover_height()
    front_art = xbmc.getInfoLabel("Player.Art(thumb)") or ""
    back_art = home.getProperty(BACK_PROP) or ""

    front_width = _info_art_width(front_art, height)
    back_width = _info_art_width(back_art, height) if back_art else 0

    # Parent footer starts at screen x=30, while artwork starts at x=10.
    # With M=10: text after one cover moves by front_width-10; after two
    # covers by front_width+back_width. Back itself moves front_width+10.
    single_shift = max(0, front_width - INFO_MARGIN)
    pair_shift = max(0, front_width + back_width)
    back_shift = max(0, front_width + INFO_MARGIN)

    if mode is None:
        mode = (xbmc.getInfoLabel("Skin.String({})".format(SETTING)) or "front").strip().lower()
    if mode == "infofront":
        text_shift = single_shift
    elif mode == "infoboth":
        text_shift = pair_shift if back_art else single_shift
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


def main():
    # 5.0.170: centered front -> centered front+back -> large front beside
    # info -> large front+back beside info -> compact footer cover -> none.
    # Back-art states are skipped when the current album has no back artwork.
    has_back = bool(sync_back_art())
    sync_compact_cover_width()
    mode = (xbmc.getInfoLabel("Skin.String({})".format(SETTING)) or "front").strip().lower()
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


if __name__ == "__main__":
    main()
