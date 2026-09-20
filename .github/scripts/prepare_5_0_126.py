from pathlib import Path
import math
import re

root = Path("skin.confluence.custom")

# 1) Long text input: let Kodi's edit control scroll the viewport with the cursor.
p = root / "1080p" / "DialogKeyboard.xml"
s = p.read_text(encoding="utf-8")
old = """\t\t\t\t<font>font13</font>
\t\t\t\t<align>center</align>
\t\t\t\t<aligny>center</aligny>"""
new = """\t\t\t\t<font>font13</font>
\t\t\t\t<align>left</align>
\t\t\t\t<aligny>center</aligny>"""
assert old in s
p.write_text(s.replace(old, new, 1), encoding="utf-8")

# 2) Persistent order for the nine main-menu entries already managed by the editor.
p = root / "resources" / "lib" / "menu_common.py"
s = p.read_text(encoding="utf-8")
anchor = """GROUP_LABEL = dict((g, label) for g, label, _ in GROUPS)
MAIN_LOCALIZE = dict((g, lid) for g, _, lid in GROUPS)
"""
replacement = """GROUP_LABEL = dict((g, label) for g, label, _ in GROUPS)
MAIN_LOCALIZE = dict((g, lid) for g, _, lid in GROUPS)

# Visual order of the menu-editor-managed main items in the unmodified 5.0.125
# Home.xml. Weather, Games and Disc keep their fixed Confluence positions; the
# nine managed items can move through the nine managed slots around them.
DEFAULT_MAIN_ORDER = [
    "pictures", "radio", "tv", "videos", "movies",
    "tvshows", "music", "addons", "system",
]
MAIN_ORDER_PREFIX = "CCMainOrder_"
"""
assert anchor in s
s = s.replace(anchor, replacement, 1)
anchor = """def main_label_key(group):
    return "CCMain_{}_Label".format(group)


def get_items(group):
"""
replacement = """def main_label_key(group):
    return "CCMain_{}_Label".format(group)


def main_order_key(slot):
    return "{}{}".format(MAIN_ORDER_PREFIX, int(slot))


def get_main_order():
    \"\"\"Return a repaired, unique main-menu order without guessing unknown values.\"\"\"
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
    \"\"\"Persist the complete managed main-menu order.\"\"\"
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
"""
assert anchor in s
s = s.replace(anchor, replacement, 1)
anchor = """    migrate_5022()
    migrate_5028()
    return initialised
"""
replacement = """    migrate_5022()
    migrate_5028()
    ensure_main_order()
    return initialised
"""
assert anchor in s
p.write_text(s.replace(anchor, replacement, 1), encoding="utf-8")

# Menu editor: move main entries left/right and list them in their real order.
p = root / "resources" / "lib" / "menu_editor.py"
s = p.read_text(encoding="utf-8")
old = """    favourites, get_items, main_label_key, reset_skin_setting, rpc, set_items,
    set_skin_string, settings_categories, settings_for_category, settings_sections,
    skin_string, log,
)"""
new = """    favourites, get_items, get_main_order, main_label_key, reset_skin_setting, rpc, set_items,
    set_main_order, set_skin_string, settings_categories, settings_for_category, settings_sections,
    skin_string, log,
)"""
assert old in s
s = s.replace(old, new, 1)

