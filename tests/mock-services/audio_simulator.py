#!/usr/bin/env python3
"""
Mock Audio Detection Service
Simulates BirdNET-Pi audio detections for E2E testing
"""

import os
import time
import json
import random
import logging
from datetime import datetime
import paho.mqtt.client as mqtt

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test bird species to simulate
TEST_SPECIES = [
    {"common_name": "Great Tit", "scientific_name": "Parus major", "confidence": 0.85},
    {"common_name": "Eurasian Blue Tit", "scientific_name": "Cyanistes caeruleus", "confidence": 0.78},
    {"common_name": "House Sparrow", "scientific_name": "Passer domesticus", "confidence": 0.92},
    {"common_name": "European Robin", "scientific_name": "Erithacus rubecula", "confidence": 0.88},
    {"common_name": "Common Blackbird", "scientific_name": "Turdus merula", "confidence": 0.81},
]


def connect_mqtt():
    """Connect to MQTT broker"""
    client = mqtt.Client(client_id="audio-simulator")
    mqtt_host = os.getenv('MQTT_HOST', 'mosquitto')
    mqtt_port = int(os.getenv('MQTT_PORT', 1883))

    logger.info(f"Connecting to MQTT at {mqtt_host}:{mqtt_port}")
    client.connect(mqtt_host, mqtt_port)
    client.loop_start()
    return client


def simulate_audio_detection(mqtt_client):
    """Publish a simulated audio detection"""
    bird = random.choice(TEST_SPECIES)

    payload = {
        'timestamp': datetime.now().isoformat(),
        'species': bird['scientific_name'],
        'common_name': bird['common_name'],
        'confidence': bird['confidence'],
        'source': 'audio_simulator'
    }

    topic = "birdwatch/audio/detection"
    mqtt_client.publish(topic, json.dumps(payload))
    logger.info(f"Published audio detection: {bird['common_name']} ({bird['confidence']:.2%})")


def main():
    """Main loop - periodically publish audio detections"""
    logger.info("Starting Audio Simulator Service")

    mqtt_client = connect_mqtt()

    # Detection frequency
    min_interval = int(os.getenv('MIN_INTERVAL', 10))
    max_interval = int(os.getenv('MAX_INTERVAL', 60))

    logger.info(f"Will publish detections every {min_interval}-{max_interval} seconds")

    try:
        while True:
            # Random interval between detections
            interval = random.randint(min_interval, max_interval)
            time.sleep(interval)

            # Simulate detection
            simulate_audio_detection(mqtt_client)

    except KeyboardInterrupt:
        logger.info("Shutting down...")
        mqtt_client.loop_stop()
        mqtt_client.disconnect()


if __name__ == '__main__':
    main()
