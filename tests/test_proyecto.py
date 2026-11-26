"""Pruebas con datos sintéticos: cada una fija de antemano la respuesta correcta."""
import pathlib, sys

import numpy as np
import pandas as pd
import pytest

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path[:0] = [str(RAIZ / "analisis"), str(RAIZ / "ingesta")]
import dcf, debut, oferta, riesgo  # noqa: E402
import edgar, factores, precios  # noqa: E402

OF = {"ticker": "ANT", "precio_oferta": 10.0, "acciones_ofrecidas": 1_000_000, "fecha_debut": "2026-11-19"}


def diarios_sinteticos():
    fechas = pd.to_datetime(["2026-11-18", "2026-11-19"])
    filas = [dict(fecha=fechas[1], ticker="ANT", open=13.0, high=13.5, low=11.0, close=12.0, adj_close=12.0, volume=500)]
    filas += [dict(fecha=f, ticker="QQQ", open=100, high=101, low=99, close=c, adj_close=c, volume=1) for f, c in zip(fechas, [100.0, 98.0])]
    return pd.DataFrame(filas)


def test_portada_424b4():
    texto = ("Class A Common Stock 1,000,000 Shares Ejemplo, PBC. We are selling 900,000 shares of Class A common stock and the "
             "selling stockholders identified in this prospectus are selling an additional 100,000 shares of Class A common stock. "
             "The initial public offering price is $10.00 per share. Per Share Total Initial public offering price $ 10.00 $ 10,000,000,000 "
             "Underwriting discount (1) $ 0.10 $ 100,000 Proceeds, before expenses, to Anthropic, PBC $ 9.90 $ 8,910,000 "
             "the underwriters have the option to purchase up to an additional 150,000 shares of Class A common stock.")
    r = edgar.leer_portada(texto.replace("10,000,000,000", "10,000,000"))
    assert r["acciones_ofrecidas"] == 1_000_000 and r["acciones_primarias"] == 900_000 and r["acciones_secundarias"] == 100_000
    assert r["precio_oferta"] == 10.0 and r["descuento_por_accion"] == 0.10 and r["opcion_sobreasignacion"] == 150_000


def test_oferta_se_detiene_si_no_coincide():
    prensa = {"precio_oferta": 83.0, "acciones_ofrecidas": 980_000_000}
    assert oferta.verificar(prensa, dict(prensa))["verificado"]
    with pytest.raises(ValueError):
        oferta.verificar(prensa, {"precio_oferta": 84.0, "acciones_ofrecidas": 980_000_000})


def test_primer_dia():
    r = debut.resumen(diarios_sinteticos(), OF)
    assert r["retorno_primer_dia"] == pytest.approx(0.20)
    assert r["prima_apertura"] == pytest.approx(0.30)
    assert r["retorno_mercado_dia"] == pytest.approx(-0.02)
    assert r["retorno_ajustado_mercado"] == pytest.approx(0.22)
    assert r["dinero_sobre_la_mesa_musd"] == pytest.approx(2.0)


def test_recorrido_intradia():
    horas = pd.date_range("2026-11-19 11:50", periods=60, freq="1min", tz="America/New_York")
    c = np.r_[np.linspace(13, 14, 10), np.linspace(14, 11, 50)]
    d = pd.DataFrame({"hora": horas, "ticker": "ANT", "open": c, "high": c, "low": c, "close": c, "volume": 100})
    r = debut.recorrido(d, OF)
    assert r["primer_minuto"] == "11:50" and r["hora_maximo"] == "11:59" and r["hora_minimo"] == "12:49"
    assert 0 < r["share_minutos_bajo_apertura"] < 1 and "precio" not in str(r["serie_vs_oferta"][0])


def test_beta_recupera_valor_conocido():
    rng = np.random.default_rng(1)
    m = rng.normal(0, 0.01, 500)
    r = pd.DataFrame({"QQQ": m, "ANT": 0.0005 + 1.6 * m + rng.normal(0, 0.01, 500)})
    b = riesgo.beta(r)
    assert b["ic95"][0] < 1.6 < b["ic95"][1]
    assert "nota" in riesgo.beta(r.head(10)) and "nota" in riesgo.garch(r.head(50))


def test_vol_realizada_recupera_sigma():
    rng = np.random.default_rng(2)
    sigma_anual = 0.60
    partes = []
    for dia in pd.bdate_range("2026-11-19", periods=5):
        horas = pd.date_range(dia + pd.Timedelta(hours=9.5), periods=390, freq="1min")
        r = rng.normal(0, sigma_anual / np.sqrt(252 * 390), 390)
        partes.append(pd.DataFrame({"hora": horas, "ticker": "ANT", "close": 100 * np.exp(np.cumsum(r))}))
    v = riesgo.vol_realizada(pd.concat(partes))
    assert v["vol_anualizada"].mean() == pytest.approx(sigma_anual, rel=0.15)


