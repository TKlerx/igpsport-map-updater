# Docker Build Environment

The Docker image runs the existing `run.sh` and `script.sh` workflow in Debian `trixie-slim`. It does not use conda and does not change map generation logic.

## Build

Linux, WSL, or macOS:

```bash
docker build --build-arg UID="$(id -u)" --build-arg GID="$(id -g)" -t igpsport-map-updater .
```

Windows PowerShell:

```powershell
docker build -t igpsport-map-updater .
```

## Verify Tools

```bash
docker run --rm igpsport-map-updater bash -lc 'java -version && uv --version && osmium --version && cat /work/.tool-versions'
```

The image records build-time tool output in `/work/.tool-versions`.

Recorded trixie stable package pin for feature 003 equivalence:

| Tool | Source | Version |
|------|--------|---------|
| `osmium-tool` | Debian trixie apt | `1.18.0-1` |
| Osmosis | Runtime fetch by `script.sh` | `0.49.2` |
| Mapsforge map-writer | Runtime fetch by `script.sh` | `0.27.0` |

Debian trixie lists `osmium-tool` as `1.18.0-1`: https://packages.debian.org/trixie/osmium-tool

## Dry Run

The CI dry-run checks native tools, Python tests, and a tiny `generate_maps_csv.py` fixture without generating a full map package:

```bash
docker run --rm igpsport-map-updater bash -lc 'set -eux; java -version; uv --version; osmium --version; uv run pytest -q; mkdir -p /tmp/igpsport-dryrun/input; touch /tmp/igpsport-dryrun/input/BR01002303102B83FO00N00E.map; uv run python generate_maps_csv.py /tmp/igpsport-dryrun/input -o /tmp/igpsport-dryrun/maps.csv; test -s /tmp/igpsport-dryrun/maps.csv'
```

## Run A Package Build

Raw Docker command:

```bash
mkdir -p input download tmp output packages

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

Helper wrapper:

```bash
./docker-run.sh input --resume
```

PowerShell helper:

```powershell
.\docker-run.ps1 input -Resume
```

## UID/GID Mapping

The image creates a non-root user from `--build-arg UID` and `--build-arg GID`, defaulting to `1000:1000`. On Linux and WSL, also pass `--user "$(id -u):$(id -g)"` at runtime so generated files in `output/` and `packages/` are owned by the host user. Docker Desktop on Windows does not need numeric UID/GID mapping, but the same mounts and wrapper still work.

## Environment Variables

| Variable | Meaning | Default |
|----------|---------|---------|
| `MAP_TAG_PROFILE` | `enhanced` or `igs630` tag profile | `enhanced` |
| `MAP_RESUME` | Resume generated maps when set to `1` | unset |
| `MAP_INPUT_DIR` | Original map input directory, set by `run.sh` | input argument |
| `JAVA_TMP_DIR` | Java scratch directory | `/work/tmp` in Docker wrapper |
| `JAVA_XMS` / `JAVA_XMX` | JVM heap min/max | auto |
| `PYTHON` | Python executable used by scripts | `python3` |
| `MAP_PRECLIP_MODE` | Osmium preclip mode: `disabled`, `auto`, `required` | `disabled` |
| `MAP_PRECLIP_CACHE_DIR` | Clipped PBF cache directory | `/work/tmp/osmium-preclip` |

These are the same variables used by the native scripts.

## Osmium Preclip

Docker includes `osmium-tool`, so it is the preferred way to test the optional preclip path on Windows. Preclip is disabled by default for the initial release:

```bash
docker run --rm \
  -e MAP_PRECLIP_MODE=auto \
  -v "$PWD/input:/work/input" \
  -v "$PWD/download:/work/download" \
  -v "$PWD/tmp:/work/tmp" \
  -v "$PWD/output:/work/output" \
  -v "$PWD/packages:/work/packages" \
  --user "$(id -u):$(id -g)" \
  igpsport-map-updater ./run.sh input --resume
```

Use `MAP_PRECLIP_MODE=required` only for validation runs where fallback would hide an Osmium problem. The cache stores clipped PBFs and metadata in `tmp/osmium-preclip/`; cache entries invalidate when source size/hash/mtime, tile bbox, strategy, or preclip version changes.

## Notes And Edge Cases

- Osmosis and Mapsforge writer are runtime-fetched by `script.sh` on first run. This keeps the image smaller and uses the existing workflow.
- The `.dockerignore` excludes generated directories and local tool downloads from the build context.
- Docker Desktop users must share the repository drive/path with Docker before bind mounts can work.
- Large regions need several GB of disk space in `download/`, `tmp/`, `output/`, and `packages/`.
- Re-running with `MAP_RESUME=1` or `--resume` reuses cached downloads and skips final maps only when sidecar metadata matches current settings.
