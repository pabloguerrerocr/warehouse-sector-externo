"""Carga las series ACUMULADAS tal como las publica el BCCR.

El BCCR publica el balance comercial y las exportaciones acumulados dentro del
ano: enero trae enero, febrero trae enero+febrero, y asi hasta diciembre, que
trae el ano completo. Para analizar hace falta el flujo del mes.

Este script guarda el crudo sin tocarlo. La desacumulacion se hace despues,
en SQL, con una funcion de ventana (05_transformar.sql).
"""
import os
import sys

import duckdb
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

AQUI = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(os.path.dirname(AQUI), "tfg-sector-externo", "data", "raw")
BD = os.path.join(AQUI, "sector_externo.duckdb")

# serie_id -> (archivo, indice de la columna de valores en el cuadro)
ACUMULADAS = {
    "balcom": ("balance_comercial.xlsx", 1),
    "export_cr": ("exportaciones.xlsx", 5),
}


def leer_cuadro(ruta, columna):
    """Lee el formato del portal del BCCR: encabezado en la fila que dice 'Fecha'."""
    crudo = pd.read_excel(ruta, sheet_name=0, header=None)
    fila = next(i for i in range(min(15, len(crudo)))
                if str(crudo.iloc[i, 0]).strip().lower().startswith("fecha"))
    df = pd.read_excel(ruta, sheet_name=0, header=fila)
    df = df.iloc[:, [0, columna]]
    df.columns = ["fecha", "valor"]
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
    return df.dropna()


con = duckdb.connect(BD)
con.execute("""
    CREATE OR REPLACE TABLE fact_acumulado_crudo (
        serie_id VARCHAR NOT NULL REFERENCES dim_serie(serie_id),
        fecha    DATE    NOT NULL,
        valor    DOUBLE  NOT NULL,   -- acumulado en el ano, tal como lo publica el BCCR
        PRIMARY KEY (serie_id, fecha)
    )""")

for serie_id, (archivo, col) in ACUMULADAS.items():
    ruta = os.path.join(RAW, archivo)
    if not os.path.exists(ruta):
        print(f"  aviso: falta {archivo}")
        continue
    d = leer_cuadro(ruta, col)
    d = d[(d["fecha"] >= "2015-01-01") & (d["fecha"] <= "2025-12-31")]
    d.insert(0, "serie_id", serie_id)
    con.execute("INSERT INTO fact_acumulado_crudo SELECT serie_id, fecha, valor FROM d")

print(con.execute("""
    SELECT serie_id, COUNT(*) AS obs, MIN(fecha) AS desde, MAX(fecha) AS hasta,
           ROUND(MIN(valor), 1) AS min, ROUND(MAX(valor), 1) AS max
    FROM fact_acumulado_crudo GROUP BY 1 ORDER BY 1
""").df().to_string(index=False))

print("\nSe ve el patron acumulado en 2024 (balcom):")
print(con.execute("""
    SELECT MONTH(fecha) AS mes, ROUND(valor, 1) AS acumulado
    FROM fact_acumulado_crudo
    WHERE serie_id = 'balcom' AND YEAR(fecha) = 2024
    ORDER BY 1 LIMIT 4
""").df().to_string(index=False))
con.close()
