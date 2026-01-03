#!/usr/bin/env python3
"""
Daily Digest Generator
Creates a summary of today's bird sightings
Can be run as a cron job or manually
"""

import os
import sys
from datetime import datetime, date
import psycopg2
from psycopg2.extras import RealDictCursor

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'birdwatch'),
    'user': os.getenv('DB_USER', 'birdwatch'),
    'password': os.getenv('DB_PASSWORD', 'birdwatch123')
}


def get_today_stats():
    """Get today's bird sighting statistics"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Get today's sightings
        cursor.execute("""
            SELECT * FROM todays_sightings
            ORDER BY total_count DESC
        """)
        sightings = cursor.fetchall()

        # Get correlated sightings count
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM correlated_sightings
            WHERE DATE(timestamp) = CURRENT_DATE
        """)
        correlated_count = cursor.fetchone()['count']

        cursor.close()
        conn.close()

        return sightings, correlated_count

    except Exception as e:
        print(f"Error fetching stats: {e}", file=sys.stderr)
        return [], 0


def generate_text_digest(sightings, correlated_count):
    """Generate a text-based daily digest"""
    today = date.today().strftime("%A, %B %d, %Y")

    output = []
    output.append("=" * 60)
    output.append(f"   BIRD WATCHER DAILY DIGEST - {today}")
    output.append("=" * 60)
    output.append("")

    if not sightings:
        output.append("No bird sightings recorded today.")
        output.append("")
        return "\n".join(output)

    # Summary stats
    total_sightings = sum(s['total_count'] for s in sightings)
    species_count = len(sightings)

    output.append(f"📊 SUMMARY")
    output.append(f"   Total Sightings:     {total_sightings}")
    output.append(f"   Unique Species:      {species_count}")
    output.append(f"   High Confidence:     {correlated_count}")
    output.append("")

    # Species breakdown
    output.append(f"🐦 SPECIES BREAKDOWN")
    output.append("")

    for i, bird in enumerate(sightings, 1):
        common_name = bird['common_name'] or bird['species']
        count = bird['total_count']
        confidence = bird['max_confidence'] * 100

        first_seen = bird['first_seen'].strftime("%H:%M") if bird['first_seen'] else "N/A"
        last_seen = bird['last_seen'].strftime("%H:%M") if bird['last_seen'] else "N/A"

        output.append(f"{i}. {common_name}")
        output.append(f"   Sightings: {count}  |  Best confidence: {confidence:.0f}%")
        output.append(f"   First seen: {first_seen}  |  Last seen: {last_seen}")
        output.append("")

    output.append("=" * 60)

    return "\n".join(output)


def save_digest(digest, filename=None):
    """Save digest to file"""
    if filename is None:
        today = date.today().strftime("%Y-%m-%d")
        filename = f"digest_{today}.txt"

    filepath = os.path.join(os.path.dirname(__file__), '..', 'data', filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    with open(filepath, 'w') as f:
        f.write(digest)

    return filepath


def main():
    """Main function"""
    print("Generating daily digest...")

    sightings, correlated_count = get_today_stats()
    digest = generate_text_digest(sightings, correlated_count)

    # Print to stdout
    print(digest)

    # Save to file
    filepath = save_digest(digest)
    print(f"\nDigest saved to: {filepath}")


if __name__ == '__main__':
    main()
