#!/bin/bash
# E2E Test Orchestration Script
# Runs complete end-to-end tests without physical hardware

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================="
echo "  Birdwatch AI - E2E Test Suite"
echo "========================================="
echo ""

# Step 1: Check prerequisites
echo -e "${YELLOW}[1/6] Checking prerequisites...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Error: docker-compose is not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Prerequisites OK${NC}"
echo ""

# Step 2: Download test fixtures
echo -e "${YELLOW}[2/6] Setting up test fixtures...${NC}"

if [ ! -f "fixtures/videos/bird_test.mp4" ]; then
    echo "No test video found. Downloading fixtures..."
    cd fixtures
    ./download_fixtures.sh || {
        echo "Download failed, generating simple test pattern..."
        ./generate_simple_video.sh
    }
    cd ..
else
    echo "Test fixtures already exist"
fi

echo -e "${GREEN}✓ Fixtures ready${NC}"
echo ""

# Step 3: Check if model exists
echo -e "${YELLOW}[3/6] Checking bird classification model...${NC}"

if [ ! -f "../classifier/model/birds_model.tflite" ]; then
    echo -e "${YELLOW}Warning: Bird classification model not found${NC}"
    echo "Downloading model..."
    cd ../classifier/model
    ./download_model.sh || {
        echo -e "${RED}Failed to download model. Tests may fail.${NC}"
        echo "Please manually download the model before running tests."
        cd ../../tests
        exit 1
    }
    cd ../../tests
fi

echo -e "${GREEN}✓ Model ready${NC}"
echo ""

# Step 4: Clean previous test data
echo -e "${YELLOW}[4/6] Cleaning previous test data...${NC}"

docker-compose -f docker-compose.test.yml down -v 2>/dev/null || true
rm -rf data/test-snapshots/* data/test-recordings/* 2>/dev/null || true
mkdir -p data/test-snapshots data/test-recordings

echo -e "${GREEN}✓ Clean slate ready${NC}"
echo ""

# Step 5: Start test environment
echo -e "${YELLOW}[5/6] Starting test environment...${NC}"
echo "This may take a few minutes on first run..."
echo ""

docker-compose -f docker-compose.test.yml up -d --build

# Wait for services to be healthy
echo "Waiting for services to initialize..."
sleep 30

# Check if key services are running
if ! docker-compose -f docker-compose.test.yml ps | grep -q "test-frigate"; then
    echo -e "${RED}Error: Frigate failed to start${NC}"
    docker-compose -f docker-compose.test.yml logs frigate
    exit 1
fi

echo -e "${GREEN}✓ Test environment running${NC}"
echo ""

# Step 6: Run tests
echo -e "${YELLOW}[6/6] Running E2E tests...${NC}"
echo ""

# Option to run tests in container or skip
if [ "$1" = "--no-wait" ]; then
    echo "Test environment is ready!"
    echo "Run tests manually with:"
    echo "  docker-compose -f docker-compose.test.yml run --rm test-runner"
else
    # Run tests
    docker-compose -f docker-compose.test.yml run --rm test-runner

    # Check test results
    if [ $? -eq 0 ]; then
        echo ""
        echo -e "${GREEN}=========================================${NC}"
        echo -e "${GREEN}  ✓ All tests passed!${NC}"
        echo -e "${GREEN}=========================================${NC}"
        echo ""
        echo "Test report: tests/data/report.html"
    else
        echo ""
        echo -e "${RED}=========================================${NC}"
        echo -e "${RED}  ✗ Some tests failed${NC}"
        echo -e "${RED}=========================================${NC}"
        echo ""
        echo "Check test report: tests/data/report.html"
        echo "View service logs:"
        echo "  docker-compose -f docker-compose.test.yml logs <service-name>"
    fi
fi

echo ""
echo "Access test services:"
echo "  Frigate UI:    http://localhost:5052"
echo "  Web Dashboard: http://localhost:8081"
echo ""
echo "Useful commands:"
echo "  View logs:     docker-compose -f docker-compose.test.yml logs -f"
echo "  Stop tests:    docker-compose -f docker-compose.test.yml down"
echo "  Clean up:      docker-compose -f docker-compose.test.yml down -v"
echo ""
