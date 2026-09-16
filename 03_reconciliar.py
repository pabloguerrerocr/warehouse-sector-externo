"""Verifica que el warehouse reproduce el panel validado del TFG.

    python 03_reconciliar.py

Si esto pasa, el SQL no rompio nada al mover los datos. Es la unica prueba que
importa: cualquiera puede cargar una base, lo dificil es cargarla sin alterar
un solo numero.
"""
import os
import sys

import duckdb
import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

AQUI = os.path.dirname(os.path.abspath(__file__))
TFG = os.path.join(os.path.dirname(AQUI), "tfg-sector-externo", "data", "procesado")
TOL = 1e-9

con = duckdb.connect(os.path.join(AQUI, "sector_externo.duckdb"))
fallas = []


def comparar(nombre, esperado, obtenido, clave):
    j = esperado.merge(obtenido, on=clave, how="outer", indicator=True)
    huerf = (j["_merge"] != "both").sum()
    d = float(np.nanmax(np.abs(j["esperado"] - j["obtenido"]))) if len(j) else 0.0
    ok = huerf == 0 and d <= TOL
    print(f"  {'OK ' if ok else 'MAL'} {nombre:34} dif={d:.2e}  filas={len(j)}"
          + (f"  SIN PAREJA={huerf}" if huerf else ""))
    if not ok:
        fallas.append(nombre)


print("Panel mensual — cada serie contra fact_observacion")
m = pd.read_csv(os.path.join(TFG, "panel_mensual.csv"), parse_dates=["fecha"])
sql_m = con.execute("SELECT serie_id, fecha, valor FROM fact_observacion").df()
sql_m["fecha"] = pd.to_datetime(sql_m["fecha"])
# pib_eeuu es trimestral: el panel mensual lo propaga hacia adelante. El
# warehouse no guarda valores derivados, asi que se reconstruye en SQL uniendo
# cada mes con el trimestre al que pertenece.
ffill = con.execute("""
    SELECT o.serie_id, f.fecha, o.valor
    FROM dim_fecha f
    JOIN fact_observacion o
      ON o.serie_id = 'pib_eeuu'
     AND o.fecha = DATE_TRUNC('quarter', f.fecha)
""").df()
ffill["fecha"] = pd.to_datetime(ffill["fecha"])
sql_m = pd.concat([sql_m[sql_m.serie_id != "pib_eeuu"], ffill], ignore_index=True)

for col in m.columns.drop("fecha"):
    s = sql_m[sql_m.serie_id == col]
    if s.empty:
        continue
    comparar(col,
             m[["fecha", col]].rename(columns={col: "esperado"}),
             s[["fecha", "valor"]].rename(columns={"valor": "obtenido"}),
             "fecha")

print("\nPanel trimestral — agregado EN SQL desde el grano mas fino")
q = pd.read_csv(os.path.join(TFG, "panel_trimestral.csv"), parse_dates=["fecha"])
# Las diarias se promedian desde el dia; las demas, desde su propia frecuencia.
sql_q = con.execute("""
    WITH diarias AS (
        SELECT serie_id, DATE_TRUNC('quarter', fecha) AS fecha, AVG(valor) AS valor
        FROM fact_observacion_diaria GROUP BY 1, 2
    ), resto AS (
        SELECT o.serie_id, DATE_TRUNC('quarter', o.fecha) AS fecha, AVG(o.valor) AS valor
        FROM fact_observacion o
        WHERE o.serie_id NOT IN (SELECT DISTINCT serie_id FROM fact_observacion_diaria)
        GROUP BY 1, 2
    )
    SELECT * FROM diarias UNION ALL SELECT * FROM resto
""").df()
sql_q["fecha"] = pd.to_datetime(sql_q["fecha"])
for col in q.columns.drop("fecha"):
    s = sql_q[sql_q.serie_id == col]
    if s.empty:
        continue
    comparar(col,
             q[["fecha", col]].rename(columns={col: "esperado"}),
             s[["fecha", "valor"]].rename(columns={"valor": "obtenido"}),
             "fecha")

con.close()
print("\n" + "=" * 62)
if fallas:
    sys.exit(f"FALLARON {len(fallas)}: {', '.join(fallas)}")
print("VEREDICTO: el warehouse reproduce el panel validado, dato por dato.")