m = re.search(r"def group_editor\(group\):\n.*?\n\ndef choose_target\(", s, re.S)
assert m
replacement = """def _move_main_group(group, delta):
    order = get_main_order()
    try:
        pos = order.index(group)
    except ValueError:
        return False
    target = pos + int(delta)
    if target < 0 or target >= len(order):
        return False
    order[pos], order[target] = order[target], order[pos]
    wanted = set_main_order(order)
    for _ in range(20):
        if get_main_order() == wanted:
            break
        xbmc.sleep(25)
    return True


def group_editor(group):
    while True:
        custom = skin_string(main_label_key(group))
        submenu_count = len(get_items(group))
        main_action = skin_string(main_action_key(group))
        order = get_main_order()
        try:
            position = order.index(group)
        except ValueError:
            position = -1

        actions = [
            ("submenu", "Untermenü bearbeiten ({} Einträge)".format(submenu_count)),
            ("rename", "Hauptmenü umbenennen" + (" – {}".format(custom) if custom else "")),
            ("target", "Hauptmenü-Ziel ändern" + (" – angepasst" if main_action else "")),
        ]
        if position > 0:
            actions.append(("left", "Hauptmenü nach links verschieben"))
        if 0 <= position < len(order) - 1:
            actions.append(("right", "Hauptmenü nach rechts verschieben"))
        actions += [
            ("reset_label", "Hauptmenüname auf Standard zurücksetzen"),
            ("reset_target", "Hauptmenü-Ziel auf Standard zurücksetzen"),
            ("reset_submenu", "Untermenü auf Confluence-Standard zurücksetzen"),
        ]

        title = "Menü: {}".format(main_label(group))
        if position >= 0:
            title += "  ·  Position {}/{}".format(position + 1, len(order))
        choice = select(title, [label for _action, label in actions])
        if choice < 0:
            return
        action = actions[choice][0]
        if action == "submenu":
            edit_submenu(group)
        elif action == "rename":
            edit_main_label(group)
        elif action == "target":
            edit_main_action(group)
        elif action == "left":
            _move_main_group(group, -1)
        elif action == "right":
            _move_main_group(group, 1)
        elif action == "reset_label":
            reset_main_label(group)
        elif action == "reset_target":
            reset_main_action(group)
        elif action == "reset_submenu":
            if D.yesno(
                "Untermenü zurücksetzen",
                "Die Einträge von '{}' auf den Startzustand zurücksetzen?".format(GROUP_LABEL[group]),
            ):
                set_items_synced(group, default_items(group))


def choose_target("""
s = s[:m.start()] + replacement + s[m.end():]

old = """    while True:
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
"""
new = """    while True:
        options = []
        keys = []
        order = get_main_order()
        for position, group in enumerate(order, 1):
            default_label = GROUP_LABEL.get(group, group)
            custom = skin_string(main_label_key(group))
            shown = custom or default_label
            options.append(
                "{}. {}   ({} Untermenüpunkte)".format(
                    position, shown, len(get_items(group))
                )
            )
            keys.append(group)
        c = select("JJS Confluence Menüeditor", options)
        if c < 0:
            return
        group_editor(keys[c])
"""
assert old in s
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")

# 3) Compact artwork: read actual image dimensions and publish a proportional width class.
p = root / "resources" / "lib" / "cover_display_action.py"
s = p.read_text(encoding="utf-8")
s = s.replace(
    "import xbmc\nimport xbmcgui\nimport xbmcvfs\n",
    "import math\nimport struct\nimport urllib.parse\n\nimport xbmc\nimport xbmcgui\nimport xbmcvfs\n",
    1,
)
s = s.replace(
    'BACK_PROP = "ConfluenceCustom.MusicBackArt"\n',
    'BACK_PROP = "ConfluenceCustom.MusicBackArt"\n'
    'COMPACT_WIDTH_PROP = "ConfluenceCustom.NowPlaying.CompactCoverWidth"\n'
    "COMPACT_HEIGHT = 115\n"
    "COMPACT_WIDTH_STEP = 10\n"
    "COMPACT_WIDTH_MIN = 30\n"
    "COMPACT_WIDTH_MAX = 800\n"
    "COMPACT_WIDTH_FALLBACK = 120\n"
    "_COMPACT_WIDTH_CACHE = {}\n",
    1,
)

anchor = """def clear_back_art():
    _home().clearProperty(BACK_PROP)


def main():
"""
replacement = r'''def _image_candidates(art):
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
'''
assert anchor in s
s = s.replace(anchor, replacement, 1)

