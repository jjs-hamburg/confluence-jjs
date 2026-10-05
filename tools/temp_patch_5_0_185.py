from pathlib import Path
import re

ROOT = Path('skin.confluence.custom')

# Version
p = ROOT / 'addon.xml'
text = p.read_text(encoding='utf-8')
assert 'version="5.0.184"' in text
p.write_text(text.replace('version="5.0.184"', 'version="5.0.185"', 1), encoding='utf-8')

# Main menu style setting/default/options/handler.
p = ROOT / 'resources/lib/mainmenu_style.py'
text = p.read_text(encoding='utf-8')
text = text.replace(
    'HOME_SHADOW_OFFSET_SETTING = "CCHomeMusicShadowOffset"\n',
    'HOME_SHADOW_OFFSET_SETTING = "CCHomeMusicShadowOffset"\nHOME_SOFT_SHADOW_INTENSITY_SETTING = "CCHomeMusicSoftShadowIntensity"\n',
    1,
)
text = text.replace(
    'DEFAULT_HOME_SHADOW_OFFSET = "4"\n',
    'DEFAULT_HOME_SHADOW_OFFSET = "4"\nDEFAULT_HOME_SOFT_SHADOW_INTENSITY = "medium"\n',
    1,
)
text = text.replace(
    'HOME_SHADOW_OFFSETS = [("0", "0 px"), ("2", "2 px"), ("4", "4 px"), ("6", "6 px"), ("8", "8 px"), ("10", "10 px"), ("12", "12 px"), ("14", "14 px"), ("16", "16 px"), ("18", "18 px"), ("20", "20 px"), ("22", "22 px"), ("24", "24 px")]\n',
    'HOME_SHADOW_OFFSETS = [("0", "0 px"), ("2", "2 px"), ("4", "4 px"), ("6", "6 px"), ("8", "8 px"), ("10", "10 px"), ("12", "12 px"), ("14", "14 px"), ("16", "16 px"), ("18", "18 px"), ("20", "20 px"), ("22", "22 px"), ("24", "24 px")]\nHOME_SOFT_SHADOW_INTENSITIES = [("dark", "Dark"), ("medium", "Medium"), ("light", "Light")]\n',
    1,
)
text = text.replace(
    '        (HOME_SHADOW_OFFSET_SETTING, DEFAULT_HOME_SHADOW_OFFSET),\n',
    '        (HOME_SHADOW_OFFSET_SETTING, DEFAULT_HOME_SHADOW_OFFSET),\n        (HOME_SOFT_SHADOW_INTENSITY_SETTING, DEFAULT_HOME_SOFT_SHADOW_INTENSITY),\n',
    1,
)
needle = '''def choose_home_cover_style():\n    _choose(\n        "Home screen cover appearance",\n        HOME_COVER_STYLE_SETTING,\n        HOME_COVER_STYLES,\n        DEFAULT_HOME_COVER_STYLE,\n    )\n'''
assert needle in text
text = text.replace(
    needle,
    needle + '''\n\ndef choose_home_soft_shadow_intensity():\n    _choose(\n        "Soft shadow intensity",\n        HOME_SOFT_SHADOW_INTENSITY_SETTING,\n        HOME_SOFT_SHADOW_INTENSITIES,\n        DEFAULT_HOME_SOFT_SHADOW_INTENSITY,\n    )\n''',
    1,
)
text = text.replace(
    '    elif mode == "homecoverstyle":\n        choose_home_cover_style()\n',
    '    elif mode == "homecoverstyle":\n        choose_home_cover_style()\n    elif mode == "homeshadowintensity":\n        choose_home_soft_shadow_intensity()\n',
    1,
)
for required in (
    'HOME_SOFT_SHADOW_INTENSITY_SETTING = "CCHomeMusicSoftShadowIntensity"',
    'DEFAULT_HOME_SOFT_SHADOW_INTENSITY = "medium"',
    'def choose_home_soft_shadow_intensity():',
    'elif mode == "homeshadowintensity":',
):
    assert required in text
p.write_text(text, encoding='utf-8')

# Includes: labels + dynamic per-layer alpha vars + static shadow alpha multiplier.
p = ROOT / '1080p/Includes.xml'
text = p.read_text(encoding='utf-8')
marker = '''\t<variable name="CCHomeMusicCoverStyleSetting">'''
pos = text.index(marker)
# Insert just before CoverStyle variable so the group stays together.
dark = ['3C','36','30','2A','24','1E','16','0E']
medium = ['36','31','2B','26','20','1B','14','0C']
light = ['30','2B','26','21','1D','18','12','0A']
vars_xml = '''\t<variable name="CCHomeMusicSoftShadowIntensitySetting">\n\t\t<value condition="String.IsEqual(Skin.String(CCHomeMusicSoftShadowIntensity),dark)">Dark</value>\n\t\t<value condition="String.IsEqual(Skin.String(CCHomeMusicSoftShadowIntensity),light)">Light</value>\n\t\t<value>Medium</value>\n\t</variable>\n\t<variable name="CCHomeMusicSoftShadowStaticDiffuse">\n\t\t<value condition="String.IsEqual(Skin.String(CCHomeMusicSoftShadowIntensity),dark)">FFFFFFFF</value>\n\t\t<value condition="String.IsEqual(Skin.String(CCHomeMusicSoftShadowIntensity),light)">CCFFFFFF</value>\n\t\t<value>E6FFFFFF</value>\n\t</variable>\n'''
for i, (d, m, l) in enumerate(zip(dark, medium, light), 1):
    vars_xml += f'''\t<variable name="CCHomeMusicSoftShadowLayer{i}Diffuse">\n\t\t<value condition="String.IsEqual(Skin.String(CCHomeMusicSoftShadowIntensity),dark)">{d}000000</value>\n\t\t<value condition="String.IsEqual(Skin.String(CCHomeMusicSoftShadowIntensity),light)">{l}000000</value>\n\t\t<value>{m}000000</value>\n\t</variable>\n'''
