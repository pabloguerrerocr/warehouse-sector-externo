-- El caso que justifica todo el proyecto.
--
-- El BCCR publica el balance comercial y las exportaciones acumulados dentro
-- del ano. El flujo del mes es la diferencia contra el mes anterior DEL MISMO
-- ANO; en enero no hay mes anterior, asi que el acumulado ES el flujo.
--
-- En SQL eso es una ventana particionada por ano. En pandas son varias lineas
-- de groupby y diff; aca es una expresion.

select
    serie_id,
    fecha,
    acumulado,
    acumulado - coalesce(
        lag(acumulado) over (partition by serie_id, year(fecha) order by fecha),
        0
    ) as flujo
from {{ ref('stg_acumulado_crudo') }}
