from pathlib import Path
import re, struct, zlib

ROOT = Path('skin.confluence.custom')
HOME = ROOT / '1080p' / 'Home.xml'
CUSTOM_HOME = ROOT / 'resources' / 'skin_modes' / 'custom' / 'Home.xml'
LIVE = ROOT / 'resources' / 'lib' / 'live_home_adjust.py'
ADDON = ROOT / 'addon.xml'
MEDIA = ROOT / 'media'


def replace_between(text, start_marker, end_marker, replacement):
    start = text.index(start_marker)
    end = text.index(end_marker, start)
    return text[:start] + replacement + text[end:]


def shadow_controls(hard_id, soft_id, description):
    indent = '\t\t\t\t'
    hard_vis = 'Skin.HasSetting(CCHomeMusicCoverDynamic) + String.IsEqual(Skin.String(CCHomeMusicCoverStyle),hardshadow)'
    soft_vis = 'Skin.HasSetting(CCHomeMusicCoverDynamic) + [String.IsEqual(Skin.String(CCHomeMusicCoverStyle),softshadow) | String.IsEqual(Skin.String(CCHomeMusicCoverStyle),shadow)]'
    return (
        f'{indent}<!-- 5.0.178: {description}. Geometry: x/y = cover + offset; size = cover + width. -->\n'
        f'{indent}<control type="image" id="{hard_id}"><description>{description} hard</description><left>0</left><top>0</top><width>195</width><height>195</height><texture>CCCoverShadowDynamicHard.png</texture><visible>{hard_vis}</visible></control>\n'
        f'{indent}<control type="image" id="{soft_id}"><description>{description} soft</description><left>0</left><top>0</top><width>195</width><height>195</height><texture border="8">CCCoverShadowDynamicSoft.png</texture><visible>{soft_vis}</visible></control>\n'
    )

home = HOME.read_text(encoding='utf-8')
home = replace_between(home, '\t\t\t\t<!-- 5.0.177: dynamic main shadow.', '\t\t\t\t<control type="group" id="9310">', shadow_controls(9400, 9410, 'Dynamic main directional shadow'))
home = replace_between(home, '\t\t\t\t<!-- 5.0.177: dynamic selector single shadow.', '\t\t\t\t<control type="group" id="9311">', shadow_controls(9420, 9430, 'Dynamic selector single directional shadow'))
home = replace_between(home, '\t\t\t\t<!-- 5.0.177: dynamic selector pair front shadow.', '\t\t\t\t<!-- 5.0.177: dynamic selector pair back shadow.', shadow_controls(9440, 9450, 'Dynamic selector pair front directional shadow'))
home = replace_between(home, '\t\t\t\t<!-- 5.0.177: dynamic selector pair back shadow.', '\t\t\t\t<control type="group" id="9312">', shadow_controls(9460, 9470, 'Dynamic selector pair back directional shadow'))
HOME.write_text(home, encoding='utf-8')
CUSTOM_HOME.write_text(home, encoding='utf-8')

live = LIVE.read_text(encoding='utf-8')
live = re.sub(r'SHADOW_WIDTHS = .*?\nSHADOW_WIDTH_DEFAULT = 14\nSHADOW_OFFSETS = .*?\nSHADOW_OFFSET_DEFAULT = 4', 'SHADOW_WIDTH_DEFAULT = 14\nSHADOW_OFFSET_DEFAULT = 4\nSHADOW_STEP = 1', live, count=1)
live = re.sub(r'DYNAMIC_SHADOW_SETS = \(.*?\n\)\n', 'DYNAMIC_SHADOW_CONTROLS = (\n    (9400, 9410, "main"),\n    (9420, 9430, "single"),\n    (9440, 9450, "pair_front"),\n    (9460, 9470, "pair_back"),\n)\n', live, count=1, flags=re.S)
old_apply = re.search(r'def _apply_dynamic_shadow_once\(size\):\n.*?\n\ndef _apply_dynamic_cover_once', live, re.S)
if not old_apply:
    raise SystemExit('dynamic shadow function not found')
