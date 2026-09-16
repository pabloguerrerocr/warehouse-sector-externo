-- FASE 2 — Transformaciones en SQL.
--
-- La desacumulacion es el caso que justifica todo el proyecto: el BCCR publica
-- el balance comercial y las exportaciones acumulados dentro del ano, y el
-- flujo del mes es la diferencia contra el mes anterior DEL MISMO ANO. En enero
-- no hay mes anterior: el acumulado ES el flujo.
--
-- En SQL eso es una funcion de ventana particionada por ano. En pandas son
-- varias lineas con groupby y diff; aca es una expresion.

CREATE OR REPLACE VIEW v_desacumulado AS
SELECT
    serie_id,
    -- El BCCR fecha el dato a fin de mes; el panel usa inicio de mes.
    DATE_TRUNC('month', fecha) AS fecha,
    valor AS acumulado,
    valor - COALESCE(
        LAG(valor) OVER (PARTITION BY serie_id, YEAR(fecha) ORDER BY fecha),
        0
    ) AS flujo
FROM fact_acumulado_crudo;


-- Serie mensual unificada: lo desacumulado sale de la vista, el resto ya venia
-- como flujo. Es la tabla contra la que se corren los chequeos de calidad.
CREATE OR REPLACE VIEW v_mensual AS
SELECT serie_id, fecha, flujo AS valor FROM v_desacumulado
UNION ALL
SELECT o.serie_id, o.fecha, o.valor
FROM fact_observacion o
JOIN dim_serie s USING (serie_id)
WHERE s.frecuencia = 'M'
  AND o.serie_id NOT IN (SELECT DISTINCT serie_id FROM fact_acumulado_crudo);


-- Variacion interanual, otra ventana: el mismo mes del ano anterior esta 12
-- filas atras si la serie no tiene huecos. Se calcula con LAG sobre la serie
-- ordenada, no restando fechas a mano.
CREATE OR REPLACE VIEW v_variacion_interanual AS
WITH s AS (
    SELECT serie_id, fecha, valor,
           LAG(valor, 12) OVER (PARTITION BY serie_id ORDER BY fecha) AS hace_un_anio
    FROM v_mensual
)
SELECT serie_id, fecha, valor, hace_un_anio,
       CASE WHEN hace_un_anio IS NULL OR hace_un_anio = 0 THEN NULL
            ELSE ROUND((valor / hace_un_anio - 1) * 100, 2)
       END AS var_interanual_pc
FROM s;


-- Promedio movil de 3 meses: ventana deslizante, no agregacion por grupo.
CREATE OR REPLACE VIEW v_media_movil AS
SELECT serie_id, fecha, valor,
       ROUND(AVG(valor) OVER (PARTITION BY serie_id ORDER BY fecha
                              ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 4) AS mm3
FROM v_mensual;
