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


def pagina_anomalias():
    st.title("Anomalias inyectadas")
    log = cargar_injection_log()

    if log is None:
        st.warning("No se encontro injection_log.json. Ejecuta el pipeline primero.")
        return

    # Metricas superiores
    col1, col2 = st.columns(2)
    col1.metric("Total anomalias inyectadas", log["total_anomalias"])
    col2.metric("Tipos distintos", len(log["anomalias_por_tipo"]))

    # Grafico de barras por tipo
    st.subheader("Anomalias por tipo")
    df_tipos = pd.DataFrame(
        list(log["anomalias_por_tipo"].items()),
        columns=["tipo", "cantidad"]
    ).set_index("tipo")
    st.bar_chart(df_tipos)

    # Tabla de detalle
    st.subheader("Detalle de anomalias")
    df_detalle = pd.DataFrame(log["detalle"])

    columnas_orden = ["tipo", "tabla", "columna", "fila_id", "valor_original", "valor_nuevo"]
    columnas_presentes = [c for c in columnas_orden if c in df_detalle.columns]
    df_detalle = df_detalle[columnas_presentes]

    # Filtro opcional por tipo, para no perderse entre 40 filas
    tipos_disponibles = ["Todos"] + sorted(df_detalle["tipo"].unique().tolist())
    tipo_seleccionado = st.selectbox("Filtrar por tipo", tipos_disponibles)

    if tipo_seleccionado != "Todos":
        df_detalle = df_detalle[df_detalle["tipo"] == tipo_seleccionado]

    st.dataframe(df_detalle, use_container_width=True, hide_index=True)

def pagina_profiling():
    st.title("Profiling del dataset")
    summary = cargar_summary()

    if summary is None:
        st.warning("No se encontro summary.json. Ejecuta el pipeline primero.")
        return

    tablas = summary["tablas"]
    nombres_tablas = list(tablas.keys())

    tabs = st.tabs(nombres_tablas)

    for tab, nombre_tabla in zip(tabs, nombres_tablas):
        with tab:
            info = tablas[nombre_tabla]

            # Metricas generales
            col1, col2, col3 = st.columns(3)
            col1.metric("Filas", info["filas"])
            col2.metric("Columnas", info["columnas"])
            col3.metric("Filas duplicadas", info["filas_duplicadas"])

            st.subheader("Detalle por columna")

            filas_tabla = []
            for nombre_col, detalle in info["columnas_detalle"].items():
                fila = {
                    "columna": nombre_col,
                    "tipo": detalle.get("tipo", ""),
                    "nulos": detalle.get("nulos", 0),
                    "% nulos": round(detalle.get("porcentaje_nulos", 0.0), 2),
                    "valores_unicos": detalle.get("valores_unicos", ""),
                }

                if detalle.get("tipo") == "numerico":
                    fila["min"] = detalle.get("min", "")
                    fila["max"] = detalle.get("max", "")
                    fila["media"] = round(detalle.get("media", 0), 2) if detalle.get("media") is not None else ""
                    fila["mediana"] = detalle.get("mediana", "")
                    fila["std"] = round(detalle.get("std", 0), 2) if detalle.get("std") is not None else ""
                    fila["ceros"] = detalle.get("ceros", "")
                    fila["negativos"] = detalle.get("negativos", "")
                else:
                    valores_frecuentes = detalle.get("valores_frecuentes", {})
                    if valores_frecuentes:
                        top_valor = list(valores_frecuentes.items())[0]
                        fila["valor_mas_frecuente"] = f"{top_valor[0]} ({top_valor[1]})"
                    else:
                        fila["valor_mas_frecuente"] = ""

                filas_tabla.append(fila)

            df_columnas = pd.DataFrame(filas_tabla)
            st.dataframe(df_columnas, use_container_width=True, hide_index=True)


