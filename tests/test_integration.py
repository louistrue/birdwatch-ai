#!/usr/bin/env python3
"""
Comprehensive integration test for visual + audio detection
"""

import sys
import os
import json
import time
from pathlib import Path
from datetime import datetime

# Add paths
sys.path.insert(0, os.path.expanduser('~/bird-watcher'))
sys.path.insert(0, os.path.expanduser('~/hailo-rpi5-examples'))

def test_components():
    print("="*60)
    print("  Integration Test: Visual + Audio Detection")
    print("="*60)
    print()
    
    # Test 1: Visual classifier
    print("Test 1: Visual Classifier")
    print("-" * 60)
    try:
        from species_classifier import SpeciesClassifier
        import cv2
        
        video_file = Path.home() / 'bird-watcher' / 'tests' / 'bird_test.mp4'
        cap = cv2.VideoCapture(str(video_file))
        cap.set(cv2.CAP_PROP_POS_FRAMES, 500)
        ret, frame = cap.read()
        cap.release()
        
        if ret:
            classifier = SpeciesClassifier()
            results = classifier.classify(frame)
            print(f"✅ Visual classifier working")
            print(f"   Top result: {results[0][0]} ({results[0][1]*100:.1f}%)")
        else:
            print("❌ Failed to read video frame")
    except Exception as e:
        print(f"❌ Visual classifier error: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    
    # Test 2: Audio classifier
    print("Test 2: Audio Classifier")
    print("-" * 60)
    try:
        from audio_classifier import AudioClassifier
        
        classifier = AudioClassifier()
        print("✅ Audio classifier initialized")
        print(f"   Device: {classifier.device}")
        
        # Test recording (quick 2 second test)
        print("   Testing recording...")
        detections = classifier.record_and_classify(duration=2)
        print(f"   Recorded and analyzed: {len(detections)} detections")
        
    except Exception as e:
        print(f"❌ Audio classifier error: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    
    # Test 3: Combined detection structure
    print("Test 3: Detection Result Structure")
    print("-" * 60)
    
    sample_result = {
        'id': 1,
        'timestamp': datetime.now().isoformat(),
        'detection_label': 'bird',
        'detection_confidence': 0.85,
        'visual_classification': [
            {'species': 'Cyanocitta cristata (Blue Jay)', 'confidence': 0.95}
        ],
        'audio_classification': [
            {
                'species': 'Blue Jay',
                'scientific_name': 'Cyanocitta cristata',
                'confidence': 0.78
            }
        ]
    }
    
    print("✅ Sample detection structure:")
    print(json.dumps(sample_result, indent=2))
    
    print()
    
    # Test 4: Check log file format
    print("Test 4: Log File Format")
    print("-" * 60)
    
    log_dir = Path.home() / 'bird-watcher' / 'logs'
    today = datetime.now().strftime('%Y-%m-%d')
    log_file = log_dir / f"{today}.json"
    
    if log_file.exists():
        with open(log_file) as f:
            detections = json.load(f)
        
        print(f"✅ Log file exists: {len(detections)} detections")
        
        # Check structure
        if detections:
            latest = detections[-1]
            has_visual = 'visual_classification' in latest
            has_audio = 'audio_classification' in latest
            
            print(f"   Latest detection:")
            print(f"     Has visual: {has_visual}")
            print(f"     Has audio: {has_audio}")
            
            if has_audio and latest['audio_classification']:
                print(f"     Audio detections: {len(latest['audio_classification'])}")
    else:
        print("⚠️  No log file yet (run pipeline to generate)")
    
    print()
    print("="*60)
    print("Integration test complete!")
    print("="*60)

if __name__ == '__main__':
    test_components()
