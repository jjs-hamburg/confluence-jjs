# -*- coding: utf-8 -*-
from __future__ import absolute_import

import re
import time

import xbmc
import xbmcgui

from cover_display_action import (
    BACK_PROP,
    INFO_TEXT_SHIFT_PROP,
    clear_back_art,
    sync_back_art,
    sync_compact_cover_width,
    sync_info_cover_geometry,
)
from nocover_manager import sync_on_startup
from songselector_state import current, playlist_metadata, size
from truetype_metrics import text_width as truetype_text_width
from worker_lock import WorkerLock

HOME_ID = 10000
SERVICE_RUNNING_PROP = "ConfluenceCustom.NowPlaying.ServiceRunning"

SONG_ELAPSED_PROP = "ConfluenceCustom.SongSelector.SongElapsed"
SONG_DURATION_PROP = "ConfluenceCustom.SongSelector.SongDuration"
SONG_REMAINING_PROP = "ConfluenceCustom.SongSelector.SongRemaining"
ALBUM_ELAPSED_PROP = "ConfluenceCustom.SongSelector.AlbumElapsed"
ALBUM_DURATION_PROP = "ConfluenceCustom.SongSelector.AlbumDuration"
ALBUM_REMAINING_PROP = "ConfluenceCustom.SongSelector.AlbumRemaining"
SONG_ELAPSED_LEN_PROP = "ConfluenceCustom.SongSelector.SongElapsedLen"
SONG_DURATION_LEN_PROP = "ConfluenceCustom.SongSelector.SongDurationLen"
SONG_REMAINING_LEN_PROP = "ConfluenceCustom.SongSelector.SongRemainingLen"
ALBUM_ELAPSED_LEN_PROP = "ConfluenceCustom.SongSelector.AlbumElapsedLen"
ALBUM_DURATION_LEN_PROP = "ConfluenceCustom.SongSelector.AlbumDurationLen"
ALBUM_REMAINING_LEN_PROP = "ConfluenceCustom.SongSelector.AlbumRemainingLen"
SONG_LONG_PROP = "ConfluenceCustom.SongSelector.SongLong"
ALBUM_LONG_PROP = "ConfluenceCustom.SongSelector.AlbumLong"
TIME_BADGE_SONG_CURRENT_CLASS_PROP = "ConfluenceCustom.SongSelector.TimeBadgeSongCurrentClass"
TIME_BADGE_SONG_REMAINING_CLASS_PROP = "ConfluenceCustom.SongSelector.TimeBadgeSongRemainingClass"
TIME_BADGE_ALBUM_CURRENT_CLASS_PROP = "ConfluenceCustom.SongSelector.TimeBadgeAlbumCurrentClass"
TIME_BADGE_ALBUM_REMAINING_CLASS_PROP = "ConfluenceCustom.SongSelector.TimeBadgeAlbumRemainingClass"
TIME_BADGE_EQUAL_CLASS_PROP = "ConfluenceCustom.SongSelector.TimeBadgeEqualClass"
TIME_BADGE_CLASS_WIDTHS = (112, 123, 134, 145, 156, 167, 178, 189, 200, 211, 222)

ALBUM_WRAP_UPPER_PROP = "ConfluenceCustom.NowPlaying.AlbumWrapUpper"
ALBUM_WRAP_LOWER_PROP = "ConfluenceCustom.NowPlaying.AlbumWrapLower"
SONG_WRAP_UPPER_PROP = "ConfluenceCustom.NowPlaying.SongWrapUpper"
SONG_WRAP_LOWER_PROP = "ConfluenceCustom.NowPlaying.SongWrapLower"
ALBUM_WRAP_CUSTOM_WIDTH_PX = 1830.0
ALBUM_WRAP_STANDARD_WIDTH_PX = 1500.0
ALBUM_WRAP_FONT = ("Roboto-Regular.ttf", 26)
SONG_WRAP_CUSTOM_WIDTH_PX = 1830.0
SONG_WRAP_STANDARD_WIDTH_PX = 1500.0
SONG_WRAP_FONT = ("Roboto-Bold.ttf", 30)