assert 'CCHomeMusicSoftShadowIntensitySetting' not in text
text = text[:pos] + vars_xml + text[pos:]

# Apply the intensity multiplier only to the static SOFT border includes, never hard shadow.
pattern = re.compile(r'(<include name="CCHomeMusicShadowBorder(?:High)?Soft\d+">)(<bordertexture)')
text, static_count = pattern.subn(r'\1<colordiffuse>$VAR[CCHomeMusicSoftShadowStaticDiffuse]</colordiffuse>\2', text)
assert static_count == 9, static_count
p.write_text(text, encoding='utf-8')

# Home: dynamic soft layers keep exactly the same 32 controls and geometry; only diffuse is variable.
p = ROOT / '1080p/Home.xml'
text = p.read_text(encoding='utf-8')
pattern = re.compile(r'(<description>Dynamic [^<]* soft shadow layer ([1-8])</description>.*?<texture )colordiffuse="[0-9A-Fa-f]{8}"', re.S)

def repl(match):
    layer = match.group(2)
    return match.group(1) + f'colordiffuse="$VAR[CCHomeMusicSoftShadowLayer{layer}Diffuse]"'

text, dynamic_count = pattern.subn(repl, text)
assert dynamic_count == 32, dynamic_count
p.write_text(text, encoding='utf-8')

# Setup row directly beneath Shadow.
p = ROOT / '1080p/SkinSettings.xml'
text = p.read_text(encoding='utf-8')
assert 'id="550"' not in text
shadow_row = '''\t\t\t\t\t\t<control type="button" id="546">\n\t\t\t\t\t\t\t<width>1125</width><height>60</height><font>font13</font>\n\t\t\t\t\t\t\t<label>Shadow</label><label2>[COLOR=selected]$VAR[CCHomeMusicShadowWidthSetting] / $VAR[CCHomeMusicShadowOffsetSetting][/COLOR]</label2>\n\t\t\t\t\t\t\t<textcolor>grey2</textcolor><focusedcolor>white</focusedcolor><texturefocus>MenuItemFO.png</texturefocus><texturenofocus>MenuItemNF.png</texturenofocus>\n\t\t\t\t\t\t\t<onclick>RunScript(special://skin/resources/lib/live_home_adjust.py,shadow)</onclick>\n\t\t\t\t\t\t\t<enable>String.IsEqual(Skin.String(CCHomeMusicCoverStyle),hardshadow) | String.IsEqual(Skin.String(CCHomeMusicCoverStyle),softshadow) | String.IsEqual(Skin.String(CCHomeMusicCoverStyle),shadow)</enable>\n\t\t\t\t\t\t</control>\n'''
assert shadow_row in text
new_row = '''\t\t\t\t\t\t<control type="button" id="550">\n\t\t\t\t\t\t\t<width>1125</width><height>60</height><font>font13</font>\n\t\t\t\t\t\t\t<label>Soft shadow intensity</label><label2>[COLOR=selected]$VAR[CCHomeMusicSoftShadowIntensitySetting][/COLOR]</label2>\n\t\t\t\t\t\t\t<textcolor>grey2</textcolor><focusedcolor>white</focusedcolor><texturefocus>MenuItemFO.png</texturefocus><texturenofocus>MenuItemNF.png</texturenofocus>\n\t\t\t\t\t\t\t<onclick>RunScript(special://skin/resources/lib/mainmenu_style.py,homeshadowintensity)</onclick>\n\t\t\t\t\t\t\t<enable>String.IsEqual(Skin.String(CCHomeMusicCoverStyle),softshadow) | String.IsEqual(Skin.String(CCHomeMusicCoverStyle),shadow)</enable>\n\t\t\t\t\t\t</control>\n'''
text = text.replace(shadow_row, shadow_row + new_row, 1)
p.write_text(text, encoding='utf-8')

# Factory publication default = Medium.
p = ROOT / 'resources/factory-default-settings.json'
text = p.read_text(encoding='utf-8')
needle = '    {"id":"cchomemusicshadowoffset","type":"string","value":"24"},\n'
assert needle in text
text = text.replace(needle, needle + '    {"id":"cchomemusicsoftshadowintensity","type":"string","value":"medium"},\n', 1)
p.write_text(text, encoding='utf-8')

# Keep custom mode snapshots byte-identical to active files.
for name in ('Home.xml', 'Includes.xml', 'SkinSettings.xml'):
    src = ROOT / '1080p' / name
    dst = ROOT / 'resources/skin_modes/custom' / name
    dst.write_bytes(src.read_bytes())

print('5.0.185 patch applied')
