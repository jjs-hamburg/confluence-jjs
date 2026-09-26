# -*- coding: utf-8 -*-
"""Credits resolver embedded in JJS KODI Confluence Custom.

This module deliberately has no database side effects. It resolves one barcode
or Discogs release id into structured, normalized performance credits. The
skin playback runtime persists the result in an album-oriented cache.
"""

from __future__ import annotations

import json
import re
import threading
import time
import unicodedata
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

MB_ROOT = "https://musicbrainz.org/ws/2"
DISCOGS_ROOT = "https://api.discogs.com"
USER_AGENT = "JJS-Confluence-Custom/5.0.127 (credits resolver; personal Kodi library)"

_MB_LOCK = threading.Lock()
_MB_LAST_REQUEST = 0.0
_DG_LOCK = threading.Lock()
_DG_LAST_REQUEST = 0.0


def _text(value):
    return str(value or "").strip()


def _fold(value):
    value = unicodedata.normalize("NFKD", _text(value)).casefold()
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def parse_identifier(value):
    value = _text(value)
    m = re.fullmatch(r"\[\s*[Rr](\d+)\s*\]", value)
    if m:
        return {"kind": "discogs", "value": m.group(1), "raw": value}
    digits = re.sub(r"\D", "", value)
    if 8 <= len(digits) <= 14 and digits == value:
        return {"kind": "barcode", "value": digits, "raw": value}
    return {"kind": "unknown", "value": value, "raw": value}


_EDITION_TITLE_HINTS = (
    "remaster", "remastered", "reissue", "deluxe", "expanded", "anniversary",
    "edition", "ryko", "sacd", "dvd a", "dvd audio", "blu ray", "bluray",
    "atmos", "auro", "5 1", "7 1", "quad", "quadraphonic", "surround",
    "stereo mix", "mono mix", "box set", "boxset",
)


def album_title_variants(value):
    """Conservative edition-independent title variants for artist/title lookup.

    The user's Kodi album names may deliberately carry an edition suffix (for
    example ``Hunky Dory (1990 Ryko Reissue)`` or ``Album - 5.1``).  Credits are
    recording-level data for our UI, so those suffixes must not prevent the
    album-level fallback from finding the underlying release group/master.
    """
    raw = re.sub(r"\s+", " ", _text(value)).strip()
    if not raw:
        return []
    out = [raw]
    current = raw
    for _ in range(3):
        changed = False
        m = re.search(r"\s*[\(\[]([^\(\)\[\]]+)[\)\]]\s*$", current)
        if m:
            tail = _fold(m.group(1))
            if re.search(r"\b(?:19|20)\d{2}\b", tail) or any(hint in tail for hint in _EDITION_TITLE_HINTS):
                current = current[:m.start()].rstrip(" -–—,;")
                if current and current not in out:
                    out.append(current)
                changed = True
        if changed:
            continue
        m = re.search(r"\s*[-–—]\s*([^\n]+)$", current)
        if m:
            tail = _fold(m.group(1))
            if re.fullmatch(r"(?:19|20)\d{2}", tail) or any(hint in tail for hint in _EDITION_TITLE_HINTS):
                current = current[:m.start()].rstrip(" -–—,;")
                if current and current not in out:
                    out.append(current)
                changed = True
        if not changed:
            break
    return out


def make_album_lookup_identifier(album_title, album_artist):
    """Stable cache key for barcode-less album-level lookup."""
    title_variants = album_title_variants(album_title)
    title = _fold(title_variants[-1] if title_variants else album_title)
    artist = _fold(album_artist)
    if not title or not artist:
        return ""
    return "album:%s|%s" % (artist, title)


def _title_match_score(got_title, wanted_title):
    got = _fold(got_title)
    if not got:
        return 0
    best = 0
    for variant in album_title_variants(wanted_title):
        wanted = _fold(variant)
        if not wanted:
            continue
        if got == wanted:
            best = max(best, 1000)
        elif got in wanted or wanted in got:
            best = max(best, 300)
    return best


def _artist_match_score(got_artist, wanted_artist):
    got = _fold(got_artist)
    wanted = _fold(wanted_artist)
    if not got or not wanted:
        return 0
    if got == wanted:
        return 500
    wanted_tokens = set(wanted.split())
    got_tokens = set(got.split())
    overlap = len(wanted_tokens & got_tokens)
    if not overlap:
        return 0
    # If every token of the shorter artist hint occurs, this is a strong match
    # even when MusicBrainz carries additional orchestra/soloist credits.
    shorter = min(len(wanted_tokens), len(got_tokens))
    return 250 if overlap == shorter else 40 * overlap


# Canonical German display names.  The mapping is intentionally conservative:
# we merge only terms that are semantically the same for the collection browser.
_INSTRUMENT_ALIASES = {
    "piano": "Piano",
    "grand piano": "Piano",
    "acoustic piano": "Piano",
    "fortepiano": "Hammerklavier",
    "electric piano": "E-Piano",
    "fender rhodes": "E-Piano",
    "rhodes piano": "E-Piano",
    "keyboards": "Keyboards",
    "keyboard": "Keyboards",
    "synthesizer": "Synthesizer",
    "synthesiser": "Synthesizer",
    "moog": "Synthesizer",
    "guitar": "Gitarre",
    "acoustic guitar": "Akustikgitarre",
    "electric guitar": "E-Gitarre",
    "bass guitar": "E-Bass",
    "electric bass": "E-Bass",
    "double bass": "Kontrabass",
    "upright bass": "Kontrabass",
    "bass": "Bass",
    "drums": "Drums",
    "drum set": "Drums",
    "drum kit": "Drums",
    "percussion": "Percussion",
    "violin": "Violine",
    "viola": "Viola",
    "cello": "Cello",
    "violoncello": "Cello",
    "flute": "Flöte",
    "clarinet": "Klarinette",
    "saxophone": "Saxophon",
    "tenor saxophone": "Tenorsaxophon",
    "alto saxophone": "Altsaxophon",
    "soprano saxophone": "Sopransaxophon",
    "baritone saxophone": "Baritonsaxophon",
    "trumpet": "Trompete",
    "trombone": "Posaune",
    "french horn": "Horn",
    "horn": "Horn",
    "oboe": "Oboe",
    "bassoon": "Fagott",
    "harpsichord": "Cembalo",
    "organ": "Orgel",
    "harmonica": "Mundharmonika",
    "vibraphone": "Vibraphon",
    "marimba": "Marimba",
}

_FUNCTION_ALIASES = {
    "conductor": "Dirigent",
    "chorus master": "Chorleitung",
    "choir director": "Chorleitung",
    "concertmaster": "Konzertmeister",
    "orchestra": "Orchester",
    "choir": "Chor",
    "chorus": "Chor",
    "vocals": "Gesang",
    "vocal": "Gesang",
    "lead vocals": "Gesang",
    "backing vocals": "Backgroundgesang",
    "background vocals": "Backgroundgesang",
    "voice": "Gesang",
    "spoken word": "Sprechstimme",
    "narrator": "Sprecher",
    "soprano": "Sopran",
    "soprano vocals": "Sopran",
    "mezzo soprano": "Mezzosopran",
    "mezzo soprano vocals": "Mezzosopran",
    "alto": "Alt",
    "alto vocals": "Alt",
    "contralto": "Alt",
    "contralto vocals": "Alt",
    "tenor": "Tenor",
    "tenor vocals": "Tenor",
    "baritone": "Bariton",
    "baritone vocals": "Bariton",
    "bass vocals": "Bass",
    "bass baritone": "Bassbariton",
    "bass baritone vocals": "Bassbariton",
    "countertenor": "Countertenor",
    "countertenor vocals": "Countertenor",
}

