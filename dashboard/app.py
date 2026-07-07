"""
Dashboard de calidad del dato — Hackathon Atmira
Reto 03: Mejora de la calidad del dato y reduccion de incidencias en produccion

Uso:
  streamlit run dashboard/app.py
"""

import os
import io
import sys
import json
import subprocess
import random
import pandas as pd
import streamlit as st
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Rutas ─────────────────────────────────────────────────────────────────────

BASE_DIR              = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIRTY_DIR             = os.path.join(BASE_DIR, "data", "dirty")
PROFILING_DIR         = os.path.join(BASE_DIR, "data", "profiling")
RESULTS_PATH          = os.path.join(BASE_DIR, "data", "results.json")
RULES_PROPUESTAS_PATH = os.path.join(BASE_DIR, "data", "rules_propuestas.json")

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


@st.cache_data
def cargar_rules_propuestas():
    if not os.path.exists(RULES_PROPUESTAS_PATH):
        return None
    with open(RULES_PROPUESTAS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def obtener_fecha_ultimo_run():
    if not os.path.exists(RESULTS_PATH):
        return "Desconocida (no se encontro results.json)"
    timestamp = os.path.getmtime(RESULTS_PATH)
    return datetime.fromtimestamp(timestamp).strftime("%d/%m/%Y %H:%M:%S")


# ── Generador de PDF ──────────────────────────────────────────────────────────

def estilo_cabecera():
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, -1), 8),
        ("GRID",       (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ])


