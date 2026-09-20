# -*- coding: utf-8 -*-
"""Backup/restore every setting of the active JJS KODI Confluence Custom skin.

The snapshot contains only skin-specific bool/string settings returned by Kodi's
Settings.GetSkinSettings API. General Kodi settings are deliberately untouched.
The destination/source is chosen explicitly through Kodi's file browser so SMB
and other VFS locations can be used.
"""
from __future__ import absolute_import

import json
import os
import sys
import time

import xbmc
import xbmcgui
import xbmcvfs

SKIN_ID = "skin.confluence.custom"
FORMAT = "confluence-custom-skin-settings"
FORMAT_VERSION = 1
DEFAULT_FILENAME = "confluence-custom-settings.json"


def _rpc(method, params=None):
    request = {"jsonrpc": "2.0", "id": 1, "method": method}
    if params is not None:
        request["params"] = params
    raw = xbmc.executeJSONRPC(json.dumps(request, ensure_ascii=False))
    response = json.loads(raw)
    if "error" in response:
        raise RuntimeError("{}: {}".format(method, response.get("error")))
    return response.get("result")


def _skin_snapshot():
    result = _rpc("Settings.GetSkinSettings") or {}
    skin = result.get("skin") or ""
    if skin != SKIN_ID:
        raise RuntimeError("JJS KODI Confluence Custom ist derzeit nicht der aktive Skin.")
    settings = []
    for item in result.get("settings") or []:
        setting_id = str(item.get("id") or "").strip()
        setting_type = item.get("type") or ""
        value = item.get("value")
        if not setting_id or setting_type not in ("boolean", "string"):
            continue
        if setting_type == "boolean":
            value = bool(value)
        else:
            value = "" if value is None else str(value)
        settings.append({"id": setting_id, "type": setting_type, "value": value})
    settings.sort(key=lambda item: item["id"].lower())
    return {
        "format": FORMAT,
        "format_version": FORMAT_VERSION,
        "skin": SKIN_ID,
        "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        "settings": settings,
    }


def _join(folder, filename):
    folder = str(folder or "")
    if folder.endswith(("/", "\\")):
        return folder + filename
    return folder + "/" + filename


def _write_text(path, text):
    fh = xbmcvfs.File(path, "w")
    try:
        written = fh.write(text)
    finally:
        fh.close()
    if not written:
        raise RuntimeError("Die Sicherungsdatei konnte nicht geschrieben werden.")


def _read_text(path):
    fh = xbmcvfs.File(path)
    try:
        raw = fh.read()
    finally:
        fh.close()
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")
    return raw


def _builtin_quote(value):
    text = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return '"{}"'.format(text)


def _reset_setting(setting_id):
    xbmc.executebuiltin("Skin.Reset({})".format(_builtin_quote(setting_id)))


def _fallback_set(item):
    setting_id = item["id"]
    if item["type"] == "boolean":
        if item["value"]:
            xbmc.executebuiltin("Skin.SetBool({})".format(_builtin_quote(setting_id)))
        else:
            _reset_setting(setting_id)
    else:
        xbmc.executebuiltin(
            "Skin.SetString({},{})".format(
                _builtin_quote(setting_id), _builtin_quote(item["value"])
            )
        )


def save_settings():
    dialog = xbmcgui.Dialog()
    folder = dialog.browseSingle(0, "Ordner für Skin-Sicherung wählen", "files")
    if not folder:
        return
    filename = dialog.input("Dateiname", defaultt=DEFAULT_FILENAME, type=xbmcgui.INPUT_ALPHANUM)
    filename = (filename or "").strip()
    if not filename:
        return
    if not filename.lower().endswith(".json"):
        filename += ".json"
    # A file name, not a path, is requested here; keep the chosen directory authoritative.
    filename = filename.replace("/", "_").replace("\\", "_")
    path = _join(folder, filename)
    if xbmcvfs.exists(path) and not dialog.yesno(
        "JJS KODI Confluence Custom", "Die Datei existiert bereits. Überschreiben?", path
    ):
        return
    payload = _skin_snapshot()
    _write_text(path, json.dumps(payload, ensure_ascii=False, indent=2))
    dialog.notification(
        "JJS KODI Confluence Custom", "Skin-Einstellungen gesichert", xbmcgui.NOTIFICATION_INFO, 4000
    )


def _validate_payload(payload):
    if not isinstance(payload, dict):
        raise RuntimeError("Ungültige Sicherungsdatei.")
    if payload.get("format") != FORMAT or int(payload.get("format_version") or 0) != FORMAT_VERSION:
        raise RuntimeError("Die Datei ist keine Confluence-Custom-Sicherung.")
    if payload.get("skin") != SKIN_ID:
        raise RuntimeError("Die Sicherung gehört nicht zu JJS KODI Confluence Custom.")
    settings = payload.get("settings")
    if not isinstance(settings, list):
        raise RuntimeError("Die Sicherungsdatei enthält keine Skin-Einstellungen.")
    result = []
    seen = set()
    for item in settings:
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
    return result


def load_settings():
    dialog = xbmcgui.Dialog()
    path = dialog.browseSingle(1, "Skin-Sicherung auswählen", "files", ".json")
    if not path:
        return
    payload = json.loads(_read_text(path))
    backup = _validate_payload(payload)
    if not dialog.yesno(
        "JJS KODI Confluence Custom",
        "Alle aktuellen Confluence-Custom-Einstellungen werden durch diese Sicherung ersetzt.",
        "Allgemeine Kodi-Einstellungen bleiben unverändert.",
    ):
        return

    current = _skin_snapshot().get("settings") or []
    backup_ids = set(item["id"] for item in backup)

    # First remove values that exist now but were not part of the snapshot.
    # This makes restore a real snapshot restore rather than a merge.
    for item in current:
        if item["id"] not in backup_ids:
            _reset_setting(item["id"])

    errors = []
    for item in backup:
        try:
            _rpc("Settings.SetSkinSettingValue", {
                "setting": item["id"],
                "value": item["value"],
            })
        except Exception:
            # Settings from older/newer revisions can be absent from the current
            # in-memory registry. Built-ins can recreate dynamic skin settings.
            try:
                _fallback_set(item)
            except Exception as exc:
                errors.append("{}: {}".format(item["id"], exc))

    if errors:
        raise RuntimeError(
            "{} Skin-Einstellungen konnten nicht übernommen werden.\n{}".format(
                len(errors), "\n".join(errors[:5])
            )
        )

    dialog.notification(
        "JJS KODI Confluence Custom", "Skin-Einstellungen werden übernommen", xbmcgui.NOTIFICATION_INFO, 3000
    )
    xbmc.sleep(150)
    xbmc.executebuiltin("ReloadSkin()")


def main():
    mode = (sys.argv[1] if len(sys.argv) > 1 else "").strip().lower()
    try:
        if mode == "save":
            save_settings()
        elif mode == "load":
            load_settings()
        else:
            raise RuntimeError("Unbekannte Aktion.")
    except Exception as exc:
        xbmcgui.Dialog().ok("JJS KODI Confluence Custom", str(exc))


if __name__ == "__main__":
    main()
