#!/usr/bin/env python3
"""Read and update iGPSPORT map_md5_list.cfg files."""

import hashlib
import re
from collections import OrderedDict
from pathlib import Path

from .generate_maps_csv import parse_filename

CFG_ENTRY_PATTERN = re.compile(r"^([^:]+):([0-9a-fA-F]{32})$")


def map_md5(path):
    """Return the MD5 checksum for a map file."""
    digest = hashlib.md5()
    with Path(path).open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_map_md5_cfg(path):
    """Read a map_md5_list.cfg file into headers and ordered entries."""
    headers = OrderedDict()
    entries = OrderedDict()

    for raw_line in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue

        key, separator, value = line.partition(":")
        if not separator:
            continue

        if key.startswith("MAP_"):
            headers[key] = value
            continue

        if CFG_ENTRY_PATTERN.match(line):
            entries[key] = value.lower()

    return headers, entries


def parsed_stem_key(stem):
    """Return the stable tile identity for a cfg stem, if it is parseable."""
    parsed = parse_filename(f"{stem}.map")
    if not parsed:
        return None
    return parsed["country_code"], parsed["product_code"], parsed["geocode"]


def update_map_md5_entries(entries, map_paths):
    """Return cfg entries updated with actual checksums for the given map files."""
    replacements = OrderedDict()
    replacements_by_tile = {}

    for path in sorted(Path(item) for item in map_paths):
        parsed = parse_filename(path.name)
        if not parsed:
            continue

        stem = path.stem
        checksum = map_md5(path)
        replacements[stem] = checksum
        replacements_by_tile[(
            parsed["country_code"],
            parsed["product_code"],
            parsed["geocode"],
        )] = (stem, checksum)

    updated = OrderedDict()
    inserted = set()

    for stem, checksum in entries.items():
        tile_key = parsed_stem_key(stem)
        replacement = replacements_by_tile.get(tile_key)

        if replacement:
            new_stem, new_checksum = replacement
            if new_stem not in inserted:
                updated[new_stem] = new_checksum
                inserted.add(new_stem)
            continue

        if stem in replacements:
            updated[stem] = replacements[stem]
            inserted.add(stem)
        else:
            updated[stem] = checksum

    for stem, checksum in replacements.items():
        if stem not in inserted:
            updated[stem] = checksum

    return updated


def render_map_md5_cfg(headers, entries):
    """Render headers and entries as CRLF cfg text."""
    rendered_headers = OrderedDict(headers)
    rendered_headers["MAP_NUM"] = str(len(entries))
    rendered_headers.setdefault("MAP_VER", "130")

    ordered_header_keys = ["MAP_NUM", "MAP_VER"]
    lines = []
    for key in ordered_header_keys:
        if key in rendered_headers:
            lines.append(f"{key}:{rendered_headers[key]}")

    for key, value in rendered_headers.items():
        if key not in ordered_header_keys:
            lines.append(f"{key}:{value}")

    for stem, checksum in entries.items():
        lines.append(f"{stem}:{checksum}")

    return "\r\n".join(lines) + "\r\n"


def build_updated_map_md5_cfg(cfg_path, map_paths):
    """Read cfg_path and return updated cfg text for map_paths."""
    headers, entries = read_map_md5_cfg(cfg_path)
    updated_entries = update_map_md5_entries(entries, map_paths)
    return render_map_md5_cfg(headers, updated_entries)
