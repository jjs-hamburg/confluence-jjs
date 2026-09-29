# -*- coding: utf-8 -*-
"""Shared menu storage/defaults for JJS KODI Confluence Custom.

The home skin renders ordinary Confluence buttons. Labels and actions are stored
in skin settings. The editor uses Kodi's standard Dialog.select/input dialogs.
"""
from __future__ import absolute_import

import json

import xbmc
import xbmcgui
import xbmcaddon

TARGET_SKIN = "skin.confluence.custom"
MAX_ITEMS = 6
INIT_SETTING = "CCMenu_Initialized_v3"
MIGRATION_5022 = "CCMenu_Migrated_5_0_22"
MIGRATION_5028 = "CCMenu_Migrated_5_0_28"

GROUPS = [
    ("videos", "Videos", 31953),
    ("movies", "Movies", 31954),
    ("tvshows", "TV shows", 31955),
    ("music", "Music", 31956),
    ("pictures", "Pictures", 31951),
    ("tv", "TV", 31952),
    ("radio", "Radio", 31960),
    ("addons", "Add-ons", 31957),
    ("system", "System", 31959),
]
GROUP_LABEL = dict((g, label) for g, label, _ in GROUPS)
MAIN_LOCALIZE = dict((g, lid) for g, _, lid in GROUPS)

# Visual order of the menu-editor-managed main items in the unmodified 5.0.125
# Home.xml. Weather, Games and Disc keep their fixed Confluence positions; the
# nine managed items can move through the nine managed slots around them.
DEFAULT_MAIN_ORDER = [
    "pictures", "radio", "tv", "videos", "movies",
    "tvshows", "music", "addons", "system",
]
MAIN_ORDER_PREFIX = "CCMainOrder_"

# Fallbacks are used only if a Kodi core localization happens to be empty.
LOC_FALLBACK = {
    5: "Settings", 7: "File manager", 130: "System information",
    137: "Search", 342: "Movies", 744: "Files", 13200: "Profiles",
    14022: "Library", 14111: "Event log", 19019: "Channels",
    19040: "Timers", 19138: "Timer rules", 19163: "Recordings",
    20343: "TV shows", 20389: "Music videos", 22020: "Guide",
    24001: "Add-ons", 24033: "Install from repository",
    24041: "Install from zip file", 24998: "My add-ons",
}


def log(message, level=xbmc.LOGINFO):
    xbmc.log("[JJS KODI Confluence Custom Menu] {}".format(message), level)


def _q(value):
    # Kodi's built-in parser accepts escaped quotes inside quoted parameters.
    # Do NOT replace double quotes with apostrophes: ActivateWindow path
    # parameters require real double quotes when they contain special chars.
    text = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return '"{}"'.format(text)


def skin_string(name):
    return xbmc.getInfoLabel("Skin.String({})".format(name)) or ""


def set_skin_string(name, value):
    xbmc.executebuiltin("Skin.SetString({},{})".format(_q(name), _q(value or "")))


def reset_skin_setting(name):
    xbmc.executebuiltin("Skin.Reset({})".format(_q(name)))


def has_skin_setting(name):
    return bool(xbmc.getCondVisibility("Skin.HasSetting({})".format(name)))


def set_skin_bool(name):
    xbmc.executebuiltin("Skin.SetBool({})".format(_q(name)))


def item_key(group, slot, field):
    return "CCMenu_{}_{}_{}".format(group, int(slot), field)


def main_label_key(group):
    return "CCMain_{}_Label".format(group)


def main_order_key(slot):
    return "{}{}".format(MAIN_ORDER_PREFIX, int(slot))


def get_main_order():
    """Return a repaired, unique main-menu order without guessing unknown values."""
    known = set(DEFAULT_MAIN_ORDER)
    order = []
    for slot in range(1, len(DEFAULT_MAIN_ORDER) + 1):
        group = skin_string(main_order_key(slot)).strip().lower()
        if group in known and group not in order:
            order.append(group)
    for group in DEFAULT_MAIN_ORDER:
        if group not in order:
            order.append(group)
    return order


def set_main_order(order):
    """Persist the complete managed main-menu order."""
    wanted = []
    for group in list(order or []):
        group = str(group).strip().lower()
        if group in DEFAULT_MAIN_ORDER and group not in wanted:
            wanted.append(group)
    for group in DEFAULT_MAIN_ORDER:
        if group not in wanted:
            wanted.append(group)
    for slot, group in enumerate(wanted, 1):
        set_skin_string(main_order_key(slot), group)
    return wanted


def ensure_main_order():
    repaired = get_main_order()
    current = [
        skin_string(main_order_key(slot)).strip().lower()
        for slot in range(1, len(DEFAULT_MAIN_ORDER) + 1)
    ]
    if current != repaired:
        set_main_order(repaired)
        log("Main-menu order initialized/repaired: {}".format(",".join(repaired)))
        return True
    return False


def get_items(group):
    items = []
    for slot in range(1, MAX_ITEMS + 1):
        label = skin_string(item_key(group, slot, "Label"))
        action = skin_string(item_key(group, slot, "Action"))
        if label:
            items.append({"label": label, "action": action})
    return items


