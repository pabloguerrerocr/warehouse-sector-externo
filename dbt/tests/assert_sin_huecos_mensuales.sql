-- Un hueco en la serie rompe silenciosamente cualquier calculo con LAG: la
-- variacion interanual dejaria de comparar contra el mismo mes.
-- Devuelve el mes que falta, no un booleano.

with rango as (
    select serie_id, min(fecha) as desde, max(fecha) as hasta
    from {{ ref('mensual') }}
    group by 1
), esperado as (
    select
        r.serie_id,
        cast(unnest(generate_series(r.desde, r.hasta, interval 1 month)) as date) as fecha
    from rango r
)
select e.serie_id, e.fecha
from esperado e
left join {{ ref('mensual') }} m
       on m.serie_id = e.serie_id and m.fecha = e.fecha
where m.fecha is null
