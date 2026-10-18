"""
evaluar_modelo.py - Mide qué tan bien estima precios el modelo SOLO (sin agente).

Para cada semilla: crea el entorno, entrena con el historial, valora las 200
propiedades nuevas y calcula el MAPE (error porcentual medio absoluto).
"""
import numpy as np

from modelo import ModeloPrecio
from simulador import Entorno


def mape(reales, estimados) -> float:
    reales, estimados = np.array(reales), np.array(estimados)
    return float(np.mean(np.abs(reales - estimados) / reales) * 100)


if __name__ == "__main__":
    resultados = []
    for semilla in range(5):
        entorno = Entorno(semilla=semilla)
        modelo = ModeloPrecio(semilla=semilla).entrenar(entorno.historial)

        reales, estimados = [], []
        while (propiedad := entorno.siguiente_propiedad()) is not None:
            estimado = modelo.predecir_una(propiedad)
            entorno.publicar_sugerencia(propiedad["id"], estimado, (estimado, estimado))
            reales.append(entorno.revelar_precio_final(propiedad["id"]))
            estimados.append(estimado)

        resultados.append(mape(reales, estimados))
        print(f"Semilla {semilla}: {len(reales)} propiedades valoradas, MAPE = {resultados[-1]:.2f} %")

    print(f"\nMAPE promedio de 5 ejecuciones: {np.mean(resultados):.2f} %  (desviación estándar {np.std(resultados):.2f})")
    print("Meta del diseño: MAPE menor al 10 %")