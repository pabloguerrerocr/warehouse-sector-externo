# Ejercicios de SQL sobre tu propio warehouse

Doce ejercicios en orden de dificultad, con **corrección automática**. Se comparan
resultados, no texto: si llegás por otro camino y da lo mismo, está bien.

```bash
python ejercicios/ejercicios.py              # ver en cuál vas
python ejercicios/ejercicios.py 4            # el enunciado del 4
python ejercicios/ejercicios.py 4 --pista    # una pista, sin la respuesta
python ejercicios/ejercicios.py --corregir   # corregir todo
```

Escribís tu respuesta en `ejercicios/respuestas/NN.sql`. El 01 ya está resuelto
como ejemplo del formato.

## Qué cubre

| # | Tema | Por qué importa |
|---|---|---|
| 1-2 | `SELECT`, `WHERE`, `GROUP BY` | el piso |
| 3 | `HAVING` | la confusión más común en entrevista: `WHERE` filtra antes de agrupar, `HAVING` después |
| 4 | `JOIN` | unir hechos con dimensiones |
| 5 | `LEFT JOIN` para encontrar lo que falta | detectar huecos, que es medio trabajo de depuración |
| 6-7 | `LAG` | cambio mensual e interanual |
| 8 | `SUM() OVER` | acumulado corriente |
| 9 | `ROWS BETWEEN` | media móvil — la ventana por defecto **no** es la que querés |
| 10 | `ROW_NUMBER` con `PARTITION BY` | el top N por grupo |
| 11 | CTEs encadenados | desacumular desde cero: la consulta que justifica el proyecto |
| 12 | Detección de anomalías | un chequeo de calidad real |

Con esos doce resolvés el 90 % de una prueba técnica de analista.
