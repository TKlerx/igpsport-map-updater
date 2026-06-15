# Specs Overview

**Last Updated**: 2026-06-15

This overview tracks spec completeness and implementation status for `specs/`.

## Status Legend

- `Done`: scope implemented and verified for the current spec.
- `Mostly Done`: main behavior exists; follow-up gaps remain.
- `Partial`: some tasks shipped, significant work remains.
- `Planned`: requirements exist, implementation has not started.
- `Migrated`: reverse-engineered documentation for existing behavior.

## Artifact Legend

- `spec`: feature requirements and scenarios
- `plan`: implementation plan and architecture notes
- `tasks`: executable task list
- `checklist`: requirements quality checklist

## Epic Overview

| # | Name | Impl Status | spec | plan | tasks | checklist | Notes |
|---|------|-------------|------|------|-------|-----------|-------|
| 001 | repository-restructure | Done | Y | Y | Y | Y | Conservative Python package restructure is complete; deeper layout cleanup can be a later spec. |
| 002 | docker-build-environment | Mostly Done | Y | Y | Y | Y | Dockerfile, wrapper scripts, documentation, and Docker CI are in place; full map builds remain manual. |
| 003 | osmium-preclip-equivalence | Mostly Done | Y | Y | Y | Y | Semantic comparators, disabled/auto/required preclip modes, cache metadata, tests, and Docker wiring are in place; CH/UK full validation remains manual. |
| 004 | core-map-package-workflow | Mostly Done | Y | Y | Y | - | Migrated documentation for existing workflow; remaining gaps are script parity, manual validation records, and deeper repo cleanup. |

## Open Work

| Spec | Remaining Work |
|------|----------------|
| 002 docker-build-environment | Keep Docker build/run docs current and use full real map generation as manual/release validation, not routine CI. |
| 003 osmium-preclip-equivalence | Run one-time Switzerland and UK baseline-vs-preclip validation and record results in `docs/osmium-preclip-validation.md`. |
| 004 core-map-package-workflow | Add stronger `script.ps1`/`script.sh` parity tests; document manual device/Cruiser validation per release; decide whether a second restructure spec should move scripts/config/tests. |

## Current Priority

1. **Device validation**: Test fixed-package output on known-good iGPSPORT devices before sending new packages to external testers.
2. **003 osmium-preclip-equivalence**: Run full Switzerland and UK baseline-vs-preclip semantic comparisons when machine time allows.
3. **004 core-map-package-workflow**: Add stronger `script.ps1`/`script.sh` parity tests and document manual device/Cruiser validation per release.

## Recent History

- **2026-06-04**: Added Spec Kit with brownfield extension and project constitution.
- **2026-06-04**: Migrated the existing core map package workflow into `004-core-map-package-workflow`.
- **2026-06-04**: Completed conservative Python package restructure under `igpsport_map_updater/`.
- **2026-06-04**: Added Mapsforge semantic comparison fixtures and CLI for baseline-vs-optimized map checks.
- **2026-06-04**: Clarified `003-osmium-preclip-equivalence`: preclip defaults to disabled, Switzerland/UK validation is one-time/manual, routine CI runs only pytest/fixtures.
- **2026-06-04**: Added GitHub Actions pytest workflow for Ubuntu and Windows.
- **2026-06-15**: Added Docker build workflow, Docker wrappers/docs, optional Osmium preclip modes, semantic output/package comparison CLIs, and metadata-based package matching for generated geocode drift.

## CI Notes

- Routine CI runs `uv sync --locked` and `uv run pytest -q` on Ubuntu and Windows.
- Docker CI builds the image, checks Java/uv/Osmium availability, runs pytest, and performs a tiny CSV dry run.
- Full Switzerland/United Kingdom baseline-vs-preclip generation is intentionally not part of routine CI.
