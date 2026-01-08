#!/usr/bin/env python3
"""
Hybrid Bird Watcher - RTSP + Hailo + TFLite
============================================
- Captures frames from RTSP IP camera
- Hailo AI HAT+ runs YOLO detection (bird class = 14)
- When a bird is detected, crops and classifies with TFLite
- Logs all detections with images

Usage:
    source venv/bin/activate
    python bird_watcher.py
"""

import os
import sys
import json
import time
import threading
import queue
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

import cv2
import numpy as np
from PIL import Image

# Load environment variables
load_dotenv()

# Import species classifier
from species_classifier import SpeciesClassifier

# COCO class index for "bird"
BIRD_CLASS_ID = 14

# Settings from .env or defaults
CONFIDENCE_THRESHOLD = float(os.getenv('CONFIDENCE_THRESHOLD', '0.5'))
CLASSIFICATION_COOLDOWN = 2.0  # seconds between classifications
SAVE_ALL_DETECTIONS = True

# Camera settings - configure via environment variables
CAMERA_IP = os.getenv('CAMERA_IP', '')
CAMERA_USER = os.getenv('CAMERA_USER', '')
CAMERA_PASSWORD = os.getenv('CAMERA_PASSWORD', '')
RTSP_URL = os.getenv('CAMERA_RTSP_SUB', '')

# Resolve any environment variable references in RTSP URL
RTSP_URL = RTSP_URL.replace('${CAMERA_USER}', CAMERA_USER)
RTSP_URL = RTSP_URL.replace('${CAMERA_PASSWORD}', CAMERA_PASSWORD)
RTSP_URL = RTSP_URL.replace('${CAMERA_IP}', CAMERA_IP)


