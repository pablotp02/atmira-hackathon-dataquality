"""
Dashboard de calidad del dato — Hackathon Atmira
Reto 03: Mejora de la calidad del dato y reduccion de incidencias en produccion

Uso:
  streamlit run dashboard/app.py
"""

import os
import sys
import json
import subprocess
import pandas as pd
import streamlit as st

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Rutas ─────────────────────────────────────────────────────────────────────

BASE_DIR      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIRTY_DIR     = os.path.join(BASE_DIR, "data", "dirty")
PROFILING_DIR = os.path.join(BASE_DIR, "data", "profiling")
RESULTS_PATH  = os.path.join(BASE_DIR, "data", "results.json")

# ── Configuracion de pagina ───────────────────────────────────────────────────

st.set_page_config(
    page_title="Data Quality Dashboard",
    page_icon="🔍",
    layout="wide",
)

# ── Carga de datos ────────────────────────────────────────────────────────────

@st.cache_data
def cargar_summary():
    path = os.path.join(PROFILING_DIR, "summary.json")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def cargar_injection_log():
    path = os.path.join(DIRTY_DIR, "injection_log.json")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def cargar_results():
    if not os.path.exists(RESULTS_PATH):
        return None
    with open(RESULTS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("Data Quality")
    st.caption("Hackathon Atmira — Reto 03")
    st.divider()

    pagina = st.radio(
        "Navegacion",
        options=[
            "Resumen",
            "Profiling del dataset",
            "Anomalias inyectadas",
            "Reglas generadas",
            "Resultados y metricas",
        ],
        label_visibility="collapsed",
    )

    st.divider()

    st.markdown("**Ejecutar pipeline**")
    st.caption("Regenera el dataset, inyecta anomalias y ejecuta la validacion completa.")

    if st.button("Ejecutar pipeline completo", use_container_width=True, type="primary"):
        with st.spinner("Ejecutando pipeline..."):
            try:
                result = subprocess.run(
                    [sys.executable, os.path.join(BASE_DIR, "run_all.py")],
                    capture_output=True,
                    text=True,
                    cwd=BASE_DIR,
                )
                if result.returncode == 0:
                    st.success("Pipeline ejecutado correctamente.")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Error al ejecutar el pipeline.")
                    st.code(result.stderr)
            except Exception as e:
                st.error(f"Error: {e}")


# ── Paginas ───────────────────────────────────────────────────────────────────

def pagina_resumen():
    st.title("Resumen del proyecto")
    st.markdown(
        "Pipeline de deteccion de anomalias en datos de e-commerce usando IA generativa. "
        "El sistema genera reglas de calidad automaticamente a partir del perfil estadistico "
        "del dataset y las aplica para detectar errores antes de que lleguen a produccion."
    )

    summary      = cargar_summary()
    log          = cargar_injection_log()
    results      = cargar_results()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        filas = sum(t["filas"] for t in summary["tablas"].values()) if summary else 0
        st.metric("Registros analizados", f"{filas:,}")

    with col2:
        total = log["total_anomalias"] if log else 0
        st.metric("Anomalias inyectadas", total)

    with col3:
        reglas = len(results["rules"]) if results else 0
        st.metric("Reglas generadas", reglas)

    with col4:
        tasa = results["metricas"]["tasa_deteccion_tipos"] if results else 0
        st.metric("Tasa de deteccion", f"{tasa}%")


def pagina_profiling():
    # --- TU COMPAÑERO DESARROLLA ESTA PAGINA ---
    st.title("Profiling del dataset")
    summary = cargar_summary()

    if summary is None:
        st.warning("No se encontro summary.json. Ejecuta el pipeline primero.")
        return

    # Aqui va el contenido de tu compañero


def pagina_anomalias():
    # --- TU COMPAÑERO DESARROLLA ESTA PAGINA ---
    st.title("Anomalias inyectadas")
    log = cargar_injection_log()

    if log is None:
        st.warning("No se encontro injection_log.json. Ejecuta el pipeline primero.")
        return

    # Aqui va el contenido de tu compañero


def pagina_reglas():
    # --- TU PAGINA ---
    st.title("Reglas generadas por el LLM")
    results = cargar_results()

    if results is None:
        st.warning("No se encontraron resultados. Ejecuta el pipeline primero.")
        return

    # Aqui va tu contenido


def pagina_resultados():
    # --- TU PAGINA ---
    st.title("Resultados y metricas")
    results = cargar_results()

    if results is None:
        st.warning("No se encontraron resultados. Ejecuta el pipeline primero.")
        return

    # Aqui va tu contenido


# ── Router ────────────────────────────────────────────────────────────────────

if pagina == "Resumen":
    pagina_resumen()
elif pagina == "Profiling del dataset":
    pagina_profiling()
elif pagina == "Anomalias inyectadas":
    pagina_anomalias()
elif pagina == "Reglas generadas":
    pagina_reglas()
elif pagina == "Resultados y metricas":
    pagina_resultados()