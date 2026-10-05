# -*- coding: utf-8 -*-
from __future__ import absolute_import

import math
import struct
import sys
import urllib.parse

import xbmc
import xbmcgui
import xbmcvfs

SETTING = "CCMusicArtworkMode"
HOME_ID = 10000
BACK_PROP = "ConfluenceCustom.MusicBackArt"
COMPACT_WIDTH_PROP = "ConfluenceCustom.NowPlaying.CompactCoverWidth"
INFO_FRONT_WIDTH_PROP = "ConfluenceCustom.NowPlaying.InfoFrontWidth"
INFO_BACK_WIDTH_PROP = "ConfluenceCustom.NowPlaying.InfoBackWidth"
INFO_BACK_SHIFT_PROP = "ConfluenceCustom.NowPlaying.InfoBackShift"
INFO_TEXT_SHIFT_PROP = "ConfluenceCustom.NowPlaying.InfoTextShift"
INFO_MARGIN_SETTING = "CCHomeMusicViewMargin"
INFO_MARGIN_DEFAULT = 10
INFO_DEFAULT_HEIGHT = 322
INFO_MAX_IMAGE_WIDTH = 1800
COVER_SIZE_SETTING="CCHomeMusicCoverSize"
INFO_COVER_SIZE_SETTING="CCHomeMusicInfoCoverSize"
COVER_DYNAMIC_SETTING="CCHomeMusicCoverDynamic"
ABOVE_MENU_SETTING="CCHomeMusicDisplayAboveMenu"
COVER_SIZE_STEP=25
COVER_SIZE_MIN=25
COMPACT_HEIGHT = 115
COMPACT_WIDTH_STEP = 10
COMPACT_WIDTH_MIN = 30
COMPACT_WIDTH_MAX = 800
COMPACT_WIDTH_FALLBACK = 120
_COMPACT_WIDTH_CACHE = {}
_ART_RATIO_CACHE = {}


def _home():
    return xbmcgui.Window(HOME_ID)


def _folder_back_art():
    try:
        playing_file = xbmc.Player().getPlayingFile() or ""
    except Exception:
        playing_file = ""
    if not playing_file:
        return ""
    normalized = playing_file.replace("\\", "/")
    if "/" not in normalized:
        return ""
    folder = normalized.rsplit("/", 1)[0] + "/"
    # back.jpg is the collection convention. The two fallbacks cost nothing and
    # make the feature tolerant of older folders without creating any files.
    for name in ("back.jpg", "back.jpeg", "back.png"):
        candidate = folder + name
        try:
            if xbmcvfs.exists(candidate):
                return candidate
        except Exception:
            pass
    return ""


def resolve_back_art():
    # The collection convention is back.jpg next to the music. Prefer that
    # exact album-local file; Kodi artwork remains a fallback.
    return (
        _folder_back_art()
        or xbmc.getInfoLabel("Player.Art(album.back)")
        or xbmc.getInfoLabel("Player.Art(back)")
        or ""
    )


def sync_back_art():
    art = resolve_back_art()
    home = _home()
    if art:
        home.setProperty(BACK_PROP, art)
    else:
        home.clearProperty(BACK_PROP)
    return art


def _image_candidates(art):
    value = str(art or "").strip()
    if not value:
        return []
    candidates = [value]
    if value.lower().startswith("image://"):
        payload = urllib.parse.unquote(value[8:])
        candidates.extend([payload, payload.rstrip("/")])
    else:
        decoded = urllib.parse.unquote(value)
        if decoded != value:
            candidates.append(decoded)
    result = []
    for candidate in candidates:
        if candidate and candidate not in result:
            result.append(candidate)
    return result


def _read_image_header(path, limit=262144):
    handle = None
    try:
        handle = xbmcvfs.File(path)
        data = handle.readBytes(int(limit))
        if isinstance(data, str):
            data = data.encode("latin1", "ignore")
        return bytes(data or b"")
    except Exception:
        return b""
    finally:
        if handle is not None:
            try:
                handle.close()
            except Exception:
                pass


