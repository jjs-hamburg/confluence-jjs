# -*- coding: utf-8 -*-
"""Readable Confluence menu editor using only Kodi's normal dialogs."""
from __future__ import absolute_import

import os
import re
import sys
import xml.etree.ElementTree as ET

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from menu_common import (
    GROUPS, GROUP_LABEL, MAX_ITEMS, activate_window, addon_details, addon_list,
    all_installed_addons, default_items, directory_items, ensure_initialised,
    favourites, get_items, main_label_key, reset_skin_setting, rpc, set_items,
    set_skin_string, settings_categories, settings_for_category, settings_sections,
    skin_string, log,
)

D = xbmcgui.Dialog()

CAPTURE_PREFIX = "ConfluenceCustom.MenuCapture."


class CaptureModeStarted(Exception):
    pass


def _capture_window():
    return xbmcgui.Window(10000)


def _capture_get(name):
    try:
        return _capture_window().getProperty(CAPTURE_PREFIX + name) or ""
    except Exception:
        return ""


def _capture_set(name, value):
    _capture_window().setProperty(CAPTURE_PREFIX + name, str(value))


def clear_capture_state():
    win = _capture_window()
    for name in ("Active", "Mode", "Group", "Index"):
        try:
            win.clearProperty(CAPTURE_PREFIX + name)
        except Exception:
            pass


def begin_capture(group, mode, index=-1):
    clear_capture_state()
    _capture_set("Active", "1")
    _capture_set("Mode", mode)
    _capture_set("Group", group)
    _capture_set("Index", index)
    D.ok(
        "Ziel in Kodi auswählen",
        "Diese Methode funktioniert bei normalen Kodi-Listen und Add-on-Listen.\n\n"
        "Navigiere bis zu der Ebene, auf der der gewünschte Eintrag sichtbar ist. Dann auf der Shield-Fernbedienung "
        "das Kodi-Kontextmenü (Long-Press/Context-Taste) öffnen und [B]Diesen Eintrag als Menüpunkt übernehmen[/B].\n\n"
        "Hinweis: Skin-Einstellungen und manche Python-Dialoge bestehen aus Controls statt ListItems. Dort kann Kodi die "
        "Linksklick-Aktion nicht an ein Context-Add-on übergeben; dafür bitte die direkten Zielbrowser im Editor verwenden."
    )
    xbmc.executebuiltin("ActivateWindow(Home)")
    raise CaptureModeStarted()


def _args_dict():
    out = {}
    for raw in sys.argv[1:]:
        if "=" in raw:
            k, v = raw.split("=", 1)
            out[k.strip().lower()] = v
    return out


def input_text(heading, current=""):
    try:
        return D.input(heading, defaultt=current, type=xbmcgui.INPUT_ALPHANUM)
    except TypeError:
        return D.input(heading, current, xbmcgui.INPUT_ALPHANUM)


def select(heading, options):
    if not options:
        D.ok(heading, "Keine Einträge verfügbar.")
        return -1
    return D.select(heading, options)


def main_label(group):
    custom = skin_string(main_label_key(group))
    return custom or GROUP_LABEL.get(group, group)


def edit_main_label(group):
    current = skin_string(main_label_key(group)) or GROUP_LABEL[group]
    value = input_text("Hauptmenü umbenennen", current)
    if value and value.strip():
        set_skin_string(main_label_key(group), value.strip())


def reset_main_label(group):
    reset_skin_setting(main_label_key(group))


def action_summary(action):
    if len(action) <= 72:
        return action
    return action[:69] + "..."


def _items_equal(left, right):
    if len(left) != len(right):
        return False
    for a, b in zip(left, right):
        if (a.get("label", ""), a.get("action", "")) != (b.get("label", ""), b.get("action", "")):
            return False
    return True


def set_items_synced(group, items):
    """Write menu settings and wait briefly until Skin.String reflects them.

    Skin.SetString/Skin.Reset can become visible to Skin.String a few UI ticks
    later. Without this, the next Dialog.select may briefly rebuild from the
    previous snapshot (most obvious after deleting an item).
    """
    wanted = list(items)[:MAX_ITEMS]
    set_items(group, wanted)
    for _ in range(20):
        if _items_equal(get_items(group), wanted):
            break
        xbmc.sleep(25)
    return wanted


def edit_item(group, index, items):
    # Work on the caller's in-memory list. Do not re-read Skin.String here:
    # Kodi may expose the previous value for a few UI ticks after Skin.SetString/Reset.
    while True:
        if index >= len(items):
            return items
        item = items[index]
        choices = [
            "Bezeichnung ändern",
            "Ziel ändern",
            "Nach links verschieben",
            "Nach rechts verschieben",
            "Eintrag löschen",
            "Ziel anzeigen: {}".format(action_summary(item.get("action", ""))),
        ]
        choice = select("{} – {}".format(GROUP_LABEL[group], item["label"]), choices)
        if choice < 0:
            return items
        if choice == 0:
            value = input_text("Bezeichnung", item["label"])
            if value and value.strip():
                items[index]["label"] = value.strip()
                set_items(group, items)
        elif choice == 1:
            target = choose_target({"group": group, "mode": "replace", "index": index})
            if target:
                items[index]["action"] = target[1]
                set_items(group, items)
        elif choice == 2:
            if index > 0:
                items[index - 1], items[index] = items[index], items[index - 1]
                set_items(group, items)
                index -= 1
        elif choice == 3:
            if index < len(items) - 1:
                items[index + 1], items[index] = items[index], items[index + 1]
                set_items(group, items)
                index += 1
        elif choice == 4:
            if D.yesno("Eintrag löschen", "'{}' wirklich löschen?".format(item["label"])):
                del items[index]
                set_items(group, items)
                # Returning this list makes the very next Dialog.select use the
                # already-updated data, independent of Skin.String propagation.
                return items
        elif choice == 5:
            D.ok("Kodi-Aktion", item.get("action", ""))


