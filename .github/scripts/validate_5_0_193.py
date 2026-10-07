from pathlib import Path
import py_compile
import subprocess
import xml.etree.ElementTree as ET

BASE = "0e39a221d5459bc7cca42fe6bf18c76198d59063"
ROOT = Path("skin.confluence.custom")
EXPECTED = {
    "skin.confluence.custom/addon.xml",
    "skin.confluence.custom/resources/lib/cover_display_action.py",
    "skin.confluence.custom/resources/lib/songpopup_data.py",
    "skin.confluence.custom/resources/lib/songselector_action.py",
}

for rel in (
    "addon.xml",
    "1080p/Home.xml",
    "1080p/custom_1116_SongSelector.xml",
):
    ET.parse(ROOT / rel)

for rel in (
    "resources/lib/cover_display_action.py",
    "resources/lib/songpopup_data.py",
    "resources/lib/songselector_action.py",
    "resources/lib/songpopup_service.py",
    "resources/lib/nowplaying_service.py",
):
    py_compile.compile(str(ROOT / rel), doraise=True)

changed = set(
    subprocess.check_output(
        ["git", "diff", "--name-only", BASE, "--", "skin.confluence.custom"],
        text=True,
    ).splitlines()
)
if changed != EXPECTED:
    raise SystemExit(f"Unexpected source scope: {sorted(changed)}")

addon = (ROOT / "addon.xml").read_text(encoding="utf-8")
if 'version="5.0.193"' not in addon:
    raise SystemExit("addon version is not 5.0.193")

cover = (ROOT / "resources/lib/cover_display_action.py").read_text(encoding="utf-8")
if '"both": "front"' not in cover or '"infoboth": "infofront"' not in cover:
    raise SystemExit("Back-cover fallback does not preserve layout size")
if '"both": "infofront"' in cover or '"infoboth": "compact"' in cover:
    raise SystemExit("Old back-cover fallback still present")

popup_data = (ROOT / "resources/lib/songpopup_data.py").read_text(encoding="utf-8")
credit_start = popup_data.index("def _clean_credit_display_text(value):")
credit_end = popup_data.index("\ndef build_credit_display_rows", credit_start)
credit_block = popup_data[credit_start:credit_end]
if "repair_mojibake(value)" not in credit_block:
    raise SystemExit("Credits do not pass through mojibake repair")

selector = (ROOT / "resources/lib/songselector_action.py").read_text(encoding="utf-8")
play_start = selector.index("def play_focused():")
play_end = selector.index("\ndef main():", play_start)
play_block = selector[play_start:play_end]
if 'Playlist.PlayOffset(music,{})' not in play_block:
    raise SystemExit("Popup selection does not use Playlist.PlayOffset")
if '"method": "Player.GoTo"' in play_block or "executeJSONRPC" in play_block:
    raise SystemExit("Synchronous Player.GoTo still present in play_focused")
if "SELECTION_TARGET_PROP" not in play_block:
    raise SystemExit("Explicit-selection transition marker was lost")

# Local, dependency-free check of the existing repair algorithm against the
# exact corruption patterns this release routes through it for credits.
def repair_mojibake(value):
    markers = ("Ã", "Â", "â", "ð", "ï¿½")
    value = str(value or "")
    def badness(candidate):
        return sum(candidate.count(marker) for marker in markers) + (candidate.count("\ufffd") * 10)
    for _unused in range(2):
        current_score = badness(value)
        if current_score <= 0:
            break
        candidates = [value]
        for encoding in ("cp1252", "latin-1"):
            try:
                candidates.append(value.encode(encoding).decode("utf-8"))
            except (UnicodeEncodeError, UnicodeDecodeError):
                pass
        best = min(candidates, key=badness)
        if badness(best) >= current_score:
            break
        value = best
    return value

cases = {
    "BeyoncÃ©": "Beyoncé",
    "GÃ¼nter": "Günter",
    "FranÃ§ois": "François",
    "Strauss â€“ Elektra": "Strauss – Elektra",
}
for broken, expected in cases.items():
    actual = repair_mojibake(broken)
    if actual != expected:
        raise SystemExit(f"Mojibake repair failed: {broken!r} -> {actual!r}")

print("5.0.193 validation OK")
print("Changed source files:")
for name in sorted(changed):
    print(" -", name)