_IGNORE_REL_TYPES = {
    "producer", "executive producer", "engineer", "recording engineer",
    "balance engineer", "mix", "mixing", "mastering", "mastered at",
    "photography", "design", "art direction", "illustration", "liner notes",
    "phonographic copyright", "copyright", "publisher", "manufactured by",
    "distributed by", "record label", "label", "composer", "lyricist",
    "librettist", "writer", "arranger", "orchestrator",
}


def normalize_instrument(value):
    raw = _text(value)
    if not raw:
        return ""

    # Discogs frequently returns redundant spellings such as
    # "Drums (Drum Set)".  Treat a parenthetical term as an alias hint, not as
    # a second instrument.  This also catches e.g. "Piano (Grand Piano)".
    m = re.fullmatch(r"\s*(.*?)\s*\(([^()]*)\)\s*", raw)
    candidates = [raw]
    if m:
        outer = _text(m.group(1))
        inner = _text(m.group(2))
        if outer:
            candidates.insert(0, outer)
        if inner:
            candidates.append(inner)

    for candidate in candidates:
        folded = _fold(candidate)
        if folded in _INSTRUMENT_ALIASES:
            return _INSTRUMENT_ALIASES[folded]
        # Strip common qualifiers which should not split collection-level facets.
        folded2 = re.sub(r"\b(additional|guest|solo)\b", "", folded)
        folded2 = re.sub(r"\s+", " ", folded2).strip()
        if folded2 in _INSTRUMENT_ALIASES:
            return _INSTRUMENT_ALIASES[folded2]

    # If the parenthesis itself is just another spelling of the outer term,
    # keep only the concise outer wording instead of exposing source clutter.
    if m and _text(m.group(1)):
        return _text(m.group(1))[:1].upper() + _text(m.group(1))[1:]
    return raw[:1].upper() + raw[1:]


def normalize_function(value):
    raw = _text(value)
    folded = _fold(raw)
    return _FUNCTION_ALIASES.get(folded, raw[:1].upper() + raw[1:] if raw else "")


def normalize_role(value):
    """Normalize an operatic/stage role without destroying the source value."""
    raw = _text(value)
    if not raw:
        return ""
    # Remove voice-type / generic performer additions but preserve role wording.
    cleaned = re.sub(
        r"\s*[\(\[]\s*(?:soprano|mezzo(?:-soprano)?|alto|contralto|tenor|baritone|bass(?:-baritone)?|"
        r"countertenor|vocals?|voice)\s*[\)\]]\s*$",
        "", raw, flags=re.I,
    ).strip()
    cleaned = re.sub(
        r"\s*[-–—,:]\s*(?:soprano|mezzo(?:-soprano)?|alto|contralto|tenor|baritone|bass(?:-baritone)?|"
        r"countertenor|vocals?|voice)\s*$",
        "", cleaned, flags=re.I,
    ).strip()
    # Cosmetic normalization only; role identity remains text based until we
    # later have stable external work/character identifiers.
    return re.sub(r"\s+", " ", cleaned)


_ROLE_ALIASES = {
    # Work/character aliases we have explicitly verified.  The raw source name
    # is kept separately by the persistence layer.
    "floria tosca": "Tosca",
}


def canonical_role(value, work_title=""):
    role = normalize_role(value)
    if not role:
        return ""
    folded = _fold(role)
    if folded in _ROLE_ALIASES:
        return _ROLE_ALIASES[folded]
    return role


def canonical_person_name(value):
    """Human display name without Discogs' numeric disambiguator suffix."""
    text = re.sub(r"\s*\(\d+\)\s*$", "", _text(value)).strip()
    return text


def canonical_person_key(value):
    """Stable local person key tolerant of Discogs disambiguator suffixes."""
    return _fold(canonical_person_name(value))


def _http_json(url, timeout=20):
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urlopen(req, timeout=timeout) as response:
            payload = response.read()
            return json.loads(payload.decode("utf-8", "replace"))
    except HTTPError as exc:
        body = ""
        try:
            body = exc.read(512).decode("utf-8", "replace")
        except Exception:
            pass
        raise RuntimeError("HTTP %s: %s" % (exc.code, body or exc.reason))
    except URLError as exc:
        raise RuntimeError("Netzwerk: %s" % exc.reason)


def _mb_json(path, params=None):
    global _MB_LAST_REQUEST
    params = dict(params or {})
    params["fmt"] = "json"
    url = MB_ROOT + path + "?" + urlencode(params, doseq=True)
    # MusicBrainz explicitly requests max. one web-service call per second.
    # 503/429 are transient in practice, so retry slowly instead of failing the
    # complete album.  The lock spans wait + request so parallel users of this
    # module can never exceed the service cadence.
    last_exc = None
    for attempt, backoff in enumerate((0.0, 2.0, 5.0, 10.0)):
        if backoff:
            time.sleep(backoff)
        with _MB_LOCK:
            delay = 1.10 - (time.monotonic() - _MB_LAST_REQUEST)
            if delay > 0:
                time.sleep(delay)
            try:
                data = _http_json(url)
                _MB_LAST_REQUEST = time.monotonic()
                return data
            except RuntimeError as exc:
                _MB_LAST_REQUEST = time.monotonic()
                last_exc = exc
                text = str(exc)
                if not ("HTTP 503" in text or "HTTP 429" in text):
                    raise
    raise last_exc or RuntimeError("MusicBrainz antwortet nicht.")


def _discogs_json(path, params=None):
    global _DG_LAST_REQUEST
    url = DISCOGS_ROOT + path
    if params:
        url += "?" + urlencode(dict(params), doseq=True)
    # Deliberately conservative even before a private token is configured.
    with _DG_LOCK:
        delay = 1.0 - (time.monotonic() - _DG_LAST_REQUEST)
        if delay > 0:
            time.sleep(delay)
        try:
            return _http_json(url)
        finally:
            _DG_LAST_REQUEST = time.monotonic()


def _artist_credit_text(value):
    parts = []
    for credit in value or []:
        if isinstance(credit, str):
            parts.append(credit)
            continue
        if not isinstance(credit, dict):
            continue
        artist = credit.get("artist") or {}
        name = credit.get("name") or artist.get("name") or ""
        if name:
            parts.append(_text(name))
        join = credit.get("joinphrase") or ""
        if join:
            parts.append(_text(join))
    return "".join(parts).strip()


def _candidate_score(rel, album_title="", album_artist=""):
    score = int(rel.get("score") or 0)
    title = _fold(rel.get("title"))
    artist = _fold(_artist_credit_text(rel.get("artist-credit")))
    wanted_title = _fold(album_title)
    wanted_artist = _fold(album_artist)
    if wanted_title:
        if title == wanted_title:
            score += 1000
        elif wanted_title in title or title in wanted_title:
            score += 300
    if wanted_artist:
        if artist == wanted_artist:
            score += 500
        else:
            wanted_tokens = set(wanted_artist.split())
            artist_tokens = set(artist.split())
            score += 40 * len(wanted_tokens & artist_tokens)
    if _fold(rel.get("status")) == "official":
        score += 20
    if _fold(rel.get("quality")) == "high":
        score += 10
    return score