def edit_submenu(group):
    # Keep one authoritative in-memory snapshot for the lifetime of this dialog.
    items = get_items(group)
    while True:
        options = ["{}. {}".format(i + 1, it["label"]) for i, it in enumerate(items)]
        add_index = None
        if len(items) < MAX_ITEMS:
            add_index = len(options)
            options.append("+ Eintrag hinzufügen")
        choice = select("{} – Untermenü ({} von max. {})".format(GROUP_LABEL[group], len(items), MAX_ITEMS), options)
        if choice < 0:
            return
        if add_index is not None and choice == add_index:
            target = choose_target({"group": group, "mode": "add", "index": -1})
            if not target:
                continue
            suggested, action = target
            label = input_text("Bezeichnung des neuen Menüpunktes", suggested)
            if not label or not label.strip():
                continue
            items.append({"label": label.strip(), "action": action})
            set_items(group, items)
        elif choice < len(items):
            items = edit_item(group, choice, items)



def main_action_key(group):
    return "CCMain_{}_Action".format(group)


def edit_main_action(group):
    target = choose_target({"group": group, "mode": "main", "index": -1})
    if target:
        set_skin_string(main_action_key(group), target[1])


def reset_main_action(group):
    reset_skin_setting(main_action_key(group))


def group_editor(group):
    while True:
        custom = skin_string(main_label_key(group))
        submenu_count = len(get_items(group))
        main_action = skin_string(main_action_key(group))
        choices = [
            "Untermenü bearbeiten ({} Einträge)".format(submenu_count),
            "Hauptmenü umbenennen" + (" – {}".format(custom) if custom else ""),
            "Hauptmenü-Ziel ändern" + (" – angepasst" if main_action else ""),
            "Hauptmenüname auf Standard zurücksetzen",
            "Hauptmenü-Ziel auf Standard zurücksetzen",
            "Untermenü auf Confluence-Standard zurücksetzen",
        ]
        choice = select("Menü: {}".format(main_label(group)), choices)
        if choice < 0:
            return
        if choice == 0:
            edit_submenu(group)
        elif choice == 1:
            edit_main_label(group)
        elif choice == 2:
            edit_main_action(group)
        elif choice == 3:
            reset_main_label(group)
        elif choice == 4:
            reset_main_action(group)
        elif choice == 5:
            if D.yesno("Untermenü zurücksetzen", "Die Einträge von '{}' auf den Startzustand zurücksetzen?".format(GROUP_LABEL[group])):
                set_items_synced(group, default_items(group))


def choose_target(capture=None):
    # Bevorzugter universeller Weg: Kodi selbst ist der Browser. Die alten
    # strukturierten Browser bleiben als Fallback für Stellen ohne ListItem-
    # Kontextmenü bzw. für echte kodi.context.item-Aktionen erhalten.
    choices = [
        "In Kodi auswählen (normale Listen / Long-Press)",
        "Confluence Custom",
        "Kodi-Einstellungen durchsuchen",
        "Video-Bibliothek durchsuchen",
        "Musik-Bibliothek durchsuchen",
        "Add-ons durchsuchen",
        "Kodi-Fenster / Dialoge",
        "Favorit",
        "Benutzerdefinierte Kodi-Aktion",
    ]
    c = select("Ziel wählen", choices)
    if c < 0:
        return None
    if c == 0:
        if not capture:
            D.ok("Kodi-Auswahl", "Für diesen Bearbeitungsschritt steht der direkte Kodi-Auswahlmodus nicht zur Verfügung.")
            return None
        begin_capture(capture.get("group", ""), capture.get("mode", ""), capture.get("index", -1))
    if c == 1:
        return choose_confluence_target()
    if c == 2:
        return browse_settings()
    if c == 3:
        return browse_path("library://video/", "Videos", "video", "Video-Bibliothek", "Video-Bibliothek")
    if c == 4:
        return browse_path("library://music/", "Music", "music", "Musik-Bibliothek", "Musik-Bibliothek")
    if c == 5:
        return browse_addons()
    if c == 6:
        return choose_kodi_window()
    if c == 7:
        return choose_favourite()
    if c == 8:
        action = input_text("Kodi-Aktion, z. B. ActivateWindow(Settings)", "")
        if not action or not action.strip():
            return None
        return ("Eigener Eintrag", action.strip())
    return None


def choose_confluence_target():
    targets = [
        ("Confluence Menüeditor öffnen", "RunScript(special://skin/resources/lib/menu_editor.py)"),
        ("Skin konfigurieren", "ActivateWindow(SkinSettings)"),
        ("Kodi Home", "ActivateWindow(Home)"),
    ]
    c = select("Confluence Custom", [x[0] for x in targets])
    return targets[c] if c >= 0 else None


