---
description: "Task list for Docker Build Environment"
---

# Tasks: Docker Build Environment

**Input**: Design documents from `specs/002-docker-build-environment/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/docker-cli.md, quickstart.md

**Tests**: The spec does not request a TDD test suite. Verification is done via CI tool checks, `uv run pytest` inside the image, and the documented dry-run (SC-002/003/004/005). No new pytest source files are fabricated; the existing suite must keep passing inside the container.

**Organization**: Tasks grouped by user story. Stories US1 and US2 are both P1; US3 is P2.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1, US2, US3 (maps to spec user stories)
- Exact file paths included. All paths are repository-root relative.

## Path Conventions

Single-project CLI/build pipeline. Docker layer is additive at repo root; no application source moves. Existing entry points `run.sh`/`script.sh` execute unchanged inside the container.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Build-context hygiene and decisions before writing the image.

- [X] T001 Create `.dockerignore` at repo root excluding `download/`, `output/`, `output-*/`, `packages/`, `tmp/`, `input/`, `maps-bak/`, `.venv/`, `.git/`, `osmosis-*/`, `__pycache__/`, `.pytest_cache/`, `.agents/`, `.claude/` (per data-model.md canonical exclude list). Exclude `osmosis-*/` ONLY when T003 = runtime-fetch; if pre-bake is chosen, drop `osmosis-*/` from `.dockerignore` so the vendored tree is copied into the image (analyze F2)
- [X] T002 Confirm `.gitignore` already excludes generated dirs (`download/`, `output/`, `packages/`, `tmp/`, `input/`, `osmosis*`); no change expected, record verification in commit message (FR per Constitution V / spec Edge Cases)
- [X] T003 Decide and document pre-bake vs runtime-fetch of Osmosis 0.49.2 + Mapsforge writer 0.27.0 (default: runtime-fetch via existing `script.sh`) — note the choice at the top of `Dockerfile` as a comment (research.md open option)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Minimal image skeleton every story builds on. No story can be verified until this exists.

**⚠️ CRITICAL**: Blocks US1, US2, US3.

- [X] T004 Create `Dockerfile` with `FROM debian:trixie-slim`, set `WORKDIR /work`, install base apt deps `ca-certificates curl unzip` with `--no-install-recommends` and clean apt lists (FR-001, research.md §1/§2)
- [X] T005 In `Dockerfile`, install `uv` (Astral install script or apt) and ensure Python 3.12+ available; expose `uv` on PATH (FR-002)
- [X] T006 In `Dockerfile`, copy project into `/work` and run `uv sync --locked` so the Python env matches `uv.lock` (parity with `.github/workflows/test.yml`)
- [X] T007 In `Dockerfile`, add `ARG UID=1000` / `ARG GID=1000`, create matching non-root group+user, then `chown -R ${UID}:${GID} /work` (covers `.venv`, the runtime-fetched `osmosis-0.49.2/` tree, the `osmosis-with-mapsforge` wrapper that `script.sh` sed-edits, and mount targets `/work/{download,tmp,output,packages,input}`), and set `USER` to the non-root user (FR-004a foundation — default UID; host-matching override added in US3; enables `script.sh` runtime fetch under non-root — analyze F1)
- [X] T007a In `Dockerfile`, order steps so the `chown -R` runs AFTER project copy + `uv sync` (T006) so all generated/fetched paths are user-owned; if pre-bake is chosen (T003), run the Osmosis + Mapsforge download as root BEFORE the `chown` (analyze F1)

**Checkpoint**: `docker build -t igpsport-map-updater .` succeeds from clean checkout (SC-001); a non-root run can fetch/write Osmosis into `/work` without permission errors.

---

## Phase 3: User Story 2 - Include Native Tooling In The Image (Priority: P1) 🎯 MVP

**Goal**: Image contains all non-Python tools the optimized build needs: JRE, `osmium-tool`.

**Independent Test**: `docker run --rm igpsport-map-updater bash -lc 'java -version && uv --version && osmium --version'` — all succeed (SC-002, US2 scenario 1).

> US2 sequenced first because US1 (running the workflow) depends on the JRE/osmium being present.

- [X] T008 [US2] In `Dockerfile`, `apt-get install` headless OpenJDK JRE (`default-jre-headless`, OpenJDK 21 on trixie) before the `USER` switch; keep `--no-install-recommends` (FR-002, research.md §2)
- [X] T009 [US2] In `Dockerfile`, `apt-get install osmium-tool` from trixie repos (FR-002, research.md §3)
- [X] T010 [US2] In `Dockerfile`, after installs, capture tool versions into an image label/file: run `java -version`, `uv --version`, `osmium --version`, `dpkg -s osmium-tool` and write the osmium version to `/work/.tool-versions` (or LABEL) for traceability (FR-002 version pin)
- [X] T011 [US2] Record the resolved `osmium-tool` version in `docs/docker.md` and reference it from `docs/osmium-preclip-validation.md` (feature 003 equivalence link) (FR-002, research.md §3)
- [X] T012 [US2] Verify `script.sh` osmium usage resolves inside the container: `osmium fileinfo` path at `script.sh:214` works (US2 scenario 2 — optimized preclip uses image osmium)

**Checkpoint**: All three tool checks pass; osmium version recorded (SC-002).

---

## Phase 4: User Story 1 - Run A Reproducible Build On Windows (Priority: P1)

**Goal**: A documented Docker command runs the package workflow in the container and drops a ZIP in host `packages/`.

**Independent Test**: With Docker installed, the documented build+run command on a small region produces a ZIP in `packages/` (US1 scenario 1); README still documents native/WSL fallback (US1 scenario 2).

- [X] T013 [US1] Verify `run.sh`/`script.sh` execute end-to-end inside the container against a small `input/` set, forwarding env via `-e` (mounts from US3 or ad-hoc `-v`); confirm Osmosis/Mapsforge fetch (or pre-baked) works (FR-003, SC-004)
- [X] T014 [P] [US1] Add a "Run with Docker" section to `README.md` documenting `docker build` and `docker run ... ./run.sh input` for at least one country package workflow, mirroring `contracts/docker-cli.md` (FR-003); also document the standalone `docker run --rm igpsport-map-updater uv run pytest -q` command (SC-003, analyze F4)
- [X] T015 [P] [US1] Add native fallback note to `README.md`: keep `run.ps1` (Windows/PowerShell) and WSL paths documented (FR-007, US1 scenario 2)
- [X] T016 [US1] Confirm tag-profile env var parity: `docker run -e MAP_TAG_PROFILE=igs630 ...` selects the `igs630` profile identically to native `script.sh` (FR-005, contracts env table)

**Checkpoint**: Documented Docker command yields a ZIP in host `packages/`; native fallback documented (SC-004, US1).

---

## Phase 5: User Story 3 - Preserve Local Artifacts And Permissions (Priority: P2)

**Goal**: Container writes outputs to host dirs as host-owned files without unexpectedly changing source; runs resume safely.

**Independent Test**: After a container run, artifacts appear in host `output/` and `packages/`, owned by the host user (not root) on Linux/WSL; source files unchanged; re-run resumes (US3 scenarios 1 & 2).

- [X] T017 [US3] Document and verify the runtime UID/GID override: `docker run --user "$(id -u):$(id -g)" ...` (and `--build-arg UID/GID` build path) produces host-owned artifacts on Linux/WSL (FR-004a, research.md §4)
- [X] T018 [P] [US3] Create `docker-run.sh` wrapper at repo root that injects `--user "$(id -u):$(id -g)"`, the standard `-v` mounts (`input download tmp output packages`), and `-e` env, then runs `run.sh <input-dir> [--resume]` inside the container (contracts §Optional wrappers, Principle V)
- [X] T019 [P] [US3] Create `docker-run.ps1` PowerShell wrapper providing the equivalent bind-mount + env invocation for Windows Docker Desktop users (FR-007, contracts §Optional wrappers)
- [X] T020 [US3] Verify persistence/resume: re-running the same command with `MAP_RESUME=1` skips already-generated outputs and reuses cached `download/` inputs (FR-004, US3 scenario 2)
- [X] T021 [US3] Verify source files are unchanged after a run (only generated dirs change) and that generated dirs remain Git-ignored (US3 scenario 1, Constitution I/V)

**Checkpoint**: Host-owned artifacts in `output/`/`packages/`; resume works; source clean (US3).

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: CI verification spanning all stories + docs + edge-case handling.

- [X] T022 Add `.github/workflows/docker.yml` (ubuntu-latest): build the image, run `java -version`/`uv --version`/`osmium --version`, `uv run pytest -q`, and the documented dry-run; no full country build (SC-005, research.md §7). Leave existing `.github/workflows/test.yml` unchanged
- [X] T023 Implement the dry-run target per SC-004 (version checks + `uv run pytest -q` + `generate_maps_csv.py` on a tiny fixture) and wire it into `.github/workflows/docker.yml` + `quickstart.md` + `docs/docker.md` (SC-004/SC-005)
- [X] T024 [P] Finalize `docs/docker.md`: UID/GID mapping, env-var table, recorded tool versions, pre-bake vs runtime-fetch note, Docker Desktop path-sharing and disk-space edge cases (spec Edge Cases)
- [X] T025 [P] Confirm `docker build` succeeds with no conda anywhere in the image (FR-006) and add a note asserting it in `docs/docker.md`
- [X] T026 Run `quickstart.md` end-to-end on a machine with Docker to validate all five steps (SC-001–SC-005)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies — start immediately.
- **Foundational (Phase 2)**: depends on Setup — BLOCKS all stories.
- **US2 (Phase 3)**: depends on Foundational. Sequenced first (P1) because US1 needs the JRE/osmium.
- **US1 (Phase 4)**: depends on Foundational + US2 tooling (needs JRE/osmium to run the workflow).
- **US3 (Phase 5)**: depends on Foundational; independent of US1/US2 verification but shares the Dockerfile user (T007). Can proceed in parallel with US1 once Foundational is done.
- **Polish (Phase 6)**: depends on US1 + US2 (CI exercises both); ideally after US3 too.

### User Story Dependencies

- **US2 (P1)**: after Foundational — no dependency on other stories.
- **US1 (P1)**: after Foundational + US2 (runtime tooling). Independently testable once tools exist.
- **US3 (P2)**: after Foundational — independently testable; refines the default non-root user from T007.

### Within Each Story

- Dockerfile edits (T004–T010) are sequential — same file.
- Docs (T014/T015) and wrappers (T018/T019) are `[P]` — different files.

### Parallel Opportunities

- T014 ∥ T015 (README additions vs fallback note — distinct sections, coordinate merge).
- T018 ∥ T019 (`docker-run.sh` vs `docker-run.ps1` — different files).
- T024 ∥ T025 (doc sections).
- US1 and US3 can run in parallel after US2 tooling lands.

---

## Parallel Example: User Story 3

```bash
# Distinct files — run together:
Task: "Create docker-run.sh wrapper at repo root"
Task: "Create docker-run.ps1 PowerShell wrapper at repo root"
```

---

## Implementation Strategy

### MVP First (US2 + US1)

1. Phase 1 Setup → Phase 2 Foundational (Dockerfile skeleton, SC-001).
2. Phase 3 US2 → tools in image, osmium pinned (SC-002). **Validate** with the three version checks.
3. Phase 4 US1 → documented build/run yields a ZIP (SC-004). **STOP and VALIDATE** — this is the usable MVP.

### Incremental Delivery

1. Setup + Foundational → image builds.
2. US2 → tools verified → demo `osmium --version` etc.
3. US1 → ZIP in `packages/` → demo the documented command (MVP).
4. US3 → host-owned artifacts + wrappers → demo on Linux/WSL.
5. Polish → CI workflow + quickstart validation.

---

## Notes

- `[P]` = different files, no dependencies.
- Most tasks edit `Dockerfile` (sequential) or docs/wrappers (parallel).
- No application source changes — Docker wraps the unchanged `script.sh` pipeline (Constitution II/IV).
- Record the resolved `osmium-tool` version; feature 003 equivalence references it.
- Commit after each task or logical group; keep generated dirs uncommitted.
