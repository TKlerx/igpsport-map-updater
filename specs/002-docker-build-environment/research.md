# Phase 0 Research: Docker Build Environment

All clarifications from spec Session 2026-06-04 are resolved. Remaining technical unknowns researched below.

## 1. Base image

- **Decision**: `debian:trixie-slim` (Debian 13).
- **Rationale**: Clarified by user. glibc base avoids musl friction for the JRE and `osmium-tool`; `-slim` keeps size down; trixie ships recent osmium and JDK packages.
- **Alternatives considered**: Ubuntu LTS (heavier, not requested); Alpine (musl risk for Java/osmium); `eclipse-temurin` Java base (would pin Java but complicate apt osmium provenance).

## 2. Java runtime for Osmosis 0.49.2 + Mapsforge writer 0.27.0

- **Decision**: Install a headless OpenJDK JRE from trixie apt (`default-jre-headless`, which is OpenJDK 21 on trixie). Record the exact `java -version`.
- **Rationale**: Osmosis 0.49.2 and Mapsforge map-writer 0.27.0 run on modern OpenJDK (8+; validated on 17/21). Headless keeps the image small (no AWT/X11). apt provenance keeps it reproducible with the base image.
- **Alternatives considered**: Bundled Temurin JDK (larger, separate update channel); full `default-jdk` (compiler not needed — the pipeline only runs jars).
- **Note**: `script.sh` auto-downloads Osmosis + the Mapsforge writer jar at runtime via `curl`/`unzip`; the image therefore needs `curl`, `unzip`, and `ca-certificates`. Osmosis dir is gitignored, so it is fetched on first run (or can be pre-baked — see open option below).

## 3. `osmium-tool` install + version pin

- **Decision**: `apt-get install osmium-tool` from trixie; capture the resolved version (e.g. via `osmium --version` and `dpkg -s osmium-tool`) and record it in `docs/docker.md` / README and reference it from feature 003 equivalence docs.
- **Rationale**: Clarified by user. apt is reproducible enough against the pinned base; source builds add maintenance cost. Recording the version gives feature 003 (osmium-preclip-equivalence) a known reference.
- **Alternatives considered**: Source build of libosmium + osmium-tool at a tag (max control, slow); unpinned apt (rejected — breaks 003 equivalence traceability).

## 4. Non-root user + host file ownership

- **Decision**: Create a non-root user in the Dockerfile with build `ARG UID=1000` / `ARG GID=1000`; allow runtime override via `docker run --user "$(id -u):$(id -g)"`. Provide `docker-run.sh` wrapper that injects the caller's UID/GID and the standard bind mounts.
- **Rationale**: Clarified by user (Option A). On Linux/WSL bind mounts preserve numeric UID/GID, so matching the host owner keeps `output/`/`packages/` host-owned and editable. On Windows Docker Desktop the mount layer ignores UID, so the same command is harmless.
- **Alternatives considered**: Root + post-run `chown` (extra step, root-owned artifacts); fixed UID 1000 only (mismatch on non-1000 hosts).
- **Implementation note**: Pre-create and `chown` the mount target dirs inside the image for the non-root user; ensure `tmp/` (JAVA_TMP_DIR) is writable.

## 5. Bind mounts vs named volumes

- **Decision**: Host bind mounts for `download/`, `tmp/`, `output/`, `packages/`, and the input maps dir (`MAP_INPUT_DIR`); repository source mounted (read-only where practical).
- **Rationale**: FR-004 / User Story 3 require artifacts visible on the host in the existing directories. Bind mounts satisfy "outputs on host" directly; named volumes would hide them.
- **Alternatives considered**: Named volumes (hidden from host); copy-out step (extra command, violates "resume where safe").

## 6. Environment variable parity (FR-005)

- **Decision**: Pass through the existing env vars the native scripts already honor: `MAP_TAG_PROFILE` (`enhanced`|`igs630`), `MAP_RESUME`, `MAP_INPUT_DIR`, `JAVA_TMP_DIR`, `JAVA_XMS`, `JAVA_XMX`, `PYTHON`. No new variables.
- **Rationale**: `script.sh` already reads these; Docker only needs `-e` forwarding so behavior matches native.
- **Alternatives considered**: New Docker-specific vars (rejected — would diverge from native path, violating parity).

## 7. CI scope (SC-005)

- **Decision**: New `.github/workflows/docker.yml` on ubuntu-latest: build the image, run `java -version` / `uv --version` / `osmium --version`, `uv run pytest -q`, and a dry-run of the workflow. No full country build. Keep existing `test.yml` (fast native pytest) unchanged.
- **Rationale**: Clarified by user (Option A) + Assumptions. Catches Dockerfile/tool regressions cheaply; full builds are too large/slow for routine CI.
- **Alternatives considered**: Dockerfile lint only (weak); real fixture region E2E (too heavy for routine CI — stays manual/release).
- **Dry-run definition**: A command that exercises the pipeline far enough to prove tools resolve (e.g. version checks + `generate_maps_csv.py` on a tiny fixture, or a `--help`/no-op path) without downloading/generating a full country map. Exact dry-run command finalized during tasks.

## Open options (decide during /speckit-tasks, non-blocking)

- **Pre-bake vs runtime-fetch Osmosis/Mapsforge**: baking the `osmosis-0.49.2/` dir + Mapsforge writer jar into the image improves reproducibility and offline runs but enlarges the image; runtime fetch keeps the image lean and reuses existing `script.sh` logic. Default to runtime fetch unless offline CI requires baking.
- **Helper wrapper scope**: ship `docker-run.sh`/`docker-run.ps1`, or document raw `docker run` only. Default: ship thin wrappers to keep the user command small (Principle V).
