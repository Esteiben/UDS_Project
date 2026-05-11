import psycopg2
import psycopg2.extras
import pandas as pd
import logging
from config import DB_CONFIG
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class UDSDataManager:
    """Gestor principal de datos para Urban Data Solutions."""
    
    def __init__(self):
        """Inicializa la conexión principal y crea las tablas si no existen."""
        self.conn = psycopg2.connect(**DB_CONFIG)
        self.cur = self.conn.cursor()
        logger.info("Conexión a PostgreSQL establecida exitosamente.")
        self._create_tables()

    def _create_tables(self):
        """Crea todas las tablas del modelo de negocio basadas en la taxonomía de la sección 2.2."""
        sql_commands = [
            # 1. Tabla contenedora RAW
            """
            CREATE TABLE IF NOT EXISTS raw_taxi_trips (
                trip_id SERIAL PRIMARY KEY,
                VendorID INT, lpep_pickup_datetime TIMESTAMP,
                lpep_dropoff_datetime TIMESTAMP, store_and_fwd_flag TEXT,
                RatecodeID FLOAT, PULocationID INT, DOLocationID INT,
                passenger_count FLOAT, trip_distance FLOAT, fare_amount FLOAT,
                extra FLOAT, mta_tax FLOAT, tip_amount FLOAT, tolls_amount FLOAT,
                ehail_fee FLOAT, improvement_surcharge FLOAT, total_amount FLOAT,
                payment_type FLOAT, trip_type FLOAT, congestion_surcharge FLOAT
            );""",
            # 2. Catálogo de zonas
            """
            CREATE TABLE IF NOT EXISTS taxi_zones (
                LocationID INT PRIMARY KEY, Borough TEXT, Zone TEXT, service_zone TEXT
            );""",
            # 3. Conductores
            """
            CREATE TABLE IF NOT EXISTS drivers (
                driver_id SERIAL PRIMARY KEY, first_name TEXT, last_name TEXT,
                license_number TEXT UNIQUE, hire_date DATE, rating FLOAT
            );""",
            # 4. Vehículos
            """
            CREATE TABLE IF NOT EXISTS vehicles (
                vehicle_id SERIAL PRIMARY KEY, make TEXT, model TEXT, year INT,
                color TEXT, plate_number TEXT UNIQUE, last_inspection_date DATE
            );""",
            # 5. Clientes corporativos
            """
            CREATE TABLE IF NOT EXISTS clients (
                client_id SERIAL PRIMARY KEY, company_name TEXT, contact_name TEXT,
                email TEXT UNIQUE, subscription_plan INT, contract_start DATE,
                contract_end DATE
            );""",
            # 6. Reportes generados
            """
            CREATE TABLE IF NOT EXISTS analytics_reports (
                report_id SERIAL PRIMARY KEY, client_id INT REFERENCES clients(client_id),
                report_type TEXT, generated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                parameters_used JSONB, file_path TEXT
            );""",
            # 7. Transacciones financieras
            """
            CREATE TABLE IF NOT EXISTS payment_transactions (
                transaction_id SERIAL PRIMARY KEY, trip_id INT REFERENCES raw_taxi_trips(trip_id),
                payment_method TEXT, card_type TEXT, transaction_status TEXT,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );""",
            # 8. Métricas de congestión
            """
            CREATE TABLE IF NOT EXISTS congestion_metrics (
                metric_id SERIAL PRIMARY KEY, location_id INT, hour_of_day INT,
                avg_speed FLOAT, trip_count INT, calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );""",
            # 9. Log de auditoría de usuarios
            """
            CREATE TABLE IF NOT EXISTS user_activity_log (
                log_id SERIAL PRIMARY KEY, user_id INT, action TEXT,
                entity_affected TEXT, log_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ip_address TEXT
            );""",
            # 10. Suscripciones
            """
            CREATE TABLE IF NOT EXISTS subscriptions (
                plan_id SERIAL PRIMARY KEY, plan_name TEXT UNIQUE, price NUMERIC(10,2),
                max_reports_monthly INT, features JSONB
            );""",
            # 11. Alertas del sistema
            """
            CREATE TABLE IF NOT EXISTS alerts (
                alert_id SERIAL PRIMARY KEY, alert_type TEXT, message TEXT,
                severity TEXT, is_read BOOLEAN DEFAULT FALSE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );""",
            # 12. Vista materializada para reportes de ingresos por cliente
            """
            CREATE MATERIALIZED VIEW IF NOT EXISTS mv_client_monthly_revenue AS
            SELECT c.client_id, c.company_name, DATE_TRUNC('month', pt.processed_at) AS month,
                   SUM(t.total_amount) AS total_revenue
            FROM raw_taxi_trips t
            JOIN payment_transactions pt ON t.trip_id = pt.trip_id
            JOIN clients c ON c.client_id = 1  -- Asume todos los viajes bajo UDS como proxy
            GROUP BY c.client_id, c.company_name, DATE_TRUNC('month', pt.processed_at);
            """
        ]
        for command in sql_commands:
            self.cur.execute(command)
        self.conn.commit()
        logger.info("Tablas y vistas verificadas/creadas.")

    def load_taxi_data(self, parquet_file_path, limit=100000):
        """
        Punto 2.1: Carga los datos del dataset Parquet en raw_taxi_trips.
        """
        logger.info(f"Iniciando ingesta de datos desde {parquet_file_path}...")
        df = pd.read_parquet(parquet_file_path)
        logger.info(f"Archivo leído. Columnas: {df.columns.tolist()}")
        if limit:
            df = df.head(limit)
        logger.info(f"Insertando {len(df)} filas...")

        tuples = [tuple(row) for row in df.itertuples(index=False, name=None)]
        insert_query = """
         INSERT INTO raw_taxi_trips (VendorID, lpep_pickup_datetime, lpep_dropoff_datetime,
          store_and_fwd_flag, RatecodeID, PULocationID, DOLocationID, passenger_count,
            trip_distance, fare_amount, extra, mta_tax, tip_amount, tolls_amount,
            ehail_fee, improvement_surcharge, total_amount, payment_type, trip_type,
            congestion_surcharge) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        psycopg2.extras.execute_batch(self.cur, insert_query, tuples)
        self.conn.commit()
        logger.info(f"Ingesta completada. {len(tuples)} registros insertados en raw_taxi_trips.")

    def crud_operations_example(self):
        """
        Punto 3: Demostración explícita de operaciones CREATE, READ, UPDATE, DELETE.
        """
        # --- CREATE ---
        insert_sql = """
            INSERT INTO alerts (alert_type, message, severity)
            VALUES (%s, %s, %s) RETURNING alert_id;
        """
        self.cur.execute(insert_sql, ("SYSTEM", "Demo de operación CRUD ejecutada.", "INFO"))
        new_alert_id = self.cur.fetchone()[0]
        self.conn.commit()
        logger.info(f"CREATE exitoso. Alert ID: {new_alert_id}")

        # --- READ ---
        select_sql = "SELECT alert_id, message, severity FROM alerts WHERE alert_id = %s;"
        self.cur.execute(select_sql, (new_alert_id,))
        alert = self.cur.fetchone()
        logger.info(f"READ exitoso. Alerta recuperada: {alert}")

        # --- UPDATE ---
        update_sql = "UPDATE alerts SET severity = %s, message = %s WHERE alert_id = %s;"
        self.cur.execute(update_sql, ("LOW", "CRUD demo actualizado.", new_alert_id))
        self.conn.commit()
        logger.info(f"UPDATE exitoso para Alert ID: {new_alert_id}")

        # --- DELETE ---
        delete_sql = "DELETE FROM alerts WHERE alert_id = %s;"
        self.cur.execute(delete_sql, (new_alert_id,))
        self.conn.commit()
        logger.info(f"DELETE exitoso para Alert ID: {new_alert_id}")

if __name__ == "__main__":
    manager = UDSDataManager()
    manager.load_taxi_data("data/green_tripdata_2023_combined.parquet", limit=500000)
    manager.crud_operations_example()
    logger.info("Script finalizado exitosamente.")