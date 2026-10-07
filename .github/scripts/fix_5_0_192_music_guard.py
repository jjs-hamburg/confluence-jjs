# -*- coding: utf-8 -*-
from pathlib import Path
import py_compile

path = Path("skin.confluence.custom/resources/lib/nowplaying_service.py")
text = path.read_text(encoding="utf-8")

if 'music_audio = audio and not xbmc.getCondVisibility("Player.HasVideo")' not in text:
    old = '''        standard = xbmc.getCondVisibility("Skin.HasSetting(CCStandardConfluence)")
        context = _playback_context()
        audio = _audio_active()

        if not standard:
            # Artwork belongs to the playing title, not to the current window.
            # Keep it stable while Videos/Music/scanners are active.
            if audio:
'''
    new = '''        standard = xbmc.getCondVisibility("Skin.HasSetting(CCStandardConfluence)")
        context = _playback_context()
        audio = _audio_active()
        music_audio = audio and not xbmc.getCondVisibility("Player.HasVideo")

        if not standard:
            # Artwork belongs to the playing MUSIC title, not to the current
            # GUI window. A video with an audio track must never alter it.
            if music_audio:
'''
    if old not in text:
        raise SystemExit("5.0.192 music-only artwork guard anchor not found")
    text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")

text = path.read_text(encoding="utf-8")
assert 'music_audio = audio and not xbmc.getCondVisibility("Player.HasVideo")' in text
assert "if music_audio:" in text
py_compile.compile(str(path), doraise=True)
print("5.0.192 music-only artwork guard OK")