def _find_mb_release(barcode, album_title="", album_artist=""):
    result = _mb_json("/release/", {"query": "barcode:%s" % barcode, "limit": 25})
    releases = result.get("releases") or []
    if not releases:
        return None, []
    releases = sorted(
        releases,
        key=lambda r: (_candidate_score(r, album_title, album_artist), int(r.get("score") or 0)),
        reverse=True,
    )
    return releases[0], releases


def _relation_artist(rel):
    artist = rel.get("artist") or {}
    return {
        "id": _text(artist.get("id")),
        "name": _text(artist.get("name")),
        "sort_name": _text(artist.get("sort-name")),
        "type": _text(artist.get("type")),
    }


def _relation_place(rel):
    place = rel.get("place") or {}
    return {"id": _text(place.get("id")), "name": _text(place.get("name"))}


def _mb_date_from_relation(rel):
    begin = _text(rel.get("begin"))
    end = _text(rel.get("end"))
    if begin and end and end != begin:
        return begin + "–" + end
    return begin or end


def _add_credit(store, kind, person, value, raw_value="", role="", role_raw="", source="musicbrainz", tracks=None):
    name = _text(person.get("name"))
    if not name:
        return
    key = (
        kind,
        _text(person.get("id")) or _fold(name),
        _fold(value),
        _fold(role),
    )
    item = store.get(key)
    if item is None:
        item = {
            "kind": kind,
            "person": name,
            "person_id": _text(person.get("id")),
            "value": _text(value),
            "raw_value": _text(raw_value) or _text(value),
            "role": _text(role),
            "role_raw": _text(role_raw) or _text(role),
            "source": source,
            "tracks": [],
            "raw_variants": [],
        }
        store[key] = item
    variant = {
        "source": source,
        "person": name,
        "person_id": _text(person.get("id")),
        "raw_value": _text(raw_value) or _text(value),
        "role_raw": _text(role_raw) or _text(role),
    }
    if variant not in item.setdefault("raw_variants", []):
        item["raw_variants"].append(variant)
    for t in tracks or []:
        if t and t not in item["tracks"]:
            item["tracks"].append(t)


def _parse_mb_relations(relations, credits, ensembles, dates, places, track_label=""):
    for rel in relations or []:
        typ_raw = _text(rel.get("type"))
        typ = _fold(typ_raw)
        target_type = _fold(rel.get("target-type"))
        if typ in _IGNORE_REL_TYPES:
            continue

        if typ in {"recorded at", "recorded in"} and target_type == "place":
            place = _relation_place(rel)
            if place.get("name"):
                places.add((place.get("id") or _fold(place["name"]), place["name"]))
            date = _mb_date_from_relation(rel)
            if date:
                dates.add(date)
            continue

        if target_type != "artist":
            continue
        person = _relation_artist(rel)
        if not person.get("name"):
            continue
        # Dates on performer/artist relationships are not necessarily recording
        # dates (they can describe the relationship itself).  Keep the compact
        # recording date deliberately conservative: only structured recorded-at/
        # recorded-in relations above contribute a date.
        attrs = rel.get("attributes") or []
        values = rel.get("attribute-values") or {}
        credits_map = rel.get("attribute-credits") or {}

        if typ == "instrument":
            inst_raw = _text(values.get("instrument"))
            if not inst_raw:
                # Older/leaner JSON may only expose attribute names.
                inst_raw = next((_text(a) for a in attrs if _fold(a) not in {"guest", "solo", "additional"}), "")
            inst_credited = _text(credits_map.get("instrument"))
            inst = normalize_instrument(inst_raw or inst_credited or "Instrument")
            _add_credit(credits, "instrument", person, inst, inst_credited or inst_raw,
                        source="musicbrainz", tracks=[track_label])
            continue

        if typ == "vocal":
            vocal_raw = _text(values.get("vocal")) or next(
                (_text(a) for a in attrs if "vocal" in _fold(a) or _fold(a) in {
                    "soprano", "mezzo soprano", "alto", "contralto", "tenor", "baritone", "bass"
                }), "vocals"
            )
            credited = _text(credits_map.get("vocal"))
            # In classical/opera MusicBrainz commonly uses the credited-as value
            # to retain the stage character, e.g. soprano vocals [Mimì].
            role = normalize_role(credited) if credited and _fold(credited) != _fold(vocal_raw) else ""
            value = normalize_function(vocal_raw if vocal_raw else "vocals")
            _add_credit(credits, "vocal", person, value, vocal_raw, role, credited,
                        source="musicbrainz", tracks=[track_label])
            continue

        if typ in {"conductor", "chorus master", "concertmaster"}:
            _add_credit(credits, "function", person, normalize_function(typ_raw), typ_raw,
                        source="musicbrainz", tracks=[track_label])
            continue

        if typ in {"orchestra", "choir", "chorus"}:
            key = (typ, person.get("id") or _fold(person["name"]))
            ensembles[key] = {
                "kind": normalize_function(typ_raw),
                "name": person["name"],
                "entity_id": person.get("id") or "",
                "source": "musicbrainz",
            }
            continue

        # A bare "performer" relation has no useful role/instrument for the
        # compact UI.  Preserve it only in the raw source response, not as a
        # visible credit.


def _mb_discogs_ids(relations):
    ids = []
    for rel in relations or []:
        url = _text((rel.get("url") or {}).get("resource"))
        m = re.search(r"discogs\.com/(?:[a-z]{2}/)?release/(\d+)", url, re.I)
        if m and m.group(1) not in ids:
            ids.append(m.group(1))
    return ids


def resolve_musicbrainz(barcode, album_title="", album_artist=""):
    candidate, candidates = _find_mb_release(barcode, album_title, album_artist)
    if not candidate:
        return {
            "status": "not_found", "source": "musicbrainz", "identifier": barcode,
            "message": "Kein MusicBrainz-Release mit diesem Barcode gefunden.",
        }
    mbid = candidate.get("id")
    inc = "+".join([
        "artist-credits", "labels", "recordings", "release-groups",
        "recording-level-rels", "artist-rels", "place-rels", "url-rels",
    ])
    release = _mb_json("/release/%s" % quote(mbid), {"inc": inc})

    credits = {}
    ensembles = {}
    dates = set()
    places = set()

    _parse_mb_relations(release.get("relations"), credits, ensembles, dates, places)
    for medium_index, medium in enumerate(release.get("media") or [], 1):
        medium_no = _text(medium.get("position")) or str(medium_index)
        for track in medium.get("tracks") or []:
            track_no = _text(track.get("number") or track.get("position"))
            track_label = "%s:%s" % (medium_no, track_no) if track_no else medium_no
            rec = track.get("recording") or {}
            _parse_mb_relations(rec.get("relations"), credits, ensembles, dates, places, track_label)

    rg = release.get("release-group") or {}
    recording_dates = sorted(dates)
    discogs_ids = _mb_discogs_ids(release.get("relations"))
    return {
        "status": "ok",
        "source": "musicbrainz",
        "identifier": barcode,
        "release": {
            "musicbrainz_id": _text(release.get("id")),
            "title": _text(release.get("title")),
            "artist": _artist_credit_text(release.get("artist-credit")),
            "barcode": _text(release.get("barcode")),
            "release_date": _text(release.get("date")),
            "release_group_id": _text(rg.get("id")),
            "release_group_title": _text(rg.get("title")),
            "candidate_count": len(candidates),
            "discogs_ids": discogs_ids,
        },
        "credits": list(credits.values()),
        "ensembles": list(ensembles.values()),
        "recording_dates": recording_dates,
        "recording_places": [name for _key, name in sorted(places)],
    }



