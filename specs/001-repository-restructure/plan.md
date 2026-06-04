# Implementation Plan: Repository Restructure

**Branch**: `001-repository-restructure` | **Date**: 2026-06-04 | **Spec**: `specs/001-repository-restructure/spec.md`

**Input**: Existing repository layout and validated Brownfield scan.

## Summary

Move reusable Python implementation modules into an importable `igpsport_map_updater` package while preserving root-level CLI compatibility wrappers. Keep PowerShell/Bash scripts and XML tag profiles in their current public locations for this phase. Update tests to import package modules directly, then verify existing behavior remains unchanged.

## Technical Context

**Language/Version**: Python 3.12+, PowerShell, Bash

**Primary Dependencies**: Python standard library; optional `pyosmium`; Java/Osmosis/Mapsforge outside Python

**Storage**: Local generated directories are ignored and not moved

**Testing**: `uv run pytest -q`

**Target Platform**: Windows PowerShell, Unix shell, future Docker

**Project Type**: CLI/build pipeline

**Constraints**: Root-level documented Python commands must continue to work during transition

## Constitution Check

- **Reproducible Map Builds**: No map-generation behavior changes are intended.
- **Compatibility Before Convenience**: Root CLI wrappers preserve existing commands.
- **Test-First For Data Path Changes**: This is structural; full pytest suite is the required gate.
- **Cross-Platform Entry Points**: `run.ps1`, `run.sh`, `script.ps1`, and `script.sh` stay in place.
- **Clear Boundaries And Small Public Commands**: Production Python code moves into a package; wrappers remain small.

## Project Structure

### Documentation (this feature)

```text
specs/001-repository-restructure/
├── spec.md
├── plan.md
├── tasks.md
└── checklists/
```

### Source Code

```text
igpsport_map_updater/
├── __init__.py
├── build_map_package.py
├── build_binavi_package.py
├── download_igpsport_maps.py
├── extract_tags_map.py
├── extract_tags_pbf.py
├── generate_maps_csv.py
├── map_md5_cfg.py
├── package_binavi.py
├── package_maps.py
└── patch_mapsforge_header.py

build_map_package.py          # compatibility wrapper
build_binavi_package.py       # compatibility wrapper
download_igpsport_maps.py     # compatibility wrapper
extract_tags_map.py           # compatibility wrapper
extract_tags_pbf.py           # compatibility wrapper
generate_maps_csv.py          # compatibility wrapper
map_md5_cfg.py                # compatibility wrapper
package_binavi.py             # compatibility wrapper
package_maps.py               # compatibility wrapper
patch_mapsforge_header.py     # compatibility wrapper
```

**Structure Decision**: Use a package-first Python layout without changing shell script locations yet. A later cleanup can move shell scripts and configs once Docker entry points are defined.

## Complexity Tracking

| Concern | Why Needed | Simpler Alternative Rejected Because |
|---------|------------|-------------------------------------|
| Root compatibility wrappers | Existing README and user muscle memory call root files directly | Moving commands outright would break documented workflows |
| Package-relative imports | Modules now live together inside a package | Keeping root imports would hide structure problems |
