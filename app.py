from fileinput import filename

from flask import Flask, render_template, request, jsonify, redirect, send_file, url_for, send_file, send_from_directory
import psycopg2
import psycopg2.extras
import pandas as pd
import json
import io
import base64
import matplotlib
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
import os
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime
from sqlalchemy import create_engine
from config import DB_CONFIG 

app = Flask(__name__)
REPORTS_DIR = os.path.join(app.root_path, 'static', 'reports')
os.makedirs(REPORTS_DIR, exist_ok=True)

DB_URL = f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
engine = create_engine(DB_URL)

def get_db_connection():
    """Conexión nativa para operaciones que no son pandas (inserts, etc.)"""
    return psycopg2.connect(**DB_CONFIG)


def create_plot():
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Urban Data Solutions - Toma de Decisiones con Datos', fontsize=16)

    # 1. Top zonas con mayor promedio de propina
    df_zones = pd.read_sql_query("""
        SELECT tz.Zone, AVG(t.tip_amount) as avg_tip_amount
        FROM raw_taxi_trips t
        JOIN taxi_zones tz ON t.PULocationID = tz.LocationID
        WHERE t.tip_amount > 0
        GROUP BY tz.Zone ORDER BY avg_tip_amount DESC LIMIT 10;
    """, engine)

    print("DEBUG: df_zones shape", df_zones.shape)
    print("DEBUG: df_zones columns", df_zones.columns.tolist())
    print("DEBUG: first rows", df_zones.head())

    if not df_zones.empty and 'zone' in df_zones.columns:
        axes[0, 0].barh(df_zones['zone'], df_zones['avg_tip_amount'], color='skyblue')
        axes[0, 0].set_title('Top 10 Zonas con Mayor Promedio de Propina ($)')
        axes[0, 0].set_xlabel('Propina Promedio ($)')
        axes[0, 0].set_xlim(0, df_zones['avg_tip_amount'].max() * 1.2)
    else:
        axes[0, 0].text(0.5, 0.5, 'Sin datos (carga taxi_zones y raw_taxi_trips)', ha='center')
        axes[0, 0].set_title('Top 10 Zonas (sin datos)')

    # 2. Evolución tarifa media por día
    df_fare = pd.read_sql_query("""
        SELECT DATE(lpep_pickup_datetime) as trip_date, AVG(fare_amount) as avg_fare
        FROM raw_taxi_trips GROUP BY trip_date ORDER BY trip_date LIMIT 30;
    """, engine)
    if not df_fare.empty:
        axes[0, 1].plot(df_fare['trip_date'], df_fare['avg_fare'], marker='o', color='green')
        axes[0, 1].set_title('Evolución de Tarifa Media (Primeros 30 días)')
        axes[0, 1].tick_params(axis='x', rotation=45)
    else:
        axes[0, 1].text(0.5, 0.5, 'Sin viajes en raw_taxi_trips', ha='center')

    # 3. Alertas por severidad
    df_alerts = pd.read_sql_query("""
        SELECT severity, COUNT(*) as count FROM alerts GROUP BY severity;
    """, engine)
    if not df_alerts.empty:
        colors = {'LOW': 'gray', 'INFO': 'blue', 'WARNING': 'orange', 'CRITICAL': 'red'}
        ax = axes[1, 0]
        bars = ax.bar(df_alerts['severity'], df_alerts['count'])
        for bar, sev in zip(bars, df_alerts['severity']):
            bar.set_color(colors.get(sev, 'gray'))
        axes[1, 0].set_title('Conteo de Alertas por Severidad')
        axes[1, 0].set_ylabel('Número de Alertas')
    else:
        axes[1, 0].text(0.5, 0.5, 'Sin alertas', ha='center')

    # 4. Ingresos por tipo de pago
    df_payment = pd.read_sql_query("""
        SELECT payment_type, SUM(total_amount) as total FROM raw_taxi_trips
        WHERE payment_type IS NOT NULL GROUP BY payment_type;
    """, engine)
    if not df_payment.empty:
        axes[1, 1].pie(df_payment['total'], labels=df_payment['payment_type'], autopct='%1.1f%%')
        axes[1, 1].set_title('Distribución de Ingresos por Método de Pago')
    else:
        axes[1, 1].text(0.5, 0.5, 'Sin datos de pagos', ha='center')

    # Convertir gráfico a base64
    img = io.BytesIO()
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.savefig(img, format='png')
    img.seek(0)
    plt.close(fig)
    return base64.b64encode(img.getvalue()).decode()

