# Feature Specification: Osmium Preclip Equivalence

**Feature Branch**: `003-osmium-preclip-equivalence`

**Created**: 2026-06-04

**Status**: Draft

**Input**: User description: "Implement PR #1's osmium preclip optimization, but require semantic equality checks between output generated with and without osmium."

## User Scenarios & Testing

### User Story 1 - Faster Large Tile Builds (Priority: P1)

A user building large map tiles can enable an optional preclip step that reduces the amount of data streamed through Osmosis.

**Why this priority**: Large regions such as UK, Italy, and Switzerland can take a long time when every tile streams a broad source PBF.

**Independent Test**: With Osmium available, the workflow creates or reuses a clipped PBF cache and passes the clipped PBF to Osmosis.

**Acceptance Scenarios**:

1. **Given** Osmium is available and no cache exists, **When** the workflow processes a tile, **Then** it creates a clipped PBF cache for that source/tile/settings combination.
2. **Given** a valid clipped cache exists, **When** the workflow processes the same source/tile/settings again, **Then** it reuses the cached clipped PBF.
3. **Given** Osmium is not available, **When** the workflow runs, **Then** it uses the original PBF path and reports that preclip is skipped.

---

### User Story 2 - Prove Semantic Equivalence (Priority: P1)

A maintainer can verify that optimized and unoptimized outputs are equivalent for map-reader-visible behavior.

**Why this priority**: Preclip changes the data path before Osmosis, so performance must not remove roads, tags, coverage, or device-compatible metadata.

**Independent Test**: A semantic comparison command compares baseline and preclip-generated `.map` files and fails if important Mapsforge metadata or tag dictionaries differ.

**Acceptance Scenarios**:

1. **Given** a baseline map and preclip map generated from the same official input and source date, **When** semantic comparison runs, **Then** magic/version, projection, tile size, bbox policy, zoom intervals, and tag dictionaries match expected equivalence rules.
2. **Given** two maps with different way tag dictionaries, **When** semantic comparison runs, **Then** it fails with a clear mismatch report.
3. **Given** two maps that differ only in allowed non-semantic metadata, **When** semantic comparison runs, **Then** it passes and reports tolerated differences.

---

### User Story 3 - Cache Safely (Priority: P2)

A maintainer can change extraction settings without accidentally reusing stale clipped PBFs.

**Why this priority**: A cache keyed only by source basename and geocode can silently reuse data after strategy or bbox policy changes.

**Independent Test**: Changing source mtime, source size/hash, bbox, extract strategy, or preclip version invalidates the clipped cache.

**Acceptance Scenarios**:

1. **Given** a cache entry created with one extraction strategy, **When** the strategy changes, **Then** the workflow regenerates the clipped PBF.
2. **Given** the source PBF changes, **When** the workflow runs, **Then** the cache invalidates.
3. **Given** the tile bbox changes, **When** the workflow runs, **Then** the cache invalidates.

### Edge Cases

- Multi-source rows must preclip each source independently and preserve source/poly pairing.
- Osmium can fail for malformed input, missing disk space, or unsupported platforms.
- Coastal/border tiles can expose differences in relation completeness and polygon clipping.
- Output may not be byte-identical even when semantically equivalent.
- iGS630/iGS800 header patching and original bbox experiments must remain compatible with preclip.

## Requirements

### Functional Requirements

- **FR-001**: The workflow MUST optionally preclip source PBFs with Osmium before Osmosis when Osmium is available and preclip is enabled.
- **FR-002**: The workflow MUST support a safe fallback to the original PBF path when Osmium is unavailable, unless the user explicitly requires preclip.
- **FR-003**: Preclip cache entries MUST include metadata sufficient to invalidate on source changes, bbox changes, extraction strategy changes, and preclip implementation version changes.
- **FR-004**: Multi-source map rows MUST preserve each source's matching poly file after preclip.
- **FR-005**: The implementation MUST provide tests for preclip command construction, cache hit/miss behavior, and fallback behavior.
- **FR-006**: The implementation MUST provide a semantic Mapsforge comparison tool or test helper.
- **FR-007**: At least one baseline-vs-preclip verification MUST compare generated `.map` outputs using semantic equality rules before the feature is considered complete.
- **FR-008**: Documentation MUST explain that Osmium is provided by Docker or must be installed separately for native runs.

### Key Entities

- **Preclip Cache Entry**: Clipped PBF plus metadata describing source identity, bbox, strategy, and implementation version.
- **Semantic Map Comparison**: Verification result comparing Mapsforge metadata and tag dictionaries between baseline and optimized outputs.
- **Preclip Mode**: User setting controlling disabled, auto, or required preclip behavior.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Unit tests pass for command construction, cache metadata, and fallback behavior.
- **SC-002**: A semantic comparison test fails on intentionally changed tag dictionaries.
- **SC-003**: A documented baseline-vs-preclip check passes for at least one small real tile or fixture.
- **SC-004**: With Osmium unavailable, existing non-preclip workflows continue to pass current tests.
- **SC-005**: With Osmium available in Docker, preclip creates a cache file and subsequent run reuses it.

## Assumptions

- Semantic equality initially checks Mapsforge headers, projection, tile size, zoom intervals, and POI/way tag dictionaries.
- Deeper feature geometry comparison may be added later if map decoding support is expanded.
- Docker is the preferred way to provide Osmium on Windows.
- PR #1 is credited as the source of the optimization idea.
