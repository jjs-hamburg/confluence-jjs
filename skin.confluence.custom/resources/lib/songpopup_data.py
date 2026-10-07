# -*- coding: utf-8 -*-
"""Pure property/data helpers for the Confluence-jjs Song Popup.

No function in this module calls Window.getControl() or mutates Kodi GUI controls.
The dialog renders fixed XML controls from Home-window properties only.
"""
from __future__ import absolute_import

import re

import xbmc

LYRICS_TEXT_PROP = "ConfluenceCustom.SongSelector.LyricsText"
LYRICS_SYNC_PROP = "ConfluenceCustom.SongSelector.LyricsSync"
LYRICS_VISIBLE_ROWS = 11
LYRICS_HISTORY_ROWS = 4
LYRICS_LINE_PROP_PREFIX = "ConfluenceCustom.SongSelector.LyricsLine"
LYRICS_ACTIVE_SLOT_PROP = "ConfluenceCustom.SongSelector.LyricsActiveSlot"
LYRICS_WINDOW_START_PROP = "ConfluenceCustom.SongSelector.LyricsWindowStart"
LYRICS_MANUAL_START_PROP = "ConfluenceCustom.SongSelector.LyricsManualStart"
LYRICS_LINE_COUNT_PROP = "ConfluenceCustom.SongSelector.LyricsLineCount"

CREDITS_SOURCE_COUNT_PROP = "ConfluenceCustom.Credits.LineCount"
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

_MOJIBAKE_MARKERS = ("Ã", "Â", "â", "ð", "ï¿½")


def repair_mojibake(text):
    """Repair UTF-8 text that was accidentally decoded as a Western code page.

    The repair is deliberately conservative: unchanged Unicode wins unless a
    round-trip through cp1252/latin-1 measurably removes mojibake markers.
    Two passes cover the common double-decoding case without touching normal
    lyrics containing umlauts, accents, dashes or other valid Unicode.
    """
    value = str(text or "")
    if not value:
        return value

    def badness(candidate):
        return sum(candidate.count(marker) for marker in _MOJIBAKE_MARKERS) + (candidate.count("\ufffd") * 10)

    for _unused in range(2):
        current_score = badness(value)
        if current_score <= 0:
            break
        candidates = [value]
        for encoding in ("cp1252", "latin-1"):
            try:
                candidates.append(value.encode(encoding).decode("utf-8"))
            except (UnicodeEncodeError, UnicodeDecodeError):
                pass
        best = min(candidates, key=badness)
        if badness(best) >= current_score:
            break
        value = best
    return value


def int_property(home, name, default=0):
    try:
        return int(home.getProperty(name) or default)
    except Exception:
        return int(default)


def font_signature():
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


def _estimated_text_width(text, signature=None):
    family, size = signature or font_signature()
    family_factor = 1.0
    if "montserrat" in family:
        family_factor = 1.04
    elif "bold" in family:
        family_factor = 1.02
    units = 0.0
    for char in str(text or ""):
        if char.isspace():
            units += 0.28
        elif char in "ilI1|!.,:;'`":
            units += 0.27
        elif char in "mwMW@#%&QO":
            units += 0.82
        elif char.isupper():
            units += 0.62
        elif ord(char) > 0x2FFF:
            units += 0.95
        else:
            units += 0.52
    return units * float(size) * family_factor


def _append_word(current, word):
    return (current + " " + word).strip() if current else word


def _hard_split_word(word, width_px, signature):
    word = str(word or "")
    if not word:
        return "", ""
    piece = ""
    for pos, char in enumerate(word):
        trial = piece + char
        if piece and _estimated_text_width(trial, signature) > width_px:
            return piece, word[pos:]
        piece = trial
    return piece, ""


def _wrap_plain_text(text, width_px, signature=None):
    signature = signature or font_signature()
    words = str(text or "").split()
    if not words:
        return [""]
    rows = []
    current = ""
    pending = list(words)
    while pending:
        word = pending.pop(0)
        trial = _append_word(current, word)
        if not current or _estimated_text_width(trial, signature) <= width_px:
            if not current and _estimated_text_width(word, signature) > width_px:
                piece, remainder = _hard_split_word(word, width_px, signature)
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


def _parse_lrc_timestamp(tag):
    match = re.match(r"^\[(\d{1,3}):(\d{1,2})(?:[.:](\d{1,3}))?\]$", tag or "")
    if not match:
        return None
    minutes = int(match.group(1))
    seconds = int(match.group(2))
    fraction_text = match.group(3) or ""
    fraction = int(fraction_text) / float(10 ** len(fraction_text)) if fraction_text else 0.0
    return (minutes * 60.0) + seconds + fraction