def _jpeg_size(data):
    if len(data) < 4 or data[:2] != b"\xff\xd8":
        return None
    sof = {0xC0,0xC1,0xC2,0xC3,0xC5,0xC6,0xC7,0xC9,0xCA,0xCB,0xCD,0xCE,0xCF}
    pos=2; length=len(data)
    while pos+4<=length:
        while pos<length and data[pos]!=0xFF: pos+=1
        while pos<length and data[pos]==0xFF: pos+=1
        if pos>=length: break
        marker=data[pos]; pos+=1
        if marker in (0xD8,0xD9): continue
        if marker==0xDA: break
        if pos+2>length: break
        seglen=struct.unpack(">H",data[pos:pos+2])[0]
        if seglen<2 or pos+seglen>length: break
        if marker in sof and seglen>=7:
            height=struct.unpack(">H",data[pos+3:pos+5])[0]; width=struct.unpack(">H",data[pos+5:pos+7])[0]
            return (width,height) if width and height else None
        pos+=seglen
    return None


def _image_size(data):
    if len(data)>=24 and data[:8]==b"\x89PNG\r\n\x1a\n":
        width,height=struct.unpack(">II",data[16:24]); return (width,height) if width and height else None
    if len(data)>=10 and data[:6] in (b"GIF87a",b"GIF89a"):
        width,height=struct.unpack("<HH",data[6:10]); return (width,height) if width and height else None
    if len(data)>=26 and data[:2]==b"BM":
        width,height=struct.unpack("<ii",data[18:26]); width,height=abs(width),abs(height); return (width,height) if width and height else None
    jpeg=_jpeg_size(data)
    if jpeg: return jpeg
    if len(data)>=30 and data[:4]==b"RIFF" and data[8:12]==b"WEBP":
        chunk=data[12:16]
        if chunk==b"VP8X" and len(data)>=30:
            width=1+int.from_bytes(data[24:27],"little"); height=1+int.from_bytes(data[27:30],"little"); return (width,height) if width and height else None
        if chunk==b"VP8L" and len(data)>=25 and data[20]==0x2F:
            bits=int.from_bytes(data[21:25],"little"); width=(bits&0x3FFF)+1; height=((bits>>14)&0x3FFF)+1; return (width,height) if width and height else None
        if chunk==b"VP8 " and len(data)>=30:
            marker=data.find(b"\x9d\x01\x2a",20,min(len(data),80))
            if marker>=0 and marker+7<=len(data):
                width=struct.unpack("<H",data[marker+3:marker+5])[0]&0x3FFF; height=struct.unpack("<H",data[marker+5:marker+7])[0]&0x3FFF; return (width,height) if width and height else None
    return None


def _art_ratio(art):
    cache_key=str(art or "")
    if not cache_key: return 1.0
    if cache_key in _ART_RATIO_CACHE: return _ART_RATIO_CACHE[cache_key]
    ratio=1.0
    for path in _image_candidates(art):
        size=_image_size(_read_image_header(path))
        if size:
            width,height=size
            if width and height: ratio=float(width)/float(height)
            break
    if len(_ART_RATIO_CACHE)>=128:
        try: _ART_RATIO_CACHE.pop(next(iter(_ART_RATIO_CACHE)))
        except Exception: _ART_RATIO_CACHE.clear()
    _ART_RATIO_CACHE[cache_key]=ratio
    return ratio


def music_view_margin():
    try: value=int((xbmc.getInfoLabel("Skin.String({})".format(INFO_MARGIN_SETTING)) or str(INFO_MARGIN_DEFAULT)).strip())
    except Exception: value=INFO_MARGIN_DEFAULT
    return max(0,min(60,value))


def _info_cover_height():
    try: offset=int((xbmc.getInfoLabel("Skin.String(CCMainMenuYOffset)") or "0").strip())
    except Exception: offset=0
    margin=music_view_margin(); return max(2,int(INFO_DEFAULT_HEIGHT-offset-(2*margin)))


def _info_art_width(art,height):
    width=int(round(_art_ratio(art)*float(height))); return max(1,min(width,INFO_MAX_IMAGE_WIDTH))


