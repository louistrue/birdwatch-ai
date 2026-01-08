#!/usr/bin/env python3
"""
Live Bird Detection Dashboard
==============================
Flask web server for viewing live Hailo bird detections.
Access at http://raspberry-pi-ip:5000
"""

from flask import Flask, render_template, jsonify, Response, send_from_directory
from pathlib import Path
import json
import time
from datetime import datetime, timedelta
from collections import Counter
import os
import subprocess
import threading
import queue

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Disable caching

# Paths
BIRD_WATCHER_DIR = Path.home() / 'bird-watcher'
LOGS_DIR = BIRD_WATCHER_DIR / 'logs'
DETECTIONS_DIR = BIRD_WATCHER_DIR / 'detections'


def get_today_log():
    """Load today's detection log."""
    today = datetime.now().strftime('%Y-%m-%d')
    log_path = LOGS_DIR / f"{today}.json"
    if log_path.exists():
        try:
            with open(log_path, 'r') as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except:
            return []
    return []


def get_statistics():
    """Calculate detection statistics."""
    detections = get_today_log()
    if not detections:
        return {
            'total_detections': 0,
            'bird_detections': 0,
            'recent_detections': 0,
            'species_count': {}
        }
    
    # Count species and objects
    species_count = Counter()
    bird_count = 0
    
    # Recent detections (last 2 minutes)
    two_min_ago = datetime.now() - timedelta(minutes=2)
    recent_count = 0
    
    for det in detections:
        detection_label = det.get('detection_label', 'unknown')
        
        # Count by detection label
        species_count[detection_label] += 1
        
        # If it's a bird detection
        if detection_label == 'bird':
            bird_count += 1
        
        # Also count species from classification if available
        if det.get('visual_classification'):
            species = det['visual_classification'][0].get('species', 'unknown')
            if species != 'background':
                species_count[species] += 1
        
        # Check if recent
        try:
            det_time = datetime.fromisoformat(det.get('timestamp', ''))
            if det_time > two_min_ago:
                recent_count += 1
        except:
            pass
    
    return {
        'total_detections': len(detections),
        'bird_detections': bird_count,
        'recent_detections': recent_count,
        'species_count': dict(species_count.most_common(15))
    }


@app.route('/')
def dashboard():
    """Main dashboard page."""
    return render_template('dashboard.html')


@app.route('/api/detections')
def api_detections():
    """Get latest detections."""
    detections = get_today_log()
    # Return last 20 detections, most recent first
    return jsonify(detections[-20:][::-1])


@app.route('/api/stats')
def api_stats():
    """Get detection statistics."""
    return jsonify(get_statistics())


@app.route('/api/stream')
def stream():
    """Server-Sent Events stream for real-time updates."""
    def event_stream():
        last_count = 0
        while True:
            detections = get_today_log()
            current_count = len(detections)
            
            # Send update if new detections
            if current_count > last_count:
                last_count = current_count
                if detections:
                    latest = detections[-1]
                    data = {
                        'type': 'detection',
                        'data': latest,
                        'stats': get_statistics()
                    }
                    yield f"data: {json.dumps(data)}\n\n"
            
            # Send heartbeat every 5 seconds
            yield f"data: {json.dumps({'type': 'heartbeat', 'time': datetime.now().isoformat()})}\n\n"
            time.sleep(5)
    
    return Response(event_stream(), mimetype='text/event-stream')


@app.route('/images/<filename>')
def serve_image(filename):
    """Serve detection images."""
    return send_from_directory(str(DETECTIONS_DIR), filename)


@app.route('/api/latest')
def api_latest():
    """Get latest detection."""
    detections = get_today_log()
    if detections:
        return jsonify(detections[-1])
    return jsonify(None)


@app.route('/video_feed')
def video_feed():
    """MJPEG video stream from RTSP camera."""
    def generate():
        # RTSP URL from environment - no default with credentials
        rtsp_url = os.environ.get('CAMERA_RTSP_SUB', '')
        
        # GStreamer pipeline for MJPEG stream
        pipeline = (
            f'rtspsrc location="{rtsp_url}" latency=300 protocols=tcp ! '
            'rtph264depay ! h264parse ! decodebin ! '
            'videoscale ! video/x-raw,width=640,height=360 ! '
            'videoconvert ! jpegenc quality=85 ! '
            'multipartmux boundary=spionisto ! '
            'tcpclientsink host=127.0.0.1 port=9999'
        )
        
        # Start GStreamer pipeline
        process = subprocess.Popen(
            ['gst-launch-1.0', '-q'] + pipeline.split(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Read MJPEG frames
        try:
            while True:
                chunk = process.stdout.read(1024)
                if not chunk:
                    break
                yield chunk
        finally:
            process.terminate()
            process.wait()
    
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=spionisto')


@app.route('/latest_frame')
def latest_frame():
    """Serve the most recent detection frame."""
    # Find most recent full frame image
    try:
        frames = sorted(DETECTIONS_DIR.glob('*_full.jpg'), reverse=True)
        if frames:
            return send_from_directory(frames[0].parent, frames[0].name)
    except Exception as e:
        print(f"Error serving latest frame: {e}")
    
    # Return placeholder
    import cv2
    import numpy as np
    placeholder = np.zeros((360, 640, 3), dtype=np.uint8)
    cv2.putText(placeholder, "Waiting for detections...", (140, 180),
               cv2.FONT_HERSHEY_SIMPLEX, 1, (100, 100, 100), 2)
    _, jpeg = cv2.imencode('.jpg', placeholder)
    return Response(jpeg.tobytes(), mimetype='image/jpeg')


if __name__ == '__main__':
    # Ensure directories exist
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    DETECTIONS_DIR.mkdir(parents=True, exist_ok=True)
    
    print()
    print("Bird Watcher Dashboard")
    print("-" * 40)
    print(f"http://0.0.0.0:5000")
    print()
    
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
