#!/bin/bash
# Generate a simple test pattern video as fallback
# This doesn't require downloading external images

set -e

VIDEOS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/videos"
mkdir -p "$VIDEOS_DIR"

if ! command -v ffmpeg &> /dev/null; then
    echo "Error: ffmpeg is required but not installed"
    exit 1
fi

echo "Generating simple test pattern video..."

# Create a 30-second video with a moving test pattern
# This simulates motion that Frigate can detect
ffmpeg -y -f lavfi \
  -i "testsrc=duration=30:size=1280x720:rate=25" \
  -f lavfi \
  -i "sine=frequency=1000:duration=30" \
  -c:v libx264 -pix_fmt yuv420p -c:a aac \
  "$VIDEOS_DIR/bird_test.mp4"

echo "Test pattern video created: $VIDEOS_DIR/bird_test.mp4"
echo "This can be used for basic testing, but won't classify actual birds."
echo "For realistic testing, run download_fixtures.sh to get real bird images."
