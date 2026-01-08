#!/usr/bin/env python3
"""
Bird audio classifier using BirdNET.
Analyzes audio recordings to identify bird species by their calls.
"""

from birdnetlib import Recording
from birdnetlib.analyzer import Analyzer
from datetime import datetime
import tempfile
import subprocess
import os
import threading
import queue
import time


class AudioClassifier:
    def __init__(self, lat=47.37, lon=8.54, device='plughw:2,0'):
        """
        Initialize BirdNET analyzer.
        
        Args:
            lat: Latitude for location-based filtering (default: Zürich)
            lon: Longitude for location-based filtering (default: Zürich)
            device: ALSA device name for microphone (default: USB mic card 2)
        """
        print("Loading BirdNET model (this takes a moment)...")
        self.analyzer = Analyzer()
        self.lat = lat
        self.lon = lon
        self.device = device
        self.recent_detections = queue.Queue(maxsize=10)  # Store recent audio detections
        print("✅ BirdNET ready")
    
    def classify_file(self, audio_path, min_confidence=0.25):
        """
        Classify birds in an audio file.
        
        Args:
            audio_path: Path to WAV file
            min_confidence: Minimum confidence threshold
        
        Returns:
            List of detections with species and confidence
        """
        try:
            recording = Recording(
                self.analyzer,
                audio_path,
                lat=self.lat,
                lon=self.lon,
                date=datetime.now(),
                min_conf=min_confidence
            )
            recording.analyze()
            
            return recording.detections
        except Exception as e:
            print(f"BirdNET classification error: {e}")
            return []
    
    def record_and_classify(self, duration=3.0):
        """
        Record audio and classify it.
        
        Args:
            duration: Recording duration in seconds
        
        Returns:
            List of detections
        """
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            temp_path = f.name
        
        try:
            # Record audio
            cmd = [
                'arecord',
                '-D', self.device,
                '-d', str(int(duration)),
                '-f', 'S16_LE',
                '-r', '48000',
                '-c', '1',
                temp_path
            ]
            result = subprocess.run(cmd, capture_output=True, check=True, timeout=int(duration) + 2)
            
            if result.returncode != 0:
                print(f"Recording failed: {result.stderr.decode()}")
                return []
            
            # Classify
            detections = self.classify_file(temp_path)
            
            # Store recent detections for visual-audio fusion
            for det in detections:
                if not self.recent_detections.full():
                    self.recent_detections.put({
                        'species': det.get('common_name', ''),
                        'scientific_name': det.get('scientific_name', ''),
                        'confidence': float(det.get('confidence', 0)),
                        'timestamp': time.time()
                    })
                else:
                    # Remove oldest and add new
                    try:
                        self.recent_detections.get_nowait()
                        self.recent_detections.put({
                            'species': det.get('common_name', ''),
                            'scientific_name': det.get('scientific_name', ''),
                            'confidence': float(det.get('confidence', 0)),
                            'timestamp': time.time()
                        })
                    except queue.Empty:
                        pass
            
            return detections
        
        except subprocess.TimeoutExpired:
            print("Recording timeout")
            return []
        except Exception as e:
            print(f"Audio recording/classification error: {e}")
            return []
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def get_recent_detections(self, time_window=5.0):
        """
        Get audio detections from the last N seconds.
        
        Args:
            time_window: Time window in seconds
        
        Returns:
            List of recent detections
        """
        current_time = time.time()
        recent = []
        
        # Copy queue to list
        temp_list = []
        while not self.recent_detections.empty():
            try:
                temp_list.append(self.recent_detections.get_nowait())
            except queue.Empty:
                break
        
        # Filter by time window and put back
        for det in temp_list:
            if current_time - det['timestamp'] <= time_window:
                recent.append(det)
                if not self.recent_detections.full():
                    self.recent_detections.put(det)
        
        return recent
    
    def start_continuous_monitoring(self, interval=3.0):
        """
        Start background thread for continuous audio monitoring.
        
        Args:
            interval: Recording interval in seconds
        """
        def monitor_worker():
            while True:
                try:
                    self.record_and_classify(duration=interval)
                    time.sleep(0.1)  # Small delay between recordings
                except Exception as e:
                    print(f"Audio monitoring error: {e}")
                    time.sleep(1)
        
        thread = threading.Thread(target=monitor_worker, daemon=True)
        thread.start()
        print(f"✅ Audio monitoring started (recording every {interval}s)")
        return thread


# Quick test
if __name__ == '__main__':
    import sys
    
    print("="*60)
    print("  BirdNET Audio Classifier Test")
    print("="*60)
    print()
    
    classifier = AudioClassifier()
    
    if len(sys.argv) > 1:
        # Classify provided file
        print(f"Analyzing audio file: {sys.argv[1]}")
        detections = classifier.classify_file(sys.argv[1])
    else:
        # Record and classify
        print("Recording for 5 seconds...")
        detections = classifier.record_and_classify(duration=5)
    
    print(f"\nDetected {len(detections)} bird(s):")
    for det in detections:
        print(f"  {det['confidence']*100:5.1f}%  {det.get('common_name', 'Unknown')} ({det.get('scientific_name', 'N/A')})")
        print(f"          Time: {det.get('start_time', 0):.1f}s - {det.get('end_time', 0):.1f}s")
    
    print()
    print("="*60)
