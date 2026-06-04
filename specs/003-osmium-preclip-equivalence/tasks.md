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

- [ ] T007 Add a documented command that compares one baseline output directory with one preclip output directory.
- [ ] T008 Generate or select a small real tile fixture for baseline vs preclip comparison.
- [ ] T009 Record the comparison result before enabling preclip by default.

## Phase 3: Osmium Preclip Integration

- [ ] T010 Add preclip mode selection: disabled, auto, required.
- [ ] T011 Add safe clipped-PBF cache metadata and invalidation.
- [ ] T012 Add tests for command construction, cache hit/miss, source change, bbox change, strategy change, and fallback behavior.
- [ ] T013 Wire preclip into Docker-backed generation.
- [ ] T014 Credit PR #1 in changelog/docs when the optimization lands.
