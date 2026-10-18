"""
pruebas.py - Fase 3: pruebas de VALUIA-AGENT contra sus medidas de desempeño.

CRITERIOS FIJADOS ANTES DE EJECUTAR (no se modifican después de ver resultados):
    MAPE  = media de |precio real - precio estimado| / precio real x 100   -> cumple si es MENOR al 10 %
    Cobertura = % de propiedades cuyo precio real cae dentro del rango      -> cumple si es al menos 80 %
    Cada escenario se ejecuta 5 veces (semillas 0, 1, 2, 3 y 4). Un escenario cumple una
    medida si la MEDIA de las 5 ejecuciones cumple el umbral.

Uso:
    python pruebas.py                                  ejecuta los 12 escenarios x 5 semillas
    python pruebas.py --escenarios 1 10 --semillas 0   solo algunos (para probar rápido)
    python pruebas.py --salida logs/prueba_rapida      cambia la carpeta de resultados

Genera en la carpeta de salida (por defecto logs/pruebas):
    resultados_por_ejecucion.csv   una fila por escenario y semilla
    resumen_escenarios.csv         media, desviación y veredicto por escenario
    detalle_propiedades.csv        una fila por propiedad valorada
    resumen.json / resumen.txt     lo mismo, en otros formatos
    eventos_escenarioN_semilla0.csv   log de eventos del agente (escenarios 9 y 10)
"""
import argparse
import json
import os
import random
import time

import numpy as np
import pandas as pd

from agente import AgenteValuIA, resumen
from simulador import Entorno

SEMILLAS = [0, 1, 2, 3, 4]
UMBRAL_MAPE = 10.0          # cumple si es menor
UMBRAL_COBERTURA = 80.0     # cumple si es mayor o igual


# ====================================================================== escenarios
# Cada función recibe el entorno (ya creado, con una semilla) y lo modifica para
# reproducir la situación del escenario. Devuelve las opciones con que se crea el agente.
# "ctx" es un diccionario donde se anotan datos que se necesitan al final (p. ej. qué
# propiedades se corrompieron).

def _quedarse_con(entorno, ids):
    """Deja como propiedades nuevas solo las indicadas (respetando el orden de llegada)."""
    ids = set(ids)
    entorno._prueba = entorno._prueba.loc[[i for i in entorno._prueba.index if i in ids]]
    entorno._cola = [i for i in entorno._cola if i in ids]


def esc_estandar(entorno, semilla, ctx):
    return {}


def esc_sin_recalibracion(entorno, semilla, ctx):
    return {"recalibrar_cada": 10 ** 9}           # nunca llega a recalibrar


def esc_recalibracion_frecuente(entorno, semilla, ctx):
    return {"recalibrar_cada": 20}


def esc_baratas(entorno, semilla, ctx):
    _quedarse_con(entorno, entorno._prueba["precio"].nsmallest(20).index)   # 10 % de 200
    return {}


def esc_caras(entorno, semilla, ctx):
    _quedarse_con(entorno, entorno._prueba["precio"].nlargest(20).index)
    return {}


def esc_historial_reducido(entorno, semilla, ctx):
    entorno.historial = entorno.historial.sample(frac=0.2, random_state=semilla)
    return {}


def esc_pocos_comparables(entorno, semilla, ctx):
    entorno.ventas_recientes = entorno.ventas_recientes.sample(frac=0.1, random_state=semilla)
    return {}


def esc_barrio_desconocido(entorno, semilla, ctx):
    original = entorno.siguiente_propiedad

    def siguiente():
        p = original()
        if p is not None:
            p["barrio"] = "BarrioNuevo"           # un barrio que no existe en ningún dato
        return p

    entorno.siguiente_propiedad = siguiente
    return {}


