"""Cifras base de la valoración, leídas del prospecto final (424B4), no copiadas a mano.

- Ingresos y resultado operativo de los últimos doce meses: suma de los cuatro trimestres más recientes de la
  tabla trimestral ("Quarterly Consolidated Statements of Operations").
- Caja neta después de la oferta: caja, equivalentes e inversiones de corto plazo menos los pagarés convertibles,
  columna "pro forma as adjusted" de la tabla de capitalización.
- Acciones después de la oferta: Clase A en circulación más Clase N en circulación, pro forma as adjusted
  (las clases T y F tienen una acción cada una).
Cifras en millones de USD; acciones en millones.
"""
import pathlib, re

RAIZ = pathlib.Path(__file__).resolve().parents[1]
CARPETA = RAIZ / "resultados" / "extractos_424b4"


def _numeros(s: str) -> list[float]:
    """'$ 376 $ 787 (1,200) 974' -> [376, 787, -1200, 974]"""
    return [(-1 if a.startswith("(") else 1) * float(a.strip("()").replace(",", ""))
            for a in re.findall(r"\(?\d[\d,]*\)?", s)]


def fila(texto: str, etiqueta: str, n: int) -> list[float]:
    m = re.search(re.escape(etiqueta) + r"((?:\s*\$?\s*\(?[\d,]+\)?){%d})" % n, texto)
    if not m:
        raise ValueError(f"No encontré la fila '{etiqueta}' con {n} valores.")
    return _numeros(m.group(1))


def leer(carpeta: pathlib.Path = CARPETA) -> dict:
    trim = (carpeta / "resultados_operacion.txt").read_text()
    cap = (carpeta / "capitalizacion.txt").read_text()
    ingresos = fila(trim, "Revenue", 7)
    operativo = fila(trim, "Operating income (loss)", 7)
    caja = fila(cap, "Cash, cash equivalents, and short-term investments", 3)[-1]
    pagares = fila(cap, "Convertible notes payable", 3)[-1]
    a = re.search(r"([\d,]+) shares issued and outstanding, pro forma as adjusted", cap)
    n = re.search(r"([\d,]+) shares outstanding, pro forma as adjusted", cap)
    if not (a and n):
        raise ValueError("No encontré las acciones pro forma as adjusted.")
    clase_a, clase_n = (int(x.group(1).replace(",", "")) for x in (a, n))
    ventas_ltm = sum(ingresos[-4:])
    return {"ingresos_trimestrales": ingresos, "operativo_trimestral": operativo,
            "ventas_base": ventas_ltm, "margen_base": sum(operativo[-4:]) / ventas_ltm,
            "ventas_ultimo_trimestre_anualizadas": ingresos[-1] * 4,
            "caja": caja, "pagares_convertibles": pagares, "caja_neta": caja - pagares,
            "acciones_clase_a": clase_a, "acciones_clase_n": clase_n,
            "acciones_diluidas": (clase_a + clase_n + 2) / 1e6}