def generar_pdf_informe(summary, log, results=None):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        topMargin=50, bottomMargin=50,
        leftMargin=50, rightMargin=50,
        title=f"Informe Calidad de Datos - {obtener_fecha_ultimo_run()}",
        author="Hackathon Atmira - Reto 03",
    )
    styles = getSampleStyleSheet()
    story  = []

    metricas   = results["metricas"]   if results else None
    rules      = results["rules"]      if results else []
    resultados = results["results"]    if results else []

    fecha_analisis = obtener_fecha_ultimo_run()

    story.append(Spacer(1, 40))
    story.append(Paragraph("Informe de Calidad de Datos", styles["Title"]))
    story.append(Spacer(1, 10))
    story.append(Paragraph("Hackathon Atmira — Reto 03", styles["Heading2"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(f"Fecha del ultimo analisis: <b>{fecha_analisis}</b>", styles["Normal"]))
    story.append(Spacer(1, 30))

    if metricas:
        story.append(Paragraph("1. Resumen de deteccion", styles["Heading2"]))
        story.append(Spacer(1, 8))
        datos_metricas = [
            ["Metrica", "Valor"],
            ["Total anomalias inyectadas", str(metricas.get("total_inyectadas", ""))],
            ["Errores detectados",         str(metricas.get("errores_detectados_total", ""))],
            ["Tipos inyectados",           str(len(metricas.get("tipos_inyectados", {})))],
            ["Tipos detectados",           str(len(metricas.get("tipos_detectados", [])))],
            ["Tipos no detectados",        str(len(metricas.get("tipos_no_detectados", [])))],
            ["Tasa de deteccion (%)",      str(metricas.get("tasa_deteccion_tipos", ""))],
        ]
        t = Table(datos_metricas, colWidths=[280, 180])
        t.setStyle(estilo_cabecera())
        story.append(t)
        story.append(Spacer(1, 20))

    if metricas and metricas.get("deteccion_por_tipo"):
        story.append(Paragraph("2. Deteccion por tipo de anomalia", styles["Heading2"]))
        story.append(Spacer(1, 8))
        cab = [["Tipo de anomalia", "Cantidad inyectada", "Detectado"]]
        filas_det = []
        for tipo, detalle in metricas["deteccion_por_tipo"].items():
            filas_det.append([
                Paragraph(tipo, styles["Normal"]),
                Paragraph(str(detalle["cantidad_inyectada"]), styles["Normal"]),
                Paragraph("SI" if detalle["detectado"] else "NO", styles["Normal"]),
            ])
        t = Table(cab + filas_det, colWidths=[240, 120, 100])
        estilo = estilo_cabecera()
        for i, fila in enumerate(filas_det, start=1):
            detectado = fila[2].text if hasattr(fila[2], "text") else str(fila[2])
            color_fondo = colors.HexColor("#1e7e34") if "SI" in detectado else colors.HexColor("#c0392b")
            estilo.add("BACKGROUND", (2, i), (2, i), color_fondo)
            estilo.add("TEXTCOLOR",  (2, i), (2, i), colors.white)
            estilo.add("FONTNAME",   (2, i), (2, i), "Helvetica-Bold")
        t.setStyle(estilo)
        story.append(t)
        story.append(Spacer(1, 20))

    story.append(PageBreak())

    if rules:
        story.append(Paragraph("3. Reglas generadas por el LLM", styles["Heading2"]))
        story.append(Spacer(1, 8))
        cab   = [["Tipo", "Tabla", "Columna", "Descripcion"]]
        filas = []
        for r in rules:
            filas.append([
                Paragraph(r.get("type", ""), styles["Normal"]),
                Paragraph(r.get("tabla", ""), styles["Normal"]),
                Paragraph(r.get("column") or r.get("column_after") or "-", styles["Normal"]),
                Paragraph(r.get("descripcion", ""), styles["Normal"]),
            ])
        t = Table(cab + filas, colWidths=[110, 90, 90, 180])
        t.setStyle(estilo_cabecera())
        story.append(t)
        story.append(Spacer(1, 20))

    if resultados:
        story.append(Paragraph("4. Resultados de validacion por regla", styles["Heading2"]))
        story.append(Spacer(1, 8))
        cab   = [["Estado", "Tipo", "Tabla", "Errores", "Detalle"]]
        filas = []
        for r in resultados:
            rule   = r["rule"]
            estado = "FALLO" if r["errors"] > 0 else "OK"
            filas.append([
                Paragraph(estado, styles["Normal"]),
                Paragraph(rule.get("type", ""), styles["Normal"]),
                Paragraph(rule.get("tabla", ""), styles["Normal"]),
                Paragraph(str(r["errors"]), styles["Normal"]),
                Paragraph(r.get("detalle", ""), styles["Normal"]),
            ])
        t = Table(cab + filas, colWidths=[45, 110, 80, 45, 190])
        estilo = estilo_cabecera()
        for i, fila in enumerate(filas, start=1):
            color_fondo = colors.HexColor("#c0392b") if "FALLO" in fila[0].text else colors.HexColor("#1e7e34")
            estilo.add("BACKGROUND", (0, i), (0, i), color_fondo)
            estilo.add("TEXTCOLOR",  (0, i), (0, i), colors.white)
            estilo.add("FONTNAME",   (0, i), (0, i), "Helvetica-Bold")
        t.setStyle(estilo)
        story.append(t)
        story.append(Spacer(1, 20))

    story.append(PageBreak())

    story.append(Paragraph("5. Profiling del dataset", styles["Heading2"]))
    story.append(Spacer(1, 8))
    for nombre_tabla, info in summary["tablas"].items():
        story.append(Paragraph(nombre_tabla, styles["Heading3"]))
        story.append(Paragraph(
            f"Filas: {info['filas']} | Columnas: {info['columnas']} | "
            f"Duplicadas: {info['filas_duplicadas']}",
            styles["Normal"]
        ))
        story.append(Spacer(1, 6))

    story.append(PageBreak())

    story.append(Paragraph("6. Anomalias inyectadas", styles["Heading2"]))
    story.append(Paragraph(f"Total: {log['total_anomalias']}", styles["Normal"]))
    story.append(Spacer(1, 10))
    cab   = [["Tipo", "Tabla", "Columna", "Fila ID"]]
    filas = []
    for anomalia in log["detalle"]:
        filas.append([
            Paragraph(anomalia["tipo"], styles["Normal"]),
            Paragraph(anomalia["tabla"], styles["Normal"]),
            Paragraph(anomalia["columna"], styles["Normal"]),
            Paragraph(str(anomalia["fila_id"]), styles["Normal"]),
        ])
    t = Table(cab + filas, colWidths=[150, 90, 90, 60])
    t.setStyle(estilo_cabecera())
    story.append(t)

    doc.build(story)
    buffer.seek(0)
    return buffer


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
            "Revision de reglas",
            "Reglas generadas",
            "Tests IA",
            "Resultados y metricas",
        ],
        label_visibility="collapsed",
    )

    st.divider()

    st.markdown("**Ejecutar pipeline**")
    st.caption("Regenera el dataset, inyecta anomalias y ejecuta la validacion completa.")

    regenerar = st.checkbox(
        "Generar dataset nuevo (seed aleatoria)",
        value=False,
        help="Sin marcar: datos reproducibles con seed fija. Marcado: dataset completamente nuevo en cada ejecucion.",
    )

    if st.button("Ejecutar pipeline completo", use_container_width=True, type="primary"):
        with st.spinner("Ejecutando pipeline..."):
            try:
                cmd = [sys.executable, os.path.join(BASE_DIR, "run_all.py")]
                if regenerar:
                    seed_aleatoria = random.randint(1, 999999)
                    cmd.append(f"--seed={seed_aleatoria}")

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    cwd=BASE_DIR,
                )
                if result.returncode == 0:
                    if regenerar:
                        st.success(f"Pipeline ejecutado con dataset nuevo (seed={seed_aleatoria}).")
                    else:
                        st.success("Pipeline ejecutado correctamente.")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Error al ejecutar el pipeline.")
                    st.code(result.stderr)
            except Exception as e:
                st.error(f"Error: {e}")

    st.divider()

    if st.button("Exportar informe PDF", use_container_width=True):
        summary = cargar_summary()
        log     = cargar_injection_log()
        results = cargar_results()
        if summary and log:
            pdf_buffer    = generar_pdf_informe(summary, log, results)
            fecha_archivo = obtener_fecha_ultimo_run().replace("/", "-").replace(":", "").replace(" ", "_")
            st.download_button(
                label="Descargar PDF",
                data=pdf_buffer,
                file_name=f"informe_calidad_{fecha_archivo}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        else:
            st.warning("Ejecuta el pipeline primero.")


# ── Paginas ───────────────────────────────────────────────────────────────────

def pagina_resumen():
    st.title("Resumen del proyecto")
    st.markdown(
        "Pipeline de deteccion de anomalias en datos de e-commerce usando IA generativa. "
        "El sistema genera reglas de calidad automaticamente a partir del perfil estadistico "
        "del dataset y las aplica para detectar errores antes de que lleguen a produccion."
    )

    fecha = obtener_fecha_ultimo_run()
    st.caption(f"Ultimo pipeline ejecutado: {fecha}")
    st.divider()

    summary = cargar_summary()
    log     = cargar_injection_log()
    results = cargar_results()

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
    st.title("Profiling del dataset")
    summary = cargar_summary()

    if summary is None:
        st.warning("No se encontro summary.json. Ejecuta el pipeline primero.")
        return

    tablas         = summary["tablas"]
    nombres_tablas = list(tablas.keys())
    tabs           = st.tabs(nombres_tablas)

    for tab, nombre_tabla in zip(tabs, nombres_tablas):
        with tab:
            info = tablas[nombre_tabla]
            col1, col2, col3 = st.columns(3)
            col1.metric("Filas", info["filas"])
            col2.metric("Columnas", info["columnas"])
            col3.metric("Filas duplicadas", info["filas_duplicadas"])

            st.subheader("Detalle por columna")
            filas_tabla = []
            for nombre_col, detalle in info["columnas_detalle"].items():
                fila = {
                    "columna":        nombre_col,
                    "tipo":           detalle.get("tipo", ""),
                    "nulos":          detalle.get("nulos", 0),
                    "% nulos":        round(detalle.get("porcentaje_nulos", 0.0), 2),
                    "valores_unicos": detalle.get("valores_unicos", ""),
                }
                if detalle.get("tipo") == "numerico":
                    fila["min"]       = detalle.get("min", "")
                    fila["max"]       = detalle.get("max", "")
                    fila["media"]     = round(detalle.get("media", 0), 2) if detalle.get("media") is not None else ""
                    fila["mediana"]   = detalle.get("mediana", "")
                    fila["std"]       = round(detalle.get("std", 0), 2) if detalle.get("std") is not None else ""
                    fila["ceros"]     = detalle.get("ceros", "")
                    fila["negativos"] = detalle.get("negativos", "")
                else:
                    vf = detalle.get("valores_frecuentes", {})
                    if vf:
                        top = list(vf.items())[0]
                        fila["valor_mas_frecuente"] = f"{top[0]} ({top[1]})"
                    else:
                        fila["valor_mas_frecuente"] = ""
                filas_tabla.append(fila)

            df_columnas = pd.DataFrame(filas_tabla)
            st.dataframe(df_columnas, use_container_width=True, hide_index=True)


def pagina_anomalias():
    st.title("Anomalias inyectadas")
    log = cargar_injection_log()

    if log is None:
        st.warning("No se encontro injection_log.json. Ejecuta el pipeline primero.")
        return

    col1, col2 = st.columns(2)
    col1.metric("Total anomalias inyectadas", log["total_anomalias"])
    col2.metric("Tipos distintos", len(log["anomalias_por_tipo"]))

    st.subheader("Anomalias por tipo")
    df_tipos = pd.DataFrame(
        list(log["anomalias_por_tipo"].items()),
        columns=["tipo", "cantidad"]
    ).set_index("tipo")
    st.bar_chart(df_tipos)

    st.subheader("Detalle de anomalias")
    df_detalle = pd.DataFrame(log["detalle"])
    columnas_orden     = ["tipo", "tabla", "columna", "fila_id", "valor_original", "valor_nuevo"]
    columnas_presentes = [c for c in columnas_orden if c in df_detalle.columns]
    df_detalle         = df_detalle[columnas_presentes]

    tipos_disponibles = ["Todos"] + sorted(df_detalle["tipo"].unique().tolist())
    tipo_seleccionado = st.selectbox("Filtrar por tipo", tipos_disponibles)
    if tipo_seleccionado != "Todos":
        df_detalle = df_detalle[df_detalle["tipo"] == tipo_seleccionado]

    st.dataframe(df_detalle, use_container_width=True, hide_index=True)


def pagina_revision_reglas():
    st.title("Revision de reglas propuestas por la IA")
    st.markdown(
        "La IA ha analizado el dataset y propone las siguientes reglas de validacion. "
        "Marca o desmarca cada regla antes de ejecutar la validacion. "
        "Solo se aplicaran las reglas que apruebes."
    )

    rules = cargar_rules_propuestas()

    if rules is None:
        st.warning("No hay reglas propuestas. Ejecuta el pipeline primero.")
        return

    filas = []
    for r in rules:
        filas.append({
            "aprobada":    True,
            "tipo":        r.get("type", ""),
            "tabla":       r.get("tabla", ""),
            "columna":     r.get("column") or r.get("column_after") or "-",
            "descripcion": r.get("descripcion", ""),
        })

    df_rules = pd.DataFrame(filas)

    df_editado = st.data_editor(
        df_rules,
        column_config={
            "aprobada":    st.column_config.CheckboxColumn("Aplicar", help="Marca para incluir esta regla en la validacion"),
            "tipo":        st.column_config.TextColumn("Tipo"),
            "tabla":       st.column_config.TextColumn("Tabla"),
            "columna":     st.column_config.TextColumn("Columna"),
            "descripcion": st.column_config.TextColumn("Descripcion"),
        },
        disabled=["tipo", "tabla", "columna", "descripcion"],
        use_container_width=True,
        hide_index=True,
    )

    n_aprobadas = int(df_editado["aprobada"].sum())
    n_total     = len(df_editado)
    st.caption(f"{n_aprobadas} de {n_total} reglas seleccionadas")

    if n_aprobadas == 0:
        st.warning("Selecciona al menos una regla para continuar.")
        return

    if st.button("Aplicar reglas seleccionadas", type="primary"):
        indices_aprobados = df_editado[df_editado["aprobada"]].index.tolist()
        reglas_aprobadas  = [rules[i] for i in indices_aprobados]

        dfs_dirty = {
            "clientes":      pd.read_csv(os.path.join(DIRTY_DIR, "clientes.csv")),
            "productos":     pd.read_csv(os.path.join(DIRTY_DIR, "productos.csv")),
            "pedidos":       pd.read_csv(os.path.join(DIRTY_DIR, "pedidos.csv")),
            "lineas_pedido": pd.read_csv(os.path.join(DIRTY_DIR, "lineas_pedido.csv")),
        }

        log_path = os.path.join(DIRTY_DIR, "injection_log.json")
        with open(log_path, "r", encoding="utf-8") as f:
            injection_log = json.load(f)

        from src.validation.run_rules import run_rules
        from src.evaluation.evaluation import evaluate

        with st.spinner("Ejecutando validacion con las reglas seleccionadas..."):
            results            = run_rules(dfs_dirty, reglas_aprobadas)
            results_con_fallos = [r for r in results if r["errors"] > 0]
            metricas           = evaluate(injection_log, results_con_fallos)

        results_data = {
            "rules":    reglas_aprobadas,
            "results":  results,
            "metricas": metricas,
        }
        with open(RESULTS_PATH, "w", encoding="utf-8") as f:
            json.dump(results_data, f, ensure_ascii=False, indent=2)

        st.cache_data.clear()

        st.success(f"{n_aprobadas} reglas aplicadas. Tasa de deteccion: {metricas['tasa_deteccion_tipos']}%")
        st.divider()

        col1, col2, col3 = st.columns(3)
        col1.metric("Reglas aplicadas",   n_aprobadas)
        col2.metric("Errores detectados", metricas["errores_detectados_total"])
        col3.metric("Tasa de deteccion",  f"{metricas['tasa_deteccion_tipos']}%")

        st.subheader("Resultados por regla")
        filas_res = []
        for r in results:
            estado = "FALLO" if r["errors"] > 0 else "OK"
            filas_res.append({
                "Estado":  estado,
                "Tipo":    r["rule"].get("type", ""),
                "Tabla":   r["rule"].get("tabla", ""),
                "Errores": r["errors"],
                "Detalle": r.get("detalle", ""),
            })
        df_res = pd.DataFrame(filas_res)

        def colorear_estado(val):
            if val == "FALLO":
                return "background-color: #c0392b; color: white; font-weight: bold"
            return "background-color: #1e7e34; color: white; font-weight: bold"

        st.dataframe(
            df_res.style.applymap(colorear_estado, subset=["Estado"]),
            use_container_width=True,
            hide_index=True,
        )


def pagina_reglas():
    st.title("Reglas generadas por el LLM")
    results = cargar_results()

    if results is None:
        st.warning("No se encontraron resultados. Ejecuta el pipeline primero.")
        return

    rules = results["rules"]
    tablas_cubiertas = len(set(r.get("tabla", "") for r in rules))
    tipos_distintos  = len(set(r.get("type", "") for r in rules))

    col1, col2, col3 = st.columns(3)
    col1.metric("Reglas generadas", len(rules))
    col2.metric("Tablas cubiertas", tablas_cubiertas)
    col3.metric("Tipos de validacion", tipos_distintos)

    st.divider()
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


def pagina_tests():
    st.title("Tests generados automaticamente por IA")
    st.markdown(
        "El LLM genera automaticamente casos de prueba para validar la logica "
        "de las transformaciones ETL. Cada test ejecuta la funcion real con un "
        "input conocido y compara el resultado con el esperado."
    )

    results = cargar_results()
    if results is None:
        st.warning("No se encontraron resultados. Ejecuta el pipeline primero.")
        return

    fixture_results   = results.get("fixture_results", [])
    unit_tests        = results.get("unit_tests", [])
    integration_tests = results.get("integration_tests", [])
    edge_cases        = results.get("edge_cases", [])
    uat_tests         = results.get("uat_tests", [])

    if not fixture_results:
        st.warning("No hay resultados de tests. Ejecuta el pipeline completo primero.")
        return

    pasados    = sum(1 for r in fixture_results if r.get("passed") is True)
    fallados   = sum(1 for r in fixture_results if r.get("passed") is False)
    pendientes = sum(1 for r in fixture_results if r.get("passed") is None)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total tests",  len(fixture_results))
    col2.metric("Pasados",      pasados)
    col3.metric("Fallados",     fallados)
    col4.metric("Pendientes",   pendientes)

    st.divider()

    def renderizar_tests(tests_def, resultados_runner, titulo):
        st.subheader(titulo)
        if not tests_def:
            st.caption("No hay tests en esta categoria.")
            return

        nombres_runner = {r["name"]: r for r in resultados_runner}

        for t in tests_def:
            nombre    = t.get("name", "sin nombre")
            resultado = nombres_runner.get(nombre)

            if resultado:
                passed = resultado.get("passed")
                if passed is True:
                    icono, color = "OK",        "#1e7e34"
                elif passed is False:
                    icono, color = "FALLO",     "#c0392b"
                else:
                    icono, color = "PENDIENTE", "#888888"
                detalle = resultado.get("detail", "")
            else:
                icono, color, detalle = "PENDIENTE", "#888888", "Sin resultado"

            st.markdown(
                f"<div style='border-left: 4px solid {color}; padding: 8px 12px; margin-bottom: 8px;'>"
                f"<b style='color:{color}'>[{icono}]</b> {nombre}<br>"
                f"<small style='color:gray'>{t.get('description', '')}</small><br>"
                f"<small>{detalle}</small>"
                f"</div>",
                unsafe_allow_html=True,
            )

    tab1, tab2, tab3, tab4 = st.tabs([
        "Unit Tests", "Integration Tests", "Edge Cases", "UAT Tests"
    ])

    with tab1:
        renderizar_tests(unit_tests, fixture_results, "Unit Tests")
    with tab2:
        renderizar_tests(integration_tests, fixture_results, "Integration Tests")
    with tab3:
        renderizar_tests(edge_cases, fixture_results, "Edge Cases")
    with tab4:
        renderizar_tests(uat_tests, fixture_results, "UAT Tests")


def pagina_resultados():
    st.title("Resultados y metricas")
    results = cargar_results()

    if results is None:
        st.warning("No se encontraron resultados. Ejecuta el pipeline primero.")
        return

    metricas         = results["metricas"]
    resultados       = results["results"]
    tasa             = metricas["tasa_deteccion_tipos"]
    total_inyectadas = metricas["total_inyectadas"]
    tipos_detectados = len(metricas["tipos_detectados"])
    tipos_no_detect  = len(metricas["tipos_no_detectados"])
    errores_total    = metricas["errores_detectados_total"]

    color = "green" if tasa == 100.0 else "orange" if tasa >= 75.0 else "red"
    st.markdown(
        f"<h1 style='text-align:center; color:{color}; font-size:5rem;'>{tasa}%</h1>"
        f"<p style='text-align:center; color:gray; font-size:1.2rem;'>Tasa de deteccion</p>",
        unsafe_allow_html=True,
    )

    st.divider()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Anomalias inyectadas", total_inyectadas)
    col2.metric("Errores detectados",   errores_total)
    col3.metric("Tipos detectados",     f"{tipos_detectados} / {tipos_detectados + tipos_no_detect}")
    col4.metric("Tipos no detectados",  tipos_no_detect)

    st.divider()
    st.subheader("Anomalias inyectadas vs detectadas por tipo")

    deteccion_por_tipo = metricas["deteccion_por_tipo"]
    filas_comparativa  = []
    for tipo, detalle in deteccion_por_tipo.items():
        filas_comparativa.append({
            "Tipo de anomalia": tipo,
            "Inyectadas":       detalle["cantidad_inyectada"],
            "Detectado":        "SI" if detalle["detectado"] else "NO",
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
    st.subheader("Resultados de validacion por regla")

    filas_resultados = []
    for r in resultados:
        rule   = r["rule"]
        estado = "FALLO" if r["errors"] > 0 else "OK"
        filas_resultados.append({
            "Estado":  estado,
            "Tipo":    rule.get("type", ""),
            "Tabla":   rule.get("tabla", ""),
            "Columna": rule.get("column") or rule.get("column_after") or "—",
            "Errores": r["errors"],
            "Detalle": r.get("detalle", ""),
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
elif pagina == "Revision de reglas":
    pagina_revision_reglas()
elif pagina == "Reglas generadas":
    pagina_reglas()
elif pagina == "Tests IA":
    pagina_tests()
elif pagina == "Resultados y metricas":
    pagina_resultados()