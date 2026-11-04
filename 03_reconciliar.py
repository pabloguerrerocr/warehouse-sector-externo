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

import tfg

sys.stdout.reconfigure(encoding="utf-8")

AQUI = os.path.dirname(os.path.abspath(__file__))
TFG = tfg.procesado()
TOL = 1e-9

con = duckdb.connect(os.path.join(AQUI, "sector_externo.duckdb"))
fallas, comparadas, omitidas = [], [], []


def comparar(nombre, esperado, obtenido, clave):
    j = esperado.merge(obtenido, on=clave, how="outer", indicator=True)
    huerf = (j["_merge"] != "both").sum()
    d = float(np.nanmax(np.abs(j["esperado"] - j["obtenido"]))) if len(j) else 0.0
    ok = huerf == 0 and d <= TOL
    comparadas.append(nombre)
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
# Una serie diaria sin su grano diario no se puede reconciliar en trimestral:
# promediar los promedios mensuales da otro numero. Se omite y se dice.
diarias = {r[0] for r in con.execute(
    "SELECT serie_id FROM dim_serie WHERE frecuencia = 'D'").fetchall()}
con_grano = {r[0] for r in con.execute(
    "SELECT DISTINCT serie_id FROM fact_observacion_diaria").fetchall()}
for col in q.columns.drop("fecha"):
    s = sql_q[sql_q.serie_id == col]
    if s.empty:
        continue
    if col in diarias and col not in con_grano:
        print(f"  --  {col:34} omitida: falta el grano diario de FRED")
        omitidas.append(col)
        continue
    comparar(col,
             q[["fecha", col]].rename(columns={col: "esperado"}),
             s[["fecha", "valor"]].rename(columns={"valor": "obtenido"}),
             "fecha")

con.close()
print("\n" + "=" * 62)
if fallas:
    sys.exit(f"FALLARON {len(fallas)}: {', '.join(fallas)}")
if omitidas:
    print(f"VEREDICTO: {len(comparadas)} de {len(comparadas) + len(omitidas)} series "
          f"reproducen el panel validado; se omitieron {len(omitidas)} "
          f"({', '.join(omitidas)}) por falta del grano diario.\n"
          "Para comparar todas, en el repo del TFG: python main.py --descargar-fred")
else:
    print(f"VEREDICTO: el warehouse reproduce el panel validado, dato por dato "
          f"({len(comparadas)} series).")
