"""
agente.py - VALUIA-AGENT: agente de aprendizaje que valora propiedades.

Ciclo del agente (se repite por cada propiedad):
    PERCEPCIÓN  -> recibe una propiedad nueva y verifica que sus datos sean válidos
    DECISIÓN    -> estima el precio con el modelo, consulta comparables recientes,
                   ajusta por el mercado y calcula un rango razonable
    ACCIÓN      -> publica el precio de referencia y el rango en el sistema de listados
    APRENDIZAJE -> cuando se conoce el precio real, mide su error y cada cierto
                   número de ventas recalibra el modelo

Todo lo que ocurre queda en un log (archivo CSV) con marca de tiempo.
"""
import csv
import json
import os
from datetime import datetime

import numpy as np
import pandas as pd

from datos import CARACTERISTICAS
from modelo import ModeloPrecio

# Valores permitidos para cada característica numérica (mínimo, máximo)
RANGOS_VALIDOS = {
    "area_m2": (10, 1000), "habitaciones": (0, 15), "antiguedad": (0, 300), "calidad": (1, 10),
    "sotano_m2": (0, 1000), "garaje_autos": (0, 10), "banos": (0, 10), "medios_banos": (0, 10),
    "lote_m2": (50, 100000), "condicion": (1, 10), "primer_piso_m2": (10, 1000),
    "anios_remodelacion": (0, 300), "chimeneas": (0, 10),
}

K_COMPARABLES = 10        # cuántos comparables pide el agente por valoración
MIN_COMPARABLES = 3       # con menos de estos, la estimación se marca como incierta
SUAVIZADO = 30            # qué tanto confía en los comparables al ajustar por el mercado
Z_RANGO = 1.5             # ancho del rango en desviaciones estándar
DISPERSION_MINIMA = 0.05  # el rango nunca es más angosto que esto
DISPERSION_POR_DEFECTO = 0.18   # dispersión usada cuando hay pocos comparables


