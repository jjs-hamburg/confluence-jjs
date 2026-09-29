# -*- coding: utf-8 -*-
from __future__ import absolute_import

import bisect
import re
import time

import xbmc
import xbmcgui

from cover_display_action import COMPACT_WIDTH_PROP, clear_back_art, sync_back_art, sync_compact_cover_width
from credits_runtime import CreditsRuntime, clear_properties as clear_credits_properties
from nocover_manager import sync_on_startup
from songselector_action import (clear_pause_guard, detail_view, focus_current, guard_pause_focus, lyrics_view, open_popup, restore_pause_focus, show_credits)
from songselector_state import (
    close_popup,
    current,
    playlist_metadata,
    popup_open,
    size,
)

HOME_ID = 10000
TOUCH_PROP = "ConfluenceCustom.SongSelector.Touch"
SELECTION_TIMEOUT_SETTING = "CCSongSelectorSelectionTimeout"
AUTO_OPEN_SETTING = "CCSongSelectorAutoOpen"
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
ALBUM_WRAP_FONT_SIGNATURE = ("roboto", 26)
SONG_WRAP_CUSTOM_WIDTH_PX = 1830.0
SONG_WRAP_STANDARD_WIDTH_PX = 1500.0
SONG_WRAP_FONT_SIGNATURE = ("robotobold", 30)
DIALOG_ID = 1116
LIST_ID = 9110
NEUTRAL_CONTROL_ID = 9131
HIGHLIGHT_PROP = "ConfluenceCustom.SongSelector.Highlight"
PROGRAMMATIC_UNTIL_PROP = "ConfluenceCustom.SongSelector.ProgrammaticUntil"
LYRICS_TEXT_PROP = "ConfluenceCustom.SongSelector.LyricsText"
LYRICS_DEBUG_PROP = "ConfluenceCustom.SongSelector.LyricsDebug"
CULRC_LYRICS_PROP = "culrc.lyrics"
CULRC_SOURCE_PROP = "culrc.source"
CULRC_RUNNING_PROP = "culrc.running"
CULRC_HASLIST_PROP = "culrc.haslist"
CULRC_ISLRC_PROP = "culrc.islrc"
LYRICS_SYNC_PROP = "ConfluenceCustom.SongSelector.LyricsSync"
LYRICS_VISIBLE_ROWS = 11
LYRICS_HISTORY_ROWS = 4
LYRICS_SYNC_DELAY_SETTING = "CCSongSelectorLyricsSyncDelay"
DEFAULT_LYRICS_SYNC_DELAY_SECONDS = 0.25
LYRICS_LINE_PROP_PREFIX = "ConfluenceCustom.SongSelector.LyricsLine"
LYRICS_ACTIVE_SLOT_PROP = "ConfluenceCustom.SongSelector.LyricsActiveSlot"
LYRICS_WINDOW_START_PROP = "ConfluenceCustom.SongSelector.LyricsWindowStart"
LYRICS_MANUAL_START_PROP = "ConfluenceCustom.SongSelector.LyricsManualStart"
LYRICS_LINE_COUNT_PROP = "ConfluenceCustom.SongSelector.LyricsLineCount"
CULRC_STATUS_PROP = "culrc.jjsstatus"
CULRC_MANUAL_PROP = "culrc.manual"
CULRC_ARTIST_PROP = "culrc.artist"
CULRC_TRACK_PROP = "culrc.track"
SELECTION_TARGET_PROP = "ConfluenceCustom.SongSelector.SelectionTarget"
SELECTION_GOTO_PENDING_PROP = "ConfluenceCustom.SongSelector.GoToPending"
CREDITS_SOURCE_COUNT_PROP = "ConfluenceCustom.Credits.LineCount"
CREDITS_SOURCE_UPDATED_PROP = "ConfluenceCustom.Credits.Updated"
CREDITS_SOURCE_PREFIX = "ConfluenceCustom.Credits.Line."
CREDITS_VISIBLE_ROWS = 13
CREDITS_WINDOW_START_PROP = "ConfluenceCustom.SongSelector.CreditsWindowStart"
CREDITS_VIEW_LINE_PREFIX = "ConfluenceCustom.SongSelector.CreditsLine"
CREDITS_DISPLAY_COUNT_PROP = "ConfluenceCustom.SongSelector.CreditsLineCount"
CREDITS_WRAP_WIDTH_PX = 510.0
CREDITS_CONTINUATION_INDENT_PX = 24.0
LYRICS_WRAP_WIDTH_PX = 510.0




_LRC_TIME_RE = re.compile(r"^(?:\[(?:\d{1,3}:)?\d{1,2}:\d{1,2}(?:[.:]\d{1,3})?\])+", re.I)
_LRC_SIMPLE_TIME_RE = re.compile(r"^(?:\[\d{1,3}:\d{1,2}(?:[.:]\d{1,3})?\])+", re.I)
_LRC_ENHANCED_TIME_RE = re.compile(r"<\d{1,3}:\d{1,2}(?:[.:]\d{1,3})?>")
_LRC_META_RE = re.compile(r"^\[(?:ar|al|ti|au|by|offset|re|ve|length|id):.*\]$", re.I)


def _lyrics_sync_delay_seconds():
    """Return the user-configured extra delay for the highlighted LRC line.

    Stored as a Skin.String so it can be tuned from Confluence-jjs settings
    without restarting the service.  Invalid values fall back safely.
    """
    try:
        raw = xbmc.getInfoLabel("Skin.String({})".format(LYRICS_SYNC_DELAY_SETTING))
        value = float(raw or DEFAULT_LYRICS_SYNC_DELAY_SECONDS)
    except Exception:
        value = DEFAULT_LYRICS_SYNC_DELAY_SECONDS
    return max(0.0, min(1.0, value))


def _culrc_setting_offset():
    """Embedded CU LRC uses the skin's own sync-delay control only."""
    return 0.0


def _parse_lrc_timestamp(tag):
    """Parse a normal LRC [mm:ss.xx] timestamp and return seconds."""
    match = re.match(r"^\[(\d{1,3}):(\d{1,2})(?:[.:](\d{1,3}))?\]$", tag or "")
    if not match:
        return None
    minutes = int(match.group(1))
    seconds = int(match.group(2))
    fraction_text = match.group(3) or ""
    fraction = 0.0
    if fraction_text:
        fraction = int(fraction_text) / float(10 ** len(fraction_text))
    return (minutes * 60.0) + seconds + fraction