new_apply = '''def _apply_dynamic_shadow_once(size):
    window = xbmcgui.Window(HOME_WINDOW_ID)
    width = max(0, _skin_int(SHADOW_WIDTH_SETTING, SHADOW_WIDTH_DEFAULT))
    offset = max(0, _skin_int(SHADOW_OFFSET_SETTING, SHADOW_OFFSET_DEFAULT))

    # 5.0.178 directional geometry:
    # - offset moves the complete shadow right AND down;
    # - width only enlarges it to the right AND down;
    # - offset=0,width=0 places the shadow exactly behind the cover.
    extent = max(1, int(size) + width)
    for hard_id, soft_id, kind in DYNAMIC_SHADOW_CONTROLS:
        cover_x, cover_y = _shadow_cover_rect(kind, size)
        x = cover_x + offset
        y = cover_y + offset
        _set_geometry(_control(window, hard_id), x, y, extent, extent)
        _set_geometry(_control(window, soft_id), x, y, extent, extent)


def _apply_dynamic_cover_once'''
live = live[:old_apply.start()] + new_apply + live[old_apply.end():]
live = re.sub(r'\ndef _step_choice\(values, current, direction, default\):\n.*?\n\n\nclass AdjustDialog', '\n\nclass AdjustDialog', live, count=1, flags=re.S)
old_shadow_actions = '''        if self.mode == "shadow":
            width, offset = self.value
            if action_id == ACTION_MOVE_LEFT:
                self._change((_step_choice(SHADOW_WIDTHS, width, -1, SHADOW_WIDTH_DEFAULT), offset))
            elif action_id == ACTION_MOVE_RIGHT:
                self._change((_step_choice(SHADOW_WIDTHS, width, 1, SHADOW_WIDTH_DEFAULT), offset))
            elif action_id == ACTION_MOVE_UP:
                self._change((width, _step_choice(SHADOW_OFFSETS, offset, -1, SHADOW_OFFSET_DEFAULT)))
            elif action_id == ACTION_MOVE_DOWN:
                self._change((width, _step_choice(SHADOW_OFFSETS, offset, 1, SHADOW_OFFSET_DEFAULT)))
'''
new_shadow_actions = '''        if self.mode == "shadow":
            width, offset = self.value
            if action_id == ACTION_MOVE_LEFT:
                self._change((max(0, width - SHADOW_STEP), offset))
            elif action_id == ACTION_MOVE_RIGHT:
                self._change((width + SHADOW_STEP, offset))
            elif action_id == ACTION_MOVE_UP:
                self._change((width, max(0, offset - SHADOW_STEP)))
            elif action_id == ACTION_MOVE_DOWN:
                self._change((width, offset + SHADOW_STEP))
'''
if old_shadow_actions not in live:
    raise SystemExit('shadow action block not found')
live = live.replace(old_shadow_actions, new_shadow_actions, 1)
live = live.replace('return "Shadow    {} px / {} px".format(width, offset), "L/R: Width   ·   U/D: Offset   ·   OK: Save"', 'return "Shadow    Width {} px / Offset {} px".format(width, offset), "L/R: Width   ·   U/D: Offset   ·   OK: Save"', 1)
LIVE.write_text(live, encoding='utf-8')

addon = ADDON.read_text(encoding='utf-8')
addon = addon.replace('version="5.0.177"', 'version="5.0.178"', 1)
addon = re.sub(r'<news>5\.0\.177:.*?</news>', '<news>5.0.178: Correct live shadow geometry: offset moves right/down, width adds right/bottom spread, both in 1 px steps from 0.</news>', addon, count=1)
ADDON.write_text(addon, encoding='utf-8')


def png_chunk(kind, data):
    return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)


def write_rgba_png(path, width, height, pixel_fn):
    raw = bytearray()
    for y in range(height):
        raw.append(0)
        for x in range(width):
            raw.extend(pixel_fn(x, y))
    data = b'\x89PNG\r\n\x1a\n'
    data += png_chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0))
    data += png_chunk(b'IDAT', zlib.compress(bytes(raw), 9))
    data += png_chunk(b'IEND', b'')
    path.write_bytes(data)

MEDIA.mkdir(parents=True, exist_ok=True)
write_rgba_png(MEDIA / 'CCCoverShadowDynamicHard.png', 1, 1, lambda x, y: (0, 0, 0, 190))

def soft_pixel(x, y):
    edge = 8
    size = 24
    fx = 1.0 if x < size - edge else max(0.0, (size - 1 - x) / float(edge - 1))
    fy = 1.0 if y < size - edge else max(0.0, (size - 1 - y) / float(edge - 1))
    alpha = int(round(190 * min(fx, fy)))
    return (0, 0, 0, alpha)

write_rgba_png(MEDIA / 'CCCoverShadowDynamicSoft.png', 24, 24, soft_pixel)
print('5.0.178 patch applied')
