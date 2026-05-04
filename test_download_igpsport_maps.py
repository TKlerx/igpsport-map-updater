"""Tests for download_igpsport_maps.py"""

from download_igpsport_maps import find_downloads, format_size, normalize, path_matches


TREE = [
    {
        "name": "europe",
        "subList": [
            {
                "name": "Switzerland",
                "subList": [
                    {
                        "name": "Aargau",
                        "mapVersion": "20260320",
                        "mapSize": 2875595,
                        "mapPathUrl": "https://example.test/CH0100.zip",
                        "subList": [],
                    },
                    {
                        "name": "Canton Of Graubünden",
                        "mapVersion": "20260320",
                        "mapSize": 3149475,
                        "mapPathUrl": "https://example.test/CH1000.zip",
                        "subList": [],
                    },
                ],
            },
            {
                "name": "Germany",
                "subList": [
                    {
                        "name": "Bayern",
                        "mapVersion": "20260320",
                        "mapSize": 1200,
                        "mapPathUrl": "https://example.test/DE0200.zip",
                        "subList": [],
                    },
                ],
            },
        ],
    },
]


def test_normalize_removes_accents_and_punctuation():
    assert normalize("Canton Of Graubünden") == "canton of graubunden"


def test_path_matches_ordered_terms():
    assert path_matches(["europe", "Switzerland", "Aargau"], ["europe", "switzerland"])
    assert path_matches(["europe", "Switzerland", "Aargau"], ["switzerland", "aargau"])
    assert not path_matches(["europe", "Switzerland", "Aargau"], ["aargau", "switzerland"])


def test_find_downloads_can_match_country():
    downloads = find_downloads(TREE, ["switzerland"])

    assert [path[-1] for path, _node in downloads] == [
        "Aargau",
        "Canton Of Graubünden",
    ]


def test_find_downloads_can_match_single_region_with_accentless_input():
    downloads = find_downloads(TREE, ["graubunden"])

    assert len(downloads) == 1
    assert downloads[0][0] == ["europe", "Switzerland", "Canton Of Graubünden"]
    assert downloads[0][1]["mapPathUrl"].endswith("CH1000.zip")


def test_format_size():
    assert format_size(0) == "unknown size"
    assert format_size(512) == "512 B"
    assert format_size(2048) == "2.0 KB"
    assert format_size(2 * 1024 * 1024) == "2.0 MB"
