"""Valoración por flujo de caja descontado con simulación de Monte Carlo, y DCF inverso.

Estructura (Damodaran, "Investment Valuation", cap. 12 y 23):
- las ventas crecen a g_1 el primer año y convergen linealmente a g_terminal en el año T;
- el margen operativo pasa del actual al objetivo de forma lineal;
- la reinversión de cada año es el aumento de ventas dividido por la razón ventas/capital
  (cuánta venta nueva genera cada dólar invertido en cómputo, centros de datos y talento);
- valor terminal: NOPAT_{T+1} · (1 − g/ROIC) / (WACC − g), con g < WACC.

Los supuestos inciertos se sortean de distribuciones triangulares [mínimo, moda, máximo] que se
declaran en entradas/supuestos.yaml, cada uno con su fuente. El resultado es una distribución de
valores por acción, no un precio objetivo: no es una recomendación de inversión.
"""
import numpy as np
from scipy.optimize import brentq

INCIERTOS = ("crecimiento_inicial", "margen_objetivo", "ventas_a_capital", "wacc")


def _flujos(s: dict, g1, m_obj, vac, wacc):
    T = s["anios"]
    t = np.arange(1, T + 1)
    g1, m_obj, vac, wacc = (np.atleast_1d(np.asarray(x, float)) for x in (g1, m_obj, vac, wacc))
    g = g1[:, None] + (s["crecimiento_terminal"] - g1)[:, None] * (t - 1) / (T - 1)
    ventas = s["ventas_base"] * np.cumprod(1 + g, axis=1)
    margen = s["margen_base"] + (m_obj - s["margen_base"])[:, None] * t / T
    nopat = ventas * margen * np.where(margen > 0, 1 - s["tasa_impuesto"], 1)  # sin impuesto mientras hay pérdidas
    previas = np.column_stack([np.full(len(g1), s["ventas_base"]), ventas[:, :-1]])
    fcf = nopat - (ventas - previas) / vac[:, None]
    desc = (1 + wacc)[:, None] ** t
    gT, roic = s["crecimiento_terminal"], s["roic_terminal"]
    nopat_T1 = ventas[:, -1] * (1 + gT) * m_obj * (1 - s["tasa_impuesto"])
    vt = nopat_T1 * (1 - gT / roic) / (wacc - gT)
    ve = (fcf / desc).sum(axis=1) + vt / desc[:, -1]
    return (ve + s["caja_neta"]) / s["acciones_diluidas"], vt / desc[:, -1] / ve


def validar(s: dict):
    faltan = [k for k, v in s.items() if v is None]
    if faltan:
        raise ValueError(f"Supuestos sin llenar desde el prospecto: {faltan}")
    if s["wacc"][0] <= s["crecimiento_terminal"]:
        raise ValueError("El WACC mínimo debe superar el crecimiento terminal.")


def simular(s: dict, n=50_000, semilla=2026) -> dict:
    validar(s)
    rng = np.random.default_rng(semilla)
    draws = {k: rng.triangular(*s[k], n) for k in INCIERTOS}
    v, peso_vt = _flujos(s, draws["crecimiento_inicial"], draws["margen_objetivo"], draws["ventas_a_capital"], draws["wacc"])
    q = np.percentile(v, [5, 25, 50, 75, 95])
    return {"n": n, "percentiles": dict(zip(["p5", "p25", "p50", "p75", "p95"], map(float, q))),
            "media": float(v.mean()), "peso_valor_terminal_mediano": float(np.median(peso_vt)), "valores": v}


def prob_sobre(v: np.ndarray, precio: float) -> float:
    return float((v > precio).mean())


def moda(s: dict) -> dict:
    return {k: s[k][1] for k in INCIERTOS}


def valor(s: dict, d: dict) -> float:
    """Valor por acción con los supuestos inciertos fijados en d (claves de INCIERTOS)."""
    return float(_flujos(s, d["crecimiento_inicial"], d["margen_objetivo"], d["ventas_a_capital"], d["wacc"])[0][0])


def inverso(s: dict, precio: float, lo=-0.5, hi=3.0) -> float | None:
    """Crecimiento del primer año que hace que el DCF (resto de supuestos en su moda) iguale el precio de mercado."""
    validar(s)
    m = moda(s)
    f = lambda g: valor(s, {**m, "crecimiento_inicial": g}) - precio
    if f(lo) * f(hi) > 0:
        return None  # ningún crecimiento en el rango explica el precio
    return float(brentq(f, lo, hi))


def tornado(s: dict) -> dict:
    """Cuánto cambia el valor por acción al llevar cada supuesto a su mínimo y a su máximo, con el resto en la moda."""
    validar(s)
    m = moda(s)
    base = valor(s, m)
    out = []
    for k in INCIERTOS:
        bajo = valor(s, {**m, k: s[k][0]})
        alto = valor(s, {**m, k: s[k][2]})
        out.append({"supuesto": k, "en_minimo": bajo, "en_maximo": alto, "rango": abs(alto - bajo)})
    return {"base": base, "supuestos": sorted(out, key=lambda x: -x["rango"])}
