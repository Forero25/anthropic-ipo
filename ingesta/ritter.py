"""Estadísticas de salidas a bolsa en EE. UU. desde 1980 (Jay R. Ritter, Universidad de Florida,
"Initial Public Offerings: Updated Statistics"). Se guarda el texto del informe en datos/ (no se publica)
y se leen las tablas que la comparación necesita."""
import pathlib, subprocess, sys

import requests

RAIZ = pathlib.Path(__file__).resolve().parents[1]
URL = "https://site.warrington.ufl.edu/ritter/files/IPO-Statistics.pdf"


def main():
    r = requests.get(URL, timeout=120, headers={"User-Agent": "Mozilla/5.0 (investigacion academica)"})
    r.raise_for_status()
    carpeta = RAIZ / "datos" / "ritter"
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "ipo_statistics.pdf").write_bytes(r.content)
    subprocess.run(["pdftotext", "-layout", str(carpeta / "ipo_statistics.pdf"), str(carpeta / "ipo_statistics.txt")], check=True)
    texto = (carpeta / "ipo_statistics.txt").read_text(errors="ignore")
    if "--explorar" in sys.argv:
        print(texto[:9000])


if __name__ == "__main__":
    main()