def esc_datos_invalidos(entorno, semilla, ctx):
    azar = random.Random(1000 + semilla)
    total = entorno.pendientes
    corruptas = set(azar.sample(range(total), total // 5))      # exactamente el 20 %
    tipos = ["area_texto", "area_negativa", "sin_lote", "calidad_nan", "calidad_fuera_de_rango"]
    ctx["invalidas"] = []
    original = entorno.siguiente_propiedad
    contador = {"i": 0}

    def siguiente():
        p = original()
        if p is None:
            return None
        posicion = contador["i"]
        contador["i"] += 1
        if posicion in corruptas:
            tipo = tipos[len(ctx["invalidas"]) % len(tipos)]
            if tipo == "area_texto":
                p["area_m2"] = "abc"
            elif tipo == "area_negativa":
                p["area_m2"] = -50
            elif tipo == "sin_lote":
                del p["lote_m2"]
            elif tipo == "calidad_nan":
                p["calidad"] = float("nan")
            else:
                p["calidad"] = 99
            ctx["invalidas"].append(p["id"])
        return p

    entorno.siguiente_propiedad = siguiente
    return {}


def _choque_de_mercado(factor):
    def preparar(entorno, semilla, ctx):
        entorno._prueba = entorno._prueba.copy()
        entorno._prueba["precio"] = entorno._prueba["precio"] * factor
        entorno.ventas_recientes = entorno.ventas_recientes.copy()
        entorno.ventas_recientes["precio"] = entorno.ventas_recientes["precio"] * factor
        return {}
    return preparar


ESCENARIOS = [
    {"id": 1, "tipo": "Normal", "nombre": "Configuración estándar", "preparar": esc_estandar,
     "esperado": "Cumple ambas medidas"},
    {"id": 2, "tipo": "Normal", "nombre": "Sin recalibración", "preparar": esc_sin_recalibracion,
     "esperado": "Cumple, quizá un poco peor que el 1"},
    {"id": 3, "tipo": "Normal", "nombre": "Recalibración cada 20 ventas", "preparar": esc_recalibracion_frecuente,
     "esperado": "Cumple, similar al 1"},
    {"id": 4, "tipo": "Normal", "nombre": "Pocas propiedades (50)", "preparar": esc_estandar, "n_prueba": 50,
     "esperado": "Cumple, con más variación entre semillas"},
    {"id": 5, "tipo": "Límite", "nombre": "Solo propiedades baratas (10 % inferior)", "preparar": esc_baratas,
     "esperado": "Caso dudoso para el MAPE"},
    {"id": 6, "tipo": "Límite", "nombre": "Solo propiedades caras (10 % superior)", "preparar": esc_caras,
     "esperado": "Caso dudoso para el MAPE"},
    {"id": 7, "tipo": "Límite", "nombre": "Historial reducido (20 %)", "preparar": esc_historial_reducido,
     "esperado": "MAPE más alto, tal vez cerca del 10 %"},
    {"id": 8, "tipo": "Límite", "nombre": "Pocos comparables (10 % de las ventas recientes)",
     "preparar": esc_pocos_comparables, "esperado": "Más casos con incertidumbre alta y rangos más anchos"},
    {"id": 9, "tipo": "Falla esperada", "nombre": "Barrio desconocido (sin comparables)",
     "preparar": esc_barrio_desconocido,
     "esperado": "Marca incertidumbre alta en el 100 % de los casos y no se cae"},
    {"id": 10, "tipo": "Falla esperada", "nombre": "20 % de propiedades con datos inválidos",
     "preparar": esc_datos_invalidos, "esperado": "Rechaza el 100 % de las inválidas y no publica nada de ellas"},
    {"id": 11, "tipo": "Falla esperada", "nombre": "Choque de mercado: precios +30 %",
     "preparar": _choque_de_mercado(1.3), "esperado": "MAPE y cobertura por debajo del umbral"},
    {"id": 12, "tipo": "Falla esperada", "nombre": "Choque de mercado: precios -30 %",
     "preparar": _choque_de_mercado(0.7), "esperado": "MAPE y cobertura por debajo del umbral"},
]


# ====================================================================== ejecución
def ejecutar_una(esc, semilla, carpeta):
    """Una ejecución: crea el entorno, aplica el escenario, corre el agente y mide."""
    inicio = time.perf_counter()
    entorno = Entorno(semilla=semilla, n_prueba=esc.get("n_prueba", 200))
    ctx = {}
    opciones = esc["preparar"](entorno, semilla, ctx)
    recibidas = entorno.pendientes

    ruta_log = None
    if esc["id"] in (9, 10) and semilla == 0:
        ruta_log = os.path.join(carpeta, f"eventos_escenario{esc['id']}_semilla0.csv")
        if os.path.exists(ruta_log):
            os.remove(ruta_log)

    agente = AgenteValuIA(entorno, semilla=semilla, ruta_log=ruta_log, **opciones)
    tabla = agente.ejecutar()
    r = resumen(tabla)

    invalidas = ctx.get("invalidas", [])
    if invalidas:
        publicadas_invalidas = len(set(invalidas) & set(entorno.sugerencias))
        rechazo = 100.0 * (len(invalidas) - publicadas_invalidas) / len(invalidas)
    else:
        rechazo = np.nan

    fila = {
        "escenario": esc["id"], "semilla": semilla, "recibidas": recibidas, "valoradas": r["propiedades"],
        "invalidas_enviadas": len(invalidas), "rechazo_invalidas_%": rechazo,
        "MAPE_%": r["MAPE_%"], "cobertura_%": r["cobertura_%"],
        "incertidumbre_alta_%": 100.0 * float((tabla["incertidumbre"] == "alta").mean()),
        "ancho_rango_medio_%": 100.0 * float(((tabla["rango_max"] - tabla["rango_min"]) / tabla["estimado"]).mean()),
        "recalibraciones": agente.recalibraciones,
        "segundos": time.perf_counter() - inicio,
    }
    detalle = tabla.copy()
    detalle.insert(0, "semilla", semilla)
    detalle.insert(0, "escenario", esc["id"])
    return fila, detalle


def resumir(por_ejecucion, escenarios):
    filas = []
    for esc in escenarios:
        d = por_ejecucion[por_ejecucion["escenario"] == esc["id"]]
        mape, cob = d["MAPE_%"], d["cobertura_%"]
        filas.append({
            "escenario": esc["id"], "tipo": esc["tipo"], "nombre": esc["nombre"], "esperado": esc["esperado"],
            "ejecuciones": len(d),
            "MAPE_media": mape.mean(), "MAPE_desv": mape.std(ddof=1) if len(d) > 1 else np.nan,
            "MAPE_ejec_cumplen": int((mape < UMBRAL_MAPE).sum()),
            "cumple_MAPE": bool(mape.mean() < UMBRAL_MAPE),
            "cobertura_media": cob.mean(), "cobertura_desv": cob.std(ddof=1) if len(d) > 1 else np.nan,
            "cobertura_ejec_cumplen": int((cob >= UMBRAL_COBERTURA).sum()),
            "cumple_cobertura": bool(cob.mean() >= UMBRAL_COBERTURA),
            "incertidumbre_alta_%": d["incertidumbre_alta_%"].mean(),
            "ancho_rango_medio_%": d["ancho_rango_medio_%"].mean(),
            "rechazo_invalidas_%": d["rechazo_invalidas_%"].mean() if d["rechazo_invalidas_%"].notna().any() else np.nan,
            "valoradas_media": d["valoradas"].mean(),
        })
    return pd.DataFrame(filas)


def main():
    parser = argparse.ArgumentParser(description="Pruebas de la Fase 3 de VALUIA-AGENT")
    parser.add_argument("--escenarios", type=int, nargs="+", help="números de escenario (por defecto, todos)")
    parser.add_argument("--semillas", type=int, nargs="+", default=SEMILLAS, help="semillas (por defecto 0 1 2 3 4)")
    parser.add_argument("--salida", default="logs/pruebas", help="carpeta de resultados")
    args = parser.parse_args()

    escenarios = [e for e in ESCENARIOS if args.escenarios is None or e["id"] in args.escenarios]
    os.makedirs(args.salida, exist_ok=True)
    total = len(escenarios) * len(args.semillas)
    print(f"Ejecutando {len(escenarios)} escenarios x {len(args.semillas)} semillas = {total} ejecuciones.")
    print("Puede tardar varios minutos; no cierres la ventana.\n")

    filas, detalles, hecho = [], [], 0
    for esc in escenarios:
        for semilla in args.semillas:
            fila, detalle = ejecutar_una(esc, semilla, args.salida)
            filas.append(fila)
            detalles.append(detalle)
            hecho += 1
            print(f"[{hecho}/{total}] escenario {esc['id']:>2} semilla {semilla}: "
                  f"MAPE {fila['MAPE_%']:.2f} %  cobertura {fila['cobertura_%']:.1f} %  ({fila['segundos']:.0f} s)")

    por_ejecucion = pd.DataFrame(filas)
    resumen_esc = resumir(por_ejecucion, escenarios)
    detalle = pd.concat(detalles, ignore_index=True)

    por_ejecucion.round(4).to_csv(os.path.join(args.salida, "resultados_por_ejecucion.csv"), index=False)
    resumen_esc.round(4).to_csv(os.path.join(args.salida, "resumen_escenarios.csv"), index=False)
    detalle.round(4).to_csv(os.path.join(args.salida, "detalle_propiedades.csv"), index=False)
    with open(os.path.join(args.salida, "resumen.json"), "w", encoding="utf-8") as f:
        json.dump({"criterios": {"MAPE_menor_a_%": UMBRAL_MAPE, "cobertura_minima_%": UMBRAL_COBERTURA,
                                 "semillas": args.semillas},
                   "escenarios": json.loads(resumen_esc.round(4).to_json(orient="records", force_ascii=False))},
                  f, ensure_ascii=False, indent=2)

    tabla_txt = resumen_esc[["escenario", "tipo", "nombre", "MAPE_media", "MAPE_desv", "cumple_MAPE",
                             "cobertura_media", "cobertura_desv", "cumple_cobertura",
                             "incertidumbre_alta_%", "rechazo_invalidas_%"]].round(2).to_string(index=False)
    with open(os.path.join(args.salida, "resumen.txt"), "w", encoding="utf-8") as f:
        f.write(f"Criterios: MAPE < {UMBRAL_MAPE} %, cobertura >= {UMBRAL_COBERTURA} %, semillas {args.semillas}\n\n")
        f.write(tabla_txt + "\n")
    print("\n" + tabla_txt)
    print(f"\nResultados guardados en {args.salida}/")


if __name__ == "__main__":
    main()