@app.route('/')
def index():
    # Obtener KPIs con engine
    kpi_trips = pd.read_sql_query("SELECT COUNT(*) AS total FROM raw_taxi_trips;", engine)['total'][0]
    kpi_revenue = pd.read_sql_query("SELECT SUM(total_amount) AS total FROM raw_taxi_trips;", engine)['total'][0]
    kpi_zones = pd.read_sql_query("SELECT COUNT(DISTINCT PULocationID) AS zonas FROM raw_taxi_trips;", engine)['zonas'][0]
    kpi_avg_fare = pd.read_sql_query("SELECT AVG(fare_amount) AS avg_fare FROM raw_taxi_trips;", engine)['avg_fare'][0]

    # Formatear los valores para mostrar
    kpi_revenue_fmt = f"${kpi_revenue:,.2f}" if kpi_revenue else "$0.00"
    kpi_avg_fare_fmt = f"${kpi_avg_fare:.2f}" if kpi_avg_fare else "$0.00"
    kpi_trips_fmt = f"{kpi_trips:,}"
    kpi_zones_fmt = str(kpi_zones)

    plot_url = create_plot()
    return render_template('index.html',
                           plot_url=plot_url,
                           kpi_trips=kpi_trips_fmt,
                           kpi_revenue=kpi_revenue_fmt,
                           kpi_zones=kpi_zones_fmt,
                           kpi_avg_fare=kpi_avg_fare_fmt)

@app.route('/clients', methods=['GET'])
def list_clients():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT client_id, company_name, contact_name, email, subscription_plan FROM clients ORDER BY client_id;")
    clients = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('clients.html', clients=clients)

@app.route('/client/add', methods=['POST'])
def add_client():
    data = request.form
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO clients (company_name, contact_name, email, subscription_plan, contract_start, contract_end)
        VALUES (%s, %s, %s, %s, CURRENT_DATE, CURRENT_DATE + INTERVAL '1 year');
    """, (data['company_name'], data['contact_name'], data['email'], data['subscription_plan']))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('list_clients'))

@app.route('/client/delete/<int:client_id>', methods=['POST'])
def delete_client(client_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM clients WHERE client_id = %s;", (client_id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('list_clients'))

@app.route('/drivers')
def list_drivers():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT driver_id, first_name, last_name, license_number, hire_date, rating FROM drivers;")
    drivers = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('drivers.html', drivers=drivers)

@app.route('/driver/add', methods=['POST'])
def add_driver():
    data = request.form
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO drivers (first_name, last_name, license_number, hire_date, rating)
        VALUES (%s, %s, %s, CURRENT_DATE, %s);
    """, (data['first_name'], data['last_name'], data['license_number'], data['rating']))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('list_drivers'))