def _skin_string(name, default=""):
    value = xbmc.getInfoLabel("Skin.String({})".format(name))
    return value or default


def _audio_active():
    return xbmc.getCondVisibility("Player.HasAudio")


def _playback_context():
    return xbmc.getCondVisibility(
        "[Window.IsActive(Home) | Window.IsActive(1116)] + "
        "!String.IsEqual(Playlist.Length(music),0) + !Playlist.IsRandom + "
        "String.IsEmpty(Window(Videos).Property(PlayingBackgroundMedia))"
    )


def _footer_text_width(text, font_spec):
    filename, pixel_size = font_spec
    return truetype_text_width(str(text or ""), filename, pixel_size)


def _append_word(current, word):
    return (current + " " + word).strip() if current else word


def _album_line_text():
    artist = (xbmc.getInfoLabel("MusicPlayer.Artist") or "").strip()
    album = (xbmc.getInfoLabel("MusicPlayer.Album") or "").strip()
    year = (xbmc.getInfoLabel("MusicPlayer.Year") or "").strip()
    disc = (xbmc.getInfoLabel("MusicPlayer.DiscNumber") or "").strip()
    parts = []
    if artist:
        parts.append(artist + " - ")
    parts.append(album)
    text = "".join(parts)
    if xbmc.getCondVisibility("Skin.HasSetting(CCNowPlayingAlbumYear)") and year and year not in ("0", "0000"):
        text += " | " + year
    if disc:
        try:
            disc_label = xbmc.getLocalizedString(427) or "Disc"
        except Exception:
            disc_label = "Disc"
        text += " - {}:{}".format(disc_label, disc)
    return text


def _split_wrap(text, width_px, font_spec, keep_year_separator=False):
    text = str(text or "").strip()
    if not text:
        return "", ""
    if _footer_text_width(text, font_spec) <= width_px:
        return "", text
    wrap_text = text
    if keep_year_separator:
        wrap_text = re.sub(r"\|\s+(\d{4})(?=\s|$)", lambda match: "|\u00a0" + match.group(1), text)
    words = [word for word in wrap_text.split(" ") if word]
    if len(words) <= 1:
        return "", text
    upper = ""
    split_at = 0
    for index, word in enumerate(words):
        trial = _append_word(upper, word)
        if upper and _footer_text_width(trial, font_spec) > width_px:
            split_at = index
            break
        upper = trial
    else:
        return "", text
    lower = " ".join(words[split_at:]).strip()
    if not upper or not lower:
        return "", text
    return upper.replace("\u00a0", " "), lower.replace("\u00a0", " ")


def _info_artwork_text_shift(home):
    try:
        return max(0.0, float(home.getProperty(INFO_TEXT_SHIFT_PROP) or 0))
    except Exception:
        return 0.0


def _set_wrap_property(home, upper_prop, lower_prop, upper, lower):
    if upper:
        home.setProperty(upper_prop, upper)
    else:
        home.clearProperty(upper_prop)
    if lower:
        home.setProperty(lower_prop, lower)
    else:
        home.clearProperty(lower_prop)


def _update_album_wrap_properties(home):
    text = _album_line_text()
    if not text:
        _set_wrap_property(home, ALBUM_WRAP_UPPER_PROP, ALBUM_WRAP_LOWER_PROP, "", "")
        return
    standard = xbmc.getCondVisibility("Skin.HasSetting(CCStandardConfluence)")
    width = ALBUM_WRAP_STANDARD_WIDTH_PX if standard else ALBUM_WRAP_CUSTOM_WIDTH_PX
    if not standard:
        mode = (_skin_string("CCMusicArtworkMode", "front") or "front").strip().lower()
        if mode in ("compact", "infofront", "infoboth"):
            width = max(240.0, width - _info_artwork_text_shift(home))
    upper, lower = _split_wrap(text, width, ALBUM_WRAP_FONT, keep_year_separator=True)
    _set_wrap_property(home, ALBUM_WRAP_UPPER_PROP, ALBUM_WRAP_LOWER_PROP, upper, lower)


