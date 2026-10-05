from pathlib import Path
import json
import re
import xml.etree.ElementTree as ET

ROOT = Path('skin.confluence.custom')


def read(path):
    return path.read_text(encoding='utf-8')


def write(path, text):
    path.write_text(text, encoding='utf-8')


# 1) Make the existing soft shadow a little more visible without touching geometry.
home_path = ROOT / '1080p' / 'Home.xml'
home = read(home_path)
alpha_by_layer = {
    1: '3C000000',
    2: '36000000',
    3: '30000000',
    4: '2A000000',
    5: '24000000',
    6: '1E000000',
    7: '16000000',
    8: '0E000000',
}
soft_matches = 0

def soft_repl(match):
    global soft_matches
    layer = int(match.group(2))
    soft_matches += 1
    return match.group(1) + alpha_by_layer[layer] + match.group(4)

home = re.sub(
    r'(<description>[^<]*soft shadow layer ([1-8])</description>.*?<texture colordiffuse=")([0-9A-Fa-f]{8})(">)',
    soft_repl,
    home,
)
if soft_matches != 32:
    raise SystemExit(f'Expected 32 dynamic soft-shadow layers, patched {soft_matches}')
write(home_path, home)
# Home is one of the custom-mode snapshot files; keep it byte-identical.
write(ROOT / 'resources' / 'skin_modes' / 'custom' / 'Home.xml', home)


# 2) Add the Setup option directly below Show track numbers.
settings_path = ROOT / '1080p' / 'SkinSettings.xml'
settings = read(settings_path)
if 'Show track times' in settings:
    raise SystemExit('Show track times already exists')
track_block = re.search(
    r'(\s*<control type="radiobutton" id="530">.*?</control>)',
    settings,
    flags=re.S,
)
if not track_block:
    raise SystemExit('Show track numbers control id 530 not found')
new_control = '''
\t\t\t\t\t\t<control type="radiobutton" id="548">
\t\t\t\t\t\t\t<width>1125</width><height>60</height><font>font13</font>
\t\t\t\t\t\t\t<label>Show track times</label><selected>String.IsEqual(Skin.String(CCSongSelectorShowTrackTimes),true)</selected>
\t\t\t\t\t\t\t<textcolor>grey2</textcolor><focusedcolor>white</focusedcolor><texturefocus>MenuItemFO.png</texturefocus><texturenofocus>MenuItemNF.png</texturenofocus>
\t\t\t\t\t\t\t<onclick>RunScript(special://skin/resources/lib/mainmenu_style.py,songtracktimes)</onclick>
\t\t\t\t\t\t\t<enable>$EXP[CCSongSelectorEnabled]</enable>
\t\t\t\t\t\t</control>'''
settings = settings[:track_block.end()] + new_control + settings[track_block.end():]
write(settings_path, settings)
write(ROOT / 'resources' / 'skin_modes' / 'custom' / 'SkinSettings.xml', settings)


# 3) Add title variables. Existing popup layout/focus/navigation stays untouched.
includes_path = ROOT / '1080p' / 'Includes.xml'
includes = read(includes_path)
if 'CCSongSelectorPopupTitleNoTrack' in includes:
    raise SystemExit('Track-time popup variables already exist')
anchor = '''\t<variable name="CCSongSelectorTrackNumbersSetting">
\t\t<value condition="String.IsEqual(Skin.String(CCSongSelectorShowTrackNumbers),true)">On</value>
\t\t<value>Off</value>
\t</variable>'''
if anchor not in includes:
    raise SystemExit('Track numbers setting variable anchor not found')
vars_xml = anchor + '''
\t<variable name="CCSongSelectorPopupTitleNoTrack">
\t\t<value condition="String.IsEqual(Skin.String(CCSongSelectorShowTrackTimes),true)">$INFO[ListItem.Title]$INFO[ListItem.Duration, | ]</value>
\t\t<value>$INFO[ListItem.Title]</value>
\t</variable>
\t<variable name="CCSongSelectorPopupTitleWithTrack">
\t\t<value condition="String.IsEqual(Skin.String(CCSongSelectorShowTrackTimes),true)">$INFO[ListItem.TrackNumber,,  ]$INFO[ListItem.Title]$INFO[ListItem.Duration, | ]</value>
\t\t<value>$INFO[ListItem.TrackNumber,,  ]$INFO[ListItem.Title]</value>
\t</variable>'''
includes = includes.replace(anchor, vars_xml, 1)
write(includes_path, includes)
write(ROOT / 'resources' / 'skin_modes' / 'custom' / 'Includes.xml', includes)


# 4) Point the two existing popup title paths at the new variables.
popup_path = ROOT / '1080p' / 'custom_1116_SongSelector.xml'
popup = read(popup_path)
plain_old = '<label>$INFO[ListItem.Title]</label>'
track_old = '<label>$INFO[ListItem.TrackNumber,,  ]$INFO[ListItem.Title]</label>'
if popup.count(plain_old) != 2 or popup.count(track_old) != 2:
    raise SystemExit(f'Unexpected popup label counts: plain={popup.count(plain_old)} track={popup.count(track_old)}')