def _mb_query_phrase(value):
    text = _text(value)
    text = re.sub(r'([+\-!(){}\[\]^"~*?:\\/])', r'\\\1', text)
    text = text.replace('&&', r'\&&').replace('||', r'\||')
    return '"%s"' % text


def _mb_release_group_score(group, album_title="", album_artist=""):
    score = int(group.get("score") or 0)
    score += _title_match_score(group.get("title"), album_title)
    score += _artist_match_score(_artist_credit_text(group.get("artist-credit")), album_artist)
    if _fold(group.get("primary-type")) == "album":
        score += 20
    return score


def _find_mb_release_group(album_title, album_artist):
    variants = album_title_variants(album_title)
    if not variants or not _text(album_artist):
        return None, []
    all_groups = []
    seen = set()
    # Prefer an artist-constrained query.  If a library AlbumArtist contains
    # extra orchestra/soloist wording, fall back to title-only and score artist
    # similarity locally rather than rejecting the album outright.
    for title in reversed(variants):
        queries = [
            "releasegroup:%s AND artist:%s" % (_mb_query_phrase(title), _mb_query_phrase(album_artist)),
            "releasegroup:%s" % _mb_query_phrase(title),
        ]
        for query in queries:
            data = _mb_json("/release-group/", {"query": query, "limit": 25})
            groups = list(data.get("release-groups") or [])
            for group in groups:
                gid = _text(group.get("id"))
                if gid and gid not in seen:
                    seen.add(gid)
                    all_groups.append(group)
            if groups and query != queries[-1]:
                break
        if all_groups:
            break
    if not all_groups:
        return None, []
    ordered = sorted(
        all_groups,
        key=lambda g: (_mb_release_group_score(g, album_title, album_artist), int(g.get("score") or 0)),
        reverse=True,
    )
    best = ordered[0]
    # Require at least a meaningful title relation and some artist relation.
    if _title_match_score(best.get("title"), album_title) < 300:
        return None, all_groups
    if _artist_match_score(_artist_credit_text(best.get("artist-credit")), album_artist) <= 0:
        return None, all_groups
    return best, all_groups


def _date_key(value):
    parts = [int(x) for x in re.findall(r"\d+", _text(value))[:3]]
    while len(parts) < 3:
        parts.append(99)
    return tuple(parts) if parts else (9999, 99, 99)


def _find_mb_release_in_group(group_id, album_title="", album_artist=""):
    params = {
        "release-group": group_id,
        "limit": 100,
        "status": "official",
        "inc": "artist-credits+release-groups",
    }
    data = _mb_json("/release/", params)
    releases = list(data.get("releases") or [])
    if not releases:
        params.pop("status", None)
        data = _mb_json("/release/", params)
        releases = list(data.get("releases") or [])
    if not releases:
        return None, []
    releases.sort(
        key=lambda r: (-_candidate_score(r, album_title, album_artist), _date_key(r.get("date")))
    )
    return releases[0], releases


def _mb_discogs_master_ids(relations):
    ids = []
    for rel in relations or []:
        url = _text((rel.get("url") or {}).get("resource"))
        m = re.search(r"discogs\.com/(?:[a-z]{2}/)?master/(\d+)", url, re.I)
        if m and m.group(1) not in ids:
            ids.append(m.group(1))
    return ids


def resolve_musicbrainz_album(album_title, album_artist):
    """Resolve credits by album identity instead of physical release barcode.

    Matching is done at MusicBrainz release-group level.  One official/early
    representative release is then used only as the technical carrier for
    recording relationships; its pressing/edition is not part of our identity.
    """
    group, groups = _find_mb_release_group(album_title, album_artist)
    identifier = make_album_lookup_identifier(album_title, album_artist)
    if not group:
        return {
            "status": "not_found", "source": "musicbrainz", "identifier": identifier,
            "message": "Kein passendes MusicBrainz-Album für Artist/Titel gefunden.",
        }
    group_id = _text(group.get("id"))
    group_detail = _mb_json(
        "/release-group/%s" % quote(group_id),
        {"inc": "artist-credits+releases+url-rels"},
    )
    candidate, releases = _find_mb_release_in_group(group_id, album_title, album_artist)
    if not candidate:
        return {
            "status": "not_found", "source": "musicbrainz", "identifier": identifier,
            "message": "MusicBrainz-Album gefunden, aber kein Release als Credits-Träger.",
        }

    mbid = candidate.get("id")
    inc = "+".join([
        "artist-credits", "labels", "recordings", "release-groups",
        "recording-level-rels", "artist-rels", "place-rels", "url-rels",
    ])
    release = _mb_json("/release/%s" % quote(mbid), {"inc": inc})

    credits = {}
    ensembles = {}
    dates = set()
    places = set()
    _parse_mb_relations(release.get("relations"), credits, ensembles, dates, places)
    for medium_index, medium in enumerate(release.get("media") or [], 1):
        medium_no = _text(medium.get("position")) or str(medium_index)
        for track in medium.get("tracks") or []:
            track_no = _text(track.get("number") or track.get("position"))
            track_label = "%s:%s" % (medium_no, track_no) if track_no else medium_no
            rec = track.get("recording") or {}
            _parse_mb_relations(rec.get("relations"), credits, ensembles, dates, places, track_label)

    rg = release.get("release-group") or {}
    return {
        "status": "ok",
        "source": "musicbrainz",
        "identifier": identifier,
        "release": {
            "musicbrainz_id": _text(release.get("id")),
            "title": _text(group_detail.get("title")) or _text(rg.get("title")) or _text(release.get("title")),
            "artist": _artist_credit_text(group_detail.get("artist-credit")) or _artist_credit_text(release.get("artist-credit")),
            "barcode": "",
            "release_date": _text(group_detail.get("first-release-date")) or _text(release.get("date")),
            "release_group_id": group_id,
            "release_group_title": _text(group_detail.get("title")) or _text(group.get("title")),
            "release_group_candidate_count": len(groups),
            "representative_release_count": len(releases),
            "match_source": "musicbrainz_artist_album",
            "discogs_ids": _mb_discogs_ids(release.get("relations")),
            "discogs_master_ids": _mb_discogs_master_ids(group_detail.get("relations")),
        },
        "credits": list(credits.values()),
        "ensembles": list(ensembles.values()),
        "recording_dates": sorted(dates),
        "recording_places": [name for _key, name in sorted(places)],
    }


_DISC_ROLE_IGNORE = {
    # Production / technical
    "producer", "executive producer", "reissue producer", "engineer",
    "recording engineer", "balance engineer", "mastered by", "remastered by",
    "mixed by", "recorded by", "lacquer cut by", "plated by", "technician",
    "drum technician", "guitar technician", "tape operator",
    # Artwork / packaging / editorial
    "design", "art direction", "artwork", "artwork by", "cover", "cover art",
    "cover design", "photography", "photography by", "photo", "illustration",
    "painting", "layout", "graphics", "typography", "calligraphy",
    "liner notes", "sleeve notes", "booklet editor", "editor",
    # Writing / business / administration
    "written by", "written-by", "composed by", "composer", "lyrics by",
    "lyricist", "libretto by", "arranged by", "orchestrated by",
    "management", "coordinator", "a&r", "research", "supervised by",
    "copyright", "published by", "manufactured by", "distributed by",
    "marketed by", "licensed from", "record company", "artist",
}

