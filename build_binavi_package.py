"""Compatibility wrapper for the BiNavi package CLI."""

from igpsport_map_updater.build_binavi_package import *  # noqa: F401,F403
from igpsport_map_updater.build_binavi_package import main


if __name__ == "__main__":
    main()
