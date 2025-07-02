from flask import Flask, render_template, jsonify
import json
import pandas as pd
from pathlib import Path
import logging
import gzip
import time

app = Flask(__name__)

# basic request logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Determine the path to the Excel file relative to this file
DATA_PATH = Path(__file__).resolve().parent.parent / '2025-6-20-iolp-buildings.xlsx'
LEASE_DATA_PATH = Path(__file__).resolve().parent.parent / '2025-6-20-iolp-leases.xlsx'

# Load a subset of the building dataset with relevant fields
_df = pd.read_excel(
    DATA_PATH,
    usecols=[
        'Real Property Asset Name',
        'Street Address',
        'City',
        'State',
        'Construction Date',
        'Owned or Leased',
        'Latitude',
        'Longitude',
        'Building Status',
        'Real Property Asset Type',
        'Congressional District Representative Name'
    ]
)

# Load leased property data with relevant fields and parse dates
_leases_df = pd.read_excel(
    LEASE_DATA_PATH,
    usecols=[
        'Real Property Asset Name',
        'City',
        'State',
        'Lease Effective Date',
        'Lease Expiration Date'
    ],
    parse_dates=['Lease Effective Date', 'Lease Expiration Date']
)

# Rename columns for cleaner JSON keys
_leases_df = _leases_df.rename(columns={
    'Real Property Asset Name': 'name',
    'City': 'city',
    'State': 'state',
    'Lease Effective Date': 'lease_start',
    'Lease Expiration Date': 'lease_end'
})

# Format dates as ISO strings for the web app
_leases_df['lease_start'] = _leases_df['lease_start'].dt.strftime('%Y-%m-%d')
_leases_df['lease_end'] = _leases_df['lease_end'].dt.strftime('%Y-%m-%d')

# cache the JSON for faster /api/leases responses
_leases_records = _leases_df.to_dict(orient='records')
_leases_json = json.dumps(_leases_records)
_leases_json_gz = gzip.compress(_leases_json.encode('utf-8'))

# Combine address fields into a single column
_df['Address'] = (
    _df['Street Address'].fillna('') + ', ' +
    _df['City'].fillna('') + ', ' +
    _df['State'].fillna('')
)

# Rename columns for friendlier JSON keys
_df = _df.rename(columns={
    'Real Property Asset Name': 'name',
    'Construction Date': 'construction_date',
    'Owned or Leased': 'owned_or_leased',
    'Latitude': 'lat',
    'Longitude': 'lon',
    'Building Status': 'building_status',
    'Real Property Asset Type': 'asset_type',
    'Congressional District Representative Name': 'representative'
})

_df['construction_date'] = _df['construction_date'].apply(lambda x: str(int(x)) if pd.notnull(x) else '')

@app.route('/')
def properties_page():
    """Render the table page."""
    return render_template('properties.html')

@app.route('/api/properties')
def properties_api():
    """Return the dataset as JSON for DataTables."""
    return jsonify(_df[['name', 'Address', 'construction_date', 'owned_or_leased']].to_dict(orient='records'))


@app.route('/api/leases')
def leases_api():
    """Return leased property data for the dashboard."""
    start = time.time()
    resp = app.response_class(
        _leases_json_gz,
        mimetype='application/json',
        headers={'Content-Encoding': 'gzip'}
    )
    logger.info("/api/leases served in %.2f ms", (time.time() - start) * 1000)
    return resp


@app.route('/owned')
def owned_dashboard():
    """Render dashboard for owned properties."""
    return render_template('owned_dashboard.html')


@app.route('/leased')
def leased_dashboard():
    """Render dashboard for leased properties."""
    logger.info("Rendering leased_dashboard")
    return render_template('leased_dashboard.html')


@app.route('/api/owned_construction_dates')
def owned_construction_dates():
    """Return counts of owned buildings by construction year."""
    owned = _df[_df['owned_or_leased'] == 'F']
    counts = owned['construction_date'].value_counts().sort_index()
    data = [
        {'year': year, 'count': int(count)}
        for year, count in counts.items()
        if year
    ]
    return jsonify(data)


@app.route('/api/owned_map_data')
def owned_map_data():
    """Return location data for owned properties."""
    owned = _df[_df['owned_or_leased'] == 'F']
    records = []
    for _, row in owned.iterrows():
        if pd.notnull(row['lat']) and pd.notnull(row['lon']):
            records.append({
                'lat': float(row['lat']),
                'lon': float(row['lon']),
                'status': row.get('building_status', ''),
                'asset_type': row.get('asset_type', ''),
                'representative': row.get('representative', '')
            })
    return jsonify(records)

if __name__ == '__main__':
    app.run(debug=True)
