# Implementation Plan: Osmium Preclip Equivalence

**Branch**: `003-osmium-preclip-equivalence` | **Date**: 2026-06-04 | **Spec**: `specs/003-osmium-preclip-equivalence/spec.md`

**Input**: Existing PR #1 idea plus user requirement to test and compare baseline vs Osmium output first.

## Summary

Add a semantic Mapsforge comparison gate before enabling Osmium preclip. The implemented comparison phase compares baseline and optimized `.map` files on map-reader-visible header and dictionary fields while allowing non-semantic metadata differences such as creation time, file size, writer label, and subfile byte offsets.

The remaining implementation phases add folder-level output comparison, GitHub Actions coverage for the fast Python/fixture tests, Docker-backed Osmium execution, safe clipped-PBF cache metadata, and one-time Switzerland plus United Kingdom baseline-vs-preclip release validation. Preclip defaults to disabled for the first release; maintainers must explicitly enable `auto` or `required` modes for test runs.

## Technical Context

**Language/Version**: Python 3.12+, PowerShell, Bash

**Primary Dependencies**: Python standard library for comparison; future Docker image supplies native `osmium-tool`

**Storage**: Baseline and candidate `.map` outputs in local generated directories

**Testing**: `uv run pytest -q`

**Target Platform**: Native Windows/Unix for comparison; Docker for actual Osmium execution

**Project Type**: CLI/build pipeline

**Performance Goals**: Preclip may improve generation time, but only after semantic equality is enforced

**Constraints**: Do not rely on byte-for-byte `.map` equality; full Switzerland and United Kingdom comparisons are manual/release validation checks, not routine CI jobs

## Constitution Check

- **Reproducible Map Builds**: Comparison makes optimized-vs-baseline differences explicit and release validation records Switzerland/United Kingdom proof results.
- **Compatibility Before Convenience**: Tag dictionaries, bbox, projection, tile size, flags, and zoom intervals are checked before accepting optimized output.
- **Test-First For Data Path Changes**: Semantic comparison tests are implemented before the preclip data path.
- **Cross-Platform Entry Points**: The comparison CLI is Python and runs through `uv`; Osmium execution will be Docker-backed, with native Osmium documented as optional.

## Project Structure

```text
igpsport_map_updater/map_semantics.py   # Mapsforge semantic reader/comparator
compare_mapsforge_maps.py               # Root compatibility CLI wrapper
test_map_semantics.py                   # Baseline-vs-preclip comparison tests

igpsport_map_updater/map_output_compare.py  # Planned folder-level map output comparator
compare_map_outputs.py                      # Planned root CLI wrapper for output directories
.github/workflows/test.yml                  # Planned fast CI pytest workflow
docs/osmium-preclip-validation.md           # Planned one-time CH/UK validation record
```

## Complexity Tracking

| Concern | Why Needed | Simpler Alternative Rejected Because |
|---------|------------|-------------------------------------|
| Semantic comparison instead of byte equality | Mapsforge outputs can differ in creation date, file size, writer label, and offsets | Byte equality would reject acceptable optimized outputs |
| Header/tag dictionary scope first | Full geometry decoding is larger work | Header and dictionary mismatches catch the highest-risk early regressions |
| Preclip disabled by default | The optimization changes the data path before Osmosis | `auto` by default would expose users before CH/UK proof is recorded |
| Manual CH/UK validation outside CI | Full country generation is expensive and environment-sensitive | Routine CI would become slow and flaky |
| Docker-backed Osmium path | `uv` cannot reliably provide native `osmium-tool` on Windows | Native-only setup would make the workflow harder to reproduce |

## Implementation Phases

1. **Semantic comparator**: Already implemented with fixture tests and root compatibility CLI.
2. **Folder-level comparator**: Match baseline and candidate outputs by iGPSPORT tile identity and run semantic comparison for every matching map.
3. **CI boundary**: Add GitHub Actions for `uv run pytest -q`; keep full country generation out of routine CI.
4. **Docker/Osmium preclip**: Add disabled/auto/required modes, cache metadata, invalidation, multi-source source/poly pairing, and missing-Osmium fallback tests.
5. **Release validation**: Run and record one-time Switzerland and United Kingdom baseline-vs-preclip comparisons before treating preclip as validated.
