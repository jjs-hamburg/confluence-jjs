from pathlib import Path
import re,sys
R=Path(sys.argv[1] if len(sys.argv)>1 else '.')/'skin.confluence.custom'
def rd(p): return (R/p).read_text()
def wr(p,s): (R/p).write_text(s)
def sub(s,p,r,n=1):
 s,c=re.subn(p,r,s,count=n,flags=re.S)
 if c!=n: raise RuntimeError((p[:60],c,n))
 return s
for p in ('1080p/SkinSettings.xml','resources/skin_modes/custom/SkinSettings.xml'):
 s=rd(p); s=sub(s,r'\n\s*<control type="button" id="519">.*?</control>',''); wr(p,s)
badge='''<include name="CCMusicViewChangeBadge">
		<control type="group">
			<width>470</width><height>74</height>
			<control type="image"><left>0</left><top>0</top><width>470</width><height>74</height><texture border="18,0,18,0" colordiffuse="$VAR[CCAudioBadgeColorDiffuse]">$VAR[CCTimeBadgeTexturePath]</texture></control>
			<control type="image"><left>0</left><top>0</top><width>470</width><height>74</height><texture border="18,0,18,0">CCTimeBadge3D.png</texture><visible>String.IsEqual(Skin.String(CCAudioBadge3D),true)</visible></control>
			<control type="label"><left>16</left><top>7</top><width>438</width><height>29</height><label>Change Music View</label><font>font_CCSub_RobotoBold_20</font><align>center</align><aligny>center</aligny><textcolor>FFFFFFFF</textcolor><shadowcolor>AA000000</shadowcolor></control>
			<control type="label"><left>16</left><top>36</top><width>438</width><height>29</height><label>L/R: Size   ·   Enter: Change   ·   Down: Leave</label><font>font_CCSub_Roboto_20</font><align>center</align><aligny>center</aligny><textcolor>FFFFFFFF</textcolor><shadowcolor>AA000000</shadowcolor><visible>String.IsEqual(Skin.String(CCMusicArtworkMode),front) | String.IsEqual(Skin.String(CCMusicArtworkMode),both) | [Skin.HasSetting(CCHomeMusicDisplayAboveMenu) + [String.IsEqual(Skin.String(CCMusicArtworkMode),infofront) | String.IsEqual(Skin.String(CCMusicArtworkMode),infoboth)]]</visible></control>
			<control type="label"><left>16</left><top>36</top><width>438</width><height>29</height><label>Enter: Change   ·   Down: Leave</label><font>font_CCSub_Roboto_20</font><align>center</align><aligny>center</aligny><textcolor>FFFFFFFF</textcolor><shadowcolor>AA000000</shadowcolor><visible>!String.IsEqual(Skin.String(CCMusicArtworkMode),front) + !String.IsEqual(Skin.String(CCMusicArtworkMode),both) + [!Skin.HasSetting(CCHomeMusicDisplayAboveMenu) | [!String.IsEqual(Skin.String(CCMusicArtworkMode),infofront) + !String.IsEqual(Skin.String(CCMusicArtworkMode),infoboth)]]</visible></control>
		</control>
	</include>'''
for p in ('1080p/Includes.xml','resources/skin_modes/custom/Includes.xml'):
 s=rd(p); s=sub(s,r'<include name="CCMusicViewChangeBadge">.*?</include>',badge); s=s.replace('<!-- 5.0.173: two-line focus guide using the exact time-badge surface. -->','<!-- 5.0.182: Change Music View with context-sensitive live sizing. -->'); wr(p,s)
