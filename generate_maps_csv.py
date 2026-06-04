"""Compatibility wrapper for the maps.csv generation CLI."""

from igpsport_map_updater.generate_maps_csv import *  # noqa: F401,F403
from igpsport_map_updater.generate_maps_csv import main


if __name__ == "__main__":
    main()