# Only Discogs roles that clearly describe a performance are admitted to the
# compact result.  This is intentionally an allow-list by musical vocabulary:
# unknown credits remain in the raw log but no longer turn into nonsense such
# as "Cover — ..." or "Design — ..." instruments.
_MUSICAL_ROLE_HINTS = {
    "piano", "fortepiano", "keyboard", "keyboards", "organ", "hammond",
    "mellotron", "clavinet", "harpsichord", "celesta", "synth", "synthesizer",
    "synthesiser", "moog", "guitar", "mandolin", "banjo", "ukulele", "sitar",
    "bass", "contrabass", "double bass", "upright bass", "drums", "drum",
    "percussion", "timpani", "tabla", "conga", "bongo", "vibraphone",
    "marimba", "xylophone", "violin", "viola", "cello", "violoncello",
    "harp", "flute", "piccolo", "clarinet", "saxophone", "sax", "oboe",
    "bassoon", "trumpet", "trombone", "horn", "cornet", "tuba", "recorder",
    "harmonica", "accordion", "bandoneon", "electronics", "electronic",
    "strings", "brass", "woodwind", "woodwinds", "glockenspiel", "dulcimer",
}


def _split_discogs_roles(value):
    # Commas outside [...] separate role fragments.
    out, buf, depth = [], [], 0
    for ch in _text(value):
        if ch == "[":
            depth += 1
        elif ch == "]" and depth:
            depth -= 1
        if ch == "," and depth == 0:
            part = "".join(buf).strip()
            if part:
                out.append(part)
            buf = []
        else:
            buf.append(ch)
    part = "".join(buf).strip()
    if part:
        out.append(part)
    return out


def _discogs_role_is_ignored(folded):
    if not folded:
        return True
    for ignored in _DISC_ROLE_IGNORE:
        if folded == ignored or folded.startswith(ignored + " "):
            return True
    # Common non-musical suffix/prefix variants not worth enumerating.
    if any(word in folded for word in (
        "artwork", "photograph", "design", "mastering", "mastered",
        "engineering", "engineered", "producer", "production", "copyright",
        "management", "coordinator", "typography", "illustration", "liner notes",
    )):
        return True
    return False


def _looks_like_instrument_role(folded):
    tokens = set(folded.split())
    for hint in _MUSICAL_ROLE_HINTS:
        if " " in hint:
            if hint in folded:
                return True
        elif hint in tokens:
            return True
    return False


def _parse_discogs_role(role):
    raw = _text(role)
    bracket = ""
    m = re.search(r"\[([^\]]+)\]\s*$", raw)
    if m:
        bracket = _text(m.group(1))
        raw_base = raw[:m.start()].strip()
    else:
        raw_base = raw
    folded = _fold(raw_base)
    if _discogs_role_is_ignored(folded):
        return None

    if "conductor" in folded:
        return ("function", "Dirigent", "")
    if "chorus master" in folded or "choir director" in folded:
        return ("function", "Chorleitung", "")
    if "concertmaster" in folded or "leader" == folded:
        return ("function", "Konzertmeister", "")
    if "orchestra" in folded:
        return ("ensemble", "Orchester", "")
    if "choir" in folded or "chorus" in folded:
        return ("ensemble", "Chor", "")

    # Bare "Bass" in Discogs is overwhelmingly the instrument in rock/jazz;
    # bass voice is retained when the role explicitly says Vocals/Voice.
    voice_types = {"soprano", "mezzo soprano", "alto", "contralto", "tenor",
                   "baritone", "countertenor"}
    if "vocal" in folded or "voice" in folded or folded in voice_types or folded in {"narrator", "spoken word"}:
        # A bracket after a vocal credit is only treated as an operatic/stage
        # character if it is not merely a vocal qualifier such as "Lead".
        qualifier_words = {
            "lead", "backing", "background", "additional", "guest", "solo",
            "harmony", "harmonies", "spoken", "voice", "vocals",
        }
        character = normalize_role(bracket)
        if _fold(character) in qualifier_words:
            character = ""
        if folded == "narrator":
            vocal_value = "Sprecher"
        elif folded == "spoken word":
            vocal_value = "Sprechstimme"
        elif "backing" in folded or "background" in folded:
            vocal_value = "Backgroundgesang"
        else:
            # Keep a real voice type (Tenor/Sopran/...) when it is the useful
            # credit itself, e.g. Beethoven 9.  Generic Vocals stays Gesang.
            vocal_value = normalize_function(raw_base)
            if _fold(vocal_value) == _fold(raw_base) and folded in {"vocals", "vocal", "voice"}:
                vocal_value = "Gesang"
        return ("vocal", vocal_value, character)

    if _looks_like_instrument_role(folded):
        return ("instrument", normalize_instrument(raw_base), "")

    # Unknown Discogs credits are deliberately not guessed as instruments.
    return None


def _discogs_result_artist_title(item):
    title = _text(item.get("title"))
    if " - " in title:
        artist, album = title.split(" - ", 1)
        return artist.strip(), album.strip()
    return "", title


def _discogs_candidate_score(item, album_title="", album_artist=""):
    artist, title = _discogs_result_artist_title(item)
    score = 0
    wanted_title = _fold(album_title)
    wanted_artist = _fold(album_artist)
    got_title = _fold(title)
    got_artist = _fold(artist)
    if wanted_title:
        if got_title == wanted_title:
            score += 1000
        elif wanted_title in got_title or got_title in wanted_title:
            score += 300
    if wanted_artist:
        if got_artist == wanted_artist:
            score += 500
        else:
            score += 40 * len(set(wanted_artist.split()) & set(got_artist.split()))
    # Discogs returns relevance order; retain a small stable preference for the
    # earlier result when our local Kodi hint cannot distinguish releases.
    return score


def _find_discogs_release(barcode, album_title="", album_artist=""):
    data = _discogs_json("/database/search", {
        "barcode": barcode, "type": "release", "per_page": 25, "page": 1,
    })
    rows = list(data.get("results") or [])
    if not rows:
        return None, []
    indexed = list(enumerate(rows))
    indexed.sort(
        key=lambda pair: (_discogs_candidate_score(pair[1], album_title, album_artist), -pair[0]),
        reverse=True,
    )
    return indexed[0][1], rows


def _discogs_barcodes(data):
    out = []
    for ident in data.get("identifiers") or []:
        if _fold(ident.get("type")) != "barcode":
            continue
        raw = _text(ident.get("value"))
        digits = re.sub(r"\D", "", raw)
        if 8 <= len(digits) <= 14 and digits not in out:
            out.append(digits)
    return out