SETTING_WINDOWS = {
    "player": "PlayerSettings",
    "media": "MediaSettings",
    "pvr": "PVRSettings",
    "services": "ServiceSettings",
    "service": "ServiceSettings",
    "games": "GameSettings",
    "game": "GameSettings",
    "interface": "InterfaceSettings",
    "system": "SystemSettings",
}


def setting_window(section_id):
    sid = (section_id or "").lower()
    for token, window in SETTING_WINDOWS.items():
        if token in sid:
            return window
    return "Settings"


def setting_action(setting):
    sid = (setting.get("id") or "").lower()
    data = setting.get("data") or ""
    if "skinsettings" in sid:
        return "ActivateWindow(SkinSettings)"
    if data:
        # SettingAction.data is already a Kodi action/built-in for action settings.
        return data
    return ""


def browse_skin_settings():
    while True:
        options = [
            "[Diesen Punkt übernehmen]  Skin konfigurieren",
            "Confluence Menüeditor  >",
        ]
        c = select("Einstellungen – Benutzeroberfläche – Skin konfigurieren", options)
        if c < 0:
            return None
        if c == 0:
            return ("Skin konfigurieren", "ActivateWindow(SkinSettings)")
        if c == 1:
            d = select("Confluence Menüeditor", [
                "[Diesen Eintrag übernehmen]  Confluence Menüeditor",
                "Zurück",
            ])
            if d == 0:
                return ("Menüeditor", "RunScript(special://skin/resources/lib/menu_editor.py)")
            if d < 0 or d == 1:
                continue


def browse_setting_category(section, category):
    section_id = section.get("id") or ""
    category_id = category.get("id") or ""
    section_label = section.get("label") or section_id
    category_label = category.get("label") or category_id
    window = setting_window(section_id)
    while True:
        settings = settings_for_category(section_id, category_id)
        options = ["[Diesen Bereich übernehmen]  {} – {}".format(section_label, category_label)]
        rows = []
        is_skin_category = "skin" in category_id.lower() or "lookandfeel" in category_id.lower() or "skin" in category_label.lower()
        if is_skin_category:
            options.append("Skin konfigurieren  >")
            rows.append(("skinsettings", None))
        for setting in settings:
            label = setting.get("label") or setting.get("id") or "Einstellung"
            action = setting_action(setting)
            options.append(label + ("  >" if action else ""))
            rows.append(("setting", setting))
        c = select("{} – {}".format(section_label, category_label), options)
        if c < 0:
            return None
        if c == 0:
            return (category_label, "ActivateWindow({})".format(window))
        kind, payload = rows[c - 1]
        if kind == "skinsettings":
            result = browse_skin_settings()
            if result:
                return result
            continue
        action = setting_action(payload)
        if not action:
            D.ok("Kein eigener Einsprungpunkt", "Diese Zeile ist eine einzelne Einstellung, für die Kodi keinen direkt aufrufbaren Dialog/Aktionspunkt meldet.\n\nDu kannst den übergeordneten Bereich übernehmen.")
            continue
        label = payload.get("label") or payload.get("id") or "Einstellung"
        if "skinsettings" in (payload.get("id") or "").lower():
            result = browse_skin_settings()
            if result:
                return result
            continue
        d = select(label, [
            "[Diesen Eintrag übernehmen]  {}".format(label),
            "Zurück",
        ])
        if d == 0:
            return (label, action)


def browse_setting_section(section):
    section_id = section.get("id") or ""
    label = section.get("label") or section_id or "Einstellungen"
    window = setting_window(section_id)
    while True:
        cats = section.get("categories") or settings_categories(section_id)
        options = ["[Diesen Bereich übernehmen]  {}".format(label)]
        options += [(cat.get("label") or cat.get("id") or "Kategorie") for cat in cats]
        c = select("Einstellungen – {}".format(label), options)
        if c < 0:
            return None
        if c == 0:
            return (label, "ActivateWindow({})".format(window))
        result = browse_setting_category(section, cats[c - 1])
        if result:
            return result


def browse_settings():
    sections = settings_sections()
    if not sections:
        return choose_settings_fallback()
    while True:
        options = ["[Diesen Punkt übernehmen]  Einstellungen"]
        options += [(sec.get("label") or sec.get("id") or "Bereich") for sec in sections]
        c = select("Einstellungen", options)
        if c < 0:
            return None
        if c == 0:
            return ("Einstellungen", "ActivateWindow(Settings)")
        result = browse_setting_section(sections[c - 1])
        if result:
            return result


def choose_settings_fallback():
    targets = [
        ("Einstellungen", "ActivateWindow(Settings)"),
        ("Player", "ActivateWindow(PlayerSettings)"),
        ("Medien", "ActivateWindow(MediaSettings)"),
        ("TV / PVR", "ActivateWindow(PVRSettings)"),
        ("Dienste", "ActivateWindow(ServiceSettings)"),
        ("Spiele", "ActivateWindow(GameSettings)"),
        ("Benutzeroberfläche", "ActivateWindow(InterfaceSettings)"),
        ("System", "ActivateWindow(SystemSettings)"),
        ("Skin konfigurieren", "ActivateWindow(SkinSettings)"),
        ("Menüeditor", "RunScript(special://skin/resources/lib/menu_editor.py)"),
    ]
    c = select("Einstellungen", [x[0] for x in targets])
    return targets[c] if c >= 0 else None


