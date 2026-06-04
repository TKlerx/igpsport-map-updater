# Changelog

This changelog documents notable changes made in this fork after diverging from the upstream base at `d4a44b8`.

## Unreleased

### Added
- Added experimental BiNavi package tooling that preserves Router and contour/overview files while replacing the main generated map.
- Added a BiNavi backlog document for DEM/contour generation, router files, and richer BiNavi tag mapping.
- Added an `igs630` tag profile for stricter compatibility with older iGS630 devices.
- Added optional iGS630 `map_md5_list.cfg` refresh support for packages, using actual generated map checksums.
- Added per-map build metadata so resume mode rebuilds maps when tag profile or other generation settings changed.
- Added iGS630-aware package naming; `MAP_TAG_PROFILE=igs630` now defaults to `IGPSport-iGS630-<Country>.zip`.
- Added an iGS630 header compatibility patch that copies the original map's Mapsforge `created_by` value into generated iGS630 maps.
- Added `ATTRIBUTION.md` with OpenStreetMap attribution text and sharing guidance for generated maps.
- Added an optional Google Drive link for separately shared unofficial generated maps.
- Added `MAP_PACKAGE_README.txt` for shared map folders and ZIP packages.
- Added `build_map_package.py` as a one-command download, generate, and package workflow.
- Added `package_maps.py` to create shareable ZIPs with generated maps, README, and manifest.
- Added official map discovery options to list country-level regions or search map names.
- Added `generate_maps_csv.py` to derive `maps.csv` entries from original iGPSport `.map` filenames.
- Added `download_igpsport_maps.py` to list/download official iGPSPORT map ZIPs from the public support API.
- Added `run.ps1` and `run.sh` for the full end-to-end workflow: generate `maps.csv`, then build new map files.
- Added project metadata and dependency management via `pyproject.toml`, `.python-version`, and `uv.lock`.
- Added automated tests for the CSV generator in `test_generate_maps_csv.py`.
- Added Python cache and pytest cache ignore rules to `.gitignore`.
- Added option 3 / multi-region source blending for tiles that span several same-country Geofabrik subregions.

### Changed
- Made the end-to-end package workflow resumable for already downloaded official input maps.
- Added `--clean-work` to the end-to-end package workflow to remove downloaded official input maps after successful packaging.
- Updated `script.ps1` and `script.sh` to make Mapsforge writer tuning configurable.
- Changed the default writer behavior from fixed `hd` mode to adaptive `auto` mode.
- Added RAM-first Mapsforge execution with automatic retry in `hd` mode if the RAM attempt fails.
- Added adaptive Java heap sizing capped to about 80% of installed RAM.
- Reduced default thread pressure for larger extracts to avoid excessive memory and IO usage.
- Updated the README to describe the new workflow, project setup, adaptive writer behavior, and troubleshooting guidance.
- Updated `generate_maps_csv.py` so one `maps.csv` row can now contain semicolon-separated PBF/poly source lists.
- Updated `script.ps1` and `script.sh` to download, clip, and merge multi-source rows before running the Mapsforge writer.
- Disabled automatic HD fallback by default; set `MAP_ALLOW_HD_FALLBACK=1` to opt back in.
- Increased the 350-700 MB PBF auto profile to use the capped RAM heap instead of a fixed 8 GB heap.
- Added original tile bounding-box clipping so broad Geofabrik sources do not generate duplicate macro-region maps for several product codes.
- Tightened resume mode to skip only exact expected output filenames, including the original tile geocode.
- Changed final output naming to preserve the original tile geocode while still updating the source date.
- Removed the fixed 6 GB heap ceiling for small PBF files; all RAM auto profiles now use the capped heap.

### Notes
- The generated filename geocode is now based on the actual bounding box stored in the generated `.map` file, so it may differ slightly from the original vendor filename when the produced map coverage differs.
- `run.*` scripts are the full workflow; `script.*` scripts are the map-generation-only step and require an existing `maps.csv`.
