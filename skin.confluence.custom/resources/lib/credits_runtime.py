# -*- coding: utf-8 -*-
"""Skin-owned playback credits runtime for Confluence-jjs.

Credits are resolved from Discogs/MusicBrainz without any dependency on
JJS Music Library Manager.  The cache is deliberately album-oriented JSON;
it is not an artist/person database.
"""
from __future__ import annotations

import json
import os
import queue
import re
import threading
import time

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from credits_resolver import (
    combine_source_results,
    make_album_lookup_identifier,
    parse_identifier,
    resolve_discogs_album_stage,
    resolve_discogs_stage,
    resolve_musicbrainz_album_stage,
    resolve_musicbrainz_stage,
    useful_display_lines,
)

HOME_ID = 10000
PROP_PREFIX = "ConfluenceCustom.Credits."
PROP_TEXT = PROP_PREFIX + "Text"
PROP_STATE = PROP_PREFIX + "State"
PROP_ALBUM_ID = PROP_PREFIX + "AlbumId"
PROP_IDENTIFIER = PROP_PREFIX + "Identifier"
PROP_TITLE = PROP_PREFIX + "Title"
PROP_UPDATED = PROP_PREFIX + "Updated"
PROP_LINE_COUNT = PROP_PREFIX + "LineCount"
PROP_LINE_PREFIX = PROP_PREFIX + "Line."
MAX_CREDIT_LINES = 96
START_DELAY = 2.0
ERROR_CACHE_SECONDS = 15 * 60.0
CACHE_VERSION = 1

_ADDON = xbmcaddon.Addon("skin.confluence.custom")
_PROFILE = xbmcvfs.translatePath(_ADDON.getAddonInfo("profile"))
_CACHE_FILE = os.path.join(_PROFILE, "credits_cache.json")
_CACHE_LOCK = threading.Lock()


def _log(message, level=xbmc.LOGINFO):
    xbmc.log("[ConfluenceCustom Credits] {}".format(message), level)


def _home():
    return xbmcgui.Window(HOME_ID)


def _set_property(name, value=""):
    win = _home()
    value = str(value or "")
    if value:
        win.setProperty(name, value)
    else:
        win.clearProperty(name)


def _line_prop(index, suffix):
    return "%s%d.%s" % (PROP_LINE_PREFIX, int(index), str(suffix))


def _clear_credit_lines():
    home = _home()
    try:
        old_count = int(home.getProperty(PROP_LINE_COUNT) or 0)
    except Exception:
        old_count = 0
    for index in range(min(MAX_CREDIT_LINES, max(0, old_count))):
        for suffix in ("Left", "Right", "NameSide"):
            home.clearProperty(_line_prop(index, suffix))
    home.clearProperty(PROP_LINE_COUNT)


def clear_properties():
    _clear_credit_lines()
    for name in (PROP_TEXT, PROP_STATE, PROP_ALBUM_ID, PROP_IDENTIFIER, PROP_TITLE, PROP_UPDATED):
        _set_property(name, "")


def _fold_display(value):
    value = str(value or "").strip().casefold()
    return re.sub(r"\s+", " ", value)


def _result_names(result):
    names = []
    for credit in (result or {}).get("credits") or []:
        if isinstance(credit, dict):
            value = str(credit.get("person") or "").strip()
            if value:
                names.append(value)
    for ensemble in (result or {}).get("ensembles") or []:
        if isinstance(ensemble, dict):
            value = str(ensemble.get("name") or "").strip()
            if value:
                names.append(value)
    return names


def _side_is_known_name(value, folded_names):
    folded = _fold_display(value)
    if not folded:
        return False
    if folded in folded_names:
        return True
    for name in folded_names:
        if len(name) >= 4 and (folded.startswith(name + " ") or folded.endswith(" " + name)):
            return True
    return False


def _credit_segments(text, name_candidates=None):
    raw_lines = str(text or "").replace("[CR]", "\n").split("\n")
    folded_names = {_fold_display(name) for name in (name_candidates or []) if _fold_display(name)}
    right_name_descriptors = {
        "dirigent", "conductor", "chorleiter", "chorleitung", "choir director",
        "chorus master", "chor", "choir", "chorus", "orchester", "orchestra",
        "ensemble", "band",
    }
    never_name_descriptors = {
        "aufnahmedatum", "aufnahmeort", "recording date", "recording location",
        "quellen", "sources", "discogs", "musicbrainz",
    }
    rows = []
    for raw in raw_lines:
        line = str(raw or "").strip()
        if not line:
            continue
        left, right = line, ""
        if " — " in line:
            left, right = [part.strip() for part in line.split(" — ", 1)]
        side = ""
        left_is_name = _side_is_known_name(left, folded_names)
        right_is_name = _side_is_known_name(right, folded_names)
        if left_is_name and not right_is_name:
            side = "left"
        elif right_is_name and not left_is_name:
            side = "right"
        elif left_is_name:
            side = "left"
        elif right_is_name:
            side = "right"
        elif right:
            descriptor = _fold_display(left)
            if descriptor in right_name_descriptors:
                side = "right"
            elif descriptor in never_name_descriptors:
                side = ""
        rows.append((left, right, side))
    return rows[:MAX_CREDIT_LINES]