def browse_path(root, window, media, heading, root_label):
    stack = [(root, root_label)]
    while stack:
        path, label = stack[-1]
        entries = directory_items(path, media)
        dirs = []
        for entry in entries:
            target = entry.get("file") or ""
            name = entry.get("label") or target
            if not target:
                continue
            if entry.get("filetype") == "directory" or target.endswith("/") or target.startswith(("library://", "videodb://", "musicdb://", "plugin://", "special://", "sources://", "addons://")):
                dirs.append((name, target))
        options = ["[Diesen Punkt übernehmen]  {}".format(label)]
        if len(stack) > 1:
            options.append("[..] Eine Ebene zurück")
        options.extend([name for name, _ in dirs])
        c = select("{} – {}".format(heading, label), options)
        if c < 0:
            if len(stack) > 1:
                stack.pop()
                continue
            return None
        if c == 0:
            return (label, activate_window(window, path, True))
        offset = 1
        if len(stack) > 1:
            if c == 1:
                stack.pop()
                continue
            offset = 2
        idx = c - offset
        if 0 <= idx < len(dirs):
            name, target = dirs[idx]
            stack.append((target, name))
    return None


def addon_id_from_path(path):
    parts = [p for p in (path or "").rstrip("/").split("/") if p]
    for part in reversed(parts):
        if "." not in part:
            continue
        details = addon_details(part)
        if details:
            return part, details
    return "", None


def _get_addons(params):
    params = dict(params or {})
    params.setdefault("enabled", "all")
    params.setdefault("installed", True)
    params.setdefault("properties", ["name", "path", "thumbnail", "version", "enabled", "summary"])
    result = rpc("Addons.GetAddons", params) or {}
    return result.get("addons") or []


def _addon_content_members(content):
    out = {}
    # Program add-ons are frequently normal script add-ons, not plugin sources.
    for atype in ("xbmc.python.pluginsource", "xbmc.python.script"):
        for addon in _get_addons({"type": atype, "content": content}):
            aid = addon.get("addonid") or ""
            if aid:
                out[aid] = addon
    return out


def _addon_categories():
    all_addons = all_installed_addons()
    by_id = dict((a.get("addonid"), a) for a in all_addons if a.get("addonid"))
    content = {
        "video": _addon_content_members("video"),
        "audio": _addon_content_members("audio"),
        "image": _addon_content_members("image"),
        "executable": _addon_content_members("executable"),
    }
    legacy_content = {
        "xbmc.addon.video": "video",
        "xbmc.addon.audio": "audio",
        "xbmc.addon.image": "image",
        "xbmc.addon.executable": "executable",
    }
    for aid, addon in by_id.items():
        atype = addon.get("type") or ""
        key = legacy_content.get(atype)
        if key:
            content[key][aid] = addon
        if atype == "xbmc.python.script":
            content["executable"][aid] = addon
        # Kodi treats plugin sources without <provides> as executable in the UI.
        if atype == "xbmc.python.pluginsource" and not any(aid in content[x] for x in content):
            content["executable"][aid] = addon

    categories = []
    claimed = set()
    for label, key, window, media, browser_path in [
        ("Programm-Add-ons", "executable", "Programs", "files", "addons://sources/executable/"),
        ("Video-Add-ons", "video", "Videos", "video", "addons://sources/video/"),
        ("Musik-Add-ons", "audio", "Music", "music", "addons://sources/audio/"),
        ("Bilder-Add-ons", "image", "Pictures", "pictures", "addons://sources/image/"),
    ]:
        members = sorted(content[key].values(), key=lambda a: (a.get("name") or a.get("addonid") or "").lower())
        if members:
            categories.append({"label": label, "members": members, "window": window, "media": media, "browser_path": browser_path})
            claimed.update(a.get("addonid") for a in members if a.get("addonid"))

    type_groups = [
        ("PVR-Clients", {"xbmc.pvrclient"}),
        ("Informationsanbieter", {"xbmc.metadata.scraper.albums", "xbmc.metadata.scraper.artists", "xbmc.metadata.scraper.movies", "xbmc.metadata.scraper.musicvideos", "xbmc.metadata.scraper.tvshows", "xbmc.metadata.scraper.library"}),
        ("Skins / Erscheinungsbild", {"xbmc.gui.skin", "xbmc.ui.screensaver", "xbmc.player.musicviz", "kodi.resource.images", "kodi.resource.uisounds", "kodi.resource.font"}),
        ("Dienste", {"xbmc.service"}),
        ("Untertitel / Liedtexte / Wetter", {"xbmc.subtitle.module", "xbmc.python.lyrics", "xbmc.python.weather"}),
        ("Kontextmenüs", {"kodi.context.item"}),
        ("InputStream / VFS / Decoder", {"kodi.inputstream", "kodi.vfs", "kodi.audiodecoder", "kodi.imagedecoder", "kodi.audioencoder"}),
        ("Spiele / Controller", {"kodi.addon.game", "kodi.game.controller", "kodi.resource.games"}),
        ("Repositories", {"xbmc.addon.repository"}),
        ("Webinterfaces", {"xbmc.webinterface"}),
        ("Peripherie", {"kodi.peripheral"}),
        ("Sprachen", {"kodi.resource.language"}),
        ("Module / Abhängigkeiten", {"xbmc.python.module", "xbmc.python.library"}),
    ]
    for label, types in type_groups:
        members = sorted([a for a in all_addons if (a.get("type") or "") in types], key=lambda a: (a.get("name") or a.get("addonid") or "").lower())
        if members:
            categories.append({
                "label": label, "members": members, "window": None, "media": "files", "browser_path": None,
                "is_context": label == "Kontextmenüs",
            })
            claimed.update(a.get("addonid") for a in members if a.get("addonid"))

    remaining = sorted([a for a in all_addons if a.get("addonid") not in claimed], key=lambda a: (a.get("name") or a.get("addonid") or "").lower())
    if remaining:
        categories.append({"label": "Sonstige installierte Add-ons", "members": remaining, "window": None, "media": "files", "browser_path": None})
    flat = sorted(all_addons, key=lambda a: (a.get("name") or a.get("addonid") or "").lower())
    if flat:
        categories.append({"label": "Alle installierten Add-ons (A–Z)", "members": flat, "window": None, "media": "files", "browser_path": "addons://user/"})
    return categories


