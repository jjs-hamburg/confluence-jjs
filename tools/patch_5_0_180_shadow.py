from pathlib import Path
import re

root = Path('skin.confluence.custom')
home_p = root / '1080p/Home.xml'
custom_home_p = root / 'resources/skin_modes/custom/Home.xml'
live_p = root / 'resources/lib/live_home_adjust.py'
addon_p = root / 'addon.xml'

home = home_p.read_text(encoding='utf-8')
live = live_p.read_text(encoding='utf-8')
addon = addon_p.read_text(encoding='utf-8')

SOFT_ALPHAS = ['34','2E','28','22','1C','16','10','08']

def controls_xml(hard_id, soft_start, desc, art_var):
    lines = []
    lines.append(f'\t\t\t\t<!-- 5.0.180: artwork-shaped dynamic {desc} shadow. Same aspect/size as the visible cover; 0/0 is truly invisible. -->')
    lines.append(f'\t\t\t\t<control type="image" id="{hard_id}"><description>Dynamic {desc} hard shadow</description><left>-10000</left><top>-10000</top><width>1</width><height>1</height><aspectratio>keep</aspectratio><texture colordiffuse="BE000000">{art_var}</texture><visible>Skin.HasSetting(CCHomeMusicCoverDynamic) + String.IsEqual(Skin.String(CCHomeMusicCoverStyle),hardshadow)</visible></control>')
    for i, alpha in enumerate(SOFT_ALPHAS):
        cid = soft_start + i
        lines.append(f'\t\t\t\t<control type="image" id="{cid}"><description>Dynamic {desc} soft shadow layer {i+1}</description><left>-10000</left><top>-10000</top><width>1</width><height>1</height><aspectratio>keep</aspectratio><texture colordiffuse="{alpha}000000">{art_var}</texture><visible>Skin.HasSetting(CCHomeMusicCoverDynamic) + [String.IsEqual(Skin.String(CCHomeMusicCoverStyle),softshadow) | String.IsEqual(Skin.String(CCHomeMusicCoverStyle),shadow)]</visible></control>')
    return '\n'.join(lines)

home, n = re.subn(r'\t\t\t\t<!-- 5\.0\.178: Dynamic main directional shadow\..*?-->\n\t\t\t\t<control type="image" id="9400">.*?</control>\n\t\t\t\t<control type="image" id="9410">.*?</control>', controls_xml(9400, 9410, 'main', '$VAR[CCNowPlayingFrontArt]'), home, count=1, flags=re.S)
assert n == 1
home, n = re.subn(r'\t\t\t\t<!-- 5\.0\.178: Dynamic selector single directional shadow\..*?-->\n\t\t\t\t<control type="image" id="9420">.*?</control>\n\t\t\t\t<control type="image" id="9430">.*?</control>', controls_xml(9420, 9430, 'selector single', '$VAR[CCNowPlayingPrimaryArt]'), home, count=1, flags=re.S)
assert n == 1
home, n = re.subn(r'\t\t\t\t<!-- 5\.0\.179: pair shadows are explicit right/bottom/corner pieces\..*?-->\n.*?(?=\t\t\t\t<control type="group" id="9312">)', controls_xml(9440, 9450, 'selector pair front', '$VAR[CCNowPlayingFrontArt]') + '\n' + controls_xml(9460, 9470, 'selector pair back', '$VAR[CCNowPlayingBackArt]') + '\n', home, count=1, flags=re.S)
assert n == 1

live, n = re.subn(r'DYNAMIC_SHADOW_CONTROLS = \(.*?\n\)\nDYNAMIC_PAIR_SHADOW_CONTROLS = \(.*?\n\)\n', 'DYNAMIC_ART_SHADOW_CONTROLS = (\n    (9400, tuple(range(9410, 9418)), "main"),\n    (9420, tuple(range(9430, 9438)), "single"),\n    (9440, tuple(range(9450, 9458)), "pair_front"),\n    (9460, tuple(range(9470, 9478)), "pair_back"),\n)\nSOFT_SHADOW_LAYERS = 8\n', live, count=1, flags=re.S)
assert n == 1

start = live.index('def _set_shadow_piece(')
end = live.index('\ndef _apply_dynamic_cover_once', start)
new_shadow = '''def _hide_shadow_control(control):\n    if control is not None:\n        _set_geometry(control, -10000, -10000, 1, 1)\n\n\ndef _soft_shadow_shifts(extent):\n    extent = max(0, int(extent))\n    if extent <= 0:\n        return ()\n    count = min(SOFT_SHADOW_LAYERS, extent)\n    return tuple(((i + 1) * extent + count - 1) // count for i in range(count))\n\n\ndef _apply_dynamic_shadow_once(size):\n    window = xbmcgui.Window(HOME_WINDOW_ID)\n    width = max(0, _skin_int(SHADOW_WIDTH_SETTING, SHADOW_WIDTH_DEFAULT))\n    offset = max(0, _skin_int(SHADOW_OFFSET_SETTING, SHADOW_OFFSET_DEFAULT))\n    extent = width + offset\n    size = max(1, int(size))\n\n    # The shadow is a black silhouette of the SAME artwork, with the same\n    # square control size and aspectratio=keep as the visible cover. This\n    # makes 0/0 truly invisible even for non-square artwork.\n    shifts = _soft_shadow_shifts(extent)\n    for hard_id, soft_ids, kind in DYNAMIC_ART_SHADOW_CONTROLS:\n        cover_x, cover_y = _shadow_cover_rect(kind, size)\n        hard = _control(window, hard_id)\n        soft = tuple(_control(window, cid) for cid in soft_ids)\n        if extent <= 0:\n            _hide_shadow_control(hard)\n            for control in soft:\n                _hide_shadow_control(control)\n            continue\n        _set_geometry(hard, cover_x + extent, cover_y + extent, size, size)\n        for index, control in enumerate(soft):\n            if index < len(shifts):\n                shift = shifts[index]\n                _set_geometry(control, cover_x + shift, cover_y + shift, size, size)\n            else:\n                _hide_shadow_control(control)\n\n'''
live = live[:start] + new_shadow + live[end+1:]
live = live.replace('# Shadow width/offset are absolute pixels: never zoom them with the cover.', '# Shadow geometry follows the rendered artwork and uses absolute pixels.')

addon = addon.replace('version="5.0.179"', 'version="5.0.180"', 1)
addon = addon.replace('5.0.179: Fix front/back pair shadows by drawing only explicit right, bottom and corner pieces; no shadow can appear above or left.', '5.0.180: Dynamic shadows now follow the rendered artwork aspect ratio; soft shadows stay feathered and 0/0 is fully hidden.')

home_p.write_text(home, encoding='utf-8')
custom_home_p.write_text(home, encoding='utf-8')
live_p.write_text(live, encoding='utf-8')
addon_p.write_text(addon, encoding='utf-8')
