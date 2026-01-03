# Bird Watcher - Step-by-Step Setup Guide

This guide walks you through setting up the Hybrid AI Bird Watcher from scratch on a Raspberry Pi 5.

## Prerequisites Checklist

- [ ] Raspberry Pi 5 (2GB+ RAM)
- [ ] MicroSD card (32GB+) or USB SSD
- [ ] Outdoor IP camera with RTSP support
- [ ] Camera mounted with view of bird feeder
- [ ] Camera connected to WiFi
- [ ] Pi connected to network (WiFi or Ethernet)

## Phase 1: Raspberry Pi Setup

### 1.1 Flash Raspberry Pi OS

```bash
# On your computer:
# 1. Download Raspberry Pi Imager: https://www.raspberrypi.com/software/
# 2. Flash Raspberry Pi OS Lite (64-bit) to SD card
# 3. Enable SSH in advanced options
# 4. Set username and password
# 5. Configure WiFi if needed
```

### 1.2 Initial Pi Configuration

```bash
# SSH into your Pi
ssh pi@raspberrypi.local

# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y git docker.io docker-compose python3-pip

# Add user to docker group
sudo usermod -aG docker $USER

# Log out and back in for group changes to take effect
exit
ssh pi@raspberrypi.local

# Verify docker works
docker ps
```

### 1.3 Optimize for Performance

```bash
# Increase swap (helpful for 2GB Pi)
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# Change CONF_SWAPSIZE to 2048
sudo dphys-swapfile setup
sudo dphys-swapfile swapon

# Enable memory cgroup (required by Frigate)
sudo nano /boot/cmdline.txt
# Add to end of line: cgroup_memory=1 cgroup_enable=memory

# Reboot
sudo reboot
```

## Phase 2: Camera Setup

### 2.1 Install and Position Camera

1. Mount camera with clear view of bird feeder
2. Connect power
3. Connect to WiFi via camera's app
4. Note camera's IP address (e.g., from router admin page)

### 2.2 Find RTSP URL

**Common RTSP URL formats:**

**Reolink:**
```
rtsp://admin:password@192.168.1.100:554/h264Preview_01_main  (main stream)
rtsp://admin:password@192.168.1.100:554/h264Preview_01_sub   (sub stream)
```

**Tapo:**
```
rtsp://admin:password@192.168.1.100:554/stream1  (main)
rtsp://admin:password@192.168.1.100:554/stream2  (sub)
```

**Hikvision:**
```
rtsp://admin:password@192.168.1.100:554/Streaming/Channels/101
rtsp://admin:password@192.168.1.100:554/Streaming/Channels/102
```

**Test RTSP URL:**

```bash
# Install VLC on your computer
# Open Network Stream: Media > Open Network Stream
# Enter: rtsp://admin:password@192.168.1.100:554/stream1
# If you see video, the URL is correct!
```

### 2.3 Configure for Best Performance

In your camera settings:
- Enable continuous recording
- Set main stream to 2K or 1080p
- Set sub stream to 640x480 or 720p
- Enable night vision
- Disable motion detection in camera (Frigate will handle this)

## Phase 3: Install Bird Watcher

### 3.1 Clone Repository

```bash
# SSH into Pi
ssh pi@raspberrypi.local

# Clone the project
cd ~
git clone <your-repo-url> birdwatch-ai
cd birdwatch-ai
```

### 3.2 Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env
```

**Update these values in .env:**

```bash
# Database
DB_PASSWORD=your_secure_password_here

# Camera details
CAMERA_IP=192.168.1.100
CAMERA_USER=admin
CAMERA_PASSWORD=your_camera_password

# These will be auto-generated from above
CAMERA_RTSP_MAIN=rtsp://admin:your_camera_password@192.168.1.100:554/stream1
CAMERA_RTSP_SUB=rtsp://admin:your_camera_password@192.168.1.100:554/stream2

