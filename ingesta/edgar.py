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
    ua = os.environ.get("SEC_USER_AGENT")
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


def leer_portada(texto: str) -> dict:
    """Precio y acciones de la portada del prospecto. Se toma la primera coincidencia: la portada va primero."""
    precio = re.search(r"initial public offering price (?:is|of) \$\s?([\d,]+\.?\d*) per share", texto, re.I)
    acciones = re.search(r"([\d,]{9,}) shares of (?:our )?Class A common stock", texto, re.I)
    if not (precio and acciones):
        sys.exit("No pude leer el precio o las acciones en la portada del 424B4.")
    return {"precio_oferta": float(precio.group(1).replace(",", "")),
            "acciones_ofrecidas": int(acciones.group(1).replace(",", ""))}


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
    out = {"cik": cik, "forma": "424B4", "fecha_presentacion": f["filingDate"], "url": url, **leer_portada(texto)}
    SALIDA.parent.mkdir(exist_ok=True)
    SALIDA.write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(out)


if __name__ == "__main__":
    main()
