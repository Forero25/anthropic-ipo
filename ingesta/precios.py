"""Precios de ANT y sus comparables desde Yahoo Finance.

- Diarios: desde un año antes del debut (los comparables necesitan historia para estimar betas).
- Intradía de 1 minuto: Yahoo guarda unos 30 días y entrega 7 por petición; se piden por tramos y se
  acumulan en datos/intradia_1m.parquet. En GitHub Actions ese archivo vive en la caché del flujo, no en
  el repositorio: los precios no se publican, solo los resultados.
"""
import pathlib, sys

import pandas as pd
import yfinance as yf

RAIZ = pathlib.Path(__file__).resolve().parents[1]
DATOS = RAIZ / "datos"
DEBUT = pd.Timestamp("2026-11-19")
ACCION = "ANT"
MERCADO = ["QQQ", "SPY"]
PARES = ["NVDA", "MSFT", "GOOGL", "AMZN", "META", "ORCL"]
INTRADIA = [ACCION, "QQQ"]


def limpiar(d: pd.DataFrame, ticker: str, col_tiempo: str) -> pd.DataFrame:
    d = d.reset_index()
    d.columns = [str(c).lower().replace(" ", "_") for c in d.columns]
    d = d.rename(columns={d.columns[0]: col_tiempo})
    d["ticker"] = ticker
    return d


def diarios(inicio="2025-11-01") -> pd.DataFrame:
    partes = []
    for t in [ACCION, *MERCADO, *PARES]:
        d = yf.download(t, start=inicio, interval="1d", auto_adjust=False, progress=False, multi_level_index=False)
        if d.empty:
            sys.exit(f"Yahoo no devolvió datos diarios de {t}; me detengo para no publicar resultados incompletos.")
        partes.append(limpiar(d, t, "fecha"))
    return pd.concat(partes, ignore_index=True)


def intradia(ticker: str, dias=29) -> pd.DataFrame:
    fin = pd.Timestamp.now(tz="UTC").normalize() + pd.Timedelta(days=1)
    ini = max(fin - pd.Timedelta(days=dias), DEBUT.tz_localize("UTC"))
    partes, a = [], ini
    while a < fin:
        b = min(a + pd.Timedelta(days=7), fin)
        d = yf.download(ticker, start=a.date(), end=b.date(), interval="1m", auto_adjust=False,
                        progress=False, multi_level_index=False, prepost=False)
        if not d.empty:
            partes.append(d)
        a = b
    if not partes:
        return pd.DataFrame()
    d = pd.concat(partes)
    d = d[~d.index.duplicated(keep="last")]
    return limpiar(d, ticker, "hora")


def acumular(nuevo: pd.DataFrame, ruta: pathlib.Path) -> pd.DataFrame:
    """Une lo descargado hoy con lo guardado; ante duplicados gana lo más reciente."""
    if ruta.exists():
        nuevo = pd.concat([pd.read_parquet(ruta), nuevo], ignore_index=True)
    return nuevo.drop_duplicates(["ticker", "hora"], keep="last").sort_values(["ticker", "hora"]).reset_index(drop=True)


def main():
    DATOS.mkdir(exist_ok=True)
    diarios().to_parquet(DATOS / "diarios.parquet", index=False)
    nuevos = [x for x in (intradia(t) for t in INTRADIA) if not x.empty]
    if nuevos:
        ruta = DATOS / "intradia_1m.parquet"
        total = acumular(pd.concat(nuevos, ignore_index=True), ruta)
        total.to_parquet(ruta, index=False)
        print("intradía acumulado:", total.groupby("ticker").size().to_dict(),
              "desde", total["hora"].min(), "hasta", total["hora"].max())


if __name__ == "__main__":
    main()
