# Attribution and Map Distribution

This repository contains tooling for generating Mapsforge `.map` files from OpenStreetMap data. Generated map files are not stored in Git by default because they are large binary artifacts and are derived from third-party map data.

## Required Attribution

If you publish generated maps, include this attribution with the release, download page, or other distribution location:

```text
Map data copyright OpenStreetMap contributors.
OpenStreetMap data is available under the Open Database License (ODbL):
https://www.openstreetmap.org/copyright
https://opendatacommons.org/licenses/odbl/
```

Also include this project-specific notice:

```text
These files are unofficial community-generated maps for iGPSPORT-compatible devices.
They are not produced, reviewed, endorsed, or supported by iGPSPORT.
```

## Recommended Sharing Notes

When sharing generated `.map` files through Google Drive, GitHub Releases, or another download location, include enough information for users to understand and reproduce the artifacts:

```text
Unofficial iGPSPORT-compatible Mapsforge maps generated with:
- Repository: https://github.com/TKlerx/igpsport-map-updater
- Generator commit: <commit-hash>
- Source data: OpenStreetMap via Geofabrik
- Source date: <YYMMDD or YYYY-MM-DD from the generated filenames/log output>
- Original iGPSPORT map set: <country/region/device source, if known>

Attribution:
Map data copyright OpenStreetMap contributors.
OpenStreetMap data is available under the Open Database License (ODbL):
https://www.openstreetmap.org/copyright
https://opendatacommons.org/licenses/odbl/

Disclaimer:
These files are unofficial community-generated maps for iGPSPORT-compatible devices.
They are not produced, reviewed, endorsed, or supported by iGPSPORT.
Use at your own risk and keep a backup of your original device maps.
```

## Sharing Guidance

- Prefer Google Drive, GitHub Releases, or another artifact/download location for generated `.map` files.
- Do not commit generated maps to normal Git history.
- Keep the matching source inputs reproducible: generator commit, original map filenames, generated `maps.csv`, and OpenStreetMap source date.
- Put `MAP_PACKAGE_README.txt` next to the map files in the shared folder.
- Put `MAP_PACKAGE_README.txt` inside each ZIP if users may download ZIP files individually.
- If you modify the process or combine data sources, document that in the sharing notes.

This is practical project guidance, not legal advice. If you publish generated maps at scale or commercially, review the ODbL terms directly.