def _clean_and_time_culrc_lyrics(raw):
    """Return (plain_text, sync_entries, rendered_line_count).

    Long logical lyric lines are expanded to physical 46-pixel display rows.
    sync_entries contains (seconds, first_row, last_row), so all wrapped rows of
    one timed LRC line stay highlighted together and share the same timestamp.
    """
    text = (raw or "").replace("\ufeff", "").replace("\x00", "")
    text = text.replace("[CR]", "\n").replace("\r\n", "\n").replace("\r", "\n")

    embedded_offset = 0.0
    offset_match = re.search(r"^\s*\[offset:\s*(-?\d+)\]\s*$", text, flags=re.I | re.M)
    if offset_match:
        try:
            embedded_offset = float(offset_match.group(1)) / 1000.0
        except Exception:
            embedded_offset = 0.0
    global_offset = _culrc_setting_offset()
    font_signature = _songselector_font_signature()

    out = []
    timed = []
    blank = False
    tag_re = re.compile(r"\[\d{1,3}:\d{1,2}(?:[.:]\d{1,3})?\]")

    for original in text.split("\n"):
        line = original.strip()
        if _LRC_META_RE.match(line):
            continue

        times = []
        rest = line
        while True:
            match = tag_re.match(rest)
            if not match:
                break
            value = _parse_lrc_timestamp(match.group(0))
            if value is not None:
                times.append(value + global_offset - embedded_offset)
            rest = rest[match.end():]

        rest = _LRC_TIME_RE.sub("", rest)
        rest = _LRC_SIMPLE_TIME_RE.sub("", rest)
        rest = _LRC_ENHANCED_TIME_RE.sub("", rest).strip()
        if not rest:
            if out and not blank:
                out.append("")
            blank = True
            continue

        wrapped = _wrap_plain_text(rest, LYRICS_WRAP_WIDTH_PX, font_signature)
        first_row = len(out)
        out.extend(wrapped)
        last_row = len(out) - 1
        blank = False
        for value in times:
            timed.append((max(0.0, float(value)), first_row, last_row))

    while out and not out[-1]:
        out.pop()

    line_count = len(out)
    timed = [(stamp, first, min(last, line_count - 1)) for stamp, first, last in timed if first < line_count]
    timed.sort(key=lambda item: (item[0], item[1], item[2]))
    return "[CR]".join(out).strip(), timed, line_count

def _clean_culrc_lyrics(raw):
    return _clean_and_time_culrc_lyrics(raw)[0]


def _int_property(home, name, default=0):
    try:
        return int(home.getProperty(name) or default)
    except Exception:
        return int(default)


def _songselector_font_signature():
    """Return the effective popup font family/size used for width estimates."""
    family = (xbmc.getInfoLabel("Skin.String(CCSongSelectorFontFamily)") or "").strip().lower()
    size_text = (xbmc.getInfoLabel("Skin.String(CCSongSelectorFontSize)") or "").strip()
    if not family or family in ("default", "submenu"):
        family = (xbmc.getInfoLabel("Skin.String(CCSubMenuFontFamily)") or "roboto").strip().lower()
        size_text = (xbmc.getInfoLabel("Skin.String(CCSubMenuFontSize)") or size_text or "26").strip()
    try:
        size = max(20, min(30, int(float(size_text or 26))))
    except Exception:
        size = 26
    return family or "roboto", size


def _estimated_text_width(text, font_signature=None):
    """Conservative pixel-width estimate for the popup fonts.

    Kodi does not expose label text metrics to a background Python service.  The
    approximation is intentionally a little conservative so wrapped rows do not
    clip at the right edge.  It follows the selected 20-30 px popup font size.
    """
    family, size = font_signature or _songselector_font_signature()
    family_factor = 1.0
    if "montserrat" in family:
        family_factor = 1.04
    elif "bold" in family:
        family_factor = 1.02
    units = 0.0
    for ch in str(text or ""):
        if ch.isspace():
            units += 0.28
        elif ch in "ilI1|!.,:;'`":
            units += 0.27
        elif ch in "mwMW@#%&QO":
            units += 0.82
        elif ch.isupper():
            units += 0.62
        elif ord(ch) > 0x2FFF:
            units += 0.95
        else:
            units += 0.52
    return units * float(size) * family_factor


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


def _split_album_wrap(text, width_px):
    """Return (upper, lower) for a maximum two-line album display.

    One-line text is deliberately kept entirely in *lower* so its baseline is
    identical to the historical album row. Only a real width overflow creates
    the upper row.
    """
    text = str(text or "").strip()
    if not text:
        return "", ""
    # Slightly favour staying on one line. This prevents an estimate that is a
    # few pixels too wide from moving a title upward even though Kodi still fits it.
    if _estimated_text_width(text, ALBUM_WRAP_FONT_SIGNATURE) <= (width_px * 1.015):
        return "", text
    words = text.split()
    if len(words) <= 1:
        return "", text
    upper = ""
    split_at = 0
    for i, word in enumerate(words):
        trial = _append_word(upper, word)
        if upper and _estimated_text_width(trial, ALBUM_WRAP_FONT_SIGNATURE) > width_px:
            split_at = i
            break
        upper = trial
    else:
        return "", text
    lower = " ".join(words[split_at:]).strip()
    if not upper or not lower:
        return "", text
    return upper, lower


def _update_album_wrap_properties(home):
    text = _album_line_text()
    if not text:
        home.clearProperty(ALBUM_WRAP_UPPER_PROP)
        home.clearProperty(ALBUM_WRAP_LOWER_PROP)
        return
    standard = xbmc.getCondVisibility("Skin.HasSetting(CCStandardConfluence)")
    width = ALBUM_WRAP_STANDARD_WIDTH_PX if standard else ALBUM_WRAP_CUSTOM_WIDTH_PX
    if not standard and xbmc.getCondVisibility(
        "String.IsEqual(Skin.String(CCMusicArtworkMode),compact)"
    ):
        try:
            compact_width = float(home.getProperty(COMPACT_WIDTH_PROP) or 120)
        except Exception:
            compact_width = 120.0
        width = max(240.0, width - compact_width - 15.0)
    upper, lower = _split_album_wrap(text, width)
    if upper:
        home.setProperty(ALBUM_WRAP_UPPER_PROP, upper)
    else:
        home.clearProperty(ALBUM_WRAP_UPPER_PROP)
    if lower:
        home.setProperty(ALBUM_WRAP_LOWER_PROP, lower)
    else:
        home.clearProperty(ALBUM_WRAP_LOWER_PROP)


def _song_line_text():
    title = (xbmc.getInfoLabel("Player.Title") or "").strip()
    if not title:
        return ""
    show_track = (xbmc.getInfoLabel("Skin.String(CCSongSelectorShowTrackNumbers)") or "").strip().lower()
    if show_track in ("1", "true", "yes", "on"):
        track = (xbmc.getInfoLabel("MusicPlayer.TrackNumber") or "").strip()
        if track and track not in ("0", "00"):
            return "{}. {}".format(track, title)
    return title


