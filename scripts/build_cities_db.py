# scripts/build_cities_db.py
import csv, sqlite3, unicodedata, os, sys

CSV_PATH = os.getenv("CITIES_CSV_PATH", "worldcities.csv")
DB_PATH  = os.getenv("CITIES_DB_PATH", "world_cities.db")

# Map CSV column names to DB fields
COL = {
    "city": "city",
    "state": "admin_name",   # state / province / region
    "country": "country",
    "lat": "lat",
    "lon": "lng",
    "pop": "population",
}

def norm(s: str) -> str:
    """Normalize a string for consistent matching (remove accents, lowercase)."""
    if s is None:
        return ""
    s = s.strip().lower()
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    return " ".join(s.split())

def main():
    if not os.path.exists(CSV_PATH):
        print(f"CSV not found: {CSV_PATH}")
        sys.exit(1)

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Create the cities table
    cur.execute("""
        CREATE TABLE cities (
            city_norm    TEXT,
            state_norm   TEXT,
            country_norm TEXT,
            city         TEXT,
            state        TEXT,
            country      TEXT,
            latitude     REAL,
            longitude    REAL,
            population   INTEGER
        )
    """)
    cur.execute("CREATE INDEX idx_city_country ON cities (city_norm, country_norm)")
    cur.execute("CREATE INDEX idx_full ON cities (city_norm, state_norm, country_norm)")

    rows = 0
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            city    = row[COL["city"]].strip()
            state   = row.get(COL["state"], "").strip()
            country = row[COL["country"]].strip()
            lat     = float(row[COL["lat"]])
            lon     = float(row[COL["lon"]])

            # Handle blank or bad population values
            pop_str = row.get(COL["pop"], "").strip()
            try:
                pop = int(float(pop_str)) if pop_str else 0
            except:
                pop = 0

            cur.execute(
                "INSERT INTO cities VALUES (?,?,?,?,?,?,?,?,?)",
                (norm(city), norm(state), norm(country),
                 city, state, country, lat, lon, pop)
            )
            rows += 1

    conn.commit()
    conn.close()
    print(f"Built {DB_PATH} with {rows} rows from {CSV_PATH}")

if __name__ == "__main__":
    main()
