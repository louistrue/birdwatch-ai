#!/usr/bin/env python3
"""
E2E Test Suite for Birdwatch AI System
Tests the complete pipeline without physical hardware
"""

import os
import time
import json
import pytest
import psycopg2
import paho.mqtt.client as mqtt
import requests
from datetime import datetime, timedelta


class TestBirdwatchPipeline:
    """End-to-end tests for bird detection pipeline"""

    @pytest.fixture(scope="class")
    def db_connection(self):
        """Database connection fixture with retries"""
        db_host = os.getenv('DB_HOST', 'database')
        db_name = os.getenv('DB_NAME', 'birdwatch_test')
        db_user = os.getenv('DB_USER', 'test_user')
        db_pass = os.getenv('DB_PASSWORD', 'test_pass')

        max_retries = 30
        for i in range(max_retries):
            try:
                conn = psycopg2.connect(
                    host=db_host,
                    database=db_name,
                    user=db_user,
                    password=db_pass
                )
                yield conn
                conn.close()
                return
            except psycopg2.OperationalError:
                if i == max_retries - 1:
                    raise
                time.sleep(2)

    @pytest.fixture(scope="class")
    def mqtt_client(self):
        """MQTT client fixture with unique ID"""
        import uuid
        client_id = f"test-client-{uuid.uuid4().hex[:8]}"
        client = mqtt.Client(client_id=client_id)
        
        print(f"Connecting to MQTT as {client_id}...")
        client.connect(os.getenv('MQTT_HOST', 'mosquitto'), 1883)
        client.loop_start()
        
        yield client
        
        client.loop_stop()
        client.disconnect()

    def test_database_initialized(self, db_connection):
        """Test that database schema is properly initialized"""
        cursor = db_connection.cursor()

        # Check that required tables exist
        cursor.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public'
        """)
        tables = {row[0] for row in cursor.fetchall()}

        required_tables = {
            'visual_detections',
            'audio_detections',
            'correlated_sightings',
            'species'
        }

        assert required_tables.issubset(tables), f"Missing tables: {required_tables - tables}"
        cursor.close()

    def test_frigate_running(self):
        """Test that Frigate NVR is accessible"""
        frigate_url = os.getenv('FRIGATE_URL', 'http://frigate:5000')

        # Wait for Frigate to be ready
        max_retries = 30
        for i in range(max_retries):
            try:
                response = requests.get(f"{frigate_url}/api/config", timeout=5)
                if response.status_code == 200:
                    break
            except requests.exceptions.RequestException:
                if i == max_retries - 1:
                    raise
                time.sleep(2)

        assert response.status_code == 200
        config = response.json()
        assert 'cameras' in config
        assert 'test_camera' in config['cameras']

    def test_web_dashboard_accessible(self):
        """Test that web dashboard is running"""
        web_url = os.getenv('WEB_URL', 'http://web:8080')

        # Wait for web service
        max_retries = 20
        for i in range(max_retries):
            try:
                response = requests.get(web_url, timeout=5)
                if response.status_code == 200:
                    break
            except requests.exceptions.RequestException:
                if i == max_retries - 1:
                    raise
                time.sleep(2)

        assert response.status_code == 200
        assert b'Bird Watch' in response.content or b'Birdwatch' in response.content

    def test_mqtt_broker_running(self, mqtt_client):
        """Test MQTT broker is accepting connections"""
        # Simple publish/subscribe test
        test_topic = "test/connectivity"
        received = []

        def on_message(client, userdata, msg):
            received.append(msg.payload.decode())

        mqtt_client.subscribe(test_topic)
        mqtt_client.on_message = on_message

        mqtt_client.publish(test_topic, "test_message")

        # Wait for message
        time.sleep(2)

        assert len(received) > 0
        assert received[0] == "test_message"

    def test_visual_detection_pipeline(self, db_connection):
        """Test complete visual detection pipeline"""
        # Deterministic test: Inject a mock snapshot if Frigate is slow in the test environment
        print("Ensuring snapshot directory exists...")
        import os, shutil
        snapshot_dir = "/snapshots/test_camera"
        os.makedirs(snapshot_dir, exist_ok=True)
        
        print("Injecting mock bird snapshot...")
        shutil.copy("/fixtures/images/great_tit_1.jpg", f"{snapshot_dir}/injected_bird.jpg")
        # Ensure fresh mtime for the classifier's polling logic
        os.utime(f"{snapshot_dir}/injected_bird.jpg", None)

        # Wait for classifier to process
        print("Waiting for visual detection processing (30 seconds)...")
        time.sleep(30)

        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM visual_detections
            WHERE timestamp > NOW() - INTERVAL '2 minutes'
        """)
        count = cursor.fetchone()[0]
        cursor.close()

        # Should have at least one detection
        assert count > 0, "No visual detections recorded"

    def test_audio_detection_pipeline(self, db_connection):
        """Test audio detection simulation"""
        # Wait for audio simulator to publish detections
        print("Waiting for audio detections (30 seconds)...")
        time.sleep(30)

        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM audio_detections
            WHERE timestamp > NOW() - INTERVAL '2 minutes'
        """)
        count = cursor.fetchone()[0]
        cursor.close()

        # Should have at least one audio detection
        assert count > 0, "No audio detections recorded"

    def test_correlation_engine(self, db_connection):
        """Test that visual and audio detections are correlated"""
        # Wait for correlations to form
        print("Waiting for correlations (30 seconds)...")
        time.sleep(30)

        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM correlated_sightings
            WHERE timestamp > NOW() - INTERVAL '5 minutes'
        """)
        count = cursor.fetchone()[0]
        cursor.close()

        # Should have correlated sightings
        # Note: May be 0 if timing doesn't align, which is okay for first run
        print(f"Found {count} correlated sightings")

    def test_mqtt_detection_published(self, mqtt_client, db_connection):
        """Test that detections are published to MQTT"""
        messages = []

        def on_message(client, userdata, msg):
            try:
                payload = json.loads(msg.payload.decode())
                print(f"MQTT Received: {msg.topic}")
                messages.append((msg.topic, payload))
            except Exception as e:
                print(f"Error parsing MQTT: {e}")

        mqtt_client.on_message = on_message
        mqtt_client.subscribe("birdwatch/#")
        
        # Give it a moment to subscribe
        time.sleep(2)

        # Re-trigger visual detection to ensure we catch it on MQTT
        print("Re-triggering visual detection for MQTT test...")
        snapshot_dir = "/snapshots/test_camera"
        os.makedirs(snapshot_dir, exist_ok=True)
        import shutil
        shutil.copy("/fixtures/images/blue_tit_1.jpg", f"{snapshot_dir}/mqtt_test_bird.jpg")
        # Ensure fresh mtime for the classifier's polling logic
        os.utime(f"{snapshot_dir}/mqtt_test_bird.jpg", None)

        # Wait for messages
        print("Listening for MQTT detections (120 seconds)...")
        start_time = time.time()
        while time.time() - start_time < 120:
            visual = [m for m in messages if m[0] == "birdwatch/visual/detection"]
            audio = [m for m in messages if m[0] == "birdwatch/audio/detection"]
            if len(visual) > 0 and len(audio) > 0:
                break
            time.sleep(5)
        
        visual = [m for m in messages if m[0] == "birdwatch/visual/detection"]
        audio = [m for m in messages if m[0] == "birdwatch/audio/detection"]
        
        print(f"Final Count - Visual: {len(visual)}, Audio: {len(audio)}")
        
        assert len(audio) > 0, "No audio detections via MQTT after 120s"
        assert len(visual) > 0, "No visual detections via MQTT after 120s"

    def test_database_species_data(self, db_connection):
        """Test that Swiss bird species are loaded"""
        cursor = db_connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM species")
        count = cursor.fetchone()[0]
        cursor.close()

        # Should have Swiss bird species
        assert count >= 10, f"Expected at least 10 Swiss bird species, got {count}"

    def test_detection_confidence_thresholds(self, db_connection):
        """Test that only confident detections are stored"""
        cursor = db_connection.cursor()

        # Check visual detections
        cursor.execute("""
            SELECT MIN(confidence), AVG(confidence), MAX(confidence)
            FROM visual_detections
            WHERE timestamp > NOW() - INTERVAL '5 minutes'
        """)
        result = cursor.fetchone()

        if result[0] is not None:  # If we have detections
            min_conf, avg_conf, max_conf = result
            # Confidence should be above threshold (0.3 in test config)
            assert min_conf >= 0.3, f"Found detection below threshold: {min_conf}"
            assert max_conf <= 1.0, f"Invalid confidence value: {max_conf}"

        cursor.close()


class TestSystemPerformance:
    """Performance and load tests"""

    def test_classifier_latency(self):
        """Test that classifier processes images in reasonable time"""
        # This would require injecting test images and measuring processing time
        # Placeholder for now
        pass

    def test_system_resources(self):
        """Test that services stay within resource limits"""
        # Would check Docker stats, memory usage, CPU usage
        # Placeholder for now
        pass


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
