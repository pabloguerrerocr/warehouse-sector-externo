# warehouse-sector-externo

Warehouse en DuckDB del panel macroeconómico de
[sector-externo-cr-eeuu](https://github.com/pabloguerrerocr/sector-externo-cr-eeuu),
con **la prueba de que mover los datos a SQL no alteró ni un número**.

```bash
pip install duckdb pandas openpyxl
python 07_pruebas.py       # reconstruye todo desde cero y lo verifica
```

## Por qué existe

Un panel ancho —una columna por variable— sirve para estimar pero no para
consultar: agregar una serie obliga a alterar la tabla. Acá los datos se guardan
largos, en esquema estrella, y **cada agregación se deriva en SQL desde el grano
más fino disponible**.

| Tabla | Filas | Qué es |
|---|---:|---|
| `dim_serie` | 12 | las series, con su frecuencia, proveedor y título original |
| `dim_fecha` | 132 | calendario con año, trimestre, mes y cierre de año |
| `fact_observacion` | 1.408 | una fila por serie y fecha |
| `fact_observacion_diaria` | 5.491 | el grano diario de las series de FRED |

## La prueba

`03_reconciliar.py` compara las 18 series contra los CSV validados del proyecto
original. Diferencia máxima tolerada: `1e-9`.

```
VEREDICTO: el warehouse reproduce el panel validado, dato por dato.
```

## Dos cosas que la reconciliación destapó

**Promediar dos veces no es lo mismo que promediar una.** `t2y` y `dolar` son
series diarias. Agregar día → mes → trimestre da distinto que día → trimestre,
porque los meses tienen distinto número de días. Por eso el warehouse guarda el
grano diario y deriva el trimestre de ahí: el error aparecía en el segundo
decimal y solo se ve si se compara contra la fuente.

**Un valor propagado no es un dato.** `pib_eeuu` es trimestral y el panel mensual
lo repite hacia adelante. Eso no se almacena: se reconstruye con un `JOIN` contra
`DATE_TRUNC('quarter', ...)`. Guardar valores derivados es como se corrompe un
warehouse.

## Estado

| Archivo | Qué hace |
|---|---|
| `01_esquema.sql` | esquema estrella, con el orden de borrado que respeta las dependencias |
| `02_cargar.py` | panel ancho → largo, más el grano diario de FRED |
| `03_reconciliar.py` | compara las 18 series contra los CSV validados |
| `04_crudo_acumulado.py` | carga el acumulado **sin tocar**, tal como lo publica el BCCR |
| `05_transformar.sql` | desacumulación, variación interanual y media móvil, en ventanas |
| `06_calidad.sql` | los 7 chequeos |
| `07_pruebas.py` | reconstruye desde cero y afirma todo. Sale con código 1 si falla |

## La desacumulación, que es el caso que justifica todo

El BCCR publica el balance comercial y las exportaciones **acumulados dentro del
año**: enero trae enero, febrero trae enero+febrero. El flujo del mes es la
diferencia contra el mes anterior *del mismo año*; en enero no hay anterior, así
que el acumulado es el flujo.

```sql
valor - COALESCE(
    LAG(valor) OVER (PARTITION BY serie_id, YEAR(fecha) ORDER BY fecha),
    0
) AS flujo
```

Una expresión. Y reconcilia con el pipeline de Python a `5.7e-14`.

## El motor de calidad

Siete chequeos que devuelven **las filas que fallan**, no un booleano: huecos en
la serie, duplicados, nulos, series huérfanas, saltos improbables, descuadre de
la desacumulación y series desactualizadas.

Sobre estos datos: **0 errores y 3 avisos**, y los tres avisos son choques
macroeconómicos reales, no errores de captura.

| Serie | Fecha | Detalle |
|---|---|---|
| `ffr` | 2020-03 | −0,93 = 5,4 desviaciones — recorte de emergencia de la Fed |
| `ipi_eeuu` | 2020-04 | −12,85 = 8,7 desviaciones — desplome industrial por COVID |
| `tpm` | 2022-08 | +1,74 = 5,0 desviaciones — alza agresiva del BCCR |

Que el motor los marque es lo correcto: distinguir un choque real de un error de
dato es trabajo de quien conoce la serie, no del chequeo.

## Datos

Públicos: FRED (Reserva Federal de San Luis) y el portal de indicadores
económicos del BCCR. Ninguno es de acceso restringido.

## Capa dbt

Las transformaciones también están como proyecto dbt en [`dbt/`](dbt/): mismos
resultados —verificado con `EXCEPT` en ambas direcciones, cero filas de
diferencia— pero con linaje, documentación y las pruebas corriendo dentro del
grafo en vez de en un script aparte.

```bash
cd dbt && dbt build      # PASS 23 · WARN 1 · ERROR 0
```
