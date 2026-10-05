from pathlib import Path
import re

ROOT = Path('skin.confluence.custom')

# Version only.
p = ROOT / 'addon.xml'
text = p.read_text(encoding='utf-8')
assert 'version="5.0.185"' in text
p.write_text(text.replace('version="5.0.185"', 'version="5.0.186"', 1), encoding='utf-8')

# Integrate the four soft-shadow intensity choices into the existing
# Cover appearance chooser. Keep the underlying style/intensity settings
# separate so all existing XML visibility/render logic remains unchanged.
p = ROOT / 'resources/lib/mainmenu_style.py'
text = p.read_text(encoding='utf-8')

old_styles = '''HOME_COVER_STYLES = [
    ("frame", "Frame"),
    ("hardshadow", "Hard shadow"),
    ("softshadow", "Soft shadow"),
]
'''
assert old_styles in text
new_styles = old_styles + '''HOME_COVER_APPEARANCES = [
    ("frame", None, "Frame"),
    ("hardshadow", None, "Hard shadow"),
    ("softshadow", "dark", "Soft shadow - Dark"),
    ("softshadow", "medium", "Soft shadow - Medium"),
    ("softshadow", "light", "Soft shadow - Light"),
    ("softshadow", "verylight", "Soft shadow - Very light"),
]
'''
text = text.replace(old_styles, new_styles, 1)

old_choose = '''def choose_home_cover_style():
    _choose(
        "Home screen cover appearance",
        HOME_COVER_STYLE_SETTING,
        HOME_COVER_STYLES,
        DEFAULT_HOME_COVER_STYLE,
    )
'''
assert old_choose in text
new_choose = '''def choose_home_cover_style():
    current_style = _get(HOME_COVER_STYLE_SETTING, DEFAULT_HOME_COVER_STYLE).lower()
    if current_style == "shadow":
        current_style = "softshadow"
    current_intensity = _get(
        HOME_SOFT_SHADOW_INTENSITY_SETTING,
        DEFAULT_HOME_SOFT_SHADOW_INTENSITY,
    ).lower()

    preselect = 0
    for index, (style, intensity, _label) in enumerate(HOME_COVER_APPEARANCES):
        if style != current_style:
            continue
        if style != "softshadow" or intensity == current_intensity:
            preselect = index
            break

    labels = [item[2] for item in HOME_COVER_APPEARANCES]
    selected = xbmcgui.Dialog().select(
        "Home screen cover appearance", labels, preselect=preselect
    )
    if selected < 0:
        return

    style, intensity, _label = HOME_COVER_APPEARANCES[selected]
    _set(HOME_COVER_STYLE_SETTING, style)
    if intensity:
        _set(HOME_SOFT_SHADOW_INTENSITY_SETTING, intensity)
'''
text = text.replace(old_choose, new_choose, 1)

old_intensity_func = '''\n\ndef choose_home_soft_shadow_intensity():
    _choose(
        "Soft shadow intensity",
        HOME_SOFT_SHADOW_INTENSITY_SETTING,
        HOME_SOFT_SHADOW_INTENSITIES,
        DEFAULT_HOME_SOFT_SHADOW_INTENSITY,
    )
'''
assert old_intensity_func in text
text = text.replace(old_intensity_func, '', 1)

old_handler = '''    elif mode == "homeshadowintensity":
        choose_home_soft_shadow_intensity()
'''
assert old_handler in text
text = text.replace(old_handler, '', 1)

for required in (
    '("softshadow", "dark", "Soft shadow - Dark")',
    '("softshadow", "medium", "Soft shadow - Medium")',
    '("softshadow", "light", "Soft shadow - Light")',
    '("softshadow", "verylight", "Soft shadow - Very light")',
    'xbmcgui.Dialog().select(',
):
    assert required in text
assert 'def choose_home_soft_shadow_intensity()' not in text
assert 'homeshadowintensity' not in text
p.write_text(text, encoding='utf-8')

# Includes: add fourth, brighter intensity and make Cover appearance display
# the selected soft-shadow level directly.
p = ROOT / '1080p/Includes.xml'
text = p.read_text(encoding='utf-8')

old_setting = '''\t<variable name="CCHomeMusicSoftShadowIntensitySetting">\n\t\t<value condition="String.IsEqual(Skin.String(CCHomeMusicSoftShadowIntensity),dark)">Dark</value>\n\t\t<value condition="String.IsEqual(Skin.String(CCHomeMusicSoftShadowIntensity),light)">Light</value>\n\t\t<value>Medium</value>\n\t</variable>\n'''
assert old_setting in text
new_setting = '''\t<variable name="CCHomeMusicSoftShadowIntensitySetting">\n\t\t<value condition="String.IsEqual(Skin.String(CCHomeMusicSoftShadowIntensity),dark)">Dark</value>\n\t\t<value condition="String.IsEqual(Skin.String(CCHomeMusicSoftShadowIntensity),light)">Light</value>\n\t\t<value condition="String.IsEqual(Skin.String(CCHomeMusicSoftShadowIntensity),verylight)">Very light</value>\n\t\t<value>Medium</value>\n\t</variable>\n'''
text = text.replace(old_setting, new_setting, 1)

