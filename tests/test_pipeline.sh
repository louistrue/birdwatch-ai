#!/bin/bash
# Test Full Pipeline with Video File
# Tests Hailo detection + TFLite classification pipeline

set -e

VIDEO_FILE="$HOME/bird-watcher/tests/bird_test.mp4"
LOG_DIR="$HOME/bird-watcher/logs"
DETECTIONS_DIR="$HOME/bird-watcher/detections"
HAILO_DIR="$HOME/hailo-rpi5-examples"

echo "=========================================="
echo "  Pipeline Test Script"
echo "=========================================="
echo ""

# Step 1: Verify video file exists
echo "Step 1: Checking video file..."
if [ ! -f "$VIDEO_FILE" ]; then
    echo "ERROR: Video file not found: $VIDEO_FILE"
    exit 1
fi
echo "✅ Video file found: $VIDEO_FILE"
echo ""

# Step 2: Test TFLite classifier standalone
echo "Step 2: Testing TFLite classifier..."
cd "$HOME/bird-watcher"
source venv/bin/activate
python3 -c "
import cv2
from species_classifier import SpeciesClassifier

cap = cv2.VideoCapture('$VIDEO_FILE')
cap.set(cv2.CAP_PROP_POS_FRAMES, 500)
ret, frame = cap.read()
cap.release()

if ret:
    classifier = SpeciesClassifier()
    results = classifier.classify(frame)
    print('✅ Classifier test passed')
    print(f'   Top result: {results[0][0]} ({results[0][1]*100:.1f}%)')
else:
    print('❌ Failed to extract frame')
    exit(1)
"
echo ""

# Step 3: Clear old detections (optional)
echo "Step 3: Preparing detection directories..."
mkdir -p "$LOG_DIR" "$DETECTIONS_DIR"
echo "✅ Directories ready"
echo ""

# Step 4: Run Hailo pipeline
echo "Step 4: Running Hailo detection pipeline..."
echo "   This will process the video and detect objects..."
echo ""

cd "$HAILO_DIR"
source setup_env.sh

# Run pipeline for 30 seconds
timeout 30 python3 basic_pipelines/bird_detection.py \
    --input "$VIDEO_FILE" \
    --use-frame \
    2>&1 | tee /tmp/pipeline_test_run.log || true

echo ""
echo "Step 5: Checking results..."

# Check for detections
TODAY=$(date +%Y-%m-%d)
LOG_FILE="$LOG_DIR/$TODAY.json"

if [ -f "$LOG_FILE" ]; then
    DETECTION_COUNT=$(python3 -c "
import json
with open('$LOG_FILE') as f:
    detections = json.load(f)
print(len(detections))
" 2>/dev/null || echo "0")
    
    echo "✅ Detection log found: $LOG_FILE"
    echo "   Total detections: $DETECTION_COUNT"
    
    # Count detection images
    IMAGE_COUNT=$(ls -1 "$DETECTIONS_DIR"/*.jpg 2>/dev/null | wc -l)
    echo "   Detection images: $IMAGE_COUNT"
    
    if [ "$DETECTION_COUNT" -gt 0 ]; then
        echo ""
        echo "✅ Pipeline test PASSED!"
        echo ""
        echo "Latest detection:"
        python3 -c "
import json
from datetime import datetime
with open('$LOG_FILE') as f:
    detections = json.load(f)
if detections:
    latest = detections[-1]
    print(f\"  ID: {latest.get('id')}\")
    print(f\"  Time: {latest.get('timestamp')}\")
    print(f\"  Label: {latest.get('detection_label', 'N/A')}\")
    if latest.get('visual_classification'):
        top = latest['visual_classification'][0]
        print(f\"  Species: {top.get('species')} ({top.get('confidence', 0)*100:.1f}%)\")
" 2>/dev/null
    else
        echo "⚠️  No detections found in log"
    fi
else
    echo "⚠️  No log file created"
fi

echo ""
echo "=========================================="
echo "Test complete!"
echo "=========================================="
