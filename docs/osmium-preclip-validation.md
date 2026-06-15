# Osmium Preclip Validation

Feature 003 uses the Docker image as the reference environment for `osmium fileinfo` and future preclip equivalence checks.

The Debian trixie image records `osmium-tool` in `/work/.tool-versions`; the planned package version is `1.18.0-1` from Debian trixie stable.

Reference: https://packages.debian.org/trixie/osmium-tool

## Routine Validation

Routine CI runs fixture-level semantic comparison tests and Docker dry-run checks. It does not generate full Switzerland or United Kingdom packages.

Fast checks:

```bash
uv run pytest -q
docker run --rm igpsport-map-updater uv run pytest -q
docker run --rm igpsport-map-updater bash -lc 'java -version && uv --version && osmium --version'
```

## Manual Release Validation

Before enabling preclip by default, run baseline and preclip builds for Switzerland and United Kingdom, then compare output folders:

```bash
# Baseline
MAP_PRECLIP_MODE=disabled ./docker-run.sh input-switzerland --resume
cp -r output output-switzerland-baseline

# Candidate
MAP_PRECLIP_MODE=auto ./docker-run.sh input-switzerland --resume
cp -r output output-switzerland-preclip

uv run python compare_map_outputs.py output-switzerland-baseline output-switzerland-preclip
```

Repeat the same process for United Kingdom. Record dates, generator commit, Docker image tool versions, and comparison result below.

| Region | Baseline command | Preclip command | Result |
|--------|------------------|-----------------|--------|
| Switzerland | Pending manual release validation | Pending manual release validation | Pending |
| United Kingdom | Pending manual release validation | Pending manual release validation | Pending |
