"""Tests for package_maps.py"""

import zipfile

from package_maps import (
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


def test_package_name_uses_country_label_latest_date_and_count(tmp_path):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    output_dir.mkdir()

    _write_map(input_dir, "CH01002303103YR1DZ005004.map")
    _write_map(output_dir, "CH01002604293YR1DZ005004.map")

    name = package_name(parsed_map_files(input_dir), parsed_map_files(output_dir))

    assert name == "IGPSport300-800-Switzerland.zip"


def test_create_package_cli(tmp_path, monkeypatch):
    from package_maps import main

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
