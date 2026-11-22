"""Cruza las cifras de la oferta reportadas por la prensa con las del prospecto final (424B4)."""
import json, pathlib

import yaml

RAIZ = pathlib.Path(__file__).resolve().parents[1]


def cargar() -> dict:
    prensa = yaml.safe_load((RAIZ / "entradas" / "oferta.yaml").read_text())
    ruta = RAIZ / "resultados" / "oferta_edgar.json"
    if not ruta.exists():
        return {**prensa, "verificado": False}
    edgar = json.loads(ruta.read_text())
    return verificar(prensa, edgar)


def verificar(prensa: dict, edgar: dict) -> dict:
    for campo in ("precio_oferta", "acciones_ofrecidas"):
        if abs(edgar[campo] - prensa[campo]) > 1e-9 * max(1, abs(prensa[campo])):
            raise ValueError(f"{campo}: la prensa dice {prensa[campo]} y el 424B4 dice {edgar[campo]}. Revisar antes de publicar.")
    return {**prensa, **edgar, "verificado": True}