def _plugin_contexts(addonid):
    contexts = []
    for content, label, window, media in [
        ("executable", "Programme", "Programs", "files"),
        ("video", "Video", "Videos", "video"),
        ("audio", "Musik", "Music", "music"),
        ("image", "Bilder", "Pictures", "pictures"),
    ]:
        if addonid in _addon_content_members(content):
            contexts.append((label, window, media))
    return contexts


_ADDON_LABEL_RE = re.compile(r"\$ADDON\[([^\s\]]+)\s+(\d+)\]")
_LOCALIZE_RE = re.compile(r"\$LOCALIZE\[(\d+)\]")


def _resolve_context_label(text, owner_addonid):
    value = (text or "").strip()
    if not value:
        return ""
    if value.isdigit():
        try:
            resolved = xbmcaddon.Addon(owner_addonid).getLocalizedString(int(value))
            if resolved:
                return resolved
        except Exception:
            pass
    def addon_repl(match):
        try:
            return xbmcaddon.Addon(match.group(1)).getLocalizedString(int(match.group(2))) or match.group(0)
        except Exception:
            return match.group(0)
    def localize_repl(match):
        try:
            return xbmc.getLocalizedString(int(match.group(1))) or match.group(0)
        except Exception:
            return match.group(0)
    value = _ADDON_LABEL_RE.sub(addon_repl, value)
    value = _LOCALIZE_RE.sub(localize_repl, value)
    return value


def _builtin_quote(value):
    text = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return '"{}"'.format(text)


def _context_run_action(addonid, library, args=""):
    lib = (library or "").strip().replace("\\", "/")
    if not lib:
        return ""
    if lib.startswith(("special://", "/")) or "://" in lib:
        path = lib
    else:
        path = "special://home/addons/{}/{}".format(addonid, lib.lstrip("/"))
    parts = [_builtin_quote(path)]
    if args:
        # Kodi Matrix+ passes the optional context-item args attribute as one
        # sys.argv entry, so preserve it as one quoted RunScript argument.
        parts.append(_builtin_quote(args))
    return "RunScript({})".format(",".join(parts))


def _context_menu_actions(addonid):
    """Read concrete kodi.context.item entries from the installed addon.xml."""
    try:
        addon_path = xbmcaddon.Addon(addonid).getAddonInfo("path")
    except Exception:
        return []
    addon_xml = os.path.join(addon_path, "addon.xml")
    try:
        addon_xml = xbmcvfs.translatePath(addon_xml)
    except Exception:
        pass
    try:
        root = ET.parse(addon_xml).getroot()
    except Exception as exc:
        log("Context addon.xml parse failed for {} at {}: {}".format(addonid, addon_xml, exc), xbmc.LOGWARNING)
        return []

    result = []

    def walk(node, parents, inherited_library="", inherited_args=""):
        tag = node.tag.rsplit("}", 1)[-1]
        if tag == "menu":
            label_node = next((c for c in list(node) if c.tag.rsplit("}", 1)[-1] == "label"), None)
            raw = label_node.text if label_node is not None else ""
            menu_label = _resolve_context_label(raw, addonid)
            # kodi.core.main/manage are attachment points, not visible submenu labels.
            new_parents = parents
            if menu_label:
                new_parents = parents + [menu_label]
            for child in list(node):
                ctag = child.tag.rsplit("}", 1)[-1]
                if ctag in ("menu", "item"):
                    walk(child, new_parents, inherited_library, inherited_args)
            return
        if tag != "item":
            return
        label_node = next((c for c in list(node) if c.tag.rsplit("}", 1)[-1] == "label"), None)
        raw_label = label_node.text if label_node is not None else ""
        label = _resolve_context_label(raw_label, addonid) or os.path.basename(node.get("library") or inherited_library or "Aktion")
        library = node.get("library") or inherited_library
        args = node.get("args") or inherited_args
        action = _context_run_action(addonid, library, args)
        if action:
            result.append({
                "label": label,
                "path": list(parents),
                "action": action,
                "visible": ((next((c.text for c in list(node) if c.tag.rsplit("}", 1)[-1] == "visible"), "") or "").strip()),
            })

    for ext in root.findall(".//extension"):
        if ext.get("point") != "kodi.context.item":
            continue
        inherited_library = ext.get("library") or ""
        inherited_args = ext.get("args") or ""
        for child in list(ext):
            if child.tag.rsplit("}", 1)[-1] in ("menu", "item"):
                walk(child, [], inherited_library, inherited_args)
    return result


