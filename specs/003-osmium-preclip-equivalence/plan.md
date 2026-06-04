# Implementation Plan: Osmium Preclip Equivalence

**Branch**: `003-osmium-preclip-equivalence` | **Date**: 2026-06-04 | **Spec**: `specs/003-osmium-preclip-equivalence/spec.md`

**Input**: Existing PR #1 idea plus user requirement to test and compare baseline vs Osmium output first.

## Summary

Add a semantic Mapsforge comparison tool before enabling Osmium preclip. The first implementation phase compares baseline and optimized `.map` files on map-reader-visible header and dictionary fields while allowing non-semantic metadata differences such as creation time, file size, writer label, and subfile byte offsets.

## Technical Context

**Language/Version**: Python 3.12+, PowerShell, Bash

**Primary Dependencies**: Python standard library for comparison; future Docker image supplies native `osmium-tool`

**Storage**: Baseline and candidate `.map` outputs in local generated directories

**Testing**: `uv run pytest -q`

**Target Platform**: Native Windows/Unix for comparison; Docker for actual Osmium execution

**Project Type**: CLI/build pipeline

**Performance Goals**: Preclip may improve generation time, but only after semantic equality is enforced

**Constraints**: Do not rely on byte-for-byte `.map` equality

## Constitution Check

- **Reproducible Map Builds**: Comparison makes optimized-vs-baseline differences explicit.
- **Compatibility Before Convenience**: Tag dictionaries, bbox, projection, tile size, flags, and zoom intervals are checked before accepting optimized output.
- **Test-First For Data Path Changes**: Semantic comparison tests are implemented before the preclip data path.
- **Cross-Platform Entry Points**: The comparison CLI is Python and runs through `uv`; Osmium execution will be Docker-backed.

## Project Structure

```text
igpsport_map_updater/map_semantics.py   # Mapsforge semantic reader/comparator
compare_mapsforge_maps.py               # Root compatibility CLI wrapper
test_map_semantics.py                   # Baseline-vs-preclip comparison tests
```

## Complexity Tracking

| Concern | Why Needed | Simpler Alternative Rejected Because |
|---------|------------|-------------------------------------|
| Semantic comparison instead of byte equality | Mapsforge outputs can differ in creation date, file size, writer label, and offsets | Byte equality would reject acceptable optimized outputs |
| Header/tag dictionary scope first | Full geometry decoding is larger work | Header and dictionary mismatches catch the highest-risk early regressions |
