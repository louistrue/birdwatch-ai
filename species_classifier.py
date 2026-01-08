#!/usr/bin/env python3
"""
Bird species classifier using Google AIY Birds model on CPU.
Classifies cropped bird images into 964 species.
"""

import tensorflow as tf
import numpy as np
from PIL import Image
from pathlib import Path


class SpeciesClassifier:
    def __init__(self, model_path='models/birds_v1.tflite', labels_path='models/bird_labels.txt'):
        # Load TFLite model
        self.interpreter = tf.lite.Interpreter(model_path=str(model_path))
        self.interpreter.allocate_tensors()
        
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()
        
        # Model expects 224x224 RGB
        self.input_size = (224, 224)
        
        # Load species labels
        self.labels = self._load_labels(labels_path)
        print(f"Loaded {len(self.labels)} bird species")
    
    def _load_labels(self, labels_path):
        """Load bird species labels from file."""
        labels = {}
        with open(labels_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    # Format: "index name" e.g. "671 Passer domesticus (House Sparrow)"
                    parts = line.split(' ', 1)
                    if len(parts) == 2:
                        try:
                            idx = int(parts[0])
                            name = parts[1]
                            labels[idx] = name
                        except ValueError:
                            # If first part isn't a number, use line index
                            pass
        return labels
    
    def preprocess(self, image):
        """
        Preprocess image for the model.
        
        Args:
            image: PIL Image or numpy array (RGB)
        
        Returns:
            Preprocessed numpy array ready for inference
        """
        if isinstance(image, np.ndarray):
            image = Image.fromarray(image)
        
        # Resize to model input size
        image = image.convert('RGB')
        image = image.resize(self.input_size, Image.BILINEAR)
        
        # Check expected input type from model
        input_dtype = self.input_details[0]['dtype']
        
        if input_dtype == np.uint8:
            # Model expects uint8 [0-255]
            input_data = np.array(image, dtype=np.uint8)
        else:
            # Model expects float32 [0-1]
            input_data = np.array(image, dtype=np.float32) / 255.0
        
        # Add batch dimension
        input_data = np.expand_dims(input_data, axis=0)
        
        return input_data
    
    def classify(self, image, top_k=5, min_confidence=0.05):
        """
        Classify a bird image.
        
        Args:
            image: PIL Image or numpy array of the bird (cropped)
            top_k: Number of top predictions to return
            min_confidence: Minimum confidence threshold
        
        Returns:
            List of (species_name, confidence) tuples
        """
        # Preprocess
        input_data = self.preprocess(image)
        
        # Run inference
        self.interpreter.set_tensor(self.input_details[0]['index'], input_data)
        self.interpreter.invoke()
        
        # Get output
        output = self.interpreter.get_tensor(self.output_details[0]['index'])[0]
        
        # Handle quantized uint8 output 
        output_dtype = self.output_details[0]['dtype']
        if output_dtype == np.uint8:
            # For quantized models, convert to float and normalize
            # The max value represents highest confidence
            output = output.astype(np.float32)
            max_val = output.max()
            if max_val > 0:
                output = output / max_val  # Normalize so max = 1.0
        else:
            # Apply softmax if needed for float outputs (check if outputs sum to ~1)
            if output.sum() < 0.99 or output.sum() > 1.01:
                output = self._softmax(output)
        
        # Get top-k predictions
        top_indices = output.argsort()[-top_k:][::-1]
        
        results = []
        for idx in top_indices:
            confidence = float(output[idx])
            if confidence >= min_confidence:
                species = self.labels.get(idx, f"Unknown (ID: {idx})")
                results.append((species, confidence))
        
        return results
    
    def _softmax(self, x):
        """Apply softmax to convert logits to probabilities."""
        exp_x = np.exp(x - np.max(x))
        return exp_x / exp_x.sum()


# Quick test
if __name__ == '__main__':
    import sys
    import time
    
    classifier = SpeciesClassifier()
    
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
        image = Image.open(image_path)
        
        start = time.time()
        results = classifier.classify(image)
        elapsed = time.time() - start
        
        print(f"\nClassification completed in {elapsed*1000:.0f}ms")
        print("Results:")
        for species, confidence in results:
            print(f"  {confidence*100:5.1f}%  {species}")
    else:
        print("Usage: python species_classifier.py <image_path>")