# Classification
CONFIDENCE_THRESHOLD=0.6
CORRELATION_WINDOW=30
```

### 3.3 Configure Frigate Camera

```bash
nano frigate/config.yml
```

**Update camera section:**

```yaml
cameras:
  garden_feeder:
    enabled: true
    ffmpeg:
      inputs:
        - path: rtsp://admin:PASSWORD@IP:554/stream1  # Update with your RTSP URL
          input_args: preset-rtsp-restream
          roles:
            - record
        - path: rtsp://admin:PASSWORD@IP:554/stream2  # Update with your RTSP URL
          input_args: preset-rtsp-restream
          roles:
            - detect
```

### 3.4 Set Up Detection Zone

You'll need to adjust the zone coordinates after seeing your camera view:

1. Start Frigate (we'll do this next)
2. Open http://your-pi-ip:5000
3. View your camera feed
4. Note the coordinates of your bird feeder
5. Update the zone in `frigate/config.yml`

## Phase 4: Download Bird Classification Model

### Recommended: Google AIY Vision Bird Classifier

Download the model using the provided script:

```bash
cd ~/birdwatch-ai/classifier/model

# Run download script
./download_model.sh
```

This downloads:
- **birds_model.tflite** - Google AIY bird classifier (~4MB)
- **labels.txt** - Species labels for ~965 bird species

### Manual Download (if script fails)

If the automatic download doesn't work:

```bash
cd ~/birdwatch-ai/classifier/model

# Download model
wget -O birds_model.tflite \
  https://storage.googleapis.com/tfhub-lite-models/google/lite-model/aiy/vision/classifier/birds_V1/3.tflite

# Download labels
wget -O labels.txt \
  https://raw.githubusercontent.com/google-coral/test_data/master/inat_bird_labels.txt
```

Or use curl:
```bash
curl -L -o birds_model.tflite \
  https://storage.googleapis.com/tfhub-lite-models/google/lite-model/aiy/vision/classifier/birds_V1/3.tflite

curl -L -o labels.txt \
  https://raw.githubusercontent.com/google-coral/test_data/master/inat_bird_labels.txt
```

### Test the Model

Verify the model works:

```bash
python3 test_model.py
```

Expected output:
- Model loaded successfully
- Input shape: [1, 224, 224, 3]
- Output shape: [1, 965]
- Sample predictions shown

### Option: Start Without Classification

For initial testing, you can skip classification:

```bash
# Comment out the classifier service in docker-compose.yml
nano ~/birdwatch-ai/docker-compose.yml
# Add # before each line in the classifier: section
```

**Note**: Without classification, you'll only get generic "bird" detections from Frigate.

## Phase 5: Launch System

### 5.1 First Launch

```bash
cd ~/birdwatch-ai

# Pull Docker images (this may take 10-20 minutes)
docker-compose pull

# Start services
docker-compose up -d

# Watch logs
docker-compose logs -f
```

Press `Ctrl+C` to stop watching logs.

### 5.2 Verify Services

```bash
# Check all services are running
docker-compose ps

# Should see:
# - mosquitto (running)
# - frigate (running)
# - database (running)
# - classifier (running, if enabled)
# - correlator (running)
# - web (running)
```

### 5.3 Access Interfaces

Open in your browser:

**Frigate NVR:**
```
http://raspberrypi.local:5000
or
http://192.168.1.xxx:5000
```

**Bird Watcher Dashboard:**
```
http://raspberrypi.local:8080
or
http://192.168.1.xxx:8080
```

## Phase 6: Configure Detection

### 6.1 Tune Detection Zone

1. Open Frigate: http://your-pi:5000
2. View your camera feed
3. Identify bird feeder position
4. Note coordinates (you can use browser dev tools to hover and see pixel positions)

```bash
nano frigate/config.yml
```

Update zone:
```yaml
zones:
  feeder:
    coordinates: 400,300,800,300,800,600,400,600  # Update these!
```

Restart Frigate:
```bash
docker-compose restart frigate
```

### 6.2 Adjust Sensitivity

If too many false detections:
```yaml
motion:
  threshold: 35        # Increase (less sensitive)
  contour_area: 100    # Increase (larger objects only)

