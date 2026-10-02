# -*- coding: utf-8 -*-
from __future__ import absolute_import

import struct

import xbmcvfs


_FONT_CACHE = {}
_WIDTH_CACHE = {}


def _u16(data, offset):
    return struct.unpack_from(">H", data, offset)[0]


def _s16(data, offset):
    return struct.unpack_from(">h", data, offset)[0]


def _u32(data, offset):
    return struct.unpack_from(">I", data, offset)[0]


class TrueTypeMetrics(object):
    """Small dependency-free TrueType width reader for the skin's own fonts.

    The footer wrap must follow the same font metrics as Kodi instead of a
    character-width estimate.  This reader uses the font's cmap/hmtx tables,
    the active OpenType GPOS kern feature and standard liga substitutions.
    It deliberately implements only the tables needed for horizontal advance
    calculation and does not render anything.
    """

    def __init__(self, data):
        self.data = bytes(data)
        self.tables = {}
        self.advances = []
        self.kern_lookups = []
        self.liga_lookups = []

        table_count = _u16(self.data, 4)
        pos = 12
        for _ in range(table_count):
            tag = self.data[pos:pos + 4].decode("latin1")
            offset = _u32(self.data, pos + 8)
            length = _u32(self.data, pos + 12)
            self.tables[tag] = (offset, length)
            pos += 16

        head = self.tables["head"][0]
        self.units_per_em = _u16(self.data, head + 18)

        maxp = self.tables["maxp"][0]
        glyph_count = _u16(self.data, maxp + 4)

        hhea = self.tables["hhea"][0]
        metric_count = _u16(self.data, hhea + 34)
        hmtx = self.tables["hmtx"][0]

        last_advance = 0
        for glyph_id in range(glyph_count):
            if glyph_id < metric_count:
                last_advance = _u16(self.data, hmtx + (glyph_id * 4))
            self.advances.append(last_advance)

        self._parse_cmap()
        if "GPOS" in self.tables:
            self._parse_gpos()
        if "GSUB" in self.tables:
            self._parse_gsub()

    def _parse_cmap(self):
        data = self.data
        base = self.tables["cmap"][0]
        count = _u16(data, base + 2)
        choices = []

        for index in range(count):
            pos = base + 4 + (index * 8)
            platform = _u16(data, pos)
            encoding = _u16(data, pos + 2)
            subtable = base + _u32(data, pos + 4)
            fmt = _u16(data, subtable)

            rank = 0
            if fmt == 12:
                rank = 100
            elif fmt == 4:
                rank = 80
            if platform == 0:
                rank += 10
            elif platform == 3 and encoding in (1, 10):
                rank += 8
            choices.append((rank, subtable, fmt))

        if not choices:
            raise ValueError("Font has no cmap")

        _, subtable, fmt = max(choices)
        self.cmap_format = fmt

        if fmt == 4:
            seg_count = _u16(data, subtable + 6) // 2
            end_offset = subtable + 14
            start_offset = end_offset + (2 * seg_count) + 2
            delta_offset = start_offset + (2 * seg_count)
            range_offset = delta_offset + (2 * seg_count)
            self.cmap4 = []
            for index in range(seg_count):
                end = _u16(data, end_offset + (2 * index))
                start = _u16(data, start_offset + (2 * index))
                delta = _s16(data, delta_offset + (2 * index))
                glyph_range = _u16(data, range_offset + (2 * index))
                self.cmap4.append(
                    (start, end, delta, glyph_range, range_offset + (2 * index))
                )
            return

        if fmt == 12:
            group_count = _u32(data, subtable + 12)
            pos = subtable + 16
            self.cmap12 = []
            for _ in range(group_count):
                start = _u32(data, pos)
                end = _u32(data, pos + 4)
                glyph = _u32(data, pos + 8)
                self.cmap12.append((start, end, glyph))
                pos += 12
            return

        raise ValueError("Unsupported cmap format {}".format(fmt))

    def glyph_id(self, codepoint):
        data = self.data

        if self.cmap_format == 4:
            for start, end, delta, glyph_range, range_pos in self.cmap4:
                if start <= codepoint <= end:
                    if glyph_range == 0:
                        return (codepoint + delta) & 0xFFFF
                    glyph_pos = range_pos + glyph_range + (2 * (codepoint - start))
                    if glyph_pos + 2 > len(data):
                        return 0
                    glyph = _u16(data, glyph_pos)
                    if glyph:
                        glyph = (glyph + delta) & 0xFFFF
                    return glyph
            return 0

        for start, end, glyph in self.cmap12:
            if start <= codepoint <= end:
                return glyph + (codepoint - start)
        return 0

    @staticmethod
    def _coverage(data, base):
        fmt = _u16(data, base)
        if fmt == 1:
            count = _u16(data, base + 2)
            return [_u16(data, base + 4 + (2 * i)) for i in range(count)]

        if fmt == 2:
            count = _u16(data, base + 2)
            pos = base + 4
            entries = []
            for _ in range(count):
                start = _u16(data, pos)
                end = _u16(data, pos + 2)
                first_index = _u16(data, pos + 4)
                pos += 6
                for glyph in range(start, end + 1):
                    entries.append((first_index + glyph - start, glyph))
            return [glyph for _, glyph in sorted(entries)]

        return []

    @staticmethod
    def _classdef(data, base):
        fmt = _u16(data, base)
        result = {}

        if fmt == 1:
            start = _u16(data, base + 2)
            count = _u16(data, base + 4)
            pos = base + 6
            for index in range(count):
                result[start + index] = _u16(data, pos + (2 * index))
            return result

        if fmt == 2:
            count = _u16(data, base + 2)
            pos = base + 4
            for _ in range(count):
                start = _u16(data, pos)
                end = _u16(data, pos + 2)
                class_id = _u16(data, pos + 4)
                pos += 6
                for glyph in range(start, end + 1):
                    result[glyph] = class_id
        return result

    @staticmethod
    def _value_record(data, pos, value_format):
        x_advance = 0
        for bit in range(8):
            mask = 1 << bit
            if value_format & mask:
                value = _s16(data, pos) if bit < 4 else _u16(data, pos)
                if bit == 2:
                    x_advance = value
                pos += 2
        return x_advance, pos

    def _pair_subtable(self, base):
        data = self.data
        fmt = _u16(data, base)
        coverage = self._coverage(data, base + _u16(data, base + 2))
        value_format_1 = _u16(data, base + 4)
        value_format_2 = _u16(data, base + 6)

        if fmt == 1:
            pair_set_count = _u16(data, base + 8)
            pair_offsets = [
                _u16(data, base + 10 + (2 * i)) for i in range(pair_set_count)
            ]
            pairs = {}
            for first, offset in zip(coverage, pair_offsets):
                pos = base + offset
                pair_count = _u16(data, pos)
                pos += 2
                for _ in range(pair_count):
                    second = _u16(data, pos)
                    pos += 2
                    first_adjust, pos = self._value_record(data, pos, value_format_1)
                    second_adjust, pos = self._value_record(data, pos, value_format_2)
                    pairs[(first, second)] = first_adjust + second_adjust
            return ("pairs", pairs)

        if fmt == 2:
            classdef_1 = self._classdef(data, base + _u16(data, base + 8))
            classdef_2 = self._classdef(data, base + _u16(data, base + 10))
            class_1_count = _u16(data, base + 12)
            class_2_count = _u16(data, base + 14)
            pos = base + 16
            matrix = []
            for _ in range(class_1_count):
                row = []
                for _ in range(class_2_count):
                    first_adjust, pos = self._value_record(data, pos, value_format_1)
                    second_adjust, pos = self._value_record(data, pos, value_format_2)
                    row.append(first_adjust + second_adjust)
                matrix.append(row)
            return (
                "classes",
                set(coverage),
                classdef_1,
                classdef_2,
                matrix,
            )

        return None

    def _feature_lookup_indexes(self, table_name, wanted_tag):
        data = self.data
        base = self.tables[table_name][0]
        script_base = base + _u16(data, base + 4)
        feature_base = base + _u16(data, base + 6)

        script_count = _u16(data, script_base)
        scripts = {}
        pos = script_base + 2
        for _ in range(script_count):
            tag = data[pos:pos + 4].decode("ascii")
            scripts[tag] = script_base + _u16(data, pos + 4)
            pos += 6

        script = scripts.get("latn") or scripts.get("DFLT")
        if script is None:
            return []

        default_offset = _u16(data, script)
        if not default_offset:
            return []

        langsys = script + default_offset
        required = _u16(data, langsys + 2)
        feature_count = _u16(data, langsys + 4)
        feature_indexes = [
            _u16(data, langsys + 6 + (2 * i)) for i in range(feature_count)
        ]
        if required != 0xFFFF:
            feature_indexes.append(required)

        record_count = _u16(data, feature_base)
        records = []
        pos = feature_base + 2
        for _ in range(record_count):
            tag = data[pos:pos + 4].decode("ascii")
            records.append((tag, feature_base + _u16(data, pos + 4)))
            pos += 6

        lookup_indexes = []
        for feature_index in feature_indexes:
            if feature_index >= len(records):
                continue
            tag, feature = records[feature_index]
            if tag != wanted_tag:
                continue
            count = _u16(data, feature + 2)
            lookup_indexes.extend(
                _u16(data, feature + 4 + (2 * i)) for i in range(count)
            )

        result = []
        seen = set()
        for index in lookup_indexes:
            if index not in seen:
                result.append(index)
                seen.add(index)
        return result

    def _lookup_offsets(self, table_name):
        data = self.data
        base = self.tables[table_name][0]
        lookup_base = base + _u16(data, base + 8)
        count = _u16(data, lookup_base)
        offsets = [
            _u16(data, lookup_base + 2 + (2 * i)) for i in range(count)
        ]
        return lookup_base, offsets

    def _parse_gpos(self):
        data = self.data
        lookup_indexes = self._feature_lookup_indexes("GPOS", "kern")
        lookup_base, lookup_offsets = self._lookup_offsets("GPOS")

        for lookup_index in lookup_indexes:
            if lookup_index >= len(lookup_offsets):
                continue
            lookup = lookup_base + lookup_offsets[lookup_index]
            lookup_type = _u16(data, lookup)
            subtable_count = _u16(data, lookup + 4)
            if lookup_type != 2:
                continue

            subtables = []
            for index in range(subtable_count):
                subtable = lookup + _u16(data, lookup + 6 + (2 * index))
                parsed = self._pair_subtable(subtable)
                if parsed is not None:
                    subtables.append(parsed)
            if subtables:
                self.kern_lookups.append(subtables)

    def _parse_gsub(self):
        data = self.data
        lookup_indexes = self._feature_lookup_indexes("GSUB", "liga")
        lookup_base, lookup_offsets = self._lookup_offsets("GSUB")

        for lookup_index in lookup_indexes:
            if lookup_index >= len(lookup_offsets):
                continue
            lookup = lookup_base + lookup_offsets[lookup_index]
            lookup_type = _u16(data, lookup)
            subtable_count = _u16(data, lookup + 4)
            if lookup_type != 4:
                continue

            subtables = []
            for index in range(subtable_count):
                subtable = lookup + _u16(data, lookup + 6 + (2 * index))
                if _u16(data, subtable) != 1:
                    continue

                coverage = self._coverage(
                    data, subtable + _u16(data, subtable + 2)
                )
                set_count = _u16(data, subtable + 4)
                ligature_sets = []
                for set_index in range(set_count):
                    ligature_set = (
                        subtable + _u16(data, subtable + 6 + (2 * set_index))
                    )
                    ligature_count = _u16(data, ligature_set)
                    records = []
                    for record_index in range(ligature_count):
                        ligature = (
                            ligature_set
                            + _u16(
                                data,
                                ligature_set + 2 + (2 * record_index),
                            )
                        )
                        ligature_glyph = _u16(data, ligature)
                        component_count = _u16(data, ligature + 2)
                        components = [
                            _u16(data, ligature + 4 + (2 * i))
                            for i in range(component_count - 1)
                        ]
                        records.append((components, ligature_glyph))
                    ligature_sets.append(records)
                subtables.append((coverage, ligature_sets))
            if subtables:
                self.liga_lookups.append(subtables)

    @staticmethod
    def _pair_adjustment(subtable, first, second):
        if subtable[0] == "pairs":
            value = subtable[1].get((first, second))
            return value if value is not None else None

        _, coverage, classdef_1, classdef_2, matrix = subtable
        if first not in coverage:
            return None
        class_1 = classdef_1.get(first, 0)
        class_2 = classdef_2.get(second, 0)
        if class_1 >= len(matrix) or class_2 >= len(matrix[class_1]):
            return None
        return matrix[class_1][class_2]

    def _apply_ligatures(self, glyphs):
        result = list(glyphs)
        for lookup in self.liga_lookups:
            index = 0
            while index < len(result):
                replaced = False
                for coverage, ligature_sets in lookup:
                    try:
                        set_index = coverage.index(result[index])
                    except ValueError:
                        continue
                    if set_index >= len(ligature_sets):
                        continue

                    for components, ligature_glyph in ligature_sets[set_index]:
                        count = len(components)
                        if result[index + 1:index + 1 + count] == components:
                            result[index:index + 1 + count] = [ligature_glyph]
                            replaced = True
                            break
                    if replaced:
                        break
                index += 1
        return result

    def width(self, text, pixel_size):
        glyphs = self._apply_ligatures(
            [self.glyph_id(ord(char)) for char in str(text or "")]
        )
        units = 0
        for glyph in glyphs:
            if 0 <= glyph < len(self.advances):
                units += self.advances[glyph]
            else:
                units += self.advances[0]

        for first, second in zip(glyphs, glyphs[1:]):
            for lookup in self.kern_lookups:
                for subtable in lookup:
                    adjustment = self._pair_adjustment(subtable, first, second)
                    if adjustment is not None:
                        units += adjustment
                        break

        return (float(units) * float(pixel_size)) / float(self.units_per_em)


def _read_font(path):
    handle = None
    try:
        handle = xbmcvfs.File(path)
        data = handle.readBytes(4 * 1024 * 1024)
        if isinstance(data, str):
            data = data.encode("latin1", "ignore")
        return bytes(data or b"")
    finally:
        if handle is not None:
            try:
                handle.close()
            except Exception:
                pass


def _font(filename):
    key = str(filename or "")
    metrics = _FONT_CACHE.get(key)
    if metrics is not None:
        return metrics

    data = _read_font("special://skin/fonts/{}".format(key))
    if not data:
        raise ValueError("Font file could not be read: {}".format(key))

    metrics = TrueTypeMetrics(data)
    if len(_FONT_CACHE) >= 8:
        _FONT_CACHE.clear()
    _FONT_CACHE[key] = metrics
    return metrics


def text_width(text, filename, pixel_size):
    key = (str(filename or ""), int(pixel_size), str(text or ""))
    if key in _WIDTH_CACHE:
        return _WIDTH_CACHE[key]
    width = _font(filename).width(key[2], key[1])
    if len(_WIDTH_CACHE) >= 512:
        _WIDTH_CACHE.clear()
    _WIDTH_CACHE[key] = width
    return width