old = """    # Confluence Custom 5.0.124: the focused artwork has exactly three user
    # states: front, front+back, and no cover. If no back artwork exists, the
    # unavailable pair state is skipped, so Enter still toggles front <-> none.
    has_back = bool(sync_back_art())
    mode = (xbmc.getInfoLabel("Skin.String({})".format(SETTING)) or "front").strip().lower()
    if mode == "front":
        new_mode = "both" if has_back else "none"
    elif mode == "both":
        new_mode = "none"
    else:
        # Also normalizes the legacy back-only state from older versions.
        new_mode = "front"
"""
new = """    # 5.0.126: front -> front+back -> compact -> none.
    has_back = bool(sync_back_art())
    sync_compact_cover_width()
    mode = (xbmc.getInfoLabel("Skin.String({})".format(SETTING)) or "front").strip().lower()
    if mode == "front":
        new_mode = "both" if has_back else "compact"
    elif mode == "both":
        new_mode = "compact"
    elif mode == "compact":
        new_mode = "none"
    else:
        new_mode = "front"
"""
assert old in s
p.write_text(s.replace(old, new, 1), encoding="utf-8")

# Service: refresh proportional width on track changes and reduce album-wrap width.
p = root / "resources" / "lib" / "songselector_service.py"
s = p.read_text(encoding="utf-8")
s = s.replace(
    "from cover_display_action import clear_back_art, sync_back_art",
    "from cover_display_action import COMPACT_WIDTH_PROP, clear_back_art, sync_back_art, sync_compact_cover_width",
    1,
)
old = """    standard = xbmc.getCondVisibility("Skin.HasSetting(CCStandardConfluence)")
    width = ALBUM_WRAP_STANDARD_WIDTH_PX if standard else ALBUM_WRAP_CUSTOM_WIDTH_PX
"""
new = """    standard = xbmc.getCondVisibility("Skin.HasSetting(CCStandardConfluence)")
    width = ALBUM_WRAP_STANDARD_WIDTH_PX if standard else ALBUM_WRAP_CUSTOM_WIDTH_PX
    if not standard and xbmc.getCondVisibility(
        "String.IsEqual(Skin.String(CCMusicArtworkMode),compact)"
    ):
        try:
            compact_width = float(home.getProperty(COMPACT_WIDTH_PROP) or 120)
        except Exception:
            compact_width = 120.0
        width = max(240.0, width - compact_width - 15.0)
"""
assert old in s
s = s.replace(old, new, 1)
old = """                if playing_file and playing_file != last_art_file:
                    sync_back_art()
                    last_art_file = playing_file
"""
new = """                if playing_file and playing_file != last_art_file:
                    sync_back_art()
                    sync_compact_cover_width()
                    last_art_file = playing_file
"""
assert old in s
p.write_text(s.replace(old, new, 1), encoding="utf-8")

# Home: movable main-menu slots + compact proportional artwork in footer.
p = root / "1080p" / "Home.xml"
s = p.read_text(encoding="utf-8")
s = s.replace(
    "!String.IsEqual(Skin.String(CCMusicArtworkMode),none) + [!String.IsEqual(Skin.String(CCMusicArtworkMode),both)",
    "!String.IsEqual(Skin.String(CCMusicArtworkMode),none) + !String.IsEqual(Skin.String(CCMusicArtworkMode),compact) + [!String.IsEqual(Skin.String(CCMusicArtworkMode),both)",
)
s = s.replace(
    "Select cycles front -> front+back -> none. Without back artwork the pair state is skipped.",
    "Select cycles front -> front+back -> compact footer cover -> none. Without back artwork the pair state is skipped.",
)

content_start = s.index(
    '\t\t\t\t<content>\n\t\t\t\t\t<item id="7">',
    s.index('<control type="fixedlist" id="9000">'),
)
content_end = s.index("\n\t\t\t\t</content>", content_start) + len("\n\t\t\t\t</content>")
old_content = s[content_start:content_end]

items = {}
for m in re.finditer(r'\t{5}<item id="(\d+)">.*?\n\t{5}</item>', old_content, re.S):
    items[int(m.group(1))] = m.group(0)
assert {7,4,14,13,12,2,10,11,3,1,6,5}.issubset(items)