class AgenteValuIA:
    def __init__(self, entorno, semilla: int = 0, ruta_log: str = None, recalibrar_cada: int = 50):
        self.entorno = entorno
        self.semilla = semilla
        self.recalibrar_cada = recalibrar_cada
        self.ruta_log = ruta_log

        # Memoria a largo plazo: el modelo aprende del historial (2006-2008)
        self.modelo = ModeloPrecio(semilla).entrenar(entorno.historial)
        self.ventas_aprendidas = []      # ventas cuyo precio real ya se conoce
        self.resultados = []             # una fila por propiedad valorada
        self.recalibraciones = 0

        if ruta_log:
            carpeta = os.path.dirname(ruta_log)
            if carpeta:
                os.makedirs(carpeta, exist_ok=True)
            if not os.path.exists(ruta_log):
                with open(ruta_log, "w", newline="", encoding="utf-8") as f:
                    csv.writer(f).writerow(["marca_de_tiempo", "semilla", "id_propiedad", "evento", "detalle"])
        self._registrar(None, "inicio", {"historial": len(entorno.historial)})

    # ------------------------------------------------------------------ log
    def _registrar(self, id_propiedad, evento: str, detalle: dict):
        """Agrega una línea al log: cuándo, en qué ejecución, a qué propiedad y qué pasó."""
        if not self.ruta_log:
            return
        fila = [datetime.now().isoformat(timespec="milliseconds"), self.semilla, id_propiedad,
                evento, json.dumps(detalle, ensure_ascii=False, default=str)]
        with open(self.ruta_log, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(fila)

    # ------------------------------------------------------------------ percepción
    def percibir(self):
        """Pide al entorno la siguiente propiedad nueva (None si ya no hay)."""
        return self.entorno.siguiente_propiedad()

    def validar(self, propiedad: dict) -> list:
        """Revisa que lleguen las 14 características y que sus valores sean razonables."""
        errores = []
        for nombre in CARACTERISTICAS:
            valor = propiedad.get(nombre)
            if valor is None or (isinstance(valor, float) and np.isnan(valor)):
                errores.append(f"falta {nombre}")
            elif nombre == "barrio":
                if not isinstance(valor, str) or not valor.strip():
                    errores.append("barrio inválido")
            elif not isinstance(valor, (int, float, np.integer, np.floating)) or isinstance(valor, bool):
                errores.append(f"{nombre} no es numérico")
            else:
                minimo, maximo = RANGOS_VALIDOS[nombre]
                if not (minimo <= valor <= maximo):
                    errores.append(f"{nombre}={valor} fuera de rango ({minimo} a {maximo})")
        return errores

    # ------------------------------------------------------------------ decisión
    def decidir(self, propiedad: dict) -> dict:
        """Calcula el precio de referencia y el rango razonable."""
        precio_modelo = self.modelo.predecir_una(propiedad)

        # Memoria a corto plazo: comparables recientes del mismo barrio
        comparables = self.entorno.consultar_comparables(propiedad["barrio"], K_COMPARABLES)
        n = len(comparables)

        if n >= MIN_COMPARABLES:
            # ¿El modelo, con lo aprendido del historial, acierta en las ventas recientes?
            razones = comparables["precio"].values / self.modelo.predecir(comparables)
            desplazamiento = float(np.median(razones))             # >1: el mercado subió; <1: bajó
            dispersion = max(float(np.std(np.log(razones))), DISPERSION_MINIMA)
            peso = n / (n + SUAVIZADO)                             # pocos comparables -> ajuste suave
            factor = 1 + peso * (desplazamiento - 1)
            incertidumbre = "normal"
        else:
            factor, dispersion, incertidumbre = 1.0, DISPERSION_POR_DEFECTO, "alta"

        precio = precio_modelo * factor
        rango = (precio * float(np.exp(-Z_RANGO * dispersion)), precio * float(np.exp(Z_RANGO * dispersion)))
        return {"precio": precio, "rango": rango, "precio_modelo": precio_modelo,
                "factor_mercado": factor, "n_comparables": n, "incertidumbre": incertidumbre}

    # ------------------------------------------------------------------ acción
    def actuar(self, id_propiedad: int, decision: dict):
        """Publica la sugerencia en el sistema de listados (el humano decide el precio final)."""
        self.entorno.publicar_sugerencia(id_propiedad, decision["precio"], decision["rango"])

    # ------------------------------------------------------------------ aprendizaje
    def aprender(self, propiedad: dict, decision: dict, precio_real: float) -> dict:
        """Compara lo estimado con el precio real y, cada cierto número de ventas, recalibra."""
        error = abs(precio_real - decision["precio"]) / precio_real * 100
        dentro = decision["rango"][0] <= precio_real <= decision["rango"][1]
        self._registrar(propiedad["id"], "retroalimentacion",
                        {"precio_real": precio_real, "error_pct": round(error, 2), "dentro_del_rango": dentro})

        fila = {nombre: propiedad[nombre] for nombre in CARACTERISTICAS}
        fila["precio"] = precio_real
        self.ventas_aprendidas.append(fila)

        if len(self.ventas_aprendidas) % self.recalibrar_cada == 0:
            ventas = pd.concat([self.entorno.historial, pd.DataFrame(self.ventas_aprendidas)], ignore_index=True)
            self.modelo = ModeloPrecio(self.semilla).entrenar(ventas)
            self.recalibraciones += 1
            self._registrar(None, "recalibracion", {"ventas_usadas": len(ventas),
                                                    "ventas_nuevas": len(self.ventas_aprendidas)})
        return {"error_pct": error, "dentro_del_rango": dentro}

    # ------------------------------------------------------------------ ciclo completo
    def valorar(self, propiedad: dict):
        """Percepción -> decisión -> acción para UNA propiedad. Devuelve la decisión (None si es inválida)."""
        id_propiedad = propiedad.get("id")
        self._registrar(id_propiedad, "percepcion", {k: propiedad.get(k) for k in CARACTERISTICAS})

        errores = self.validar(propiedad)
        if errores:
            self._registrar(id_propiedad, "percepcion_invalida", {"errores": errores})
            return None

        decision = self.decidir(propiedad)
        self._registrar(id_propiedad, "decision", {k: (round(v, 2) if isinstance(v, float) else v)
                                                   for k, v in decision.items() if k != "rango"}
                        | {"rango": [round(decision["rango"][0], 2), round(decision["rango"][1], 2)]})
        self.actuar(id_propiedad, decision)
        self._registrar(id_propiedad, "accion", {"publicado": round(decision["precio"], 2)})
        return decision

    def ejecutar(self, max_propiedades: int = None) -> pd.DataFrame:
        """Atiende todas las propiedades que lleguen y devuelve una tabla con los resultados."""
        atendidas = 0
        while max_propiedades is None or atendidas < max_propiedades:
            propiedad = self.percibir()
            if propiedad is None:
                break
            atendidas += 1
            decision = self.valorar(propiedad)
            if decision is None:
                continue
            precio_real = self.entorno.revelar_precio_final(propiedad["id"])
            resultado = self.aprender(propiedad, decision, precio_real)
            self.resultados.append({
                "id": propiedad["id"], "estimado": decision["precio"], "real": precio_real,
                "rango_min": decision["rango"][0], "rango_max": decision["rango"][1],
                "error_pct": resultado["error_pct"], "dentro_del_rango": resultado["dentro_del_rango"],
                "incertidumbre": decision["incertidumbre"], "n_comparables": decision["n_comparables"],
            })
        return pd.DataFrame(self.resultados)


def resumen(tabla: pd.DataFrame) -> dict:
    """Las dos medidas de desempeño del diseño."""
    return {"propiedades": len(tabla),
            "MAPE_%": float(tabla["error_pct"].mean()),
            "cobertura_%": float(tabla["dentro_del_rango"].mean() * 100)}


if __name__ == "__main__":
    from simulador import Entorno

    entorno = Entorno(semilla=0)
    agente = AgenteValuIA(entorno, semilla=0, ruta_log="logs/ejecucion_demo.csv")
    tabla = agente.ejecutar()

    r = resumen(tabla)
    print(f"Propiedades valoradas: {r['propiedades']}")
    print(f"MAPE: {r['MAPE_%']:.2f} %   (meta: menor al 10 %)")
    print(f"Cobertura del rango: {r['cobertura_%']:.1f} %   (meta: al menos 80 %)")
    print(f"Recalibraciones del modelo: {agente.recalibraciones}")
    print("\nTres valoraciones de ejemplo:")
    print(tabla.head(3).round(1).to_string())

    # Caso de falla esperada: una propiedad con datos inválidos
    mala = {nombre: 3 for nombre in CARACTERISTICAS} | {"barrio": "OldTown", "area_m2": -50, "id": 99999}
    del mala["lote_m2"]
    print("\nPropiedad inválida (área negativa y sin lote):")
    print("  decisión del agente ->", agente.valorar(mala))
    print("\nLog guardado en logs/ejecucion_demo.csv")