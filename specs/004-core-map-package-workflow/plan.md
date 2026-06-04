# Implementation Plan: Core Map Package Workflow

**Branch**: `004-core-map-package-workflow` | **Date**: 2026-06-04 | **Spec**: `specs/004-core-map-package-workflow/spec.md`

**Input**: Migrated feature specification from existing source code and tests.

## Summary

The implemented workflow turns official iGPSPORT map downloads into replacement Mapsforge packages. Python CLI utilities handle discovery, source selection, package naming, manifests, MD5 config updates, and header patch helpers. PowerShell and Bash scripts orchestrate the heavy map-generation path through Osmosis/Mapsforge.

## Technical Context

**Language/Version**: Python 3.12+, PowerShell, Bash

**Primary Dependencies**: Python standard library for most utilities; optional `pyosmium` for PBF tag extraction; Java/Osmosis/Mapsforge writer for real map generation

**Storage**: Local filesystem directories: `input/`, `download/`, `output/`, `tmp/`, `packages/`, plus sidecar build metadata

**Testing**: `uv run pytest -q`

**Target Platform**: Windows PowerShell users, Unix shell users, and future Docker users

**Project Type**: CLI/build pipeline

**Performance Goals**: Avoid unnecessary rebuilds through resume metadata; future osmium preclip optimization is tracked separately

**Constraints**: Generated maps must preserve official iGPSPORT filename identity and must not regress device compatibility

**Scale/Scope**: Country or region-level map packages composed of multiple official map tiles

## Constitution Check

- **Reproducible Map Builds**: Existing implementation records package contents and build metadata; source-selection correctness is covered by tests.
- **Compatibility Before Convenience**: iGS630 tag and header patches exist, but final compatibility still requires manual device checks.
- **Test-First For Data Path Changes**: Existing tests cover parsing, source selection, packaging, MD5 config, and header patching.
- **Cross-Platform Entry Points**: PowerShell and Bash generation scripts both exist, but parity is only partly covered by automated tests.
- **Clear Boundaries And Small Public Commands**: Current root-level module layout works but is crowded; restructure is tracked by `specs/001-repository-restructure`.

## Project Structure

### Documentation (this feature)

```text
specs/004-core-map-package-workflow/
├── spec.md
├── plan.md
└── tasks.md
```

### Source Code (current repository)

```text
build_map_package.py          # End-to-end workflow command
download_igpsport_maps.py    # Official map discovery/download/extraction
generate_maps_csv.py         # Filename parsing and Geofabrik source selection
package_maps.py              # ZIP package creation and manifest generation
map_md5_cfg.py               # Optional map_md5_list.cfg update logic
patch_mapsforge_header.py    # Mapsforge created_by/bbox compatibility patching

run.ps1 / run.sh             # Local-input workflow wrappers
script.ps1 / script.sh       # Map-generation orchestration

tag-igpsport*.xml            # Enhanced tag profile and transform
tag-igpsport-igs630*.xml     # iGS630 compatibility tag profile and transform

test_build_map_package.py
test_download_igpsport_maps.py
test_generate_maps_csv.py
test_package_maps.py
test_map_md5_cfg.py
test_patch_mapsforge_header.py
test_tag_profiles.py
```

**Structure Decision**: This migrated feature documents the current root-level layout. Future work should move reusable Python logic into a package while preserving these public commands.

## Complexity Tracking

| Concern | Why It Exists | Follow-up |
|---------|---------------|-----------|
| PowerShell and Bash generation scripts duplicate behavior | Users run on Windows and Unix today | Prefer Docker/shared implementation for native-tool-heavy features |
| Compatibility patches copy raw header bytes | Some devices are sensitive to Mapsforge metadata details | Keep tests at byte level for header helpers |
| Source selection has geography edge cases | Official iGPSPORT tiles do not always align with one Geofabrik region | Continue adding focused tests for real problematic tiles |
| Root-level module sprawl | The project grew from scripts into a pipeline | Covered by repository restructure spec |