def _context_level(actions, path):
    """Return visible child menus and leaf actions for one context-menu level.

    The parser keeps each item's original nested menu path. Build the tree lazily
    so the editor can be navigated exactly like the add-on's context menu instead
    of flattening everything into one technical list. Order follows addon.xml.
    """
    path = list(path or [])
    child_menus = []
    seen = set()
    leaves = []
    plen = len(path)
    for item in actions:
        item_path = list(item.get("path") or [])
        if item_path[:plen] != path:
            continue
        if len(item_path) > plen:
            name = item_path[plen]
            if name not in seen:
                seen.add(name)
                child_menus.append(name)
        elif len(item_path) == plen:
            leaves.append(item)
    return child_menus, leaves


def _take_context_action(item, addon_label):
    """Confirm a concrete leaf only after the user has navigated to it."""
    while True:
        options = [
            "[Diesen Eintrag übernehmen]  {}".format(item["label"]),
            "Kodi-Aktion anzeigen",
        ]
        c = select("{} – {}".format(addon_label, item["label"]), options)
        if c < 0:
            return None
        if c == 0:
            return (item["label"], item["action"])
        D.ok("Kodi-Aktion", item.get("action", ""))


def browse_context_actions(addonid, addon_label):
    actions = _context_menu_actions(addonid)
    if not actions:
        D.ok("Kontextmenü-Aktionen", "Dieses Add-on definiert keine einzeln auslesbaren kodi.context.item-Aktionen.")
        return None

    stack = [[]]
    while stack:
        path = stack[-1]
        child_menus, leaves = _context_level(actions, path)
        options, rows = [], []

        if path:
            options.append("[..] Eine Ebene zurück")
            rows.append(("back", None))

        for name in child_menus:
            options.append(name + "  >")
            rows.append(("menu", name))

        for item in leaves:
            options.append(item["label"] + "  >")
            rows.append(("item", item))

        level_label = " › ".join(path) if path else "Kontextmenü"
        c = select("{} – {}".format(addon_label, level_label), options)
        if c < 0:
            if path:
                stack.pop()
                continue
            return None

        kind, payload = rows[c]
        if kind == "back":
            stack.pop()
            continue
        if kind == "menu":
            stack.append(path + [payload])
            continue
        result = _take_context_action(payload, addon_label)
        if result:
            return result


def browse_addon_entry(addon, category=None):
    aid = addon.get("addonid") or ""
    label = addon.get("name") or aid or "Add-on"
    atype = addon.get("type") or ""
    contexts = _plugin_contexts(aid) if aid else []
    if category and category.get("window") and not any(x[1] == category.get("window") for x in contexts):
        contexts.insert(0, (category.get("label") or "Add-on", category.get("window"), category.get("media") or "files"))
    while True:
        options, rows = [], []
        for ctx_label, window, media in contexts:
            root = "plugin://{}/".format(aid)
            options.append("[Dieses Add-on übernehmen]  {} ({})".format(label, ctx_label))
            rows.append(("take_plugin", (window, media, root)))
            options.append("In '{}' navigieren ({})  >".format(label, ctx_label))
            rows.append(("browse_plugin", (window, media, root)))
        if atype in ("xbmc.python.script", "xbmc.addon.executable"):
            options.append("[Add-on direkt starten übernehmen]  {}".format(label))
            rows.append(("run", None))
        options.append("[Add-on-Einstellungen übernehmen]  {}".format(label))
        rows.append(("settings", None))
        options.append("Zurück")
        rows.append(("back", None))
        c = select("Add-on – {}".format(label), options)
        if c < 0:
            return None
        kind, payload = rows[c]
        if kind == "back":
            return None
        if kind == "run":
            return (label, "RunAddon({})".format(aid))
        if kind == "settings":
            return ("{} – Einstellungen".format(label), "Addon.OpenSettings({})".format(aid))
        window, media, root = payload
        if kind == "take_plugin":
            return (label, activate_window(window, root, True))
        result = browse_path(root, window, media, label, label)
        if result:
            return result


def browse_addons():
    categories = _addon_categories()
    if not categories:
        D.ok("Add-ons", "Keine installierten Add-ons gefunden.")
        return None
    while True:
        c = select("Meine Add-ons – Kategorie wählen", [x["label"] for x in categories])
        if c < 0:
            return None
        category = categories[c]
        options, rows = [], []
        if category.get("browser_path"):
            options.append("[Diese Kategorie übernehmen]  {}".format(category["label"]))
            rows.append(("take_category", None))
        for addon in category.get("members") or []:
            name = addon.get("name") or addon.get("addonid") or "Add-on"
            if addon.get("enabled") is False:
                name += "  [deaktiviert]"
            options.append(name + "  >")
            rows.append(("addon", addon))
        d = select("Add-ons – {}".format(category["label"]), options)
        if d < 0:
            continue
        kind, payload = rows[d]
        if kind == "take_category":
            path = category["browser_path"]
            window = category.get("window")
            return (category["label"], activate_window(window or "AddonBrowser", path, True))
        result = browse_addon_entry(payload, category)
        if result:
            return result


