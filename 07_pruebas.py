"""FASE 4 — Construye el warehouse desde cero y lo prueba.

    python 07_pruebas.py

Sale con codigo 1 si algo falla, para poder colgarlo de un hook de git o de CI.
Las pruebas que importan son las de reconciliacion: verifican que el SQL produce
exactamente lo mismo que el pipeline de Python ya validado.
"""
import os
import subprocess
import sys

import duckdb
import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

AQUI = os.path.dirname(os.path.abspath(__file__))
TFG = os.path.join(os.path.dirname(AQUI), "tfg-sector-externo", "data", "procesado")
BD = os.path.join(AQUI, "sector_externo.duckdb")
TOL = 1e-9

fallas = []


def prueba(nombre, condicion, detalle=""):
    print(f"  {'OK ' if condicion else 'MAL'} {nombre}" + (f"  {detalle}" if detalle else ""))
    if not condicion:
        fallas.append(nombre)


print("Reconstruyendo desde cero")
for script in ("02_cargar.py", "04_crudo_acumulado.py"):
    r = subprocess.run([sys.executable, os.path.join(AQUI, script)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    prueba(f"corre {script}", r.returncode == 0, r.stderr.strip()[-120:] if r.returncode else "")

con = duckdb.connect(BD)
for sql in ("05_transformar.sql", "06_calidad.sql"):
    try:
        con.execute(open(os.path.join(AQUI, sql), encoding="utf-8").read())
        prueba(f"aplica {sql}", True)
    except Exception as e:
        prueba(f"aplica {sql}", False, str(e)[:120])

print("\nIntegridad del esquema")
n = con.execute("SELECT COUNT(*) FROM dim_serie").fetchone()[0]
prueba("dim_serie tiene 12 series", n == 12, f"({n})")
huerf = con.execute("""SELECT COUNT(*) FROM fact_observacion o
                       LEFT JOIN dim_serie s USING (serie_id)
                       WHERE s.serie_id IS NULL""").fetchone()[0]
prueba("sin observaciones huerfanas", huerf == 0, f"({huerf})")
dup = con.execute("""SELECT COUNT(*) FROM (SELECT serie_id, fecha FROM fact_observacion
                     GROUP BY 1,2 HAVING COUNT(*) > 1)""").fetchone()[0]
prueba("sin duplicados en fact_observacion", dup == 0, f"({dup})")

print("\nReconciliacion contra el panel validado en Python")
m = pd.read_csv(os.path.join(TFG, "panel_mensual.csv"), parse_dates=["fecha"])
sqlm = con.execute("SELECT serie_id, fecha, valor FROM v_mensual").df()
sqlm["fecha"] = pd.to_datetime(sqlm["fecha"])
for col in ("balcom", "export_cr", "ffr", "tpm", "reservas", "itcer", "tc_venta", "ipi_eeuu"):
    s = sqlm[sqlm.serie_id == col]
    if s.empty:
        prueba(f"{col} presente en v_mensual", False)
        continue
    j = m[["fecha", col]].merge(s, on="fecha")
    d = float(np.abs(j[col] - j["valor"]).max())
    prueba(f"{col:10} reconcilia", d <= 1e-8 and len(j) == 132, f"dif={d:.1e} n={len(j)}")

print("\nReglas de negocio")
desc = con.execute("""
    WITH c AS (SELECT serie_id, YEAR(fecha) AS anio, SUM(flujo) AS suma,
                      MAX(CASE WHEN MONTH(fecha)=12 THEN acumulado END) AS dic
               FROM v_desacumulado GROUP BY 1,2)
    SELECT COUNT(*) FROM c WHERE dic IS NOT NULL AND ABS(suma - dic) > 1e-6
""").fetchone()[0]
prueba("la suma de flujos reproduce el acumulado de diciembre", desc == 0, f"({desc} descuadres)")

err = con.execute("SELECT COUNT(*) FROM reporte_calidad WHERE severidad='error'").fetchone()[0]
prueba("el reporte de calidad no tiene errores", err == 0, f"({err})")

avisos = con.execute("SELECT COUNT(*) FROM reporte_calidad WHERE severidad='aviso'").fetchone()[0]
print(f"\n  ({avisos} avisos — son choques macro reales, no errores de dato)")

con.close()
print("\n" + "=" * 60)
if fallas:
    sys.exit(f"FALLARON {len(fallas)}: {', '.join(fallas)}")
print("TODAS LAS PRUEBAS PASAN")