def _split_song_wrap(text, width_px):
    """Same two-line policy as the proven album wrap, for the song title."""
    text = str(text or "").strip()
    if not text:
        return "", ""
    if _estimated_text_width(text, SONG_WRAP_FONT_SIGNATURE) <= (width_px * 1.015):
        return "", text
    words = text.split()
    if len(words) <= 1:
        return "", text
    upper = ""
    split_at = 0
    for i, word in enumerate(words):
        trial = _append_word(upper, word)
        if upper and _estimated_text_width(trial, SONG_WRAP_FONT_SIGNATURE) > width_px:
            split_at = i
            break
        upper = trial
    else:
        return "", text
    lower = " ".join(words[split_at:]).strip()
    if not upper or not lower:
        return "", text
    return upper, lower


def _update_song_wrap_properties(home):
    text = _song_line_text()
    if not text:
        home.clearProperty(SONG_WRAP_UPPER_PROP)
        home.clearProperty(SONG_WRAP_LOWER_PROP)
        return
    standard = xbmc.getCondVisibility("Skin.HasSetting(CCStandardConfluence)")
    width = SONG_WRAP_STANDARD_WIDTH_PX if standard else SONG_WRAP_CUSTOM_WIDTH_PX
    if not standard and xbmc.getCondVisibility(
        "String.IsEqual(Skin.String(CCMusicArtworkMode),compact)"
    ):
        try:
            compact_width = float(home.getProperty(COMPACT_WIDTH_PROP) or 120)
        except Exception:
            compact_width = 120.0
        width = max(240.0, width - compact_width - 15.0)
    upper, lower = _split_song_wrap(text, width)
    if upper:
        home.setProperty(SONG_WRAP_UPPER_PROP, upper)
    else:
        home.clearProperty(SONG_WRAP_UPPER_PROP)
    if lower:
        home.setProperty(SONG_WRAP_LOWER_PROP, lower)
    else:
        home.clearProperty(SONG_WRAP_LOWER_PROP)


def _append_word(current, word):
    return (current + " " + word).strip() if current else word


def _hard_split_word(word, width_px, font_signature):
    """Split an exceptional no-space token so it can never disappear off-screen."""
    word = str(word or "")
    if not word:
        return "", ""
    piece = ""
    for pos, ch in enumerate(word):
        trial = piece + ch
        if piece and _estimated_text_width(trial, font_signature) > width_px:
            return piece, word[pos:]
        piece = trial
    return piece, ""


def _wrap_plain_text(text, width_px, font_signature=None):
    """Word-wrap one display string using the same conservative width model."""
    font_signature = font_signature or _songselector_font_signature()
    words = str(text or "").split()
    if not words:
        return [""]
    rows = []
    current = ""
    pending = list(words)
    while pending:
        word = pending.pop(0)
        trial = _append_word(current, word)
        if not current or _estimated_text_width(trial, font_signature) <= width_px:
            if not current and _estimated_text_width(word, font_signature) > width_px:
                piece, remainder = _hard_split_word(word, width_px, font_signature)
                current = piece
                if remainder:
                    pending.insert(0, remainder)
                    rows.append(current)
                    current = ""
                continue
            current = trial
        else:
            rows.append(current)
            current = ""
            pending.insert(0, word)
    if current or not rows:
        rows.append(current)
    return rows


def _credit_row_width(left, right, font_signature):
    width = _estimated_text_width(left, font_signature) + _estimated_text_width(right, font_signature)
    if left and right:
        width += _estimated_text_width(" — ", font_signature)
    return width


def _wrap_credit_row(left, right, name_side, font_signature=None):
    """Expand one logical credit into visual rows while preserving name colour.

    Each returned row is (left, right, name_side, continuation).  Continuation
    rows are rendered 24 px inward by the XML view.
    """
    font_signature = font_signature or _songselector_font_signature()
    segments = [("left", str(left or "").strip())]
    if str(right or "").strip():
        segments.append(("right", str(right or "").strip()))
    tokens = []
    for side, text in segments:
        for word in text.split():
            tokens.append([side, word])
    if not tokens:
        return []

    rows = []
    cur_left = ""
    cur_right = ""
    logical_row_index = 0

    def capacity():
        return CREDITS_WRAP_WIDTH_PX if logical_row_index == 0 else (CREDITS_WRAP_WIDTH_PX - CREDITS_CONTINUATION_INDENT_PX)

    def flush():
        nonlocal cur_left, cur_right, logical_row_index
        if not cur_left and not cur_right:
            return
        side = name_side if ((name_side == "left" and cur_left) or (name_side == "right" and cur_right)) else ""
        rows.append((cur_left, cur_right, side, logical_row_index > 0))
        logical_row_index += 1
        cur_left = ""
        cur_right = ""

    pending = list(tokens)
    while pending:
        side, word = pending.pop(0)
        trial_left = _append_word(cur_left, word) if side == "left" else cur_left
        trial_right = _append_word(cur_right, word) if side == "right" else cur_right
        cap = capacity()
        if _credit_row_width(trial_left, trial_right, font_signature) <= cap:
            cur_left, cur_right = trial_left, trial_right
            continue

        if cur_left or cur_right:
            flush()
            pending.insert(0, [side, word])
            continue

        # One unusually long token: split it instead of letting Kodi clip it.
        piece, remainder = _hard_split_word(word, cap, font_signature)
        if side == "left":
            cur_left = piece
        else:
            cur_right = piece
        flush()
        if remainder:
            pending.insert(0, [side, remainder])

    flush()
    return rows


def _build_credit_display_rows(home, font_signature=None):
    count = max(0, _int_property(home, CREDITS_SOURCE_COUNT_PROP, 0))
    font_signature = font_signature or _songselector_font_signature()
    rows = []
    for source_index in range(count):
        base = CREDITS_SOURCE_PREFIX + str(source_index) + "."
        left = home.getProperty(base + "Left") or ""
        right = home.getProperty(base + "Right") or ""
        name_side = (home.getProperty(base + "NameSide") or "").strip().lower()
        rows.extend(_wrap_credit_row(left, right, name_side, font_signature))
    return rows


def _clear_lyrics_window(home):
    """Clear the fixed property-backed lyrics viewport.

    Kodi 21 proved unstable when a background service directly mutated a visible
    ControlList. The lyrics page therefore renders only Home window properties;
    the service never calls getControl(), reset(), addItem() or selectItem().
    """
    for slot in range(LYRICS_VISIBLE_ROWS):
        base = LYRICS_LINE_PROP_PREFIX + str(slot)
        home.clearProperty(base)
        home.clearProperty(base + ".Active")
    home.clearProperty(LYRICS_ACTIVE_SLOT_PROP)
    home.setProperty(LYRICS_WINDOW_START_PROP, "0")
    home.setProperty(LYRICS_MANUAL_START_PROP, "0")
    home.setProperty(LYRICS_LINE_COUNT_PROP, "0")