def clean_and_time_lyrics(raw):
    text = repair_mojibake(raw or "").replace("\ufeff", "").replace("\x00", "")
    text = text.replace("[CR]", "\n").replace("\r\n", "\n").replace("\r", "\n")
    embedded_offset = 0.0
    offset_match = re.search(r"^\s*\[offset:\s*(-?\d+)\]\s*$", text, flags=re.I | re.M)
    if offset_match:
        try:
            embedded_offset = float(offset_match.group(1)) / 1000.0
        except Exception:
            embedded_offset = 0.0
    signature = font_signature()
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
                times.append(value - embedded_offset)
            rest = rest[match.end():]
        rest = _LRC_TIME_RE.sub("", rest)
        rest = _LRC_SIMPLE_TIME_RE.sub("", rest)
        rest = _LRC_ENHANCED_TIME_RE.sub("", rest).strip()
        if not rest:
            if out and not blank:
                out.append("")
            blank = True
            continue
        wrapped = _wrap_plain_text(rest, LYRICS_WRAP_WIDTH_PX, signature)
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


def clear_lyrics_window(home):
    for slot in range(LYRICS_VISIBLE_ROWS):
        base = LYRICS_LINE_PROP_PREFIX + str(slot)
        home.clearProperty(base)
        home.clearProperty(base + ".Active")
    home.clearProperty(LYRICS_ACTIVE_SLOT_PROP)
    home.setProperty(LYRICS_WINDOW_START_PROP, "0")
    home.setProperty(LYRICS_MANUAL_START_PROP, "0")
    home.setProperty(LYRICS_LINE_COUNT_PROP, "0")


def lyrics_scroll_window(line_count, active_line):
    line_count = max(0, int(line_count or 0))
    if line_count <= 0:
        return 0, -1
    active_line = min(max(int(active_line or 0), 0), line_count - 1)
    maximum_start = max(0, line_count - LYRICS_VISIBLE_ROWS)
    start = min(max(active_line - LYRICS_HISTORY_ROWS, 0), maximum_start)
    end = min(line_count - 1, start + LYRICS_VISIBLE_ROWS - 1)
    return start, end


def publish_lyrics_window(home, lines, start, active_range=None):
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


def _credit_row_width(left, right, signature):
    width = _estimated_text_width(left, signature) + _estimated_text_width(right, signature)
    if left and right:
        width += _estimated_text_width(" — ", signature)
    return width


def _wrap_credit_row(left, right, name_side, signature=None):
    signature = signature or font_signature()
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
        return CREDITS_WRAP_WIDTH_PX if logical_row_index == 0 else CREDITS_WRAP_WIDTH_PX - CREDITS_CONTINUATION_INDENT_PX
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
        if _credit_row_width(trial_left, trial_right, signature) <= cap:
            cur_left, cur_right = trial_left, trial_right
            continue
        if cur_left or cur_right:
            flush()
            pending.insert(0, [side, word])
            continue
        piece, remainder = _hard_split_word(word, cap, signature)
        if side == "left":
            cur_left = piece
        else:
            cur_right = piece
        flush()
        if remainder:
            pending.insert(0, [side, remainder])
    flush()
    return rows


def build_credit_display_rows(home, signature=None):
    count = max(0, int_property(home, CREDITS_SOURCE_COUNT_PROP, 0))
    signature = signature or font_signature()
    rows = []
    for source_index in range(count):
        base = CREDITS_SOURCE_PREFIX + str(source_index) + "."
        left = home.getProperty(base + "Left") or ""
        right = home.getProperty(base + "Right") or ""
        name_side = (home.getProperty(base + "NameSide") or "").strip().lower()
        rows.extend(_wrap_credit_row(left, right, name_side, signature))
    return rows


def clear_credits_window(home):
    for slot in range(CREDITS_VISIBLE_ROWS):
        base = CREDITS_VIEW_LINE_PREFIX + str(slot)
        for suffix in ("Left", "Right", "NameSide", "Continuation"):
            home.clearProperty(base + "." + suffix)
    home.clearProperty(CREDITS_DISPLAY_COUNT_PROP)


def publish_credits_window(home, rows, start):
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
            values = {"Left": left, "Right": right, "NameSide": name_side, "Continuation": "1" if continuation else ""}
            for suffix, value in values.items():
                if value:
                    home.setProperty(target_base + "." + suffix, str(value))
                else:
                    home.clearProperty(target_base + "." + suffix)
        else:
            for suffix in ("Left", "Right", "NameSide", "Continuation"):
                home.clearProperty(target_base + "." + suffix)
    return start
