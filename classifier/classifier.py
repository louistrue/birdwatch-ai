#!/usr/bin/env python3
"""
Bird Visual Classifier Service
Monitors Frigate snapshots and classifies bird species using TFLite model
"""

import os
import time
import json
import logging
from datetime import datetime
from pathlib import Path
import numpy as np
from PIL import Image
import paho.mqtt.client as mqtt
import psycopg2
from psycopg2.extras import RealDictCursor
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

try:
    import tflite_runtime.interpreter as tflite
except ImportError:
    import tensorflow.lite as tflite

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BirdClassifier:
    """TFLite bird species classifier"""

    def __init__(self, model_path, labels_path=None, confidence_threshold=0.6):
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.interpreter = None
        self.input_details = None
        self.output_details = None
        self.labels = []

        # Load model
        self.load_model()

        # Load labels if provided
        if labels_path and os.path.exists(labels_path):
            self.load_labels(labels_path)
        else:
            logger.warning("No labels file found, using indices")

    def load_model(self):
        """Load TFLite model"""
        try:
            logger.info(f"Loading model from {self.model_path}")
            self.interpreter = tflite.Interpreter(model_path=self.model_path)
            self.interpreter.allocate_tensors()

            self.input_details = self.interpreter.get_input_details()
            self.output_details = self.interpreter.get_output_details()

            logger.info(f"Model loaded successfully")
            logger.info(f"Input shape: {self.input_details[0]['shape']}")
            logger.info(f"Output shape: {self.output_details[0]['shape']}")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise

    def load_labels(self, labels_path):
        """Load species labels"""
        try:
            with open(labels_path, 'r') as f:
                self.labels = [line.strip() for line in f.readlines()]
            logger.info(f"Loaded {len(self.labels)} labels")
        except Exception as e:
            logger.error(f"Failed to load labels: {e}")

    def preprocess_image(self, image_path):
        """Preprocess image for model input"""
        try:
            # Get expected input shape
            input_shape = self.input_details[0]['shape']
            height, width = input_shape[1], input_shape[2]

            # Load and resize image
            image = Image.open(image_path).convert('RGB')
            image = image.resize((width, height), Image.LANCZOS)

            # Convert to numpy array
            input_data = np.array(image, dtype=np.float32)

            # Normalize to [0, 1] or [-1, 1] depending on model
            input_data = input_data / 255.0

            # Add batch dimension
            input_data = np.expand_dims(input_data, axis=0)

            return input_data
        except Exception as e:
            logger.error(f"Failed to preprocess image {image_path}: {e}")
            return None

    def classify(self, image_path):
        """Classify bird species in image"""
        try:
            # Preprocess image
            input_data = self.preprocess_image(image_path)
            if input_data is None:
                return None

            # Run inference
            self.interpreter.set_tensor(self.input_details[0]['index'], input_data)
            self.interpreter.invoke()

            # Get output
            output_data = self.interpreter.get_tensor(self.output_details[0]['index'])
            results = np.squeeze(output_data)

            # Get top prediction
            top_idx = np.argmax(results)
            confidence = float(results[top_idx])

            # Get species name
            if self.labels:
                species = self.labels[top_idx]
            else:
                species = f"Species_{top_idx}"

            # Only return if confidence above threshold
            if confidence >= self.confidence_threshold:
                return {
                    'species': species,
                    'confidence': confidence,
                    'scientific_name': species,  # Parse if available
                    'common_name': species.split('_')[-1] if '_' in species else species
                }
            else:
                logger.debug(f"Low confidence ({confidence:.2f}) for {image_path}")
                return None

        except Exception as e:
            logger.error(f"Classification failed for {image_path}: {e}")
            return None


