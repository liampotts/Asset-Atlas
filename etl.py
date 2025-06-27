import pandas as pd
import sqlite3
import re

# Load Excel data
buildings = pd.read_excel('2025-6-20-iolp-buildings.xlsx')
leases = pd.read_excel('2025-6-20-iolp-leases.xlsx')

# Clean building names by removing street address if it appears in the name
# This is a simple heuristic and may not perfectly cleanse all names.
def clean_asset_name(row):
    name = row['Real Property Asset Name']
    addr = row['Street Address']
    if isinstance(name, str) and isinstance(addr, str):
        pattern = re.escape(addr.strip())
        cleaned = re.sub(pattern, '', name, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r'\s+', ' ', cleaned)
        return cleaned
    return name

buildings['Clean Asset Name'] = buildings.apply(clean_asset_name, axis=1)

# Create SQLite database
conn = sqlite3.connect('asset_atlas.db')
cur = conn.cursor()

# Addresses table
cur.execute('''
CREATE TABLE IF NOT EXISTS addresses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    street_address TEXT,
    city TEXT,
    state TEXT,
    zip_code TEXT,
    latitude REAL,
    longitude REAL,
    congressional_district TEXT,
    congressional_rep TEXT,
    UNIQUE(street_address, city, state, zip_code)
)
''')

# Properties table
cur.execute('''
CREATE TABLE IF NOT EXISTS properties (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    location_code TEXT UNIQUE,
    asset_name TEXT,
    clean_asset_name TEXT,
    installation_name TEXT,
    owned_or_leased TEXT,
    gsa_region TEXT,
    address_id INTEGER,
    rentable_sqft REAL,
    available_sqft REAL,
    construction_date TEXT,
    building_status TEXT,
    asset_type TEXT,
    FOREIGN KEY(address_id) REFERENCES addresses(id)
)
''')

# Leases table
cur.execute('''
CREATE TABLE IF NOT EXISTS leases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id INTEGER,
    federal_leased_code TEXT,
    lease_number TEXT,
    lease_effective_date TEXT,
    lease_expiration_date TEXT,
    FOREIGN KEY(property_id) REFERENCES properties(id)
)
''')
conn.commit()

# Helper: get or create address
def get_address_id(row):
    cur.execute('''SELECT id FROM addresses WHERE street_address=? AND city=? AND state=? AND zip_code=?''',
                (row['Street Address'], row['City'], row['State'], str(row['Zip Code'])))
    res = cur.fetchone()
    if res:
        return res[0]
    cur.execute('''INSERT INTO addresses (street_address, city, state, zip_code, latitude, longitude,
                   congressional_district, congressional_rep)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                (row['Street Address'], row['City'], row['State'], str(row['Zip Code']),
                 row['Latitude'], row['Longitude'],
                 row.get('Congressional District'), row.get('Congressional District Representative Name') or row.get('Congressional District Representative')))
    conn.commit()
    return cur.lastrowid

# Insert buildings as properties
for _, row in buildings.iterrows():
    addr_id = get_address_id(row)
    cur.execute('''INSERT OR IGNORE INTO properties
                (location_code, asset_name, clean_asset_name, installation_name,
                 owned_or_leased, gsa_region, address_id, rentable_sqft, available_sqft,
                 construction_date, building_status, asset_type)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (row['Location Code'], row['Real Property Asset Name'], row['Clean Asset Name'],
                 row['Installation Name'], row['Owned or Leased'], row['GSA Region'], addr_id,
                 row['Building Rentable Square Feet'], row['Available Square Feet'],
                 row.get('Construction Date'), row.get('Building Status'), row['Real Property Asset Type']))
conn.commit()

# Map location code to property id
code_to_id = {r[1]: r[0] for r in cur.execute('SELECT id, location_code FROM properties')}

# Insert leases
for _, row in leases.iterrows():
    prop_id = code_to_id.get(row['Location Code'])
    if not prop_id:
        addr_id = get_address_id(row)
        clean_name = clean_asset_name(row)
        cur.execute('''INSERT OR IGNORE INTO properties
                    (location_code, asset_name, clean_asset_name, installation_name,
                     owned_or_leased, gsa_region, address_id, rentable_sqft, available_sqft,
                     construction_date, building_status, asset_type)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (row['Location Code'], row['Real Property Asset Name'], clean_name,
                     row['Installation Name'], 'L', row['GSA Region'], addr_id,
                     row['Building Rentable Square Feet'], row['Available Square Feet'],
                     None, None, row['Real Property Asset type']))
        conn.commit()
        prop_id = cur.lastrowid
        code_to_id[row['Location Code']] = prop_id
    cur.execute('''INSERT INTO leases
                (property_id, federal_leased_code, lease_number, lease_effective_date, lease_expiration_date)
                VALUES (?, ?, ?, ?, ?)''',
                (prop_id, row['Federal Leased Code'], row['Lease Number'],
                 str(row.get('Lease Effective Date')), str(row.get('Lease Expiration Date'))))
conn.commit()
conn.close()
print('Database created as asset_atlas.db')
