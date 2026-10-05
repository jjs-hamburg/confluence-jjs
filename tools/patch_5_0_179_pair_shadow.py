from pathlib import Path
import base64, re

ROOT = Path('skin.confluence.custom')
HOME = ROOT / '1080p' / 'Home.xml'
CUSTOM_HOME = ROOT / 'resources' / 'skin_modes' / 'custom' / 'Home.xml'
LIVE = ROOT / 'resources' / 'lib' / 'live_home_adjust.py'
ADDON = ROOT / 'addon.xml'
MEDIA = ROOT / 'media'

home = HOME.read_text(encoding='utf-8')
old = '''\t\t\t\t<!-- 5.0.178: Dynamic selector pair front directional shadow. Geometry: x/y = cover + offset; size = cover + width. -->
\t\t\t\t<control type="image" id="9440"><description>Dynamic selector pair front directional shadow hard</description><left>0</left><top>0</top><width>195</width><height>195</height><texture>CCCoverShadowDynamicHard.png</texture><visible>Skin.HasSetting(CCHomeMusicCoverDynamic) + String.IsEqual(Skin.String(CCHomeMusicCoverStyle),hardshadow)</visible></control>
\t\t\t\t<control type="image" id="9450"><description>Dynamic selector pair front directional shadow soft</description><left>0</left><top>0</top><width>195</width><height>195</height><texture border="8">CCCoverShadowDynamicSoft.png</texture><visible>Skin.HasSetting(CCHomeMusicCoverDynamic) + [String.IsEqual(Skin.String(CCHomeMusicCoverStyle),softshadow) | String.IsEqual(Skin.String(CCHomeMusicCoverStyle),shadow)]</visible></control>
\t\t\t\t<!-- 5.0.178: Dynamic selector pair back directional shadow. Geometry: x/y = cover + offset; size = cover + width. -->
\t\t\t\t<control type="image" id="9460"><description>Dynamic selector pair back directional shadow hard</description><left>0</left><top>0</top><width>195</width><height>195</height><texture>CCCoverShadowDynamicHard.png</texture><visible>Skin.HasSetting(CCHomeMusicCoverDynamic) + String.IsEqual(Skin.String(CCHomeMusicCoverStyle),hardshadow)</visible></control>
\t\t\t\t<control type="image" id="9470"><description>Dynamic selector pair back directional shadow soft</description><left>0</left><top>0</top><width>195</width><height>195</height><texture border="8">CCCoverShadowDynamicSoft.png</texture><visible>Skin.HasSetting(CCHomeMusicCoverDynamic) + [String.IsEqual(Skin.String(CCHomeMusicCoverStyle),softshadow) | String.IsEqual(Skin.String(CCHomeMusicCoverStyle),shadow)]</visible></control>'''
new = '''\t\t\t\t<!-- 5.0.179: pair shadows are explicit right/bottom/corner pieces. This prevents any shadow from appearing above/left even when front/back artwork does not fill its nominal square control. -->
\t\t\t\t<control type="image" id="9440"><description>Dynamic pair front hard shadow right</description><left>-10000</left><top>-10000</top><width>1</width><height>1</height><texture>CCCoverShadowDynamicHard.png</texture><visible>Skin.HasSetting(CCHomeMusicCoverDynamic) + String.IsEqual(Skin.String(CCHomeMusicCoverStyle),hardshadow)</visible></control>
\t\t\t\t<control type="image" id="9441"><description>Dynamic pair front hard shadow bottom</description><left>-10000</left><top>-10000</top><width>1</width><height>1</height><texture>CCCoverShadowDynamicHard.png</texture><visible>Skin.HasSetting(CCHomeMusicCoverDynamic) + String.IsEqual(Skin.String(CCHomeMusicCoverStyle),hardshadow)</visible></control>
\t\t\t\t<control type="image" id="9442"><description>Dynamic pair front hard shadow corner</description><left>-10000</left><top>-10000</top><width>1</width><height>1</height><texture>CCCoverShadowDynamicHard.png</texture><visible>Skin.HasSetting(CCHomeMusicCoverDynamic) + String.IsEqual(Skin.String(CCHomeMusicCoverStyle),hardshadow)</visible></control>
\t\t\t\t<control type="image" id="9450"><description>Dynamic pair front soft shadow right</description><left>-10000</left><top>-10000</top><width>1</width><height>1</height><texture>CCCoverShadowDynamicSoftRight.png</texture><visible>Skin.HasSetting(CCHomeMusicCoverDynamic) + [String.IsEqual(Skin.String(CCHomeMusicCoverStyle),softshadow) | String.IsEqual(Skin.String(CCHomeMusicCoverStyle),shadow)]</visible></control>
\t\t\t\t<control type="image" id="9451"><description>Dynamic pair front soft shadow bottom</description><left>-10000</left><top>-10000</top><width>1</width><height>1</height><texture>CCCoverShadowDynamicSoftBottom.png</texture><visible>Skin.HasSetting(CCHomeMusicCoverDynamic) + [String.IsEqual(Skin.String(CCHomeMusicCoverStyle),softshadow) | String.IsEqual(Skin.String(CCHomeMusicCoverStyle),shadow)]</visible></control>
\t\t\t\t<control type="image" id="9452"><description>Dynamic pair front soft shadow corner</description><left>-10000</left><top>-10000</top><width>1</width><height>1</height><texture>CCCoverShadowDynamicSoft.png</texture><visible>Skin.HasSetting(CCHomeMusicCoverDynamic) + [String.IsEqual(Skin.String(CCHomeMusicCoverStyle),softshadow) | String.IsEqual(Skin.String(CCHomeMusicCoverStyle),shadow)]</visible></control>
\t\t\t\t<control type="image" id="9460"><description>Dynamic pair back hard shadow right</description><left>-10000</left><top>-10000</top><width>1</width><height>1</height><texture>CCCoverShadowDynamicHard.png</texture><visible>Skin.HasSetting(CCHomeMusicCoverDynamic) + String.IsEqual(Skin.String(CCHomeMusicCoverStyle),hardshadow)</visible></control>
\t\t\t\t<control type="image" id="9461"><description>Dynamic pair back hard shadow bottom</description><left>-10000</left><top>-10000</top><width>1</width><height>1</height><texture>CCCoverShadowDynamicHard.png</texture><visible>Skin.HasSetting(CCHomeMusicCoverDynamic) + String.IsEqual(Skin.String(CCHomeMusicCoverStyle),hardshadow)</visible></control>
\t\t\t\t<control type="image" id="9462"><description>Dynamic pair back hard shadow corner</description><left>-10000</left><top>-10000</top><width>1</width><height>1</height><texture>CCCoverShadowDynamicHard.png</texture><visible>Skin.HasSetting(CCHomeMusicCoverDynamic) + String.IsEqual(Skin.String(CCHomeMusicCoverStyle),hardshadow)</visible></control>
\t\t\t\t<control type="image" id="9470"><description>Dynamic pair back soft shadow right</description><left>-10000</left><top>-10000</top><width>1</width><height>1</height><texture>CCCoverShadowDynamicSoftRight.png</texture><visible>Skin.HasSetting(CCHomeMusicCoverDynamic) + [String.IsEqual(Skin.String(CCHomeMusicCoverStyle),softshadow) | String.IsEqual(Skin.String(CCHomeMusicCoverStyle),shadow)]</visible></control>
\t\t\t\t<control type="image" id="9471"><description>Dynamic pair back soft shadow bottom</description><left>-10000</left><top>-10000</top><width>1</width><height>1</height><texture>CCCoverShadowDynamicSoftBottom.png</texture><visible>Skin.HasSetting(CCHomeMusicCoverDynamic) + [String.IsEqual(Skin.String(CCHomeMusicCoverStyle),softshadow) | String.IsEqual(Skin.String(CCHomeMusicCoverStyle),shadow)]</visible></control>
\t\t\t\t<control type="image" id="9472"><description>Dynamic pair back soft shadow corner</description><left>-10000</left><top>-10000</top><width>1</width><height>1</height><texture>CCCoverShadowDynamicSoft.png</texture><visible>Skin.HasSetting(CCHomeMusicCoverDynamic) + [String.IsEqual(Skin.String(CCHomeMusicCoverStyle),softshadow) | String.IsEqual(Skin.String(CCHomeMusicCoverStyle),shadow)]</visible></control>'''
if old not in home:
    raise SystemExit('Expected 5.0.178 pair shadow block not found')
