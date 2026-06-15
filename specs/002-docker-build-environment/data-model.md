# Phase 1 Data Model: Docker Build Environment

This feature has no application data entities. The "model" is the container/build configuration. Entities below map spec Key Entities to concrete, testable configuration.

## Entity: Docker Image

Reproducible environment containing the project runtime tools.

| Field | Value / Source | Validation |
|-------|----------------|------------|
| Base | `debian:trixie-slim` | FR-001; `cat /etc/os-release` shows Debian 13 |
| Java | OpenJDK JRE headless (apt, OpenJDK 21 on trixie) | FR-002; `java -version` succeeds |
| osmium-tool | apt `osmium-tool`, version recorded/pinned | FR-002; `osmium --version` succeeds and matches recorded version |
| Python/uv | `uv` + Python 3.12+ | FR-002; `uv --version` succeeds |
| Support tools | `curl`, `unzip`, `ca-certificates` | needed by `script.sh` Osmosis/Mapsforge fetch |
| Osmosis | 0.49.2 (runtime-fetched by `script.sh`, or pre-baked) | matches existing `OSMOSIS_VERSION` |
| Mapsforge writer | 0.27.0 (runtime-fetched) | matches existing `MAPSFORGE_WRITER_VERSION` |
| User | non-root, `ARG UID=1000`/`GID=1000`, runtime-overridable | FR-004a; `id -u` != 0 inside container |

**State**: built → tool-verified (SC-002) → run-capable. Rebuild on Dockerfile or pin change.

## Entity: Mounted Workspace

Host repository plus generated artifact directories bound into the container.

| Mount | Direction | Purpose | Constraint |
|-------|-----------|---------|------------|
| repo source | host → container | run `run.sh`/`script.sh`, Python package | source unchanged unless command generates it (US3) |
| `download/` | read-write | cached PBF/poly inputs | persist across runs (FR-004); gitignored |
| `tmp/` | read-write | `JAVA_TMP_DIR` scratch | writable by non-root user |
| `output/` | read-write | generated `.map` files | host-visible, host-owned (FR-004a) |
| `packages/` | read-write | final ZIP packages | host-visible, gitignored |
| `MAP_INPUT_DIR` | read | original iGPSPORT maps | provided by user, e.g. `input/` |

**Validation**: after a run, artifacts appear on host in these dirs and are owned by the host user, not root (FR-004a, US3 scenario 1). Re-run resumes safely (US3 scenario 2 via `MAP_RESUME`).

## Entity: Build Command

Documented user command for region/package generation.

| Field | Value | Validation |
|-------|-------|------------|
| Build | `docker build` with `--build-arg UID/GID` | SC-001 builds from clean checkout |
| Run | `docker run` with `-e` env + bind mounts, invoking `run.sh`/`script.sh` | SC-004 dry-run without host-native Java/Osmium |
| Env contract | `MAP_TAG_PROFILE`, `MAP_RESUME`, `MAP_INPUT_DIR`, `JAVA_TMP_DIR`, `JAVA_XMS`, `JAVA_XMX`, `PYTHON` | FR-005 parity with native |
| Wrapper (optional) | `docker-run.sh` / `docker-run.ps1` | injects UID/GID + standard mounts |

See `contracts/docker-cli.md` for the full command/env contract.

## Configuration values (canonical)

- Base image: `debian:trixie-slim`
- Osmosis: `0.49.2`
- Mapsforge writer: `0.27.0`
- Tag profiles: `enhanced` (default), `igs630`
- Excluded from image context (`.dockerignore`): `download/`, `output/`, `output-*/`, `packages/`, `tmp/`, `input/`, `maps-bak/`, `.venv/`, `.git/`, `osmosis-*/`, `__pycache__/`, `.pytest_cache/`
