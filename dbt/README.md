# Capa dbt sobre el warehouse

Las mismas transformaciones que están en `05_transformar.sql`, pero como modelos
versionados con pruebas, documentación y linaje. **No se reescribió la lógica: se
comprobó que produce exactamente las mismas filas.**

| Vista original | Modelo dbt | Filas | Resultado |
|---|---|---:|---|
| `v_mensual` | `main_marts.mensual` | 1.056 | idéntico |
| `v_desacumulado` | `main_marts.desacumulado` | 264 | idéntico |
| `v_media_movil` | `main_marts.media_movil` | 1.056 | idéntico |

Comparado con `EXCEPT` en ambas direcciones: cero filas de diferencia.

## Correr

```bash
cd dbt
set DBT_PROFILES_DIR=.        # en PowerShell: $env:DBT_PROFILES_DIR="."
dbt build                     # construye y prueba
dbt docs generate && dbt docs serve
```

Última corrida: **PASS 23 · WARN 1 · ERROR 0**.

## Por qué dbt y no los scripts

Los scripts numerados funcionan, pero el orden vive en el nombre del archivo y
las pruebas viven en otro script que hay que acordarse de correr. En dbt el orden
sale de `ref()` y las pruebas corren con la construcción: si un modelo rompe una
regla, el `build` falla ahí y no aguas abajo.

Lo que se gana concretamente:

- **El linaje es real.** `variacion_interanual` depende de `mensual`, que depende
  de `desacumulado`. dbt lo deduce de los `ref()`, no de un comentario.
- **Las pruebas son parte del grafo.** `assert_desacumulado_reconcilia` corre
  justo después del modelo que valida, no al final de todo.
- **Cada prueba devuelve las filas que fallan**, que ya era el criterio del motor
  de calidad escrito a mano. dbt lo hace nativo.

## Los chequeos

| Prueba | Severidad | Qué atrapa |
|---|---|---|
| `assert_desacumulado_reconcilia` | error | La suma de los flujos del año no reproduce el acumulado de diciembre. Tolerancia 1e-6; la corrida real da 5,7e-14 |
| `assert_sin_huecos_mensuales` | error | Un mes faltante, que rompería en silencio cualquier `LAG` |
| `assert_una_fila_por_serie_y_fecha` | error | Duplicados en la llave del panel |
| `assert_salto_mensual_razonable` | **aviso** | Cambios a más de 5 desviaciones. Devuelve 3 filas, y las tres son choques macro reales |
| `assert_series_al_dia` | aviso | Series que terminan antes que el resto del panel |
| `relationships` sobre `serie_id` | error | Hechos sin su dimensión |
| `not_null` / `unique` | error | Lo básico, declarado en el YAML |

El aviso de 5 desviaciones es deliberado: un salto grande puede ser un error de
captura o un choque real, y esa diferencia la decide una persona. Bajar el umbral
a 4 devuelve 5 filas en vez de 3, y las dos de más no son errores.
