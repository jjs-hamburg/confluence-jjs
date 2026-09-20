# -*- coding: utf-8 -*-
from __future__ import absolute_import

import hashlib
import os
import sys

import xbmc
import xbmcgui
import xbmcvfs

SETTING = "CCStandardConfluence"
MANAGED = (
    "Font.xml",
    "Home.xml",
    "Includes.xml",
    "IncludesBackgroundBuilding.xml",
    "IncludesHomeMenuItems.xml",
    "SkinSettings.xml",
)


def _native(path):
    return xbmcvfs.translatePath(path)


def _skin_root():
    return _native("special://skin/")


def _source_dir(mode):
    return os.path.join(_skin_root(), "resources", "skin_modes", mode)


def _active_dir():
    return os.path.join(_skin_root(), "1080p")


def _bytes(path):
    with open(path, "rb") as fh:
        return fh.read()


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _desired_mode():
    return "standard" if xbmc.getCondVisibility("Skin.HasSetting({})".format(SETTING)) else "custom"


def _matches(mode):
    src = _source_dir(mode)
    dst = _active_dir()
    try:
        for name in MANAGED:
            a = os.path.join(src, name)
            b = os.path.join(dst, name)
            if not os.path.isfile(a) or not os.path.isfile(b) or _sha(a) != _sha(b):
                return False
        return True
    except Exception:
        return False


def _copy_mode(mode):
    src = _source_dir(mode)
    dst = _active_dir()
    payload = {}
    old = {}
    staged = []
    replaced = []

    for name in MANAGED:
        source = os.path.join(src, name)
        target = os.path.join(dst, name)
        if not os.path.isfile(source):
            raise RuntimeError("Modusdatei fehlt: {}".format(name))
        payload[name] = _bytes(source)
        if os.path.isfile(target):
            old[name] = _bytes(target)

    try:
        for name in MANAGED:
            target = os.path.join(dst, name)
            temp = target + ".ccmode-new"
            with open(temp, "wb") as fh:
                fh.write(payload[name])
                fh.flush()
                try:
                    os.fsync(fh.fileno())
                except Exception:
                    pass
            staged.append(temp)
            if _sha(temp) != hashlib.sha256(payload[name]).hexdigest():
                raise RuntimeError("Prüfung fehlgeschlagen: {}".format(name))

        for name in MANAGED:
            target = os.path.join(dst, name)
            temp = target + ".ccmode-new"
            os.replace(temp, target)
            replaced.append(name)
    except Exception:
        for name in reversed(replaced):
            if name in old:
                target = os.path.join(dst, name)
                temp = target + ".ccmode-rollback"
                try:
                    with open(temp, "wb") as fh:
                        fh.write(old[name])
                    os.replace(temp, target)
                except Exception:
                    pass
        raise
    finally:
        for p in staged:
            try:
                if os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass


def _set_flag(mode):
    if mode == "standard":
        xbmc.executebuiltin("Skin.SetBool({})".format(SETTING))
    else:
        xbmc.executebuiltin("Skin.Reset({})".format(SETTING))


def switch(mode, show_error=True):
    if mode not in ("standard", "custom"):
        return False
    try:
        if not _matches(mode):
            _copy_mode(mode)
        _set_flag(mode)
        xbmc.sleep(100)
        xbmc.executebuiltin("ReloadSkin()")
        return True
    except Exception as exc:
        xbmc.log("JJS KODI Confluence Custom mode switch failed: {}".format(exc), xbmc.LOGERROR)
        if show_error:
            xbmcgui.Dialog().ok("Custom Confluence", "Umschalten fehlgeschlagen:[CR]{}".format(exc))
        return False


def ensure_mode():
    """Repair active XML set after an add-on update. Returns True when reloaded."""
    mode = _desired_mode()
    if _matches(mode):
        return False
    try:
        _copy_mode(mode)
        xbmc.log("JJS KODI Confluence Custom: XML-Satz für Modus {} wiederhergestellt".format(mode), xbmc.LOGINFO)
        xbmc.executebuiltin("ReloadSkin()")
        return True
    except Exception as exc:
        xbmc.log("JJS KODI Confluence Custom ensure mode failed: {}".format(exc), xbmc.LOGERROR)
        return False


def main():
    mode = (sys.argv[1] if len(sys.argv) > 1 else "").strip().lower()
    if mode in ("standard", "custom"):
        switch(mode)
    elif mode == "ensure":
        ensure_mode()


if __name__ == "__main__":
    main()