popup = popup.replace(plain_old, '<label>$VAR[CCSongSelectorPopupTitleNoTrack]</label>')
popup = popup.replace(track_old, '<label>$VAR[CCSongSelectorPopupTitleWithTrack]</label>')
write(popup_path, popup)


# 5) Add setting/default/toggle to the existing settings helper.
style_path = ROOT / 'resources' / 'lib' / 'mainmenu_style.py'
style = read(style_path)
replacements = [
    ('SONG_SELECTOR_TRACK_SETTING = "CCSongSelectorShowTrackNumbers"\n',
     'SONG_SELECTOR_TRACK_SETTING = "CCSongSelectorShowTrackNumbers"\nSONG_SELECTOR_TRACK_TIME_SETTING = "CCSongSelectorShowTrackTimes"\n'),
    ('DEFAULT_SONG_SELECTOR_TRACK = "false"\n',
     'DEFAULT_SONG_SELECTOR_TRACK = "false"\nDEFAULT_SONG_SELECTOR_TRACK_TIME = "false"\n'),
    ('        (SONG_SELECTOR_TRACK_SETTING, DEFAULT_SONG_SELECTOR_TRACK),\n',
     '        (SONG_SELECTOR_TRACK_SETTING, DEFAULT_SONG_SELECTOR_TRACK),\n        (SONG_SELECTOR_TRACK_TIME_SETTING, DEFAULT_SONG_SELECTOR_TRACK_TIME),\n'),
    ('def toggle_song_selector_track_numbers():\n    current = _get(SONG_SELECTOR_TRACK_SETTING, DEFAULT_SONG_SELECTOR_TRACK).lower()\n    _set(SONG_SELECTOR_TRACK_SETTING, "false" if current == "true" else "true")\n\n\n',
     'def toggle_song_selector_track_numbers():\n    current = _get(SONG_SELECTOR_TRACK_SETTING, DEFAULT_SONG_SELECTOR_TRACK).lower()\n    _set(SONG_SELECTOR_TRACK_SETTING, "false" if current == "true" else "true")\n\n\ndef toggle_song_selector_track_times():\n    current = _get(SONG_SELECTOR_TRACK_TIME_SETTING, DEFAULT_SONG_SELECTOR_TRACK_TIME).lower()\n    _set(SONG_SELECTOR_TRACK_TIME_SETTING, "false" if current == "true" else "true")\n\n\n'),
    ('    elif mode == "songtracknumbers":\n        toggle_song_selector_track_numbers()\n',
     '    elif mode == "songtracknumbers":\n        toggle_song_selector_track_numbers()\n    elif mode == "songtracktimes":\n        toggle_song_selector_track_times()\n'),
]
for old, new in replacements:
    if old not in style:
        raise SystemExit(f'mainmenu_style.py anchor missing: {old[:70]!r}')
    style = style.replace(old, new, 1)
write(style_path, style)


# 6) Fresh-install snapshot: new option defaults to off.
defaults_path = ROOT / 'resources' / 'factory-default-settings.json'
defaults = read(defaults_path)
anchor_default = '{"id":"ccsongselectorshowtracknumbers","type":"string","value":"true"},'
if anchor_default not in defaults:
    raise SystemExit('Factory-default track-number anchor missing')
defaults = defaults.replace(
    anchor_default,
    anchor_default + '\n    {"id":"CCSongSelectorShowTrackTimes","type":"string","value":"false"},',
    1,
)
# Validate JSON after editing.
json.loads(defaults)
write(defaults_path, defaults)


# 7) Version/news.
addon_path = ROOT / 'addon.xml'
addon = read(addon_path)
addon, n = re.subn(r'version="5\.0\.180"', 'version="5.0.181"', addon, count=1)
if n != 1:
    raise SystemExit('addon version 5.0.180 not found')
addon, n = re.subn(
    r'<news>5\.0\.180:.*?</news>',
    '<news>5.0.181: Make the dynamic soft shadow more visible and add optional song durations to the song popup.</news>',
    addon,
    count=1,
)
if n != 1:
    raise SystemExit('5.0.180 news entry not found')
write(addon_path, addon)


# Final structural validation.
for xml_path in [
    ROOT / '1080p' / 'Home.xml',
    ROOT / '1080p' / 'SkinSettings.xml',
    ROOT / '1080p' / 'Includes.xml',
    ROOT / '1080p' / 'custom_1116_SongSelector.xml',
    ROOT / 'addon.xml',
]:
    ET.parse(xml_path)

if read(ROOT / '1080p' / 'Home.xml') != read(ROOT / 'resources' / 'skin_modes' / 'custom' / 'Home.xml'):
    raise SystemExit('Home active/custom mismatch')
if read(ROOT / '1080p' / 'SkinSettings.xml') != read(ROOT / 'resources' / 'skin_modes' / 'custom' / 'SkinSettings.xml'):
    raise SystemExit('SkinSettings active/custom mismatch')
if read(ROOT / '1080p' / 'Includes.xml') != read(ROOT / 'resources' / 'skin_modes' / 'custom' / 'Includes.xml'):
    raise SystemExit('Includes active/custom mismatch')

print('5.0.181 patch validated')