def _lyrics_scroll_window(line_count, active_line):
    """Return first/last visible lyric row with the active line near row five."""
    line_count = max(0, int(line_count or 0))
    if line_count <= 0:
        return 0, -1
    active_line = min(max(int(active_line or 0), 0), line_count - 1)
    maximum_start = max(0, line_count - LYRICS_VISIBLE_ROWS)
    start = min(max(active_line - LYRICS_HISTORY_ROWS, 0), maximum_start)
    end = min(line_count - 1, start + LYRICS_VISIBLE_ROWS - 1)
    return start, end


def _publish_lyrics_window(home, lines, start, active_range=None):
    """Publish one fixed 11-row lyrics viewport through Home properties only."""
    lines = list(lines or [])
    line_count = len(lines)
    maximum_start = max(0, line_count - LYRICS_VISIBLE_ROWS)
    try:
        start = min(max(int(start or 0), 0), maximum_start)
    except Exception:
        start = 0
    home.setProperty(LYRICS_WINDOW_START_PROP, str(start))
    home.setProperty(LYRICS_LINE_COUNT_PROP, str(line_count))
    try:
        active_first, active_last = active_range if active_range is not None else (-1, -1)
        active_first, active_last = int(active_first), int(active_last)
    except Exception:
        active_first, active_last = -1, -1
    first_active_slot = -1
    for slot in range(LYRICS_VISIBLE_ROWS):
        absolute = start + slot
        name = LYRICS_LINE_PROP_PREFIX + str(slot)
        active_name = name + ".Active"
        if absolute < line_count:
            line = lines[absolute]
            home.setProperty(name, line if line else " ")
            if active_first <= absolute <= active_last:
                home.setProperty(active_name, "1")
                if first_active_slot < 0:
                    first_active_slot = slot
            else:
                home.clearProperty(active_name)
        else:
            home.clearProperty(name)
            home.clearProperty(active_name)
    if first_active_slot >= 0:
        home.setProperty(LYRICS_ACTIVE_SLOT_PROP, str(first_active_slot))
    else:
        home.clearProperty(LYRICS_ACTIVE_SLOT_PROP)
    return start


def _clear_credits_window(home):
    for slot in range(CREDITS_VISIBLE_ROWS):
        base = CREDITS_VIEW_LINE_PREFIX + str(slot)
        for suffix in ("Left", "Right", "NameSide", "Continuation"):
            home.clearProperty(base + "." + suffix)
    home.clearProperty(CREDITS_DISPLAY_COUNT_PROP)


def _publish_credits_window(home, rows, start):
    """Publish one 13-row wrapped credits viewport through Home properties."""
    rows = list(rows or [])
    count = len(rows)
    maximum = max(0, count - CREDITS_VISIBLE_ROWS)
    try:
        start = min(max(int(start or 0), 0), maximum)
    except Exception:
        start = 0
    home.setProperty(CREDITS_WINDOW_START_PROP, str(start))
    if count:
        home.setProperty(CREDITS_DISPLAY_COUNT_PROP, str(count))
    else:
        home.clearProperty(CREDITS_DISPLAY_COUNT_PROP)
    for slot in range(CREDITS_VISIBLE_ROWS):
        target_base = CREDITS_VIEW_LINE_PREFIX + str(slot)
        source_index = start + slot
        if source_index < count:
            left, right, name_side, continuation = rows[source_index]
            values = {
                "Left": left,
                "Right": right,
                "NameSide": name_side,
                "Continuation": "1" if continuation else "",
            }
            for suffix, value in values.items():
                if value:
                    home.setProperty(target_base + "." + suffix, str(value))
                else:
                    home.clearProperty(target_base + "." + suffix)
        else:
            for suffix in ("Left", "Right", "NameSide", "Continuation"):
                home.clearProperty(target_base + "." + suffix)
    return start


def _debug_value(value):
    value = (value or "").strip()
    return value if value else "<leer>"


def _update_lyrics_debug(home, raw_lyrics):
    """Expose the exact Kodi/CU-LRC state on the temporary diagnostics page."""
    kodi_artist = xbmc.getInfoLabel("MusicPlayer.Artist") or ""
    kodi_title = xbmc.getInfoLabel("MusicPlayer.Title") or ""
    kodi_album = xbmc.getInfoLabel("MusicPlayer.Album") or ""
    kodi_file = xbmc.getInfoLabel("Player.Filename") or ""
    lyric_script = xbmc.getInfoLabel("Skin.String(LyricScript_Path)") or ""
    cleaned = home.getProperty(LYRICS_TEXT_PROP) or ""
    lines = [
        "LYRICS-DIAGNOSE 5.0.78",
        "Kodi Artist: " + _debug_value(kodi_artist),
        "Kodi Titel: " + _debug_value(kodi_title),
        "Kodi Album: " + _debug_value(kodi_album),
        "Kodi Datei: " + _debug_value(kodi_file),
        "Skin LyricScript_Path: " + _debug_value(lyric_script),
        "CU LRC running: " + _debug_value(home.getProperty(CULRC_RUNNING_PROP)),
        "CU LRC source: " + _debug_value(home.getProperty(CULRC_SOURCE_PROP)),
        "CU LRC islrc: " + _debug_value(home.getProperty(CULRC_ISLRC_PROP)),
        "CU LRC haslist: " + _debug_value(home.getProperty(CULRC_HASLIST_PROP)),
        "CU LRC manual: " + _debug_value(home.getProperty(CULRC_MANUAL_PROP)),
        "CU LRC manual artist: " + _debug_value(home.getProperty(CULRC_ARTIST_PROP)),
        "CU LRC manual track: " + _debug_value(home.getProperty(CULRC_TRACK_PROP)),
        "CU LRC lyrics roh: {} Zeichen".format(len(raw_lyrics or "")),
        "Popup LyricsText: {} Zeichen".format(len(cleaned)),
        "",
        "--- Songtext ---",
        cleaned if cleaned else ("Songtext wird gesucht …" if home.getProperty(CULRC_RUNNING_PROP) == "true" else "Kein Songtext verfügbar."),
    ]
    home.setProperty(LYRICS_DEBUG_PROP, "[CR]".join(lines))


def _selection_target(home):
    value = home.getProperty(SELECTION_TARGET_PROP)
    if value == "":
        return None
    try:
        return int(value)
    except Exception:
        home.clearProperty(SELECTION_TARGET_PROP)
        home.clearProperty(SELECTION_GOTO_PENDING_PROP)
        return None


def _consume_selection_goto_pending(home, max_age=3.0):
    """Consume the one Stop callback expected from a popup Player.GoTo request.

    PAPPlayer can emit onPlayBackStopped before Kodi updates the playlist index.
    The old target==current check therefore raced with that index update and
    intermittently treated a song selection as a real Stop, closing the popup.
    """
    raw = home.getProperty(SELECTION_GOTO_PENDING_PROP)
    home.clearProperty(SELECTION_GOTO_PENDING_PROP)
    if not raw:
        return False
    try:
        age = time.time() - float(raw)
    except Exception:
        return False
    return 0.0 <= age <= float(max_age)