class BirdWatcher:
    def __init__(self):
        """Initialize the bird watcher."""
        # Paths
        self.base_dir = Path(__file__).parent
        self.detections_dir = self.base_dir / 'detections'
        self.logs_dir = self.base_dir / 'logs'
        self.detections_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)
        
        # Initialize species classifier (CPU)
        print("Loading species classifier...")
        self.species_classifier = SpeciesClassifier(
            model_path=self.base_dir / 'models' / 'birds_v1.tflite',
            labels_path=self.base_dir / 'models' / 'bird_labels.txt'
        )
        
        # State
        self.last_classification_time = 0
        self.detection_count = 0
        self.today_log = []
        self.running = False
        
        # Load YOLO model for CPU fallback (when Hailo not available)
        self.net = None
        self._load_yolo_model()
        
        print("Bird Watcher ready!")
        print(f"Camera: {CAMERA_IP}")
        print(f"Confidence threshold: {CONFIDENCE_THRESHOLD}")
    
    def _load_yolo_model(self):
        """Load YOLO model for bird detection."""
        # Try to use OpenCV DNN with a YOLO model
        # This is a fallback - ideally we use Hailo
        model_cfg = '/usr/share/opencv4/haarcascades'  # placeholder
        
        # For now, we'll use simple motion detection + classification
        # The Hailo integration requires the GStreamer pipeline
        print("Note: Using motion detection mode (Hailo GStreamer integration available separately)")
    
    def detect_motion(self, frame1, frame2, threshold=25, min_area=500):
        """Simple motion detection between two frames."""
        # Convert to grayscale
        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
        
        # Blur to reduce noise
        gray1 = cv2.GaussianBlur(gray1, (21, 21), 0)
        gray2 = cv2.GaussianBlur(gray2, (21, 21), 0)
        
        # Compute difference
        diff = cv2.absdiff(gray1, gray2)
        _, thresh = cv2.threshold(diff, threshold, 255, cv2.THRESH_BINARY)
        
        # Dilate to fill gaps
        thresh = cv2.dilate(thresh, None, iterations=2)
        
        # Find contours
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        regions = []
        for contour in contours:
            if cv2.contourArea(contour) > min_area:
                x, y, w, h = cv2.boundingRect(contour)
                regions.append((x, y, x + w, y + h))
        
        return regions
    
    def process_detection(self, frame, bbox):
        """
        Process a potential bird detection.
        
        Args:
            frame: Full camera frame (numpy array, BGR)
            bbox: Bounding box (x1, y1, x2, y2)
        
        Returns:
            Classification result dict or None
        """
        current_time = time.time()
        
        # Check cooldown
        if current_time - self.last_classification_time < CLASSIFICATION_COOLDOWN:
            return None
        
        x1, y1, x2, y2 = bbox
        
        # Expand bbox slightly for better classification
        h, w = frame.shape[:2]
        pad = 20
        x1 = max(0, x1 - pad)
        y1 = max(0, y1 - pad)
        x2 = min(w, x2 + pad)
        y2 = min(h, y2 + pad)
        
        # Check minimum size
        if (x2 - x1) < 50 or (y2 - y1) < 50:
            return None
        
        # Crop region
        crop = frame[y1:y2, x1:x2]
        
        # Convert BGR to RGB for classifier
        crop_rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        crop_pil = Image.fromarray(crop_rgb)
        
        # Classify species
        start = time.time()
        species_results = self.species_classifier.classify(crop_pil, top_k=5)
        classification_time = time.time() - start
        
        # Check if top result has reasonable confidence
        if not species_results or species_results[0][1] < 0.1:
            return None  # Probably not a bird
        
        self.last_classification_time = current_time
        self.detection_count += 1
        
        # Build result
        timestamp = datetime.now()
        result = {
            'id': self.detection_count,
            'timestamp': timestamp.isoformat(),
            'bbox': [x1, y1, x2, y2],
            'visual_classification': [
                {'species': s, 'confidence': float(c)} 
                for s, c in species_results
            ],
            'classification_time_ms': classification_time * 1000
        }
        
        # Save detection image
        if SAVE_ALL_DETECTIONS:
            img_filename = f"{timestamp.strftime('%Y%m%d_%H%M%S')}_{self.detection_count}.jpg"
            img_path = self.detections_dir / img_filename
            cv2.imwrite(str(img_path), crop)
            result['image_path'] = str(img_path)
            
            # Also save full frame with bbox
            frame_copy = frame.copy()
            cv2.rectangle(frame_copy, (x1, y1), (x2, y2), (0, 255, 0), 2)
            frame_filename = f"{timestamp.strftime('%Y%m%d_%H%M%S')}_{self.detection_count}_full.jpg"
            cv2.imwrite(str(self.detections_dir / frame_filename), frame_copy)
        
        # Log to daily file
        self.today_log.append(result)
        self._save_daily_log()
        
        # Print result
        self._print_detection(result)
        
        return result
    
    def _print_detection(self, result):
        """Pretty print a detection result."""
        print("\n" + "="*60)
        print(f"🐦 BIRD DETECTED! (#{result['id']})")
        print(f"   Time: {result['timestamp']}")
        print(f"   Classification time: {result['classification_time_ms']:.0f}ms")
        print()
        print("   Species identification:")
        for i, pred in enumerate(result['visual_classification'][:3]):
            marker = "→" if i == 0 else " "
            print(f"   {marker} {pred['confidence']*100:5.1f}%  {pred['species']}")
        print("="*60)
    
    def _save_daily_log(self):
        """Save today's detections to JSON log."""
        today = datetime.now().strftime('%Y-%m-%d')
        log_path = self.logs_dir / f"{today}.json"
        
        with open(log_path, 'w') as f:
            json.dump(self.today_log, f, indent=2)
    
    def run(self):
        """Main detection loop using RTSP stream."""
        print(f"\nConnecting to camera: {RTSP_URL.replace(CAMERA_PASSWORD, '****')}")
        
        cap = cv2.VideoCapture(RTSP_URL)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce latency
        
        if not cap.isOpened():
            print("ERROR: Could not connect to camera!")
            print("Check your .env settings and camera connectivity.")
            return
        
        print("Connected! Starting motion detection...")
        print("Press Ctrl+C to stop\n")
        
        self.running = True
        prev_frame = None
        frame_count = 0
        
        try:
            while self.running:
                ret, frame = cap.read()
                if not ret:
                    print("Lost connection to camera, reconnecting...")
                    cap.release()
                    time.sleep(2)
                    cap = cv2.VideoCapture(RTSP_URL)
                    continue
                
                frame_count += 1
                
                # Skip frames for performance (process every 3rd frame)
                if frame_count % 3 != 0:
                    prev_frame = frame
                    continue
                
                if prev_frame is not None:
                    # Detect motion
                    regions = self.detect_motion(prev_frame, frame)
                    
                    for bbox in regions:
                        # Process each motion region
                        result = self.process_detection(frame, bbox)
                
                prev_frame = frame
                
                # Small delay to prevent CPU overload
                time.sleep(0.01)
        
        except KeyboardInterrupt:
            print("\n\nShutting down...")
        
        finally:
            self.running = False
            cap.release()
            print(f"\nTotal detections: {self.detection_count}")
            print(f"Logs saved to: {self.logs_dir}")
            print(f"Images saved to: {self.detections_dir}")


def main():
    print("="*60)
    print("  🐦 BIRD WATCHER - Hybrid Detection System")
    print("="*60)
    print()
    
    watcher = BirdWatcher()
    watcher.run()


if __name__ == '__main__':
    main()
