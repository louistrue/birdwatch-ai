#!/bin/bash
# Download test fixtures for E2E testing

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGES_DIR="$SCRIPT_DIR/images"
VIDEOS_DIR="$SCRIPT_DIR/videos"

echo "Downloading test fixtures..."

mkdir -p "$IMAGES_DIR" "$VIDEOS_DIR"

# Download sample bird images from public datasets
# Using Wikimedia Commons public domain bird images

echo "Downloading sample bird images..."

# Great Tit
curl -L "https://upload.wikimedia.org/wikipedia/commons/thumb/8/86/GreatTit001.jpg/320px-GreatTit001.jpg" \
  -o "$IMAGES_DIR/great_tit_1.jpg" 2>/dev/null || echo "Failed to download great_tit_1.jpg"

# Blue Tit
curl -L "https://upload.wikimedia.org/wikipedia/commons/thumb/8/86/Eurasian_blue_tit_Lancashire.jpg/320px-Eurasian_blue_tit_Lancashire.jpg" \
  -o "$IMAGES_DIR/blue_tit_1.jpg" 2>/dev/null || echo "Failed to download blue_tit_1.jpg"

# House Sparrow
curl -L "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6e/Passer_domesticus_male_%2815%29.jpg/320px-Passer_domesticus_male_%2815%29.jpg" \
  -o "$IMAGES_DIR/house_sparrow_1.jpg" 2>/dev/null || echo "Failed to download house_sparrow_1.jpg"

# European Robin
curl -L "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f3/Erithacus_rubecula_with_cocked_head.jpg/320px-Erithacus_rubecula_with_cocked_head.jpg" \
  -o "$IMAGES_DIR/european_robin_1.jpg" 2>/dev/null || echo "Failed to download european_robin_1.jpg"

# Blackbird
curl -L "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a9/Common_Blackbird.jpg/320px-Common_Blackbird.jpg" \
  -o "$IMAGES_DIR/blackbird_1.jpg" 2>/dev/null || echo "Failed to download blackbird_1.jpg"

echo "Sample images downloaded to $IMAGES_DIR"

# Generate a test video from images (requires ffmpeg)
if command -v ffmpeg &> /dev/null; then
    echo "Generating test video from images..."

    # Create a simple slideshow video that loops through bird images
    # This simulates a bird feeder camera feed
    ffmpeg -y \
      -loop 1 -t 3 -i "$IMAGES_DIR/great_tit_1.jpg" \
      -loop 1 -t 3 -i "$IMAGES_DIR/blue_tit_1.jpg" \
      -loop 1 -t 3 -i "$IMAGES_DIR/house_sparrow_1.jpg" \
      -loop 1 -t 3 -i "$IMAGES_DIR/european_robin_1.jpg" \
      -loop 1 -t 3 -i "$IMAGES_DIR/blackbird_1.jpg" \
      -filter_complex "[0][1][2][3][4]concat=n=5:v=1:a=0,fps=25,scale=1280:720" \
      -c:v libx264 -pix_fmt yuv420p \
      "$VIDEOS_DIR/bird_test.mp4" 2>/dev/null

    echo "Test video created: $VIDEOS_DIR/bird_test.mp4"
else
    echo "Warning: ffmpeg not found. Cannot generate test video."
    echo "Install ffmpeg to create test videos, or provide your own bird_test.mp4"
fi

echo ""
echo "Fixtures ready!"
echo "Images: $IMAGES_DIR"
echo "Videos: $VIDEOS_DIR"
echo ""
echo "You can also add your own test images/videos to these directories."
