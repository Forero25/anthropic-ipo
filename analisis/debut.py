"""El primer día de ANT en bolsa: precio de oferta, apertura, cierre y el recorrido minuto a minuto.

Convenciones (Ritter, 1991; Loughran y Ritter, 2004):
- retorno del primer día = cierre del primer día / precio de oferta − 1 (la "infravaloración");
- prima de apertura = apertura / precio de oferta − 1;
- dinero dejado sobre la mesa = (cierre − precio de oferta) × acciones vendidas en la oferta;
- retorno ajustado por mercado = retorno del día de ANT desde la oferta − retorno del Nasdaq-100 (QQQ) ese día.
"""
import numpy as np
import pandas as pd


def dia(d: pd.DataFrame, ticker: str, fecha) -> pd.Series:
    f = d[(d["ticker"] == ticker) & (pd.to_datetime(d["fecha"]).dt.normalize() == pd.Timestamp(fecha))]
    if f.empty:
        raise ValueError(f"No hay datos diarios de {ticker} el {fecha}.")
    return f.iloc[0]


def resumen(diarios: pd.DataFrame, oferta: dict, mercado="QQQ") -> dict:
    p0, n = oferta["precio_oferta"], oferta["acciones_ofrecidas"]
    fecha = pd.Timestamp(oferta["fecha_debut"])
    a = dia(diarios, oferta["ticker"], fecha)
    m = diarios[diarios["ticker"] == mercado].sort_values("fecha")
    m_ret = m.set_index(pd.to_datetime(m["fecha"]).dt.normalize())["close"].pct_change().loc[fecha]
    ret = a["close"] / p0 - 1
    return {
        "precio_oferta": p0, "apertura": float(a["open"]), "cierre": float(a["close"]),
        "maximo": float(a["high"]), "minimo": float(a["low"]), "volumen": int(a["volume"]),
        "prima_apertura": float(a["open"] / p0 - 1), "retorno_primer_dia": float(ret),
        "retorno_mercado_dia": float(m_ret), "retorno_ajustado_mercado": float(ret - m_ret),
        "cierre_vs_apertura": float(a["close"] / a["open"] - 1),
        "dinero_sobre_la_mesa_musd": float((a["close"] - p0) * n / 1e6),
        "recaudo_oferta_musd": float(p0 * n / 1e6),
    }


def recorrido(intradia: pd.DataFrame, oferta: dict) -> dict:
    """Recorrido minuto a minuto del primer día: cuándo hizo el máximo y el mínimo, y cuánto tiempo pasó bajo la apertura."""
    fecha = pd.Timestamp(oferta["fecha_debut"]).date()
    d = intradia[(intradia["ticker"] == oferta["ticker"]) & (pd.to_datetime(intradia["hora"]).dt.date == fecha)]
    d = d[d["volume"] > 0].sort_values("hora")
    if d.empty:
        return {}
    precio_tipico = (d["high"] + d["low"] + d["close"]) / 3
    vwap = float((precio_tipico * d["volume"]).sum() / d["volume"].sum())
    apertura = float(d["open"].iloc[0])
    return {
        "primer_minuto": str(pd.Timestamp(d["hora"].iloc[0]).time())[:5],
        "minutos_con_operaciones": int(len(d)),
        "hora_maximo": str(pd.Timestamp(d.loc[d["high"].idxmax(), "hora"]).time())[:5],
        "hora_minimo": str(pd.Timestamp(d.loc[d["low"].idxmin(), "hora"]).time())[:5],
        "vwap": vwap, "vwap_vs_oferta": vwap / oferta["precio_oferta"] - 1,
        "share_minutos_bajo_apertura": float((d["close"] < apertura).mean()),
        # cada 5 minutos, como retorno frente al precio de oferta (no se publican series de precios)
        "serie_vs_oferta": [{"hora": str(pd.Timestamp(h).time())[:5], "r": round(float(c) / oferta["precio_oferta"] - 1, 5)}
                            for h, c in zip(d["hora"], d["close"])][::5],
    }
