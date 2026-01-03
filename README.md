# Hybrid AI Bird Watcher

A comprehensive bird identification system combining visual detection (Frigate + TFLite) with audio recognition (BirdNET) running on Raspberry Pi 5. Perfect for monitoring garden birds in Switzerland and beyond.

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  OUTDOORS                           │  INDOORS                  │
│                                     │                           │
│  ┌─────────────┐                    │  ┌─────────────────────┐  │
│  │ IP Camera   │ ════ WiFi ════════════▶│  Raspberry Pi 5     │  │
│  │ (RTSP)      │                    │  │                     │  │
│  └─────────────┘                    │  │  ┌───────────────┐  │  │
│                                     │  │  │ Frigate       │  │  │
│  ┌─────────────┐                    │  │  │ (detection)   │  │  │
│  │ Bird Feeder │                    │  │  └───────┬───────┘  │  │
│  └─────────────┘                    │  │          │          │  │
│                                     │  │          ▼          │  │
│                                     │  │  ┌───────────────┐  │  │
│                                     │  │  │ Bird Classifier│  │  │
│                                     │  │  │ (TFLite)      │  │  │
│                                     │  │  └───────┬───────┘  │  │
│                                     │  │          │          │  │
│                                     │  │          ▼          │  │
│  ┌─────────────┐                    │  │  ┌───────────────┐  │  │
│  │ USB Mic     │ ◀── Window ───────────│  │ BirdNET-Pi    │  │  │
│  │ (optional)  │                    │  │  │ (audio ID)    │  │  │
│  └─────────────┘                    │  │  └───────┬───────┘  │  │
│                                     │  │          │          │  │
│                                     │  │          ▼          │  │
│                                     │  │  ┌───────────────┐  │  │
│                                     │  │  │ Web Dashboard │  │  │
│                                     │  │  │ + Database    │  │  │
│                                     │  │  └───────────────┘  │  │
│                                     │  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Features

- **Visual Detection**: Motion-triggered bird detection using Frigate NVR
- **Species Classification**: TensorFlow Lite models for bird species identification
- **Audio Recognition**: Optional BirdNET integration for call identification
- **Correlation Engine**: Matches visual and audio detections for high-confidence sightings
- **Web Dashboard**: Real-time monitoring and statistics
- **Swiss Bird Species**: Pre-configured for common Swiss garden birds
- **eBird Export**: Export sightings to eBird-compatible format
- **Daily Digest**: Automated daily summary of bird activity

## Hardware Requirements

### Required
- Raspberry Pi 5 (2GB+ RAM)
- MicroSD card (32GB+) or USB SSD (recommended)
- Outdoor IP camera with RTSP support
- Power supply for Pi

### Recommended
- Reolink RLC-510A or Tapo C320WS camera
- USB microphone (e.g., Fifine K669) for audio detection
- Coral USB Accelerator for faster inference (optional)
- USB SSD for reliable storage

### Camera Requirements
- RTSP streaming support (essential)
- 1080p minimum resolution
- WiFi with good range
- Night vision
- Weather sealing (IP65+)

## Quick Start

### 1. Initial Setup

```bash
# Clone the repository
git clone <repository-url>
cd birdwatch-ai

# Copy environment template
cp .env.example .env

# Edit .env with your camera details
nano .env
```

### 2. Configure Camera Settings

Edit `.env` file:

```bash
# Update with your camera's IP and credentials
CAMERA_IP=192.168.1.100
CAMERA_USER=admin
CAMERA_PASSWORD=your_camera_password
```

### 3. Download Bird Classification Model

The system uses the Google AIY Vision Bird Classifier (~965 species):

```bash
cd classifier/model
./download_model.sh
```

This downloads:
- `birds_model.tflite` - MobileNet V2 bird classifier (~4MB)
- `labels.txt` - Species labels for ~965 bird species

**Manual download** (if script fails):
```bash
# Model
wget -O birds_model.tflite https://storage.googleapis.com/tfhub-lite-models/google/lite-model/aiy/vision/classifier/birds_V1/3.tflite

# Labels
wget -O labels.txt https://raw.githubusercontent.com/google-coral/test_data/master/inat_bird_labels.txt
```

**Test the model:**
```bash
python3 test_model.py
cd ../..
```

See `classifier/model/README.md` for detailed model information.

### 4. Configure Frigate