group_id = {
    "pictures": 4, "radio": 13, "tv": 12, "videos": 2,
    "movies": 10, "tvshows": 11, "music": 3, "addons": 1, "system": 5,
}
default_order = [
    "pictures", "radio", "tv", "videos", "movies",
    "tvshows", "music", "addons", "system",
]

def variant(block, slot_number, group):
    key = "CCMainOrder_{}".format(slot_number)
    if group == default_order[slot_number - 1]:
        order_cond = (
            "[String.IsEmpty(Skin.String({})) | String.IsEqual(Skin.String({}),{})]"
        ).format(key, key, group)
    else:
        order_cond = "String.IsEqual(Skin.String({}),{})".format(key, group)
    return re.sub(
        r"<visible>(.*?)</visible>",
        lambda match: "<visible>{} + [{}]</visible>".format(order_cond, match.group(1)),
        block, count=1, flags=re.S,
    )

def slot(slot_number):
    return "\n".join(
        variant(items[group_id[group]], slot_number, group)
        for group in default_order
    )

new_content = "\t\t\t\t<content>\n"
new_content += items[7] + "\n"
new_content += slot(1) + "\n"
new_content += items[14] + "\n"
for slot_number in range(2, 9):
    new_content += slot(slot_number) + "\n"
new_content += items[6] + "\n"
new_content += slot(9) + "\n\t\t\t\t</content>"
s = s[:content_start] + new_content + s[content_end:]

footer_marker = """\t\t\t<!-- 5.0.113: year stays with album metadata; technical audio data moved to the time line. -->
\t\t\t<!-- Long album titles: truncate, scroll, or wrap upward while keeping the original lower baseline. -->
"""
assert footer_marker in s

classes = list(range(30, 801, 10))
image_lines = []
for width in classes:
    visible = (
        "String.IsEqual(Skin.String(CCMusicArtworkMode),compact) + "
        "String.IsEqual(Window(Home).Property(ConfluenceCustom.NowPlaying.CompactCoverWidth),{})"
    ).format(width)
    image_lines.append(
        """\t\t\t<control type="image">
\t\t\t\t<description>Compact proportional cover {0}px class</description>
\t\t\t\t<left>0</left><top>0</top><width>{0}</width><height>115</height>
\t\t\t\t<aspectratio align="left" aligny="center">keep</aspectratio>
\t\t\t\t<texture fallback="$VAR[CCGlobalNoCover]">$VAR[CCNowPlayingFrontArt]</texture>
\t\t\t\t<visible>{1}</visible>
\t\t\t</control>""".format(width, visible)
    )
    image_lines.append(
        """\t\t\t<control type="image">
\t\t\t\t<description>Compact proportional cover focus {0}px class</description>
\t\t\t\t<left>0</left><top>0</top><width>{0}</width><height>115</height>
\t\t\t\t<aspectratio align="left" aligny="center">keep</aspectratio>
\t\t\t\t<texture fallback="$VAR[CCGlobalNoCover]">$VAR[CCNowPlayingFrontArt]</texture>
\t\t\t\t<bordertexture infill="false" border="5">folder-focus.png</bordertexture><bordersize>4</bordersize>
\t\t\t\t<visible>Control.HasFocus(9150) + {1}</visible>
\t\t\t</control>""".format(width, visible)
    )

animations = []
for width in classes:
    animations.append(
        """\t\t\t\t<animation effect="slide" start="0,0" end="{0},0" time="0" condition="String.IsEqual(Skin.String(CCMusicArtworkMode),compact) + String.IsEqual(Window(Home).Property(ConfluenceCustom.NowPlaying.CompactCoverWidth),{1})">conditional</animation>""".format(width + 15, width)
    )

compact_block = (
    "\t\t\t<!-- 5.0.126: compact artwork has a fixed 115 px height only. -->\n"
    + "\n".join(image_lines)
    + "\n\t\t\t<control type=\"group\">\n"
    + "\n".join(animations)
    + "\n"
)
s = s.replace(footer_marker, compact_block + footer_marker, 1)

