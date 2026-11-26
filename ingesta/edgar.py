"""Prospecto final (424B4) de Anthropic en SEC EDGAR: precio de la oferta y número de acciones.

La SEC exige un User-Agent con nombre y correo. Se toma de la variable de entorno SEC_USER_AGENT
(en GitHub, un secreto del repositorio); el código no lo guarda en ningún archivo.
"""
import html, json, os, pathlib, re, sys, time

import requests

RAIZ = pathlib.Path(__file__).resolve().parents[1]
CRUDO = RAIZ / "datos" / "edgar"
SALIDA = RAIZ / "resultados" / "oferta_edgar.json"


def sesion():
    # Se limpian espacios, saltos de línea y comillas que suelen colarse al pegar el secreto
    ua = " ".join(os.environ.get("SEC_USER_AGENT", "").split()).strip("\"' ")
    if not ua:
        sys.exit("Falta SEC_USER_AGENT (nombre y correo, como pide la SEC).")
    s = requests.Session()
    s.headers.update({"User-Agent": ua, "Accept-Encoding": "gzip, deflate"})
    return s


def get(s, url):
    for intento in range(4):
        r = s.get(url, timeout=60)
        if r.status_code == 200:
            time.sleep(0.2)  # la SEC pide no pasar de 10 peticiones por segundo
            return r
        time.sleep(2 ** intento)
    r.raise_for_status()


def buscar_cik(s, ticker="ANT", nombre="anthropic"):
    tabla = get(s, "https://www.sec.gov/files/company_tickers.json").json()
    for fila in tabla.values():
        if fila["ticker"].upper() == ticker or nombre in fila["title"].lower():
            return int(fila["cik_str"])
    sys.exit("No encontré a Anthropic en company_tickers.json de la SEC.")


def a_texto(contenido: str) -> str:
    sin_tags = re.sub(r"<[^>]+>", " ", re.sub(r"(?is)<(script|style).*?</\1>", " ", contenido))
    return re.sub(r"\s+", " ", html.unescape(sin_tags)).strip()


def _num(x: str) -> float:
    return float(x.replace(",", ""))


def leer_portada(texto: str) -> dict:
    """Cifras de la portada del prospecto. Se toma la primera coincidencia de cada una: la portada va primero.
    Se verifica que acciones nuevas + acciones de accionistas vendedores = total, y que total × precio = monto bruto."""
    pat = {
        "acciones_ofrecidas": r"Class A Common Stock ([\d,]+) Shares",
        "acciones_primarias": r"We are selling ([\d,]+) shares of Class A common stock",
        "acciones_secundarias": r"selling stockholders[^.]{0,80}?selling an additional ([\d,]+) shares",
        "precio_oferta": r"initial public offering price(?: per share)? (?:is|of) \$\s?(\d[\d,]*\.?\d*)",
        "descuento_por_accion": r"Underwriting discount(?: \(\d\))? \$ ?([\d.]+)",
        "ingresos_anthropic_antes_gastos": r"Proceeds, before expenses, to Anthropic, PBC \$ ?[\d.]+ \$ ?([\d,]+)",
        "opcion_sobreasignacion": r"option to purchase up to an additional ([\d,]+) shares",
    }
    out = {}
    for k, p in pat.items():
        m = re.search(p, texto, re.I)
        if not m:
            sys.exit(f"No pude leer {k} en la portada del 424B4.")
        out[k] = _num(m.group(1))
    for k in ("acciones_ofrecidas", "acciones_primarias", "acciones_secundarias", "opcion_sobreasignacion", "ingresos_anthropic_antes_gastos"):
        out[k] = int(out[k])
    if out["acciones_primarias"] + out["acciones_secundarias"] != out["acciones_ofrecidas"]:
        sys.exit("Las acciones nuevas y las de accionistas vendedores no suman el total de la portada.")
    bruto = re.search(r"\$ ?([\d,]{13,})", texto)
    if bruto and abs(_num(bruto.group(1)) - out["acciones_ofrecidas"] * out["precio_oferta"]) > 1:
        sys.exit("Total de acciones × precio no coincide con el monto bruto de la portada.")
    return out


SECCIONES = {
    "resumen_financiero": r"summary consolidated financial (?:and other )?data",
    "capitalizacion": r"capitalization the following table sets forth",
    "acciones_en_circulacion": r"shares of (?:our )?class a common stock to be outstanding after this offering",
    "resultados_operacion": r"results of operations the following table",
    "metricas_clave": r"key (?:business|operating) metrics",
}


def guardar_extractos(texto: str, largo=15000):
    """Guarda las secciones del prospecto con las cifras que necesita la valoración (documento público de la SEC),
    para que cada supuesto del DCF se pueda citar y verificar contra el texto."""
    carpeta = RAIZ / "resultados" / "extractos_424b4"
    carpeta.mkdir(parents=True, exist_ok=True)
    for nombre, patron in SECCIONES.items():
        coincidencias = [m.start() for m in re.finditer(patron, texto, re.I)]
        # la primera aparición suele ser el índice; se toma la segunda si existe
        if coincidencias:
            i = coincidencias[1] if len(coincidencias) > 1 else coincidencias[0]
            (carpeta / f"{nombre}.txt").write_text(texto[i:i + largo])


def main():
    s = sesion()
    cik = buscar_cik(s)
    rec = get(s, f"https://data.sec.gov/submissions/CIK{cik:010d}.json").json()["filings"]["recent"]
    filas = [dict(zip(rec, v)) for v in zip(*rec.values())]
    finales = [f for f in filas if f["form"] == "424B4"]
    if not finales:
        sys.exit("Todavía no hay 424B4 en EDGAR.")
    f = finales[0]  # el más reciente
    url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{f['accessionNumber'].replace('-', '')}/{f['primaryDocument']}"
    texto = a_texto(get(s, url).text)
    CRUDO.mkdir(parents=True, exist_ok=True)
    (CRUDO / "424b4.txt").write_text(texto)
    # Portada y resumen de la oferta (documento público de la SEC): se guardan para poder auditar la lectura
    i = texto.lower().find("the offering")
    (RAIZ / "resultados" / "portada_424b4.txt").parent.mkdir(exist_ok=True)
    (RAIZ / "resultados" / "portada_424b4.txt").write_text(texto[:6000] + "\n\n[...]\n\n" + texto[max(i, 0):max(i, 0) + 6000])
    guardar_extractos(texto)
    out = {"cik": cik, "forma": "424B4", "fecha_presentacion": f["filingDate"], "url": url, **leer_portada(texto)}
    SALIDA.parent.mkdir(exist_ok=True)
    SALIDA.write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(out)


if __name__ == "__main__":
    main()
