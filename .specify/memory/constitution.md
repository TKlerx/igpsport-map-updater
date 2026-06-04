# iGPSPORT Map Updater Constitution

## Core Principles

### I. Reproducible Map Builds
Map outputs must be reproducible from documented inputs: official iGPSPORT map filenames, Geofabrik PBF/poly sources, tag profiles, generator commit, and build settings. Generated `.map`, ZIP, PBF, temp, and package artifacts are local build outputs unless explicitly published as release artifacts.

### II. Compatibility Before Convenience
Device compatibility is part of correctness. Changes to map generation, headers, filenames, tag profiles, package contents, or checksum files must preserve the iGPSPORT filename format and must be tested against the targeted device family or a documented compatibility proxy.

### III. Test-First For Data Path Changes
Any change that can alter generated map content, map metadata, source selection, clipping, package membership, or resume behavior must add or update automated tests before implementation. Performance optimizations must include equivalence checks against the unoptimized path.

### IV. Cross-Platform Entry Points
Windows/PowerShell and Unix/Docker workflows are both supported user paths. Feature work must either cover both native script families or explicitly route the feature through a shared Docker path with native fallback documented.

### V. Clear Boundaries And Small Public Commands
Source code, shell entry points, configuration, specs, docs, tests, and generated artifacts must live in clear locations. User-facing commands should stay stable and small; shared logic should move into testable Python modules or documented scripts instead of growing root-level one-off files.

## Additional Constraints

- Python tooling uses `uv`; native tools such as Java, Osmosis, Mapsforge, and Osmium must be documented separately or provided by Docker.
- Optional dependencies must degrade safely. If an optional optimizer is missing or fails, the pipeline must either fall back to the proven path or stop with a clear error when fallback could change correctness.
- Map output comparison must avoid byte-for-byte assumptions unless determinism is proven. Semantic comparisons should check Mapsforge headers, projection, tile size, zoom intervals, tag dictionaries, and, when available, decoded feature geometry/counts.
- Generated local artifact directories such as `download/`, `input/`, `output/`, `packages/`, `tmp/`, and compatibility experiment outputs must not be committed in normal source changes.

## Development Workflow

- Start feature work with a spec under `specs/`.
- Preserve existing user changes in the worktree; never clean or reset generated/user files without explicit approval.
- Run focused tests for touched behavior, and run the broader pytest suite before finalizing structural or generation-path changes.
- Document manual device/Cruiser checks for any change that cannot be fully verified automatically.

## Governance

This constitution guides specs, implementation plans, PR review, and release decisions. Amendments require updating this file with the reason for the change and reviewing active specs for impact.

**Version**: 1.0.0 | **Ratified**: 2026-06-04 | **Last Amended**: 2026-06-04
