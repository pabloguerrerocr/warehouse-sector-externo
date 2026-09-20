-- Aviso, no error: un salto de mas de 5 desviaciones tipicas del cambio de la
-- propia serie puede ser un choque macro real o un error de captura. La corrida
-- de referencia devuelve 3 filas, y las tres son choques reales.
--
-- Se marca como warn para que no tumbe la construccion.
{{ config(severity = 'warn') }}

with d as (
    select serie_id, fecha,
           valor - lag(valor) over (partition by serie_id order by fecha) as cambio
    from {{ ref('mensual') }}
), e as (
    select serie_id, avg(cambio) as media, stddev_samp(cambio) as de
    from d where cambio is not null group by 1
)
select d.serie_id, d.fecha, d.cambio
from d join e using (serie_id)
where d.cambio is not null and e.de > 0
  and abs(d.cambio - e.media) / e.de > 5
