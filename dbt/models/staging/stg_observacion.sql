-- Observaciones que el BCCR ya publica como flujo del mes.
-- Staging solo renombra y tipa: ninguna regla de negocio vive aca.

select
    serie_id,
    cast(fecha as date) as fecha,
    cast(valor as double) as valor
from {{ source('crudo', 'fact_observacion') }}
