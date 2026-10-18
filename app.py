"""
app.py - Versión web de VALUIA-AGENT (Streamlit).

Para probarla en tu computador:   python -m streamlit run app.py
Es la misma lógica de main.py (menú por terminal), pero en una página web:
  - Pestaña 1: describir una propiedad y recibir precio de referencia y rango.
  - Pestaña 2: ejecutar la simulación completa y ver las medidas de desempeño.
  - Pestaña 3: ver los resultados de las pruebas de la Fase 3.
"""
import os

import pandas as pd
import streamlit as st

# Asegura que los archivos (data/, logs/) se encuentren sin importar desde dónde se lance la app
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from agente import AgenteValuIA, resumen  # noqa: E402
from datos import CARACTERISTICAS  # noqa: E402
from simulador import Entorno  # noqa: E402

st.set_page_config(page_title="ValuIA-Agent", page_icon="🏠", layout="wide")

# (clave, etiqueta, tipo, valor típico)
CAMPOS = [
    ("area_m2", "Área construida (m²)", "decimal", 140.0),
    ("habitaciones", "Número de habitaciones", "entero", 3),
    ("barrio", "Barrio", "texto", "NAmes"),
    ("antiguedad", "Antigüedad (años)", "entero", 30),
    ("calidad", "Calidad de acabados (1 a 10)", "entero", 6),
    ("sotano_m2", "Área del sótano (m²)", "decimal", 90.0),
    ("garaje_autos", "Plazas de garaje", "entero", 2),
    ("banos", "Baños completos", "entero", 2),
    ("medios_banos", "Medios baños", "entero", 0),
    ("lote_m2", "Área del lote (m²)", "decimal", 900.0),
    ("condicion", "Condición general (1 a 10)", "entero", 5),
    ("primer_piso_m2", "Área del primer piso (m²)", "decimal", 90.0),
    ("anios_remodelacion", "Años desde la última remodelación", "entero", 20),
    ("chimeneas", "Número de chimeneas", "entero", 1),
]


@st.cache_resource(show_spinner="Cargando el agente (entrenando el modelo)...")
def cargar_agente():
    """Un agente listo para valorar propiedades sueltas. Se crea una sola vez y se reutiliza."""
    entorno = Entorno(semilla=0)
    agente = AgenteValuIA(entorno, semilla=0)          # sin log en archivo
    barrios = sorted(entorno.historial["barrio"].unique())
    return agente, barrios


# ---------------------------------------------------------------- barra lateral
with st.sidebar:
    st.header("ValuIA-Agent")
    st.write(
        "Agente inteligente que sugiere un precio de referencia y un rango razonable para una "
        "propiedad, a partir de sus características y de ventas comparables recientes."
    )
    st.write("Ciclo del agente: percibir, validar, decidir, actuar y aprender.")
    st.caption(
        "Datos: Ames Housing (Iowa, 2006-2010). Las ventas reales se simulan como un sistema de "
        "listados. La decisión final del precio siempre es del agente inmobiliario."
    )
    st.caption("Proyecto de Inteligencia Artificial, Universidad Tecnológica de Bolívar.")
    st.caption("Código: https://github.com/Salvadorr01/ValuIA-Agent")

st.title("🏠 ValuIA-Agent")
tab1, tab2, tab3 = st.tabs(["Valorar una propiedad", "Simulación completa", "Pruebas de la Fase 3"])