class BirdDetectionHandler(FileSystemEventHandler):
    """Watch for new snapshots from Frigate"""

    def __init__(self, classifier, db_conn, mqtt_client):
        self.classifier = classifier
        self.db_conn = db_conn
        self.mqtt_client = mqtt_client
        self.processed_files = set()

    def on_created(self, event):
        """Handle new file creation"""
        if event.is_directory:
            return

        # Only process image files
        if not event.src_path.lower().endswith(('.jpg', '.jpeg', '.png')):
            return

        # Avoid duplicate processing
        if event.src_path in self.processed_files:
            return

        # Wait a moment for file to be fully written
        time.sleep(0.5)

        self.process_image(event.src_path)

    def process_image(self, image_path):
        """Process and classify a bird image"""
        try:
            logger.info(f"Processing image: {image_path}")

            # Mark as processed
            self.processed_files.add(image_path)

            # Classify
            result = self.classifier.classify(image_path)

            if result:
                logger.info(f"Detected: {result['common_name']} ({result['confidence']:.2%})")

                # Save to database
                self.save_detection(image_path, result)

                # Publish to MQTT
                self.publish_detection(image_path, result)
            else:
                logger.debug(f"No confident detection for {image_path}")

        except Exception as e:
            logger.error(f"Error processing {image_path}: {e}")

    def save_detection(self, image_path, result):
        """Save detection to database"""
        try:
            cursor = self.db_conn.cursor()
            cursor.execute("""
                INSERT INTO visual_detections
                (timestamp, image_path, species, common_name, confidence, source)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                datetime.now(),
                image_path,
                result['scientific_name'],
                result['common_name'],
                result['confidence'],
                'classifier'
            ))
            self.db_conn.commit()
            cursor.close()
        except Exception as e:
            logger.error(f"Failed to save detection to database: {e}")
            self.db_conn.rollback()

    def publish_detection(self, image_path, result):
        """Publish detection to MQTT"""
        try:
            topic = "birdwatch/visual/detection"
            payload = {
                'timestamp': datetime.now().isoformat(),
                'image_path': image_path,
                'species': result['scientific_name'],
                'common_name': result['common_name'],
                'confidence': result['confidence'],
                'source': 'classifier'
            }
            self.mqtt_client.publish(topic, json.dumps(payload))
        except Exception as e:
            logger.error(f"Failed to publish to MQTT: {e}")


def connect_database():
    """Connect to PostgreSQL database"""
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'database'),
            database=os.getenv('DB_NAME', 'birdwatch'),
            user=os.getenv('DB_USER', 'birdwatch'),
            password=os.getenv('DB_PASSWORD', 'birdwatch123')
        )
        logger.info("Connected to database")
        return conn
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise


def connect_mqtt():
    """Connect to MQTT broker"""
    try:
        client = mqtt.Client(client_id="bird-classifier")
        client.connect(
            os.getenv('MQTT_HOST', 'mosquitto'),
            int(os.getenv('MQTT_PORT', 1883))
        )
        client.loop_start()
        logger.info("Connected to MQTT broker")
        return client
    except Exception as e:
        logger.error(f"MQTT connection failed: {e}")
        raise


def main():
    """Main service loop"""
    logger.info("Starting Bird Classifier Service")

    # Configuration
    model_path = os.getenv('MODEL_PATH', '/app/model/birds_model.tflite')
    labels_path = os.getenv('LABELS_PATH', '/app/model/labels.txt')
    snapshots_dir = os.getenv('SNAPSHOTS_DIR', '/snapshots')
    confidence_threshold = float(os.getenv('CONFIDENCE_THRESHOLD', 0.6))

    # Check if model exists
    if not os.path.exists(model_path):
        logger.error(f"Model not found at {model_path}")
        logger.info("Please download a TFLite bird classification model")
        logger.info("Example: iNaturalist birds or Caltech-UCSD Birds")
        return

    # Initialize classifier
    classifier = BirdClassifier(
        model_path=model_path,
        labels_path=labels_path if os.path.exists(labels_path) else None,
        confidence_threshold=confidence_threshold
    )

    # Connect to services
    db_conn = connect_database()
    mqtt_client = connect_mqtt()

    # Set up file watcher
    event_handler = BirdDetectionHandler(classifier, db_conn, mqtt_client)
    observer = Observer()
    observer.schedule(event_handler, snapshots_dir, recursive=True)
    observer.start()

    logger.info(f"Watching for snapshots in {snapshots_dir}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        observer.stop()

    observer.join()
    db_conn.close()
    mqtt_client.loop_stop()
    mqtt_client.disconnect()


if __name__ == '__main__':
    main()