def choose_pvr_target():
    targets = [
        ("TV – Kanäle", "ActivateWindow(TVChannels)"),
        ("TV – Programmführer", "ActivateWindow(TVGuide)"),
        ("TV – Aufnahmen", "ActivateWindow(TVRecordings)"),
        ("TV – Timer", "ActivateWindow(TVTimers)"),
        ("TV – Timerregeln", "ActivateWindow(TVTimerRules)"),
        ("TV – Suche", "ActivateWindow(TVSearch)"),
        ("Radio – Kanäle", "ActivateWindow(RadioChannels)"),
        ("Radio – Programmführer", "ActivateWindow(RadioGuide)"),
        ("Radio – Aufnahmen", "ActivateWindow(RadioRecordings)"),
        ("Radio – Timer", "ActivateWindow(RadioTimers)"),
        ("Radio – Timerregeln", "ActivateWindow(RadioTimerRules)"),
        ("Radio – Suche", "ActivateWindow(RadioSearch)"),
    ]
    c = select("TV / Radio", [x[0] for x in targets])
    return targets[c] if c >= 0 else None


def choose_kodi_window():
    groups = [
        ("Hauptfenster", [
            ("Home", "Home"), ("Programme", "Programs"), ("Bilder", "Pictures"), ("Dateimanager", "FileManager"),
            ("Einstellungen", "Settings"), ("Systeminformationen", "SystemInfo"), ("Bildschirm kalibrieren", "ScreenCalibration"),
            ("Videos", "Videos"), ("Musik", "Music"), ("Profile", "Profiles"), ("Skin konfigurieren", "SkinSettings"),
            ("Add-on-Browser", "AddonBrowser"), ("Ereignisprotokoll", "EventLog"), ("Favoriten", "FavouritesBrowser"),
            ("Wetter", "Weather"), ("Spiele", "Games"),
        ]),
        ("Einstellungsfenster", [
            ("System", "SystemSettings"), ("Dienste", "ServiceSettings"), ("TV / PVR", "PVRSettings"),
            ("Spiele", "GameSettings"), ("Player", "PlayerSettings"), ("Medien", "MediaSettings"),
            ("Benutzeroberfläche", "InterfaceSettings"),
        ]),
        ("TV / Radio", None),
        ("Wiedergabe / Playlists", [
            ("Video-Wiedergabeliste", "VideoPlaylist"), ("Musik-Wiedergabeliste", "MusicPlaylist"),
            ("Musik-Playlisteditor", "MusicPlaylistEditor"), ("Vollbildvideo", "FullscreenVideo"),
            ("Visualisierung", "Visualisation"), ("Diashow", "Slideshow"), ("Video OSD", "VideoOSD"),
            ("Musik OSD", "MusicOSD"), ("Player-Steuerung", "PlayerControls"),
            ("Player-Prozessinfo", "PlayerProcessInfo"), ("Seekbar", "SeekBar"),
        ]),
        ("Dialoge", [
            ("Ja/Nein-Dialog", "YesNoDialog"), ("Fortschrittsdialog", "ProgressDialog"), ("Virtuelle Tastatur", "VirtualKeyboard"),
            ("Lautstärkebalken", "VolumeBar"), ("Untermenü-Dialog", "SubMenu"), ("Kontextmenü", "ContextMenu"),
            ("Benachrichtigung", "Notification"), ("Numerische Eingabe", "NumericInput"), ("Gamepad-Eingabe", "GamepadInput"),
            ("Beenden-Menü", "ShutdownMenu"), ("Visualisierungs-Presets", "VisualisationPresetList"),
            ("Video-OSD-Einstellungen", "OSDVideoSettings"), ("Audio-OSD-Einstellungen", "OSDAudioSettings"),
            ("Video-Lesezeichen", "VideoBookmarks"), ("Dateibrowser", "FileBrowser"), ("Netzwerk einrichten", "NetworkSetup"),
            ("Medienquelle", "MediaSource"), ("Profileinstellungen", "ProfileSettings"), ("Sperreinstellungen", "LockSettings"),
            ("Inhalt festlegen", "ContentSettings"), ("Bibliothek exportieren", "LibExportSettings"),
            ("Song-Information", "SongInformation"), ("Smart-Playlist-Editor", "SmartPlaylistEditor"),
            ("Smart-Playlist-Regel", "SmartPlaylistRule"), ("Bildinformation", "PictureInfo"), ("Add-on-Einstellungen", "AddonSettings"),
            ("Vollbildinformation", "FullscreenInfo"), ("Slider-Dialog", "SliderDialog"), ("Add-on-Information", "AddonInformation"),
            ("Textanzeige", "TextViewer"), ("Peripheriegeräte", "Peripherals"), ("Peripherie-Einstellungen", "PeripheralSettings"),
            ("Erweiterter Fortschritt", "ExtendedProgressDialog"), ("Medienfilter", "MediaFilter"), ("Untertitelsuche", "SubtitleSearch"),
            ("CMS-OSD-Einstellungen", "OSDCMSSettings"), ("Informationsanbieter-Einstellungen", "InfoProviderSettings"),
            ("Untertitel-OSD-Einstellungen", "OSDSubtitleSettings"), ("Musikinformation", "MusicInformation"),
            ("OK-Dialog", "OKDialog"), ("Filminformation", "MovieInformation"), ("Videoversionen verwalten", "ManageVideoVersions"),
            ("Farbauswahl", "DialogColorPicker"), ("Videoversion wählen", "SelectVideoVersion"),
            ("Video-Extra wählen", "SelectVideoExtra"), ("Video-Extras verwalten", "ManageVideoExtras"),
            ("Auswahldialog", "SelectDialog"), ("Busy-Dialog", "BusyDialog"), ("Busy-Dialog ohne Abbruch", "BusyDialogNoCancel"),
            ("PVR-Guide-Information", "PVRGuideInfo"), ("Teletext", "Teletext"),
            ("Game-Stretch-Modus", "GameStretchMode"), ("Game-Lautstärke", "GameVolume"),
            ("Erweiterte Game-Einstellungen", "GameAdvancedSettings"), ("Game-Videodrehung", "GameVideoRotation"),
            ("Game-Ports", "GamePorts"), ("In-Game-Saves", "InGameSaves"), ("Game-Saves", "GameSaves"), ("Game-Agents", "GameAgents"),
        ]),
        ("Confluence Custom", [("Confluence Menüeditor", "__MENUEDITOR__")]),
        ("Fenstername oder ID manuell eingeben", "manual"),
    ]
    while True:
        g = select("Kodi-Fenster / Dialoge", [x[0] for x in groups])
        if g < 0:
            return None
        label, targets = groups[g]
        if label == "TV / Radio":
            result = choose_pvr_target()
            if result:
                return result
            continue
        if targets == "manual":
            window = input_text("Kodi-Fenstername oder numerische Window-ID", "")
            if not window or not window.strip():
                continue
            window = window.strip()
            path = input_text("Optionaler Pfad/Parameter (leer = keiner)", "")
            if path and path.strip():
                return (window, activate_window(window, path.strip(), True))
            return (window, "ActivateWindow({})".format(window))
        c = select(label, [x[0] for x in targets])
        if c < 0:
            continue
        item_label, window = targets[c]
        if window == "__MENUEDITOR__":
            return (item_label, "RunScript(special://skin/resources/lib/menu_editor.py)")
        return (item_label, "ActivateWindow({})".format(window))


