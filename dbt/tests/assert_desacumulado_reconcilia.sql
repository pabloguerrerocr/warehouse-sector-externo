-- La prueba que sostiene el proyecto entero: si desacumular esta bien hecho,
-- la suma de los doce flujos de un anio tiene que reproducir el acumulado de
-- diciembre. Devuelve las filas que NO reconcilian.
--
-- Tolerancia 1e-6: el dato viene en millones de dolares con decimales, y la
-- suma en punto flotante no da exacto. La corrida real reconcilia a 5,7e-14.

with por_anio as (
    select
        serie_id,
        year(fecha) as anio,
        sum(flujo) as suma_flujos,
        max(acumulado) filter (where month(fecha) = 12) as acumulado_diciembre
    from {{ ref('desacumulado') }}
    group by 1, 2
)
select *, abs(suma_flujos - acumulado_diciembre) as diferencia
from por_anio
where acumulado_diciembre is not null
  and abs(suma_flujos - acumulado_diciembre) > 1e-6
