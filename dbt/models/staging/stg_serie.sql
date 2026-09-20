select
    serie_id,
    etiqueta,
    frecuencia,
    origen,
    proveedor,
    titulo_original
from {{ source('crudo', 'dim_serie') }}
