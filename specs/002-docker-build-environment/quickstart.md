# Quickstart: Docker Build Environment

Build and run the iGPSPORT map workflow in a reproducible Debian `trixie` container — no conda, no native Java/Osmium on the host.

## Prerequisites

- Docker Desktop (Windows/macOS) or Docker Engine (Linux/WSL).
- A directory of original iGPSPORT maps (e.g. `input/`).
- No host-side Java, Osmosis, or `osmium-tool` required.

## 1. Build the image

Linux / WSL / macOS:

```bash
docker build --build-arg UID="$(id -u)" --build-arg GID="$(id -g)" -t igpsport-map-updater .
```

Windows PowerShell:

```powershell
docker build -t igpsport-map-updater .
```

Expected: image builds from a clean checkout (SC-001).

## 2. Verify tooling

```bash
docker run --rm igpsport-map-updater bash -lc 'java -version && uv --version && osmium --version'
```

Expected: all three succeed (SC-002). The `osmium --version` value matches the version recorded in `docs/docker.md` / README (referenced by feature 003).

## 3. Run the test suite in the image

```bash
docker run --rm igpsport-map-updater uv run pytest -q
```

Expected: tests pass (SC-003).

Dry-run the Docker workflow without generating a full country package:

```bash
docker run --rm igpsport-map-updater bash -lc 'set -eux; java -version; uv --version; osmium --version; uv run pytest -q; mkdir -p /tmp/igpsport-dryrun/input; touch /tmp/igpsport-dryrun/input/BR01002303102B83FO00N00E.map; uv run python generate_maps_csv.py /tmp/igpsport-dryrun/input -o /tmp/igpsport-dryrun/maps.csv; test -s /tmp/igpsport-dryrun/maps.csv'
```

Expected: tools resolve, pytest passes, and a tiny generated `maps.csv` exists (SC-004/SC-005).

## 4. Generate map packages

```bash
docker run --rm \
  -e MAP_TAG_PROFILE=enhanced \
  -v "$PWD/input:/work/input" \
  -v "$PWD/download:/work/download" \
  -v "$PWD/tmp:/work/tmp" \
  -v "$PWD/output:/work/output" \
  -v "$PWD/packages:/work/packages" \
  --user "$(id -u):$(id -g)" \
  igpsport-map-updater ./run.sh input
```

Expected: a ZIP appears in host `packages/`, owned by you (not root) on Linux/WSL (US1, US3, FR-004a). Re-run with `--resume` to skip finished outputs.

Or, with the helper wrapper:

```bash
./docker-run.sh input --resume
```

## 5. Native fallback (no Docker)

Docker is optional. The native paths remain documented:

```powershell
.\run.ps1 input          # Windows / PowerShell
```

```bash
./run.sh input           # Linux / WSL native
```

## Notes

- Generated dirs (`download/`, `output/`, `packages/`, `tmp/`, `input/`) are gitignored and excluded from the image build context via `.dockerignore`.
- Osmosis 0.49.2 and the Mapsforge writer 0.27.0 jar are fetched on first run by `script.sh` (or pre-baked into the image — see plan open options).
- Tag-profile and Java env vars (`MAP_TAG_PROFILE`, `JAVA_XMX`, …) behave identically to the native scripts (FR-005). See `contracts/docker-cli.md`.
- Full country builds are a manual/release step; routine CI only builds the image and runs version checks + pytest + dry-run (SC-005).