Edit `frigate/config.yml`:
- Update RTSP URLs with your camera credentials
- Adjust detection zones to focus on your feeder area
- Tune sensitivity settings

### 5. Launch the System

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check service status
docker-compose ps
```

### 6. Access the Dashboard

Open your browser:
- **Bird Watcher Dashboard**: http://localhost:8080
- **Frigate NVR**: http://localhost:5000

## Project Structure

```
birdwatch-ai/
├── docker-compose.yml          # Main orchestration
├── .env.example                # Configuration template
├── frigate/
│   └── config.yml             # Frigate camera configuration
├── classifier/
│   ├── classifier.py          # Visual classification service
│   ├── model/                 # TFLite models directory
│   ├── Dockerfile
│   └── requirements.txt
├── correlator/
│   ├── correlate.py           # Audio/visual correlation
│   ├── Dockerfile
│   └── requirements.txt
├── web/
│   ├── app.py                 # Web dashboard
│   ├── templates/
│   │   └── index.html
│   ├── Dockerfile
│   └── requirements.txt
├── database/
│   └── init.sql               # Database schema
├── data/
│   ├── snapshots/             # Bird snapshots
│   ├── recordings/            # Video recordings
│   └── postgres/              # Database files
├── mosquitto/
│   └── config/                # MQTT broker config
└── scripts/
    ├── daily_digest.py        # Daily summary generator
    └── export_ebird.py        # eBird export tool
```

## Services

### Frigate (Port 5000)
- Motion detection and recording
- RTSP stream processing
- Snapshot generation
- Built-in web UI

### Bird Classifier
- Watches for new snapshots
- Runs TFLite inference
- Publishes detections via MQTT
- Stores results in database

### Correlator
- Listens for visual and audio detections
- Matches species within time window
- Creates high-confidence sightings

### Web Dashboard (Port 8080)
- Real-time sighting display
- Daily statistics
- Species breakdown
- Recent detections

### Database (PostgreSQL)
- Stores all detections
- Tracks daily statistics
- Swiss bird species catalog

### MQTT Broker (Port 1883)
- Inter-service communication
- Event publishing

## BirdNET Integration (Optional)

For audio bird identification:

### Install BirdNET-Pi

```bash
# On the same Raspberry Pi or separate device
git clone https://github.com/mcguirepr89/BirdNET-Pi.git
cd BirdNET-Pi
./install.sh
```

### Configure BirdNET Bridge

Create a simple bridge to publish BirdNET detections to MQTT:

```python
# Save as birdnet_bridge.py
import paho.mqtt.client as mqtt
import requests
import json
import time

BIRDNET_URL = "http://localhost:8000"
MQTT_HOST = "localhost"
MQTT_TOPIC = "birdwatch/audio/detection"

# Poll BirdNET API and publish to MQTT
# See BirdNET-Pi API documentation
```

## Utility Scripts

### Daily Digest

Generate a summary of today's bird activity:

```bash
# Run manually
docker-compose exec web python /app/scripts/daily_digest.py

# Or set up a cron job on the host
0 20 * * * docker-compose -f /home/pi/birdwatch-ai/docker-compose.yml exec -T web python /app/scripts/daily_digest.py
```

### eBird Export

Export sightings to eBird-compatible CSV:

```bash
# Export last 7 days
docker-compose exec web python /app/scripts/export_ebird.py --days 7

# Export specific date range
docker-compose exec web python /app/scripts/export_ebird.py --start-date 2024-01-01 --end-date 2024-01-31
```

## Configuration

### Detection Sensitivity

Edit `frigate/config.yml`:

```yaml
motion:
  threshold: 30        # Lower = more sensitive
  contour_area: 50     # Minimum motion area

objects:
  filters:
    bird:
      min_area: 500        # Minimum bird size
      min_score: 0.5       # Detection confidence
      threshold: 0.7       # Classification threshold
```

### Classification Confidence

Edit `.env`:

```bash
CONFIDENCE_THRESHOLD=0.6    # Minimum confidence for species ID
CORRELATION_WINDOW=30       # Seconds to match audio/visual
```

### Detection Zones

Edit `frigate/config.yml` to focus on your bird feeder:

```yaml
zones:
  feeder:
    coordinates: 400,300,800,300,800,600,400,600  # Adjust to your camera view
