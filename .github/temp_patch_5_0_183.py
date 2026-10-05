from pathlib import Path
import re
import sys

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else '.')
SKIN = ROOT / 'skin.confluence.custom'


def rd(path):
    return (SKIN / path).read_text(encoding='utf-8')


def wr(path, text):
    (SKIN / path).write_text(text, encoding='utf-8')


def sub_once(text, pattern, repl, label):
    out, count = re.subn(pattern, repl, text, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError('%s: expected one replacement, got %d' % (label, count))
    return out


# 1) Setup: remove the old standalone Music cover size row.
settings = rd('1080p/SkinSettings.xml')
settings = sub_once(
    settings,
    r'\n\s*<control type="button" id="519">.*?</control>',
    '',
    'remove Music cover size setup row',
)
wr('1080p/SkinSettings.xml', settings)
wr('resources/skin_modes/custom/SkinSettings.xml', settings)


# 2) Change Music View badge: bold heading and context-sensitive L/R hint.
includes = rd('1080p/Includes.xml')
expr_anchor = '<expression name="CCHomeCurrentMainHasSubMenu">'
if 'name="CCMusicViewSizeAdjustable"' not in includes:
    idx = includes.index(expr_anchor)
    expression = '\t<expression name="CCMusicViewSizeAdjustable">String.IsEqual(Skin.String(CCMusicArtworkMode),front) | String.IsEqual(Skin.String(CCMusicArtworkMode),both) | [Skin.HasSetting(CCHomeMusicDisplayAboveMenu) + [String.IsEqual(Skin.String(CCMusicArtworkMode),infofront) | String.IsEqual(Skin.String(CCMusicArtworkMode),infoboth)]]</expression>\n'
    includes = includes[:idx] + expression + includes[idx:]

badge = '''<include name="CCMusicViewChangeBadge">
		<control type="group">
			<width>470</width><height>74</height>
			<control type="image">
				<left>0</left><top>0</top><width>470</width><height>74</height>
				<texture border="18,0,18,0" colordiffuse="$VAR[CCAudioBadgeColorDiffuse]">$VAR[CCTimeBadgeTexturePath]</texture>
			</control>
			<control type="image">
				<left>0</left><top>0</top><width>470</width><height>74</height>
				<texture border="18,0,18,0">CCTimeBadge3D.png</texture>
				<visible>String.IsEqual(Skin.String(CCAudioBadge3D),true)</visible>
			</control>
			<control type="label">
				<left>16</left><top>7</top><width>438</width><height>29</height>
				<label>Change Music View</label><font>font_CCSub_RobotoBold_20</font>
				<align>center</align><aligny>center</aligny><textcolor>FFFFFFFF</textcolor><shadowcolor>AA000000</shadowcolor>
			</control>
			<control type="label">
				<left>16</left><top>36</top><width>438</width><height>29</height>
				<label>L/R: Size   ·   Enter: Change   ·   Down: Leave</label><font>font_CCSub_Roboto_20</font>
				<align>center</align><aligny>center</aligny><textcolor>FFFFFFFF</textcolor><shadowcolor>AA000000</shadowcolor>
				<visible>$EXP[CCMusicViewSizeAdjustable]</visible>
			</control>
			<control type="label">
				<left>16</left><top>36</top><width>438</width><height>29</height>
				<label>Enter: Change   ·   Down: Leave</label><font>font_CCSub_Roboto_20</font>
				<align>center</align><aligny>center</aligny><textcolor>FFFFFFFF</textcolor><shadowcolor>AA000000</shadowcolor>
				<visible>!$EXP[CCMusicViewSizeAdjustable]</visible>
			</control>
		</control>
	</include>'''
includes = sub_once(includes, r'<include name="CCMusicViewChangeBadge">.*?</include>', badge, 'replace Change Music View badge')
includes = includes.replace('<!-- 5.0.173: two-line focus guide using the exact time-badge surface. -->', '<!-- 5.0.183: Change Music View with context-sensitive live sizing. -->', 1)
wr('1080p/Includes.xml', includes)
wr('resources/skin_modes/custom/Includes.xml', includes)


# 3) Home: live L/R actions, dynamic info artwork, and resizeable info text controls.
home = rd('1080p/Home.xml')
onload_anchor = '\t<onload condition="Skin.HasSetting(CCHomeMusicCoverDynamic)">RunScript(special://skin/resources/lib/live_home_adjust.py,apply)</onload>\n'
if onload_anchor not in home:
    raise RuntimeError('main dynamic cover onload anchor missing')
home = home.replace(onload_anchor, onload_anchor + '\t<onload condition="Skin.HasSetting(CCHomeMusicInfoCoverDynamic)">RunScript(special://skin/resources/lib/cover_display_action.py,apply)</onload>\n', 1)

nav_old = '<onleft>9150</onleft><onright>9150</onright>'
nav_new = '<onleft>RunScript(special://skin/resources/lib/cover_display_action.py,smaller)</onleft><onright>RunScript(special://skin/resources/lib/cover_display_action.py,larger)</onright>'
if home.count(nav_old) != 1:
    raise RuntimeError('9150 L/R anchor count is %d' % home.count(nav_old))
home = home.replace(nav_old, nav_new, 1)

# Assign IDs to the twelve 1830px album/song labels inside the existing InfoTextShift tree.
start = home.index('InfoTextShiftThousands')
end = home.index('<control type="grouplist" id="9140">', start)
segment = home[start:end]
blocks = list(re.finditer(r'<control type="label">.*?</control>', segment, flags=re.S))
targets = [m for m in blocks if '<width>1830</width>' in m.group(0)]
if len(targets) != 12:
    raise RuntimeError('expected 12 dynamic-width labels, got %d' % len(targets))
for control_id, match in reversed(list(zip(range(9500, 9512), targets))):
    block = match.group(0).replace('<control type="label">', '<control type="label" id="%d">' % control_id, 1)
    segment = segment[:match.start()] + block + segment[match.end():]
home = home[:start] + segment + home[end:]

front_visible = '<visible>String.IsEqual(Skin.String(CCMusicArtworkMode),infofront) | [String.IsEqual(Skin.String(CCMusicArtworkMode),infoboth) + String.IsEmpty(Window(Home).Property(ConfluenceCustom.MusicBackArt))]</visible>'
pair_visible = '<visible>String.IsEqual(Skin.String(CCMusicArtworkMode),infoboth) + !String.IsEmpty(Window(Home).Property(ConfluenceCustom.MusicBackArt))</visible>'
if home.count(front_visible) != 1 or home.count(pair_visible) != 1:
    raise RuntimeError('static info artwork visibility anchors changed')

# Put the dynamic controls immediately before the proven static infofront group.
front_vis_pos = home.index(front_visible)
front_group_pos = home.rfind('<control type="group">', 0, front_vis_pos)
if front_group_pos < 0:
    raise RuntimeError('infofront group start not found')
dynamic_art = '''<!-- 5.0.183: dynamic info-side artwork. Static controls remain the fallback when Above Menu is off. -->
			<control type="image" id="9480">
				<description>Dynamic info-side single front</description><left>-20</left><top>-187</top><width>1800</width><height>302</height>
				<aspectratio align="left" aligny="bottom">keep</aspectratio><texture fallback="$VAR[CCGlobalNoCover]">$VAR[CCNowPlayingFrontArt]</texture>
				<visible>Skin.HasSetting(CCHomeMusicInfoCoverDynamic) + Skin.HasSetting(CCHomeMusicDisplayAboveMenu) + [String.IsEqual(Skin.String(CCMusicArtworkMode),infofront) | [String.IsEqual(Skin.String(CCMusicArtworkMode),infoboth) + String.IsEmpty(Window(Home).Property(ConfluenceCustom.MusicBackArt))]]</visible>
			</control>
			<control type="image" id="9481">
				<description>Dynamic info-side pair front</description><left>-20</left><top>-187</top><width>1800</width><height>302</height>
				<aspectratio align="left" aligny="bottom">keep</aspectratio><texture fallback="$VAR[CCGlobalNoCover]">$VAR[CCNowPlayingFrontArt]</texture>
				<visible>Skin.HasSetting(CCHomeMusicInfoCoverDynamic) + Skin.HasSetting(CCHomeMusicDisplayAboveMenu) + String.IsEqual(Skin.String(CCMusicArtworkMode),infoboth) + !String.IsEmpty(Window(Home).Property(ConfluenceCustom.MusicBackArt))</visible>
			</control>
			<control type="image" id="9482">
				<description>Dynamic info-side pair back</description><left>292</left><top>-187</top><width>1800</width><height>302</height>
				<aspectratio align="left" aligny="bottom">keep</aspectratio><texture>$VAR[CCNowPlayingBackArt]</texture>
				<visible>Skin.HasSetting(CCHomeMusicInfoCoverDynamic) + Skin.HasSetting(CCHomeMusicDisplayAboveMenu) + String.IsEqual(Skin.String(CCMusicArtworkMode),infoboth) + !String.IsEmpty(Window(Home).Property(ConfluenceCustom.MusicBackArt))</visible>
			</control>
			'''
home = home[:front_group_pos] + dynamic_art + home[front_group_pos:]

home = home.replace(front_visible, '<visible>[String.IsEqual(Skin.String(CCMusicArtworkMode),infofront) | [String.IsEqual(Skin.String(CCMusicArtworkMode),infoboth) + String.IsEmpty(Window(Home).Property(ConfluenceCustom.MusicBackArt))]] + [!Skin.HasSetting(CCHomeMusicInfoCoverDynamic) | !Skin.HasSetting(CCHomeMusicDisplayAboveMenu)]</visible>', 1)
home = home.replace(pair_visible, '<visible>String.IsEqual(Skin.String(CCMusicArtworkMode),infoboth) + !String.IsEmpty(Window(Home).Property(ConfluenceCustom.MusicBackArt)) + [!Skin.HasSetting(CCHomeMusicInfoCoverDynamic) | !Skin.HasSetting(CCHomeMusicDisplayAboveMenu)]</visible>', 1)

wr('1080p/Home.xml', home)
wr('resources/skin_modes/custom/Home.xml', home)


# 4) cover_display_action.py: one clean geometry path, no monkey-patching/redefinition.
cover = rd('resources/lib/cover_display_action.py')
cover = cover.replace('import struct\n', 'import struct\nimport sys\n', 1)
const_anchor = 'INFO_MAX_IMAGE_WIDTH = 1800\n'
if const_anchor not in cover:
    raise RuntimeError('cover constants anchor missing')
cover = cover.replace(const_anchor, const_anchor + '''COVER_SIZE_SETTING = "CCHomeMusicCoverSize"\nCOVER_DYNAMIC_SETTING = "CCHomeMusicCoverDynamic"\nINFO_COVER_SIZE_SETTING = "CCHomeMusicInfoCoverSize"\nINFO_DYNAMIC_SETTING = "CCHomeMusicInfoCoverDynamic"\nABOVE_MENU_SETTING = "CCHomeMusicDisplayAboveMenu"\nCOVER_SIZE_STEP = 25\nCOVER_SIZE_MIN = 25\nINFO_TEXT_BASE_WIDTH = 1830\nINFO_TEXT_MIN_WIDTH = 240\nINFO_SINGLE_FRONT_ID = 9480\nINFO_PAIR_FRONT_ID = 9481\nINFO_PAIR_BACK_ID = 9482\nINFO_TEXT_CONTROL_IDS = tuple(range(9500, 9512)) + (9140, 9141, 9104)\nINFO_TEXT_WIDTH_PROP = "ConfluenceCustom.NowPlaying.InfoTextWidth"\nINFO_DYNAMIC_GEOMETRY_PROP = "ConfluenceCustom.NowPlaying.InfoDynamicGeometry"\n''', 1)

new_sync = r'''def _skin_string(name, default=""):
    value = xbmc.getInfoLabel("Skin.String({})".format(name))
    return value if value else default


def _skin_int(name, default):
    try:
        return int(_skin_string(name, str(default)))
    except (TypeError, ValueError):
        return int(default)


def _set_skin_string(name, value):
    xbmc.executebuiltin("Skin.SetString({},{})".format(name, int(value)))


def _set_skin_bool(name):
    xbmc.executebuiltin("Skin.SetBool({})".format(name))


def _has_setting(name):
    return xbmc.getCondVisibility("Skin.HasSetting({})".format(name))


def _current_mode():
    return (_skin_string(SETTING, "front") or "front").strip().lower()


def _home_control(home, control_id):
    try:
        return home.getControl(int(control_id))
    except Exception:
        return None


def _set_geometry(control, x, y, width, height):
    if control is None:
        return False
    try:
        control.setPosition(int(x), int(y))
        control.setWidth(max(1, int(width)))
        control.setHeight(max(1, int(height)))
        return True
    except Exception:
        return False


def _set_info_text_width(home, width):
    width = max(INFO_TEXT_MIN_WIDTH, min(INFO_TEXT_BASE_WIDTH, int(width)))
    cached = home.getProperty(INFO_TEXT_WIDTH_PROP) or ""
    if cached == str(width):
        return True
    changed = 0
    for control_id in INFO_TEXT_CONTROL_IDS:
        control = _home_control(home, control_id)
        if control is not None:
            try:
                control.setWidth(width)
                changed += 1
            except Exception:
                pass
    if changed == len(INFO_TEXT_CONTROL_IDS):
        home.setProperty(INFO_TEXT_WIDTH_PROP, str(width))
        return True
    home.clearProperty(INFO_TEXT_WIDTH_PROP)
    return False


def _apply_dynamic_info_art(home, mode, height, front_width, back_width, margin, back_art):
    key = "{}|{}|{}|{}|{}|{}".format(mode, int(height), int(front_width), int(back_width), int(margin), 1 if back_art else 0)
    if home.getProperty(INFO_DYNAMIC_GEOMETRY_PROP) == key:
        return True
    top = 115 - int(height)
    if mode == "infoboth" and back_art:
        ok_front = _set_geometry(_home_control(home, INFO_PAIR_FRONT_ID), -20, top, INFO_MAX_IMAGE_WIDTH, height)
        ok_back = _set_geometry(_home_control(home, INFO_PAIR_BACK_ID), -20 + front_width + margin, top, INFO_MAX_IMAGE_WIDTH, height)
        ok = ok_front and ok_back
    else:
        ok = _set_geometry(_home_control(home, INFO_SINGLE_FRONT_ID), -20, top, INFO_MAX_IMAGE_WIDTH, height)
    if ok:
        home.setProperty(INFO_DYNAMIC_GEOMETRY_PROP, key)
    else:
        home.clearProperty(INFO_DYNAMIC_GEOMETRY_PROP)
    return ok


def sync_info_cover_geometry(mode=None):
    """Publish artwork geometry and keep the footer text edge aligned.

    The established static geometry remains untouched unless the user has
    explicitly resized an info-side cover and Above Menu is enabled. In that
    dynamic case artwork, text start, text width and wrap width all derive from
    the same real artwork dimensions.
    """
    home = _home()
    mode = (mode or _current_mode()).strip().lower()
    natural_height = _info_cover_height()
    dynamic_info = (
        _has_setting(INFO_DYNAMIC_SETTING)
        and _has_setting(ABOVE_MENU_SETTING)
        and mode in ("infofront", "infoboth")
    )
    if dynamic_info:
        requested = max(COVER_SIZE_MIN, _skin_int(INFO_COVER_SIZE_SETTING, natural_height))
        height = min(natural_height, requested)
    else:
        height = natural_height

    front_art = xbmc.getInfoLabel("Player.Art(thumb)") or ""
    back_art = home.getProperty(BACK_PROP) or ""
    front_width = _info_art_width(front_art, height)
    back_width = _info_art_width(back_art, height) if back_art else 0
    margin = music_view_margin()

    single_shift = max(0, front_width + (2 * margin) - 30)
    pair_shift = max(0, front_width + back_width + (3 * margin) - 30)
    back_shift = max(0, front_width + margin)

    if mode == "infofront":
        text_shift = single_shift
    elif mode == "infoboth":
        text_shift = pair_shift if back_art else single_shift
    elif mode == "compact":
        try:
            compact_width = int(home.getProperty(COMPACT_WIDTH_PROP) or COMPACT_WIDTH_FALLBACK)
        except Exception:
            compact_width = COMPACT_WIDTH_FALLBACK
        text_shift = max(0, compact_width + (2 * margin) - 30)
    else:
        text_shift = 0

    home.setProperty(INFO_FRONT_WIDTH_PROP, str(front_width))
    if back_art:
        home.setProperty(INFO_BACK_WIDTH_PROP, str(back_width))
    else:
        home.clearProperty(INFO_BACK_WIDTH_PROP)
    home.setProperty(INFO_BACK_SHIFT_PROP, str(back_shift))
    home.setProperty(INFO_TEXT_SHIFT_PROP, str(text_shift))
    _set_shift_digits(home, INFO_BACK_SHIFT_PROP, back_shift)
    _set_shift_digits(home, INFO_TEXT_SHIFT_PROP, text_shift)

    if dynamic_info:
        _apply_dynamic_info_art(home, mode, height, front_width, back_width, margin, back_art)
        _set_info_text_width(home, max(INFO_TEXT_MIN_WIDTH, INFO_TEXT_BASE_WIDTH - text_shift))
    else:
        home.clearProperty(INFO_DYNAMIC_GEOMETRY_PROP)
        _set_info_text_width(home, INFO_TEXT_BASE_WIDTH)
    return text_shift


'''
cover = sub_once(cover, r'def sync_info_cover_geometry\(mode=None\):.*?(?=def compact_cover_width)', new_sync, 'replace info geometry function')

new_main = r'''def _resize_cover(direction):
    sync_back_art()
    mode = _current_mode()
    delta = COVER_SIZE_STEP if direction > 0 else -COVER_SIZE_STEP

    if mode in ("front", "both"):
        current = max(COVER_SIZE_MIN, _skin_int(COVER_SIZE_SETTING, 195))
        value = max(COVER_SIZE_MIN, current + delta)
        if value == current:
            return
        _set_skin_string(COVER_SIZE_SETTING, value)
        _set_skin_bool(COVER_DYNAMIC_SETTING)
        try:
            from live_home_adjust import apply_dynamic_cover
            apply_dynamic_cover(value)
        except Exception:
            pass
        return

    if mode in ("infofront", "infoboth") and _has_setting(ABOVE_MENU_SETTING):
        natural = _info_cover_height()
        if _has_setting(INFO_DYNAMIC_SETTING):
            current = max(COVER_SIZE_MIN, min(natural, _skin_int(INFO_COVER_SIZE_SETTING, natural)))
        else:
            current = natural
        value = max(COVER_SIZE_MIN, min(natural, current + delta))
        if value == current:
            return
        _set_skin_string(INFO_COVER_SIZE_SETTING, value)
        _set_skin_bool(INFO_DYNAMIC_SETTING)
        # Clear the cache before the first switch from the proven static controls.
        _home().clearProperty(INFO_DYNAMIC_GEOMETRY_PROP)
        sync_info_cover_geometry(mode)


def _cycle_view():
    # Proven 5.0.170 order: centered front -> centered front+back -> large
    # front beside info -> large front+back beside info -> compact -> none.
    has_back = bool(sync_back_art())
    sync_compact_cover_width()
    mode = _current_mode()
    if mode == "front":
        new_mode = "both" if has_back else "infofront"
    elif mode == "both":
        new_mode = "infofront"
    elif mode == "infofront":
        new_mode = "infoboth" if has_back else "compact"
    elif mode == "infoboth":
        new_mode = "compact"
    elif mode == "compact":
        new_mode = "none"
    else:
        new_mode = "front"
    xbmc.executebuiltin("Skin.SetString({},{})".format(SETTING, new_mode))
    sync_info_cover_geometry(mode=new_mode)


def main(action="change"):
    action = (action or "change").strip().lower()
    if action == "smaller":
        _resize_cover(-1)
    elif action == "larger":
        _resize_cover(1)
    elif action == "apply":
        sync_back_art()
        sync_compact_cover_width()
        sync_info_cover_geometry()
    else:
        _cycle_view()


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "change")
'''
cover = sub_once(cover, r'def main\(\):.*?if __name__ == "__main__":\n\s*main\(\)\n?', new_main, 'replace cover action main')
wr('resources/lib/cover_display_action.py', cover)


# 5) Smooth the soft edge using the SAME eight artwork silhouettes. No extra
# image controls: for a 30px shadow the fade samples 23..30 in 1px steps.
shadow = rd('resources/lib/live_home_adjust.py')
new_shifts = '''def _soft_shadow_shifts(extent):
    extent = max(0, int(extent))
    if extent <= 0:
        return ()
    count = min(SOFT_SHADOW_LAYERS, extent)
    start = extent - count + 1
    return tuple(range(start, extent + 1))
'''
shadow = sub_once(shadow, r'def _soft_shadow_shifts\(extent\):.*?(?=\n\ndef _apply_dynamic_shadow_once)', new_shifts.rstrip(), 'smooth eight-layer soft shadow')
wr('resources/lib/live_home_adjust.py', shadow)


# 6) Version metadata.
addon = rd('addon.xml')
addon = addon.replace('version="5.0.181"', 'version="5.0.183"', 1)
addon = sub_once(addon, r'<news>.*?</news>', '<news>5.0.183: Move cover sizing into Change Music View, add coordinated dynamic info-side artwork/text sizing, and smooth the soft shadow without additional image layers.</news>', 'update news')
wr('addon.xml', addon)

print('patched 5.0.183 from the restored 5.0.181 tree')
