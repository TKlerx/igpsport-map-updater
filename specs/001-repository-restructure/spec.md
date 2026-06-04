# Feature Specification: Repository Restructure

**Feature Branch**: `001-repository-restructure`

**Created**: 2026-06-04

**Status**: Draft

**Input**: User description: "Restructure the repository because scripts, generated artifacts, experiments, docs, and tests are all mixed at the root."

## User Scenarios & Testing

### User Story 1 - Understand The Repo Layout (Priority: P1)

A maintainer can open the repository and immediately distinguish source code, shell entry points, configuration, tests, docs, specs, and generated artifacts.

**Why this priority**: The current root-level sprawl makes it difficult to know what should be edited, committed, ignored, or shared.

**Independent Test**: A fresh clone contains no generated map artifacts in source-controlled areas, and the README documents where each category belongs.

**Acceptance Scenarios**:

1. **Given** a fresh clone, **When** a maintainer lists the root directory, **Then** source, scripts, configs, docs, tests, specs, and generated artifact directories are clearly separated.
2. **Given** a generated `.map` or ZIP artifact, **When** `git status --short` is run, **Then** the artifact is ignored unless explicitly placed in a release-controlled location.

---

### User Story 2 - Keep Existing Commands Working (Priority: P1)

A current user can still run documented root-level commands or wrappers after the code is reorganized.

**Why this priority**: A cleanup that breaks existing workflows would be a regression.

**Independent Test**: Existing documented commands either continue to work or print a clear migration message pointing to the new command.

**Acceptance Scenarios**:

1. **Given** official input maps, **When** the user runs the documented package builder, **Then** it generates and packages maps successfully.
2. **Given** a user following old `run.ps1` or `run.sh` docs, **When** they use the wrapper, **Then** the wrapper delegates to the new script location or gives a clear instruction.

---

### User Story 3 - Develop Against Testable Modules (Priority: P2)

A contributor can modify Python logic without relying on root-level script imports or generated files.

**Why this priority**: The upcoming Docker and Osmium work needs tested reusable code.

**Independent Test**: `uv run pytest` passes after Python modules are moved into a package and tests import from that package.

**Acceptance Scenarios**:

1. **Given** the new package layout, **When** tests run, **Then** imports resolve without manipulating `sys.path` ad hoc.
2. **Given** shared code used by packaging and map generation, **When** it changes, **Then** unit tests cover it directly.

### Edge Cases

- Existing uncommitted user/generated files must not be deleted during the restructure.
- Existing package ZIPs, generated maps, and downloaded PBFs may remain locally but must be ignored by source control.
- Windows path handling must remain valid after scripts move.
- Documentation links to files must be updated.

## Requirements

### Functional Requirements

- **FR-001**: The repository MUST separate Python source modules, user-facing scripts, tag/config files, docs, tests, specs, and generated artifacts into documented locations.
- **FR-002**: The repository MUST keep or provide root-level compatibility wrappers for primary commands during the transition.
- **FR-003**: Generated artifacts MUST be ignored by default, including local map outputs, packages, downloads, temp files, and compatibility experiment outputs.
- **FR-004**: Python tests MUST import production code from a package-style source layout.
- **FR-005**: Documentation MUST identify the recommended one-command workflow and the optional local-input workflow after the restructure.
- **FR-006**: The restructure MUST preserve behavior of existing tests before functional changes are added.

### Key Entities

- **Source Package**: Testable Python modules for downloading, CSV generation, packaging, header patching, checksum files, and BiNavi helpers.
- **Script Entry Point**: User-facing PowerShell/Bash wrappers that run package/generation workflows.
- **Configuration Profile**: Tag mapping and transform XML files for default and iGS630-compatible builds.
- **Generated Artifact**: Local `.map`, ZIP, PBF, poly, temp, and cache files not intended for source control.

## Success Criteria

### Measurable Outcomes

- **SC-001**: `uv run pytest` passes after the restructure.
- **SC-002**: `git status --short` does not show generated `.map`, `.zip`, `.pbf`, or temp cache artifacts after a normal build.
- **SC-003**: README Quick Start contains a single primary command path before optional/manual workflows.
- **SC-004**: At least one existing package workflow test and one CSV-generation test pass against the new package imports.

## Assumptions

- Root-level wrappers may remain to avoid breaking users.
- Large generated artifacts remain local and are not moved into the new source layout.
- The restructure will be a dedicated change before Docker and Osmium preclip implementation.
