#!/bin/bash
# Download Google AIY Bird Classifier Model and Labels
# Run this script to download the model and labels for the bird classifier

set -e

echo "=========================================="
echo "Bird Classifier Model Download Script"
echo "=========================================="
echo ""

# Create model directory if it doesn't exist
mkdir -p "$(dirname "$0")"
cd "$(dirname "$0")"

# Model URL (version 3 - latest)
MODEL_URL="https://github.com/google-coral/test_data/raw/master/birds_v1.tflite"
MODEL_FILE="birds_model.tflite"

# Labels URL
LABELS_URL="https://raw.githubusercontent.com/google-coral/test_data/master/inat_bird_labels.txt"
LABELS_FILE="labels.txt"

# Download model
echo "Downloading bird classification model..."
echo "URL: $MODEL_URL"
if command -v wget &> /dev/null; then
    wget -O "$MODEL_FILE" "$MODEL_URL"
elif command -v curl &> /dev/null; then
    curl -L -o "$MODEL_FILE" "$MODEL_URL"
else
    echo "Error: Neither wget nor curl is available. Please install one of them."
    exit 1
fi

echo "✓ Model downloaded: $MODEL_FILE"
MODEL_SIZE=$(du -h "$MODEL_FILE" | cut -f1)
echo "  Size: $MODEL_SIZE"
echo ""

# Download labels
echo "Downloading bird species labels..."
echo "URL: $LABELS_URL"
if command -v wget &> /dev/null; then
    wget -O "$LABELS_FILE" "$LABELS_URL"
elif command -v curl &> /dev/null; then
    curl -L -o "$LABELS_FILE" "$LABELS_URL"
else
    echo "Error: Neither wget nor curl is available."
    exit 1
fi

echo "✓ Labels downloaded: $LABELS_FILE"
LABEL_COUNT=$(wc -l < "$LABELS_FILE")
echo "  Species count: $LABEL_COUNT"
echo ""

# Verify files
echo "Verifying downloads..."
if [ -f "$MODEL_FILE" ] && [ -s "$MODEL_FILE" ]; then
    echo "✓ Model file exists and is not empty"
else
    echo "✗ Model file is missing or empty"
    exit 1
fi

if [ -f "$LABELS_FILE" ] && [ -s "$LABELS_FILE" ]; then
    echo "✓ Labels file exists and is not empty"
else
    echo "✗ Labels file is missing or empty"
    exit 1
fi

echo ""
echo "=========================================="
echo "Download Complete!"
echo "=========================================="
echo ""
echo "Files downloaded:"
echo "  - $MODEL_FILE ($MODEL_SIZE)"
echo "  - $LABELS_FILE ($LABEL_COUNT species)"
echo ""
echo "Model details:"
echo "  - Model: Google AIY Vision Classifier Birds V1"
echo "  - Architecture: MobileNet V2"
echo "  - Dataset: iNaturalist birds (subset)"
echo "  - Species: ~965 bird species"
echo "  - Input: 224x224 RGB image"
echo "  - Format: TensorFlow Lite (quantized)"
echo ""
echo "Next steps:"
echo "  1. Test the model: python3 test_model.py"
echo "  2. Start the bird watcher: docker-compose up -d"
echo ""
