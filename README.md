🚖 Urban Data Solutions (UDS) - Proyecto de Construcción de Software
Sexto Semestre | TareaF 01
Análisis de movilidad urbana con datos de taxis de NYC

📌 Descripción
Plataforma web para la gestión y análisis de datos de taxis verdes de Nueva York (2023).
Permite cargar más de 400,000 registros, gestionar clientes y conductores, generar reportes PDF y detectar alertas de calidad, todo sobre una base de datos PostgreSQL.

🛠️ Tecnologías
Backend: Python 3, Flask, psycopg2, SQLAlchemy, Pandas, ReportLab

Base de datos: PostgreSQL

Frontend: HTML5, Bootstrap 5, Font Awesome, Matplotlib (gráficos dinámicos)

Datos: NYC TLC Green Taxi Trip Records (2023)

📁 Estructura del proyecto
text
UDS_Project/
├── app.py                  # Aplicación Flask (rutas, gráficos, CRUD)
├── uds_data_manager.py     # Script de creación de tablas e ingesta de datos
├── templates/              # Plantillas HTML (dashboard, clientes, reportes, etc.)
├── static/reports/         # PDFs generados
├── data/                   # Datasets Parquet (no incluidos)
├── config.example.py       # Ejemplo de configuración (sin credenciales reales)
└── .gitignore
⚙️ Instalación rápida
Clonar el repositorio e instalar dependencias:

bash
git clone https://github.com/Esteiben/UDS.git
cd UDS_Project
python -m venv venv
source venv/bin/activate   # En Windows: venv\Scripts\activate
pip install -r requirements.txt  # (si existe) o manualmente: pandas, psycopg2-binary, flask, sqlalchemy, matplotlib, reportlab
Configurar la base de datos PostgreSQL y crear la BD uds_analytics.

Copiar config.example.py a config.py y ajustar las credenciales.

Ejecutar el script de creación de tablas e ingesta:

bash
python uds_data_manager.py
Iniciar la aplicación:

bash
python app.py
Abrir http://127.0.0.1:5000 en el navegador.

📊 Funcionalidades
Dashboard con KPIs y gráficos de toma de decisiones

CRUD de clientes y conductores (modales con validación)

Generación de reportes PDF con datos reales de viajes

Sistema de alertas automáticas sobre anomalías en los datos

Carga de archivos CSV/Parquet para actualizar los datos

👤 Autor
Estiben - GitHub