spec=[('main',9400,range(9700,9732),'$VAR[CCNowPlayingFrontArt]'),('selector single',9420,range(9740,9772),'$VAR[CCNowPlayingPrimaryArt]'),('selector pair front',9440,range(9780,9812),'$VAR[CCNowPlayingFrontArt]'),('selector pair back',9460,range(9820,9852),'$VAR[CCNowPlayingBackArt]')]
oldids=list(range(9410,9418))+list(range(9430,9438))+list(range(9450,9458))+list(range(9470,9478)); al=[round(16-12*i/31) for i in range(32)]
dyn='''\n\t\t\t\t<!-- 5.0.182: live-sized info artwork only for Above Menu. -->
\t\t\t\t<control type="group"><visible>Skin.HasSetting(CCHomeMusicDisplayAboveMenu) + [String.IsEqual(Skin.String(CCMusicArtworkMode),infofront) | [String.IsEqual(Skin.String(CCMusicArtworkMode),infoboth) + String.IsEmpty(Window(Home).Property(ConfluenceCustom.MusicBackArt))]]</visible><control type="image" id="9480"><left>-20</left><top>-187</top><width>1800</width><height>302</height><aspectratio align="left" aligny="bottom">keep</aspectratio><texture fallback="$VAR[CCGlobalNoCover]">$VAR[CCNowPlayingFrontArt]</texture></control></control>
\t\t\t\t<control type="group"><visible>Skin.HasSetting(CCHomeMusicDisplayAboveMenu) + String.IsEqual(Skin.String(CCMusicArtworkMode),infoboth) + !String.IsEmpty(Window(Home).Property(ConfluenceCustom.MusicBackArt))</visible><control type="image" id="9481"><left>-20</left><top>-187</top><width>1800</width><height>302</height><aspectratio align="left" aligny="bottom">keep</aspectratio><texture fallback="$VAR[CCGlobalNoCover]">$VAR[CCNowPlayingFrontArt]</texture></control><control type="image" id="9482"><left>292</left><top>-187</top><width>1800</width><height>302</height><aspectratio align="left" aligny="bottom">keep</aspectratio><texture>$VAR[CCNowPlayingBackArt]</texture></control></control>'''
for p in ('1080p/Home.xml','resources/skin_modes/custom/Home.xml'):
 s=rd(p); s=s.replace('<onleft>9150</onleft><onright>9150</onright>','<onleft>RunScript(special://skin/resources/lib/cover_display_action.py,smaller)</onleft><onright>RunScript(special://skin/resources/lib/cover_display_action.py,larger)</onright>',1)
 for i in oldids: s=sub(s,rf'\s*<control type="image" id="{i}"><description>.*?soft shadow layer \d+</description>.*?</control>','')
 for d,h,ids,art in spec:
  m=re.search(rf'<control type="image" id="{h}"><description>.*?</control>',s,re.S)
  if not m: raise RuntimeError(('hard',h))
  z=''.join(f'\n\t\t\t\t<control type="image" id="{i}"><description>Dynamic {d} soft shadow layer {j}</description><left>-10000</left><top>-10000</top><width>1</width><height>1</height><aspectratio>keep</aspectratio><texture colordiffuse="{a:02X}000000">{art}</texture><visible>Skin.HasSetting(CCHomeMusicCoverDynamic) + [String.IsEqual(Skin.String(CCHomeMusicCoverStyle),softshadow) | String.IsEqual(Skin.String(CCHomeMusicCoverStyle),shadow)]</visible></control>' for j,(i,a) in enumerate(zip(ids,al),1))
  s=s[:m.end()]+z+s[m.end():]
 s=s.replace('<visible>String.IsEqual(Skin.String(CCMusicArtworkMode),infofront) | [String.IsEqual(Skin.String(CCMusicArtworkMode),infoboth) + String.IsEmpty(Window(Home).Property(ConfluenceCustom.MusicBackArt))]</visible>','<visible>!Skin.HasSetting(CCHomeMusicDisplayAboveMenu) + [String.IsEqual(Skin.String(CCMusicArtworkMode),infofront) | [String.IsEqual(Skin.String(CCMusicArtworkMode),infoboth) + String.IsEmpty(Window(Home).Property(ConfluenceCustom.MusicBackArt))]]</visible>',1)
 s=s.replace('<visible>String.IsEqual(Skin.String(CCMusicArtworkMode),infoboth) + !String.IsEmpty(Window(Home).Property(ConfluenceCustom.MusicBackArt))</visible>','<visible>!Skin.HasSetting(CCHomeMusicDisplayAboveMenu) + String.IsEqual(Skin.String(CCMusicArtworkMode),infoboth) + !String.IsEmpty(Window(Home).Property(ConfluenceCustom.MusicBackArt))</visible>',1)
 marker='\t\t\t</control>\n\t\t\t<!-- 5.0.126: compact artwork has a fixed 115 px height only. -->'
 if marker not in s: raise RuntimeError(('marker',p))
 s=s.replace(marker,dyn+marker,1); wr(p,s)