def _publish_credit_lines(text, name_candidates=None):
    home = _home()
    rows = _credit_segments(text, name_candidates)
    try:
        old_count = int(home.getProperty(PROP_LINE_COUNT) or 0)
    except Exception:
        old_count = 0
    clear_to = min(MAX_CREDIT_LINES, max(old_count, len(rows)))
    for index in range(clear_to):
        if index < len(rows):
            left, right, side = rows[index]
            home.setProperty(_line_prop(index, "Left"), left)
            if right:
                home.setProperty(_line_prop(index, "Right"), right)
            else:
                home.clearProperty(_line_prop(index, "Right"))
            if side:
                home.setProperty(_line_prop(index, "NameSide"), side)
            else:
                home.clearProperty(_line_prop(index, "NameSide"))
        else:
            for suffix in ("Left", "Right", "NameSide"):
                home.clearProperty(_line_prop(index, suffix))
    if rows:
        home.setProperty(PROP_LINE_COUNT, str(len(rows)))
    else:
        home.clearProperty(PROP_LINE_COUNT)


def _publish(album_id, identifier, state, text="", title="", name_candidates=None):
    plain_text = str(text or "").replace("[B]", "").replace("[/B]", "")
    _publish_credit_lines(plain_text, name_candidates)
    _set_property(PROP_ALBUM_ID, str(int(album_id)) if album_id is not None else "")
    _set_property(PROP_IDENTIFIER, identifier)
    _set_property(PROP_STATE, state)
    _set_property(PROP_TEXT, plain_text.replace("\n", "[CR]"))
    _set_property(PROP_TITLE, title)
    _set_property(PROP_UPDATED, "%.3f" % time.time())


def _json_rpc(method, params=None):
    request = {"jsonrpc": "2.0", "method": method, "id": 1}
    if params is not None:
        request["params"] = params
    try:
        payload = json.loads(xbmc.executeJSONRPC(json.dumps(request)))
    except Exception:
        return None
    if payload.get("error"):
        return None
    return payload.get("result")


def _current_song_id():
    try:
        value = int(xbmc.getInfoLabel("MusicPlayer.DBID") or 0)
        if value > 0:
            return value
    except Exception:
        pass
    result = _json_rpc("Player.GetActivePlayers") or []
    player_id = next((int(p.get("playerid")) for p in result if p.get("type") == "audio"), None)
    if player_id is None:
        return None
    item = (_json_rpc("Player.GetItem", {
        "playerid": player_id, "properties": ["album", "artist", "file"]
    }) or {}).get("item", {})
    try:
        value = int(item.get("id") or 0)
        return value if value > 0 else None
    except Exception:
        return None


def _current_album_id(last_song_id=None, last_album_id=None):
    if not xbmc.Player().isPlayingAudio():
        return None, None
    song_id = _current_song_id()
    if song_id is None:
        return None, None
    if song_id == last_song_id and last_album_id is not None:
        return song_id, last_album_id
    song = (_json_rpc("AudioLibrary.GetSongDetails", {
        "songid": int(song_id), "properties": ["albumid"]
    }) or {}).get("songdetails", {})
    try:
        album_id = int(song.get("albumid", -1))
    except Exception:
        album_id = -1
    return song_id, album_id if album_id >= 0 else None


def _current_album_hints():
    title = str(xbmc.getInfoLabel("MusicPlayer.Album") or "").strip()
    artist = str(xbmc.getInfoLabel("MusicPlayer.AlbumArtist") or "").strip()
    if not artist:
        artist = str(xbmc.getInfoLabel("MusicPlayer.Artist") or "").strip()
    return title, artist


