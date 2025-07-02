# Asset Atlas

This repository contains data from the General Services Administration's
**Inventory of Owned and Leased Properties (IOLP)**.  The Excel files
`2025-6-20-iolp-buildings.xlsx` and `2025-6-20-iolp-leases.xlsx` were
exported from the IOLP website.

The accompanying XML metadata explains each field of the datasets.  It
notes in part:

```
The Owned and Leased Data Sets include the following data except where
noted below for Leases:Location Code - GSA’s alphanumeric identifier for
the buildingReal Property Asset Name - Allows users to find information
about a specific building Installation Name - Allows users to identify
whether a property is part of an installation, such as a campusOwned or
Leased - Indicates the building is federally owned (F) or leased (L)GSA
Region - GSA assigned region for building locationStreet Address -
Building addressCity - Building CityState - Building StateZip Code -
Building ZipLatitude and Longitude - Map coordinates of the building
(only through .csv export)Rentable Square Feet - Total rentable square
feet in buildingAvailable Square Feet - Vacant space in building
Construction Date (Owned Only)- Year builtCongressional District -
Congressional District building is locatedRepresentative -
Representative of the Congressional DistrictBuilding Status (Owned
Only)- Indicates building is activeLease Number (Leased Only) - GSA’s
alphanumeric identifier for the leaseLease Effective/Expiration Dates
(Leased Only) - Date lease starts/expiresReal Property Asset Type -
Identifies a property as land, building, or structure
```

## Database creation

Run the ETL script after installing its Python dependencies:

```bash
pip install pandas openpyxl
python etl.py
```

The script reads both spreadsheets, cleans the building names and
creates `asset_atlas.db`, a SQLite database with the following tables:

- **addresses** – unique combination of street address, city, state,
  and ZIP code with geolocation and congressional district data.
- **properties** – building details keyed by the IOLP `Location Code`.
  Each property references an address and includes both the original and
  cleaned asset name.
- **leases** – lease information for properties that are leased.

## Cleaning building names

Building names sometimes contain the address.  The script attempts to
remove the street address from the `Real Property Asset Name` column with
this heuristic:

```python
pattern = re.escape(addr.strip())
cleaned = re.sub(pattern, '', name, flags=re.IGNORECASE).strip()
cleaned = re.sub(r'\s+', ' ', cleaned)
```

Because addresses vary in format (for example `AVENUE` vs `AVE`), the
result is not perfect but it captures many cases.

## Simple web interface

The `webapp` directory contains a small Flask application that loads the
building spreadsheet and exposes a page to explore the data.  Install
the dependencies listed in `requirements.txt` and run `webapp/app.py`:

```bash
pip install -r requirements.txt
python webapp/app.py
```

Navigate to <http://localhost:5000/> to see a filterable table showing
property name, address, construction date, and whether the building is
owned or leased.  The interface now uses Bootstrap and DataTables for a
modern look with sorting and paging controls.  A navigation bar at the
top provides links to an **Owned Dashboard** and a new **Leased Dashboard**
showing lease terms as an interactive Gantt chart alongside a table of
leases.
