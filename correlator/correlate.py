#!/usr/bin/env python3
"""
Bird Detection Correlation Engine
Matches visual and audio detections to create high-confidence sightings
"""

import os
import time
import json
import logging
from datetime import datetime, timedelta
from collections import defaultdict
import paho.mqtt.client as mqtt
import psycopg2
from psycopg2.extras import RealDictCursor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BirdCorrelator:
    """Correlates visual and audio bird detections"""

    def __init__(self, db_conn, correlation_window=30):
        self.db_conn = db_conn
        self.correlation_window = correlation_window  # seconds
        self.recent_detections = {
            'visual': [],
            'audio': []
        }

    def add_visual_detection(self, detection):
        """Add a visual detection"""
        self.recent_detections['visual'].append({
            'timestamp': datetime.fromisoformat(detection['timestamp']),
            'species': detection['species'],
            'common_name': detection['common_name'],
            'confidence': detection['confidence'],
            'image_path': detection.get('image_path')
        })
        self._save_raw_detection('visual', detection)
        self._cleanup_old_detections()
        self._check_correlations()

    def add_audio_detection(self, detection):
        """Add an audio detection"""
        self.recent_detections['audio'].append({
            'timestamp': datetime.fromisoformat(detection['timestamp']),
            'species': detection['species'],
            'common_name': detection['common_name'],
            'confidence': detection['confidence'],
            'audio_path': detection.get('audio_path')
        })
        self._save_raw_detection('audio', detection)
        self._cleanup_old_detections()
        self._check_correlations()

    def _cleanup_old_detections(self):
        """Remove detections outside correlation window"""
        cutoff_time = datetime.now() - timedelta(seconds=self.correlation_window)

        for source in ['visual', 'audio']:
            self.recent_detections[source] = [
                d for d in self.recent_detections[source]
                if d['timestamp'] > cutoff_time
            ]

    def _save_raw_detection(self, source, detection):
        """Save raw detection to database if not already saved by another service"""
        # Note: Visual detections are usually saved by the classifier itself,
        # but for robustness we can ensure it here or only do it for audio.
        # Based on Test Suite, we need audio_detections to be populated.
        if source == 'visual':
            return # Classifier already saves visual detections

        try:
            cursor = self.db_conn.cursor()
            cursor.execute("""
                INSERT INTO audio_detections
                (timestamp, species, common_name, confidence, audio_path, source)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                datetime.fromisoformat(detection['timestamp']),
                detection['species'],
                detection['common_name'],
                detection['confidence'],
                detection.get('audio_path'),
                detection.get('source', 'audio_simulator')
            ))
            self.db_conn.commit()
            cursor.close()
        except Exception as e:
            logger.exception(f"Failed to save raw audio detection: {e}")
            self.db_conn.rollback()

    def _check_correlations(self):
        """Check for matching visual and audio detections"""
        for visual in self.recent_detections['visual']:
            for audio in self.recent_detections['audio']:
                # Check if same species
                if self._species_match(visual['species'], audio['species']):
                    # Check if within time window
                    time_diff = abs((visual['timestamp'] - audio['timestamp']).total_seconds())

                    if time_diff <= self.correlation_window:
                        self._create_correlated_sighting(visual, audio, time_diff)

    def _species_match(self, species1, species2):
        """Check if two species identifications match"""
        # Simple exact match for now
        # Could be enhanced with fuzzy matching or taxonomy
        return species1.lower() == species2.lower()

    def _create_correlated_sighting(self, visual, audio, time_diff):
        """Create a correlated sighting entry"""
        try:
            # Check if already correlated
            cursor = self.db_conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("""
                SELECT id FROM correlated_sightings
                WHERE species = %s
                AND timestamp BETWEEN %s AND %s
            """, (
                visual['species'],
                min(visual['timestamp'], audio['timestamp']),
                max(visual['timestamp'], audio['timestamp'])
            ))

            if cursor.fetchone():
                # Already correlated
                cursor.close()
                return

            # Calculate combined confidence
            combined_confidence = (visual['confidence'] + audio['confidence']) / 2

            # Insert correlated sighting
            cursor.execute("""
                INSERT INTO correlated_sightings
                (timestamp, species, common_name, confidence, visual_confidence,
                 audio_confidence, image_path, audio_path, time_diff)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                visual['timestamp'],
                visual['species'],
                visual['common_name'],
                combined_confidence,
                visual['confidence'],
                audio['confidence'],
                visual.get('image_path'),
                audio.get('audio_path'),
                time_diff
            ))

            sighting_id = cursor.fetchone()['id']
            self.db_conn.commit()
            cursor.close()

            logger.info(
                f"Created correlated sighting #{sighting_id}: {visual['common_name']} "
                f"(visual: {visual['confidence']:.2%}, audio: {audio['confidence']:.2%}, "
                f"time_diff: {time_diff:.1f}s)"
            )

        except Exception as e:
            logger.error(f"Failed to create correlated sighting: {e}")
            self.db_conn.rollback()


