"""
simulador.py - Entorno simulado de VALUIA-AGENT.

No tenemos una inmobiliaria real ni su sistema de listados, así que este archivo
los simula usando las ventas reales de Ames Housing. El entorno hace cuatro cosas:

  1. Guarda el HISTORIAL (ventas de 2006 a 2008): es la memoria con la que se
     entrena el modelo.
  2. Entrega propiedades NUEVAS para valorar, una por una. Son 200 casas de
     2009-2010 que el modelo nunca vio, y su precio real queda oculto.
  3. Responde consultas de COMPARABLES: ventas recientes (2009-2010) del mismo barrio.
  4. Revela el PRECIO FINAL de venta, pero solo cuando el agente ya publicó su
     sugerencia (así el agente no puede hacer trampa).

La aleatoriedad (el ambiente es estocástico) está en qué 200 casas llegan, en
qué orden llegan y en qué comparables aparecen. Se controla con una semilla:
la misma semilla da siempre el mismo entorno.
"""
import random

from datos import cargar_datos, CARACTERISTICAS

ANIO_CORTE = 2008          # hasta este año es historial; después es mercado reciente


class Entorno:
    def __init__(self, semilla: int = 0, n_prueba: int = 200):
        self.semilla = semilla
        self.azar = random.Random(semilla)

        datos = cargar_datos()
        self.historial = datos[datos["anio_venta"] <= ANIO_CORTE]
        mercado = datos[datos["anio_venta"] > ANIO_CORTE]

        # Se mezclan las casas del mercado reciente (con la semilla) y se separan:
        # las primeras n_prueba son las propiedades nuevas; el resto son ventas
        # recientes que el agente puede consultar como comparables.
        ids = list(mercado.index)
        self.azar.shuffle(ids)
        self._prueba = mercado.loc[ids[:n_prueba]]
        self.ventas_recientes = mercado.loc[ids[n_prueba:]]

        self._cola = list(self._prueba.index)   # propiedades que aún no han llegado
        self.sugerencias = {}                   # lo que el agente publicó (el "sistema de listados")

    # ---------------------------------------------------------------- percepción
    def siguiente_propiedad(self):
        """Entrega la siguiente propiedad nueva (sin precio) o None si ya no hay más."""
        if not self._cola:
            return None
        id_propiedad = self._cola.pop(0)
        percepcion = self._prueba.loc[id_propiedad, CARACTERISTICAS].to_dict()
        percepcion["id"] = int(id_propiedad)
        return percepcion

    @property
    def pendientes(self) -> int:
        return len(self._cola)

    def consultar_comparables(self, barrio: str, k: int = 10):
        """Ventas recientes del mismo barrio (máximo k, elegidas al azar).
        Si el barrio tiene pocas ventas recientes, devuelve menos (o ninguna)."""
        similares = self.ventas_recientes[self.ventas_recientes["barrio"] == barrio]
        if len(similares) > k:
            similares = similares.sample(k, random_state=self.azar.randint(0, 10**6))
        return similares.copy()

    # ---------------------------------------------------------------- acción
    def publicar_sugerencia(self, id_propiedad: int, precio: float, rango: tuple):
        """El agente publica su precio de referencia y su rango en el 'sistema de listados'."""
        self.sugerencias[id_propiedad] = {"precio": precio, "rango": rango}

    # ---------------------------------------------------------------- retroalimentación
    def revelar_precio_final(self, id_propiedad: int) -> float:
        """Precio real de cierre. Solo se revela si el agente ya publicó su sugerencia."""
        if id_propiedad not in self.sugerencias:
            raise ValueError("El precio final solo se conoce después de publicar la sugerencia.")
        return float(self._prueba.loc[id_propiedad, "precio"])


if __name__ == "__main__":
    # Demostración: python simulador.py
    e = Entorno(semilla=0)
    print("Casas en el historial (2006-2008):", len(e.historial))
    print("Ventas recientes disponibles como comparables:", len(e.ventas_recientes))
    print("Propiedades nuevas por valorar:", e.pendientes)

    p = e.siguiente_propiedad()
    print("\nPrimera propiedad que llega (sin precio):")
    for clave, valor in p.items():
        print(f"  {clave:20s} {valor if not isinstance(valor, float) else round(valor, 1)}")

    comp = e.consultar_comparables(p["barrio"], k=5)
    print(f"\nComparables recientes en el barrio {p['barrio']}: {len(comp)}")
    print(comp[["area_m2", "calidad", "anio_venta", "precio"]].round(1).to_string())

    try:
        e.revelar_precio_final(p["id"])
    except ValueError as error:
        print("\nIntento de ver el precio antes de publicar ->", error)
    e.publicar_sugerencia(p["id"], 150000.0, (130000.0, 170000.0))
    print("Precio final real tras publicar:", e.revelar_precio_final(p["id"]))

    print("\nProbando la semilla (primer id que llega):")
    print("  semilla 0:", Entorno(0).siguiente_propiedad()["id"], "| otra vez semilla 0:", Entorno(0).siguiente_propiedad()["id"])
    print("  semilla 1:", Entorno(1).siguiente_propiedad()["id"], "| semilla 2:", Entorno(2).siguiente_propiedad()["id"])