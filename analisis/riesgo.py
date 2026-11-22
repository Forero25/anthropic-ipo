"""Cómo se comporta ANT en bolsa: beta, volatilidad, correlación con sus pares y factores.

Cada medida declara cuántas observaciones usa y no se calcula si son muy pocas: con una semana de
historia una beta no significa nada, y el resultado lo dice en vez de inventar precisión.
"""
import numpy as np
import pandas as pd

MIN_BETA, MIN_GARCH, MIN_FACTORES = 20, 120, 60


def retornos(diarios: pd.DataFrame) -> pd.DataFrame:
    p = diarios.pivot_table(index="fecha", columns="ticker", values="adj_close").sort_index()
    return p.pct_change(fill_method=None).iloc[1:]


def ols(y: np.ndarray, X: np.ndarray):
    """Mínimos cuadrados con errores estándar robustos a heterocedasticidad (HC1)."""
    X = np.column_stack([np.ones(len(y)), X])
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    e = y - X @ b
    n, k = X.shape
    XtX_inv = np.linalg.inv(X.T @ X)
    V = XtX_inv @ (X.T * e ** 2) @ X @ XtX_inv * n / (n - k)
    r2 = 1 - (e @ e) / ((y - y.mean()) @ (y - y.mean()))
    return b, np.sqrt(np.diag(V)), float(r2)


def beta(r: pd.DataFrame, accion="ANT", mercado="QQQ") -> dict:
    d = r[[accion, mercado]].dropna()
    if len(d) < MIN_BETA:
        return {"n": len(d), "nota": f"menos de {MIN_BETA} sesiones: todavía no se estima"}
    b, se, r2 = ols(d[accion].to_numpy(), d[[mercado]].to_numpy())
    return {"n": len(d), "beta": float(b[1]), "ee": float(se[1]), "ic95": [float(b[1] - 1.96 * se[1]), float(b[1] + 1.96 * se[1])], "r2": r2}


def correlaciones(r: pd.DataFrame, accion="ANT", pares=("NVDA", "MSFT", "GOOGL", "AMZN", "META", "ORCL", "QQQ")) -> dict:
    d = r.dropna(subset=[accion])
    if len(d) < MIN_BETA:
        return {"n": len(d), "nota": f"menos de {MIN_BETA} sesiones"}
    return {"n": len(d), **{p: float(d[accion].corr(d[p])) for p in pares if p in d}}


def vol_realizada(intradia: pd.DataFrame, ticker="ANT", cada="5min") -> pd.DataFrame:
    """Volatilidad realizada diaria con retornos de 5 minutos (Andersen y Bollerslev, 1998), anualizada con 252 sesiones.
    Se usan 5 minutos y no 1 para que el ruido de microestructura (rebote entre compra y venta) no la infle."""
    d = intradia[intradia["ticker"] == ticker].copy()
    d["hora"] = pd.to_datetime(d["hora"])
    d = d.set_index("hora")["close"]
    out = []
    for dia, s in d.groupby(d.index.date):
        p = s.resample(cada).last().dropna()
        r = np.log(p).diff().dropna()
        if len(r) >= 10:
            out.append({"fecha": str(dia), "vol_anualizada": float(np.sqrt((r ** 2).sum() * 252)), "n_retornos": int(len(r))})
    return pd.DataFrame(out)


def garch(r: pd.DataFrame, accion="ANT") -> dict:
    y = r[accion].dropna() * 100
    if len(y) < MIN_GARCH:
        return {"n": len(y), "nota": f"menos de {MIN_GARCH} sesiones: un GARCH(1,1) no se estima con tan poca historia"}
    from arch import arch_model
    m = arch_model(y, vol="GARCH", p=1, q=1, dist="t", mean="Constant").fit(disp="off")
    a, b = float(m.params["alpha[1]"]), float(m.params["beta[1]"])
    return {"n": len(y), "alpha": a, "beta": b, "persistencia": a + b,
            "vida_media_dias": float(np.log(0.5) / np.log(a + b)) if a + b < 1 else None}


def factores(r: pd.DataFrame, f: pd.DataFrame, accion="ANT") -> dict:
    """Fama-French de cinco factores más momentum, sobre el exceso de retorno de ANT."""
    d = r[[accion]].join(f.set_index("fecha"), how="inner").dropna()
    if len(d) < MIN_FACTORES:
        return {"n": len(d), "nota": f"menos de {MIN_FACTORES} sesiones con factores publicados"}
    cols = ["Mkt-RF", "SMB", "HML", "RMW", "CMA", "Mom"]
    b, se, r2 = ols((d[accion] - d["RF"]).to_numpy(), d[cols].to_numpy())
    return {"n": len(d), "r2": r2, "alfa_diario": float(b[0]),
            **{c: {"coef": float(b[i + 1]), "ee": float(se[i + 1])} for i, c in enumerate(cols)}}
