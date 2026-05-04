#!/usr/bin/env python3
"""
List or download official iGPSPORT map files from the public support API.

Examples:
    python download_igpsport_maps.py europe switzerland --list
    python download_igpsport_maps.py europe switzerland --download -o input
    python download_igpsport_maps.py aargau --download -o input/switzerland
"""

import argparse
import json
import os
import re
import sys
import unicodedata
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

DEFAULT_API_BASE_URL = "https://prod.en.igpsport.com/service"
DEFAULT_MAP_VERSION_ID = "1f504832-9c67-11ef-a0af-000c29d603cc"
DEFAULT_LANGUAGE = "en"


def normalize(value):
    """Normalize names for forgiving path matching."""
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_only = decomposed.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", ascii_only.lower()).strip()


def fetch_map_tree(
    map_version_id=DEFAULT_MAP_VERSION_ID,
    language=DEFAULT_LANGUAGE,
    api_base_url=DEFAULT_API_BASE_URL,
):
    """Fetch the nested map region tree from the iGPSPORT support API."""
    query = urllib.parse.urlencode({
        "mapVersionId": map_version_id,
        "language": language,
    })
    url = f"{api_base_url.rstrip('/')}/web/api/Map/MapInfoList?{query}"
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json,text/plain,*/*",
            "User-Agent": "igpsport-map-updater",
        },
    )

    with urllib.request.urlopen(req) as resp:
        payload = json.loads(resp.read().decode("utf-8"))

    if payload.get("code") != 0:
        message = payload.get("message") or "unknown API error"
        raise RuntimeError(f"iGPSPORT API returned code {payload.get('code')}: {message}")

    return payload.get("data", [])


def iter_nodes(nodes, path=None):
    """Yield every node with its display path."""
    path = path or []

    for node in nodes:
        current_path = [*path, node.get("name", "")]
        yield current_path, node
        yield from iter_nodes(node.get("subList") or [], current_path)


def iter_downloads(nodes):
    """Yield downloadable leaf nodes."""
    for path, node in iter_nodes(nodes):
        url = node.get("mapPathUrl") or node.get("fileUrl")
        if url:
            yield path, node


def path_matches(path, wanted):
    """Return true when wanted terms appear in path order."""
    if not wanted:
        return True

    normalized_path = [normalize(part) for part in path]
    normalized_wanted = [normalize(part) for part in wanted]
    path_index = 0

    for term in normalized_wanted:
        found = False
        while path_index < len(normalized_path):
            part = normalized_path[path_index]
            path_index += 1
            if term == part or term in part:
                found = True
                break

        if not found:
            return False

    return True


def find_downloads(nodes, wanted):
    """Find downloadable map entries whose path matches the requested terms."""
    return [
        (path, node)
        for path, node in iter_downloads(nodes)
        if path_matches(path, wanted)
    ]


def safe_filename(value):
    """Create a safe fallback filename from a region path."""
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("_")
    return cleaned or "igpsport-map"


def filename_from_response(url, response, fallback_name):
    """Resolve a filename from Content-Disposition, URL path, or fallback."""
    disposition = response.headers.get("Content-Disposition", "")
    match = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)', disposition)
    if match:
        return urllib.parse.unquote(match.group(1))

    path_name = Path(urllib.parse.urlparse(url).path).name
    if path_name:
        return path_name

    return f"{safe_filename(fallback_name)}.zip"


def download_file(url, destination):
    """Download a file atomically enough to avoid keeping partial final names."""
    req = urllib.request.Request(url, headers={"User-Agent": "igpsport-map-updater"})
    with urllib.request.urlopen(req) as resp:
        filename = filename_from_response(url, resp, destination.stem)
        target = destination / filename
        partial = target.with_suffix(target.suffix + ".download")

        with open(partial, "wb") as out:
            while True:
                chunk = resp.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)

    os.replace(partial, target)
    return target


def extract_map_files(zip_path, output_dir):
    """Extract .map files from a downloaded archive and return extracted paths."""
    extracted = []
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            if member.is_dir() or not member.filename.lower().endswith(".map"):
                continue

            name = Path(member.filename).name
            target = output_dir / name
            with archive.open(member) as source, open(target, "wb") as dest:
                while True:
                    chunk = source.read(1024 * 1024)
                    if not chunk:
                        break
                    dest.write(chunk)
            extracted.append(target)

    return extracted


def format_size(size):
    if not size:
        return "unknown size"

    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024

    return f"{value:.1f} GB"


def print_downloads(downloads):
    for path, node in downloads:
        print(" > ".join(path))
        print(f"  Version: {node.get('mapVersion') or node.get('ver') or 'unknown'}")
        print(f"  Size:    {format_size(node.get('mapSize') or node.get('size'))}")
        print(f"  URL:     {node.get('mapPathUrl') or node.get('fileUrl')}")


def main():
    parser = argparse.ArgumentParser(
        description="List or download official iGPSPORT map ZIPs from the support API."
    )
    parser.add_argument(
        "path",
        nargs="*",
        help="Region path terms to match, e.g. europe switzerland or aargau",
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download matching ZIPs and extract contained .map files",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List matching downloadable maps without downloading",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="input",
        help="Directory for downloaded and extracted official maps (default: input)",
    )
    parser.add_argument(
        "--keep-zip",
        action="store_true",
        help="Keep downloaded ZIP archives after extraction",
    )
    parser.add_argument(
        "--map-version-id",
        default=DEFAULT_MAP_VERSION_ID,
        help=f"iGPSPORT mapVersionId (default: {DEFAULT_MAP_VERSION_ID})",
    )
    parser.add_argument(
        "--language",
        default=DEFAULT_LANGUAGE,
        help=f"API language parameter (default: {DEFAULT_LANGUAGE})",
    )
    parser.add_argument(
        "--api-base-url",
        default=DEFAULT_API_BASE_URL,
        help=f"API base URL (default: {DEFAULT_API_BASE_URL})",
    )
    args = parser.parse_args()

    if not args.download and not args.list:
        args.list = True

    tree = fetch_map_tree(args.map_version_id, args.language, args.api_base_url)
    downloads = find_downloads(tree, args.path)

    if not downloads:
        print("No matching downloadable maps found.", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(downloads)} downloadable map(s).")
    print_downloads(downloads)

    if not args.download:
        return

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    for path, node in downloads:
        url = node.get("mapPathUrl") or node.get("fileUrl")
        label = " > ".join(path)
        print(f"\nDownloading {label}...")
        downloaded = download_file(url, output_dir)
        print(f"  Saved: {downloaded}")

        if zipfile.is_zipfile(downloaded):
            extracted = extract_map_files(downloaded, output_dir)
            for target in extracted:
                print(f"  Extracted: {target}")

            if not args.keep_zip:
                downloaded.unlink()
                print(f"  Removed ZIP: {downloaded}")


if __name__ == "__main__":
    main()
