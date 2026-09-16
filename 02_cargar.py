"""Carga el panel del TFG al warehouse en DuckDB.

    python 02_cargar.py

Lee los CSV ya validados de tfg-sector-externo y los pasa de formato ancho
(una columna por variable) a largo (una fila por serie, fecha y valor).
"""
import os
import sys

import duckdb
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

AQUI = os.path.dirname(os.path.abspath(__file__))
TFG = os.path.join(os.path.dirname(AQUI), "tfg-sector-externo", "data", "procesado")
BD = os.path.join(AQUI, "sector_externo.duckdb")

if not os.path.isdir(TFG):
    sys.exit(f"No encuentro los CSV del TFG en {TFG}")

con = duckdb.connect(BD)
con.execute(open(os.path.join(AQUI, "01_esquema.sql"), encoding="utf-8").read())

# ------------------------------------------------------------------ dim_serie
origen = pd.read_csv(os.path.join(TFG, "origen_de_los_datos.csv"))
origen["proveedor"] = origen["origen"].str.split(" - ").str[0].str.strip()
origen = origen.rename(columns={"variable": "serie_id"})[
    ["serie_id", "etiqueta", "frecuencia", "origen", "proveedor", "titulo_original"]]
con.execute("INSERT INTO dim_serie SELECT * FROM origen")

# ------------------------------------------------------------------ largo
paneles = {"panel_mensual.csv": "M", "panel_trimestral.csv": "Q"}
largo = []
for archivo in paneles:
    ruta = os.path.join(TFG, archivo)
    if not os.path.exists(ruta):
        print(f"  aviso: falta {archivo}, se omite")
        continue
    df = pd.read_csv(ruta, parse_dates=["fecha"])
    l = df.melt(id_vars="fecha", var_name="serie_id", value_name="valor")
    l["archivo"] = archivo
    largo.append(l)

largo = pd.concat(largo, ignore_index=True)

# El panel trimestral repite las series mensuales agregadas; nos quedamos con
# la observacion del panel que corresponde a la frecuencia declarada de la serie.
frec = dict(zip(origen["serie_id"], origen["frecuencia"]))
largo["frec_serie"] = largo["serie_id"].map(frec)
largo = largo[
    ((largo["archivo"] == "panel_trimestral.csv") & (largo["frec_serie"] == "Q"))
    | ((largo["archivo"] == "panel_mensual.csv") & (largo["frec_serie"] != "Q"))
].drop(columns=["archivo", "frec_serie"])
largo = largo.drop_duplicates(subset=["serie_id", "fecha"])

# ------------------------------------------------------------------ dim_fecha
fechas = pd.DataFrame({"fecha": sorted(largo["fecha"].unique())})
fechas["anio"] = fechas["fecha"].dt.year
fechas["trimestre"] = fechas["fecha"].dt.quarter
fechas["mes"] = fechas["fecha"].dt.month
fechas["fin_de_anio"] = fechas["mes"] == 12
con.execute("INSERT INTO dim_fecha SELECT * FROM fechas")

con.execute("INSERT INTO fact_observacion SELECT serie_id, fecha, valor FROM largo")

# ------------------------------------------------------------------ resumen
print("Cargado en", BD, "\n")
for t in ("dim_serie", "dim_fecha", "fact_observacion"):
    print(f"  {t:18} {con.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]:>6} filas")

print("\nPor serie:")
print(con.execute("""
    SELECT s.serie_id, s.frecuencia AS frec, COUNT(o.valor) AS obs,
           MIN(o.fecha) AS desde, MAX(o.fecha) AS hasta,
           COUNT(*) - COUNT(o.valor) AS nulos
    FROM dim_serie s LEFT JOIN fact_observacion o USING (serie_id)
    GROUP BY 1, 2 ORDER BY 2, 1
""").df().to_string(index=False))

con.close()


# ---------------------------------------------------------------- grano diario
# dataset.py agrega las series diarias de FRED (t2y, dolar) DIRECTO a trimestre,
# no de mensual a trimestre. Los meses tienen distinto numero de dias, asi que
# promediar dos veces no da lo mismo. Un warehouse guarda el grano mas fino que
# tenga disponible, y deja que cada agregacion salga de ahi.
CACHE = os.path.join(os.path.dirname(AQUI), "tfg-sector-externo",
                     "data", "raw", "cache")
DIARIAS = {"t2y": "fred_DGS2.csv", "dolar": "fred_DTWEXBGS.csv"}

con = duckdb.connect(BD)
con.execute("""
    CREATE OR REPLACE TABLE fact_observacion_diaria (
        serie_id VARCHAR NOT NULL REFERENCES dim_serie(serie_id),
        fecha    DATE    NOT NULL,
        valor    DOUBLE,
        PRIMARY KEY (serie_id, fecha)
    )""")

ini, fin = "2015-01-01", "2025-12-31"
for serie_id, archivo in DIARIAS.items():
    ruta = os.path.join(CACHE, archivo)
    if not os.path.exists(ruta):
        print(f"  aviso: falta {archivo}")
        continue
    d = pd.read_csv(ruta)
    d.columns = ["fecha", "valor"]
    d["fecha"] = pd.to_datetime(d["fecha"])
    d = d[(d["fecha"] >= ini) & (d["fecha"] <= fin)].dropna()
    d.insert(0, "serie_id", serie_id)
    con.execute("INSERT INTO fact_observacion_diaria SELECT serie_id, fecha, valor FROM d")

print("\nGrano diario:")
print(con.execute("""
    SELECT serie_id, COUNT(*) AS obs, MIN(fecha) AS desde, MAX(fecha) AS hasta
    FROM fact_observacion_diaria GROUP BY 1 ORDER BY 1
""").df().to_string(index=False))
con.close()