# ---------------------------------------------------------------- pestaña 1
with tab1:
    st.subheader("Describe la propiedad")
    agente, barrios = cargar_agente()
    st.caption("Barrios conocidos: " + ", ".join(barrios))
    st.caption(
        "Prueba también un caso de falla: escribe un área negativa o un texto en un barrio que no "
        "existe, y mira cómo reacciona el agente."
    )

    with st.form("formulario_propiedad"):
        columnas = st.columns(3)
        valores = {}
        for i, (clave, etiqueta, tipo, defecto) in enumerate(CAMPOS):
            with columnas[i % 3]:
                if tipo == "texto":
                    valores[clave] = st.text_input(etiqueta, value=defecto, key=f"campo_{clave}")
                elif tipo == "entero":
                    valores[clave] = st.number_input(etiqueta, value=defecto, step=1, key=f"campo_{clave}")
                else:
                    valores[clave] = st.number_input(etiqueta, value=defecto, step=1.0, key=f"campo_{clave}")
        enviado = st.form_submit_button("Valorar propiedad", type="primary")

    if enviado:
        contador = st.session_state.get("contador", 0) + 1
        st.session_state["contador"] = contador
        propiedad = {clave: valores[clave] for clave in CARACTERISTICAS}
        propiedad["barrio"] = str(propiedad["barrio"]).strip()
        propiedad["id"] = 900000 + contador

        decision = agente.valorar(propiedad)
        if decision is None:
            st.error("El agente no valoró la propiedad porque los datos no son válidos:")
            for error in agente.validar(propiedad):
                st.write("- " + error)
        else:
            c1, c2, c3 = st.columns(3)
            c1.metric("Precio de referencia", f"USD {decision['precio']:,.0f}")
            c2.metric("Rango mínimo", f"USD {decision['rango'][0]:,.0f}")
            c3.metric("Rango máximo", f"USD {decision['rango'][1]:,.0f}")
            if decision["incertidumbre"] == "alta":
                st.warning(
                    f"Incertidumbre alta: solo hay {decision['n_comparables']} ventas comparables "
                    "recientes en ese barrio, por eso el rango es más ancho."
                )
            else:
                st.success(f"Incertidumbre normal, con {decision['n_comparables']} comparables recientes.")
            st.write(
                f"Estimación del modelo: USD {decision['precio_modelo']:,.0f}. "
                f"Ajuste de mercado: x{decision['factor_mercado']:.3f}."
            )
            st.caption("Es una sugerencia: la decisión final del precio de listado es del agente inmobiliario.")

# ---------------------------------------------------------------- pestaña 2
with tab2:
    st.subheader("Ejecutar la simulación completa")
    st.write(
        "El agente valora 200 propiedades nuevas (que nunca vio) una por una, recibe el precio real "
        "de cada una y se recalibra cada 50 ventas. Al final se calculan las dos medidas de desempeño."
    )
    semilla = st.number_input("Semilla del simulador", min_value=0, max_value=1000, value=0, step=1)
    if st.button("Ejecutar simulación", type="primary"):
        with st.spinner("Ejecutando... (puede tardar entre 10 y 60 segundos)"):
            entorno = Entorno(semilla=int(semilla))
            agente_sim = AgenteValuIA(entorno, semilla=int(semilla))
            tabla = agente_sim.ejecutar()
        st.session_state["simulacion"] = {
            "semilla": int(semilla), "tabla": tabla, "r": resumen(tabla),
            "recalibraciones": agente_sim.recalibraciones,
        }

    sim = st.session_state.get("simulacion")
    if sim:
        r, tabla = sim["r"], sim["tabla"]
        st.write(f"Resultados con la semilla {sim['semilla']}:")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Propiedades valoradas", r["propiedades"])
        c2.metric("MAPE", f"{r['MAPE_%']:.2f} %")
        c2.caption("Meta: menor al 10 % → " + ("cumple" if r["MAPE_%"] < 10 else "no cumple"))
        c3.metric("Cobertura del rango", f"{r['cobertura_%']:.1f} %")
        c3.caption("Meta: al menos 80 % → " + ("cumple" if r["cobertura_%"] >= 80 else "no cumple"))
        c4.metric("Recalibraciones", sim["recalibraciones"])

        st.write("Precio real frente a precio estimado (cada punto es una propiedad):")
        st.scatter_chart(tabla[["real", "estimado"]], x="real", y="estimado")
        st.write("Primeras 20 valoraciones:")
        st.dataframe(tabla.head(20).round(2), width="stretch")
        st.download_button("Descargar todos los resultados (CSV)", tabla.to_csv(index=False).encode("utf-8"),
                           file_name=f"simulacion_semilla{sim['semilla']}.csv", mime="text/csv")

# ---------------------------------------------------------------- pestaña 3
with tab3:
    st.subheader("Pruebas de la Fase 3")
    st.write(
        "Criterios fijados antes de ejecutar: MAPE menor al 10 % y cobertura del rango de al menos "
        "80 %. Cada escenario se ejecutó 5 veces (semillas 0 a 4) y cumple si la media cumple el umbral."
    )
    ruta = "logs/pruebas/resumen_escenarios.csv"
    if os.path.exists(ruta):
        r = pd.read_csv(ruta)
        vista = r[["escenario", "tipo", "nombre", "MAPE_media", "MAPE_desv", "cumple_MAPE",
                   "cobertura_media", "cobertura_desv", "cumple_cobertura",
                   "incertidumbre_alta_%", "rechazo_invalidas_%"]].round(2)
        st.dataframe(vista, width="stretch", hide_index=True)
        st.caption("Los archivos completos de evidencia están en la carpeta logs/pruebas del repositorio.")
    else:
        st.info("Aún no hay resultados de pruebas. Ejecuta `python pruebas.py` para generarlos.")