def pagina_reglas():
    st.title("Reglas generadas por el LLM")
    results = cargar_results()

    if results is None:
        st.warning("No se encontraron resultados. Ejecuta el pipeline primero.")
        return

    rules = results["rules"]

    # ── Metricas superiores ───────────────────────────────────────────────────

    tablas_cubiertas = len(set(r.get("tabla", "") for r in rules))
    tipos_distintos  = len(set(r.get("type", "") for r in rules))

    col1, col2, col3 = st.columns(3)
    col1.metric("Reglas generadas", len(rules))
    col2.metric("Tablas cubiertas", tablas_cubiertas)
    col3.metric("Tipos de validacion", tipos_distintos)

    st.divider()

    # ── Grafico de barras por tipo ────────────────────────────────────────────

    st.subheader("Reglas por tipo de validacion")

    conteo_tipos = {}
    for r in rules:
        tipo = r.get("type", "desconocido")
        conteo_tipos[tipo] = conteo_tipos.get(tipo, 0) + 1

    df_tipos = pd.DataFrame(
        list(conteo_tipos.items()),
        columns=["Tipo", "Cantidad"]
    ).sort_values("Cantidad", ascending=False)

    st.bar_chart(df_tipos.set_index("Tipo"))

    st.divider()

    # ── Detalle por tabla ─────────────────────────────────────────────────────

    st.subheader("Detalle por tabla")

    tablas = sorted(set(r.get("tabla", "sin tabla") for r in rules))
    tabs   = st.tabs(tablas)

    for tab, tabla in zip(tabs, tablas):
        with tab:
            reglas_tabla = [r for r in rules if r.get("tabla") == tabla]

            filas = []
            for r in reglas_tabla:
                filas.append({
                    "Tipo":        r.get("type", ""),
                    "Columna":     r.get("column") or r.get("column_after") or "—",
                    "Descripcion": r.get("descripcion", ""),
                })

            df = pd.DataFrame(filas)
            st.dataframe(df, use_container_width=True, hide_index=True)


def pagina_resultados():
    st.title("Resultados y metricas")
    results = cargar_results()

    if results is None:
        st.warning("No se encontraron resultados. Ejecuta el pipeline primero.")
        return

    metricas        = results["metricas"]
    resultados      = results["results"]
    tasa            = metricas["tasa_deteccion_tipos"]
    total_inyectadas = metricas["total_inyectadas"]
    tipos_detectados = len(metricas["tipos_detectados"])
    tipos_no_detect  = len(metricas["tipos_no_detectados"])
    errores_total    = metricas["errores_detectados_total"]

    # ── Tasa de deteccion prominente ─────────────────────────────────────────

    color = "green" if tasa == 100.0 else "orange" if tasa >= 75.0 else "red"
    st.markdown(
        f"<h1 style='text-align:center; color:{color}; font-size:5rem;'>{tasa}%</h1>"
        f"<p style='text-align:center; color:gray; font-size:1.2rem;'>Tasa de deteccion</p>",
        unsafe_allow_html=True,
    )

    st.divider()

    # ── Metricas en dos columnas ──────────────────────────────────────────────

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Anomalias inyectadas",  total_inyectadas)
    col2.metric("Errores detectados",    errores_total)
    col3.metric("Tipos detectados",      f"{tipos_detectados} / {tipos_detectados + tipos_no_detect}")
    col4.metric("Tipos no detectados",   tipos_no_detect)

    st.divider()

    # ── Inyectadas vs detectadas ──────────────────────────────────────────────

    st.subheader("Anomalias inyectadas vs detectadas por tipo")

    deteccion_por_tipo = metricas["deteccion_por_tipo"]
    filas_comparativa = []
    for tipo, detalle in deteccion_por_tipo.items():
        filas_comparativa.append({
            "Tipo de anomalia":   tipo,
            "Inyectadas":         detalle["cantidad_inyectada"],
            "Detectado":          "SI" if detalle["detectado"] else "NO",
        })

    df_comparativa = pd.DataFrame(filas_comparativa)

    def colorear_detectado(val):
        if val == "SI":
            return "background-color: #1e7e34; color: white; font-weight: bold"
        return "background-color: #c0392b; color: white; font-weight: bold"

    st.dataframe(
        df_comparativa.style.applymap(colorear_detectado, subset=["Detectado"]),
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    # ── Resultados de validacion ──────────────────────────────────────────────

    st.subheader("Resultados de validacion por regla")

    filas_resultados = []
    for r in resultados:
        rule   = r["rule"]
        estado = "FALLO" if r["errors"] > 0 else "OK"
        filas_resultados.append({
            "Estado":   estado,
            "Tipo":     rule.get("type", ""),
            "Tabla":    rule.get("tabla", ""),
            "Columna":  rule.get("column") or rule.get("column_after") or "—",
            "Errores":  r["errors"],
            "Detalle":  r.get("detalle", ""),
        })

    df_resultados = pd.DataFrame(filas_resultados)

    def colorear_estado(val):
        if val == "FALLO":
            return "background-color: #c0392b; color: white; font-weight: bold"
        return "background-color: #1e7e34; color: white; font-weight: bold"

    st.dataframe(
        df_resultados.style.applymap(colorear_estado, subset=["Estado"]),
        use_container_width=True,
        hide_index=True,
    )

    # ── Tipos no detectados ───────────────────────────────────────────────────

    if metricas["tipos_no_detectados"]:
        st.divider()
        st.subheader("Oportunidades de mejora")
        for tipo in metricas["tipos_no_detectados"]:
            st.warning(f"Tipo no detectado: {tipo}")
    else:
        st.divider()
        st.success("El sistema detecto el 100% de los tipos de anomalias inyectadas.")


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