def _album_identifier(album_id):
    result = _json_rpc("AudioLibrary.GetSongs", {
        "properties": ["comment", "albumid", "album", "albumartist", "file"],
        "filter": {"albumid": int(album_id)},
        "limits": {"start": 0, "end": 1000},
    }) or {}
    candidates = []
    seen = set()
    for song in result.get("songs") or []:
        code = str(song.get("comment") or "").strip()
        if not code or code in seen:
            continue
        seen.add(code)
        artists = song.get("albumartist") or []
        artist = artists.strip() if isinstance(artists, str) else " / ".join(
            str(v or "").strip() for v in artists if str(v or "").strip()
        )
        candidates.append({
            "identifier": code,
            "album_title": str(song.get("album") or "").strip(),
            "album_artist": artist,
            "example_file": str(song.get("file") or "").strip(),
        })
    for item in candidates:
        if item["identifier"].lower().startswith("[r"):
            return item
    return candidates[0] if candidates else None


def _ensure_profile():
    try:
        if not os.path.isdir(_PROFILE):
            os.makedirs(_PROFILE, exist_ok=True)
    except Exception:
        pass


def _read_cache():
    _ensure_profile()
    try:
        with open(_CACHE_FILE, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if int(data.get("version") or 0) != CACHE_VERSION:
            return {"version": CACHE_VERSION, "albums": {}}
        if not isinstance(data.get("albums"), dict):
            data["albums"] = {}
        return data
    except Exception:
        return {"version": CACHE_VERSION, "albums": {}}


def _write_cache(data):
    _ensure_profile()
    tmp = _CACHE_FILE + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, sort_keys=True)
        os.replace(tmp, _CACHE_FILE)
    except Exception as exc:
        _log("Cache could not be written: {!r}".format(exc), xbmc.LOGWARNING)
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass


def _load_cached(album_id, identifier):
    with _CACHE_LOCK:
        data = _read_cache()
        row = (data.get("albums") or {}).get(str(int(album_id)))
    if not isinstance(row, dict) or str(row.get("identifier") or "") != str(identifier or ""):
        return None
    result = row.get("result")
    if not isinstance(result, dict):
        return None
    result = dict(result)
    result["_cached_at"] = float(row.get("saved_at") or 0.0)
    return result


def _save_cached(album_id, identifier, result):
    if not isinstance(result, dict):
        return
    with _CACHE_LOCK:
        data = _read_cache()
        data.setdefault("albums", {})[str(int(album_id))] = {
            "identifier": str(identifier or ""),
            "saved_at": time.time(),
            "result": result,
        }
        _write_cache(data)


