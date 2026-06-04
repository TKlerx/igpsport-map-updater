"""Tests for build_binavi_package.py."""

from argparse import Namespace
from pathlib import Path

from igpsport_map_updater.build_binavi_package import workflow_commands


def _write(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"data")


def test_workflow_commands_use_binavi_maps_dir_and_packager(tmp_path, monkeypatch):
    monkeypatch.setattr("os.name", "nt")
    base = tmp_path / "IT00"
    _write(base / "Maps" / "IT000026022039Y27X07X0A5.map")
    _write(base / "Router" / "IT0000N.rtd")
    args = Namespace(
        base_dir=base,
        package_dir="packages",
        output_dir="output",
        name=None,
        label=None,
    )

    commands = workflow_commands(args)

    assert commands[0][-2] == str(base / "Maps")
    assert commands[0][-1] == "-Resume"
    assert commands[1][1] == "package_binavi.py"
    assert commands[1][2] == str(base)
    assert commands[1][-2:] == ["--label", "Italy"]


def test_workflow_commands_allow_name_override(tmp_path):
    base = tmp_path / "IT00"
    _write(base / "Maps" / "IT000026022039Y27X07X0A5.map")
    _write(base / "Router" / "IT0000N.rtd")
    args = Namespace(
        base_dir=base,
        package_dir="dist",
        output_dir="custom-output",
        name="BiNavi-Italy.zip",
        label=None,
    )

    commands = workflow_commands(args)

    assert "--output-dir" in commands[1]
    assert "custom-output" in commands[1]
    assert commands[1][-2:] == ["--name", "BiNavi-Italy.zip"]