def _set_shift_digits(home,base,value):
    value=max(0,min(1999,int(value)))
    for suffix,digit in (("Thousands",value//1000),("Hundreds",(value//100)%10),("Tens",(value//10)%10),("Ones",value%10)):
        home.setProperty(base+suffix,str(digit))


def sync_info_cover_geometry(mode=None):
    home=_home(); mode=(mode or (xbmc.getInfoLabel("Skin.String({})".format(SETTING)) or "front")).strip().lower(); height=_info_cover_height(); margin=music_view_margin(); front_art=xbmc.getInfoLabel("Player.Art(thumb)") or ""; back_art=sync_back_art(); front_width=_info_art_width(front_art,height); back_width=_info_art_width(back_art,height) if back_art else 0; back_shift=front_width+margin; text_shift=(front_width+margin+back_width+margin) if mode=="infoboth" and back_art else front_width+margin
    home.setProperty(INFO_FRONT_WIDTH_PROP,str(front_width)); home.setProperty(INFO_BACK_WIDTH_PROP,str(back_width)); home.setProperty(INFO_BACK_SHIFT_PROP,str(back_shift)); home.setProperty(INFO_TEXT_SHIFT_PROP,str(text_shift)); _set_shift_digits(home,INFO_BACK_SHIFT_PROP,back_shift); _set_shift_digits(home,INFO_TEXT_SHIFT_PROP,text_shift); return (height,front_width,back_width,back_shift,text_shift)


def _compact_width():
    art=xbmc.getInfoLabel("Player.Art(thumb)") or ""
    if not art: return COMPACT_WIDTH_FALLBACK
    return max(COMPACT_WIDTH_MIN,min(COMPACT_WIDTH_MAX,int(round(_art_ratio(art)*COMPACT_HEIGHT))))


def sync_compact_cover_width():
    width=_compact_width(); _home().setProperty(COMPACT_WIDTH_PROP,str(width)); return width


def _next_mode(mode,has_back):
    if mode=="front": return "both" if has_back else "infofront"
    if mode=="both": return "infofront"
    if mode=="infofront": return "infoboth" if has_back else "compact"
    if mode=="infoboth": return "compact"
    if mode=="compact": return "none"
    return "front"


def cycle_view():
    current=(xbmc.getInfoLabel("Skin.String({})".format(SETTING)) or "front").strip().lower(); back=sync_back_art(); new_mode=_next_mode(current,bool(back)); xbmc.executebuiltin("Skin.SetString({},{})".format(SETTING,new_mode)); sync_compact_cover_width(); sync_info_cover_geometry(new_mode)


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
        raw=(xbmc.getInfoLabel("Skin.String({})".format(INFO_COVER_SIZE_SETTING)) or "").strip(); requested=_get_int(INFO_COVER_SIZE_SETTING,natural) if raw else natural; return max(2,min(natural,requested))
    return natural

def _geom(cid,x,y,w,h):
    try:
        c=_home().getControl(cid); c.setPosition(int(x),int(y)); c.setWidth(max(1,int(w))); c.setHeight(max(1,int(h)))
    except Exception: pass

def sync_info_cover_geometry(mode=None):
    result=_old_sync_info(mode); mode=(mode or _current_mode()).lower()
    if _above_menu() and mode in ("infofront","infoboth"):
        h=_info_cover_height(); m=music_view_margin(); f=xbmc.getInfoLabel("Player.Art(thumb)") or ""; fw=_info_art_width(f,h); top=115-h; _geom(9480,-20,top,INFO_MAX_IMAGE_WIDTH,h); _geom(9481,-20,top,INFO_MAX_IMAGE_WIDTH,h); _geom(9482,-20+fw+m,top,INFO_MAX_IMAGE_WIDTH,h); back=_home().getProperty(BACK_PROP) or ""; bw=_info_art_width(back,h) if back else 0; single=max(0,fw+2*m-30); pair=max(0,fw+bw+3*m-30); bs=max(0,fw+m); ts=pair if mode=="infoboth" and back else single; home=_home(); home.setProperty(INFO_FRONT_WIDTH_PROP,str(fw)); home.setProperty(INFO_BACK_SHIFT_PROP,str(bs)); home.setProperty(INFO_TEXT_SHIFT_PROP,str(ts)); _set_shift_digits(home,INFO_BACK_SHIFT_PROP,bs); _set_shift_digits(home,INFO_TEXT_SHIFT_PROP,ts)
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

if __name__ == "__main__": main(sys.argv[1] if len(sys.argv)>1 else "change")
