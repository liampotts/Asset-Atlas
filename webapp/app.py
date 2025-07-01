from flask import Flask, render_template, jsonify
import pandas as pd
from pathlib import Path

app = Flask(__name__)

# Determine the path to the Excel file relative to this file
DATA_PATH = Path(__file__).resolve().parent.parent / '2025-6-20-iolp-buildings.xlsx'

# Load a subset of the building dataset with relevant fields
_df = pd.read_excel(
    DATA_PATH,
    usecols=[
        'Real Property Asset Name',
        'Street Address',
        'City',
        'State',
        'Construction Date',
        'Owned or Leased'
    ]
)

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
    'Owned or Leased': 'owned_or_leased'
})

@app.route('/')
def properties_page():
    """Render the table page."""
    return render_template('properties.html')

@app.route('/api/properties')
def properties_api():
    """Return the dataset as JSON for DataTables."""
    return jsonify(_df[['name', 'Address', 'construction_date', 'owned_or_leased']].to_dict(orient='records'))

if __name__ == '__main__':
    app.run(debug=True)
