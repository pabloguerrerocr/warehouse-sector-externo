"""Ejercicios de SQL sobre tu propio warehouse, con correccion automatica.

    python ejercicios/ejercicios.py              # ver en cual vas
    python ejercicios/ejercicios.py 3            # ver el enunciado del 3
    python ejercicios/ejercicios.py 3 --pista    # una pista, sin la respuesta
    python ejercicios/ejercicios.py --corregir   # corregir todo lo que escribiste

Escribi tu respuesta en ejercicios/respuestas/NN.sql y corre --corregir.
La correccion compara tu resultado contra el esperado, no tu texto: si llegas
por otro camino y da lo mismo, esta bien.
"""
import os
import sys

import duckdb
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
AQUI = os.path.dirname(os.path.abspath(__file__))
BD = os.path.join(os.path.dirname(AQUI), "sector_externo.duckdb")
RESP = os.path.join(AQUI, "respuestas")
os.makedirs(RESP, exist_ok=True)

# Cada ejercicio: (tema, enunciado, pista, SQL de referencia)
E = [
 ("SELECT y WHERE",
  "Devolvé serie_id, fecha y valor de la tasa de politica monetaria del BCCR\n"
  "('tpm') solo para el ano 2022, ordenado por fecha. Usa fact_observacion.",
  "YEAR(fecha) te da el ano. Filtras dos condiciones con AND.",
  "SELECT serie_id, fecha, valor FROM fact_observacion "
  "WHERE serie_id='tpm' AND YEAR(fecha)=2022 ORDER BY fecha"),

 ("GROUP BY y agregacion",
  "Por cada serie, devolvé serie_id, cuantas observaciones tiene (obs),\n"
  "y su valor minimo y maximo. Ordenado por serie_id.",
  "COUNT(*), MIN(valor), MAX(valor) agrupando por serie_id.",
  "SELECT serie_id, COUNT(*) AS obs, MIN(valor) AS minimo, MAX(valor) AS maximo "
  "FROM fact_observacion GROUP BY serie_id ORDER BY serie_id"),

 ("HAVING",
  "Devolvé el anio y el promedio de la tasa de fondos federales ('ffr'),\n"
  "pero SOLO los anios cuyo promedio supero el 2 por ciento. Ordenado por anio.",
  "HAVING filtra DESPUES de agrupar; WHERE filtra antes. El promedio no existe\n"
  "hasta que se agrupa, asi que la condicion va en HAVING.",
  "SELECT YEAR(fecha) AS anio, AVG(valor) AS promedio FROM fact_observacion "
  "WHERE serie_id='ffr' GROUP BY 1 HAVING AVG(valor) > 2 ORDER BY 1"),

 ("JOIN",
  "Devolvé serie_id, etiqueta y el promedio del valor, uniendo fact_observacion\n"
  "con dim_serie. Solo las series del proveedor 'BCCR'. Ordenado por serie_id.",
  "JOIN ... USING (serie_id) y filtras por s.proveedor.",
  "SELECT o.serie_id, s.etiqueta, AVG(o.valor) AS promedio "
  "FROM fact_observacion o JOIN dim_serie s USING (serie_id) "
  "WHERE s.proveedor='BCCR' GROUP BY 1,2 ORDER BY 1"),

 ("LEFT JOIN para encontrar lo que falta",
  "El pib_eeuu es trimestral: solo tiene 44 observaciones contra 132 fechas.\n"
  "Devolvé las fechas de dim_fecha que NO tienen observacion de 'pib_eeuu'.\n"
  "Columna: fecha. Ordenado por fecha.",
  "LEFT JOIN de dim_fecha contra fact_observacion filtrado a pib_eeuu, y te\n"
  "quedas con las filas donde el lado derecho quedo en NULL.",
  "SELECT f.fecha FROM dim_fecha f "
  "LEFT JOIN fact_observacion o ON o.fecha=f.fecha AND o.serie_id='pib_eeuu' "
  "WHERE o.fecha IS NULL ORDER BY f.fecha"),

 ("LAG — cambio contra el mes anterior",
  "Para 'reservas' en 2024, devolvé fecha, valor, y el cambio contra el mes\n"
  "anterior (columna 'cambio'). El primer mes tendra NULL. Ordenado por fecha.\n"
  "Ojo: el mes anterior a enero 2024 es diciembre 2023, que si existe.",
  "LAG(valor) OVER (ORDER BY fecha) mira la fila anterior. Calcula la ventana\n"
  "sobre TODA la serie en un CTE y recien despues filtras el ano.",
  "WITH s AS (SELECT fecha, valor, valor - LAG(valor) OVER (ORDER BY fecha) AS cambio "
  "FROM fact_observacion WHERE serie_id='reservas') "
  "SELECT * FROM s WHERE YEAR(fecha)=2024 ORDER BY fecha"),

 ("LAG 12 — variacion interanual",
  "Para 'itcer', devolvé fecha y la variacion interanual en por ciento\n"
  "(columna 'var_pc'), redondeada a 2 decimales. Solo filas donde se pueda\n"
  "calcular. Ordenado por fecha.",
  "LAG(valor, 12) trae el mismo mes del ano pasado. La variacion es\n"
  "(valor/hace_un_anio - 1) * 100. Filtras los NULL al final.",
  "WITH s AS (SELECT fecha, valor, LAG(valor,12) OVER (ORDER BY fecha) AS previo "
  "FROM fact_observacion WHERE serie_id='itcer') "
  "SELECT fecha, ROUND((valor/previo - 1)*100, 2) AS var_pc FROM s "
  "WHERE previo IS NOT NULL ORDER BY fecha"),

 ("SUM OVER — acumulado corriente",
  "Para 'balcom' en 2023, devolvé fecha, valor y el acumulado del ano hasta ese\n"
  "mes (columna 'acumulado'). Ordenado por fecha.\n"
  "Esto reconstruye lo que el BCCR publica: por eso hay que desacumularlo.",
  "SUM(valor) OVER (ORDER BY fecha) suma todo lo anterior mas la fila actual.",
  "SELECT fecha, valor, SUM(valor) OVER (ORDER BY fecha) AS acumulado "
  "FROM fact_observacion WHERE serie_id='balcom' AND YEAR(fecha)=2023 ORDER BY fecha"),

 ("Marco de ventana — media movil",
  "Para 'tc_venta' en 2024, devolvé fecha, valor y la media movil de 3 meses\n"
  "(columna 'mm3') redondeada a 4 decimales. Ordenado por fecha.\n"
  "La media de enero usa solo enero; la de febrero, enero y febrero.",
  "AVG(valor) OVER (ORDER BY fecha ROWS BETWEEN 2 PRECEDING AND CURRENT ROW).\n"
  "Sin el ROWS BETWEEN, la ventana por defecto no es la que queres.",
  "SELECT fecha, valor, ROUND(AVG(valor) OVER (ORDER BY fecha "
  "ROWS BETWEEN 2 PRECEDING AND CURRENT ROW),4) AS mm3 "
  "FROM fact_observacion WHERE serie_id='tc_venta' AND YEAR(fecha)=2024 ORDER BY fecha"),

 ("ROW_NUMBER — el top N por grupo",
  "Por cada anio, devolvé el mes en que 'reservas' alcanzo su valor mas alto.\n"
  "Columnas: anio, fecha, valor. Ordenado por anio.",
  "ROW_NUMBER() OVER (PARTITION BY YEAR(fecha) ORDER BY valor DESC) numera\n"
  "dentro de cada anio. Te quedas con los que tienen numero 1.",
  "WITH s AS (SELECT YEAR(fecha) AS anio, fecha, valor, "
  "ROW_NUMBER() OVER (PARTITION BY YEAR(fecha) ORDER BY valor DESC) AS n "
  "FROM fact_observacion WHERE serie_id='reservas') "
  "SELECT anio, fecha, valor FROM s WHERE n=1 ORDER BY anio"),

 ("CTE encadenado — desacumular desde cero",
  "Usando fact_acumulado_crudo, devolvé para 'export_cr' en 2024: fecha (truncada\n"
  "a inicio de mes) y el flujo del mes (columna 'flujo'). En enero el flujo es el\n"
  "acumulado. Ordenado por fecha.\n"
  "Esta es la consulta que justifica todo el proyecto.",
  "LAG particionado POR ANO: LAG(valor) OVER (PARTITION BY YEAR(fecha) ORDER BY\n"
  "fecha). En enero LAG da NULL, y COALESCE(..., 0) lo convierte en cero.",
  "SELECT DATE_TRUNC('month', fecha) AS fecha, "
  "valor - COALESCE(LAG(valor) OVER (PARTITION BY YEAR(fecha) ORDER BY fecha),0) AS flujo "
  "FROM fact_acumulado_crudo WHERE serie_id='export_cr' AND YEAR(fecha)=2024 "
  "ORDER BY 1"),

 ("Calidad — detectar saltos anomalos",
  "Devolvé las observaciones de 'ipi_eeuu' cuyo cambio mensual se aparta mas de\n"
  "4 desviaciones estandar del cambio promedio de esa serie.\n"
  "Columnas: fecha, cambio. Ordenado por fecha.\n"
  "Esto es un chequeo de calidad real, no un ejercicio de juguete.",
  "Tres pasos en CTEs: 1) calcular el cambio con LAG. 2) calcular AVG y\n"
  "STDDEV_SAMP del cambio. 3) unir y filtrar con ABS(cambio-media)/de > 4.",
  "WITH d AS (SELECT fecha, valor - LAG(valor) OVER (ORDER BY fecha) AS cambio "
  "FROM fact_observacion WHERE serie_id='ipi_eeuu'), "
  "e AS (SELECT AVG(cambio) AS media, STDDEV_SAMP(cambio) AS de FROM d WHERE cambio IS NOT NULL) "
  "SELECT d.fecha, d.cambio FROM d, e WHERE d.cambio IS NOT NULL "
  "AND ABS(d.cambio - e.media)/e.de > 4 ORDER BY d.fecha"),
]


