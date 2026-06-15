# Tasks: Osmium Preclip Equivalence

**Input**: `specs/003-osmium-preclip-equivalence/spec.md`

## Phase 1: Semantic Comparison Before Osmium

- [x] T001 Add a Mapsforge semantic reader in `igpsport_map_updater/map_semantics.py`.
- [x] T002 Compare file version, bbox, tile size, projection, flags, map start, start zoom, language, POI tags, way tags, and zoom interval ranges.
- [x] T003 Ignore allowed non-semantic differences: file size, creation date, created_by value, and zoom interval byte offsets.
- [x] T004 Add root CLI wrapper `compare_mapsforge_maps.py`.
- [x] T005 Add fixture tests proving baseline and Osmium/preclip candidate maps can differ only in non-semantic metadata.
- [x] T006 Add fixture tests proving way tag dictionary differences fail clearly.

## Phase 2: Real Baseline-vs-Preclip Verification

- [x] T007 Add folder-level comparison logic in `igpsport_map_updater/map_output_compare.py` that matches maps by country/product/geocode and compares each pair semantically.
- [x] T008 Add root CLI wrapper `compare_map_outputs.py` for comparing one baseline output directory with one preclip output directory.
- [x] T009 Add tests in `test_map_output_compare.py` for matching by tile identity, missing baseline/candidate maps, and semantic mismatch reporting.
- [ ] T010 Run one-time Switzerland baseline-vs-preclip generation and semantic output comparison; record the result in `docs/osmium-preclip-validation.md`.
- [ ] T011 Run one-time United Kingdom baseline-vs-preclip generation and semantic output comparison; record the result in `docs/osmium-preclip-validation.md`.
- [x] T012 Document in `docs/osmium-preclip-validation.md` that full Switzerland and United Kingdom comparisons are manual/release validation checks, not routine CI jobs.

## Phase 3: CI Boundary

- [x] T013 Add GitHub Actions workflow in `.github/workflows/test.yml` that installs `uv`, syncs dependencies, and runs `uv run pytest -q`.
- [x] T014 Ensure CI covers `test_map_semantics.py` fixture semantic comparison tests.
- [x] T015 Keep full country generation and baseline-vs-preclip package comparisons out of routine CI.

## Phase 4: Osmium Preclip Integration

- [x] T016 Add preclip mode selection: disabled, auto, required.
- [x] T017 Make disabled the default preclip mode for the initial release.
- [x] T018 Add safe clipped-PBF cache metadata and invalidation.
- [x] T019 Add tests for command construction, cache hit/miss, source change, bbox change, strategy change, and fallback behavior.
- [x] T020 Add explicit tests that disabled mode and missing Osmium preserve the current non-preclip generation path.
- [x] T021 Add multi-source preclip tests proving each source PBF is clipped independently and remains paired with its matching poly file.
- [x] T022 Wire preclip into Docker-backed generation.
- [x] T023 Document Docker-provided Osmium, optional native Osmium installation, and disabled/auto/required modes in `README.md`.
- [x] T024 Credit PR #1 in changelog/docs when the optimization lands.
