#!/bin/bash
# Utility script to manually inject test images into the pipeline
# Simulates Frigate snapshot generation for testing

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SNAPSHOTS_DIR="$SCRIPT_DIR/data/test-snapshots"
FIXTURES_DIR="$SCRIPT_DIR/fixtures/images"

if [ ! -d "$FIXTURES_DIR" ] || [ -z "$(ls -A $FIXTURES_DIR 2>/dev/null)" ]; then
    echo "Error: No test images found in $FIXTURES_DIR"
    echo "Run: cd fixtures && ./download_fixtures.sh"
    exit 1
fi

mkdir -p "$SNAPSHOTS_DIR"

echo "Injecting test images into pipeline..."
echo "This simulates Frigate generating snapshots"
echo ""

count=0
for img in "$FIXTURES_DIR"/*.jpg; do
    if [ -f "$img" ]; then
        # Generate unique filename with timestamp
        timestamp=$(date +%s%N | cut -b1-13)
        filename="test_camera_${timestamp}.jpg"

        # Copy to snapshots directory
        cp "$img" "$SNAPSHOTS_DIR/$filename"

        echo "Injected: $filename (from $(basename $img))"
        count=$((count + 1))

        # Small delay to avoid race conditions
        sleep 1
    fi
done

echo ""
echo "Injected $count test images"
echo "The classifier should process these automatically"
echo "Check logs: docker-compose -f docker-compose.test.yml logs -f classifier"
