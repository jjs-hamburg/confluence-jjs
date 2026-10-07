# -*- coding: utf-8 -*-
from pathlib import Path
import py_compile
import xml.etree.ElementTree as ET

root = Path("skin.confluence.custom")
addon = (root / "addon.xml").read_text(encoding="utf-8")
home = (root / "1080p" / "Home.xml").read_text(encoding="utf-8")
nowplaying = (root / "resources/lib/nowplaying_service.py").read_text(encoding="utf-8")
cover = (root / "resources/lib/cover_display_action.py").read_text(encoding="utf-8")
geometry = (root / "resources/lib/home_geometry_action.py").read_text(encoding="utf-8")
live = (root / "resources/lib/live_home_adjust.py").read_text(encoding="utf-8")
popup = (root / "resources/lib/songpopup_service.py").read_text(encoding="utf-8")
popup_data = (root / "resources/lib/songpopup_data.py").read_text(encoding="utf-8")

assert 'version="5.0.192"' in addon
assert "live_home_adjust.py,apply" not in home
assert "cover_display_action.py,apply" not in home
assert "normalize_artwork_mode_for_back" in nowplaying
assert "clear_back_art" not in nowplaying
geometry_body = nowplaying.split("def _geometry_signature(home):", 1)[1].split("def _request_geometry_sync", 1)[0]
assert 'Window.IsActive(Home)' not in geometry_body
assert "def normalize_artwork_mode_for_back():" in cover
assert '"both": "infofront"' in cover
assert '"infoboth": "compact"' in cover
assert "apply_dynamic_cover()" in geometry
assert "sync_info_cover_geometry()" in geometry
assert "PAIR_GAP = 40" in live
assert "def _pair_cover_rects(size):" in live
assert "_art_ratio(front_art)" in live
assert "front_width + PAIR_GAP + back_width" in live

# 5.0.191 Song Popup fixes must remain intact.
assert "explicit_selection_resolved = False" in popup
assert "and not explicit_selection_resolved" in popup
assert "PLAYBACK_END_SETTLE_SECONDS = 1.0" in popup
assert "self.stop_now = True" in popup
assert "_clean_credit_display_text" in popup_data
assert "_CREDIT_UNSUPPORTED_RANGES" in popup_data

for path in (
    root / "resources/lib/nowplaying_service.py",
    root / "resources/lib/cover_display_action.py",
    root / "resources/lib/home_geometry_action.py",
    root / "resources/lib/live_home_adjust.py",
    root / "resources/lib/songpopup_service.py",
    root / "resources/lib/songpopup_data.py",
):
    py_compile.compile(str(path), doraise=True)

ET.parse(root / "addon.xml")
ET.parse(root / "1080p" / "Home.xml")
print("Confluence-jjs 5.0.192 validation OK")
