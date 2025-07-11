from flask import Flask, render_template, jsonify
import os
import json
import pandas as pd
from pathlib import Path

app = Flask(__name__)

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
    return app.response_class(_leases_json, mimetype='application/json')


@app.route('/owned')
def owned_dashboard():
    """Render dashboard for owned properties."""
    return render_template('owned_dashboard.html')


@app.route('/leased')
def leased_dashboard():
    """Render dashboard for leased properties."""
    return render_template('leased_dashboard.html')


@app.route('/map')
def map_page():
    """Render interactive map with Google Maps API."""
    api_key = os.environ.get('GOOGLE_MAPS_API_KEY', '')
    return render_template('map.html', api_key=api_key)


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


@app.route('/api/map_data')
def map_data():
    """Return location data for all properties within the continental US."""
    records = []
    for _, row in _df.iterrows():
        if pd.notnull(row['lat']) and pd.notnull(row['lon']):
            lat = float(row['lat'])
            lon = float(row['lon'])
            if 24 <= lat <= 49 and -125 <= lon <= -66:
                records.append({
                    'name': row['name'],
                    'address': row['Address'],
                    'lat': lat,
                    'lon': lon
                })
    return jsonify(records)

if __name__ == '__main__':
    app.run(debug=True)