def _skin_string(name, default=""):
    value = xbmc.getInfoLabel("Skin.String({})".format(name))
    return value or default


def _seconds(name, default):
    try:
        return max(0, int(_skin_string(name, str(default))))
    except Exception:
        return default


def _selector_enabled():
    return _skin_string("CCSongSelectorEnabled", "true").strip().lower() != "false"


def _auto_open_enabled():
    return _skin_string(AUTO_OPEN_SETTING, "false").strip().lower() == "true"


def _selector_context():
    """Stable home/music context used by selector data and playback information.

    Playback information has its own setup section since 5.0.113, so time/fanart
    properties must keep updating even when the optional Songselektor UI is disabled.
    Popup visibility itself is still guarded by CCSongSelectorEnabled in the skin and
    in the auto-open/action paths. Player.HasAudio is intentionally omitted here because
    it can drop briefly during a normal track transition.
    """
    return xbmc.getCondVisibility(
        "[Window.IsActive(Home) | Window.IsActive(1116)] + "
        "!String.IsEqual(Playlist.Length(music),0) + !Playlist.IsRandom + "
        "String.IsEmpty(Window(Videos).Property(PlayingBackgroundMedia))"
    )


def _audio_active():
    return xbmc.getCondVisibility("Player.HasAudio")


def _focus(control_id):
    xbmc.executebuiltin("Control.SetFocus({})".format(int(control_id)))


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
    """Store a rendered time and its exact character count for compact XML layout."""
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
    value = (xbmc.getInfoLabel("Skin.String({})".format(name)) or "").strip().lower()
    if not value:
        return bool(default)
    return value == "true"


def _time_badge_class(left, right):
    """Return a compact fixed-width class for Roboto 20 time badge text.

    Roboto's tabular digits are 11 px at size 20; colon, space and pipe are
    about 5 px. Add 10 px padding on each side, then round up to the nearest
    supported class. This is stable in Kodi and avoids the previous 250 px tile.
    """
    text = "{} | {}".format(left or "", right or "")
    text_width = 0
    for ch in text:
        if ch.isdigit() or ch == "−":
            text_width += 11
        elif ch in (":", " ", "|"):
            text_width += 5
        else:
            text_width += 11
    # Keep a small safety reserve. Kodi/FreeType may measure Roboto fractionally
    # wider on LibreELEC; without this reserve a <1 px overflow triggers Kodi's
    # ellipsis and visually removes several digits.
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
        total += max(0, duration)
        if index < playing:
            before += max(0, duration)
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
        for prop in (SONG_ELAPSED_PROP, SONG_DURATION_PROP, SONG_REMAINING_PROP,
                     SONG_ELAPSED_LEN_PROP, SONG_DURATION_LEN_PROP, SONG_REMAINING_LEN_PROP,
                     SONG_LONG_PROP):
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
        for prop in (ALBUM_ELAPSED_PROP, ALBUM_DURATION_PROP, ALBUM_REMAINING_PROP,
                     ALBUM_ELAPSED_LEN_PROP, ALBUM_DURATION_LEN_PROP, ALBUM_REMAINING_LEN_PROP,
                     ALBUM_LONG_PROP):
            home.clearProperty(prop)

    _publish_time_badge_classes(home)


def _list_focused():
    return xbmc.getCondVisibility("Window.IsActive({}) + Control.HasFocus({})".format(DIALOG_ID, 9110))


def _container_position():
    if not _list_focused():
        return None
    try:
        current_item = int(xbmc.getInfoLabel("Container({}).CurrentItem".format(LIST_ID)) or 0)
        return current_item - 1 if current_item > 0 else None
    except Exception:
        return None


def _close_dialog():
    xbmc.executebuiltin("Dialog.Close({},true)".format(DIALOG_ID))


def _programmatic_focus_active(home):
    try:
        return float(home.getProperty(PROGRAMMATIC_UNTIL_PROP) or "0") > time.time()
    except Exception:
        return False


def _set_navigation_highlight(home, enabled):
    if enabled:
        home.setProperty(HIGHLIGHT_PROP, "1")
    else:
        home.clearProperty(HIGHLIGHT_PROP)


def _hide_navigation_highlight(home):
    """Hide the grey navigation focus and park on the neutral control."""
    _set_navigation_highlight(home, False)
    _focus(NEUTRAL_CONTROL_ID)


class _PlaybackEvents(xbmc.Player):
    """Minimal player callback bridge for events polling cannot distinguish.

    In particular Player.HasAudio also drops briefly between tracks.  A real
    Stop button, however, fires onPlayBackStopped.  Recording Stop plus the next
    AV-start lets the service close immediately and recognize a fast Stop/Play
    without reintroducing flicker at normal track transitions.
    """
    def __init__(self):
        super(_PlaybackEvents, self).__init__()
        self.stop_serial = 0
        self.start_serial = 0

    def onPlayBackStopped(self):
        clear_pause_guard()
        xbmc.log(
            "[CC-TRANSITION] callback=onPlayBackStopped idx={} title={!r} file={!r}".format(
                current(),
                xbmc.getInfoLabel("Player.Title") or "",
                xbmc.getInfoLabel("Player.FilenameAndPath") or "",
            ),
            xbmc.LOGINFO,
        )
        self.stop_serial += 1

    def onPlayBackEnded(self):
        xbmc.log(
            "[CC-TRANSITION] callback=onPlayBackEnded idx={} title={!r} file={!r}".format(
                current(),
                xbmc.getInfoLabel("Player.Title") or "",
                xbmc.getInfoLabel("Player.FilenameAndPath") or "",
            ),
            xbmc.LOGINFO,
        )
        # Track end is not an explicit Stop. Keep the selector alive across
        # natural playlist transitions; final playback end is still handled by
        # the existing Player.HasAudio timeout.
        pass

    def onPlayBackPaused(self):
        xbmc.log(
            "[CC-TRANSITION] callback=onPlayBackPaused idx={} title={!r}".format(
                current(),
                xbmc.getInfoLabel("Player.Title") or "",
            ),
            xbmc.LOGINFO,
        )
        guard_pause_focus()

    def onPlayBackResumed(self):
        xbmc.log(
            "[CC-TRANSITION] callback=onPlayBackResumed idx={} title={!r}".format(
                current(),
                xbmc.getInfoLabel("Player.Title") or "",
            ),
            xbmc.LOGINFO,
        )
        restore_pause_focus()

    def onPlayBackStarted(self):
        xbmc.log(
            "[CC-TRANSITION] callback=onPlayBackStarted idx={} title={!r} file={!r}".format(
                current(),
                xbmc.getInfoLabel("Player.Title") or "",
                xbmc.getInfoLabel("Player.FilenameAndPath") or "",
            ),
            xbmc.LOGINFO,
        )
        self.start_serial += 1

    def onAVStarted(self):
        xbmc.log(
            "[CC-TRANSITION] callback=onAVStarted idx={} title={!r} file={!r}".format(
                current(),
                xbmc.getInfoLabel("Player.Title") or "",
                xbmc.getInfoLabel("Player.FilenameAndPath") or "",
            ),
            xbmc.LOGINFO,
        )
        self.start_serial += 1



