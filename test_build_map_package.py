"""Tests for build_map_package.py"""

from argparse import Namespace
from pathlib import Path

from igpsport_map_updater.build_map_package import (
    display_label,
    main,
    safe_slug,
    workflow_commands,
)


def test_safe_slug():
    assert safe_slug(["Switzerland"]) == "switzerland"
    assert safe_slug(["Czech", "Republic"]) == "czech-republic"


def test_display_label_uses_country_label():
    assert display_label(["switzerland"]) == "Switzerland"
    assert display_label(["czech-republic"]) == "Czech-Republic"
    assert display_label(["new zealand"]) == "New-Zealand"


def test_workflow_commands_include_download_generate_and_package(monkeypatch):
    monkeypatch.setattr("os.name", "nt")
    args = Namespace(
        region=["switzerland"],
        keep_zip=False,
        package_dir="packages",
        output_dir="output",
        name=None,
        label=None,
        package_prefix=None,
        md5_cfg=None,
    )

    commands = workflow_commands(args, Path("tmp/igpsport-official-switzerland/input"))

    assert commands[0][1:4] == [
        "download_igpsport_maps.py",
        "switzerland",
        "--download",
    ]
    assert "--resume" in commands[0]
    assert Path(commands[1][-2]) == Path("tmp/igpsport-official-switzerland/input")
    assert commands[1][-1] == "-Resume"
    assert commands[2][-2:] == ["--label", "Switzerland"]


def test_workflow_commands_can_override_package_name():
    args = Namespace(
        region=["switzerland"],
        keep_zip=True,
        package_dir="dist",
        output_dir="custom-output",
        name="IGPSport300-800-Switzerland.zip",
        label=None,
        package_prefix="IGPSport-iGS630",
        md5_cfg="map_md5_list.cfg",
    )

    commands = workflow_commands(args, Path("tmp/in"))

    assert "--keep-zip" in commands[0]
    assert "--name" in commands[2]
    assert "IGPSport300-800-Switzerland.zip" in commands[2]
    assert "--output-dir" in commands[2]
    assert "custom-output" in commands[2]
    assert "--package-prefix" in commands[2]
    assert "IGPSport-iGS630" in commands[2]
    assert commands[2][-2:] == ["--md5-cfg", "map_md5_list.cfg"]


def test_clean_work_removes_region_work_folder(tmp_path, monkeypatch):
    calls = []

    def fake_run_command(command, dry_run=False):
        calls.append((command, dry_run))

    monkeypatch.setattr("igpsport_map_updater.build_map_package.run_command", fake_run_command)
    monkeypatch.setattr(
        "sys.argv",
        [
            "build_map_package.py",
            "switzerland",
            "--work-root",
            str(tmp_path),
            "--clean-work",
        ],
    )

    main()

    assert len(calls) == 3
    assert not (tmp_path / "igpsport-official-switzerland").exists()
