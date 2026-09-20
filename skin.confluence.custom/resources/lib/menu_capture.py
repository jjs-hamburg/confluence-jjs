# -*- coding: utf-8 -*-
"""Temporary Kodi context item used by JJS KODI Confluence Custom's universal target picker.

While the editor's capture mode is active this context item copies the selected
ListItem's normal activation target into the pending Confluence menu slot. The
selected item itself is never activated by this script.
"""
from __future__ import absolute_import

import re
import sys

import xbmc
import xbmcaddon
import xbmcgui

from menu_common import MAX_ITEMS, get_items, set_items, set_skin_string

D = xbmcgui.Dialog()
PREFIX = "ConfluenceCustom.MenuCapture."
HOME = 10000


def _home():
    return xbmcgui.Window(HOME)


def _get(name):
    try:
        return _home().getProperty(PREFIX + name) or ""
    except Exception:
        return ""


def _clear():
    win = _home()
    for name in ("Active", "Mode", "Group", "Index"):
        try:
            win.clearProperty(PREFIX + name)
        except Exception:
            pass


def _q(value):
    text = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return '"{}"'.format(text)


def _activate(window, path):
    return "ActivateWindow({},{},return)".format(window, _q(path))


WINDOW_IDS = {
    10000: "Home",
    10001: "Programs",
    10002: "Pictures",
    10003: "FileManager",
    10004: "Settings",
    10025: "Videos",
    10028: "VideoPlaylist",
    10035: "SkinSettings",
    10040: "AddonBrowser",
    10050: "EventLog",
    10060: "FavouritesBrowser",
    10500: "MusicPlaylist",
    10502: "Music",
    10503: "MusicPlaylistEditor",
    10700: "TVChannels",
    10701: "TVRecordings",
    10702: "TVGuide",
    10703: "TVTimers",
    10704: "TVSearch",
    10705: "RadioChannels",
    10706: "RadioRecordings",
    10707: "RadioGuide",
    10708: "RadioTimers",
    10709: "RadioSearch",
    10710: "TVTimerRules",
    10711: "RadioTimerRules",
    10821: "Games",
}

VISIBLE_WINDOWS = [
    "Videos", "Music", "Programs", "Pictures", "AddonBrowser", "FileManager",
    "FavouritesBrowser", "TVChannels", "TVRecordings", "TVGuide", "TVTimers",
    "TVSearch", "TVTimerRules", "RadioChannels", "RadioRecordings", "RadioGuide",
    "RadioTimers", "RadioSearch", "RadioTimerRules", "Games", "Home",
]


def _base_window(path=""):
    p = (path or "").lower()
    if p.startswith(("musicdb://", "library://music/")):
        return "Music"
    if p.startswith(("videodb://", "library://video/")):
        return "Videos"
    if p.startswith("addons://"):
        return "AddonBrowser"

    # A context menu is a dialog over the real container. Window.IsVisible()
    # lets us recover that underlying media window reliably.
    for name in VISIBLE_WINDOWS:
        try:
            if xbmc.getCondVisibility("Window.IsVisible({})".format(name)):
                return name
        except Exception:
            pass
    try:
        wid = xbmcgui.getCurrentWindowId()
    except Exception:
        wid = 0
    return WINDOW_IDS.get(wid, str(wid) if wid else "")


def _listitem():
    return getattr(sys, "listitem", None)


def _path(li):
    values = []
    if li is not None:
        try:
            values.append(li.getPath())
        except Exception:
            pass
        for prop in ("path", "Path", "url", "URL"):
            try:
                values.append(li.getProperty(prop))
            except Exception:
                pass
    for label in ("ListItem.Path", "ListItem.FileNameAndPath"):
        try:
            values.append(xbmc.getInfoLabel(label))
        except Exception:
            pass
    for value in values:
        if value:
            return value
    return ""


def _label(li):
    if li is not None:
        try:
            value = li.getLabel()
            if value:
                return value
        except Exception:
            pass
    return xbmc.getInfoLabel("ListItem.Label") or "Menüpunkt"


def _addon_id_from_uri(path):
    m = re.match(r"^(?:plugin|script|addon)://([^/]+)", path or "", re.I)
    return m.group(1) if m else ""


def _is_addon_id(value):
    if not value or "/" in value or ":" in value or " " in value:
        return False
    try:
        xbmcaddon.Addon(value)
        return True
    except Exception:
        return False


