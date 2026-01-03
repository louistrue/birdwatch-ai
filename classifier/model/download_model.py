#!/usr/bin/env python3
"""
Download and convert TensorFlow Hub bird classifier to TFLite
Model: google/aiy/vision/classifier/birds_V1/1
"""

import tensorflow as tf
import tensorflow_hub as hub
import numpy as np
import os

print("TensorFlow version:", tf.__version__)
print("Downloading model from TensorFlow Hub...")

# Model URL
MODEL_URL = "https://tfhub.dev/google/aiy/vision/classifier/birds_V1/1"

# Load the model
model = hub.load(MODEL_URL)

print("Model loaded successfully!")
print("Model signature:", list(model.signatures.keys()))

# Get the serving signature
infer = model.signatures['default']
print("Input signature:", infer.structured_input_signature)
print("Output signature:", infer.structured_outputs)

# Convert to TFLite
converter = tf.lite.TFLiteConverter.from_saved_model(
    MODEL_URL,
    signature_keys=['default']
)

# Enable optimization
converter.optimizations = [tf.lite.Optimize.DEFAULT]

print("Converting to TFLite format...")
tflite_model = converter.convert()

# Save the model
output_path = 'birds_model.tflite'
with open(output_path, 'wb') as f:
    f.write(tflite_model)

print(f"Model saved to {output_path}")
print(f"Model size: {len(tflite_model) / 1024 / 1024:.2f} MB")

# Test the model
print("\nTesting TFLite model...")
interpreter = tf.lite.Interpreter(model_path=output_path)
interpreter.allocate_tensors()

input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

print("Input details:", input_details)
print("Output details:", output_details)

# Create a test image
input_shape = input_details[0]['shape']
print(f"Expected input shape: {input_shape}")

test_image = np.random.randint(0, 255, input_shape, dtype=np.uint8)
interpreter.set_tensor(input_details[0]['index'], test_image)
interpreter.invoke()
output = interpreter.get_tensor(output_details[0]['index'])

print(f"Output shape: {output.shape}")
print("Model is working correctly!")

