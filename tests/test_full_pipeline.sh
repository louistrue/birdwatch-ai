#!/bin/bash
# Full Pipeline Test with Video + Audio
# Tests Hailo detection + TFLite classification + BirdNET audio

set -e

VIDEO_FILE="$HOME/bird-watcher/tests/bird_test.mp4"
LOG_DIR="$HOME/bird-watcher/logs"
DETECTIONS_DIR="$HOME/bird-watcher/detections"
HAILO_DIR="$HOME/hailo-rpi5-examples"

echo "=========================================="
echo "  Full Pipeline Test (Video + Audio)"
echo "=========================================="
echo ""

# Step 1: Test Audio Classifier with sample audio
echo "Step 1: Testing Audio Classifier..."
cd "$HOME/bird-watcher"
source venv/bin/activate

# Create a test audio file (5 seconds of silence + noise for testing)
echo "Creating test audio file..."
arecord -D plughw:2,0 -d 5 -f S16_LE -r 48000 -c 1 /tmp/test_audio.wav 2>&1 &
RECORD_PID=$!
sleep 2
echo "Recording test audio (speak or make noise near microphone)..."
wait $RECORD_PID 2>/dev/null || true

if [ -f /tmp/test_audio.wav ] && [ -s /tmp/test_audio.wav ]; then
    echo "✅ Test audio recorded: $(ls -lh /tmp/test_audio.wav | awk '{print $5}')"
    
    echo ""
    echo "Testing BirdNET classification..."
    python3 -c "
from audio_classifier import AudioClassifier
import time

print('Loading BirdNET...')
classifier = AudioClassifier()
print('Analyzing test audio...')
detections = classifier.classify_file('/tmp/test_audio.wav', min_confidence=0.1)

if detections:
    print(f'✅ Detected {len(detections)} bird(s):')
    for det in detections[:5]:
        print(f'  {det[\"confidence\"]*100:5.1f}%  {det.get(\"common_name\", \"Unknown\")} ({det.get(\"scientific_name\", \"N/A\")})')
else:
    print('⚠️  No birds detected in audio (this is OK if no birds were calling)')
" 2>&1
else
    echo "⚠️  Could not record test audio"
fi

echo ""
echo "Step 2: Testing Visual Classifier..."
python3 -c "
import cv2
from species_classifier import SpeciesClassifier

print('Extracting frame from video...')
cap = cv2.VideoCapture('$VIDEO_FILE')
cap.set(cv2.CAP_PROP_POS_FRAMES, 500)
ret, frame = cap.read()
cap.release()

if ret:
    print('✅ Frame extracted')
    classifier = SpeciesClassifier()
    results = classifier.classify(frame)
    print('Visual classification results:')
    for species, conf in results[:3]:
        print(f'  {conf*100:5.1f}%  {species}')
else:
    print('❌ Failed to extract frame')
" 2>&1

echo ""
echo "Step 3: Testing Combined Pipeline..."
echo "  This will run the full detection pipeline with video input"
echo "  Audio monitoring will run in background"
echo ""

# Clear old detections for clean test
mkdir -p "$LOG_DIR" "$DETECTIONS_DIR"
TODAY=$(date +%Y-%m-%d)
BACKUP_LOG="$LOG_DIR/${TODAY}_backup.json"
if [ -f "$LOG_DIR/${TODAY}.json" ]; then
    cp "$LOG_DIR/${TODAY}.json" "$BACKUP_LOG"
    echo "Backed up existing log to: $BACKUP_LOG"
fi

echo "Starting detection pipeline (30 seconds)..."
cd "$HAILO_DIR"
source setup_env.sh

# Run pipeline for 30 seconds
timeout 30 python3 basic_pipelines/bird_detection.py \
    --input "$VIDEO_FILE" \
    --use-frame \
    2>&1 | tee /tmp/pipeline_test_full.log || true

echo ""
echo "Step 4: Analyzing Results..."

python3 -c "
import json
from pathlib import Path
from datetime import datetime

log_file = Path.home() / 'bird-watcher' / 'logs' / f'{datetime.now().strftime(\"%Y-%m-%d\")}.json'

if log_file.exists():
    with open(log_file) as f:
        detections = json.load(f)
    
    print(f'✅ Total detections: {len(detections)}')
    
    # Count detections with audio
    with_audio = [d for d in detections if d.get('audio_classification')]
    print(f'   Detections with audio: {len(with_audio)}')
    
    # Show latest detection
    if detections:
        latest = detections[-1]
        print(f'')
        print(f'Latest detection:')
        print(f'  ID: {latest.get(\"id\")}')
        print(f'  Visual: {latest.get(\"visual_classification\", [{}])[0].get(\"species\", \"N/A\")}')
        if latest.get('audio_classification'):
            print(f'  Audio: {latest[\"audio_classification\"][0].get(\"species\", \"N/A\")}')
        else:
            print(f'  Audio: No matches')
    
    # Show all detections with audio
    if with_audio:
        print(f'')
        print(f'Detections with audio confirmation:')
        for det in with_audio[:5]:
            vis = det.get('visual_classification', [{}])[0].get('species', 'N/A')
            aud = det.get('audio_classification', [{}])[0].get('species', 'N/A')
            print(f'  #{det.get(\"id\")}: Visual={vis[:30]} | Audio={aud[:30]}')
else:
    print('⚠️  No log file found')
" 2>&1

echo ""
echo "=========================================="
echo "Test Complete!"
echo "=========================================="
echo ""
echo "Check results:"
echo "  - Log file: $LOG_DIR/${TODAY}.json"
echo "  - Images: $DETECTIONS_DIR/"
echo "  - Pipeline log: /tmp/pipeline_test_full.log"
echo ""
