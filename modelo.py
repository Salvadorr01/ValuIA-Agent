"""
modelo.py - Modelo de regresión de VALUIA-AGENT.

Este es el "cerebro" que estima el precio de una propiedad a partir de sus
14 características. Aprende de las ventas del historial (2006-2008).

Detalles:
  * Se entrena con el LOGARITMO del precio. Los precios de casas son muy
    desiguales (de 13 mil a 755 mil) y con el logaritmo el modelo se equivoca
    en proporción, que es justo lo que mide el MAPE.
  * El barrio es un texto, así que se convierte en columnas de 0 y 1
    (una por barrio) con OneHotEncoder. Las demás características ya son números.
  * El regresor es GradientBoostingRegressor: construye muchos árboles de
    decisión pequeños, cada uno corrigiendo los errores del anterior.
"""
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from datos import CARACTERISTICAS, CATEGORICAS


class ModeloPrecio:
    def __init__(self, semilla: int = 0):
        codificar = ColumnTransformer(
            [("barrio", OneHotEncoder(handle_unknown="ignore"), CATEGORICAS)],
            remainder="passthrough",          # las columnas numéricas pasan tal cual
        )
        regresor = GradientBoostingRegressor(
            n_estimators=300, max_depth=3, learning_rate=0.05,
            subsample=0.8, random_state=semilla,
        )
        self.pipeline = Pipeline([("codificar", codificar), ("regresor", regresor)])
        self.entrenado = False

    def entrenar(self, ventas: pd.DataFrame):
        """Aprende de una tabla de ventas (con las 14 características y el precio)."""
        self.pipeline.fit(ventas[CARACTERISTICAS], np.log(ventas["precio"]))
        self.entrenado = True
        return self

    def predecir(self, ventas: pd.DataFrame) -> np.ndarray:
        """Estima el precio de varias propiedades a la vez."""
        return np.exp(self.pipeline.predict(ventas[CARACTERISTICAS]))

    def predecir_una(self, propiedad: dict) -> float:
        """Estima el precio de una sola propiedad (un diccionario con las 14 características)."""
        fila = pd.DataFrame([propiedad])
        return float(self.predecir(fila)[0])