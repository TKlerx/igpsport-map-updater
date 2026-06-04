"""Compatibility wrapper for the official iGPSPORT map downloader CLI."""

from igpsport_map_updater.download_igpsport_maps import *  # noqa: F401,F403
from igpsport_map_updater.download_igpsport_maps import main


if __name__ == "__main__":
    main()