def run():
    sync_on_startup()
    monitor = xbmc.Monitor()
    home = xbmcgui.Window(HOME_ID)
    credits_runtime = CreditsRuntime()
    credits_runtime.start()
    playback_events = _PlaybackEvents()
    last_stop_serial = playback_events.stop_serial
    last_start_serial = playback_events.start_serial
    last_touch = home.getProperty(TOUCH_PROP)
    last_user_activity = time.monotonic()
    last_size = -1
    last_art_file = ""
    last_list_position = None
    was_open = False
    meta = []
    last_time_update = 0.0
    audio_missing_since = None
    last_playing = -1
    last_lyrics_file = None
    blocked_lyrics_raw = None
    last_lyrics_raw = None
    lyrics_sync_entries = []
    lyrics_sync_times = []
    lyrics_line_count = 0
    lyrics_lines = []
    last_lyrics_active = -1
    last_lyrics_window_key = None
    last_lyrics_sync_enabled = None
    last_lyrics_font_signature = None
    last_credits_window_key = None
    last_credits_source_key = None
    credits_display_rows = []
    stop_wait_for_audio_clear = False
    last_transition_state = None

    # Auto-open is session based: opening once at playback start must never mean
    # reopening on every track change. A brief Player.HasAudio gap between songs
    # therefore does not end the session.
    playback_session_active = _audio_active()
    playback_missing_since = None
    last_auto_open_setting = _auto_open_enabled()
    # If the service/skin is (re)started while music is already playing and the
    # option is enabled, arm exactly one automatic opening. Previously this state
    # was initialized as an already-active session with no pending open, so the
    # configured auto-popup could be skipped for the whole playback session.
    auto_open_pending = bool(playback_session_active and last_auto_open_setting)

    while not monitor.abortRequested():
        # Keep the album wrap properties current in both Custom and Standard mode.
        # The rest of the service remains inert in Standard mode as before.
        _update_album_wrap_properties(home)
        _update_song_wrap_properties(home)
        # Standard Confluence mode keeps the custom service installed but inert.
        # This prevents auto-popup/navigation side effects while the original
        # Confluence XML set is active.
        if xbmc.getCondVisibility("Skin.HasSetting(CCStandardConfluence)"):
            clear_credits_properties()
            if popup_open():
                try:
                    close_popup()
                    _close_dialog()
                except Exception:
                    pass
            if monitor.waitForAbort(0.5):
                break
            continue

        try:
            credits_runtime.poll()
        except Exception as exc:
            xbmc.log("[ConfluenceCustom] Credits runtime: {!r}".format(exc), xbmc.LOGWARNING)

        now = time.monotonic()
        audio = _audio_active()
        auto_open_enabled = _auto_open_enabled()

        # Safety net for the pause guard. The callbacks above normally move
        # focus immediately; this also protects against another GUI action
        # reclaiming the native playlist while playback remains paused.
        if xbmc.getCondVisibility("Player.Paused"):
            if popup_open() and not detail_view() and _list_focused():
                guard_pause_focus()
        else:
            restore_pause_focus()

        # Diagnostic only: record the exact Kodi runtime state whenever one of
        # the values that drives the footer/popup changes. This does not mutate
        # playback or skin state.
        diag_state = (
            current(),
            xbmc.getInfoLabel("Player.Title") or "",
            xbmc.getInfoLabel("MusicPlayer.Title") or "",
            xbmc.getInfoLabel("Player.FilenameAndPath") or "",
            bool(audio),
        )
        if diag_state != last_transition_state:
            last_transition_state = diag_state
            xbmc.log(
                "[CC-TRANSITION] state idx={} Player.Title={!r} MusicPlayer.Title={!r} "
                "file={!r} has_audio={} time={!r} duration={!r}".format(
                    diag_state[0],
                    diag_state[1],
                    diag_state[2],
                    diag_state[3],
                    diag_state[4],
                    xbmc.getInfoLabel("Player.Time") or "",
                    xbmc.getInfoLabel("Player.Duration") or "",
                ),
                xbmc.LOGINFO,
            )

        # Kodi/PAPLayer also fires onPlayBackStopped when Player.GoTo replaces
        # the current playlist item. play_focused() sets SELECTION_TARGET_PROP
        # before issuing Player.GoTo, so that existing state is the exact marker
        # that distinguishes an explicit popup selection from a real Stop button.
        if playback_events.stop_serial != last_stop_serial:
            last_stop_serial = playback_events.stop_serial
            selection_target = _selection_target(home)
            goto_stop_expected = _consume_selection_goto_pending(home)
            selection_in_progress = (
                popup_open()
                and selection_target is not None
                and goto_stop_expected
            )
            if not selection_in_progress:
                playback_session_active = False
                playback_missing_since = None
                auto_open_pending = False
                audio_missing_since = None
                stop_wait_for_audio_clear = True
                _clear_times(home)
                home.clearProperty(LYRICS_TEXT_PROP)
                home.clearProperty(LYRICS_SYNC_PROP)
                home.clearProperty(SELECTION_TARGET_PROP)
                home.clearProperty(SELECTION_GOTO_PENDING_PROP)
                lyrics_sync_entries = []
                lyrics_sync_times = []
                lyrics_line_count = 0
                lyrics_lines = []
                last_lyrics_active = -1
                last_lyrics_window_key = None
                last_lyrics_sync_enabled = None
                last_lyrics_font_signature = None
                _clear_lyrics_window(home)
                _clear_credits_window(home)
                home.clearProperty(CREDITS_WINDOW_START_PROP)
                last_credits_window_key = None
                last_credits_source_key = None
                credits_display_rows = []
                if popup_open():
                    close_popup()
                    _close_dialog()
                was_open = False

        # If Play follows Stop so quickly that polling never observes HasAudio=false,
        # the AV-start callback still marks this as a genuinely new playback session.
        if playback_events.start_serial != last_start_serial:
            last_start_serial = playback_events.start_serial
            if stop_wait_for_audio_clear or not playback_session_active:
                stop_wait_for_audio_clear = False
                playback_session_active = True
                playback_missing_since = None
                if auto_open_enabled:
                    auto_open_pending = True

        # Enabling the option during an already running session arms one opening
        # for the next visit to Home. Starting a new playback session does the same.
        if auto_open_enabled and not last_auto_open_setting and audio:
            auto_open_pending = True
        last_auto_open_setting = auto_open_enabled

        if stop_wait_for_audio_clear:
            if not audio:
                stop_wait_for_audio_clear = False
            # Do not reinterpret the tail of the stopped stream as a new start.
        elif audio:
            if not playback_session_active:
                playback_session_active = True
                if auto_open_enabled:
                    auto_open_pending = True
            playback_missing_since = None
        elif playback_session_active:
            if playback_missing_since is None:
                playback_missing_since = now
            elif now - playback_missing_since >= 2.5:
                playback_session_active = False
                playback_missing_since = None
                auto_open_pending = False
        else:
            playback_missing_since = None

        # The popup belongs to Home. If music starts elsewhere we remember the
        # request and open it once, immediately on the next visit to Home.
        if (auto_open_pending and auto_open_enabled and audio and _selector_enabled()
                and xbmc.getCondVisibility("Window.IsActive(Home)")
                and xbmc.getCondVisibility("!String.IsEqual(Playlist.Length(music),0) + !Playlist.IsRandom + String.IsEmpty(Window(Videos).Property(PlayingBackgroundMedia))")
                and not popup_open()):
            open_popup()
            auto_open_pending = False

        context = _selector_context()
        opened = popup_open()

        if context:
            count = size()
            playing = current() if count > 0 else -1
            count_changed = count != last_size

            # Credits use the same crash-safe property viewport principle as lyrics.
            # 0.1.31 publishes logical structured rows. 5.0.90 expands them into
            # physical display rows first so long credits wrap without losing the
            # highlighted name segment. Continuation rows are indented by the XML.
            credits_count = max(0, _int_property(home, CREDITS_SOURCE_COUNT_PROP, 0))
            credits_updated = home.getProperty(CREDITS_SOURCE_UPDATED_PROP) or ""
            font_signature = _songselector_font_signature()
            credits_source_key = (credits_updated, credits_count, font_signature)
            if credits_source_key != last_credits_source_key:
                credits_display_rows = _build_credit_display_rows(home, font_signature)
                if credits_display_rows:
                    home.setProperty(CREDITS_DISPLAY_COUNT_PROP, str(len(credits_display_rows)))
                else:
                    home.clearProperty(CREDITS_DISPLAY_COUNT_PROP)
                last_credits_source_key = credits_source_key
                last_credits_window_key = None
            credits_start = _int_property(home, CREDITS_WINDOW_START_PROP, 0)
            credits_key = (credits_source_key, len(credits_display_rows), credits_start)
            if credits_key != last_credits_window_key:
                actual_credits_start = _publish_credits_window(home, credits_display_rows, credits_start)
                last_credits_window_key = (credits_source_key, len(credits_display_rows), actual_credits_start)

            # CU LRC Lyrics is the optional provider for the third popup page.
            # Never carry the previous song's text into a newly playing track:
            # if CU LRC has not cleared/replaced its property yet, block that exact
            # old value until the provider changes or clears it.
            raw_lyrics = home.getProperty(CULRC_LYRICS_PROP) or ""
            lyrics_file = xbmc.getInfoLabel("Player.FilenameAndPath") or ""
            if audio and lyrics_file:
                if last_lyrics_file is None:
                    last_lyrics_file = lyrics_file
                elif lyrics_file != last_lyrics_file:
                    blocked_lyrics_raw = raw_lyrics or None
                    last_lyrics_file = lyrics_file
                    last_lyrics_raw = None
                    home.clearProperty(LYRICS_TEXT_PROP)
                    home.setProperty(LYRICS_SYNC_PROP, "1")
                    lyrics_sync_entries = []
                    lyrics_sync_times = []
                    lyrics_line_count = 0
                    lyrics_lines = []
                    last_lyrics_active = -1
                    last_lyrics_window_key = None
                    last_lyrics_sync_enabled = None
                    last_lyrics_font_signature = None
                    _clear_lyrics_window(home)

            if not audio:
                home.clearProperty(LYRICS_TEXT_PROP)
                home.clearProperty(LYRICS_SYNC_PROP)
                blocked_lyrics_raw = None
                last_lyrics_raw = None
                lyrics_sync_entries = []
                lyrics_sync_times = []
                lyrics_line_count = 0
                lyrics_lines = []
                last_lyrics_active = -1
                last_lyrics_window_key = None
                last_lyrics_sync_enabled = None
                last_lyrics_font_signature = None
                _clear_lyrics_window(home)
            elif not raw_lyrics:
                home.clearProperty(LYRICS_TEXT_PROP)
                blocked_lyrics_raw = None
                last_lyrics_raw = ""
                lyrics_sync_entries = []
                lyrics_sync_times = []
                lyrics_line_count = 0
                lyrics_lines = []
                last_lyrics_active = -1
                last_lyrics_window_key = None
                last_lyrics_font_signature = None
                _clear_lyrics_window(home)
            elif blocked_lyrics_raw is not None and raw_lyrics == blocked_lyrics_raw:
                home.clearProperty(LYRICS_TEXT_PROP)
            else:
                blocked_lyrics_raw = None
                current_lyrics_font_signature = _songselector_font_signature()
                if raw_lyrics != last_lyrics_raw or current_lyrics_font_signature != last_lyrics_font_signature:
                    cleaned_lyrics, lyrics_sync_entries, lyrics_line_count = _clean_and_time_culrc_lyrics(raw_lyrics)
                    lyrics_sync_times = [entry[0] for entry in lyrics_sync_entries]
                    lyrics_lines = cleaned_lyrics.split("[CR]") if cleaned_lyrics else []
                    if cleaned_lyrics:
                        home.setProperty(LYRICS_TEXT_PROP, cleaned_lyrics)
                        home.setProperty(LYRICS_MANUAL_START_PROP, "0")
                        _publish_lyrics_window(home, lyrics_lines, 0, None)
                    else:
                        home.clearProperty(LYRICS_TEXT_PROP)
                        _clear_lyrics_window(home)
                    if home.getProperty(LYRICS_SYNC_PROP) == "":
                        home.setProperty(LYRICS_SYNC_PROP, "1")
                    last_lyrics_active = -1
                    last_lyrics_window_key = None
                    last_lyrics_sync_enabled = None
                    last_lyrics_raw = raw_lyrics
                    last_lyrics_font_signature = current_lyrics_font_signature

            # CU LRC's JJS compatibility build reports a definitive per-track
            # result. Once no lyrics were found, remove the third page immediately
            # instead of leaving a permanent 'searching' placeholder.
            if lyrics_view() and home.getProperty(CULRC_STATUS_PROP) == 'not_found':
                show_credits()

            # Synchronized LRC display uses a fixed, property-backed 11-row
            # viewport. This deliberately avoids mutating Kodi GUI controls from
            # the background service, which can crash Kodi 21.
            sync_enabled = home.getProperty(LYRICS_SYNC_PROP) != "0"
            sync_ready = (
                lyrics_view()
                and (home.getProperty(CULRC_ISLRC_PROP) or "").strip().lower() == "true"
                and bool(lyrics_sync_entries)
                and lyrics_line_count > 0
            )
            if sync_enabled != last_lyrics_sync_enabled:
                last_lyrics_window_key = None
                last_lyrics_sync_enabled = sync_enabled

            active_first = -1
            active_last = -1
            if sync_ready and sync_enabled:
                try:
                    # LRC timestamps tend to feel slightly early when switched
                    # exactly on the timestamp. Hold the previous line by the
                    # user-selected amount before advancing the visual highlight.
                    lyric_time = max(0.0, float(xbmc.Player().getTime()) - _lyrics_sync_delay_seconds())
                except Exception:
                    lyric_time = 0.0
                entry_pos = bisect.bisect_right(lyrics_sync_times, lyric_time) - 1
                if entry_pos >= 0:
                    active_first = lyrics_sync_entries[entry_pos][1]
                    active_last = lyrics_sync_entries[entry_pos][2]

            if lyrics_view() and lyrics_lines:
                if sync_enabled and active_first >= 0:
                    window_start, _unused = _lyrics_scroll_window(lyrics_line_count, active_first)
                elif sync_enabled:
                    window_start = 0
                else:
                    window_start = _int_property(home, LYRICS_MANUAL_START_PROP,
                                                 _int_property(home, LYRICS_WINDOW_START_PROP, 0))
                    # Paused/manual mode deliberately has no active-line highlight.
                    active_first = -1
                    active_last = -1
                active_range = (active_first, active_last) if active_first >= 0 else None
                window_key = (window_start, active_first, active_last, len(lyrics_lines), sync_enabled)
                if window_key != last_lyrics_window_key:
                    actual_start = _publish_lyrics_window(home, lyrics_lines, window_start, active_range)
                    if not sync_enabled:
                        home.setProperty(LYRICS_MANUAL_START_PROP, str(actual_start))
                    last_lyrics_window_key = (actual_start, active_first, active_last, len(lyrics_lines), sync_enabled)
                last_lyrics_active = active_first
            else:
                if lyrics_lines:
                    # Keep the first rows ready for the instant the page is opened.
                    window_key = (0, -1, -1, len(lyrics_lines), True)
                    if last_lyrics_window_key != window_key:
                        _publish_lyrics_window(home, lyrics_lines, 0, None)
                        last_lyrics_window_key = window_key
                last_lyrics_active = -1

            # Album-time calculation still needs playlist metadata, but only when
            # the queue changes. Popup navigation itself is now a native Kodi list.
            if not meta or count_changed:
                meta = playlist_metadata()

            if audio:
                audio_missing_since = None
                playing_file = xbmc.getInfoLabel("Player.FilenameAndPath") or ""
                if playing_file and playing_file != last_art_file:
                    sync_back_art()
                    sync_compact_cover_width()
                    last_art_file = playing_file
                if now - last_time_update >= 0.50:
                    _set_times(home, meta, playing)
                    last_time_update = now
            elif opened:
                if audio_missing_since is None:
                    audio_missing_since = now
                if now - audio_missing_since >= 2.5:
                    home.clearProperty(SELECTION_TARGET_PROP)
                    home.clearProperty(SELECTION_GOTO_PENDING_PROP)
                    close_popup()
                    _close_dialog()
                    opened = False
            else:
                _clear_times(home)

            if opened:
                if not was_open:
                    # open_popup() has already positioned the native list before
                    # revealing the grey navigation tile. Do not repeat that
                    # selectItem sequence here: the second pass was the visible
                    # bottom-to-current jump when the dialog opened.
                    last_user_activity = now
                    last_list_position = _container_position()

                touch = home.getProperty(TOUCH_PROP)
                if touch and touch != last_touch:
                    last_touch = touch
                    last_user_activity = now

                # Observe Kodi's native absolute current item. A change outside our
                # short programmatic-focus grace period is real Up/Down navigation.
                position = _container_position()
                if position is not None and position != last_list_position:
                    last_list_position = position
                    if not _programmatic_focus_active(home):
                        _set_navigation_highlight(home, True)
                        last_user_activity = now

                selected_target = _selection_target(home)
                explicit_selection = selected_target == playing

                # Natural track changes follow immediately only when the user has
                # not left the current row to browse. While browsing, the cursor
                # stays where the user put it until the inactivity timeout below.
                if was_open and not detail_view() and last_playing >= 0 and playing != last_playing:
                    position = _container_position()
                    if explicit_selection or position == last_playing or position == playing:
                        focus_current(take_focus=True)
                        last_list_position = playing
                    if selected_target is not None:
                        home.clearProperty(SELECTION_TARGET_PROP)
                        home.clearProperty(SELECTION_GOTO_PENDING_PROP)

                selection_timeout = _seconds(SELECTION_TIMEOUT_SETTING, 5)
                if (not detail_view() and selection_timeout and _list_focused()
                        and now - last_user_activity >= selection_timeout):
                    position = _container_position()
                    if position is not None and position != playing:
                        focus_current(take_focus=True)
                        last_list_position = playing
                    # Keep the permanent navigation highlight active. Reset the
                    # timer so we do not repeatedly reposition the same row.
                    _set_navigation_highlight(home, True)
                    last_user_activity = now

        else:
            _clear_times(home)
            _set_navigation_highlight(home, False)
            home.clearProperty(LYRICS_TEXT_PROP)
            home.clearProperty(LYRICS_SYNC_PROP)
            home.clearProperty(SELECTION_TARGET_PROP)
            home.clearProperty(SELECTION_GOTO_PENDING_PROP)
            clear_pause_guard()
            lyrics_sync_entries = []
            lyrics_sync_times = []
            lyrics_line_count = 0
            lyrics_lines = []
            last_lyrics_active = -1
            last_lyrics_window_key = None
            last_lyrics_sync_enabled = None
            _clear_lyrics_window(home)
            _clear_credits_window(home)
            home.clearProperty(CREDITS_WINDOW_START_PROP)
            last_credits_window_key = None
            last_lyrics_file = None
            blocked_lyrics_raw = None
            last_lyrics_raw = None
            clear_back_art()
            last_art_file = ""
            meta = []
            audio_missing_since = None
            if opened:
                close_popup()
                _close_dialog()
                opened = False
            playing = -1
            count = -1

        last_size = count
        was_open = opened
        last_playing = playing

        if monitor.waitForAbort(0.15):
            break

    clear_credits_properties()


SERVICE_RUNNING_PROP = "ConfluenceCustom.SongSelector.ServiceRunning"

if __name__ == "__main__":
    _service_home = xbmcgui.Window(HOME_ID)
    if _service_home.getProperty(SERVICE_RUNNING_PROP) != "1":
        _service_home.setProperty(SERVICE_RUNNING_PROP, "1")
        try:
            run()
        finally:
            _service_home.clearProperty(SERVICE_RUNNING_PROP)
