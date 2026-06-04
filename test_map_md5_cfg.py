"""Tests for iGS630 map_md5_list.cfg handling."""

import hashlib

from igpsport_map_updater.map_md5_cfg import (
    build_updated_map_md5_cfg,
    read_map_md5_cfg,
    render_map_md5_cfg,
    update_map_md5_entries,
)


def _write_map(directory, filename, content):
    path = directory / filename
    path.write_bytes(content)
    return path


def test_read_and_render_cfg_updates_map_num(tmp_path):
    cfg = tmp_path / "map_md5_list.cfg"
    cfg.write_text(
        "MAP_NUM:999\r\n"
        "MAP_VER:130\r\n"
        "CH01002303103AN27G00H00G:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\r\n",
        encoding="utf-8",
    )

    headers, entries = read_map_md5_cfg(cfg)
    rendered = render_map_md5_cfg(headers, entries)

    assert headers["MAP_VER"] == "130"
    assert "MAP_NUM:1\r\n" in rendered
    assert "CH01002303103AN27G00H00G:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\r\n" in rendered


def test_update_entries_replaces_same_tile_with_new_date(tmp_path):
    new_map = _write_map(
        tmp_path,
        "CH01002605033AN27G00H00G.map",
        b"generated-map",
    )
    old_entries = {
        "CH01002303103AN27G00H00G": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "DE01002303103LK25L00X00Q": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    }

    updated = update_map_md5_entries(old_entries, [new_map])

    assert "CH01002303103AN27G00H00G" not in updated
    assert updated["CH01002605033AN27G00H00G"] == hashlib.md5(b"generated-map").hexdigest()
    assert updated["DE01002303103LK25L00X00Q"] == "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"


def test_build_updated_cfg_appends_new_tile(tmp_path):
    cfg = tmp_path / "map_md5_list.cfg"
    cfg.write_text("MAP_NUM:0\r\nMAP_VER:130\r\n", encoding="utf-8")
    new_map = _write_map(
        tmp_path,
        "BR01002604292B83FO00N00E.map",
        b"generated-br",
    )

    rendered = build_updated_map_md5_cfg(cfg, [new_map])

    assert "MAP_NUM:1\r\n" in rendered
    assert (
        f"BR01002604292B83FO00N00E:{hashlib.md5(b'generated-br').hexdigest()}\r\n"
        in rendered
    )
