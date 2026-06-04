"""Tests for Mapsforge tag profile XML files."""

import xml.etree.ElementTree as ET
from pathlib import Path


NS = {"mf": "http://mapsforge.org/tag-mapping"}


def _tag_values(path, key):
    tree = ET.parse(path)
    return {
        node.attrib["value"]
        for node in tree.findall(".//mf:osm-tag", NS)
        if node.attrib.get("key") == key
    }


def test_igs630_profile_excludes_waterways_and_keeps_official_path_tags():
    values = _tag_values(Path("tag-igpsport-igs630.xml"), "highway")
    waterways = _tag_values(Path("tag-igpsport-igs630.xml"), "waterway")

    assert "footway" in values
    assert "path" in values
    assert waterways == set()


def test_enhanced_profile_includes_waterways():
    waterways = _tag_values(Path("tag-igpsport.xml"), "waterway")

    assert {"canal", "dam", "drain", "river", "stream"} <= waterways


def test_igs630_transform_preserves_footway_and_path():
    text = Path("tag-igpsport-igs630-transform.xml").read_text(encoding="utf-8")

    assert 'v="footway"' not in text
    assert 'v="path"' not in text
