# -*- coding: utf-8 -*-
"""Apply the bundled Confluence Custom snapshot only on a genuine fresh install.

Existing installations must never be overwritten by a later skin update.  The
first startup therefore decides, before any migration/default code runs,
whether this profile already contains Confluence Custom skin settings.  Fresh
installs get a small pending marker so an interrupted first run can safely be
retried.
"""
from __future__ import absolute_import

import json
import os
import xml.etree.ElementTree as ET

import xbmc
import xbmcvfs

SKIN_ID = "skin.confluence.custom"
FORMAT = "confluence-custom-skin-settings"
FORMAT_VERSION = 1
DEFAULTS_FILE = "special://skin/resources/factory-default-settings.json"
STATE_FILE = ".factory-defaults-v1"
PENDING_FILE = ".factory-defaults-v1.pending"


def _log(message, level=xbmc.LOGINFO):
    xbmc.log("[Confluence Custom] {}".format(message), level)


def _profile_dir():
    return xbmcvfs.translatePath("special://profile/addon_data/{}/".format(SKIN_ID))


def _ensure_dir(path):
    if not xbmcvfs.exists(path):
        xbmcvfs.mkdirs(path)


def _path(name):
    base = _profile_dir()
    _ensure_dir(base)
    return os.path.join(base, name)


def _write(path, text):
    fh = xbmcvfs.File(path, "w")
    try:
        fh.write(text)
    finally:
        fh.close()


def _read(path):
    fh = xbmcvfs.File(path)
    try:
        data = fh.read()
    finally:
        fh.close()
    if isinstance(data, bytes):
        data = data.decode("utf-8", errors="replace")
    return data


def _existing_skin_settings():
    """Return True conservatively when this profile already has skin settings."""
    path = _path("settings.xml")
    if not xbmcvfs.exists(path):
        return False
    try:
        root = ET.parse(path).getroot()
        for setting in root.findall("setting"):
            if (setting.get("id") or setting.get("name") or "").strip():
                return True
        return False
    except Exception as exc:
        # Never risk overwriting an existing profile merely because its settings
        # file is temporarily unreadable or from a Kodi variant we did not expect.
        _log("Could not inspect existing skin settings; factory defaults skipped: {}".format(exc), xbmc.LOGWARNING)
        return True


def begin():
    """Capture fresh-install state before any migration/default code changes it."""
    if xbmc.getSkinDir() != SKIN_ID:
        return False
    state = _path(STATE_FILE)
    pending = _path(PENDING_FILE)
    if xbmcvfs.exists(state):
        return False
    if xbmcvfs.exists(pending):
        return True
    if _existing_skin_settings():
        _write(state, "skipped-existing\n")
        _log("Factory defaults not applied: existing Confluence Custom settings found")
        return False
    _write(pending, "fresh-install\n")
    _log("Fresh Confluence Custom install detected; factory defaults scheduled")
    return True


def _rpc(method, params=None):
    request = {"jsonrpc": "2.0", "id": 1, "method": method}
    if params is not None:
        request["params"] = params
    raw = xbmc.executeJSONRPC(json.dumps(request, ensure_ascii=False))
    response = json.loads(raw)
    if "error" in response:
        raise RuntimeError("{}: {}".format(method, response.get("error")))
    return response.get("result")


def _quote(value):
    text = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return '"{}"'.format(text)


def _reset(setting_id):
    xbmc.executebuiltin("Skin.Reset({})".format(_quote(setting_id)))


def _fallback_set(item):
    setting_id = item["id"]
    if item["type"] == "boolean":
        if item["value"]:
            xbmc.executebuiltin("Skin.SetBool({})".format(_quote(setting_id)))
        else:
            _reset(setting_id)
    else:
        xbmc.executebuiltin(
            "Skin.SetString({},{})".format(_quote(setting_id), _quote(item["value"]))
        )


def _load_defaults():
    payload = json.loads(_read(xbmcvfs.translatePath(DEFAULTS_FILE)))
    if not isinstance(payload, dict):
        raise RuntimeError("Ungültige Factory-Defaults-Datei")
    if payload.get("format") != FORMAT or int(payload.get("format_version") or 0) != FORMAT_VERSION:
        raise RuntimeError("Falsches Factory-Defaults-Format")
    if payload.get("skin") != SKIN_ID:
        raise RuntimeError("Factory-Defaults gehören nicht zu Confluence Custom")
    result = []
    seen = set()
    for item in payload.get("settings") or []:
        if not isinstance(item, dict):
            continue
        setting_id = str(item.get("id") or "").strip()
        setting_type = item.get("type") or ""
        if not setting_id or setting_id in seen or setting_type not in ("boolean", "string"):
            continue
        value = item.get("value")
        if setting_type == "boolean":
            value = bool(value)
        else:
            value = "" if value is None else str(value)
        result.append({"id": setting_id, "type": setting_type, "value": value})
        seen.add(setting_id)
    if not result:
        raise RuntimeError("Factory-Defaults enthalten keine Einstellungen")
    return result


def apply():
    """Apply the full snapshot and mark completion. Safe to retry while pending."""
    if xbmc.getSkinDir() != SKIN_ID:
        return False
    pending = _path(PENDING_FILE)
    if not xbmcvfs.exists(pending):
        return False

    defaults = _load_defaults()
    default_ids = set(item["id"] for item in defaults)

    # Original Confluence may have been imported immediately before us. Remove
    # values not present in the supplied snapshot so the result is a real clone,
    # not a merge of two configurations.
    current = (_rpc("Settings.GetSkinSettings") or {}).get("settings") or []
    for item in current:
        setting_id = str(item.get("id") or "").strip()
        if setting_id and setting_id not in default_ids:
            _reset(setting_id)

    errors = []
    for item in defaults:
        try:
            _rpc("Settings.SetSkinSettingValue", {
                "setting": item["id"],
                "value": item["value"],
            })
        except Exception:
            try:
                _fallback_set(item)
            except Exception as exc:
                errors.append("{}: {}".format(item["id"], exc))

    if errors:
        raise RuntimeError(
            "{} Factory-Defaults konnten nicht gesetzt werden: {}".format(
                len(errors), "; ".join(errors[:5])
            )
        )

    try:
        xbmcvfs.delete(pending)
    except Exception:
        pass
    _write(_path(STATE_FILE), "applied\n")
    _log("Applied {} Confluence Custom factory defaults".format(len(defaults)))
    return True
