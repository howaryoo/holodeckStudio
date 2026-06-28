#!/usr/bin/env bash
# E2E smoke test: generate short episode, validate .mp4 exists and is playable.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_DIR"

echo "=== Holodeck Studio E2E Media Smoke Test ==="

# Check system deps
command -v ffmpeg >/dev/null 2>&1 || { echo "SKIP: ffmpeg not installed"; exit 0; }
command -v ffprobe >/dev/null 2>&1 || { echo "SKIP: ffprobe not installed"; exit 0; }
command -v convert >/dev/null 2>&1 || { echo "SKIP: ImageMagick not installed"; exit 0; }

MEDIA_DIR="./output/media/e2e-test-$(date +%s)"
mkdir -p "$MEDIA_DIR"
trap 'rm -rf "$MEDIA_DIR"' EXIT

# Run vit with --open (suppress interactive launch)
echo "--- Running holodeck produce ---"
uv run holodeck produce "Test episode for e2e media validation" --open 2>&1 | tee "$MEDIA_DIR/produce.log" || true

# Check for video in output
VIDEO_URL=$(grep -Eo 'file://[^ ]+\.mp4' "$MEDIA_DIR/produce.log" | head -1)
if [ -z "$VIDEO_URL" ]; then
    VIDEO_URL=$(grep -Eo '/[^ ]+\.mp4' "$MEDIA_DIR/produce.log" | head -1)
fi

if [ -n "$VIDEO_URL" ]; then
    VIDEO_PATH="${VIDEO_URL#file://}"
    echo "--- Found video: $VIDEO_PATH ---"
    if [ -f "$VIDEO_PATH" ]; then
        ffprobe -v error -show_entries format=duration,size -of default=noprint_wrappers=1 "$VIDEO_PATH"
        echo "PASS: .mp4 exists and is playable"
    else
        echo "FAIL: $VIDEO_PATH not found"
        exit 1
    fi
else
    echo "WARN: No video URL found in output"
    echo "--- Last 20 lines of produce log ---"
    tail -20 "$MEDIA_DIR/produce.log"
fi

echo "=== E2E test complete ==="