def resolve_discogs(release_id):
    data = _discogs_json("/releases/%s" % quote(str(release_id)))
    credits = {}
    ensembles = {}
    for artist in data.get("extraartists") or []:
        person = {"id": str(artist.get("id") or ""), "name": _text(artist.get("name"))}
        tracks = [_text(v) for v in re.split(r"\s*,\s*", _text(artist.get("tracks"))) if _text(v)]
        for role_raw in _split_discogs_roles(artist.get("role")):
            parsed = _parse_discogs_role(role_raw)
            if not parsed:
                continue
            kind, value, character = parsed
            if kind == "ensemble":
                key = (value, person.get("id") or _fold(person.get("name")))
                ensembles[key] = {
                    "kind": value, "name": person.get("name"), "entity_id": person.get("id"),
                    "source": "discogs",
                }
            else:
                _add_credit(credits, kind, person, value, role_raw, character, character,
                            source="discogs", tracks=tracks)

    recording_places = []
    for company in data.get("companies") or []:
        relation = _fold(company.get("entity_type_name"))
        if relation not in {"recorded at", "recorded in"}:
            continue
        name = _text(company.get("name"))
        if name and name not in recording_places:
            recording_places.append(name)

    return {
        "status": "ok",
        "source": "discogs",
        "identifier": str(release_id),
        "release": {
            "discogs_id": str(data.get("id") or release_id),
            "title": _text(data.get("title")),
            "artist": ", ".join(_text(a.get("name")) for a in data.get("artists") or [] if _text(a.get("name"))),
            "release_date": _text(data.get("released")) or _text(data.get("year")),
            "discogs_uri": _text(data.get("uri")),
            "barcodes": _discogs_barcodes(data),
        },
        "credits": list(credits.values()),
        "ensembles": list(ensembles.values()),
        # Discogs release dates are NOT recording dates.  Keep this empty unless
        # a genuine recording date can be derived from structured source data.
        "recording_dates": [],
        "recording_places": recording_places,
    }



def resolve_discogs_master(master_id):
    data = _discogs_json("/masters/%s" % quote(str(master_id)))
    main_release = _text(data.get("main_release"))
    if not main_release:
        return {
            "status": "not_found", "source": "discogs", "identifier": str(master_id),
            "message": "Discogs-Master ohne Hauptrelease.",
        }
    result = resolve_discogs(main_release)
    if result.get("status") == "ok":
        rel = result.setdefault("release", {})
        rel["discogs_master_id"] = str(data.get("id") or master_id)
        rel["master_title"] = _text(data.get("title"))
        rel["match_source"] = "discogs_master"
    return result


def _find_discogs_album_candidate(album_title, album_artist, resource_type):
    rows_all = []
    seen = set()
    for title in reversed(album_title_variants(album_title)):
        data = _discogs_json("/database/search", {
            "artist": album_artist,
            "release_title": title,
            "type": resource_type,
            "per_page": 25,
            "page": 1,
        })
        rows = list(data.get("results") or [])
        for row in rows:
            key = (str(row.get("type") or resource_type), str(row.get("id") or ""))
            if key not in seen:
                seen.add(key)
                rows_all.append(row)
        if rows:
            break
    if not rows_all:
        return None, []
    indexed = list(enumerate(rows_all))
    indexed.sort(
        key=lambda pair: (_discogs_candidate_score(pair[1], album_title, album_artist), -pair[0]),
        reverse=True,
    )
    best = indexed[0][1]
    artist, title = _discogs_result_artist_title(best)
    if _title_match_score(title, album_title) < 300 or _artist_match_score(artist, album_artist) <= 0:
        return None, rows_all
    return best, rows_all


def resolve_discogs_album(album_title, album_artist, master_ids=None, release_ids=None):
    """Resolve Discogs at album/master level; pressing identity is irrelevant."""
    identifier = make_album_lookup_identifier(album_title, album_artist)
    # MusicBrainz often provides direct Discogs relationships.  They avoid the
    # authenticated Discogs search endpoint and are therefore the preferred bridge.
    for master_id in master_ids or []:
        result = resolve_discogs_master(master_id)
        if result.get("status") == "ok":
            result["identifier"] = identifier
            return result
    for release_id in release_ids or []:
        result = resolve_discogs(release_id)
        if result.get("status") == "ok":
            result["identifier"] = identifier
            result.setdefault("release", {})["match_source"] = "musicbrainz_discogs_release_link"
            return result

    candidate, candidates = _find_discogs_album_candidate(album_title, album_artist, "master")
    if candidate:
        result = resolve_discogs_master(candidate.get("id"))
        if result.get("status") == "ok":
            result["identifier"] = identifier
            result.setdefault("release", {})["discogs_candidate_count"] = len(candidates)
            return result

    candidate, candidates = _find_discogs_album_candidate(album_title, album_artist, "release")
    if candidate:
        result = resolve_discogs(candidate.get("id"))
        if result.get("status") == "ok":
            result["identifier"] = identifier
            rel = result.setdefault("release", {})
            rel["discogs_candidate_count"] = len(candidates)
            rel["match_source"] = "discogs_artist_album_release"
            return result
    return {
        "status": "not_found", "source": "discogs", "identifier": identifier,
        "message": "Kein passendes Discogs-Album für Artist/Titel gefunden.",
    }


def merge_results(primary, secondary):
    if not secondary or secondary.get("status") != "ok":
        return primary
    if not primary or primary.get("status") != "ok":
        return secondary
    out = dict(primary)
    merged = {}
    release_title = _text((primary.get("release") or {}).get("title")) or _text((secondary.get("release") or {}).get("title"))
    for item in (primary.get("credits") or []) + (secondary.get("credits") or []):
        kind = _text(item.get("kind"))
        value = _text(item.get("value"))
        if kind == "instrument":
            value = normalize_instrument(value)
        elif kind in {"vocal", "function"}:
            value = normalize_function(value)
        key = (
            kind,
            canonical_person_key(item.get("person")),
            _fold(value),
            _fold(canonical_role(item.get("role"), release_title)),
        )
        old = merged.get(key)
        if old is None:
            merged[key] = dict(item)
        else:
            old_tracks = old.setdefault("tracks", [])
            for t in item.get("tracks") or []:
                if t not in old_tracks:
                    old_tracks.append(t)
            for variant in item.get("raw_variants") or []:
                if variant not in old.setdefault("raw_variants", []):
                    old["raw_variants"].append(variant)
            if old.get("source") != item.get("source"):
                old["source"] = "+".join(sorted(set((old.get("source") or "").split("+") + [item.get("source") or ""]))).strip("+")
    ensembles = {}
    for item in (primary.get("ensembles") or []) + (secondary.get("ensembles") or []):
        key = (_fold(item.get("kind")), _fold(item.get("name")))
        ensembles.setdefault(key, dict(item))
    out["credits"] = list(merged.values())
    out["ensembles"] = list(ensembles.values())
    out["sources"] = sorted(set([primary.get("source"), secondary.get("source")]) - {None, ""})
    out["recording_dates"] = sorted(set((primary.get("recording_dates") or []) + (secondary.get("recording_dates") or [])))
    out["recording_places"] = sorted(set((primary.get("recording_places") or []) + (secondary.get("recording_places") or [])))
    return out


def _source_error_message(source, exc):
    text = str(exc)
    if source == "discogs" and "HTTP 401" in text:
        return "Discogs-Datenbanksuche verlangt derzeit Authentifizierung/API-Token (HTTP 401)."
    if source == "musicbrainz" and ("HTTP 503" in text or "HTTP 429" in text):
        return "MusicBrainz ist trotz Wiederholungen vorübergehend ausgelastet."
    return text


def _finalize_sources(result, source_errors=None):
    if not isinstance(result, dict):
        result = {}
    sources = result.get("sources") or ([result.get("source")] if result.get("source") else [])
    result["sources"] = [x for x in sources if x]
    result["source_errors"] = dict(source_errors or {})
    return result


_NO_COMPACT_DATA_PREFIX = "Keine für die kompakte Anzeige geeigneten Besetzungsdaten gefunden."


def useful_display_text(value):
    """Return True only for cache text that contains real compact credits data."""
    text = _text(value)
    if not text:
        return False
    if text.startswith(_NO_COMPACT_DATA_PREFIX):
        return False
    if text == "Keine Besetzungsdaten gefunden.":
        return False
    return True