@app.route('/driver/delete/<int:driver_id>', methods=['POST'])
def delete_driver(driver_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM drivers WHERE driver_id = %s;", (driver_id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('list_drivers'))

@app.route('/reports')
def reports():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    # Obtener lista de reportes generados
    cur.execute("""
        SELECT r.report_id, r.client_id, c.company_name, r.report_type, r.generated_date, r.parameters_used, r.file_path
        FROM analytics_reports r
        LEFT JOIN clients c ON r.client_id = c.client_id
        ORDER BY r.generated_date DESC;
    """)
    reports_list = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('reports.html', reports=reports_list)

@app.route('/alerts')
def list_alerts():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("""
        SELECT alert_id, alert_type, message, severity, is_read, 
               created_at::timestamp(0) as created_at
        FROM alerts 
        ORDER BY 
            CASE severity 
                WHEN 'CRITICAL' THEN 1 
                WHEN 'HIGH' THEN 2 
                WHEN 'MEDIUM' THEN 3 
                WHEN 'LOW' THEN 4 
                ELSE 5 
            END,
            created_at DESC 
        LIMIT 50;
    """)
    alerts = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('alerts.html', alerts=alerts)

@app.route('/upload', methods=['GET', 'POST'])
def upload_csv():
    if request.method == 'POST':
        file = request.files['csv_file']
        if file.filename.endswith('.csv'):
            df = pd.read_csv(file)
        elif file.filename.endswith('.parquet'):
            df = pd.read_parquet(file)
        else:
            return "Formato no soportado", 400

        conn = get_db_connection()
        cur = conn.cursor()
        tuples = [tuple(row) for row in df.itertuples(index=False, name=None)]
        psycopg2.extras.execute_batch(cur, """
            INSERT INTO raw_taxi_trips (VendorID, lpep_pickup_datetime, lpep_dropoff_datetime,
            store_and_fwd_flag, RatecodeID, PULocationID, DOLocationID, passenger_count,
            trip_distance, fare_amount, extra, mta_tax, tip_amount, tolls_amount,
            ehail_fee, improvement_surcharge, total_amount, payment_type, trip_type,
            congestion_surcharge) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, tuples)
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('index'))
    return render_template('upload.html')

@app.route('/reports/generate')
def generate_reports():
    conn = get_db_connection()
    cur = conn.cursor()
    # Obtener el primer cliente (o podrías elegir de un formulario futuro)
    cur.execute("SELECT client_id FROM clients LIMIT 1;")
    client = cur.fetchone()
    if not client:
        cur.close()
        conn.close()
        return "Debe existir al menos un cliente para generar reportes.", 400
    client_id = client[0]

    # Consultar datos reales: resumen mensual de ingresos por zona para enero 2023
    cur.execute("""
        SELECT tz.Zone, COUNT(*) AS trips, SUM(t.total_amount) AS total_revenue
        FROM raw_taxi_trips t
        JOIN taxi_zones tz ON t.PULocationID = tz.LocationID
        WHERE t.lpep_pickup_datetime >= '2023-01-01' AND t.lpep_pickup_datetime < '2023-02-01'
        GROUP BY tz.Zone
        ORDER BY total_revenue DESC
        LIMIT 15;
    """)
    data = cur.fetchall()
    if not data:
        cur.close()
        conn.close()
        return "No hay datos de viajes para generar el reporte.", 400

    # Crear nombre de archivo único (incluye timestamp)
    filename = f"revenue_report_{client_id}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.pdf"
    filepath = os.path.join(REPORTS_DIR, filename)

    # Asegurarse de que no exista (por si acaso)
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
        except Exception as e:
            cur.close()
            conn.close()
            return f"Error al eliminar archivo previo: {str(e)}", 500

    try:
        # Generar PDF
        pdf = canvas.Canvas(filepath, pagesize=A4)
        pdf.setTitle("Reporte de Ingresos Mensuales - UDS")
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(50, 800, "Urban Data Solutions - Reporte de Ingresos Mensuales")
        pdf.setFont("Helvetica", 12)
        pdf.drawString(50, 775, f"Cliente ID: {client_id} - Mes: Enero 2023")
        pdf.drawString(50, 755, "Top 15 Zonas por Ingresos Totales:")

        # Construir tabla
        table_data = [["Zona", "Viajes", "Ingreso Total ($)"]]
        for row in data:
            table_data.append([row[0], str(row[1]), f"${row[2]:,.2f}"])
        table = Table(table_data, colWidths=[200, 80, 120])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.grey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (1,1), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 10),
            ('BOTTOMPADDING', (0,0), (-1,0), 12),
            ('GRID', (0,0), (-1,-1), 1, colors.black),
        ]))
        table.wrapOn(pdf, 450, 600)
        table.drawOn(pdf, 50, 500)
        pdf.save()
    except Exception as e:
        cur.close()
        conn.close()
        return f"Error al generar el PDF: {str(e)}", 500

    # Insertar registro en base de datos (solo el nombre del archivo)
    cur.execute("""
        INSERT INTO analytics_reports (client_id, report_type, parameters_used, file_path)
        VALUES (%s, 'Ingresos Mensuales', %s, %s)
    """, (client_id, '{"mes": "2023-01"}', filename))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('reports'))


@app.route('/alerts/generate')
def generate_alerts():
    conn = get_db_connection()
    cur = conn.cursor()
    # Buscar viajes con distancia 0 o negativa
    cur.execute("SELECT COUNT(*) FROM raw_taxi_trips WHERE trip_distance <= 0;")
    count = cur.fetchone()[0]
    if count > 0:
        cur.execute("""
            INSERT INTO alerts (alert_type, message, severity, is_read)
            VALUES ('CALIDAD', %s, 'HIGH', FALSE)
        """, (f'Se encontraron {count} viajes con distancia <= 0.',))
    # Buscar viajes con monto total negativo
    cur.execute("SELECT COUNT(*) FROM raw_taxi_trips WHERE total_amount < 0;")
    count = cur.fetchone()[0]
    if count > 0:
        cur.execute("""
            INSERT INTO alerts (alert_type, message, severity, is_read)
            VALUES ('FINANCIERO', %s, 'CRITICAL', FALSE)
        """, (f'Existen {count} viajes con monto total negativo.',))
    # Buscar viajes con propina excesiva (> 100 % de la tarifa)
    cur.execute("""
        SELECT COUNT(*) FROM raw_taxi_trips
        WHERE tip_amount > fare_amount AND fare_amount > 0;
    """)
    count = cur.fetchone()[0]
    if count > 0:
        cur.execute("""
            INSERT INTO alerts (alert_type, message, severity, is_read)
            VALUES ('FRAUDE', %s, 'MEDIUM', FALSE)
        """, (f'{count} viajes con propina mayor al 100%% de la tarifa.',))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('list_alerts'))

@app.route('/download_report/<int:report_id>')
def download_report(report_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT file_path FROM analytics_reports WHERE report_id = %s;", (report_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    if not result:
        return "Reporte no encontrado", 404
    filename = result[0]
    # send_from_directory busca el archivo en REPORTS_DIR
    return send_from_directory(REPORTS_DIR, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)