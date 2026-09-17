-- Ejercicio 1
SELECT serie_id, fecha, valor FROM fact_observacion WHERE serie_id='tpm' AND YEAR(fecha)=2022 ORDER BY fecha
