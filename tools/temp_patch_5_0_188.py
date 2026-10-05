from pathlib import Path
import re

ROOT = Path('skin.confluence.custom')

# Version only.
p = ROOT / 'addon.xml'
text = p.read_text(encoding='utf-8')
assert 'version="5.0.187"' in text
p.write_text(text.replace('version="5.0.187"', 'version="5.0.188"', 1), encoding='utf-8')

# Integrated selector: keep only the three brighter 5.0.187 levels.
p = ROOT / 'resources/lib/mainmenu_style.py'
text = p.read_text(encoding='utf-8')
old = '''HOME_COVER_APPEARANCES = [
    ("frame", None, "Frame"),
    ("hardshadow", None, "Hard shadow"),
    ("softshadow", "dark", "Soft shadow - Dark"),
    ("softshadow", "medium", "Soft shadow - Medium"),
    ("softshadow", "light", "Soft shadow - Light"),
    ("softshadow", "verylight", "Soft shadow - Very light"),
]
'''
new = '''HOME_COVER_APPEARANCES = [
    ("frame", None, "Frame"),
    ("hardshadow", None, "Hard shadow"),
    ("softshadow", "dark", "Soft shadow - Dark"),
    ("softshadow", "medium", "Soft shadow - Medium"),
    ("softshadow", "light", "Soft shadow - Light"),
]
'''
assert old in text
text = text.replace(old, new, 1)
# Preserve the visual choice for anyone coming from the 5.0.187 Very light test level.
needle = '''    if _get(HOME_COVER_STYLE_SETTING).lower() == "shadow":
        _set(HOME_COVER_STYLE_SETTING, "softshadow")
'''
assert needle in text
replacement = needle + '''    if _get(HOME_SOFT_SHADOW_INTENSITY_SETTING).lower() == "verylight":
        _set(HOME_SOFT_SHADOW_INTENSITY_SETTING, "light")
'''
text = text.replace(needle, replacement, 1)
p.write_text(text, encoding='utf-8')

# Re-map opacity values: new Dark=old Medium, new Medium=old Light, new Light=old Very light.
for rel in ('1080p/Includes.xml',):
    p = ROOT / rel
    text = p.read_text(encoding='utf-8')
    names = ['CCHomeMusicSoftShadowStaticDiffuse'] + [f'CCHomeMusicSoftShadowLayer{i}Diffuse' for i in range(1,9)]
    for name in names:
        pat = re.compile(r'(\t<variable name="' + re.escape(name) + r'">\n)(.*?)(\t</variable>)', re.S)
        m = pat.search(text)
        assert m, name
        body = m.group(2)
        dark = re.search(r'<value condition="String\.IsEqual\(Skin\.String\(CCHomeMusicSoftShadowIntensity\),dark\)">([^<]+)</value>', body)
        light = re.search(r'<value condition="String\.IsEqual\(Skin\.String\(CCHomeMusicSoftShadowIntensity\),light\)">([^<]+)</value>', body)
        very = re.search(r'<value condition="String\.IsEqual\(Skin\.String\(CCHomeMusicSoftShadowIntensity\),verylight\)">([^<]+)</value>', body)
        default = re.search(r'\t\t<value>([^<]+)</value>', body)
        assert dark and light and very and default, name
        new_body = (
            '\t\t<value condition="String.IsEqual(Skin.String(CCHomeMusicSoftShadowIntensity),dark)">' + default.group(1) + '</value>\n'
            '\t\t<value condition="String.IsEqual(Skin.String(CCHomeMusicSoftShadowIntensity),light)">' + very.group(1) + '</value>\n'
            '\t\t<value>' + light.group(1) + '</value>\n'
        )
        text = text[:m.start()] + m.group(1) + new_body + m.group(3) + text[m.end():]

    # Label variables: remove Very light option from visible labels.
    text = re.sub(r'\n\t\t<value condition="String\.IsEqual\(Skin\.String\(CCHomeMusicSoftShadowIntensity\),verylight\)">Very light</value>', '', text, count=1)
    text = re.sub(r'\n\t\t<value condition="\[String\.IsEqual\(Skin\.String\(CCHomeMusicCoverStyle\),softshadow\) \| String\.IsEqual\(Skin\.String\(CCHomeMusicCoverStyle\),shadow\)\] \+ String\.IsEqual\(Skin\.String\(CCHomeMusicSoftShadowIntensity\),verylight\)">Soft shadow - Very light</value>', '', text, count=1)
    assert 'Soft shadow - Very light' not in text
    p.write_text(text, encoding='utf-8')

# Keep custom snapshot byte-identical.
(ROOT/'resources/skin_modes/custom/Includes.xml').write_bytes((ROOT/'1080p/Includes.xml').read_bytes())

print('5.0.188 patch applied')
