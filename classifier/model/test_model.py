#!/usr/bin/env python3
"""
Test the bird classification model
Verifies that the model is properly downloaded and can run inference
"""

import os
import sys
import numpy as np
from PIL import Image

try:
    import tflite_runtime.interpreter as tflite
    print("Using tflite_runtime")
except ImportError:
    try:
        import tensorflow.lite as tflite
        print("Using tensorflow.lite")
    except ImportError:
        print("Error: Neither tflite_runtime nor tensorflow is installed")
        print("Install with: pip install tflite-runtime or pip install tensorflow")
        sys.exit(1)

# Paths
MODEL_PATH = os.path.join(os.path.dirname(__file__), 'birds_model.tflite')
LABELS_PATH = os.path.join(os.path.dirname(__file__), 'labels.txt')

def load_labels(filename):
    """Load labels from file"""
    if not os.path.exists(filename):
        print(f"Warning: Labels file not found: {filename}")
        return []

    with open(filename, 'r') as f:
        labels = [line.strip() for line in f.readlines()]
    return labels

def test_model():
    """Test the bird classification model"""
    print("=" * 60)
    print("Bird Classifier Model Test")
    print("=" * 60)
    print()

    # Check if model exists
    if not os.path.exists(MODEL_PATH):
        print(f"✗ Model file not found: {MODEL_PATH}")
        print()
        print("Please download the model first:")
        print("  ./download_model.sh")
        print()
        print("Or manually download from:")
        print("  https://storage.googleapis.com/tfhub-lite-models/google/lite-model/aiy/vision/classifier/birds_V1/3.tflite")
        return False

    print(f"✓ Model file found: {MODEL_PATH}")
    model_size = os.path.getsize(MODEL_PATH) / (1024 * 1024)
    print(f"  Size: {model_size:.2f} MB")
    print()

    # Load labels
    labels = load_labels(LABELS_PATH)
    if labels:
        print(f"✓ Loaded {len(labels)} bird species labels")
        print(f"  First few species:")
        for label in labels[:5]:
            print(f"    - {label}")
        print()
    else:
        print("✗ Labels file not found or empty")
        print()

    # Load interpreter
    print("Loading TFLite model...")
    try:
        interpreter = tflite.Interpreter(model_path=MODEL_PATH)
        interpreter.allocate_tensors()
        print("✓ Model loaded successfully")
    except Exception as e:
        print(f"✗ Failed to load model: {e}")
        return False

    # Get input and output details
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()

    print()
    print("Model Details:")
    print(f"  Input shape: {input_details[0]['shape']}")
    print(f"  Input type: {input_details[0]['dtype']}")
    print(f"  Output shape: {output_details[0]['shape']}")
    print(f"  Output type: {output_details[0]['dtype']}")
    print()

    # Create test image
    input_shape = input_details[0]['shape']
    height, width = input_shape[1], input_shape[2]

    print(f"Creating test image ({height}x{width})...")
    test_image = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)
    test_image = np.expand_dims(test_image, axis=0)

    # Ensure correct dtype
    if input_details[0]['dtype'] == np.uint8:
        test_image = test_image.astype(np.uint8)
    else:
        test_image = test_image.astype(np.float32) / 255.0

    # Run inference
    print("Running inference...")
    try:
        interpreter.set_tensor(input_details[0]['index'], test_image)
        interpreter.invoke()
        output = interpreter.get_tensor(output_details[0]['index'])
        print("✓ Inference successful")
        print()
    except Exception as e:
        print(f"✗ Inference failed: {e}")
        return False

    # Display results
    results = np.squeeze(output)
    top_k = 3
    top_indices = np.argsort(results)[-top_k:][::-1]

    print("Top predictions (random test image):")
    for i, idx in enumerate(top_indices, 1):
        score = results[idx]
        if labels and idx < len(labels):
            label = labels[idx]
        else:
            label = f"Class {idx}"
        print(f"  {i}. {label}: {score:.4f}")
    print()

    print("=" * 60)
    print("✓ All tests passed!")
    print("=" * 60)
    print()
    print("The model is ready to use for bird classification.")
    print("Start the bird watcher with: docker-compose up -d")
    print()

    return True

if __name__ == '__main__':
    success = test_model()
    sys.exit(0 if success else 1)