home = home.replace(old, new, 1)
HOME.write_text(home, encoding='utf-8')
CUSTOM_HOME.write_text(home, encoding='utf-8')

live = LIVE.read_text(encoding='utf-8')
old_map = '''DYNAMIC_SHADOW_CONTROLS = (
    (9400, 9410, "main"),
    (9420, 9430, "single"),
    (9440, 9450, "pair_front"),
    (9460, 9470, "pair_back"),
)
'''
new_map = '''DYNAMIC_SHADOW_CONTROLS = (
    (9400, 9410, "main"),
    (9420, 9430, "single"),
)
DYNAMIC_PAIR_SHADOW_CONTROLS = (
    ((9440, 9441, 9442), (9450, 9451, 9452), "pair_front"),
    ((9460, 9461, 9462), (9470, 9471, 9472), "pair_back"),
)
'''
if old_map not in live:
    raise SystemExit('Expected dynamic shadow map not found')
live = live.replace(old_map, new_map, 1)

old_apply = '''def _apply_dynamic_shadow_once(size):
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


'''
new_apply = '''def _set_shadow_piece(control, rect):
    if control is None:
        return
    if rect is None:
        _set_geometry(control, -10000, -10000, 1, 1)
        return
    _set_geometry(control, *rect)


def _pair_shadow_rects(cover_x, cover_y, size, width, offset):
    # Build the visible part of the shifted/enlarged shadow explicitly.
    # This is the rectangle S minus the cover rectangle C. Because offset
    # is never negative, the result is at most: right strip, bottom strip,
    # and bottom-right corner. No control is ever drawn above or left.
    size = int(size)
    width = max(0, int(width))
    offset = max(0, int(offset))
    shadow_x = int(cover_x) + offset
    shadow_y = int(cover_y) + offset
    shadow_right = shadow_x + size + width
    shadow_bottom = shadow_y + size + width
    cover_right = int(cover_x) + size
    cover_bottom = int(cover_y) + size

    right_x = max(cover_right, shadow_x)
    right_y = shadow_y
    right_w = shadow_right - right_x
    right_h = min(cover_bottom, shadow_bottom) - right_y

    bottom_x = shadow_x
    bottom_y = max(cover_bottom, shadow_y)
    bottom_w = min(cover_right, shadow_right) - bottom_x
    bottom_h = shadow_bottom - bottom_y

    corner_x = max(cover_right, shadow_x)
    corner_y = max(cover_bottom, shadow_y)
    corner_w = shadow_right - corner_x
    corner_h = shadow_bottom - corner_y

    def rect(x, y, w, h):
        return (x, y, w, h) if w > 0 and h > 0 else None

    return (
        rect(right_x, right_y, right_w, right_h),
        rect(bottom_x, bottom_y, bottom_w, bottom_h),
        rect(corner_x, corner_y, corner_w, corner_h),
    )


def _apply_dynamic_shadow_once(size):
    window = xbmcgui.Window(HOME_WINDOW_ID)
    width = max(0, _skin_int(SHADOW_WIDTH_SETTING, SHADOW_WIDTH_DEFAULT))
    offset = max(0, _skin_int(SHADOW_OFFSET_SETTING, SHADOW_OFFSET_DEFAULT))

    # Keep the already verified 5.0.178 whole-rectangle path for main/single.
    extent = max(1, int(size) + width)
    for hard_id, soft_id, kind in DYNAMIC_SHADOW_CONTROLS:
        cover_x, cover_y = _shadow_cover_rect(kind, size)
        x = cover_x + offset
        y = cover_y + offset
        _set_geometry(_control(window, hard_id), x, y, extent, extent)
        _set_geometry(_control(window, soft_id), x, y, extent, extent)

    # 5.0.179: pair artwork uses explicit visible pieces. This avoids relying
    # on the cover image to mask the shadow inside its nominal square control.
    for hard_ids, soft_ids, kind in DYNAMIC_PAIR_SHADOW_CONTROLS:
        cover_x, cover_y = _shadow_cover_rect(kind, size)
        rects = _pair_shadow_rects(cover_x, cover_y, size, width, offset)
        for control_id, rect in zip(hard_ids, rects):
            _set_shadow_piece(_control(window, control_id), rect)
        for control_id, rect in zip(soft_ids, rects):
            _set_shadow_piece(_control(window, control_id), rect)


'''
if old_apply not in live:
    raise SystemExit('Expected 5.0.178 apply block not found')
live = live.replace(old_apply, new_apply, 1)
LIVE.write_text(live, encoding='utf-8')

addon = ADDON.read_text(encoding='utf-8')
addon = addon.replace('version="5.0.178"', 'version="5.0.179"', 1)
addon = re.sub(r'<news>.*?</news>', '<news>5.0.179: Fix front/back pair shadows by drawing only explicit right, bottom and corner pieces; no shadow can appear above or left.</news>', addon, count=1, flags=re.S)
ADDON.write_text(addon, encoding='utf-8')

(MEDIA / 'CCCoverShadowDynamicSoftRight.png').write_bytes(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAABgAAAABCAYAAADErm6rAAAAFUlEQVR4nGNkYGDYx0A5eIqEnyDzAZciBwIxsmo8AAAAAElFTkSuQmCC'))
(MEDIA / 'CCCoverShadowDynamicSoftBottom.png').write_bytes(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAAYCAYAAAA7zJfaAAAAI0lEQVR4nK3EMREAAAQAwD819K8hDT3Mdj88VMBzc+vAQIIFv7kFfLIQlbQAAAAASUVORK5CYII='))
