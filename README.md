# VALUIA-AGENT

Agente inteligente que sugiere un precio de referencia y un rango razonable para una propiedad que se va a publicar, a partir de sus características y de las ventas comparables recientes. Proyecto de la asignatura Inteligencia Artificial (Universidad Tecnológica de Bolívar, docente Edwin Puertas).

- ESTUDIANTE 1: Salvador Simarra Cassiani (T00079076)
- ESTUDIANTE 2: Jesús Nicanor Gutiérrez Grau (T00068008)

## Aplicación desplegada

Se puede probar sin instalar nada en: **https://valuia-agent.streamlit.app/**

La página tiene tres pestañas: valorar una propiedad descrita por el usuario (incluye el rechazo de datos inválidos), ejecutar la simulación completa con las dos medidas de desempeño y consultar los resultados de las pruebas de la Fase 3. Si la aplicación estuvo sin uso, el servicio gratuito la duerme: basta con pulsar el botón para reactivarla y esperar uno o dos minutos.

## Qué hace el agente

El agente trabaja en un ciclo de cinco pasos para cada propiedad nueva:

1. **Percibir**: recibe las 14 características de la propiedad.
2. **Validar**: rechaza datos faltantes, no numéricos o fuera de rango (no publica nada en ese caso).
3. **Decidir**: estima el precio con un modelo de regresión (Gradient Boosting) y lo ajusta con el comportamiento de ventas comparables del mismo barrio. Calcula un rango y un nivel de incertidumbre.
4. **Actuar**: publica el precio de referencia y el rango como sugerencia. La decisión final es del agente inmobiliario humano.
5. **Aprender**: cuando se conoce el precio real de venta calcula su error y, cada 50 ventas, reentrena el modelo con la información nueva.

Cada evento queda registrado en un log CSV con marca de tiempo.

## Datos y simulador

- Datos: *Ames Housing* (Kaggle), 2930 ventas de casas en Ames, Iowa, entre 2006 y 2010. El archivo está en `data/AmesHousing.csv`.
- No existe un sistema real de listados, así que `simulador.py` lo simula: las ventas de 2006-2008 (1941) son el historial de entrenamiento; de 2009-2010 se reservan 200 propiedades nuevas con el precio oculto hasta que el agente publica su sugerencia, y las 789 restantes sirven como ventas comparables recientes. La aleatoriedad (qué propiedades llegan, en qué orden y qué comparables hay) se controla con una semilla.

## Medidas de desempeño

Los umbrales se fijaron antes de ejecutar las pruebas.

| Medida | Fórmula | Umbral |
|---|---|---|
| Error porcentual absoluto medio (MAPE) | media de \|precio real − precio estimado\| / precio real × 100 | menor al 10 % |
| Cobertura del rango | % de propiedades cuyo precio real cae dentro del rango sugerido | al menos 80 % |

## Resultados de las pruebas (Fase 3)

Cada escenario se ejecutó 5 veces (semillas 0, 1, 2, 3 y 4) sobre 200 propiedades nuevas, salvo donde se indica. Se muestra la media y, entre paréntesis, la desviación estándar. Un escenario cumple una medida si la media de las 5 ejecuciones cumple el umbral.

| # | Tipo | Escenario | MAPE (%) | Cumple | Cobertura (%) | Cumple |
|---|---|---|---|---|---|---|
| 1 | Normal | Configuración estándar | 9,55 (0,61) | Sí | 83,5 (1,17) | Sí |
| 2 | Normal | Sin recalibración | 9,54 (0,55) | Sí | 83,6 (1,08) | Sí |
| 3 | Normal | Recalibración cada 20 ventas | 9,62 (0,53) | Sí | 82,5 (0,71) | Sí |
| 4 | Normal | Pocas propiedades (50) | 9,11 (0,85) | Sí | 85,6 (1,67) | Sí |
| 5 | Límite | Solo propiedades baratas (10 % inferior) | 21,46 (6,13) | No | 75,0 (9,35) | No |
| 6 | Límite | Solo propiedades caras (10 % superior) | 8,01 (1,24) | Sí | 82,0 (10,37) | Sí |
| 7 | Límite | Historial reducido (20 %) | 10,37 (0,95) | No | 83,3 (2,31) | Sí |
| 8 | Límite | Pocos comparables (10 % de las ventas recientes) | 9,59 (0,64) | Sí | 83,4 (5,73) | Sí |
| 9 | Falla esperada | Barrio desconocido (sin comparables) | 9,87 (0,63) | Sí | 94,7 (0,57) | Sí |
| 10 | Falla esperada | 20 % de propiedades con datos inválidos | 9,22 (0,65) | Sí | 82,9 (1,14) | Sí |
| 11 | Falla esperada | Choque de mercado: precios +30 % | 17,76 (0,76) | No | 40,0 (4,02) | No |
| 12 | Falla esperada | Choque de mercado: precios −30 % | 31,08 (1,34) | No | 30,0 (1,87) | No |

Observaciones principales:

