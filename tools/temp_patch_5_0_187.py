from pathlib import Path
import re

ROOT = Path('skin.confluence.custom')

# Version only.
p = ROOT / 'addon.xml'
text = p.read_text(encoding='utf-8')
assert 'version="5.0.186"' in text
p.write_text(text.replace('version="5.0.186"', 'version="5.0.187"', 1), encoding='utf-8')

# Keep shadow geometry/UI untouched. Only widen the four soft-shadow opacity levels.
p = ROOT / '1080p/Includes.xml'
text = p.read_text(encoding='utf-8')

static_block = '''\t<variable name="CCHomeMusicSoftShadowStaticDiffuse">\n\t\t<value condition="String.IsEqual(Skin.String(CCHomeMusicSoftShadowIntensity),dark)">FFFFFFFF</value>\n\t\t<value condition="String.IsEqual(Skin.String(CCHomeMusicSoftShadowIntensity),light)">80FFFFFF</value>\n\t\t<value condition="String.IsEqual(Skin.String(CCHomeMusicSoftShadowIntensity),verylight)">4DFFFFFF</value>\n\t\t<value>BFFFFFFF</value>\n\t</variable>'''
text, n = re.subn(r'\t<variable name="CCHomeMusicSoftShadowStaticDiffuse">.*?\t</variable>', static_block, text, count=1, flags=re.S)
assert n == 1

levels = {
    1: ('3C','2D','1E','12'),
    2: ('36','29','1B','10'),
    3: ('30','24','18','0E'),
    4: ('2A','20','15','0D'),
    5: ('24','1B','12','0B'),
    6: ('1E','17','0F','09'),
    7: ('16','11','0B','07'),
    8: ('0E','0B','07','04'),
}
for i, (dark, medium, light, verylight) in levels.items():
    block = f'''\t<variable name="CCHomeMusicSoftShadowLayer{i}Diffuse">\n\t\t<value condition="String.IsEqual(Skin.String(CCHomeMusicSoftShadowIntensity),dark)">{dark}000000</value>\n\t\t<value condition="String.IsEqual(Skin.String(CCHomeMusicSoftShadowIntensity),light)">{light}000000</value>\n\t\t<value condition="String.IsEqual(Skin.String(CCHomeMusicSoftShadowIntensity),verylight)">{verylight}000000</value>\n\t\t<value>{medium}000000</value>\n\t</variable>'''
    text, n = re.subn(rf'\t<variable name="CCHomeMusicSoftShadowLayer{i}Diffuse">.*?\t</variable>', block, text, count=1, flags=re.S)
    assert n == 1, i

p.write_text(text, encoding='utf-8')

# Custom mode snapshot must remain byte-identical.
(ROOT / 'resources/skin_modes/custom/Includes.xml').write_bytes(p.read_bytes())

print('5.0.187 patch applied')
