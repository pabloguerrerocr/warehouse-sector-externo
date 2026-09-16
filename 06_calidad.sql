-- FASE 3 — Motor de calidad de datos.
--
-- Cada chequeo devuelve LAS FILAS QUE FALLAN, no un booleano. Un chequeo que
-- solo dice "hay un problema" obliga a buscarlo a mano; uno que devuelve la
-- fila permite arreglarlo.
--
-- Severidad:  error = el dato no se puede usar
--             aviso = revisar antes de publicar

CREATE OR REPLACE TABLE reporte_calidad (
    chequeo   VARCHAR,
    severidad VARCHAR,
    serie_id  VARCHAR,
    fecha     DATE,
    detalle   VARCHAR
);

DELETE FROM reporte_calidad;

-- 1 ── Huecos: meses que faltan entre el primero y el ultimo de cada serie.
-- Se genera el calendario esperado y se busca lo que NO esta.
INSERT INTO reporte_calidad
WITH rango AS (
    SELECT serie_id, MIN(fecha) AS desde, MAX(fecha) AS hasta
    FROM v_mensual GROUP BY 1
), esperado AS (
    SELECT r.serie_id, UNNEST(generate_series(r.desde, r.hasta, INTERVAL 1 MONTH))::DATE AS fecha
    FROM rango r
)
SELECT 'hueco en la serie', 'error', e.serie_id, e.fecha,
       'no hay observacion para este mes'
FROM esperado e
LEFT JOIN v_mensual m ON m.serie_id = e.serie_id AND m.fecha = e.fecha
WHERE m.fecha IS NULL;

-- 2 ── Duplicados por (serie, fecha).
INSERT INTO reporte_calidad
SELECT 'duplicado', 'error', serie_id, fecha,
       'aparece ' || COUNT(*) || ' veces'
FROM v_mensual GROUP BY 1, 2, 3, serie_id, fecha HAVING COUNT(*) > 1;

-- 3 ── Nulos.
INSERT INTO reporte_calidad
SELECT 'valor nulo', 'error', serie_id, fecha, 'valor NULL'
FROM v_mensual WHERE valor IS NULL;

-- 4 ── Observaciones huerfanas: hecho sin su dimension.
INSERT INTO reporte_calidad
SELECT 'serie huerfana', 'error', o.serie_id, o.fecha,
       'la serie no existe en dim_serie'
FROM fact_observacion o
LEFT JOIN dim_serie s USING (serie_id)
WHERE s.serie_id IS NULL;

-- 5 ── Saltos improbables: variacion mensual a mas de 5 desviaciones estandar
-- de la variacion tipica de esa misma serie. No es un error automatico -por eso
-- es aviso- pero es donde suelen esconderse los errores de captura.
INSERT INTO reporte_calidad
WITH d AS (
    SELECT serie_id, fecha,
           valor - LAG(valor) OVER (PARTITION BY serie_id ORDER BY fecha) AS cambio
    FROM v_mensual
), est AS (
    SELECT serie_id, AVG(cambio) AS media, STDDEV_SAMP(cambio) AS de
    FROM d WHERE cambio IS NOT NULL GROUP BY 1
)
SELECT 'salto improbable', 'aviso', d.serie_id, d.fecha,
       'cambio ' || ROUND(d.cambio, 2) || ' = ' ||
       ROUND(ABS(d.cambio - e.media) / NULLIF(e.de, 0), 1) || ' desviaciones'
FROM d JOIN est e USING (serie_id)
WHERE e.de > 0 AND ABS(d.cambio - e.media) / e.de > 5;

-- 6 ── Reconciliacion contable de las series acumuladas: la suma de los flujos
-- del ano tiene que reproducir el acumulado de diciembre. Si no cuadra, la
-- desacumulacion esta mal.
INSERT INTO reporte_calidad
WITH c AS (
    SELECT serie_id, YEAR(fecha) AS anio, SUM(flujo) AS suma,
           MAX(CASE WHEN MONTH(fecha) = 12 THEN acumulado END) AS dic
    FROM v_desacumulado GROUP BY 1, 2
)
SELECT 'descuadre de desacumulacion', 'error', serie_id,
       MAKE_DATE(anio, 12, 1),
       'suma de flujos ' || ROUND(suma, 2) || ' != acumulado de diciembre ' || ROUND(dic, 2)
FROM c WHERE dic IS NOT NULL AND ABS(suma - dic) > 1e-6;

-- 7 ── Cobertura: series que no llegan al final del periodo comun.
INSERT INTO reporte_calidad
WITH fin AS (SELECT MAX(fecha) AS tope FROM v_mensual)
SELECT 'serie desactualizada', 'aviso', m.serie_id, MAX(m.fecha),
       'termina antes que el resto del panel'
FROM v_mensual m, fin
GROUP BY m.serie_id, fin.tope
HAVING MAX(m.fecha) < fin.tope;
