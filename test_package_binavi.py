"""Tests for experimental BiNavi packaging."""

import zipfile

from igpsport_map_updater.package_binavi import (
    binavi_package_name,
    create_binavi_package,
    main_binavi_map,
)


def _write(path, content=b"data"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def test_main_binavi_map_finds_single_parseable_map(tmp_path):
    base = tmp_path / "IT00"
    _write(base / "Maps" / "IT000026022039Y27X07X0A5.map")
    _write(base / "Maps" / "IT0000C.map")
    _write(base / "Router" / "IT0000N.rtd")

    parsed = main_binavi_map(base)

    assert parsed["filename"] == "IT000026022039Y27X07X0A5.map"


def test_binavi_package_name_defaults_to_country_label(tmp_path):
    base = tmp_path / "IT00"
    _write(base / "Maps" / "IT000026022039Y27X07X0A5.map")
    _write(base / "Router" / "IT0000N.rtd")

    assert binavi_package_name(main_binavi_map(base)) == "IGPSport-BiNavi-Italy-Experimental.zip"


def test_create_binavi_package_replaces_only_main_map(tmp_path):
    base = tmp_path / "IT00"
    package_path = tmp_path / "pkg.zip"
    readme = tmp_path / "BINAVI_EXPERIMENTAL_README.txt"
    readme.write_text("readme\n", encoding="utf-8")

    _write(base / "Maps" / "IT000026022039Y27X07X0A5.map", b"official-main")
    _write(base / "Maps" / "IT0000C.map", b"contour")
    _write(base / "Maps" / "IT00A026022007D04Z00I00N.map", b"overview")
    _write(base / "Router" / "IT0000N.rtd", b"router")
    generated = _write(tmp_path / "output" / "IT000026050739Y27X07X0A5.map", b"generated-main")
    replacement = {
        "filename": generated.name,
        "path": generated,
    }

    create_binavi_package(base, replacement, readme, package_path, main_binavi_map(base))

    with zipfile.ZipFile(package_path) as archive:
        names = sorted(archive.namelist())
        assert "Maps/IT000026022039Y27X07X0A5.map" not in names
        assert "Maps/IT000026050739Y27X07X0A5.map" in names
        assert "Maps/IT0000C.map" in names
        assert "Maps/IT00A026022007D04Z00I00N.map" in names
        assert "Router/IT0000N.rtd" in names
        assert archive.read("Maps/IT000026050739Y27X07X0A5.map") == b"generated-main"
        assert b"Router/*.rtd files are copied" in archive.read("MANIFEST.txt")
