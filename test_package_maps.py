"""Tests for package_maps.py"""

import hashlib
import zipfile

from igpsport_map_updater.package_maps import (
    default_package_prefix,
    find_matching_outputs,
    package_name,
    parsed_map_files,
)


def _write_map(directory, filename, content=b"map"):
    path = directory / filename
    path.write_bytes(content)
    return path


def test_find_matching_outputs_ignores_generated_date(tmp_path):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    output_dir.mkdir()

    _write_map(input_dir, "CH01002303103YR1DZ005004.map")
    _write_map(output_dir, "CH01002604293YR1DZ005004.map")
    _write_map(output_dir, "CH02002604293YR1DZ005004.map")

    matches = find_matching_outputs(parsed_map_files(input_dir), output_dir)

    assert [match["filename"] for match in matches] == [
        "CH01002604293YR1DZ005004.map",
    ]


def test_find_matching_outputs_uses_metadata_when_generated_geocode_shifts(tmp_path):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    output_dir.mkdir()

    _write_map(input_dir, "CZ01002603203EB25I01C013.map")
    shifted = _write_map(output_dir, "CZ01002604163EB25J01C012.map")
    shifted.with_name(f"{shifted.name}.build.json").write_text(
        "{"
        '"OriginalName":"CZ01002603203EB25I01C013.map",'
        '"CountryCode":"CZ",'
        '"ProductCode":"0100",'
        '"OriginalTileGeocode":"3EB25I01C013",'
        '"GeneratedDataGeocode":"3EB25J01C012"'
        "}",
        encoding="utf-8",
    )

    matches = find_matching_outputs(parsed_map_files(input_dir), output_dir)

    assert [match["filename"] for match in matches] == [
        "CZ01002604163EB25J01C012.map",
    ]


def test_package_name_uses_country_label_latest_date_and_count(tmp_path):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    output_dir.mkdir()

    _write_map(input_dir, "CH01002303103YR1DZ005004.map")
    _write_map(output_dir, "CH01002604293YR1DZ005004.map")

    name = package_name(parsed_map_files(input_dir), parsed_map_files(output_dir))

    assert name == "IGPSport300-800-Switzerland.zip"


def test_package_name_uses_igs630_prefix_when_profile_is_active(tmp_path, monkeypatch):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    output_dir.mkdir()

    _write_map(input_dir, "GR00002604203HV2CO06N05S.map")
    _write_map(output_dir, "GR00002605033HV2CO06N05S.map")
    monkeypatch.setenv("MAP_TAG_PROFILE", "igs630")

    assert default_package_prefix() == "IGPSport-iGS630"
    assert package_name(parsed_map_files(input_dir), parsed_map_files(output_dir)) == (
        "IGPSport-iGS630-Greece.zip"
    )


def test_package_name_can_override_prefix(tmp_path):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    output_dir.mkdir()

    _write_map(input_dir, "GR00002604203HV2CO06N05S.map")
    _write_map(output_dir, "GR00002605033HV2CO06N05S.map")

    name = package_name(
        parsed_map_files(input_dir),
        parsed_map_files(output_dir),
        prefix="IGPSport630",
    )

    assert name == "IGPSport630-Greece.zip"


def test_create_package_cli(tmp_path, monkeypatch):
    from igpsport_map_updater.package_maps import main

    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    package_dir = tmp_path / "packages"
    readme = tmp_path / "MAP_PACKAGE_README.txt"
    input_dir.mkdir()
    output_dir.mkdir()
    readme.write_text("hello maps\n", encoding="utf-8")

    _write_map(input_dir, "BR01002303102B83FO00N00E.map")
    _write_map(output_dir, "BR01002604292B83FO00N00E.map", b"generated")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "sys.argv",
        [
            "package_maps.py",
            str(input_dir),
            "--output-dir",
            str(output_dir),
            "--package-dir",
            str(package_dir),
            "--readme",
            str(readme),
            "--label",
            "brazil",
        ],
    )

    main()

    package = package_dir / "IGPSport300-800-brazil.zip"
    assert package.exists()

    with zipfile.ZipFile(package) as archive:
        assert sorted(archive.namelist()) == [
            "BR01002604292B83FO00N00E.map",
            "MANIFEST.txt",
            "README.txt",
        ]
        assert archive.read("README.txt").replace(b"\r\n", b"\n") == b"hello maps\n"
        assert b"BR01002303102B83FO00N00E.map" in archive.read("MANIFEST.txt")


def test_create_package_cli_can_include_updated_md5_cfg(tmp_path, monkeypatch):
    from igpsport_map_updater.package_maps import main

    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    package_dir = tmp_path / "packages"
    readme = tmp_path / "MAP_PACKAGE_README.txt"
    md5_cfg = tmp_path / "map_md5_list.cfg"
    input_dir.mkdir()
    output_dir.mkdir()
    readme.write_text("hello maps\n", encoding="utf-8")
    md5_cfg.write_text(
        "MAP_NUM:1\r\n"
        "MAP_VER:130\r\n"
        "BR01002303102B83FO00N00E:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\r\n",
        encoding="utf-8",
    )

    _write_map(input_dir, "BR01002303102B83FO00N00E.map")
    _write_map(output_dir, "BR01002604292B83FO00N00E.map", b"generated")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "sys.argv",
        [
            "package_maps.py",
            str(input_dir),
            "--output-dir",
            str(output_dir),
            "--package-dir",
            str(package_dir),
            "--readme",
            str(readme),
            "--md5-cfg",
            str(md5_cfg),
        ],
    )

    main()

    package = package_dir / "IGPSport300-800-Brazil.zip"
    with zipfile.ZipFile(package) as archive:
        cfg_text = archive.read("map_md5_list.cfg").decode("utf-8")
        assert "MAP_NUM:1\r\n" in cfg_text
        assert "BR01002303102B83FO00N00E" not in cfg_text
        expected_md5 = hashlib.md5(b"generated").hexdigest()
        assert f"BR01002604292B83FO00N00E:{expected_md5}" in cfg_text
        assert b"iGS630 MD5 cfg base:" in archive.read("MANIFEST.txt")
