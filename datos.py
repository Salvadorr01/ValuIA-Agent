"""
datos.py - Carga y preparación de los datos de Ames Housing para VALUIA-AGENT.

Deja una tabla con las 14 características de entrada del agente, el precio
real de venta y el año de venta (que usaremos para simular el mercado).
"""
import pandas as pd

RUTA_CSV = "data/AmesHousing.csv"
PIES2_A_M2 = 0.092903          # 1 pie cuadrado = 0,092903 m²

# Las 14 características de entrada del agente (sección 5 del documento)
CARACTERISTICAS = [
    "area_m2", "habitaciones", "barrio", "antiguedad", "calidad",           # las 5 del diseño original
    "sotano_m2", "garaje_autos", "banos", "medios_banos", "lote_m2",        # ampliación
    "condicion", "primer_piso_m2", "anios_remodelacion", "chimeneas",       # ampliación
]
CATEGORICAS = ["barrio"]       # el resto son numéricas


def cargar_datos(ruta: str = RUTA_CSV) -> pd.DataFrame:
    """Lee el CSV y devuelve una tabla limpia, una fila por casa vendida."""
    crudo = pd.read_csv(ruta)

    datos = pd.DataFrame({
        # --- las 5 características del diseño original ---
        "area_m2": crudo["Gr Liv Area"] * PIES2_A_M2,            # área construida en m²
        "habitaciones": crudo["Bedroom AbvGr"],                   # número de habitaciones
        "barrio": crudo["Neighborhood"],                          # ubicación
        "antiguedad": (crudo["Yr Sold"] - crudo["Year Built"]).clip(lower=0),  # años al vender
        "calidad": crudo["Overall Qual"],                         # calidad de acabados, 1 a 10
        # --- las 9 características agregadas ---
        "sotano_m2": crudo["Total Bsmt SF"].fillna(0) * PIES2_A_M2,   # área del sótano (0 si no hay)
        "garaje_autos": crudo["Garage Cars"].fillna(0),               # plazas de garaje (0 si no hay)
        "banos": crudo["Full Bath"],                                  # baños completos
        "medios_banos": crudo["Half Bath"],                           # medios baños
        "lote_m2": crudo["Lot Area"] * PIES2_A_M2,                    # área del lote en m²
        "condicion": crudo["Overall Cond"],                           # condición general, 1 a 10
        "primer_piso_m2": crudo["1st Flr SF"] * PIES2_A_M2,           # área del primer piso en m²
        "anios_remodelacion": (crudo["Yr Sold"] - crudo["Year Remod/Add"]).clip(lower=0),
        "chimeneas": crudo["Fireplaces"],                             # número de chimeneas
        # --- datos que NO recibe el agente como entrada ---
        "anio_venta": crudo["Yr Sold"],                           # año de la venta
        "precio": crudo["SalePrice"],                             # precio real de venta
    })
    return datos


if __name__ == "__main__":
    # Esto solo se ejecuta si corres:  python datos.py
    d = cargar_datos()
    print("Forma de la tabla (filas, columnas):", d.shape)
    print("Características de entrada:", len(CARACTERISTICAS))
    print("\nPrimeras 3 filas (de lado para que quepan):")
    print(d.head(3).round(1).T.to_string())
    print("\nCasas vendidas por año:")
    print(d["anio_venta"].value_counts().sort_index().to_string())
    print("\nNúmero de barrios distintos:", d["barrio"].nunique())
    print("Valores faltantes en total:", int(d.isna().sum().sum()))