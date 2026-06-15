# Contract: Docker Build & Run CLI

User-facing command interface for the Docker build environment. These commands are the stable public surface (Principle V). Examples use `igpsport-map-updater` as the image tag.

## Build

```bash
docker build \
  --build-arg UID="$(id -u)" \
  --build-arg GID="$(id -g)" \
  -t igpsport-map-updater .
```

- **Contract**: builds from a clean checkout with no conda (FR-006, SC-001).
- On Windows PowerShell, UID/GID args are optional (Docker Desktop ignores them); a default `1000` is baked.

## Tool verification

```bash
docker run --rm igpsport-map-updater bash -lc 'java -version && uv --version && osmium --version'
```

- **Contract**: each command exits 0 (SC-002, FR-002, US2 scenario 1). `osmium --version` matches the recorded pinned version.

## Run tests inside the image

```bash
docker run --rm igpsport-map-updater uv run pytest -q
```

- **Contract**: SC-003.

## Run the package workflow

```bash
docker run --rm \
  -e MAP_TAG_PROFILE=enhanced \
  -e MAP_RESUME=1 \
  -v "$PWD/input:/work/input" \
  -v "$PWD/download:/work/download" \
  -v "$PWD/tmp:/work/tmp" \
  -v "$PWD/output:/work/output" \
  -v "$PWD/packages:/work/packages" \
  --user "$(id -u):$(id -g)" \
  igpsport-map-updater ./run.sh input --resume
```

- **Contract**: a ZIP appears in host `packages/` (US1 scenario 1); artifacts host-owned (FR-004a); inputs/outputs persist and resume across runs (FR-004, US3).

## Dry-run (no full build)

```bash
docker run --rm igpsport-map-updater bash -lc \
  'java -version && uv --version && osmium --version && uv run pytest -q'
```

- **Contract**: SC-004 / SC-005 — proves tools resolve and tests pass without host-native Java/Osmium and without generating a full country map. Exact dry-run target may be extended (e.g. `generate_maps_csv.py` on a tiny fixture) during `/speckit-tasks`.

## Environment variable contract (parity with native — FR-005)

| Variable | Meaning | Default |
|----------|---------|---------|
| `MAP_TAG_PROFILE` | tag profile: `enhanced` or `igs630` | `enhanced` |
| `MAP_RESUME` | skip already-generated outputs when `1` | unset |
| `MAP_INPUT_DIR` | original iGPSPORT maps dir (set by `run.sh`) | — |
| `JAVA_TMP_DIR` | Java scratch dir | `<repo>/tmp` |
| `JAVA_XMS` / `JAVA_XMX` | JVM heap min/max | auto |
| `PYTHON` | python executable for entry scripts | `python3` |

All variables behave identically to the native `script.sh` path; Docker only forwards them via `-e`.

## Optional wrappers

- `docker-run.sh <input-dir> [--resume]` — injects `--user "$(id -u):$(id -g)"`, the standard `-v` mounts, and `-e` env, then runs `run.sh` inside the container.
- `docker-run.ps1 <input-dir> [-Resume]` — PowerShell equivalent for Windows Docker Desktop users.

## Fallback contract (FR-007)

If Docker is unavailable, the README MUST keep documenting the native Windows/PowerShell (`run.ps1`) and WSL paths (US1 scenario 2).
