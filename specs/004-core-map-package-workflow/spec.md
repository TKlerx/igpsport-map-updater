# Feature Specification: Core Map Package Workflow

**Feature Branch**: `004-core-map-package-workflow`

**Created**: 2026-06-04

**Status**: migrated

**Input**: Reverse-engineered from the existing end-to-end iGPSPORT map package workflow.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Build A Country Package From Official Maps (Priority: P1)

A user can request a region such as Switzerland or United Kingdom and receive a ZIP package containing generated `.map` files that match the official iGPSPORT tile filenames.

**Why this priority**: This is the main user-facing workflow and the command documented first in the README.

**Independent Test**: Run the workflow in dry-run mode and verify the command sequence includes download, CSV generation, map generation, and package creation.

**Acceptance Scenarios**:

1. **Given** a region name, **When** the user runs `uv run python build_map_package.py <region>`, **Then** the workflow downloads matching official maps, creates `maps.csv`, generates replacement maps, and creates a ZIP package.
2. **Given** an explicit package name or prefix, **When** the user passes `--name` or `--package-prefix`, **Then** the resulting package naming uses that override.
3. **Given** a previous region work directory, **When** the user passes `--clean-work`, **Then** only that workflow's work directory is removed before rebuilding.

---

### User Story 2 - Derive Geofabrik Sources From Official Tile Names (Priority: P1)

The workflow can parse official iGPSPORT map filenames, derive tile bounding boxes, and select suitable Geofabrik PBF/poly sources for each tile.

**Why this priority**: Wrong source selection can produce incomplete or geographically wrong maps.

**Independent Test**: Run the CSV generation tests and real filename parsing tests.

**Acceptance Scenarios**:

1. **Given** an official iGPSPORT `.map` filename, **When** it is parsed, **Then** the country code, date, product code, and geocode are extracted.
2. **Given** a parsed geocode, **When** its bounding box is decoded, **Then** the bbox is suitable for matching against Geofabrik regions.
3. **Given** a tile crossing awkward regional boundaries, **When** candidate sources are selected, **Then** the workflow prefers sufficiently covering same-country or multi-region sources.
4. **Given** a western UK/Northern Ireland tile, **When** source matching runs, **Then** it chooses Ireland and Northern Ireland instead of Great Britain when coverage requires it.

---

### User Story 3 - Generate Maps With Compatible Tag Profiles (Priority: P1)

The generation scripts can build Mapsforge `.map` files using the default enhanced profile or the stricter iGS630 compatibility profile.

**Why this priority**: Device compatibility is part of correctness; some devices fail or misbehave with overly rich tags or unexpected Mapsforge metadata.

**Independent Test**: Run tag profile tests and header patch tests; manually verify generated maps on target devices where required.

**Acceptance Scenarios**:

1. **Given** default settings, **When** generation runs, **Then** the enhanced tag profile is used.
2. **Given** `MAP_TAG_PROFILE=igs630`, **When** generation runs, **Then** waterway tags are excluded while official path/footway behavior is preserved.
3. **Given** an official source map and generated target map, **When** the iGS630 compatibility patch runs, **Then** the generated map receives the official Mapsforge `created_by` header value.
4. **Given** bbox compatibility mode, **When** the bbox patch runs, **Then** the generated map receives the official bbox bytes.

---

### User Story 4 - Package Generated Maps With Manifest And Optional MD5 Config (Priority: P2)

The user can package generated maps into a release ZIP containing a README, manifest, matching replacement maps, and optionally an updated `map_md5_list.cfg`.

**Why this priority**: Packaging turns generated maps into something users can install and inspect.

**Independent Test**: Run package tests with temporary map files and optional MD5 config input.

**Acceptance Scenarios**:

1. **Given** official input maps and generated output maps, **When** packaging runs, **Then** maps are matched by country/product/geocode rather than generated date.
2. **Given** `MAP_TAG_PROFILE=igs630`, **When** package naming runs without an explicit prefix, **Then** the iGS630 package prefix is used.
3. **Given** a `map_md5_list.cfg`, **When** packaging runs, **Then** checksums for generated maps are updated and included in the ZIP.
4. **Given** generated maps, **When** the manifest is created, **Then** it records package name, map membership, and source control metadata when available.

---

### Edge Cases

- Region names may match multiple official download nodes; the downloader must support listing and ordered path matching.
- Official downloads may already be extracted locally; resume behavior should avoid duplicate network work.
- Some map tiles require combined Geofabrik sources rather than one exact source.
- Generated output may already exist but may have been created with a different profile or source mode; resume must detect this.
- Optional compatibility patches may need to preserve exact header bytes instead of interpreting and reserializing values.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The workflow MUST expose an end-to-end package command via `build_map_package.py`.
- **FR-002**: The workflow MUST download or reuse official iGPSPORT maps as canonical tile inputs.
- **FR-003**: The workflow MUST generate `maps.csv` from official filenames and Geofabrik region metadata.
- **FR-004**: The workflow MUST preserve official iGPSPORT map filename identity for replacement maps.
- **FR-005**: The workflow MUST support both PowerShell and Unix generation entry points.
- **FR-006**: The workflow MUST support an enhanced default tag profile and an iGS630 compatibility tag profile.
- **FR-007**: The workflow MUST patch Mapsforge header metadata for compatibility when the iGS630 profile requires it.
- **FR-008**: The workflow MUST package only generated maps that match the official input tile keys.
- **FR-009**: The workflow MUST optionally update and include `map_md5_list.cfg` for device families that use it.
- **FR-010**: The workflow MUST keep generated artifacts in ignored local directories unless explicitly published.
- **FR-011**: Resume behavior MUST consider build profile metadata, not only file existence.
- **FR-012**: Changes that alter source selection, generated metadata, package membership, or compatibility profile behavior MUST include automated tests.

### Key Entities *(include if feature involves data)*

- **Official Map**: A downloaded iGPSPORT `.map` file whose filename encodes country, date, product code, and geocode.
- **Tile Key**: The stable identity derived from country/product/geocode, used to match official and generated maps independent of date.
- **Geofabrik Source**: One or more PBF/poly URLs selected to cover a tile bbox.
- **Build Profile**: Sidecar metadata describing settings such as tag profile, source mode, header patching, and writer version.
- **Package Manifest**: Text metadata inside a ZIP describing package contents and provenance.
- **MD5 Config**: Optional device checksum file updated to match generated map payloads.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `uv run pytest -q` passes for the existing workflow tests.
- **SC-002**: Dry-run package workflow emits the expected command sequence without running heavy map generation.
- **SC-003**: Source selection tests cover normal same-region matching, multi-region matching, and the UK/Northern Ireland edge case.
- **SC-004**: Package tests prove generated maps are matched by tile identity rather than generated date.
- **SC-005**: Header patch tests prove `created_by` and bbox bytes can be copied from an official map to a generated map.

## Assumptions

- Real `.map` generation still depends on Java, Osmosis, Mapsforge writer files, and downloaded PBF data.
- Python utilities are run through `uv`.
- Byte-for-byte equality of generated `.map` files is not assumed.
- Manual device or Cruiser validation remains required for compatibility claims that automated tests cannot prove.
- Docker is expected to become the preferred route for native tools such as `osmium-tool`.
