#!/usr/bin/env python3
"""
Fetch ICE flight data from Airtable and save to CSV.
Requires AIRTABLE_PAT environment variable with personal access token.
"""

import os
import sys
import pandas as pd
from pyairtable import Api

# Airtable configuration
BASE_ID = 'appXo5spat4J3IQ9K'
TABLE_ID = 'tbl4ZyyH4kmbsgDAw'
OUTPUT_FILE = 'msp-ice-flights.csv'

def fetch_airtable_data():
    """Fetch data from Airtable and save to CSV."""
    # Get PAT from environment
    pat = os.environ.get('AIRTABLE_PAT')
    if not pat:
        print("Error: AIRTABLE_PAT environment variable not set", file=sys.stderr)
        print("Please add to .envrc.local: export AIRTABLE_PAT='your-token-here'", file=sys.stderr)
        sys.exit(1)

    # Connect to Airtable
    api = Api(pat)
    table = api.table(BASE_ID, TABLE_ID)

    # Fetch all records
    print(f"Fetching data from Airtable (base: {BASE_ID}, table: {TABLE_ID})...")
    records = table.all()

    # Extract fields from records
    data = [record['fields'] for record in records]

    # Convert to DataFrame
    df = pd.DataFrame(data)

    # Add Date column derived from Day column (which has correct CST dates)
    # Day column format: "Wed Nov 19 2025"
    if 'Day' in df.columns:
        df['Date'] = pd.to_datetime(df['Day'], format='%a %b %d %Y')
    elif 'Arrive' in df.columns:
        # Fallback to Arrive if Day doesn't exist (though dates will be UTC-based)
        df['Date'] = pd.to_datetime(df['Arrive']).dt.date
        df['Date'] = pd.to_datetime(df['Date'])

    # Sort by Date (ascending), then by Callsign (ascending)
    sort_columns = []
    if 'Date' in df.columns:
        sort_columns.append('Date')
    if 'Callsign' in df.columns:
        sort_columns.append('Callsign')

    if sort_columns:
        df = df.sort_values(by=sort_columns)

    # Save to CSV
    df.to_csv(OUTPUT_FILE, index=False)

    print(f"✓ Downloaded {len(df)} records to {OUTPUT_FILE}")
    print(f"  Columns: {', '.join(df.columns.tolist())}")

if __name__ == '__main__':
    fetch_airtable_data()
