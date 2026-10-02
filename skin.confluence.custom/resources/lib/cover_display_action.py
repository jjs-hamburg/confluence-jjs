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
COMPACT_HEIGHT = 115
COMPACT_WIDTH_STEP = 10
COMPACT_WIDTH_MIN = 30
COMPACT_WIDTH_MAX = 800
COMPACT_WIDTH_FALLBACK = 120
_COMPACT_WIDTH_CACHE = {}


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


if __name__ == "__main__":
    main()
