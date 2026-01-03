# E2E Testing Guide

Complete end-to-end testing for the Birdwatch AI system **without any physical hardware**.

## Overview

This test suite simulates the entire bird watching pipeline:

- **Simulated RTSP Camera**: FFmpeg-based video stream (no real camera needed)
- **Mock Audio Detection**: Simulates BirdNET audio detections via MQTT
- **Full System Integration**: Tests all services working together
- **Automated Test Suite**: Comprehensive pytest-based tests

## Quick Start

### 1. Run Complete Test Suite

```bash
cd tests
./run_e2e_tests.sh
```

This will:
1. ✅ Download test fixtures (bird images/videos)
2. ✅ Verify the classification model exists
3. ✅ Start all services in Docker
4. ✅ Run automated tests
5. ✅ Generate HTML test report

### 2. View Test Results

After tests complete:

- **Test Report**: `tests/data/report.html` (open in browser)
- **Frigate UI**: http://localhost:5000
- **Web Dashboard**: http://localhost:8081

## What Gets Tested

### Core Functionality
- ✅ Database schema initialization
- ✅ All services start and are accessible
- ✅ MQTT broker connectivity
- ✅ Frigate camera detection
- ✅ Visual detection pipeline (camera → Frigate → classifier → database)
- ✅ Audio detection simulation (mock BirdNET → MQTT → database)
- ✅ Correlation engine (matching visual + audio)
- ✅ Web dashboard functionality
- ✅ Detection confidence thresholds

### Integration Points
- ✅ MQTT message flow between services
- ✅ Database writes from all services
- ✅ File system watching (Frigate snapshots)
- ✅ TFLite model inference
- ✅ API endpoints

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  E2E Test Environment (All in Docker)                   │
│                                                          │
│  ┌──────────────┐      ┌──────────────┐                 │
│  │ RTSP         │      │ Audio        │                 │
│  │ Simulator    │      │ Simulator    │                 │
│  │ (FFmpeg)     │      │ (Mock BirdNET)│                │
│  └──────┬───────┘      └──────┬───────┘                 │
│         │                     │                          │
│         │  RTSP               │  MQTT                    │
│         ▼                     ▼                          │
│  ┌──────────────┐      ┌──────────────┐                 │
│  │ Frigate NVR  │      │ Correlator   │                 │
│  │              │      │              │                 │
│  └──────┬───────┘      └──────┬───────┘                 │
│         │                     │                          │
│         │ Snapshots           │                          │
│         ▼                     │                          │
│  ┌──────────────┐             │                          │
│  │ Classifier   │─────────────┤                          │
│  │ (TFLite)     │   MQTT      │                          │
│  └──────┬───────┘             │                          │
│         │                     │                          │
│         ▼                     ▼                          │
│  ┌────────────────────────────────┐                      │
│  │     PostgreSQL Database        │                      │
│  └────────────────────────────────┘                      │
│                                                          │
│  ┌──────────────┐      ┌──────────────┐                 │
│  │ Web Dashboard│      │ Test Runner  │                 │
│  │ (Port 8081)  │      │ (pytest)     │                 │
│  └──────────────┘      └──────────────┘                 │
└─────────────────────────────────────────────────────────┘
```

## Test Fixtures

### Automatic Download

Test images and videos are automatically downloaded:

```bash
cd tests/fixtures
./download_fixtures.sh
```

This downloads public domain bird images from Wikimedia Commons:
- Great Tit
- Blue Tit
- House Sparrow
- European Robin
- Common Blackbird

### Manual Fixtures

Add your own test media:

```bash
# Add images
cp your_bird_photo.jpg tests/fixtures/images/

# Add videos
cp your_bird_video.mp4 tests/fixtures/videos/bird_test.mp4
```

### Simple Test Pattern

If you can't download real bird images:

```bash
cd tests/fixtures
./generate_simple_video.sh
```

This creates a test pattern video that generates motion for Frigate to detect (but won't classify as actual birds).

## Manual Testing

### Start Test Environment Only

```bash
cd tests
./run_e2e_tests.sh --no-wait
```

Then interact manually:

```bash
# View logs
docker-compose -f docker-compose.test.yml logs -f

# Inject test images
./inject_test_images.sh

# Access services
open http://localhost:5000  # Frigate
open http://localhost:8081  # Dashboard

# Run tests later
docker-compose -f docker-compose.test.yml run --rm test-runner
```

### Individual Service Testing

```bash
# Test database
docker-compose -f docker-compose.test.yml exec database psql -U test_user -d birdwatch_test

# Test MQTT
docker-compose -f docker-compose.test.yml exec mosquitto mosquitto_sub -t "birdwatch/#"

# Test classifier
docker-compose -f docker-compose.test.yml logs -f classifier

