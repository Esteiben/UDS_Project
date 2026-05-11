from config import DB_CONFIG
import psycopg2
import pandas as pd
from sqlalchemy import create_engine

DB_URL = f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
engine = create_engine(DB_URL)

# 1. Contar viajes en raw_taxi_trips
viajes = pd.read_sql_query("SELECT count(*) AS total FROM raw_taxi_trips;", engine)
print(f"Viajes totales en raw_taxi_trips: {viajes['total'][0]}")

# 2. Ver zonas disponibles
zonas = pd.read_sql_query("SELECT count(*) AS total FROM taxi_zones;", engine)
print(f"Zonas en taxi_zones: {zonas['total'][0]}")

# 3. Ver algunos LocationID únicos en raw_taxi_trips
ids = pd.read_sql_query("SELECT DISTINCT PULocationID FROM raw_taxi_trips LIMIT 10;", engine)
print("Ejemplos de PULocationID en viajes:", ids['pulocationid'].tolist())

# 4. Probar el JOIN manualmente
join_result = pd.read_sql_query("""
    SELECT tz.Zone, AVG(CASE WHEN t.tip_amount > 0 THEN 1 ELSE 0 END) as avg_tips
    FROM raw_taxi_trips t
    JOIN taxi_zones tz ON t.PULocationID = tz.LocationID
    GROUP BY tz.Zone ORDER BY avg_tips DESC LIMIT 10;
""", engine)
print(f"Filas obtenidas del JOIN: {len(join_result)}")
if not join_result.empty:
    print(join_result.head())