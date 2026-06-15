#!/usr/bin/env bash
set -euo pipefail

IMAGE="${IMAGE:-igpsport-map-updater}"

if [ "$#" -lt 1 ]; then
    echo "Usage: ./docker-run.sh <input-dir> [--resume]" >&2
    exit 1
fi

INPUT_DIR="$1"
shift

RESUME_ARGS=()
if [ "${1:-}" = "--resume" ]; then
    RESUME_ARGS=(--resume)
    shift
fi

if [ "$#" -gt 0 ]; then
    echo "Error: unknown argument '$1'" >&2
    exit 1
fi

if [ ! -d "$INPUT_DIR" ]; then
    echo "Error: '$INPUT_DIR' is not a directory." >&2
    exit 1
fi

INPUT_ABS="$(cd "$INPUT_DIR" && pwd)"

mkdir -p download tmp output packages

docker run --rm \
    --user "$(id -u):$(id -g)" \
    -e MAP_TAG_PROFILE="${MAP_TAG_PROFILE:-enhanced}" \
    -e MAP_RESUME="${MAP_RESUME:-}" \
    -e JAVA_TMP_DIR="${JAVA_TMP_DIR:-/work/tmp}" \
    -e JAVA_XMS="${JAVA_XMS:-}" \
    -e JAVA_XMX="${JAVA_XMX:-}" \
    -v "$INPUT_ABS:/work/input" \
    -v "$PWD/download:/work/download" \
    -v "$PWD/tmp:/work/tmp" \
    -v "$PWD/output:/work/output" \
    -v "$PWD/packages:/work/packages" \
    "$IMAGE" ./run.sh input "${RESUME_ARGS[@]}"