class CreditsRuntime:
    def __init__(self):
        self._last_song_id = None
        self._last_album_id = None
        self._generation = 0
        self._worker = None
        self._lock = threading.Lock()
        self._events = queue.Queue()

    def start(self):
        _ensure_profile()

    def _still_current(self, generation, album_id):
        with self._lock:
            return generation == self._generation and album_id == self._last_album_id

    def _queue_publish(self, generation, album_id, identifier, state, text="", title="", names=None):
        self._events.put((generation, int(album_id), str(identifier or ""), state,
                          str(text or ""), str(title or ""), list(names or [])))

    def _drain_events(self):
        while True:
            try:
                event = self._events.get_nowait()
            except queue.Empty:
                break
            generation, album_id, identifier, state, text, title, names = event
            if self._still_current(generation, album_id):
                _publish(album_id, identifier, state, text, title, names)

    def _background_worker(self, generation, album_id, info):
        deadline = time.monotonic() + START_DELAY
        while time.monotonic() < deadline:
            if not self._still_current(generation, album_id):
                return
            time.sleep(0.05)

        identifier = info["identifier"]
        album_title = info.get("album_title") or ""
        album_artist = info.get("album_artist") or ""
        published_useful = False
        dg = None
        mb = None

        def publish_result(result):
            nonlocal published_useful
            lines = useful_display_lines(result)
            text = "\n".join(lines).strip()
            if not text or not self._still_current(generation, album_id):
                return False
            title = (result.get("release") or {}).get("title") or album_title
            self._queue_publish(generation, album_id, identifier, "ready", text, title, _result_names(result))
            published_useful = True
            return True

        def resolve_album_fallback():
            mb_album = resolve_musicbrainz_album_stage(album_title, album_artist)
            if not self._still_current(generation, album_id):
                return None
            publish_result(mb_album)
            dg_album = resolve_discogs_album_stage(album_title, album_artist, mb_album)
            if not self._still_current(generation, album_id):
                return None
            return combine_source_results(
                make_album_lookup_identifier(album_title, album_artist), dg_album, mb_album
            )

        try:
            if info.get("lookup_mode") == "album":
                final = resolve_album_fallback()
            else:
                dg = resolve_discogs_stage(identifier, album_title, album_artist)
                if not self._still_current(generation, album_id):
                    return
                publish_result(dg)
                parsed = parse_identifier(identifier)
                barcode = parsed.get("value") if parsed.get("kind") == "barcode" else ""
                if not barcode and dg and dg.get("status") == "ok":
                    barcodes = (dg.get("release") or {}).get("barcodes") or []
                    barcode = str(barcodes[0]).strip() if barcodes else ""
                if barcode and self._still_current(generation, album_id):
                    mb = resolve_musicbrainz_stage(barcode, album_title, album_artist)
                    if not self._still_current(generation, album_id):
                        return
                final = combine_source_results(identifier, dg, mb)
                if not useful_display_lines(final) and album_title and album_artist:
                    barcode_final = final
                    fallback = resolve_album_fallback()
                    if fallback:
                        if useful_display_lines(fallback):
                            final = fallback
                        else:
                            merged_errors = {}
                            merged_sources = []
                            for item in (barcode_final, fallback):
                                if not item:
                                    continue
                                merged_errors.update(item.get("source_errors") or {})
                                for source in item.get("sources") or ([item.get("source")] if item.get("source") else []):
                                    if source and source not in merged_sources:
                                        merged_sources.append(source)
                            final = dict(fallback)
                            final["source_errors"] = merged_errors
                            final["sources"] = merged_sources
                            final["status"] = "partial" if merged_errors else "not_found"

            if final:
                _save_cached(album_id, identifier, final)
            if final and useful_display_lines(final):
                publish_result(final)
                return
            if self._still_current(generation, album_id) and not published_useful:
                state = "empty" if final and final.get("status") in {"ok", "not_found"} else "error"
                self._queue_publish(generation, album_id, identifier, state,
                                    "No credits found.", album_title)
        except Exception as exc:
            _log("Resolverfehler: {!r}".format(exc), xbmc.LOGWARNING)
            if self._still_current(generation, album_id) and not published_useful:
                self._queue_publish(generation, album_id, identifier, "error",
                                    "No credits found.", album_title)

    def _load_album(self, album_id):
        hint_title, hint_artist = _current_album_hints()
        info = _album_identifier(album_id)
        if info:
            info = dict(info)
            info["album_title"] = info.get("album_title") or hint_title
            info["album_artist"] = info.get("album_artist") or hint_artist
            parsed = parse_identifier(info.get("identifier"))
            if parsed.get("kind") in {"barcode", "discogs"}:
                info["lookup_mode"] = "identifier"
            else:
                album_key = make_album_lookup_identifier(info.get("album_title"), info.get("album_artist"))
                if not album_key:
                    _publish(album_id, "", "missing_identifier", "No credits found.", info.get("album_title") or "")
                    return
                info["identifier"] = album_key
                info["lookup_mode"] = "album"
        else:
            album_key = make_album_lookup_identifier(hint_title, hint_artist)
            if not album_key:
                _publish(album_id, "", "missing_identifier", "No credits found.", hint_title)
                return
            info = {
                "identifier": album_key,
                "album_title": hint_title,
                "album_artist": hint_artist,
                "example_file": "",
                "lookup_mode": "album",
            }

        identifier = info["identifier"]
        cached = _load_cached(album_id, identifier)
        if cached:
            status = str(cached.get("status") or "")
            lines = useful_display_lines(cached)
            if lines:
                _publish(album_id, identifier, "ready", "\n".join(lines),
                         (cached.get("release") or {}).get("title") or info.get("album_title") or "",
                         _result_names(cached))
                return
            if status == "not_found":
                _publish(album_id, identifier, "empty", "No credits found.", info.get("album_title") or "")
                return
            age = max(0.0, time.time() - float(cached.get("_cached_at") or 0.0))
            if age < ERROR_CACHE_SECONDS:
                _publish(album_id, identifier, "error", "No credits found.", info.get("album_title") or "")
                return

        _publish(album_id, identifier, "loading", "Loading credits …", info.get("album_title") or "")
        with self._lock:
            generation = self._generation
        self._worker = threading.Thread(
            target=self._background_worker,
            args=(generation, album_id, info),
            daemon=True,
            name="ConfluenceCustom-Credits",
        )
        self._worker.start()

    def poll(self):
        self._drain_events()
        song_id, album_id = _current_album_id(self._last_song_id, self._last_album_id)
        self._last_song_id = song_id
        if album_id is None:
            if self._last_album_id is not None:
                with self._lock:
                    self._generation += 1
                    self._last_album_id = None
                clear_properties()
            return
        if album_id == self._last_album_id:
            return
        with self._lock:
            self._generation += 1
            self._last_album_id = int(album_id)
        self._load_album(int(album_id))
