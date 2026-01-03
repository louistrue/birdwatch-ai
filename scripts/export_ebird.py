#!/usr/bin/env python3
"""
eBird Export Script
Exports bird sightings to eBird-compatible CSV format
"""

import os
import sys
import csv
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'birdwatch'),
    'user': os.getenv('DB_USER', 'birdwatch'),
    'password': os.getenv('DB_PASSWORD', 'birdwatch123')
}

# eBird location settings (update with your location)
LOCATION_NAME = os.getenv('EBIRD_LOCATION', 'My Garden')
LATITUDE = os.getenv('EBIRD_LAT', '47.3769')  # Default: Zurich
LONGITUDE = os.getenv('EBIRD_LON', '8.5417')
PROTOCOL = 'eBird - Stationary Count'


def get_sightings(start_date=None, end_date=None):
    """Get bird sightings from database"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Use correlated sightings for higher confidence
        query = """
            SELECT
                DATE(timestamp) as date,
                TO_CHAR(timestamp, 'HH24:MI') as time,
                species,
                common_name,
                scientific_name,
                COUNT(*) as count,
                MAX(confidence) as max_confidence
            FROM correlated_sightings
        """

        conditions = []
        params = []

        if start_date:
            conditions.append("DATE(timestamp) >= %s")
            params.append(start_date)

        if end_date:
            conditions.append("DATE(timestamp) <= %s")
            params.append(end_date)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += """
            GROUP BY DATE(timestamp), TO_CHAR(timestamp, 'HH24:MI'),
                     species, common_name, scientific_name
            ORDER BY date DESC, time DESC
        """

        cursor.execute(query, params)
        sightings = cursor.fetchall()

        cursor.close()
        conn.close()

        return sightings

    except Exception as e:
        print(f"Error fetching sightings: {e}", file=sys.stderr)
        return []


def export_to_ebird_csv(sightings, filename=None):
    """Export sightings to eBird-compatible CSV format"""
    if filename is None:
        today = datetime.now().strftime("%Y%m%d")
        filename = f"ebird_export_{today}.csv"

    filepath = os.path.join(os.path.dirname(__file__), '..', 'data', filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    # eBird CSV format
    # https://support.ebird.org/en/support/solutions/articles/48000838205
    fieldnames = [
        'Common Name',
        'Scientific Name',
        'Count',
        'Location Name',
        'Latitude',
        'Longitude',
        'Date',
        'Start Time',
        'Protocol',
        'Duration (Minutes)',
        'All Obs Reported',
        'Species Comments'
    ]

    with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for sighting in sightings:
            writer.writerow({
                'Common Name': sighting['common_name'] or sighting['species'],
                'Scientific Name': sighting.get('scientific_name', ''),
                'Count': sighting['count'],
                'Location Name': LOCATION_NAME,
                'Latitude': LATITUDE,
                'Longitude': LONGITUDE,
                'Date': sighting['date'].strftime('%m/%d/%Y'),
                'Start Time': sighting['time'],
                'Protocol': PROTOCOL,
                'Duration (Minutes)': 60,  # Adjust as needed
                'All Obs Reported': 'N',
                'Species Comments': f"Automated detection (confidence: {sighting['max_confidence']:.0%})"
            })

    return filepath


def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description='Export bird sightings to eBird format')
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD)')
    parser.add_argument('--days', type=int, help='Export last N days')
    parser.add_argument('--output', help='Output filename')

    args = parser.parse_args()

    # Parse dates
    start_date = None
    end_date = None

    if args.days:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=args.days)
    elif args.start_date:
        start_date = datetime.strptime(args.start_date, '%Y-%m-%d').date()
        if args.end_date:
            end_date = datetime.strptime(args.end_date, '%Y-%m-%d').date()
        else:
            end_date = datetime.now().date()

    # Fetch sightings
    print(f"Fetching sightings...")
    if start_date:
        print(f"Date range: {start_date} to {end_date or 'today'}")

    sightings = get_sightings(start_date, end_date)

    if not sightings:
        print("No sightings found for the specified date range.")
        return

    print(f"Found {len(sightings)} sightings")

    # Export to CSV
    filepath = export_to_ebird_csv(sightings, args.output)
    print(f"Exported to: {filepath}")
    print(f"\nYou can now upload this file to eBird:")
    print(f"https://ebird.org/submit")
    print(f"\nNote: Review and verify automated detections before submitting!")


if __name__ == '__main__':
    main()
