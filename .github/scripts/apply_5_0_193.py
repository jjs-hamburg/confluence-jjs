from pathlib import Path

BASE_VERSION = 'version="5.0.192"'
NEW_VERSION = 'version="5.0.193"'


def replace_once(path, old, new, label):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one source block in {path}, found {count}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


addon = Path("skin.confluence.custom/addon.xml")
addon_text = addon.read_text(encoding="utf-8")
if NEW_VERSION in addon_text:
    print("5.0.193 source already applied")
    raise SystemExit(0)
if BASE_VERSION not in addon_text:
    raise SystemExit("Unexpected addon base version; refusing to patch")

replace_once(
    addon,
    BASE_VERSION,
    NEW_VERSION,
    "version bump",
)
replace_once(
    addon,
    '<news>5.0.192: Keep artwork state stable across window changes and scans, skip unavailable back-cover modes only on mode/title change, tighten large front/back spacing for non-square artwork, and retain the 5.0.191 Song Popup fixes.</news>',
    '<news>5.0.193: Preserve the validated artwork stability, keep the selected large/small layout when a new title has no back cover, repair mojibake in Song Popup credits, and switch popup track selection through Kodi\'s non-blocking playlist offset action.</news>',
    "news update",
)

replace_once(
    "skin.confluence.custom/resources/lib/cover_display_action.py",
    '''    fallback = {\n        "both": "infofront",\n        "infoboth": "compact",\n    }.get(mode)''',
    '''    fallback = {\n        # Keep the selected layout size; only drop the unavailable back cover.\n        "both": "front",\n        "infoboth": "infofront",\n    }.get(mode)''',
    "back-cover fallback",
)

replace_once(
    "skin.confluence.custom/resources/lib/songpopup_data.py",
    '''def _clean_credit_display_text(value):\n    text = unicodedata.normalize("NFC", str(value or ""))\n    text = "".join(char for char in text if _credit_char_supported(char))\n    text = re.sub(r"\\s+", " ", text).strip()\n    return text.strip(" :;,-–—·•|/\\\\")''',
    '''def _clean_credit_display_text(value):\n    # Credits can contain the same UTF-8-as-Western-codepage mojibake already\n    # handled for lyrics. Repair it before glyph filtering so sequences such as\n    # "Ã…" / "â…" do not survive as formally valid but visibly wrong text.\n    text = unicodedata.normalize("NFC", repair_mojibake(value))\n    text = "".join(char for char in text if _credit_char_supported(char))\n    text = re.sub(r"\\s+", " ", text).strip()\n    return text.strip(" :;,-–—·•|/\\\\")''',
    "credits mojibake repair",
)

replace_once(
    "skin.confluence.custom/resources/lib/songselector_action.py",
    '''    home = _home()\n    home.setProperty(SELECTION_TARGET_PROP, str(target))\n    request = {\n        "jsonrpc": "2.0",\n        "method": "Player.GoTo",\n        "params": {"playerid": _audio_player_id(), "to": target},\n        "id": 1,\n    }\n    try:\n        result = json.loads(xbmc.executeJSONRPC(json.dumps(request)))\n        if result.get("error"):\n            home.clearProperty(SELECTION_TARGET_PROP)\n            return\n    except Exception:\n        home.clearProperty(SELECTION_TARGET_PROP)\n        return\n    _touch()''',
    '''    home = _home()\n    home.setProperty(SELECTION_TARGET_PROP, str(target))\n    # Player.GoTo via executeJSONRPC keeps this foreground RunScript alive while\n    # Kodi changes tracks. That can raise DialogBusy; its focus then hides the\n    # popup navigation highlight. Playlist.PlayOffset is Kodi's native playlist\n    # action and executebuiltin is non-blocking, so this action can return at once.\n    xbmc.executebuiltin("Playlist.PlayOffset(music,{})".format(target), wait=False)\n    _touch()''',
    "non-blocking popup song selection",
)

print("5.0.193 source patch applied")
