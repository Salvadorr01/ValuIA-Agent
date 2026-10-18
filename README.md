# VALUIA-AGENT

Agente inteligente que sugiere un precio de referencia y un rango razonable para una propiedad que se va a publicar, a partir de sus características y de las ventas comparables recientes. Proyecto de la asignatura Inteligencia Artificial (Universidad Tecnológica de Bolívar, docente Edwin Puertas).

- ESTUDIANTE 1: Salvador Simarra Cassiani (T00079076)
- ESTUDIANTE 2: Jesús Nicanor Gutiérrez Grau (T00068008)

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

| Medida | Fórmula | Meta |
|---|---|---|
| Error porcentual absoluto medio (MAPE) | media de \|precio real − precio estimado\| / precio real × 100 | menor al 10 % |
| Cobertura del rango | % de propiedades cuyo precio real cae dentro del rango sugerido | al menos 80 % |

Resultados completos de la Fase 3: [PENDIENTE]

## Requisitos

- Python 3.13
- Librerías: ver `requirements.txt` (pandas 3.0.6, numpy 2.5.4, scikit-learn 1.9.1)

## Instalación y ejecución

```
git clone [PENDIENTE: URL del repositorio]
cd ValuIA-Agent
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

(Los dos comandos del entorno virtual son para Windows; en Linux o Mac se usa `source .venv/bin/activate`.)

Al ejecutar `python main.py` aparece un menú:

1. Ejecutar la simulación completa: pide una semilla, valora las 200 propiedades y muestra MAPE, cobertura y recalibraciones. El log se guarda en `logs/ejecucion_semillaN.csv`.
2. Valorar una propiedad que el usuario describa: Enter usa valores típicos; si se escribe un dato inválido, el agente lo rechaza con un mensaje.
3. Salir.

También se puede ejecutar directo: `python main.py --simulacion 3`.

## Estructura del proyecto

| Archivo | Función |
|---|---|
| `main.py` | Interfaz por terminal |
| `agente.py` | Agente: percibir, validar, decidir, actuar y aprender |
| `modelo.py` | Modelo de precio (Gradient Boosting sobre el logaritmo del precio) |
| `simulador.py` | Entorno simulado de listados y ventas |
| `datos.py` | Carga y preparación de los datos |
| `evaluar_modelo.py` | Evalúa el modelo solo, sin el agente |
| `data/` | Dataset Ames Housing |
| `logs/` | Registros de ejecución |

## Limitaciones

- Los datos son de una sola ciudad (Ames, Iowa), de 2006 a 2010; el modelo no se puede usar tal cual en otro mercado.
- El mercado de Ames se mantuvo casi plano en esos años, por lo que el ajuste por mercado tiene un efecto pequeño.
- En las pruebas no participa un agente inmobiliario humano; la salida es solo una sugerencia.