def choose_other_window():
    return choose_kodi_window()


def choose_favourite():
    favs = favourites()
    usable = []
    for fav in favs:
        ftype = fav.get("type")
        title = fav.get("title") or "Favorit"
        action = ""
        if ftype == "window" and fav.get("window"):
            param = fav.get("windowparameter") or ""
            if param:
                action = activate_window(fav["window"], param, True)
            else:
                action = "ActivateWindow({})".format(fav["window"])
        elif ftype == "media" and fav.get("path"):
            action = "PlayMedia({})".format(fav["path"])
        elif ftype == "script" and fav.get("path"):
            action = "RunScript({})".format(fav["path"])
        if action:
            usable.append((title, action))
    if not usable:
        D.ok("Favoriten", "Keine verwendbaren Favoriten gefunden.")
        return None
    c = select("Favorit wählen", [x[0] for x in usable])
    return usable[c] if c >= 0 else None


def run():
    if xbmc.getSkinDir() != "skin.confluence.custom":
        D.ok("Confluence Menüeditor", "Der Editor kann nur mit Confluence Custom verwendet werden.")
        return
    ensure_initialised(False)

    args = _args_dict()
    resume = args.get("resume", "")
    resume_group = args.get("group", "")
    try:
        resume_index = int(args.get("index", "-1"))
    except ValueError:
        resume_index = -1

    # If the user manually opens the editor while a capture is still active,
    # make the pending state explicit instead of leaving a hidden context item
    # active indefinitely.
    if _capture_get("Active"):
        c = select("Kodi-Zielauswahl ist noch aktiv", [
            "Weiter in Kodi auswählen",
            "Auswahl abbrechen und Editor öffnen",
        ])
        if c < 0 or c == 0:
            xbmc.executebuiltin("ActivateWindow(Home)")
            return
        clear_capture_state()

    # Return as close as practical to the place from which capture started.
    if resume_group in GROUP_LABEL:
        if resume == "item" and resume_index >= 0:
            items = get_items(resume_group)
            if resume_index < len(items):
                items = edit_item(resume_group, resume_index, items)
            edit_submenu(resume_group)
            group_editor(resume_group)
        elif resume == "submenu":
            edit_submenu(resume_group)
            group_editor(resume_group)
        elif resume == "group":
            group_editor(resume_group)

    while True:
        options = []
        keys = []
        for group, default_label, _ in GROUPS:
            custom = skin_string(main_label_key(group))
            shown = custom or default_label
            options.append("{}   ({} Untermenüpunkte)".format(shown, len(get_items(group))))
            keys.append(group)
        c = select("Confluence Menüeditor", options)
        if c < 0:
            return
        group_editor(keys[c])


if __name__ == "__main__":
    try:
        run()
    except CaptureModeStarted:
        pass
    except Exception as exc:
        log("Editor failed: {}".format(exc), xbmc.LOGERROR)
        D.ok("Confluence Menüeditor", "Fehler im Menüeditor:\n{}".format(exc))
