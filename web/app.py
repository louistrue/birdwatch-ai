#!/usr/bin/env python3
"""
Bird Watcher Web Dashboard
View bird detections, statistics, and recordings
"""

import os
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'database'),
    'database': os.getenv('DB_NAME', 'birdwatch_test'),
    'user': os.getenv('DB_USER', 'test_user'),
    'password': os.getenv('DB_PASSWORD', 'test_pass')
}

FRIGATE_URL = os.getenv('FRIGATE_URL', 'http://frigate:5000')


def get_db():
    """Get database connection"""
    return psycopg2.connect(**DB_CONFIG)


@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html', frigate_url=FRIGATE_URL)


@app.route('/api/today')
def today_sightings():
    """Get today's bird sightings"""
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT * FROM todays_sightings
            ORDER BY total_count DESC
        """)

        sightings = cursor.fetchall()
        cursor.close()
        conn.close()

        return jsonify([dict(row) for row in sightings])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/recent')
def recent_detections():
    """Get recent bird detections"""
    try:
        limit = request.args.get('limit', 50, type=int)
        source = request.args.get('source', 'all')

        conn = get_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        if source == 'all':
            query = """
                SELECT * FROM all_detections
                ORDER BY timestamp DESC
                LIMIT %s
            """
        else:
            query = f"""
                SELECT * FROM all_detections
                WHERE source = %s
                ORDER BY timestamp DESC
                LIMIT %s
            """

        if source == 'all':
            cursor.execute(query, (limit,))
        else:
            cursor.execute(query, (source, limit))

        detections = cursor.fetchall()
        cursor.close()
        conn.close()

        # Convert datetime objects to strings
        for d in detections:
            if d.get('timestamp'):
                d['timestamp'] = d['timestamp'].isoformat()
            if d.get('first_seen'):
                d['first_seen'] = d['first_seen'].isoformat()
            if d.get('last_seen'):
                d['last_seen'] = d['last_seen'].isoformat()

        return jsonify([dict(row) for row in detections])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/stats/daily')
def daily_stats():
    """Get daily statistics"""
    try:
        days = request.args.get('days', 7, type=int)
        start_date = datetime.now().date() - timedelta(days=days)

        conn = get_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT
                date,
                species,
                visual_count,
                audio_count,
                correlated_count,
                first_seen,
                last_seen
            FROM daily_stats
            WHERE date >= %s
            ORDER BY date DESC, visual_count + audio_count DESC
        """, (start_date,))

        stats = cursor.fetchall()
        cursor.close()
        conn.close()

        # Convert date/time objects to strings
        for s in stats:
            if s.get('date'):
                s['date'] = s['date'].isoformat()
            if s.get('first_seen'):
                s['first_seen'] = str(s['first_seen'])
            if s.get('last_seen'):
                s['last_seen'] = str(s['last_seen'])

        return jsonify([dict(row) for row in stats])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/stats/species')
def species_stats():
    """Get statistics by species"""
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT
                s.scientific_name,
                s.common_name_en,
                s.common_name_de,
                COUNT(DISTINCT DATE(ad.timestamp)) AS days_seen,
                COUNT(ad.id) AS total_detections,
                MAX(ad.timestamp) AS last_seen
            FROM species s
            LEFT JOIN all_detections ad ON s.scientific_name = ad.species
            GROUP BY s.scientific_name, s.common_name_en, s.common_name_de
            HAVING COUNT(ad.id) > 0
            ORDER BY total_detections DESC
        """)

        stats = cursor.fetchall()
        cursor.close()
        conn.close()

        # Convert datetime objects to strings
        for s in stats:
            if s.get('last_seen'):
                s['last_seen'] = s['last_seen'].isoformat()

        return jsonify([dict(row) for row in stats])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/species')
def species_list():
    """Get list of known species"""
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT * FROM species
            ORDER BY common_name_en
        """)

        species = cursor.fetchall()
        cursor.close()
        conn.close()

        return jsonify([dict(row) for row in species])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/correlated')
def correlated_sightings():
    """Get correlated (high-confidence) sightings"""
    try:
        limit = request.args.get('limit', 50, type=int)

        conn = get_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT * FROM correlated_sightings
            ORDER BY timestamp DESC
            LIMIT %s
        """, (limit,))

        sightings = cursor.fetchall()
        cursor.close()
        conn.close()

        # Convert datetime objects to strings
        for s in sightings:
            if s.get('timestamp'):
                s['timestamp'] = s['timestamp'].isoformat()
            if s.get('created_at'):
                s['created_at'] = s['created_at'].isoformat()

        return jsonify([dict(row) for row in sightings])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
