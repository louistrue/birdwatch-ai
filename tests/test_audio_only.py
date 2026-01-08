#!/usr/bin/env python3
"""
Test BirdNET audio classifier standalone
"""

import sys
import os
sys.path.insert(0, os.path.expanduser('~/bird-watcher'))

from audio_classifier import AudioClassifier
import time

def test_audio_classifier():
    print("="*60)
    print("  BirdNET Audio Classifier Test")
    print("="*60)
    print()
    
    # Initialize classifier
    print("Loading BirdNET...")
    classifier = AudioClassifier(device='plughw:2,0')
    print()
    
    # Test 1: Record and classify
    print("Test 1: Recording 5 seconds of audio...")
    print("(Make bird sounds or play bird audio near microphone)")
    print()
    
    detections = classifier.record_and_classify(duration=5)
    
    if detections:
        print(f"✅ Detected {len(detections)} bird(s):")
        for det in detections:
            print(f"  {det['confidence']*100:5.1f}%  {det.get('common_name', 'Unknown')}")
            print(f"      Scientific: {det.get('scientific_name', 'N/A')}")
            print(f"      Time: {det.get('start_time', 0):.1f}s - {det.get('end_time', 0):.1f}s")
    else:
        print("⚠️  No birds detected")
        print("   (This is OK if no birds were calling)")
    
    print()
    print("Test 2: Testing continuous monitoring...")
    print("Starting background monitoring (will run for 10 seconds)...")
    
    # Start monitoring
    thread = classifier.start_continuous_monitoring(interval=3.0)
    time.sleep(10)
    
    # Check recent detections
    recent = classifier.get_recent_detections(time_window=10.0)
    print(f"Recent detections (last 10s): {len(recent)}")
    for det in recent:
        print(f"  {det['species']}: {det['confidence']*100:.1f}%")
    
    print()
    print("="*60)
    print("Audio test complete!")
    print("="*60)

if __name__ == '__main__':
    test_audio_classifier()