end_button = """\t\t\t<control type="button" id="9104">
\t\t\t\t<left>0</left><top>32</top><width>1830</width><height>45</height><label/><font/>
\t\t\t\t<texturefocus/><texturenofocus/><onfocus>RunScript(special://skin/resources/lib/songselector_action.py,open)</onfocus>
\t\t\t\t<onclick>RunScript(special://skin/resources/lib/songselector_action.py,open)</onclick><onup>9000</onup><ondown>9000</ondown>
\t\t\t</control>
\t\t</control>
"""
assert end_button in s
s = s.replace(
    end_button,
    end_button.replace("\n\t\t</control>\n", "\n\t\t\t</control>\n\t\t</control>\n"),
    1,
)
p.write_text(s, encoding="utf-8")
(root / "resources" / "skin_modes" / "custom" / "Home.xml").write_text(s, encoding="utf-8")

# 4) Name/version/provider; technical ID stays unchanged.
p = root / "addon.xml"
s = p.read_text(encoding="utf-8")
old = 'version="5.0.125" name="Confluence Custom" provider-name="Jezz_X, Team Kodi; custom menu editor"'
new = 'version="5.0.126" name="JJS KODI Confluence Custom" provider-name="Jezz_X, Team Kodi; JJS"'
assert old in s
s = s.replace(old, new, 1)
s = s.replace("<label>Confluence-Menüauswahl abbrechen</label>", "<label>JJS-Confluence-Menüauswahl abbrechen</label>")
s = s.replace(
    '<summary lang="de_DE">Confluence Skin von Jezz_X.</summary>',
    '<summary lang="de_DE">JJS KODI Confluence Custom – erweiterter Confluence-Skin auf Basis von Jezz_X / Team Kodi.</summary>',
)
s = s.replace(
    '<summary lang="en_GB">Confluence skin by Jezz_X.</summary>',
    '<summary lang="en_GB">JJS KODI Confluence Custom – extended Confluence skin based on Jezz_X / Team Kodi.</summary>',
)
s = s.replace(
    '<summary lang="en_US">Confluence skin by Jezz_X.</summary>',
    '<summary lang="en_US">JJS KODI Confluence Custom – extended Confluence skin based on Jezz_X / Team Kodi.</summary>',
)
p.write_text(s, encoding="utf-8")

# Runtime branding only; historical docs/test notes remain untouched.
for path in (root / "resources" / "lib").glob("*.py"):
    text = path.read_text(encoding="utf-8")
    text = text.replace("Confluence Custom", "JJS KODI Confluence Custom")
    text = text.replace('"Confluence Menüeditor"', '"JJS Confluence Menüeditor"')
    path.write_text(text, encoding="utf-8")

# 5) Changelog and focused tests.
p = root / "changelog.txt"
old = p.read_text(encoding="utf-8")
entry = """5.0.126: JJS-Namensgebung, lange Texteingaben, Hauptmenü-Reihenfolge und kompakte Coveransicht.
- Sichtbarer Skin-Name: JJS KODI Confluence Custom; technische ID skin.confluence.custom bleibt unverändert.
- Bildschirmtastatur: Texteingabe linksbündig, damit Kodis Edit-Control bei langen Namen dem Cursor bis zum Anfang und Ende folgt; keine zusätzliche Zeichenbegrenzung.
- Menüeditor: die neun vom Editor verwalteten Hauptmenüs lassen sich nach links/rechts verschieben; die Reihenfolge wird persistent in Skin-Settings gespeichert.
- Neue Coveransicht „kompakt“: großes Cover oben verschwindet; unten links steht das Cover als Block vor den Wiedergabeinformationen.
- Kompaktes Cover: nur 115 px Höhe ist fest; Breite folgt der echten Bildproportion. Longboxes und andere nicht-quadratische Cover werden weder quadratisch gezwungen noch beschnitten.
- Cover-Zyklus mit Back-Cover: Vorderseite -> Vorderseite + Rückseite -> kompakt -> kein Cover -> Vorderseite; ohne Back-Cover wird die Paaransicht übersprungen.

"""
p.write_text(entry + old, encoding="utf-8")

