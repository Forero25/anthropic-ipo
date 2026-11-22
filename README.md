# La salida a bolsa de Anthropic, con datos

Anthropic, la empresa que desarrolla Claude, empezó a cotizar en el Nasdaq el 19 de noviembre de 2026 con el símbolo ANT. Este repositorio estudia esa salida a bolsa con las herramientas de las finanzas empíricas: cuánto dinero quedó sobre la mesa el primer día, cómo se mueve la acción frente al mercado y a sus pares, y qué crecimiento hace falta para justificar su precio.

## Qué calcula

| Bloque | Pregunta | Método | Estado |
|---|---|---|---|
| Oferta | ¿A qué precio y cuántas acciones? | Lectura del prospecto final (424B4) en SEC EDGAR, cruzada con la prensa | Corre en cada actualización |
| Primer día | ¿Cuánto subió desde el precio de oferta? | Retorno del primer día, prima de apertura, retorno ajustado por el Nasdaq-100, dinero dejado sobre la mesa (Ritter, 1991; Loughran y Ritter, 2004) | Corre en cada actualización |
| Recorrido intradía | ¿Cuándo hizo máximos y mínimos? | Precios de 1 minuto, VWAP | Corre en cada actualización |
| Riesgo | ¿Cuánto se mueve y con qué? | Volatilidad realizada con retornos de 5 minutos; beta frente al Nasdaq-100 con errores robustos; correlaciones con NVDA, MSFT, GOOGL, AMZN, META y ORCL | La beta se estima desde 20 sesiones |
| Volatilidad condicional | ¿La volatilidad persiste? | GARCH(1,1) con errores t | Desde 120 sesiones |
| Factores | ¿Es solo mercado o también tamaño, valor y momentum? | Fama-French de cinco factores más momentum | Desde 60 sesiones con factores publicados |
| Valoración | ¿Qué crecimiento descuenta el precio? | DCF con simulación de Monte Carlo, DCF inverso y análisis de sensibilidad | Cuando `entradas/supuestos.yaml` tenga las cifras del prospecto |

Cada medida dice cuántas observaciones usa y no se calcula si son muy pocas. Con una semana de historia, una beta no significa nada, y el resultado lo dice en vez de inventar precisión.

## Cómo está hecho

```
ingesta/edgar.py     prospecto final (424B4) de EDGAR ──> resultados/oferta_edgar.json
ingesta/precios.py   Yahoo Finance: diarios + 1 minuto acumulado ──> datos/ (caché del flujo, no se publica)
ingesta/factores.py  biblioteca de Kenneth French ──> datos/factores.parquet
analisis/            oferta, debut, riesgo, dcf ──> resultados/resumen.json
```

GitHub Actions corre todo cada día hábil después del cierre de Nueva York (`.github/workflows/diario.yml`): pruebas, descarga y análisis. Yahoo guarda los precios de 1 minuto unos 30 días; el flujo los acumula en su caché para no perder el primer día.

## Lo que este proyecto no hace

- **No es una recomendación de inversión.** Describe lo que pasó y qué supuestos son coherentes con el precio; no dice si comprar o vender.
- **El DCF no es un precio objetivo.** Es una distribución de valores bajo supuestos explícitos, cada uno con su fuente; cambiar los supuestos cambia el resultado, y el análisis de sensibilidad muestra cuánto.
- **No publica precios.** Se descargan en cada corrida; el repositorio solo guarda retornos y estadísticas.
- **No usa cifras de la prensa como resultado.** La prensa sirve para cruzar: si el prospecto dice otra cosa, el flujo se detiene.
- **No compara todavía con otras salidas a bolsa.** La comparación con la cohorte histórica (datos de Jay Ritter) es la siguiente fase.

## Conflicto de interés

Este proyecto se desarrolló con ayuda de Claude, un modelo de Anthropic, la empresa que se analiza. Por eso todas las cifras salen de código y de fuentes públicas verificables, el tono es descriptivo y no hay recomendaciones.

## Reproducir

```
pip install -r requirements.txt
pytest
python ingesta/precios.py
python ingesta/factores.py
SEC_USER_AGENT="Tu nombre tu@correo" python ingesta/edgar.py   # la SEC exige nombre y correo
python analisis/correr.py
```

## Datos y licencias

- Prospecto: SEC EDGAR (dominio público).
- Precios: Yahoo Finance, descargados en cada corrida y no redistribuidos.
- Factores: [Kenneth R. French Data Library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html).

Código bajo licencia MIT.
