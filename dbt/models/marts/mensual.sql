-- Serie mensual unificada: lo desacumulado sale del modelo anterior, el resto
-- ya venia como flujo. Es la tabla contra la que corren los chequeos.

select serie_id, fecha, flujo as valor
from {{ ref('desacumulado') }}

union all

select o.serie_id, o.fecha, o.valor
from {{ ref('stg_observacion') }} o
join {{ ref('stg_serie') }} s using (serie_id)
where s.frecuencia = 'M'
  and o.serie_id not in (select distinct serie_id from {{ ref('desacumulado') }})
