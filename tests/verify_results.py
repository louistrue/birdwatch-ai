#!/usr/bin/env python3
"""
Verify pipeline test results
Checks detection logs, images, and dashboard connectivity
"""

import json
from pathlib import Path
from datetime import datetime
import requests

HOME = Path.home()
LOGS_DIR = HOME / 'bird-watcher' / 'logs'
DETECTIONS_DIR = HOME / 'bird-watcher' / 'detections'

def main():
    print("="*60)
    print("  Pipeline Test Results Verification")
    print("="*60)
    print()
    
    # Check log file
    today = datetime.now().strftime('%Y-%m-%d')
    log_file = LOGS_DIR / f"{today}.json"
    
    if log_file.exists():
        with open(log_file) as f:
            detections = json.load(f)
        
        print(f"✅ Detection log found: {log_file}")
        print(f"   Total detections: {len(detections)}")
        
        # Count by type
        bird_detections = [d for d in detections if d.get('detection_label') == 'bird']
        other_detections = [d for d in detections if d.get('detection_label') != 'bird']
        
        print(f"   Bird detections: {len(bird_detections)}")
        print(f"   Other detections: {len(other_detections)}")
        
        # Show species breakdown
        species_count = {}
        for det in bird_detections:
            if det.get('visual_classification'):
                species = det['visual_classification'][0].get('species', 'unknown')
                species_count[species] = species_count.get(species, 0) + 1
        
        if species_count:
            print(f"\n   Species detected:")
            for species, count in sorted(species_count.items(), key=lambda x: x[1], reverse=True):
                print(f"     - {species}: {count}")
        
        # Show latest detection
        if detections:
            latest = detections[-1]
            print(f"\n   Latest detection:")
            print(f"     ID: {latest.get('id')}")
            print(f"     Time: {latest.get('timestamp')}")
            print(f"     Label: {latest.get('detection_label', 'N/A')}")
            print(f"     Confidence: {latest.get('detection_confidence', 0)*100:.1f}%")
            if latest.get('visual_classification'):
                top = latest['visual_classification'][0]
                print(f"     Species: {top.get('species')} ({top.get('confidence', 0)*100:.1f}%)")
    else:
        print(f"⚠️  No log file found: {log_file}")
    
    print()
    
    # Check detection images
    image_files = list(DETECTIONS_DIR.glob('*.jpg'))
    print(f"✅ Detection images: {len(image_files)}")
    if image_files:
        print(f"   Latest: {sorted(image_files, key=lambda x: x.stat().st_mtime)[-1].name}")
    
    print()
    
    # Check dashboard
    try:
        response = requests.get('http://localhost:5000/api/stats', timeout=2)
        if response.status_code == 200:
            stats = response.json()
            print(f"✅ Dashboard API responding")
            print(f"   Total detections: {stats.get('total_detections', 0)}")
            print(f"   Bird detections: {stats.get('bird_detections', 0)}")
            print(f"   Recent (2 min): {stats.get('recent_detections', 0)}")
        else:
            print(f"⚠️  Dashboard API returned status {response.status_code}")
    except Exception as e:
        print(f"⚠️  Dashboard not accessible: {e}")
    
    print()
    print("="*60)
    print("Verification complete!")
    print("="*60)

if __name__ == '__main__':
    main()
