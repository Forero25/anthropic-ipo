"""Factores diarios de Fama y French (cinco factores) y momentum, de la biblioteca de Kenneth French.
Se publican con unas semanas de rezago: el modelo de factores solo corre cuando hay suficientes días de ANT cubiertos."""
import io, pathlib, zipfile

import pandas as pd
import requests

RAIZ = pathlib.Path(__file__).resolve().parents[1]
BASE = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
ARCHIVOS = {"ff5": "F-F_Research_Data_5_Factors_2x3_daily_CSV.zip", "mom": "F-F_Momentum_Factor_daily_CSV.zip"}


def leer_csv_french(texto: str) -> pd.DataFrame:
    """Los CSV de French traen notas arriba y abajo: se toman solo las filas que empiezan con una fecha AAAAMMDD."""
    lineas = texto.splitlines()
    ini = next(i for i, l in enumerate(lineas) if l.strip()[:8].isdigit()) - 1
    filas = [lineas[ini]] + [l for l in lineas[ini + 1:] if l.strip()[:8].isdigit() and len(l.split(",")[0].strip()) == 8]
    d = pd.read_csv(io.StringIO("\n".join(filas)))
    d = d.rename(columns={d.columns[0]: "fecha"})
    d.columns = [c.strip() for c in d.columns]
    d["fecha"] = pd.to_datetime(d["fecha"].astype(str).str.strip(), format="%Y%m%d")
    for c in d.columns[1:]:
        d[c] = pd.to_numeric(d[c], errors="coerce") / 100  # vienen en porcentaje
    return d


def main():
    partes = []
    for clave, archivo in ARCHIVOS.items():
        r = requests.get(BASE + archivo, timeout=120)
        r.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            partes.append(leer_csv_french(z.read(z.namelist()[0]).decode("latin-1")))
    f = partes[0].merge(partes[1], on="fecha", how="inner")
    (RAIZ / "datos").mkdir(exist_ok=True)
    f.to_parquet(RAIZ / "datos" / "factores.parquet", index=False)
    print("factores hasta", f["fecha"].max().date())


if __name__ == "__main__":
    main()