# Check Frigate events
docker-compose -f docker-compose.test.yml exec frigate ls -la /media/snapshots
```

### Inject Test Images

Simulate Frigate snapshot generation:

```bash
./inject_test_images.sh
```

This copies test images into the snapshots directory where the classifier watches.

## Troubleshooting

### Services Won't Start

```bash
# Check logs
docker-compose -f docker-compose.test.yml logs

# Check specific service
docker-compose -f docker-compose.test.yml logs frigate

# Restart
docker-compose -f docker-compose.test.yml restart
```

### No Detections

```bash
# Verify Frigate is receiving RTSP stream
docker-compose -f docker-compose.test.yml logs frigate | grep rtsp

# Check if snapshots are being created
docker-compose -f docker-compose.test.yml exec frigate ls /media/snapshots

# Manually inject test images
./inject_test_images.sh

# Lower detection threshold
# Edit frigate.test.yml: min_score: 0.1
docker-compose -f docker-compose.test.yml restart frigate
```

### Model Not Found

```bash
# Download the bird classification model
cd ../classifier/model
./download_model.sh
cd ../../tests
```

### Tests Timeout

Increase wait times in `test_pipeline.py`:

```python
# Increase from 60 to 120 seconds
time.sleep(120)
```

Or run services longer before testing:

```bash
# Start services
./run_e2e_tests.sh --no-wait

# Wait a few minutes
sleep 180

# Then run tests
docker-compose -f docker-compose.test.yml run --rm test-runner
```

### Database Connection Issues

```bash
# Check database is running
docker-compose -f docker-compose.test.yml ps database

# Reset database
docker-compose -f docker-compose.test.yml down -v
docker-compose -f docker-compose.test.yml up -d database

# Wait for initialization
sleep 10
```

## Configuration

### Adjust Detection Sensitivity

Edit `frigate.test.yml`:

```yaml
objects:
  filters:
    bird:
      min_score: 0.1      # Lower = more detections
      threshold: 0.3      # Lower = less filtering
```

### Adjust Audio Detection Frequency

Edit `docker-compose.test.yml`:

```yaml
audio-simulator:
  environment:
    - MIN_INTERVAL=5      # Seconds between detections
    - MAX_INTERVAL=15
```

### Adjust Classification Threshold

Edit `docker-compose.test.yml`:

```yaml
classifier:
  environment:
    - CONFIDENCE_THRESHOLD=0.3  # Lower = more classifications
```

## Cleanup

### Stop Services

```bash
docker-compose -f docker-compose.test.yml down
```

### Full Cleanup (including data)

```bash
docker-compose -f docker-compose.test.yml down -v
rm -rf data/test-snapshots/* data/test-recordings/*
```

### Remove Test Images

```bash
rm -rf fixtures/images/* fixtures/videos/*
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  e2e-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Download fixtures
        run: |
          cd tests/fixtures
          ./generate_simple_video.sh

      - name: Download model
        run: |
          cd classifier/model
          ./download_model.sh

      - name: Run E2E tests
        run: |
          cd tests
          ./run_e2e_tests.sh

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: test-report
          path: tests/data/report.html
```

## Advanced Testing

### Load Testing

```python
# tests/e2e/test_load.py
def test_concurrent_detections():
    """Test system under load"""
    # Inject 100 images simultaneously
    # Measure processing time
    pass
```

### Performance Benchmarking

```python
def test_classification_latency():
    """Measure classifier performance"""
    start = time.time()
    # Inject image and wait for DB write
    latency = time.time() - start
    assert latency < 5.0  # Should complete in 5 seconds
```

### API Testing

```python
def test_web_api():
    """Test dashboard API endpoints"""
    response = requests.get('http://web:8080/api/recent')
    assert response.status_code == 200
    data = response.json()
    assert 'detections' in data
```

## Benefits of This Approach

✅ **No Hardware Required** - Test on any machine with Docker
✅ **Fast Feedback** - Complete pipeline test in minutes
✅ **Reproducible** - Same test data every time
✅ **Portable** - Works on local dev, CI/CD, anywhere
✅ **Cost Effective** - No need to buy cameras/Pi before testing
✅ **Isolated** - Doesn't affect production data
✅ **Comprehensive** - Tests all integration points

## Next Steps

Once E2E tests pass:

1. **Deploy to real hardware** - You know the software works!
2. **Tune parameters** - Adjust thresholds based on real camera
3. **Add more tests** - Cover edge cases specific to your setup
4. **Monitor in production** - Compare to test baseline

## Resources

- [Frigate Testing Docs](https://docs.frigate.video/)
- [pytest Documentation](https://docs.pytest.org/)
- [Docker Compose Testing](https://docs.docker.com/compose/compose-file/)

---

Happy testing! 🧪🐦