```

## Swiss Bird Species

The system comes pre-configured with common Swiss garden birds:

- Kohlmeise (Great Tit)
- Blaumeise (Eurasian Blue Tit)
- Haussperling (House Sparrow)
- Amsel (Common Blackbird)
- Rotkehlchen (European Robin)
- Buchfink (Common Chaffinch)
- Grünfink (European Greenfinch)
- Elster (Eurasian Magpie)
- Ringeltaube (Common Wood Pigeon)
- Buntspecht (Great Spotted Woodpecker)

And 5 more species. See `database/init.sql` for the full list.

## Troubleshooting

### Camera Not Detected

1. Verify camera is on same network
2. Test RTSP URL with VLC: `vlc rtsp://user:pass@ip:554/stream1`
3. Check firewall settings
4. Verify RTSP port (usually 554)

### No Detections

1. Check Frigate logs: `docker-compose logs frigate`
2. Adjust motion sensitivity
3. Verify detection zone covers feeder
4. Check camera view in Frigate UI

### High CPU Usage

1. Use sub-stream for detection (lower resolution)
2. Reduce detection FPS
3. Consider Coral USB Accelerator
4. Disable recording if not needed

### False Positives

1. Increase `min_area` in bird filter
2. Adjust motion `threshold`
3. Refine detection zones
4. Increase `min_score`

### Database Connection Issues

```bash
# Check database status
docker-compose ps database

# View database logs
docker-compose logs database

# Reset database (caution: loses data)
docker-compose down
rm -rf data/postgres
docker-compose up -d
```

## Performance Optimization

### Pi 5 with 2GB RAM

```yaml
# In docker-compose.yml, add memory limits:
services:
  frigate:
    mem_limit: 768m
  classifier:
    mem_limit: 512m
```

### Use USB SSD

```bash
# Move data directory to SSD
sudo mkdir /mnt/ssd/birdwatch-data
# Update docker-compose.yml volume paths
```

### Enable Swap

```bash
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# Set CONF_SWAPSIZE=2048
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

## Advanced Features

### Time-Lapse Generation

```bash
# Generate daily time-lapse from recordings
# See Frigate documentation for timelapse feature
```

### Custom Species Training

Train a custom TFLite model on your local bird species:

1. Collect images of birds at your feeder
2. Label them with species names
3. Fine-tune an existing model
4. Convert to TFLite
5. Replace `classifier/model/birds_model.tflite`

### Email Notifications

Add email alerts for rare species:

```python
# Add to correlator/correlate.py
import smtplib

RARE_SPECIES = ['Great Spotted Woodpecker', 'European Goldfinch']

if bird['common_name'] in RARE_SPECIES:
    send_email(f"Rare bird spotted: {bird['common_name']}")
```

## Maintenance

### Update Services

```bash
# Pull latest images
docker-compose pull

# Restart services
docker-compose down
docker-compose up -d
```

### Backup Data

```bash
# Backup database
docker-compose exec database pg_dump -U birdwatch birdwatch > backup.sql

# Backup recordings and snapshots
tar -czf data_backup.tar.gz data/snapshots data/recordings
```

### Clean Old Data

```bash
# Clean recordings older than 7 days (Frigate does this automatically)
# Clean snapshots older than 30 days
find data/snapshots -type f -mtime +30 -delete
```

## Testing

### E2E Testing (No Hardware Required!)

You can test the **entire system** without any physical hardware:

```bash
cd tests
./run_e2e_tests.sh
```

This simulates:
- RTSP camera feed (using FFmpeg)
- Audio detections (mock BirdNET)
- Complete pipeline (Frigate → Classifier → Database → Dashboard)

See [tests/README.md](tests/README.md) for complete testing guide.

Benefits:
- ✅ Test before buying hardware
- ✅ Validate configuration changes
- ✅ CI/CD integration
- ✅ Rapid development iteration

## Resources

- [Frigate Documentation](https://frigate.video/)
- [BirdNET-Pi](https://github.com/mcguirepr89/BirdNET-Pi)
- [TensorFlow Lite](https://www.tensorflow.org/lite)
- [eBird](https://ebird.org/)
- [Swiss Bird Species](https://www.vogelwarte.ch/)

## License

MIT License - See LICENSE file for details

## Contributing

Contributions welcome! Please open an issue or submit a pull request.

## Acknowledgments

- Frigate NVR team
- BirdNET developers
- TensorFlow team
- Swiss Ornithological Institute

---

Happy bird watching! 🐦
