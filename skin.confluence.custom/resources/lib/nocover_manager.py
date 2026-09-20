# -*- coding: utf-8 -*-
from __future__ import absolute_import

import json
import os

import xbmc
import xbmcvfs

MODE_SETTING = "CCHomeNoCoverStyle"
FREE_PATH_SETTING = "CCNoCoverFreePath"
MODE_KODI = "kodi"
MODE_CUSTOM = "custom"
MODE_FREE = "free"

PROFILE_DIR = "special://profile/addon_data/skin.confluence.custom"
PROFILE_FREE = PROFILE_DIR + "/CCNoCoverUserImage"
PROFILE_FREE_EXT = PROFILE_DIR + "/CCNoCoverUserImage.ext"

# Kodi uses two different built-in music placeholders:
# - DefaultAlbumCover.png for album/cover fallbacks
# - DefaultAudio.png for bare audio files (notably in Music -> Files)
# Both are deliberately removed from the base Textures.xbt so the loose files
# below really become Kodi's global defaults. "Kodi Default" is restored by a
# tiny higher-priority theme bundle containing the two original textures.
SKIN_MEDIA_DIR = "special://skin/media"
ACTIVE_DEFAULTS = (
    SKIN_MEDIA_DIR + "/DefaultAlbumCover.png",
    SKIN_MEDIA_DIR + "/DefaultAudio.png",
)
CUSTOM_DEFAULT = SKIN_MEDIA_DIR + "/CCNoCoverJewelCase.png"
KODI_THEME = "CCNoCoverKodi.xbt"
SKIN_DEFAULT_THEME = "SKINDEFAULT"
THEME_SETTING = "lookandfeel.skintheme"


def _get(name):
    return (xbmc.getInfoLabel("Skin.String({})".format(name)) or "").strip()


def _set(name, value):
    escaped = str(value).replace('\\', '\\\\').replace('"', '\\"')
    xbmc.executebuiltin('Skin.SetString("{}","{}")'.format(name, escaped))


def _mode():
    value = _get(MODE_SETTING).lower()
    if value == "jewelcase":
        return MODE_CUSTOM
    if value == "standard":
        return MODE_KODI
    if value in (MODE_KODI, MODE_CUSTOM, MODE_FREE):
        return value
    return MODE_CUSTOM


def _delete(path):
    try:
        if xbmcvfs.exists(path):
            return bool(xbmcvfs.delete(path))
    except Exception:
        return False
    return True


def _copy(src, dst):
    try:
        _delete(dst)
        return bool(xbmcvfs.copy(src, dst))
    except Exception:
        return False


def _ensure_profile_dir():
    try:
        if not xbmcvfs.exists(PROFILE_DIR):
            xbmcvfs.mkdirs(PROFILE_DIR)
    except Exception:
        pass


def _write_text(path, text):
    try:
        f = xbmcvfs.File(path, 'w')
        f.write(text)
        f.close()
        return True
    except Exception:
        return False


def _read_text(path):
    try:
        if not xbmcvfs.exists(path):
            return ""
        f = xbmcvfs.File(path)
        data = f.read()
        f.close()
        return data or ""
    except Exception:
        return ""


def _free_source_path():
    path = _get(FREE_PATH_SETTING)
    if path and xbmcvfs.exists(path):
        return path
    ext = _read_text(PROFILE_FREE_EXT).strip()
    old = PROFILE_FREE + ext if ext else PROFILE_FREE
    if xbmcvfs.exists(old):
        _set(FREE_PATH_SETTING, old)
        return old
    return ""


def save_free_image(source):
    source = source or ""
    if not source:
        return False
    _ensure_profile_dir()
    clean = source.split('?', 1)[0].split('#', 1)[0]
    ext = os.path.splitext(clean)[1].lower()
    if ext not in ('.png', '.jpg', '.jpeg', '.webp', '.bmp'):
        ext = ''
    for old_ext in ('', '.png', '.jpg', '.jpeg', '.webp', '.bmp'):
        _delete(PROFILE_FREE + old_ext)
    dst = PROFILE_FREE + ext
    if not _copy(source, dst):
        return False
    _write_text(PROFILE_FREE_EXT, ext)
    _set(FREE_PATH_SETTING, dst)
    return True


def _rpc(method, params=None):
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
    }
    if params is not None:
        request["params"] = params
    try:
        raw = xbmc.executeJSONRPC(json.dumps(request))
        result = json.loads(raw or "{}")
        return result
    except Exception as exc:
        xbmc.log("[Confluence Custom] JSON-RPC failed: {}".format(exc), xbmc.LOGWARNING)
        return {"error": {"message": str(exc)}}


def _current_theme():
    result = _rpc("Settings.GetSettingValue", {"setting": THEME_SETTING})
    try:
        return str(result["result"]["value"])
    except Exception:
        return ""


def _set_theme(theme):
    current = _current_theme()
    if current.lower() == str(theme).lower():
        return True
    result = _rpc(
        "Settings.SetSettingValue",
        {"setting": THEME_SETTING, "value": str(theme)},
    )
    if "error" in result:
        xbmc.log(
            "[Confluence Custom] Unable to set skin theme {}: {}".format(theme, result),
            xbmc.LOGWARNING,
        )
        return False
    return True


def _activate_global_default(mode):
    """Make the selected image Kodi's global album AND bare-audio placeholder."""
    if mode == MODE_KODI:
        # The small theme bundle contains Kodi's original DefaultAlbumCover.png
        # and DefaultAudio.png, overriding both loose files globally.
        return _set_theme(KODI_THEME)

    if mode == MODE_FREE:
        source = _free_source_path()
        if not source:
            return False
    else:
        source = CUSTOM_DEFAULT

    # With both names removed from Textures.xbt, these loose files are what
    # Kodi resolves for album fallbacks and bare audio file icons everywhere.
    for target in ACTIVE_DEFAULTS:
        if not _copy(source, target):
            xbmc.log(
                "[Confluence Custom] Unable to replace {}".format(target),
                xbmc.LOGWARNING,
            )
            return False

    # No theme bundle: fall through from the stripped base Textures.xbt to the
    # two loose global music placeholders above.
    return _set_theme(SKIN_DEFAULT_THEME)


def apply(mode=None, reload_skin=False):
    mode = (mode or _mode()).strip().lower()
    if mode == 'jewelcase':
        mode = MODE_CUSTOM
    elif mode == 'standard':
        mode = MODE_KODI
    if mode not in (MODE_KODI, MODE_CUSTOM, MODE_FREE):
        mode = MODE_CUSTOM

    ok = True
    if mode == MODE_FREE and not _free_source_path():
        mode = MODE_CUSTOM
        ok = False

    if not _activate_global_default(mode):
        ok = False

    _set(MODE_SETTING, mode)

    if reload_skin:
        xbmc.executebuiltin('ReloadSkin()')
    return mode, ok


def sync_on_startup():
    try:
        mode = _mode()
        if mode == MODE_FREE and not _free_source_path():
            mode = MODE_CUSTOM
        apply(mode, reload_skin=False)
    except Exception as exc:
        xbmc.log('[Confluence Custom] No-cover sync failed: {}'.format(exc), xbmc.LOGWARNING)