objects:
  filters:
    bird:
      min_area: 1000   # Increase (larger birds only)
      min_score: 0.6   # Increase (more confident)
```

If missing birds:
```yaml
motion:
  threshold: 25        # Decrease (more sensitive)
  contour_area: 30     # Decrease (smaller objects)

objects:
  filters:
    bird:
      min_area: 300    # Decrease (smaller birds)
      min_score: 0.4   # Decrease (less strict)
```

Restart after changes:
```bash
docker-compose restart frigate
```

## Phase 7: Optional - BirdNET Audio

### 7.1 Install BirdNET-Pi

BirdNET can run on the same Pi or a separate one:

```bash
# On your Pi
cd ~
git clone https://github.com/mcguirepr89/BirdNET-Pi.git
cd BirdNET-Pi
./install.sh

# Follow prompts
# Access BirdNET web UI on port 8000
```

### 7.2 Connect USB Microphone

1. Plug in USB microphone
2. Position near window facing garden
3. Configure in BirdNET settings

### 7.3 Bridge BirdNET to Bird Watcher

Create a simple bridge script to publish BirdNET detections to MQTT:

```python
# This is a future enhancement
# For now, BirdNET and visual detection work independently
```

## Phase 8: Testing

### 8.1 Test Camera Detection

1. Wave your hand in front of camera
2. Check Frigate Events (in Frigate UI)
3. Check for snapshots in `data/snapshots/`

### 8.2 Test Bird Detection

1. Wait for a real bird (or use a bird toy)
2. Check Frigate for "bird" detection
3. Check database:

```bash
docker-compose exec database psql -U birdwatch -d birdwatch -c "SELECT * FROM visual_detections ORDER BY timestamp DESC LIMIT 5;"
```

### 8.3 Test Dashboard

1. Open http://your-pi:8080
2. Should see recent detections
3. Check Today's Visitors section

## Troubleshooting

### Camera Not Connecting

```bash
# Test RTSP URL from Pi
docker run --rm -it linuxserver/ffmpeg \
  -rtsp_transport tcp \
  -i "rtsp://admin:password@192.168.1.100:554/stream1" \
  -frames:v 1 -f image2 test.jpg
```

### High CPU Usage

```bash
# Check CPU usage
htop

# Reduce Frigate FPS
nano frigate/config.yml
# Set fps: 3 under detect:

docker-compose restart frigate
```

### Out of Memory

```bash
# Add swap space (if not done already)
# See Phase 1.3

# Or add memory limits
nano docker-compose.yml
# Add under each service:
    mem_limit: 512m
```

### Database Issues

```bash
# Reset database
docker-compose down
sudo rm -rf data/postgres
docker-compose up -d database
```

## Daily Usage

### View Dashboard

```
http://your-pi:8080
```

### Generate Daily Digest

```bash
docker-compose exec web python /app/../scripts/daily_digest.py
```

### Export to eBird

```bash
docker-compose exec web python /app/../scripts/export_ebird.py --days 7
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f classifier
```

### Restart Services

```bash
# All services
docker-compose restart

# Specific service
docker-compose restart frigate
```

## Maintenance

### Weekly

- Check disk space: `df -h`
- Review detection accuracy
- Clean old snapshots: `find data/snapshots -mtime +30 -delete`

### Monthly

- Update Docker images: `docker-compose pull && docker-compose up -d`
- Backup database: `docker-compose exec database pg_dump -U birdwatch > backup.sql`
- Review and tune detection settings

## Next Steps

1. Fine-tune detection zones for best coverage
2. Train custom model on your local bird species
3. Set up automated daily digest emails
4. Add BirdNET for audio correlation
5. Create custom alerts for rare species
6. Share your findings on eBird!

## Getting Help

- Check logs: `docker-compose logs -f`
- Frigate docs: https://frigate.video/
- Open an issue on GitHub
- Join bird watching communities

---

Happy bird watching! 🐦