def _song_line_text():
    title = (xbmc.getInfoLabel("Player.Title") or "").strip()
    if not title:
        return ""
    show_track = (_skin_string("CCSongSelectorShowTrackNumbers", "") or "").strip().lower()
    if show_track in ("1", "true", "yes", "on"):
        track = (xbmc.getInfoLabel("MusicPlayer.TrackNumber") or "").strip()
        if track and track not in ("0", "00"):
            return "{}. {}".format(track, title)
    return title


def _update_song_wrap_properties(home):
    text = _song_line_text()
    if not text:
        _set_wrap_property(home, SONG_WRAP_UPPER_PROP, SONG_WRAP_LOWER_PROP, "", "")
        return
    standard = xbmc.getCondVisibility("Skin.HasSetting(CCStandardConfluence)")
    width = SONG_WRAP_STANDARD_WIDTH_PX if standard else SONG_WRAP_CUSTOM_WIDTH_PX
    if not standard:
        mode = (_skin_string("CCMusicArtworkMode", "front") or "front").strip().lower()
        if mode in ("compact", "infofront", "infoboth"):
            width = max(240.0, width - _info_artwork_text_shift(home))
    upper, lower = _split_wrap(text, width, SONG_WRAP_FONT)
    _set_wrap_property(home, SONG_WRAP_UPPER_PROP, SONG_WRAP_LOWER_PROP, upper, lower)


def _format_time(seconds):
    seconds = max(0, int(seconds or 0))
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return "{}:{:02d}:{:02d}".format(hours, minutes, secs)
    return "{}:{:02d}".format(minutes, secs)


def _set_flag(home, prop, enabled):
    if enabled:
        home.setProperty(prop, "1")
    else:
        home.clearProperty(prop)


def _set_time_value(home, prop, length_prop, value):
    value = value or ""
    if value:
        home.setProperty(prop, value)
        home.setProperty(length_prop, str(len(value)))
    else:
        home.clearProperty(prop)
        home.clearProperty(length_prop)


def _clear_times(home):
    for prop in (
        SONG_ELAPSED_PROP, SONG_DURATION_PROP, SONG_REMAINING_PROP,
        ALBUM_ELAPSED_PROP, ALBUM_DURATION_PROP, ALBUM_REMAINING_PROP,
        SONG_ELAPSED_LEN_PROP, SONG_DURATION_LEN_PROP, SONG_REMAINING_LEN_PROP,
        ALBUM_ELAPSED_LEN_PROP, ALBUM_DURATION_LEN_PROP, ALBUM_REMAINING_LEN_PROP,
        SONG_LONG_PROP, ALBUM_LONG_PROP,
        TIME_BADGE_SONG_CURRENT_CLASS_PROP, TIME_BADGE_SONG_REMAINING_CLASS_PROP,
        TIME_BADGE_ALBUM_CURRENT_CLASS_PROP, TIME_BADGE_ALBUM_REMAINING_CLASS_PROP,
        TIME_BADGE_EQUAL_CLASS_PROP,
    ):
        home.clearProperty(prop)


def _setting_enabled(name, default=True):
    value = (_skin_string(name, "") or "").strip().lower()
    if not value:
        return bool(default)
    return value == "true"


def _time_badge_class(left, right):
    text = "{} | {}".format(left or "", right or "")
    text_width = 0
    for char in text:
        if char.isdigit() or char == "−":
            text_width += 11
        elif char in (":", " ", "|"):
            text_width += 5
        else:
            text_width += 11
    wanted = text_width + 24
    for width in TIME_BADGE_CLASS_WIDTHS:
        if wanted <= width:
            return "w{}".format(width)
    return "w{}".format(TIME_BADGE_CLASS_WIDTHS[-1])