old_static = '''\t<variable name="CCHomeMusicSoftShadowStaticDiffuse">\n\t\t<value condition="String.IsEqual(Skin.String(CCHomeMusicSoftShadowIntensity),dark)">FFFFFFFF</value>\n\t\t<value condition="String.IsEqual(Skin.String(CCHomeMusicSoftShadowIntensity),light)">CCFFFFFF</value>\n\t\t<value>E6FFFFFF</value>\n\t</variable>\n'''
assert old_static in text
new_static = '''\t<variable name="CCHomeMusicSoftShadowStaticDiffuse">\n\t\t<value condition="String.IsEqual(Skin.String(CCHomeMusicSoftShadowIntensity),dark)">FFFFFFFF</value>\n\t\t<value condition="String.IsEqual(Skin.String(CCHomeMusicSoftShadowIntensity),light)">CCFFFFFF</value>\n\t\t<value condition="String.IsEqual(Skin.String(CCHomeMusicSoftShadowIntensity),verylight)">B3FFFFFF</value>\n\t\t<value>E6FFFFFF</value>\n\t</variable>\n'''
text = text.replace(old_static, new_static, 1)

# A fourth alpha ramp, one step lighter than Light. Geometry is untouched.
verylight = ['2A','25','21','1D','19','14','0F','08']
for i, vl in enumerate(verylight, 1):
    pattern = re.compile(
        rf'(\t<variable name="CCHomeMusicSoftShadowLayer{i}Diffuse">\n'
        rf'\t\t<value condition="String.IsEqual\(Skin.String\(CCHomeMusicSoftShadowIntensity\),dark\)">[0-9A-F]{{2}}000000</value>\n'
        rf'\t\t<value condition="String.IsEqual\(Skin.String\(CCHomeMusicSoftShadowIntensity\),light\)">[0-9A-F]{{2}}000000</value>\n)'
        rf'(\t\t<value>[0-9A-F]{{2}}000000</value>\n\t</variable>)'
    )
    text, count = pattern.subn(
        rf'\1\t\t<value condition="String.IsEqual(Skin.String(CCHomeMusicSoftShadowIntensity),verylight)">{vl}000000</value>\n\2',
        text,
        count=1,
    )
    assert count == 1, (i, count)

old_cover_style = '''\t<variable name="CCHomeMusicCoverStyleSetting">\n\t\t<value condition="String.IsEqual(Skin.String(CCHomeMusicCoverStyle),hardshadow)">Hard shadow</value>\n\t\t<value condition="String.IsEqual(Skin.String(CCHomeMusicCoverStyle),softshadow) | String.IsEqual(Skin.String(CCHomeMusicCoverStyle),shadow)">Soft shadow</value>\n\t\t<value>Frame</value>\n\t</variable>\n'''
assert old_cover_style in text
new_cover_style = '''\t<variable name="CCHomeMusicCoverStyleSetting">\n\t\t<value condition="String.IsEqual(Skin.String(CCHomeMusicCoverStyle),hardshadow)">Hard shadow</value>\n\t\t<value condition="[String.IsEqual(Skin.String(CCHomeMusicCoverStyle),softshadow) | String.IsEqual(Skin.String(CCHomeMusicCoverStyle),shadow)] + String.IsEqual(Skin.String(CCHomeMusicSoftShadowIntensity),dark)">Soft shadow - Dark</value>\n\t\t<value condition="[String.IsEqual(Skin.String(CCHomeMusicCoverStyle),softshadow) | String.IsEqual(Skin.String(CCHomeMusicCoverStyle),shadow)] + String.IsEqual(Skin.String(CCHomeMusicSoftShadowIntensity),light)">Soft shadow - Light</value>\n\t\t<value condition="[String.IsEqual(Skin.String(CCHomeMusicCoverStyle),softshadow) | String.IsEqual(Skin.String(CCHomeMusicCoverStyle),shadow)] + String.IsEqual(Skin.String(CCHomeMusicSoftShadowIntensity),verylight)">Soft shadow - Very light</value>\n\t\t<value condition="String.IsEqual(Skin.String(CCHomeMusicCoverStyle),softshadow) | String.IsEqual(Skin.String(CCHomeMusicCoverStyle),shadow)">Soft shadow - Medium</value>\n\t\t<value>Frame</value>\n\t</variable>\n'''
text = text.replace(old_cover_style, new_cover_style, 1)
p.write_text(text, encoding='utf-8')

# Remove the separate 5.0.185 setup row entirely.
p = ROOT / '1080p/SkinSettings.xml'
text = p.read_text(encoding='utf-8')
pattern = re.compile(r'\s*<control type="button" id="5900">.*?</control>\n', re.S)
text, count = pattern.subn('\n', text, count=1)
assert count == 1, count
assert 'Soft shadow intensity' not in text
assert 'homeshadowintensity' not in text
p.write_text(text, encoding='utf-8')

# Keep custom mode snapshots byte-identical to active files.
for name in ('Includes.xml', 'SkinSettings.xml'):
    src = ROOT / '1080p' / name
    dst = ROOT / 'resources/skin_modes/custom' / name
    dst.write_bytes(src.read_bytes())

print('5.0.186 patch applied')