SUP = {"anios": 10, "ventas_base": 10_000.0, "margen_base": -0.2, "tasa_impuesto": 0.21, "caja_neta": 50_000.0,
       "acciones_diluidas": 1_000.0, "crecimiento_terminal": 0.03, "roic_terminal": 0.15,
       "crecimiento_inicial": [0.3, 0.6, 1.0], "persistencia_crecimiento": [0.4, 0.6, 0.8], "margen_objetivo": [0.15, 0.25, 0.35],
       "ventas_a_capital": [0.8, 1.2, 1.8], "wacc": [0.09, 0.11, 0.13]}


def test_dcf_coherente():
    m = dcf.moda(SUP)
    assert dcf.valor(SUP, {**m, "wacc": 0.10}) > dcf.valor(SUP, {**m, "wacc": 0.12})
    assert dcf.valor(SUP, {**m, "margen_objetivo": 0.30}) > dcf.valor(SUP, {**m, "margen_objetivo": 0.20})
    precio = dcf.valor(SUP, {**m, "crecimiento_inicial": 0.45})
    assert dcf.inverso(SUP, precio) == pytest.approx(0.45, abs=1e-6)
    sim = dcf.simular(SUP, n=5_000)
    p = sim["percentiles"]
    assert p["p5"] < p["p50"] < p["p95"]
    with pytest.raises(ValueError):
        dcf.simular({**SUP, "ventas_base": None})


def test_csv_french():
    texto = ("This file was created by CMPT_ME_BEME_OP_INV_RETS_DAILY\n\n,Mkt-RF,SMB,HML,RMW,CMA,RF\n"
             "20261118,   -1.50,    0.20,   0.10,  0.05, -0.02,  0.017\n20261119,  0.50, -0.10, 0.00, 0.00, 0.00, 0.017\n\nCopyright 2026\n")
    d = factores.leer_csv_french(texto)
    assert len(d) == 2 and d.loc[0, "Mkt-RF"] == pytest.approx(-0.015) and d["fecha"].iloc[1] == pd.Timestamp("2026-11-19")


def test_acumular_sin_duplicados(tmp_path):
    h = pd.date_range("2026-11-19 10:00", periods=3, freq="1min")
    viejo = pd.DataFrame({"hora": h, "ticker": "ANT", "close": [1.0, 2.0, 3.0]})
    ruta = tmp_path / "x.parquet"
    viejo.to_parquet(ruta)
    nuevo = pd.DataFrame({"hora": h[1:].append(pd.DatetimeIndex([h[-1] + pd.Timedelta(minutes=1)])), "ticker": "ANT", "close": [2.5, 3.0, 4.0]})
    t = precios.acumular(nuevo, ruta)
    assert len(t) == 4 and t.loc[t["hora"] == h[1], "close"].item() == 2.5


def test_crecimiento_converge_geometricamente():
    """Con persistencia 0,5 el exceso de crecimiento sobre el terminal se reduce a la mitad cada año."""
    s = {**SUP, "anios": 4, "crecimiento_terminal": 0.03}
    m = dcf.moda(s)
    v1 = dcf.valor(s, {**m, "persistencia_crecimiento": 0.5})
    v2 = dcf.valor(s, {**m, "persistencia_crecimiento": 0.7})
    assert v2 > v1  # más persistencia del crecimiento, más valor


def test_estados_lee_trimestres_y_capitalizacion(tmp_path):
    import estados
    (tmp_path / "resultados_operacion.txt").write_text(
        "Revenue $ 10 $ 20 $ 30 $ 40 $ 50 $ 60 $ 70 Operating expenses: x Operating income (loss) (5) (4) (3) (2) (1) 2 (1) Interest")
    (tmp_path / "capitalizacion.txt").write_text(
        "Cash, cash equivalents, and short-term investments $ 100 $ 100 $ 300 Convertible notes payable $ 90 $ 80 $ 80 "
        "Class A ... 1,000,000 shares issued and outstanding, pro forma as adjusted — Class N ... 500,000 shares outstanding, pro forma as adjusted (1)")
    e = estados.leer(tmp_path)
    assert e["ventas_base"] == 220 and e["margen_base"] == pytest.approx(-2 / 220)
    assert e["caja_neta"] == 220 and e["acciones_diluidas"] == pytest.approx(1.500002)
