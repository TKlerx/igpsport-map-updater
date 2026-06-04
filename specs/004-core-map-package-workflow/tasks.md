# Tasks: Core Map Package Workflow

**Input**: Migrated implementation in the existing repository root.

**Status**: migrated; completed tasks represent behavior already present in the codebase.

## Phase 1: Official Map Discovery And Download

- [x] T001 Implement region normalization and ordered path matching in `download_igpsport_maps.py`
- [x] T002 Implement official map tree traversal and country/region listing in `download_igpsport_maps.py`
- [x] T003 Implement download filename detection and ZIP extraction in `download_igpsport_maps.py`
- [x] T004 Add downloader tests in `test_download_igpsport_maps.py`

## Phase 2: Tile Parsing And Source Selection

- [x] T005 Implement iGPSPORT filename parsing in `generate_maps_csv.py`
- [x] T006 Implement base36 geocode decoding and tile bbox calculations in `generate_maps_csv.py`
- [x] T007 Implement Geofabrik region lookup and bbox overlap scoring in `generate_maps_csv.py`
- [x] T008 Implement multi-region source selection in `generate_maps_csv.py`
- [x] T009 Implement UK/Northern Ireland source-selection edge case in `generate_maps_csv.py`
- [x] T010 Add source-selection and real filename tests in `test_generate_maps_csv.py`

## Phase 3: Generation Orchestration

- [x] T011 Implement local-input workflow wrappers in `run.ps1` and `run.sh`
- [x] T012 Implement map-generation orchestration in `script.ps1` and `script.sh`
- [x] T013 Implement build metadata sidecar checks for resume behavior in generation scripts
- [x] T014 Implement automatic map writer configuration and memory handling in generation scripts
- [x] T015 Implement iGS630 profile switching through `MAP_TAG_PROFILE`

## Phase 4: Compatibility Profiles And Header Patching

- [x] T016 Add enhanced tag profile XML in `tag-igpsport.xml` and `tag-igpsport-transform.xml`
- [x] T017 Add iGS630 compatibility tag profile XML in `tag-igpsport-igs630.xml` and `tag-igpsport-igs630-transform.xml`
- [x] T018 Implement Mapsforge `created_by` patching in `patch_mapsforge_header.py`
- [x] T019 Implement Mapsforge bbox byte copying in `patch_mapsforge_header.py`
- [x] T020 Add tag profile tests in `test_tag_profiles.py`
- [x] T021 Add header patch tests in `test_patch_mapsforge_header.py`

## Phase 5: Packaging And Device Metadata

- [x] T022 Implement generated map matching by tile identity in `package_maps.py`
- [x] T023 Implement package naming, package prefix selection, and country labeling in `package_maps.py`
- [x] T024 Implement package manifest creation in `package_maps.py`
- [x] T025 Implement optional `map_md5_list.cfg` update logic in `map_md5_cfg.py`
- [x] T026 Add packaging tests in `test_package_maps.py`
- [x] T027 Add MD5 config tests in `test_map_md5_cfg.py`

## Phase 6: End-To-End Workflow Command

- [x] T028 Implement end-to-end command sequence in `build_map_package.py`
- [x] T029 Implement dry-run support in `build_map_package.py`
- [x] T030 Implement package name and prefix overrides in `build_map_package.py`
- [x] T031 Implement region work directory cleanup in `build_map_package.py`
- [x] T032 Add workflow command tests in `test_build_map_package.py`

## Phase 7: Documentation And Verification

- [x] T033 Document the main package command and iGS630 profile usage in `README.md`
- [x] T034 Document lower-level CSV generation, generation scripts, and packaging commands in `README.md`
- [x] T035 Verify automated tests with `uv run pytest -q`

## Identified Gaps

- [ ] G001 Add CI so `uv run pytest -q` runs automatically on pull requests.
- [ ] G002 Add semantic `.map` comparison tooling for optimized vs baseline generation paths.
- [ ] G003 Add stronger parity tests for `script.ps1` and `script.sh` behavior.
- [ ] G004 Document manual device/Cruiser verification results per released package.
- [ ] G005 Complete repository restructure so reusable Python code is no longer spread across root-level scripts.
