"""Compatibility wrapper for the end-to-end map package CLI."""

from igpsport_map_updater.build_map_package import *  # noqa: F401,F403
from igpsport_map_updater.build_map_package import main


if __name__ == "__main__":
    main()
