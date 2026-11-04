"""Ubica el repositorio del TFG, de donde este warehouse lee sus datos.

El warehouse no copia los datos: los lee del repositorio sector-externo-cr-eeuu,
que es donde se validaron. Se busca, en este orden:

  1. la ruta de la variable de entorno TFG_DIR
  2. ../sector-externo-cr-eeuu   (el nombre del repositorio publico)
  3. ../tfg-sector-externo       (el nombre de la carpeta local original)
"""
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
PADRE = os.path.dirname(AQUI)
REPO = "https://github.com/pabloguerrerocr/sector-externo-cr-eeuu"


def raiz() -> str:
    candidatos = [os.environ.get("TFG_DIR"),
                  os.path.join(PADRE, "sector-externo-cr-eeuu"),
                  os.path.join(PADRE, "tfg-sector-externo")]
    for c in candidatos:
        if c and os.path.isdir(os.path.join(c, "data", "procesado")):
            return c
    sys.exit("No encuentro el repositorio del TFG. Clonalo al lado de este:\n"
             f"  git clone {REPO} {os.path.join(PADRE, 'sector-externo-cr-eeuu')}\n"
             "o indica donde esta con la variable de entorno TFG_DIR.")


def procesado() -> str:
    """Los paneles validados: data/procesado/ del TFG."""
    return os.path.join(raiz(), "data", "procesado")


def crudo() -> str:
    """Los Excel del BCCR y el cache de FRED: data/raw/ del TFG."""
    return os.path.join(raiz(), "data", "raw")
