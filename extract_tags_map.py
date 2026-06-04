"""Compatibility wrapper for the Mapsforge tag extraction CLI."""

from igpsport_map_updater.extract_tags_map import *  # noqa: F401,F403
from igpsport_map_updater.extract_tags_map import main


if __name__ == "__main__":
    main()
