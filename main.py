"""
main.py - Interfaz por terminal de VALUIA-AGENT.

Uso:
    python main.py                      abre el menú
    python main.py --simulacion 3       ejecuta directamente la simulación con la semilla 3

Desde el menú se puede:
    1) Ejecutar la simulación completa (200 propiedades nuevas) y ver las dos medidas de desempeño.
    2) Valorar una propiedad que el usuario describe (el agente da precio de referencia y rango).
"""
import argparse

from agente import AgenteValuIA, resumen
from datos import CARACTERISTICAS
from simulador import Entorno

# Nombre en español, y valor típico que se usa si el usuario solo pulsa Enter
CAMPOS = {
    "area_m2": ("Área construida (m²)", 140),
    "habitaciones": ("Número de habitaciones", 3),
    "barrio": ("Barrio", "NAmes"),
    "antiguedad": ("Antigüedad (años)", 30),
    "calidad": ("Calidad de acabados (1 a 10)", 6),
    "sotano_m2": ("Área del sótano (m²)", 90),
    "garaje_autos": ("Plazas de garaje", 2),
    "banos": ("Baños completos", 2),
    "medios_banos": ("Medios baños", 0),
    "lote_m2": ("Área del lote (m²)", 900),
    "condicion": ("Condición general (1 a 10)", 5),
    "primer_piso_m2": ("Área del primer piso (m²)", 90),
    "anios_remodelacion": ("Años desde la última remodelación", 20),
    "chimeneas": ("Número de chimeneas", 1),
}


def simulacion(semilla: int):
    """Crea el entorno simulado, deja trabajar al agente y muestra las medidas de desempeño."""
    ruta_log = f"logs/ejecucion_semilla{semilla}.csv"
    print(f"\nEjecutando la simulación con la semilla {semilla}... (puede tardar unos segundos)")
    entorno = Entorno(semilla=semilla)
    agente = AgenteValuIA(entorno, semilla=semilla, ruta_log=ruta_log)
    tabla = agente.ejecutar()
    r = resumen(tabla)
    print(f"\nPropiedades valoradas: {r['propiedades']}")
    print(f"MAPE: {r['MAPE_%']:.2f} %   (meta: menor al 10 %)")
    print(f"Cobertura del rango: {r['cobertura_%']:.1f} %   (meta: al menos 80 %)")
    print(f"Recalibraciones del modelo: {agente.recalibraciones}")
    print(f"Log guardado en {ruta_log}")


def leer_valor(clave: str, etiqueta: str, defecto):
    """Pregunta un dato. Enter = valor típico. Si escriben letras donde va un número, se deja tal cual
    para que el agente lo rechace como dato inválido."""
    texto = input(f"  {etiqueta} [{defecto}]: ").strip()
    if texto == "":
        return defecto
    if clave == "barrio":
        return texto
    try:
        numero = float(texto.replace(",", "."))
        return int(numero) if numero.is_integer() else numero
    except ValueError:
        return texto


def valorar_manual():
    """El usuario describe una propiedad y el agente la valora."""
    print("\nCargando el agente...")
    entorno = Entorno(semilla=0)
    agente = AgenteValuIA(entorno, semilla=0, ruta_log="logs/ejecucion_manual.csv")
    barrios = sorted(entorno.historial["barrio"].unique())
    print("Barrios conocidos:", ", ".join(barrios))

    contador = 0
    while True:
        contador += 1
        print("\nDescribe la propiedad (Enter usa el valor típico que aparece entre corchetes):")
        propiedad = {clave: leer_valor(clave, *CAMPOS[clave]) for clave in CARACTERISTICAS}
        propiedad["id"] = 900000 + contador

        decision = agente.valorar(propiedad)
        if decision is None:
            print("\nEl agente no valoró la propiedad porque los datos no son válidos:")
            for error in agente.validar(propiedad):
                print("  -", error)
        else:
            print("\n--- Valoración ---")
            print(f"Precio de referencia: USD {decision['precio']:,.0f}")
            print(f"Rango razonable:      USD {decision['rango'][0]:,.0f} a USD {decision['rango'][1]:,.0f}")
            print(f"Estimación del modelo: USD {decision['precio_modelo']:,.0f}  (ajuste de mercado x{decision['factor_mercado']:.3f})")
            print(f"Comparables usados: {decision['n_comparables']}   Incertidumbre: {decision['incertidumbre']}")
            print("La decisión final del precio de listado es del agente inmobiliario.")
        if input("\n¿Valorar otra propiedad? (s/n): ").strip().lower() != "s":
            break
    print("Log guardado en logs/ejecucion_manual.csv")


def menu():
    while True:
        print("\n=== VALUIA-AGENT ===")
        print("1) Ejecutar la simulación completa")
        print("2) Valorar una propiedad que yo describa")
        print("3) Salir")
        try:
            opcion = input("Elige una opción: ").strip()
        except EOFError:
            break
        if opcion == "1":
            texto = input("Semilla del simulador (Enter = 0): ").strip()
            simulacion(int(texto) if texto.isdigit() else 0)
        elif opcion == "2":
            valorar_manual()
        elif opcion == "3":
            break
        else:
            print("Opción no válida.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Interfaz de VALUIA-AGENT")
    parser.add_argument("--simulacion", type=int, metavar="SEMILLA",
                        help="ejecuta directamente la simulación con esta semilla")
    args = parser.parse_args()
    if args.simulacion is not None:
        simulacion(args.simulacion)
    else:
        menu()