def _publish_time_badge_classes(home):
    pairs = (
        (TIME_BADGE_SONG_CURRENT_CLASS_PROP, SONG_ELAPSED_PROP, SONG_DURATION_PROP, "CCSongTimeCurrent"),
        (TIME_BADGE_SONG_REMAINING_CLASS_PROP, SONG_REMAINING_PROP, SONG_DURATION_PROP, "CCSongTimeRemaining"),
        (TIME_BADGE_ALBUM_CURRENT_CLASS_PROP, ALBUM_ELAPSED_PROP, ALBUM_DURATION_PROP, "CCAlbumTimeCurrent"),
        (TIME_BADGE_ALBUM_REMAINING_CLASS_PROP, ALBUM_REMAINING_PROP, ALBUM_DURATION_PROP, "CCAlbumTimeRemaining"),
    )
    visible_widths = []
    for class_prop, left_prop, right_prop, setting in pairs:
        left = home.getProperty(left_prop)
        right = home.getProperty(right_prop)
        if left and right:
            width_class = _time_badge_class(left, right)
            home.setProperty(class_prop, width_class)
            if _setting_enabled(setting, True):
                try:
                    visible_widths.append(int(width_class[1:]))
                except Exception:
                    pass
        else:
            home.clearProperty(class_prop)
    if visible_widths:
        home.setProperty(TIME_BADGE_EQUAL_CLASS_PROP, "w{}".format(max(visible_widths)))
    else:
        home.clearProperty(TIME_BADGE_EQUAL_CLASS_PROP)


def _album_durations(items, playing, album):
    total = 0
    before = 0
    for index, item in enumerate(items or []):
        item_album = item.get("album") or ""
        if album and item_album != album:
            continue
        try:
            duration = int(item.get("duration") or 0)
        except Exception:
            duration = 0
        duration = max(0, duration)
        total += duration
        if index < playing:
            before += duration
    if album and total <= 0:
        return _album_durations(items, playing, "")
    return before, total


def _set_times(home, items, playing):
    if playing < 0:
        _clear_times(home)
        return
    player = xbmc.Player()
    try:
        song_elapsed = max(0, int(player.getTime()))
    except Exception:
        song_elapsed = 0
    try:
        song_total = max(0, int(player.getTotalTime()))
    except Exception:
        song_total = 0
    song_remaining = max(0, song_total - song_elapsed) if song_total > 0 else 0
    if song_total > 0:
        _set_time_value(home, SONG_ELAPSED_PROP, SONG_ELAPSED_LEN_PROP, _format_time(min(song_elapsed, song_total)))
        _set_time_value(home, SONG_DURATION_PROP, SONG_DURATION_LEN_PROP, _format_time(song_total))
        _set_time_value(home, SONG_REMAINING_PROP, SONG_REMAINING_LEN_PROP, "−" + _format_time(song_remaining))
        _set_flag(home, SONG_LONG_PROP, song_total >= 3600)
    else:
        for prop in (
            SONG_ELAPSED_PROP, SONG_DURATION_PROP, SONG_REMAINING_PROP,
            SONG_ELAPSED_LEN_PROP, SONG_DURATION_LEN_PROP, SONG_REMAINING_LEN_PROP,
            SONG_LONG_PROP,
        ):
            home.clearProperty(prop)

    album = xbmc.getInfoLabel("MusicPlayer.Album") or ""
    before, total = _album_durations(items, playing, album)
    album_elapsed = before + song_elapsed
    if total > 0:
        album_elapsed = min(album_elapsed, total)
        album_remaining = max(0, total - album_elapsed)
        _set_time_value(home, ALBUM_ELAPSED_PROP, ALBUM_ELAPSED_LEN_PROP, _format_time(album_elapsed))
        _set_time_value(home, ALBUM_DURATION_PROP, ALBUM_DURATION_LEN_PROP, _format_time(total))
        _set_time_value(home, ALBUM_REMAINING_PROP, ALBUM_REMAINING_LEN_PROP, "−" + _format_time(album_remaining))
        _set_flag(home, ALBUM_LONG_PROP, total >= 3600)
    else:
        for prop in (
            ALBUM_ELAPSED_PROP, ALBUM_DURATION_PROP, ALBUM_REMAINING_PROP,
            ALBUM_ELAPSED_LEN_PROP, ALBUM_DURATION_LEN_PROP, ALBUM_REMAINING_LEN_PROP,
            ALBUM_LONG_PROP,
        ):
            home.clearProperty(prop)
    _publish_time_badge_classes(home)


