"""El debut de ANT frente a 46 años de salidas a bolsa en EE. UU. (tabla 1 de Ritter, 1980-2025)."""
import numpy as np


def comparar(debut: dict, oferta: dict, ritter: dict) -> dict:
    f = ritter["filas"]
    mesa = debut["dinero_sobre_la_mesa_musd"] / 1000  # miles de millones
    recaudo = oferta["precio_oferta"] * oferta["acciones_ofrecidas"] / 1e9
    anios_mesa_mayor = [x["anio"] for x in f if x["dinero_mesa_mmusd"] > mesa]
    anios_recaudo_mayor = [x["anio"] for x in f if x["recaudo_mmusd"] > recaudo]
    total = {"recaudo": sum(x["recaudo_mmusd"] for x in f), "mesa": sum(x["dinero_mesa_mmusd"] for x in f)}
    medios = np.array([x["retorno_medio"] for x in f])
    ult = f[-1]
    return {"fuente": ritter["fuente"], "anios": [f[0]["anio"], f[-1]["anio"]],
            "dinero_mesa_ant_mmusd": mesa, "recaudo_ant_mmusd": recaudo,
            "anios_con_mas_dinero_en_la_mesa_que_ant": anios_mesa_mayor,
            "anios_con_mas_recaudo_que_ant": anios_recaudo_mayor,
            "ultimo_anio": ult,
            "ant_vs_ultimo_anio": {"mesa": mesa / ult["dinero_mesa_mmusd"], "recaudo": recaudo / ult["recaudo_mmusd"]},
            "participacion_en_total_historico": {"recaudo": recaudo / total["recaudo"], "mesa": mesa / total["mesa"]},
            "retorno_ant": debut["retorno_primer_dia"],
            "retorno_medio_historico": float(np.average([x["retorno_medio"] for x in f], weights=[x["n"] for x in f])),
            "percentil_ant_entre_medias_anuales": float((medios < debut["retorno_primer_dia"]).mean()),
            "serie": [{"anio": x["anio"], "retorno_medio": x["retorno_medio"], "dinero_mesa_mmusd": x["dinero_mesa_mmusd"],
                       "recaudo_mmusd": x["recaudo_mmusd"]} for x in f]}