def norm(df):
    """Compara resultados, no texto: ordena, redondea y normaliza nombres."""
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    for c in df.columns:
        if pd.api.types.is_numeric_dtype(df[c]):
            df[c] = df[c].round(6)
        else:
            df[c] = df[c].astype(str)
    return df.sort_values(list(df.columns)).reset_index(drop=True)


def ruta(i):
    return os.path.join(RESP, f"{i:02d}.sql")


def mostrar(i, pista=False):
    tema, enun, hint, _ = E[i - 1]
    print(f"\n{'=' * 66}\nEJERCICIO {i} de {len(E)} · {tema}\n{'=' * 66}")
    print(enun)
    if pista:
        print(f"\nPISTA\n-----\n{hint}")
    print(f"\nEscribi tu respuesta en: ejercicios/respuestas/{i:02d}.sql")
    if not os.path.exists(ruta(i)):
        open(ruta(i), "w", encoding="utf-8").write(f"-- Ejercicio {i}: {tema}\n\n")


def corregir():
    con = duckdb.connect(BD, read_only=True)
    bien = 0
    for i, (tema, _, _, ref) in enumerate(E, start=1):
        p = ruta(i)
        sql = ""
        if os.path.exists(p):
            sql = "\n".join(l for l in open(p, encoding="utf-8").read().splitlines()
                            if not l.strip().startswith("--")).strip().rstrip(";")
        if not sql:
            print(f"  ··  {i:2}. {tema:36} sin responder")
            continue
        try:
            tuyo = con.execute(sql).df()
        except Exception as e:
            print(f"  ✗   {i:2}. {tema:36} ERROR: {str(e).splitlines()[0][:44]}")
            continue
        esp = con.execute(ref).df()
        try:
            ok = norm(tuyo).equals(norm(esp))
        except Exception:
            ok = False
        if ok:
            bien += 1
            print(f"  OK  {i:2}. {tema:36} {len(tuyo)} filas")
        else:
            print(f"  ✗   {i:2}. {tema:36} devolvio {tuyo.shape}, se esperaba {esp.shape}")
            if list(norm(tuyo).columns) != list(norm(esp).columns):
                print(f"        columnas tuyas:    {list(tuyo.columns)}")
                print(f"        columnas esperadas:{list(esp.columns)}")
    con.close()
    print(f"\n{bien} de {len(E)} correctos")


if __name__ == "__main__":
    a = sys.argv[1:]
    if "--corregir" in a:
        corregir()
    elif a and a[0].isdigit():
        mostrar(int(a[0]), "--pista" in a)
    else:
        print(f"\n{len(E)} ejercicios sobre tu warehouse. En orden de dificultad.\n")
        for i, (tema, _, _, _) in enumerate(E, start=1):
            hecho = os.path.exists(ruta(i)) and len(
                [l for l in open(ruta(i), encoding="utf-8").read().splitlines()
                 if l.strip() and not l.strip().startswith("--")]) > 0
            print(f"  {'[x]' if hecho else '[ ]'} {i:2}. {tema}")
        print("\n  python ejercicios/ejercicios.py 1          ver el enunciado")
        print("  python ejercicios/ejercicios.py 1 --pista  la pista")
        print("  python ejercicios/ejercicios.py --corregir corregir todo")
