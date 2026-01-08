# BirdNET Audio Integration

## Overview

Audio classification has been integrated into the bird detection pipeline. When a bird is detected visually by Hailo YOLO, the system now checks for matching audio detections from BirdNET to confirm/enhance species identification.

## Architecture

```
Visual Detection (Hailo) → TFLite Classification → Audio Check (BirdNET) → Combined Result
```

## Components

### 1. Audio Classifier (`audio_classifier.py`)
- Uses BirdNET library for bird call recognition
- Records audio continuously in background (3-second intervals)
- Maintains a queue of recent detections (5-second window)
- USB microphone: `plughw:2,0` (Delock 20672)

### 2. Detection Pipeline Integration
- Modified `bird_detection.py` to:
  - Initialize audio classifier on startup
  - Check recent audio detections when bird is visually detected
  - Combine visual + audio results in detection log

### 3. Dashboard Updates
- Displays audio classification results alongside visual
- Shows "Audio Confirmation" section when matches found
- Color-coded: Visual (blue) vs Audio (green)

## Usage

### Start Detection Pipeline with Audio

```bash
cd ~/hailo-rpi5-examples
source setup_env.sh
python3 basic_pipelines/bird_detection.py \
    --input "rtsp://user:pass@ip:554/stream2" \
    --use-frame
```

The audio classifier will automatically start in the background.

### Test Audio Classifier Standalone

```bash
cd ~/bird-watcher
source venv/bin/activate
python3 audio_classifier.py
```

This will record 5 seconds of audio and classify it.

### Configure Audio Device

If your microphone is on a different card, edit `bird_detection.py`:

```python
self.audio_classifier = AudioClassifier(
    lat=47.37,
    lon=8.54,
    device='plughw:2,0'  # Change this to your device
)
```

Find your device:
```bash
arecord -l
```

## Detection Result Format

```json
{
  "id": 1,
  "timestamp": "2026-01-08T21:30:00",
  "detection_label": "bird",
  "detection_confidence": 0.85,
  "visual_classification": [
    {"species": "Cyanocitta cristata (Blue Jay)", "confidence": 0.95}
  ],
  "audio_classification": [
    {
      "species": "Blue Jay",
      "scientific_name": "Cyanocitta cristata",
      "confidence": 0.78
    }
  ]
}
```

## How It Works

1. **Continuous Audio Monitoring**: BirdNET records and analyzes 3-second audio clips continuously
2. **Visual Detection**: Hailo detects a bird in the video frame
3. **Visual Classification**: TFLite identifies the species from the cropped image
4. **Audio Check**: System checks recent audio detections (last 5 seconds)
5. **Fusion**: If audio matches visual, both are included in the result
6. **Logging**: Combined result saved to JSON log and displayed on dashboard

## Performance

- Audio analysis: ~1-2 seconds per 3-second clip
- Visual classification: ~70-100ms per detection
- Audio runs in background thread (non-blocking)
- Recent detections cached for quick lookup

## Troubleshooting

### No Audio Detections

1. Check microphone is detected:
   ```bash
   arecord -l
   ```

2. Test recording:
   ```bash
   arecord -D plughw:2,0 -d 5 -f S16_LE -r 48000 test.wav
   ```

3. Check BirdNET is working:
   ```bash
   python3 audio_classifier.py
   ```

### Audio Not Matching Visual

- BirdNET may detect different species than visual classifier
- Audio confidence threshold is 0.25 (adjustable)
- Some birds are silent or calls may not be captured
- This is normal - audio is supplementary confirmation

## Files Modified

- `bird-watcher/audio_classifier.py` - New audio classification module
- `hailo-rpi5-examples/basic_pipelines/bird_detection.py` - Integrated audio
- `bird-watcher/web_dashboard.py` - Statistics updated
- `bird-watcher/static/dashboard.js` - Audio display added