def set_items(group, items):
    items = list(items)[:MAX_ITEMS]
    for slot in range(1, MAX_ITEMS + 1):
        if slot <= len(items):
            item = items[slot - 1]
            set_skin_string(item_key(group, slot, "Label"), item.get("label", ""))
            set_skin_string(item_key(group, slot, "Action"), item.get("action", ""))
        else:
            reset_skin_setting(item_key(group, slot, "Label"))
            reset_skin_setting(item_key(group, slot, "Action"))


def loc(string_id):
    try:
        value = xbmc.getLocalizedString(int(string_id))
    except Exception:
        value = ""
    return value or LOC_FALLBACK.get(int(string_id), str(string_id))


def cond(condition):
    try:
        return bool(xbmc.getCondVisibility(condition))
    except Exception:
        return False


def skin_loc(string_id, fallback):
    try:
        value = xbmcaddon.Addon(TARGET_SKIN).getLocalizedString(int(string_id))
    except Exception:
        value = ""
    return value or fallback


def rpc(method, params=None):
    request = {"jsonrpc": "2.0", "id": 1, "method": method}
    if params is not None:
        request["params"] = params
    try:
        result = json.loads(xbmc.executeJSONRPC(json.dumps(request)))
    except Exception as exc:
        log("JSON-RPC decode failed for {}: {}".format(method, exc), xbmc.LOGWARNING)
        return None
    if "error" in result:
        log("JSON-RPC {} failed: {}".format(method, result.get("error")), xbmc.LOGWARNING)
        return None
    return result.get("result")


def directory_items(path, media="files"):
    result = rpc("Files.GetDirectory", {"directory": path, "media": media}) or {}
    items = result.get("files") or []
    # Some plugins do not classify their directory listing using the expected
    # media type. A generic retry keeps deep plugin entry points browseable.
    if not items and media != "files":
        result = rpc("Files.GetDirectory", {"directory": path, "media": "files"}) or {}
        items = result.get("files") or []
    return items


def quote_builtin(value):
    return '"{}"'.format(str(value).replace('"', "'"))


def activate_window(window, path=None, use_return=True):
    if path:
        suffix = ",return" if use_return else ""
        return "ActivateWindow({},{}{})".format(window, quote_builtin(path), suffix)
    return "ActivateWindow({})".format(window)


def _node_defaults(path, window, media, limit=6):
    out = []
    for entry in directory_items(path, media):
        label = entry.get("label") or ""
        target = entry.get("file") or ""
        if not label or not target:
            continue
        out.append({"label": label, "action": activate_window(window, target, True)})
        if len(out) >= limit:
            break
    return out


def default_items(group):
    if group == "movies":
        return _node_defaults("library://video/movies/", "Videos", "video", 6)
    if group == "tvshows":
        return _node_defaults("library://video/tvshows/", "Videos", "video", 6)
    if group == "music":
        return _node_defaults("library://music/", "Music", "music", 6)

    # Publication defaults deliberately keep these menus small and predictable.
    # Labels are resolved at first start from Kodi's current language.
    if group == "videos":
        return [
            {"label": loc(744), "action": "ActivateWindow(Videos,Files,return)"},
            {"label": loc(24001), "action": "ActivateWindow(Videos,Addons,return)"},
        ]

    if group == "pictures":
        return []

    if group == "system":
        return [
            {"label": loc(7), "action": "ActivateWindow(FileManager)"},
            {"label": loc(5), "action": "ActivateWindow(Settings)"},
            {"label": skin_loc(31965, "Configure skin"), "action": "ActivateWindow(SkinSettings)"},
            {"label": skin_loc(31966, "Menu editor"), "action": "RunScript(special://skin/resources/lib/menu_editor.py)"},
            {"label": loc(130), "action": "ActivateWindow(SystemInfo)"},
        ]

    fixed = {
        "tv": [
            (19019, "ActivateWindow(TVChannels)"),
            (22020, "ActivateWindow(TVGuide)"),
            (19163, "ActivateWindow(TVRecordings)"),
            (19138, "ActivateWindow(TVTimerRules)"),
            (19040, "ActivateWindow(TVTimers)"),
            (137, "ActivateWindow(TVSearch)"),
        ],
        "radio": [
            (19019, "ActivateWindow(RadioChannels)"),
            (22020, "ActivateWindow(RadioGuide)"),
            (19163, "ActivateWindow(RadioRecordings)"),
            (19138, "ActivateWindow(RadioTimerRules)"),
            (19040, "ActivateWindow(RadioTimers)"),
            (137, "ActivateWindow(RadioSearch)"),
        ],
        "addons": [
            (24998, "ActivateWindow(addonbrowser,addons://user,return)"),
            (24033, "ActivateWindow(addonbrowser,addons://repos/,return)"),
            (24041, "InstallFromZip"),
        ],
    }
    return [{"label": loc(lid), "action": action} for lid, action in fixed.get(group, [])]