def useful_display_lines(result):
    """Return compact display lines only when they contain useful credits data."""
    if not result or result.get("status") != "ok":
        return []
    lines = [str(line or "").strip() for line in display_lines(result)]
    lines = [line for line in lines if line]
    if len(lines) == 1 and lines[0].startswith(_NO_COMPACT_DATA_PREFIX):
        return []
    return lines


def _result_sources(result):
    if not result:
        return []
    return [x for x in (result.get("sources") or ([result.get("source")] if result.get("source") else [])) if x]


def combine_source_results(identifier, discogs_result=None, musicbrainz_result=None):
    """Combine staged resolver results and assign a cache-safe terminal status.

    A provider returning ``status=ok`` merely means that a release response was
    parsed successfully.  It is only a successful credits result when the compact
    popup has useful lines.  If no useful lines exist and any provider failed, the
    result is ``partial`` so a later album start can retry.  ``not_found`` is used
    only when all providers that were actually queried completed without errors.
    """
    dg = discogs_result
    mb = musicbrainz_result
    errors = {}
    for result in (dg, mb):
        if result:
            errors.update(result.get("source_errors") or {})

    dg_ok = bool(dg and dg.get("status") == "ok")
    mb_ok = bool(mb and mb.get("status") == "ok")
    if dg_ok and mb_ok:
        out = merge_results(dg, mb)
        if dg.get("release"):
            out.setdefault("release", {})["match_source"] = (dg.get("release") or {}).get("match_source") or "discogs_release_id"
    elif dg_ok:
        out = dict(dg)
    elif mb_ok:
        out = dict(mb)
    else:
        # Prefer a real provider result over a synthetic fallback so diagnostics
        # and release-identification details are retained in the raw import.
        out = dict(dg or mb or {
            "status": "not_found", "identifier": identifier,
            "message": "Keine Besetzungsdaten gefunden.",
        })

    sources = []
    for result in (dg, mb):
        for source in _result_sources(result):
            if source not in sources:
                sources.append(source)
    out["sources"] = sources or _result_sources(out)
    out["source_errors"] = errors

    if out.get("status") == "ok" and useful_display_lines(out):
        return out

    # A clean release hit without useful credits is not a successful credits hit.
    out["status"] = "partial" if errors else "not_found"
    out["message"] = "Keine Besetzungsdaten gefunden."
    return out


def resolve_discogs_stage(identifier, album_title="", album_artist=""):
    """Resolve only the Discogs half of an identifier.

    Used by the playback runtime so a stable Discogs result can be published
    immediately while slower MusicBrainz enrichment continues afterwards.
    The interactive resolver still uses :func:`resolve` and therefore retains
    the combined two-source behaviour.
    """
    parsed = parse_identifier(identifier)
    if parsed["kind"] not in {"discogs", "barcode"}:
        return _finalize_sources({
            "status": "invalid", "identifier": identifier,
            "message": "Unbekanntes Identifier-Format.",
        })
    try:
        if parsed["kind"] == "discogs":
            result = resolve_discogs(parsed["value"])
            if result.get("status") == "ok":
                result.setdefault("release", {})["match_source"] = "discogs_release_id"
            return _finalize_sources(result)

        barcode = parsed["value"]
        candidate, candidates = _find_discogs_release(barcode, album_title, album_artist)
        if not candidate:
            return _finalize_sources({
                "status": "not_found", "source": "discogs", "identifier": barcode,
                "message": "Kein Discogs-Release mit diesem Barcode gefunden.",
            })
        result = resolve_discogs(candidate.get("id"))
        if result.get("status") == "ok":
            rel = result.setdefault("release", {})
            rel["discogs_candidate_count"] = len(candidates)
            rel["match_source"] = "discogs_barcode"
        return _finalize_sources(result)
    except Exception as exc:
        return _finalize_sources({
            "status": "error", "source": "discogs", "identifier": parsed.get("value") or identifier,
            "message": "Keine Discogs-Daten gefunden.",
        }, {"discogs": _source_error_message("discogs", exc)})


def resolve_musicbrainz_stage(barcode, album_title="", album_artist=""):
    """Resolve only MusicBrainz for a known barcode, returning errors as data."""
    barcode = _text(barcode)
    if not barcode:
        return _finalize_sources({
            "status": "not_found", "source": "musicbrainz", "identifier": "",
            "message": "Kein Barcode für MusicBrainz vorhanden.",
        })
    try:
        return _finalize_sources(resolve_musicbrainz(barcode, album_title, album_artist))
    except Exception as exc:
        return _finalize_sources({
            "status": "error", "source": "musicbrainz", "identifier": barcode,
            "message": "Keine MusicBrainz-Daten gefunden.",
        }, {"musicbrainz": _source_error_message("musicbrainz", exc)})



def resolve_musicbrainz_album_stage(album_title, album_artist):
    """Album-level MusicBrainz fallback; provider failures are returned as data."""
    identifier = make_album_lookup_identifier(album_title, album_artist)
    if not identifier:
        return _finalize_sources({
            "status": "invalid", "source": "musicbrainz", "identifier": "",
            "message": "Artist und Albumtitel werden für den Fallback benötigt.",
        })
    try:
        return _finalize_sources(resolve_musicbrainz_album(album_title, album_artist))
    except Exception as exc:
        return _finalize_sources({
            "status": "error", "source": "musicbrainz", "identifier": identifier,
            "message": "Keine MusicBrainz-Daten gefunden.",
        }, {"musicbrainz": _source_error_message("musicbrainz", exc)})


def resolve_discogs_album_stage(album_title, album_artist, musicbrainz_result=None):
    """Album-level Discogs fallback, preferably bridged from MusicBrainz IDs."""
    identifier = make_album_lookup_identifier(album_title, album_artist)
    if not identifier:
        return _finalize_sources({
            "status": "invalid", "source": "discogs", "identifier": "",
            "message": "Artist und Albumtitel werden für den Fallback benötigt.",
        })
    release = (musicbrainz_result or {}).get("release") or {}
    try:
        return _finalize_sources(resolve_discogs_album(
            album_title,
            album_artist,
            master_ids=release.get("discogs_master_ids") or [],
            release_ids=release.get("discogs_ids") or [],
        ))
    except Exception as exc:
        return _finalize_sources({
            "status": "error", "source": "discogs", "identifier": identifier,
            "message": "Keine Discogs-Daten gefunden.",
        }, {"discogs": _source_error_message("discogs", exc)})


def resolve_album(album_title, album_artist, use_discogs=True):
    """Resolve barcode-less credits by artist + edition-independent album title."""
    identifier = make_album_lookup_identifier(album_title, album_artist)
    mb = resolve_musicbrainz_album_stage(album_title, album_artist)
    dg = resolve_discogs_album_stage(album_title, album_artist, mb) if use_discogs else None
    return combine_source_results(identifier, dg, mb)


def resolve(identifier, album_title="", album_artist="", use_discogs=True):
    """Resolve one identifier with the same staged combination logic as playback."""
    parsed = parse_identifier(identifier)
    if parsed["kind"] not in {"discogs", "barcode"}:
        return _finalize_sources({
            "status": "invalid", "identifier": identifier,
            "message": "Unbekanntes Identifier-Format.",
        })

    dg = resolve_discogs_stage(identifier, album_title, album_artist) if use_discogs else None
    barcode = parsed["value"] if parsed["kind"] == "barcode" else ""

    # A direct Discogs release may expose the physical barcode required for the
    # independent MusicBrainz enrichment stage.
    if not barcode and dg and dg.get("status") == "ok":
        barcodes = (dg.get("release") or {}).get("barcodes") or []
        if barcodes:
            barcode = _text(barcodes[0])

    mb = resolve_musicbrainz_stage(barcode, album_title, album_artist) if barcode else None
    return combine_source_results(identifier, dg, mb)