def _wrap_signature(home):
    return (
        xbmc.getInfoLabel("MusicPlayer.Artist") or "",
        xbmc.getInfoLabel("MusicPlayer.Album") or "",
        xbmc.getInfoLabel("MusicPlayer.Year") or "",
        xbmc.getInfoLabel("MusicPlayer.DiscNumber") or "",
        xbmc.getInfoLabel("Player.Title") or "",
        xbmc.getInfoLabel("MusicPlayer.TrackNumber") or "",
        _skin_string("CCMusicArtworkMode", "front"),
        _skin_string("CCSongSelectorShowTrackNumbers", ""),
        bool(xbmc.getCondVisibility("Skin.HasSetting(CCNowPlayingAlbumYear)")),
        bool(xbmc.getCondVisibility("Skin.HasSetting(CCStandardConfluence)")),
        home.getProperty(INFO_TEXT_SHIFT_PROP) or "",
    )


def _geometry_signature(home):
    return (
        bool(xbmc.getCondVisibility("Window.IsActive(Home)")),
        xbmc.getInfoLabel("Player.FilenameAndPath") or "",
        xbmc.getInfoLabel("Player.Art(thumb)") or "",
        home.getProperty(BACK_PROP) or "",
        _skin_string("CCMusicArtworkMode", "front"),
        _skin_string("CCMainMenuYOffset", "0"),
        _skin_string("CCHomeMusicViewMargin", "10"),
        _skin_string("CCHomeMusicInfoCoverSize", ""),
        bool(xbmc.getCondVisibility("Skin.HasSetting(CCHomeMusicInfoCoverDynamic)")),
        bool(xbmc.getCondVisibility("Skin.HasSetting(CCHomeMusicDisplayAboveMenu)")),
        bool(xbmc.getCondVisibility("Skin.HasSetting(CCStandardConfluence)")),
    )


def run():
    sync_on_startup()
    monitor = xbmc.Monitor()
    home = xbmcgui.Window(HOME_ID)
    last_size = -1
    meta = []
    last_time_update = 0.0
    last_art_file = ""
    last_wrap_signature = None
    last_geometry_signature = None

    while not monitor.abortRequested():
        now = time.monotonic()
        wrap_signature = _wrap_signature(home)
        if wrap_signature != last_wrap_signature:
            _update_album_wrap_properties(home)
            _update_song_wrap_properties(home)
            last_wrap_signature = wrap_signature

        standard = xbmc.getCondVisibility("Skin.HasSetting(CCStandardConfluence)")
        context = _playback_context()
        audio = _audio_active()

        if not standard and context:
            count = size()
            playing = current() if count > 0 else -1
            if not meta or count != last_size:
                meta = playlist_metadata()
                last_size = count

            if audio:
                playing_file = xbmc.getInfoLabel("Player.FilenameAndPath") or ""
                if playing_file and playing_file != last_art_file:
                    sync_back_art()
                    sync_compact_cover_width()
                    last_art_file = playing_file
                    last_geometry_signature = None

                geometry_signature = _geometry_signature(home)
                if geometry_signature != last_geometry_signature:
                    # Direct Home-control mutation is event driven. In particular,
                    # it no longer runs every 150 ms while the user is elsewhere.
                    if geometry_signature[0]:
                        sync_info_cover_geometry()
                    last_geometry_signature = geometry_signature

                if now - last_time_update >= 0.50:
                    _set_times(home, meta, playing)
                    last_time_update = now
            else:
                _clear_times(home)
        else:
            _clear_times(home)
            if not context:
                clear_back_art()
                last_art_file = ""
                last_size = -1
                meta = []
                last_geometry_signature = None

        if monitor.waitForAbort(0.15 if context else 0.50):
            break


if __name__ == "__main__":
    _service_home = xbmcgui.Window(HOME_ID)
    _service_lock = WorkerLock("nowplaying")
    if _service_lock.acquire():
        _service_home.setProperty(SERVICE_RUNNING_PROP, "1")
        try:
            run()
        finally:
            _service_home.clearProperty(SERVICE_RUNNING_PROP)
            _service_lock.release()
    else:
        xbmc.log("[ConfluenceCustom] Now Playing worker already running; duplicate start suppressed", xbmc.LOGINFO)