class MQTTHandler:
    """Handle MQTT messages for bird detections"""

    def __init__(self, correlator):
        self.correlator = correlator
        self.client = None

    def on_connect(self, client, userdata, flags, rc):
        """Handle MQTT connection"""
        if rc == 0:
            logger.info("Connected to MQTT broker")
            # Subscribe to detection topics
            client.subscribe("birdwatch/visual/detection")
            client.subscribe("birdwatch/audio/detection")
        else:
            logger.error(f"MQTT connection failed with code {rc}")

    def on_message(self, client, userdata, msg):
        """Handle incoming MQTT messages"""
        try:
            payload = json.loads(msg.payload.decode())

            if msg.topic == "birdwatch/visual/detection":
                self.correlator.add_visual_detection(payload)
            elif msg.topic == "birdwatch/audio/detection":
                self.correlator.add_audio_detection(payload)

        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")

    def connect(self, host, port):
        """Connect to MQTT broker"""
        self.client = mqtt.Client(client_id="bird-correlator")
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect(host, port)
        return self.client


def connect_database():
    """Connect to PostgreSQL with retries"""
    db_host = os.getenv('DB_HOST', 'database')
    db_name = os.getenv('DB_NAME', 'birdwatch')
    db_user = os.getenv('DB_USER', 'birdwatch')
    db_pass = os.getenv('DB_PASSWORD', 'birdwatch123')

    max_retries = 30
    for i in range(max_retries):
        try:
            conn = psycopg2.connect(
                host=db_host,
                database=db_name,
                user=db_user,
                password=db_pass
            )
            logger.info("Connected to database")
            return conn
        except psycopg2.OperationalError as e:
            if i == max_retries - 1:
                logger.error(f"Database connection failed after {max_retries} attempts: {e}")
                raise
            logger.warning(f"Database not ready, retrying in 2s... ({i+1}/{max_retries})")
            time.sleep(2)


def main():
    """Main service loop"""
    logger.info("Starting Bird Correlation Engine")

    # Configuration
    mqtt_host = os.getenv('MQTT_HOST', 'mosquitto')
    mqtt_port = int(os.getenv('MQTT_PORT', 1883))
    correlation_window = int(os.getenv('CORRELATION_WINDOW', 30))

    # Connect to database
    db_conn = connect_database()

    # Initialize correlator
    correlator = BirdCorrelator(db_conn, correlation_window)

    # Connect to MQTT
    mqtt_handler = MQTTHandler(correlator)
    mqtt_client = mqtt_handler.connect(mqtt_host, mqtt_port)

    logger.info(f"Correlation window: {correlation_window} seconds")
    logger.info("Ready to correlate detections")

    try:
        mqtt_client.loop_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        mqtt_client.disconnect()
        db_conn.close()


if __name__ == '__main__':
    main()
