-- Unicidad de la llave del panel. dbt no trae un test de combinacion de
-- columnas sin dbt_utils, y agregar un paquete por esto no vale la pena.

select serie_id, fecha, count(*) as veces
from {{ ref('mensual') }}
group by 1, 2
having count(*) > 1