- En los escenarios normales el agente cumple, pero con poco margen: en el escenario 1, 3 de las 5 ejecuciones quedaron por debajo del 10 % de MAPE.
- En el escenario 9 el agente marcó incertidumbre alta en el 100 % de los casos; las medidas cumplen porque el rango por defecto es más ancho (cerca de 55 % de ancho frente a 36 % en el estándar), no porque sea más preciso.
- En el escenario 10 el agente rechazó el 100 % de las propiedades inválidas y no publicó nada de ellas.
- Las debilidades claras son las casas baratas (sobrestimación), el historial reducido y los cambios bruscos de mercado.

Evidencia completa en `logs/pruebas/`:

| Archivo | Contenido |
|---|---|
| `resultados_por_ejecucion.csv` | Una fila por escenario y semilla (60 ejecuciones) |
| `resumen_escenarios.csv`, `resumen.json`, `resumen.txt` | Medias, desviaciones y veredicto por escenario |
| `detalle_propiedades.csv` | Una fila por propiedad valorada |
| `eventos_escenario9_semilla0.csv`, `eventos_escenario10_semilla0.csv` | Log de eventos del agente en dos fallas esperadas |

## Casos de prueba sugeridos

Para ver el agente en funcionamiento, en la aplicación desplegada (https://valuia-agent.streamlit.app/) se sugiere probar estos cuatro casos, en este orden:

| Caso | Qué hacer | Resultado esperado |
|---|---|---|
| Típico | En la pestaña "Valorar una propiedad", pulsar "Valorar propiedad" sin cambiar los valores | Precio de referencia cercano a USD 168 mil, con un rango de unos USD 135 mil a 209 mil e incertidumbre normal (10 comparables). El valor exacto puede variar unos pocos miles de dólares entre consultas, porque los comparables se eligen al azar |
| Dato inválido (falla esperada) | Cambiar el área construida a `-50` y pulsar "Valorar propiedad" | Mensaje de error: el agente rechaza la propiedad, indica el motivo (`area_m2=-50.0 fuera de rango (10 a 1000)`) y no publica ninguna sugerencia |
| Barrio desconocido (falla esperada) | Escribir el barrio `Zzz` y pulsar "Valorar propiedad" | Aviso de incertidumbre alta: no hay ventas comparables y el rango es más ancho |
| Simulación completa | En la pestaña "Simulación completa", dejar la semilla en 0 y pulsar "Ejecutar simulación" | MAPE de 9,24 %, cobertura de 84,5 % y 4 recalibraciones; las dos medidas cumplen su umbral |

Los resultados de los 12 escenarios de la Fase 3 están en la pestaña "Pruebas de la Fase 3" y en `logs/pruebas/`.

## Requisitos

- Python 3.13
- Librerías: ver `requirements.txt` (pandas 3.0.6, numpy 2.5.4, scikit-learn 1.9.1, streamlit 1.66.0)

## Instalación y ejecución

```
git clone https://github.com/Salvadorr01/ValuIA-Agent.git
cd ValuIA-Agent
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

(Los dos comandos del entorno virtual son para Windows; en Linux o Mac se usa `source .venv/bin/activate`.)

Interfaz por terminal:

```
python main.py
```

Al ejecutarla aparece un menú: 1) ejecutar la simulación completa (pide una semilla y muestra MAPE, cobertura y recalibraciones; guarda el log en `logs/ejecucion_semillaN.csv`), 2) valorar una propiedad que el usuario describa (Enter usa valores típicos; un dato inválido se rechaza con un mensaje), 3) salir. También se puede ejecutar directo: `python main.py --simulacion 3`.

Aplicación web en el computador local:

```
python -m streamlit run app.py
```

Repetir las pruebas de la Fase 3 (12 escenarios x 5 semillas, entre 6 y 15 minutos):

```
python pruebas.py
```

Genera los archivos de `logs/pruebas/`. Para probar solo algunos escenarios: `python pruebas.py --escenarios 1 10 --semillas 0 --salida logs/prueba_rapida`.

## Estructura del proyecto

| Archivo | Función |
|---|---|
| `main.py` | Interfaz por terminal |
| `app.py` | Interfaz web (Streamlit), desplegada en el enlace de arriba |
| `agente.py` | Agente: percibir, validar, decidir, actuar y aprender |
| `modelo.py` | Modelo de precio (Gradient Boosting sobre el logaritmo del precio) |
| `simulador.py` | Entorno simulado de listados y ventas |
| `datos.py` | Carga y preparación de los datos |
| `evaluar_modelo.py` | Evalúa el modelo solo, sin el agente |
| `pruebas.py` | Pruebas de la Fase 3 (12 escenarios x 5 semillas) |
| `data/` | Dataset Ames Housing |
| `logs/` | Registros de ejecución y evidencia de las pruebas |

## Limitaciones

- Los datos son de una sola ciudad (Ames, Iowa), de 2006 a 2010; el modelo no se puede usar tal cual en otro mercado.
- El mercado de Ames se mantuvo casi plano en esos años, por lo que el ajuste por mercado tiene un efecto pequeño. Ante un cambio brusco de precios (escenarios 11 y 12) el agente se adapta lento y falla.
- El agente sobrestima las casas baratas y pierde precisión con poco historial.
- La cobertura de las casas caras (y de las baratas) se mide con solo 20 propiedades por ejecución, por lo que varía mucho entre semillas.
- En las pruebas no participa un agente inmobiliario humano; la salida es solo una sugerencia.