"""Osmium preclip command and cache helpers."""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path


PRECLIP_VERSION = "1"
DEFAULT_STRATEGY = "smart"


@dataclass(frozen=True)
class PreclipRequest:
    source_pbf: Path
    cache_dir: Path
    tile_geocode: str
    bbox: tuple[float, float, float, float]
    strategy: str = DEFAULT_STRATEGY

    @property
    def bbox_arg(self):
        left, bottom, right, top = self.bbox
        return f"{left},{bottom},{right},{top}"


def normalize_preclip_mode(value):
    mode = (value or "disabled").strip().lower()
    aliases = {"off": "disabled", "false": "disabled", "0": "disabled"}
    mode = aliases.get(mode, mode)
    if mode not in {"disabled", "auto", "required"}:
        raise ValueError("MAP_PRECLIP_MODE must be disabled, auto, or required")
    return mode


def osmium_available(executable="osmium"):
    return shutil.which(executable) is not None


def source_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_metadata(path):
    path = Path(path)
    stat = path.stat()
    return {
        "source_name": path.name,
        "source_size": stat.st_size,
        "source_mtime_ns": stat.st_mtime_ns,
        "source_sha256": source_sha256(path),
    }


def cache_paths(request: PreclipRequest, metadata=None):
    metadata = metadata or source_metadata(request.source_pbf)
    key_data = {
        "version": PRECLIP_VERSION,
        "source": metadata,
        "tile_geocode": request.tile_geocode,
        "bbox": request.bbox,
        "strategy": request.strategy,
    }
    key = hashlib.sha256(json.dumps(key_data, sort_keys=True).encode("utf-8")).hexdigest()[:24]
    safe_source = "".join(ch if ch.isalnum() or ch in ".-" else "_" for ch in request.source_pbf.name)
    clipped = request.cache_dir / f"{safe_source}.{request.tile_geocode}.{key}.osm.pbf"
    return clipped, clipped.with_suffix(clipped.suffix + ".json")


def expected_cache_metadata(request: PreclipRequest, metadata=None):
    metadata = metadata or source_metadata(request.source_pbf)
    return {
        "format_version": "1",
        "preclip_version": PRECLIP_VERSION,
        "strategy": request.strategy,
        "tile_geocode": request.tile_geocode,
        "bbox": list(request.bbox),
        **metadata,
    }


def cache_valid(request: PreclipRequest):
    metadata = source_metadata(request.source_pbf)
    clipped, meta_path = cache_paths(request, metadata)
    if not clipped.is_file() or not meta_path.is_file():
        return False
    try:
        recorded = json.loads(meta_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return recorded == expected_cache_metadata(request, metadata)


def build_osmium_extract_command(request: PreclipRequest, output_path):
    return [
        "osmium",
        "extract",
        "-b",
        request.bbox_arg,
        "-s",
        request.strategy,
        "-f",
        "pbf",
        "--overwrite",
        "-o",
        str(output_path),
        str(request.source_pbf),
    ]
