"""Tests for build_map_package.py"""

from argparse import Namespace
from pathlib import Path

from build_map_package import display_label, safe_slug, workflow_commands


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
    )

    commands = workflow_commands(args, Path("tmp/igpsport-official-switzerland/input"))

    assert commands[0][1:4] == [
        "download_igpsport_maps.py",
        "switzerland",
        "--download",
    ]
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
    )

    commands = workflow_commands(args, Path("tmp/in"))

    assert "--keep-zip" in commands[0]
    assert commands[2][-2:] == ["--name", "IGPSport300-800-Switzerland.zip"]
    assert "--output-dir" in commands[2]
    assert "custom-output" in commands[2]
