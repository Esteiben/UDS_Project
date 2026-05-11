import pandas as pd
import glob

# Listar todos los archivos .parquet en la carpeta data/
archivos = glob.glob("data/green_tripdata_2023-*.parquet")
print("Archivos encontrados:", archivos)

# Leer y concatenar
df_total = pd.concat([pd.read_parquet(f) for f in archivos], ignore_index=True)
print(f"Total de registros combinados: {len(df_total)}")

# Guardar el dataset unificado (se puede guardar como parquet o CSV)
df_total.to_parquet("data/green_tripdata_2023_combined.parquet", index=False)
print("Archivo combinado guardado en data/green_tripdata_2023_combined.parquet")
