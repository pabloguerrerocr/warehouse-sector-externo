-- El mismo mes del ano anterior esta 12 filas atras si la serie no tiene
-- huecos. Por eso el chequeo de huecos corre antes que esto.

with s as (
    select
        serie_id,
        fecha,
        valor,
        lag(valor, 12) over (partition by serie_id order by fecha) as hace_un_anio
    from {{ ref('mensual') }}
)
select
    serie_id,
    fecha,
    valor,
    hace_un_anio,
    case
        when hace_un_anio is null or hace_un_anio = 0 then null
        else round((valor / hace_un_anio - 1) * 100, 2)
    end as var_interanual_pc
from s
