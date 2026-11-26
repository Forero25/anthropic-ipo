"""Corre todo lo que los datos disponibles permiten y escribe resultados/resumen.json.
Cada bloque que todavía no tiene datos suficientes queda marcado como pendiente, con el motivo."""
import datetime as dt, json, pathlib, sys

import pandas as pd
import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import debut, dcf, estados, historia, oferta, riesgo  # noqa: E402

RAIZ = pathlib.Path(__file__).resolve().parents[1]
DATOS, SALIDA = RAIZ / "datos", RAIZ / "resultados"


def main():
    of = oferta.cargar()
    diarios = pd.read_parquet(DATOS / "diarios.parquet")
    r = riesgo.retornos(diarios)
    out = {"actualizado": dt.date.today().isoformat(), "ultimo_dato": str(pd.to_datetime(diarios["fecha"]).max().date()),
           "oferta": {k: of[k] for k in ("precio_oferta", "acciones_ofrecidas", "acciones_primarias", "acciones_secundarias",
                                          "descuento_por_accion", "ingresos_anthropic_antes_gastos", "opcion_sobreasignacion",
                                          "rango_indicativo", "fecha_debut", "url", "verificado") if k in of},
           "debut": debut.resumen(diarios, of)}
    if "descuento_por_accion" in of:
        out["oferta"]["comision_bancos_pct"] = of["descuento_por_accion"] / of["precio_oferta"]
    ruta_i = DATOS / "intradia_1m.parquet"
    if ruta_i.exists():
        intr = pd.read_parquet(ruta_i)
        out["recorrido"] = debut.recorrido(intr, of)
        vr = riesgo.vol_realizada(intr)
        out["vol_realizada"] = vr.to_dict("records")
    ruta_r = SALIDA / "ritter_tabla1.json"
    if ruta_r.exists():
        out["historia"] = historia.comparar(out["debut"], of, json.loads(ruta_r.read_text()))
    out["beta"] = riesgo.beta(r)
    out["correlaciones"] = riesgo.correlaciones(r)
    out["garch"] = riesgo.garch(r)
    ruta_f = DATOS / "factores.parquet"
    out["factores"] = riesgo.factores(r, pd.read_parquet(ruta_f)) if ruta_f.exists() else {"nota": "sin factores descargados"}
    sup = yaml.safe_load((RAIZ / "entradas" / "supuestos.yaml").read_text())
    try:
        base = estados.leer()
        out["estados"] = {k: v for k, v in base.items()}
        sup |= {k: base[k] for k in ("ventas_base", "margen_base", "caja_neta", "acciones_diluidas")}
    except (FileNotFoundError, ValueError) as e:
        out["estados"] = {"nota": str(e)}
    try:
        sim = dcf.simular(sup)
        precio = out["debut"]["cierre"]
        out["dcf"] = {k: v for k, v in sim.items() if k != "valores"} | {
            "precio_referencia": precio, "capitalizacion_al_precio_musd": precio * sup["acciones_diluidas"],
            "prob_valor_sobre_precio": dcf.prob_sobre(sim["valores"], precio),
            "crecimiento_implicito": dcf.inverso(sup, precio), "tornado": dcf.tornado(sup)}
    except ValueError as e:
        out["dcf"] = {"nota": str(e)}
    SALIDA.mkdir(exist_ok=True)
    (SALIDA / "resumen.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(json.dumps({k: out[k] for k in ("oferta", "debut", "beta")}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