def migrate_5022():
    """Repair path actions written by 5.0.21 without resetting user menus."""
    if has_skin_setting(MIGRATION_5022):
        return False
    changed = 0
    for group, _, _ in GROUPS:
        for slot in range(1, MAX_ITEMS + 1):
            key = item_key(group, slot, "Action")
            action = skin_string(key)
            if action and action.startswith("ActivateWindow(") and "'" in action:
                fixed = action.replace("'", '\"')
                if fixed != action:
                    set_skin_string(key, fixed)
                    changed += 1
        mkey = "CCMain_{}_Action".format(group)
        action = skin_string(mkey)
        if action and action.startswith("ActivateWindow(") and "'" in action:
            fixed = action.replace("'", '\"')
            if fixed != action:
                set_skin_string(mkey, fixed)
                changed += 1
    set_skin_bool(MIGRATION_5022)
    log("5.0.22 action migration complete ({} repaired)".format(changed))
    return bool(changed)


def migrate_5028():
    """Repair Cleaner action routes captured by 5.0.27 as folder navigation."""
    if has_skin_setting(MIGRATION_5028):
        return False
    changed = 0
    marker = "plugin://context.musiclibrary.cleaner/?action=start_view&view="

    def repair(action):
        if not action or marker not in action or not action.startswith("ActivateWindow("):
            return action
        # Capture the quoted plugin URL only. The old window/history wrapper is
        # wrong for these four action routes because the Cleaner opens Music itself.
        first = action.find('\"' + marker)
        if first < 0:
            return action
        last = action.find('\"', first + 1)
        if last < 0:
            return action
        url = action[first:last + 1]
        return "RunPlugin({})".format(url)

    for group, _, _ in GROUPS:
        for slot in range(1, MAX_ITEMS + 1):
            key = item_key(group, slot, "Action")
            action = skin_string(key)
            fixed = repair(action)
            if fixed != action:
                set_skin_string(key, fixed)
                changed += 1
        mkey = "CCMain_{}_Action".format(group)
        action = skin_string(mkey)
        fixed = repair(action)
        if fixed != action:
            set_skin_string(mkey, fixed)
            changed += 1
    set_skin_bool(MIGRATION_5028)
    log("5.0.28 Cleaner action migration complete ({} repaired)".format(changed))
    return bool(changed)


def ensure_initialised(force=False):
    if xbmc.getSkinDir() != TARGET_SKIN:
        return False
    initialised = False
    if force or not has_skin_setting(INIT_SETTING):
        for group, _, _ in GROUPS:
            set_items(group, default_items(group))
        set_skin_bool(INIT_SETTING)
        log("Menu defaults initialised")
        initialised = True
    migrate_5022()
    migrate_5028()
    ensure_main_order()
    return initialised


def addon_list():
    addons = []
    # Query plugin sources by content type. This is the canonical JSON-RPC
    # representation and works for video/audio/image/program plugins.
    for content, window, media in [
        ("video", "Videos", "video"),
        ("audio", "Music", "music"),
        ("image", "Pictures", "pictures"),
        ("executable", "Programs", "programs"),
    ]:
        result = rpc("Addons.GetAddons", {
            "type": "xbmc.python.pluginsource",
            "content": content,
            "enabled": True,
            "properties": ["name", "thumbnail", "path"],
        }) or {}
        for addon in result.get("addons") or []:
            addonid = addon.get("addonid") or ""
            name = addon.get("name") or addon.get("label") or addonid
            path = addon.get("path") or ("plugin://{}/".format(addonid) if addonid else "")
            if addonid and path:
                addons.append({"id": addonid, "label": name, "window": window, "media": media, "path": path})
    # An add-on can expose more than one content type. Deduplicate identical
    # (id, window) entries while preserving useful video/audio variants.
    seen = set()
    unique = []
    for addon in sorted(addons, key=lambda x: (x["label"].lower(), x["window"])):
        key = (addon["id"], addon["window"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(addon)
    return unique


def addon_details(addonid):
    if not addonid:
        return None
    result = rpc("Addons.GetAddonDetails", {
        "addonid": addonid,
        "properties": ["name", "path", "thumbnail", "version", "enabled"],
    }) or {}
    return result.get("addon")


def all_installed_addons():
    result = rpc("Addons.GetAddons", {
        "enabled": "all",
        "installed": True,
        "properties": ["name", "path", "thumbnail", "version", "enabled"],
    }) or {}
    return result.get("addons") or []


def settings_sections():
    result = rpc("Settings.GetSections", {
        "level": "expert",
        "properties": ["categories"],
    }) or {}
    return result.get("sections") or []


def settings_categories(section_id):
    result = rpc("Settings.GetCategories", {
        "level": "expert",
        "section": section_id,
        "properties": ["settings"],
    }) or {}
    return result.get("categories") or []


def settings_for_category(section_id, category_id):
    result = rpc("Settings.GetSettings", {
        "level": "expert",
        "filter": {"section": section_id, "category": category_id},
    }) or {}
    return result.get("settings") or []


def favourites():
    result = rpc("Favourites.GetFavourites", {
        "type": None,
        "properties": ["path", "window", "windowparameter", "thumbnail"],
    }) or {}
    return result.get("favourites") or []
