-- Aviso: series que terminan antes que el resto del panel. Una serie
-- desactualizada no es un error de dato, pero sesga cualquier corte al ultimo
-- periodo si nadie lo nota.
{{ config(severity = 'warn') }}

with fin as (select max(fecha) as tope from {{ ref('mensual') }})
select m.serie_id, max(m.fecha) as ultima_fecha, fin.tope
from {{ ref('mensual') }} m, fin
group by m.serie_id, fin.tope
having max(m.fecha) < fin.tope
