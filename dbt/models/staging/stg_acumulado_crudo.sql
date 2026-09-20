-- Series que el BCCR publica ACUMULADAS dentro del ano.
-- El dato viene fechado a fin de mes; el panel trabaja a inicio de mes.

select
    serie_id,
    date_trunc('month', cast(fecha as date)) as fecha,
    cast(valor as double) as acumulado
from {{ source('crudo', 'fact_acumulado_crudo') }}
