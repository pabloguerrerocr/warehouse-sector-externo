-- Esquema estrella del panel del sector externo.
--
-- El panel ancho (una columna por variable) sirve para estimar, pero no para
-- consultar: agregar una serie obliga a alterar la tabla. Acá se guarda largo
-- -una fila por (serie, fecha, valor)- que es la forma en que un warehouse
-- guarda series de tiempo.

-- Se borra en orden inverso a las dependencias: primero lo que apunta a otro.
-- Las dos ultimas las crean fases posteriores, pero hay que borrarlas aca o el
-- DROP de dim_serie falla al reconstruir (lo encontro 07_pruebas.py).
DROP TABLE IF EXISTS reporte_calidad;
DROP VIEW  IF EXISTS v_media_movil;
DROP VIEW  IF EXISTS v_variacion_interanual;
DROP VIEW  IF EXISTS v_mensual;
DROP VIEW  IF EXISTS v_desacumulado;
DROP TABLE IF EXISTS fact_acumulado_crudo;
DROP TABLE IF EXISTS fact_observacion_diaria;
DROP TABLE IF EXISTS fact_observacion;
DROP TABLE IF EXISTS dim_fecha;
DROP TABLE IF EXISTS dim_serie;

-- ---------------------------------------------------------------- dimensiones
CREATE TABLE dim_serie (
    serie_id        VARCHAR PRIMARY KEY,   -- 'ffr', 'tc_venta', ...
    etiqueta        VARCHAR NOT NULL,
    frecuencia      VARCHAR NOT NULL CHECK (frecuencia IN ('D','M','Q')),
    origen          VARCHAR NOT NULL,      -- 'FRED - FEDFUNDS' | 'BCCR - tpm.xlsx'
    proveedor       VARCHAR NOT NULL CHECK (proveedor IN ('FRED','BCCR')),
    titulo_original VARCHAR
);

CREATE TABLE dim_fecha (
    fecha       DATE PRIMARY KEY,
    anio        SMALLINT NOT NULL,
    trimestre   TINYINT  NOT NULL CHECK (trimestre BETWEEN 1 AND 4),
    mes         TINYINT  NOT NULL CHECK (mes BETWEEN 1 AND 12),
    fin_de_anio BOOLEAN  NOT NULL          -- diciembre: cierra el acumulado
);

-- ---------------------------------------------------------------- hechos
CREATE TABLE fact_observacion (
    serie_id VARCHAR NOT NULL REFERENCES dim_serie(serie_id),
    fecha    DATE    NOT NULL REFERENCES dim_fecha(fecha),
    valor    DOUBLE,                        -- NULL = hueco declarado, no cero
    PRIMARY KEY (serie_id, fecha)           -- impide duplicados por construccion
);

-- La consulta que siempre se hace: una serie ordenada en el tiempo.
CREATE INDEX idx_obs_serie_fecha ON fact_observacion (serie_id, fecha);