(root / "TEST-NOTES-5.0.126.txt").write_text(
    """JJS KODI Confluence Custom 5.0.126 – Testhinweise
======================================================

1. Lange Texteingabe / Dateiname
- Datei mit sehr langem Namen umbenennen bzw. einen Text von mindestens 255 Zeichen in der Kodi-Tastatur öffnen.
- Cursor mit Links bis zum ersten Zeichen bewegen.
- Erwartung: der sichtbare Textausschnitt folgt dem Cursor vollständig bis zum Anfang.
- Danach mit Rechts bis zum Ende. Auch dabei muss der Ausschnitt dem Cursor folgen.
- Es gibt keine vom Skin gesetzte zusätzliche Zeichenbegrenzung.

2. Hauptmenü-Reihenfolge
- JJS Confluence Menüeditor öffnen.
- Z. B. Musik mehrfach nach links und danach wieder nach rechts verschieben.
- Erwartung: Reihenfolge auf Home ändert sich entsprechend.
- Untermenü, eigenes Label und eigenes Ziel müssen beim semantisch gleichen Hauptmenü bleiben.
- Skin neu laden und Kodi neu starten: Reihenfolge muss erhalten bleiben.
- Weather, Games und Disc sind weiterhin feste Confluence-Einträge und werden vom JJS-Menüeditor nicht umsortiert.

3. Kompakte Coveransicht
- Während Musikwiedergabe Cover fokussieren und per Enter durchschalten.
- Mit back.jpg: Front -> Front+Back -> Kompakt -> Kein Cover -> Front.
- Ohne back.jpg: Front -> Kompakt -> Kein Cover -> Front.
- In Kompakt: oben darf kein großes Cover sichtbar sein.
- Unten links muss das Cover direkt vor den Wiedergabeinformationen stehen.
- Höhe = vollständiger Wiedergabeinformationsblock (115 px).
- Quadratcover prüfen.
- Unbedingt eine schmale/hohe Longbox prüfen: sie muss schmal bleiben und darf nicht quadratisch verzerrt oder beschnitten werden.
- Wiedergabeinformationen müssen passend zur tatsächlich benötigten Coverbreite nach rechts rücken.
- Albumtitel-Umbruch sowie Zeit-/Audio-Badges gegenprüfen.

4. Standard-Confluence-Modus
- Umschalten auf Standard Confluence.
- Custom-Hauptmenüreihenfolge und kompakte Home-Coveransicht sollen dort nicht eingreifen.
- Die globale DialogKeyboard-Korrektur muss auch im Standard-Modus wirken.

5. Update
- Installation über bestehende 5.0.125.
- Skin-ID bleibt skin.confluence.custom; vorhandene Einstellungen müssen erhalten bleiben.
""",
    encoding="utf-8",
)

# Final validation.
import py_compile
import xml.etree.ElementTree as ET

addon = ET.parse(root / "addon.xml").getroot()
assert addon.attrib["id"] == "skin.confluence.custom"
assert addon.attrib["version"] == "5.0.126"
assert addon.attrib["name"] == "JJS KODI Confluence Custom"

for path in sorted((root / "resources" / "lib").rglob("*.py")):
    py_compile.compile(str(path), doraise=True)

for xml_dir in (
    root / "1080p",
    root / "resources" / "skin_modes" / "custom",
    root / "resources" / "skin_modes" / "standard",
):
    for path in sorted(xml_dir.glob("*.xml")):
        ET.parse(path)

assert (
    (root / "1080p" / "Home.xml").read_bytes()
    == (root / "resources" / "skin_modes" / "custom" / "Home.xml").read_bytes()
)

for cache in list((root / "resources" / "lib").rglob("__pycache__")):
    for child in cache.iterdir():
        child.unlink()
    cache.rmdir()

print("Prepared and validated JJS KODI Confluence Custom 5.0.126")
