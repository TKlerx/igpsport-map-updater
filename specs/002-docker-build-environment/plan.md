# Implementation Plan: Docker Build Environment

**Branch**: `002-docker-build-environment` | **Date**: 2026-06-05 | **Spec**: `specs/002-docker-build-environment/spec.md`

**Input**: Feature specification from `specs/002-docker-build-environment/spec.md` plus clarifications (Session 2026-06-04).

## Summary

Provide a reproducible Linux container that runs the existing map-generation workflow so Windows users can build map packages without conda or native GIS tooling. The image is built on a Debian `trixie` (Debian 13) slim base and bundles the non-Python tools the pipeline needs but `uv` cannot supply: a JRE for Osmosis/Mapsforge and `osmium-tool` (apt, pinned version for feature 003 equivalence). The container runs as a non-root user whose UID/GID can be matched to the host so artifacts written to mounted `download/`, `tmp/`, `output/`, and `packages/` stay host-owned on Linux/WSL. The existing `script.sh`/`run.sh` entry points, tag-profile env vars (`MAP_TAG_PROFILE`, `MAP_RESUME`, `MAP_INPUT_DIR`, `JAVA_*`), and native PowerShell fallback remain unchanged. CI builds the image and runs tool version checks + `uv run pytest` + a dry-run; full country builds stay manual/release verification.

## Technical Context

**Language/Version**: Python 3.12+ (via `uv`), Bash entry points (`run.sh`, `script.sh`), Dockerfile

**Primary Dependencies (image)**: Debian `trixie` slim base; OpenJDK JRE from trixie apt (for Osmosis 0.49.2 + Mapsforge writer 0.27.0); `osmium-tool` from trixie apt (version pinned/recorded); `uv` for Python; curl/unzip for the existing Osmosis/Mapsforge auto-download in `script.sh`

**Storage**: Host bind mounts for `download/`, `tmp/`, `output/`, `packages/` (and read-only repo/source); generated artifacts gitignored

**Testing**: `uv run pytest -q` inside the image; tool version smoke checks (`java -version`, `uv --version`, `osmium --version`); dry-run workflow

**Target Platform**: Linux container on Docker Desktop (Windows/WSL) or native Docker; native Windows/PowerShell remains documented fallback

**Project Type**: CLI / build pipeline packaged as a container

**Performance Goals**: Reproducibility over speed; image build from clean checkout; full map builds excluded from routine CI (too large)

**Constraints**: No conda (FR-006); non-root host-owned outputs (FR-004a); do not commit `input/`/`download/`/`output/`/`packages/`/`tmp/`; pin osmium version for cross-feature equivalence

**Scale/Scope**: One Dockerfile + `.dockerignore`, optional compose/helper wrapper, README/docs section, one CI job. No application source changes.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Reproducible Map Builds**: PASS — base image pinned to Debian `trixie`; `osmium-tool`, JRE, Osmosis 0.49.2, and Mapsforge writer 0.27.0 versions are recorded so the container environment is documented and reproducible.
- **II. Compatibility Before Convenience**: PASS — Docker only relocates the existing `script.sh` pipeline into a known OS; it does not alter generation logic, headers, filenames, tag profiles, or package contents. SC-002/SC-004 verify tooling; full-build compatibility remains a documented manual/release check.
- **III. Test-First For Data Path Changes**: PASS (with note) — this feature changes the *execution environment*, not the data path. No `.map` content logic changes. Verification is added as CI tool-availability + dry-run checks and a documented version-pin record; no equivalence regression is introduced because outputs come from the unchanged script.
- **IV. Cross-Platform Entry Points**: PASS — this feature *is* the shared Docker path; FR-007 keeps native Windows/PowerShell documented as fallback.
- **V. Clear Boundaries And Small Public Commands**: PASS — Dockerfile, `.dockerignore`, and any helper live at clear root locations; docs in README/`docs/`; no new root one-off Python files. User command stays a single documented `docker build` / `docker run`.

No violations → Complexity Tracking left empty.

## Project Structure

### Documentation (this feature)

```text
specs/002-docker-build-environment/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (image/mount/env configuration model)
├── quickstart.md        # Phase 1 output (build + run walkthrough)
├── contracts/
│   └── docker-cli.md     # Phase 1 output (docker build/run command + env contract)
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

```text
Dockerfile                 # New: trixie-slim base, JRE + osmium-tool + uv, non-root user w/ ARG UID/GID
.dockerignore              # New: exclude download/ output/ packages/ tmp/ input/ .venv/ maps-bak/ etc.
docker-run.sh              # New (optional): host wrapper that maps UID/GID + bind mounts, then runs run.sh/script.sh
docker-run.ps1             # New (optional): PowerShell wrapper for Windows Docker Desktop users

run.sh / script.sh         # Existing: unchanged entry points executed inside the container
run.ps1 / script.ps1       # Existing: native Windows fallback (unchanged)
igpsport_map_updater/      # Existing: Python package (unchanged)
osmosis-0.49.2/            # Existing: vendored Osmosis (gitignored; auto-downloaded by script.sh if absent)

.github/workflows/
└── docker.yml             # New: build image, run version checks + uv run pytest + dry-run (no full build)

README.md                  # Update: Docker build/run section (FR-003) + native fallback note (FR-007)
docs/docker.md             # New (optional): detailed Docker usage, UID/GID mapping, version-pin record
```

**Structure Decision**: Single-project CLI/build pipeline. The Docker layer is additive and root-level — it wraps the unchanged `script.sh` pipeline. No application code moves. Optional `docker-run.*` wrappers exist only to encapsulate UID/GID matching and the standard bind-mount set so the user-facing command stays small (Principle V).

## Complexity Tracking

> No constitution violations — section intentionally empty.
