"""Estadísticas de salidas a bolsa en EE. UU. desde 1980 (Jay R. Ritter, Universidad de Florida,
"Initial Public Offerings: Updated Statistics"). Se guarda el texto del informe en datos/ (no se publica)
y se leen las tablas que la comparación necesita."""
import json, pathlib, re, subprocess, sys

import requests

RAIZ = pathlib.Path(__file__).resolve().parents[1]
URL = "https://site.warrington.ufl.edu/ritter/files/IPO-Statistics.pdf"


FILA = re.compile(r"^\s*(\d{4})\s+([\d,]+)\s+(-?[\d.]+)%\s+(-?[\d.]+)%\s+(-?[\d.]+)%\s+\$([\d.,]+) billion\s+\$([\d.,]+) billion", re.M)


def tabla1(texto: str) -> list[dict]:
    """Tabla 1: por año, número de salidas a bolsa, retorno medio del primer día (igual y por monto), mediana,
    dinero dejado sobre la mesa y monto recaudado (miles de millones de USD)."""
    i = [m.start() for m in re.finditer(r"Table 1: Mean First-day Returns and Money Left on the Table", texto)]
    bloque = texto[i[-1]:]
    bloque = bloque[:bloque.find("Table 1a")]
    filas = [{"anio": int(a), "n": int(n.replace(",", "")), "retorno_medio": float(ew) / 100, "retorno_ponderado": float(pw) / 100,
              "retorno_mediano": float(md) / 100, "dinero_mesa_mmusd": float(dm.replace(",", "")), "recaudo_mmusd": float(rc.replace(",", ""))}
             for a, n, ew, pw, md, dm, rc in FILA.findall(bloque)]
    if len(filas) < 40 or filas[0]["anio"] != 1980:
        sys.exit(f"Tabla 1 de Ritter con formato inesperado: {len(filas)} filas.")
    return filas


def main():
    r = requests.get(URL, timeout=120, headers={"User-Agent": "Mozilla/5.0 (investigacion academica)"})
    r.raise_for_status()
    carpeta = RAIZ / "datos" / "ritter"
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "ipo_statistics.pdf").write_bytes(r.content)
    subprocess.run(["pdftotext", "-layout", str(carpeta / "ipo_statistics.pdf"), str(carpeta / "ipo_statistics.txt")], check=True)
    texto = (carpeta / "ipo_statistics.txt").read_text(errors="ignore")
    filas = tabla1(texto)
    (RAIZ / "resultados").mkdir(exist_ok=True)
    (RAIZ / "resultados" / "ritter_tabla1.json").write_text(json.dumps(
        {"fuente": "Jay R. Ritter, Initial Public Offerings: Updated Statistics, Table 1", "url": URL, "filas": filas}, indent=1))
    print("Ritter: tabla 1 con", len(filas), "años")
    if "--explorar" in sys.argv:
        for titulo in ("Table 1: Mean First-day Returns", "Table 11: Mean and Median Gross Spreads"):
            pos = [i for i in range(len(texto)) if texto.startswith(titulo, i)]
            i = pos[1] if len(pos) > 1 else (pos[0] if pos else 0)
            print("=" * 20, titulo, "\n", texto[i:i + 7000])


if __name__ == "__main__":
    main()
