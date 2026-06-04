"""Compatibility wrapper for the map package CLI."""

from igpsport_map_updater.package_maps import *  # noqa: F401,F403
from igpsport_map_updater.package_maps import main


if __name__ == "__main__":
    main()
