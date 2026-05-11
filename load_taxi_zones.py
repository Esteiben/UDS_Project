import pandas as pd
import psycopg2
from config import DB_CONFIG 

URL_ZONES = "https://d37ci6vzurychx.cloudfront.net/misc/taxi+_zone_lookup.csv"
df = pd.read_csv(URL_ZONES)

conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()

for _, row in df.iterrows():
    cur.execute("""
        INSERT INTO taxi_zones (LocationID, Borough, Zone, service_zone)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (LocationID) DO NOTHING;
    """, (row['LocationID'], row['Borough'], row['Zone'], row['service_zone']))

conn.commit()
cur.close()
conn.close()
print(f"Se insertaron {len(df)} zonas en taxi_zones.")