def _sort_credit(item):
    order = {"vocal": 0, "instrument": 1, "function": 2}
    return (order.get(item.get("kind"), 9), _fold(item.get("role")), _fold(item.get("person")), _fold(item.get("value")))


def _role_sort_key(item, release_title, original_index):
    # Deliberately simple and deterministic: every role alphabetically by its
    # canonical name.  No guessed title-role or importance weighting.
    role = canonical_role(item.get("role"), release_title)
    return (_fold(role), canonical_person_key(item.get("person")), original_index)


def source_status_lines(result):
    sources = result.get("sources") or ([result.get("source")] if result.get("source") else [])
    names = {"discogs": "Discogs", "musicbrainz": "MusicBrainz"}
    lines = []
    if sources:
        lines.append("Quellen — %s" % " + ".join(names.get(s, s) for s in sources if s))
    for source, message in (result.get("source_errors") or {}).items():
        lines.append("%s — %s" % (names.get(source, source), message))
    return lines


def _credit_track_count(item):
    return len(set(_text(t) for t in (item.get("tracks") or []) if _text(t)))


def _recording_lines(result):
    dates = [_text(x) for x in (result.get("recording_dates") or []) if _text(x)]
    places = [_text(x) for x in (result.get("recording_places") or []) if _text(x)]
    # Preserve order while removing duplicates.  Date and place are deliberately
    # separate popup lines and each is omitted completely when unavailable.
    dates = list(dict.fromkeys(dates))
    places = list(dict.fromkeys(places))
    lines = []
    if dates:
        value = dates[0] if len(dates) == 1 else "%s … %s" % (dates[0], dates[-1])
        lines.append("Aufnahmedatum — %s" % value)
    if places:
        lines.append("Aufnahmeort — %s" % ", ".join(places))
    return lines


def _is_pure_vocal_value(value):
    """True for voice-type/generic vocal credits that duplicate an opera role."""
    folded = _fold(value)
    if not folded:
        return False
    if any(token in folded for token in ("vocal", "voice")):
        return True
    return folded in {
        "gesang", "sopran", "soprano", "mezzo sopran", "mezzo soprano",
        "mezzosopran", "alt", "alto", "contralto", "tenor",
        "bariton", "baritone", "bass", "bass bariton", "bass baritone",
        "bassbariton", "countertenor", "backgroundgesang",
    }

def display_lines(result):
    """Return only information suitable for the later compact skin popup.

    Source diagnostics, release metadata, artwork, production and other raw
    credits deliberately stay out of this list; credits_test.log retains the
    complete resolver result for diagnosis.
    """
    if result.get("status") != "ok":
        return [result.get("message") or "Keine Besetzungsdaten gefunden."]

    credits = list(result.get("credits") or [])
    ensembles = list(result.get("ensembles") or [])
    release_title = _text((result.get("release") or {}).get("title"))

    lines = []
    seen = set()

    # Opera/stage roles: always alphabetically by canonical role name.
    role_credits = [(idx, c) for idx, c in enumerate(credits) if c.get("role")]
    role_credits.sort(key=lambda pair: _role_sort_key(pair[1], release_title, pair[0]))
    role_people = set()
    for _idx, c in role_credits:
        role = canonical_role(c.get("role"), release_title)
        person = canonical_person_name(c.get("person"))
        if not role or not person:
            continue
        role_people.add(canonical_person_key(person))
        line = "%s — %s" % (role, person)
        key = _fold(line)
        if key not in seen:
            seen.add(key)
            lines.append(line)

    # Non-role performers: merge instruments/functions per person.  A pure
    # voice-type credit is suppressed only when that same person is already
    # shown with a concrete stage role.  Thus "Siegmund — Jon Vickers" does
    # not get a second "Jon Vickers — Tenor" line, while a tenor soloist in
    # Beethoven's Ninth remains visible.
    by_person = {}
    person_order = []
    conductor = []
    chorus_leaders = []
    for idx, c in enumerate(credits):
        if c.get("role"):
            continue
        person = canonical_person_name(c.get("person"))
        value = _text(c.get("value"))
        if c.get("kind") == "instrument":
            value = normalize_instrument(value)
        elif c.get("kind") == "vocal":
            value = normalize_function(value)
        if not person or not value:
            continue
        value_fold = _fold(value)
        if value_fold == "dirigent":
            conductor.append((idx, c))
            continue
        if value_fold in {"chorleitung", "chorleiter", "chorus master", "choir director"}:
            chorus_leaders.append((idx, c))
            continue
        if value_fold in {"mitwirkende", "performer", "artist"}:
            continue
        if canonical_person_key(person) in role_people and _is_pure_vocal_value(value):
            continue
        if person not in by_person:
            by_person[person] = {"values": [], "tracks": set(), "index": idx}
            person_order.append(person)
        if value not in by_person[person]["values"]:
            by_person[person]["values"].append(value)
        by_person[person]["tracks"].update(_text(t) for t in (c.get("tracks") or []) if _text(t))

    person_order.sort(key=lambda p: (-len(by_person[p]["tracks"]), by_person[p]["index"]))
    for person in person_order:
        values = by_person[person]["values"]
        if not values:
            continue
        line = "%s — %s" % (person, ", ".join(values))
        key = _fold(line)
        if key not in seen:
            seen.add(key)
            lines.append(line)

    # Ensemble order for the popup is intentional: choir first, then chorus
    # leader, then orchestra/other ensembles.  This is independent of source
    # order so Discogs/MusicBrainz cannot reshuffle the visible layout.
    choir_ensembles = []
    other_ensembles = []
    for e in ensembles:
        kind_fold = _fold(e.get("kind"))
        if kind_fold in {"chor", "choir", "chorus"}:
            choir_ensembles.append(e)
        else:
            other_ensembles.append(e)

    for e in choir_ensembles:
        kind = _text(e.get("kind")) or "Chor"
        name = _text(e.get("name"))
        if not name:
            continue
        line = "%s — %s" % (kind, name)
        key = _fold(line)
        if key not in seen:
            seen.add(key)
            lines.append(line)

    for _idx, c in chorus_leaders:
        person = canonical_person_name(c.get("person"))
        if not person:
            continue
        line = "Chorleiter — %s" % person
        key = _fold(line)
        if key not in seen:
            seen.add(key)
            lines.append(line)

    for e in other_ensembles:
        kind = _text(e.get("kind"))
        name = _text(e.get("name"))
        if not name:
            continue
        line = "%s — %s" % (kind, name) if kind else name
        key = _fold(line)
        if key not in seen:
            seen.add(key)
            lines.append(line)

    # Conductor deliberately follows choir/chorus leader/orchestra.
    for _idx, c in conductor:
        person = canonical_person_name(c.get("person"))
        if not person:
            continue
        line = "Dirigent — %s" % person
        key = _fold(line)
        if key not in seen:
            seen.add(key)
            lines.append(line)

    for recording_line in _recording_lines(result):
        key = _fold(recording_line)
        if key not in seen:
            seen.add(key)
            lines.append(recording_line)

    return lines or ["Keine für die kompakte Anzeige geeigneten Besetzungsdaten gefunden."]