p='resources/lib/cover_display_action.py'; s=rd(p); s=s.replace('import struct\n','import struct\nimport sys\n',1); s=s.replace('INFO_MAX_IMAGE_WIDTH = 1800\n','INFO_MAX_IMAGE_WIDTH = 1800\nCOVER_SIZE_SETTING="CCHomeMusicCoverSize"\nINFO_COVER_SIZE_SETTING="CCHomeMusicInfoCoverSize"\nCOVER_DYNAMIC_SETTING="CCHomeMusicCoverDynamic"\nABOVE_MENU_SETTING="CCHomeMusicDisplayAboveMenu"\nCOVER_SIZE_STEP=25\nCOVER_SIZE_MIN=25\n',1)
s=s.replace('def main():','def cycle_view():',1)
insert='''
# 5.0.182 live sizing -------------------------------------------------------
_old_info_height = _info_cover_height
_old_sync_info = sync_info_cover_geometry

def _above_menu(): return xbmc.getCondVisibility("Skin.HasSetting({})".format(ABOVE_MENU_SETTING))
def _get_int(name,default):
    try: return int((xbmc.getInfoLabel("Skin.String({})".format(name)) or str(default)).strip())
    except Exception: return int(default)
def _set_int(name,value): xbmc.executebuiltin("Skin.SetString({},{})".format(name,int(value)))
def _current_mode(): return (xbmc.getInfoLabel("Skin.String({})".format(SETTING)) or "front").strip().lower()
def _info_cover_height():
    natural=_old_info_height(); mode=_current_mode()
    if _above_menu() and mode in ("infofront","infoboth"):
        raw=(xbmc.getInfoLabel("Skin.String({})".format(INFO_COVER_SIZE_SETTING)) or "").strip()
        requested=_get_int(INFO_COVER_SIZE_SETTING,natural) if raw else natural
        return max(2,min(natural,requested))
    return natural

def _geom(cid,x,y,w,h):
    try:
        c=_home().getControl(cid); c.setPosition(int(x),int(y)); c.setWidth(max(1,int(w))); c.setHeight(max(1,int(h)))
    except Exception: pass

def sync_info_cover_geometry(mode=None):
    result=_old_sync_info(mode); mode=(mode or _current_mode()).lower()
    if _above_menu() and mode in ("infofront","infoboth"):
        h=_info_cover_height(); m=music_view_margin(); f=xbmc.getInfoLabel("Player.Art(thumb)") or ""; fw=_info_art_width(f,h); top=115-h
        _geom(9480,-20,top,INFO_MAX_IMAGE_WIDTH,h); _geom(9481,-20,top,INFO_MAX_IMAGE_WIDTH,h); _geom(9482,-20+fw+m,top,INFO_MAX_IMAGE_WIDTH,h)
        back=_home().getProperty(BACK_PROP) or ""; bw=_info_art_width(back,h) if back else 0
        single=max(0,fw+2*m-30); pair=max(0,fw+bw+3*m-30); bs=max(0,fw+m); ts=pair if mode=="infoboth" and back else single
        home=_home(); home.setProperty(INFO_FRONT_WIDTH_PROP,str(fw)); home.setProperty(INFO_BACK_SHIFT_PROP,str(bs)); home.setProperty(INFO_TEXT_SHIFT_PROP,str(ts)); _set_shift_digits(home,INFO_BACK_SHIFT_PROP,bs); _set_shift_digits(home,INFO_TEXT_SHIFT_PROP,ts)
        if back: home.setProperty(INFO_BACK_WIDTH_PROP,str(bw))
    return result

def resize_cover(direction):
    sync_back_art(); mode=_current_mode(); delta=COVER_SIZE_STEP if direction>0 else -COVER_SIZE_STEP
    if mode in ("front","both"):
        v=max(COVER_SIZE_MIN,_get_int(COVER_SIZE_SETTING,195)+delta); _set_int(COVER_SIZE_SETTING,v); xbmc.executebuiltin("Skin.SetBool({})".format(COVER_DYNAMIC_SETTING))
        try:
            from live_home_adjust import apply_dynamic_cover; apply_dynamic_cover(v)
        except Exception: pass
    elif _above_menu() and mode in ("infofront","infoboth"):
        natural=_old_info_height(); raw=(xbmc.getInfoLabel("Skin.String({})".format(INFO_COVER_SIZE_SETTING)) or "").strip(); cur=min(_get_int(INFO_COVER_SIZE_SETTING,natural) if raw else natural,natural); _set_int(INFO_COVER_SIZE_SETTING,min(natural,max(COVER_SIZE_MIN,cur+delta))); sync_info_cover_geometry(mode)

def main(action="change"):
    a=(action or "change").lower()
    if a=="smaller": resize_cover(-1)
    elif a=="larger": resize_cover(1)
    else: cycle_view()
'''
s=s.replace('\n\nif __name__ == "__main__":\n    main()\n',insert+'\nif __name__ == "__main__":\n    main(sys.argv[1] if len(sys.argv)>1 else "change")\n',1); wr(p,s)
p='resources/lib/live_home_adjust.py'; s=rd(p); s=s.replace('(9400, tuple(range(9410, 9418)), "main"),(9420, tuple(range(9430, 9438)), "single"),(9440, tuple(range(9450, 9458)), "pair_front"),(9460, tuple(range(9470, 9478)), "pair_back"),'.replace('),(', '),\n    ('),'(9400, tuple(range(9700, 9732)), "main"),\n    (9420, tuple(range(9740, 9772)), "single"),\n    (9440, tuple(range(9780, 9812)), "pair_front"),\n    (9460, tuple(range(9820, 9852)), "pair_back"),',1); s=s.replace('SOFT_SHADOW_LAYERS = 8','SOFT_SHADOW_LAYERS = 32',1)
s=sub(s,r'def _soft_shadow_shifts\(extent\):.*?\n\n\ndef _apply_dynamic_shadow_once','''def _soft_shadow_plan(extent):
    extent=max(0,int(extent))
    if not extent: return {}
    count=min(SOFT_SHADOW_LAYERS,extent)
    if count==1: return {0:extent}
    return {int(round(i*float(SOFT_SHADOW_LAYERS-1)/float(count-1))):max(1,int(round((i+1)*float(extent)/float(count)))) for i in range(count)}


def _apply_dynamic_shadow_once''')
s=s.replace('shifts = _soft_shadow_shifts(extent)','plan = _soft_shadow_plan(extent)',1); s=s.replace('if index < len(shifts):\n                shift = shifts[index]','if index in plan:\n                shift = plan[index]',1); wr(p,s)
p='addon.xml'; s=rd(p).replace('version="5.0.181"','version="5.0.182"',1).replace('5.0.181: Make the dynamic soft shadow more visible and add optional song durations to the song popup.','5.0.182: Smooth the soft shadow and move live cover sizing into Change Music View.',1); wr(p,s)
print('patched 5.0.182')
