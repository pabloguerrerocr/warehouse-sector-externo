-- Ventana deslizante, no agregacion por grupo. Sin el ROWS BETWEEN, el marco
-- por defecto de SQL no es el que uno quiere.

select
    serie_id,
    fecha,
    valor,
    round(avg(valor) over (
        partition by serie_id order by fecha
        rows between 2 preceding and current row
    ), 4) as mm3
from {{ ref('mensual') }}