def infer_action(li):
    """Best-effort reconstruction of the selected item's normal left-click target."""
    path = _path(li)
    if xbmc.getCondVisibility("ListItem.IsParentFolder"):
        return "", path, "Übergeordnete '..'-Einträge können nicht übernommen werden."

    try:
        is_folder = bool(xbmc.getCondVisibility("ListItem.IsFolder"))
    except Exception:
        is_folder = False
    try:
        is_playable = bool(xbmc.getCondVisibility("ListItem.IsPlayable"))
    except Exception:
        is_playable = False

    if not path:
        return "", path, (
            "Kodi stellt für diesen Eintrag keinen adressierbaren Pfad bereit. "
            "Solche transienten Dialog-/Aktionszeilen können nicht automatisch übernommen werden."
        )

    lower = path.lower()
    window = _base_window(path)

    # Browsable locations: use the same media window and the item's own path.
    if is_folder or lower.startswith((
        "library://", "videodb://", "musicdb://", "addons://", "sources://",
        "special://", "smb://", "nfs://", "upnp://", "ftp://", "dav://", "davs://",
    )):
        if not window:
            return "", path, "Das zugehörige Kodi-Fenster konnte nicht bestimmt werden."
        return _activate(window, path), path, ""

    if lower.startswith("plugin://"):
        if is_playable:
            return "PlayMedia({})".format(_q(path)), path, ""
        # Non-folder plugin entries execute a plugin route rather than entering it.
        return "RunPlugin({})".format(_q(path)), path, ""

    if lower.startswith("script://"):
        addonid = _addon_id_from_uri(path)
        if addonid:
            return "RunAddon({})".format(addonid), path, ""
        return "RunScript({})".format(_q(path)), path, ""

    if lower.startswith("addon://"):
        addonid = _addon_id_from_uri(path)
        if addonid:
            return "RunAddon({})".format(addonid), path, ""

    if _is_addon_id(path):
        return "RunAddon({})".format(path), path, ""

    # A normal non-folder media/file item behaves like a left click: play/open it.
    return "PlayMedia({})".format(_q(path)), path, ""


def _resume(mode, group, index=-1):
    if mode == "replace":
        args = "resume=item,group={},index={}".format(group, index)
    elif mode == "main":
        args = "resume=group,group={}".format(group)
    else:
        args = "resume=submenu,group={}".format(group)
    # Run after the native context menu has fully disappeared.
    xbmc.sleep(120)
    xbmc.executebuiltin("RunScript(special://skin/resources/lib/menu_editor.py,{})".format(args))


def _cancel():
    mode = _get("Mode")
    group = _get("Group")
    try:
        index = int(_get("Index") or "-1")
    except ValueError:
        index = -1
    _clear()
    D.notification("JJS Confluence Menüeditor", "Zielauswahl abgebrochen", time=1800)
    if group:
        _resume(mode, group, index)


def _take():
    if _get("Active") != "1":
        return
    mode = _get("Mode")
    group = _get("Group")
    try:
        index = int(_get("Index") or "-1")
    except ValueError:
        index = -1

    li = _listitem()
    label = _label(li)
    action, path, error = infer_action(li)
    if not action:
        D.ok("Eintrag kann nicht übernommen werden", error or "Für diesen Eintrag konnte keine Linksklick-Aktion bestimmt werden.")
        return

    if mode == "add":
        items = get_items(group)
        if len(items) >= MAX_ITEMS:
            D.ok("Untermenü voll", "Es sind bereits {} Untermenüpunkte vorhanden.".format(MAX_ITEMS))
            return
        items.append({"label": label, "action": action})
        set_items(group, items)
        resume_index = len(items) - 1
    elif mode == "replace":
        items = get_items(group)
        if index < 0 or index >= len(items):
            D.ok("Menüeditor", "Der ursprüngliche Untermenüpunkt existiert nicht mehr.")
            _clear()
            _resume("submenu", group, -1)
            return
        # Changing a target keeps the user's existing menu label, exactly like
        # the normal editor's "Ziel ändern" function.
        items[index]["action"] = action
        set_items(group, items)
        resume_index = index
    elif mode == "main":
        set_skin_string("CCMain_{}_Action".format(group), action)
        resume_index = -1
    else:
        D.ok("Menüeditor", "Unbekannter Auswahlmodus: {}".format(mode))
        return

    _clear()
    D.notification("JJS Confluence Menüeditor", "Übernommen: {}".format(label), time=1800)
    _resume(mode, group, resume_index)


def run():
    arg = (sys.argv[1] if len(sys.argv) > 1 else "take").strip().lower()
    if arg == "cancel":
        _cancel()
    else:
        _take()


if __name__ == "__main__":
    run()
