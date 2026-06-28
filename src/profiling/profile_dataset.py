"""
Modulo de profiling del dataset sintetico de e-commerce
Hackathon Atmira - Reto 03: Calidad del dato

Lee los 4 CSV de data/raw/ y genera:
  - Resumen JSON en data/profiling/summary.json (para el LLM)
  - Informe HTML en data/profiling/reports/ (para inspeccion visual)

Usa solo pandas, sin dependencias externas adicionales.

Uso:
  python src/profiling/profile_dataset.py
"""

import os
import json
import pandas as pd

# ── Configuracion ─────────────────────────────────────────────────────────────

RAW_DIR       = os.path.join(os.path.dirname(__file__), "..", "..", "data", "raw")
PROFILING_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "profiling")
REPORTS_DIR   = os.path.join(PROFILING_DIR, "reports")

TABLAS = {
    "clientes":      "clientes.csv",
    "productos":     "productos.csv",
    "pedidos":       "pedidos.csv",
    "lineas_pedido": "lineas_pedido.csv",
}

# ── Profiling ─────────────────────────────────────────────────────────────────

def perfilar_columna(serie: pd.Series) -> dict:
    info = {}
    info["nulos"]             = int(serie.isna().sum())
    info["porcentaje_nulos"]  = round(float(serie.isna().mean()) * 100, 2)
    info["valores_unicos"]    = int(serie.nunique())

    if pd.api.types.is_numeric_dtype(serie):
        info["tipo"]      = "numerico"
        info["min"]       = float(serie.min()) if not serie.isna().all() else None
        info["max"]       = float(serie.max()) if not serie.isna().all() else None
        info["media"]     = round(float(serie.mean()), 4) if not serie.isna().all() else None
        info["mediana"]   = float(serie.median()) if not serie.isna().all() else None
        info["std"]       = round(float(serie.std()), 4) if not serie.isna().all() else None
        info["ceros"]     = int((serie == 0).sum())
        info["negativos"] = int((serie < 0).sum())
    else:
        info["tipo"] = "texto_o_categorico"
        top = serie.value_counts().head(5).to_dict()
        info["valores_frecuentes"] = {str(k): int(v) for k, v in top.items()}

    return info


def perfilar_tabla(df: pd.DataFrame, nombre: str) -> dict:
    return {
        "tabla":            nombre,
        "filas":            len(df),
        "columnas":         len(df.columns),
        "filas_duplicadas": int(df.duplicated().sum()),
        "columnas_detalle": {col: perfilar_columna(df[col]) for col in df.columns},
    }


# ── Informe HTML ──────────────────────────────────────────────────────────────

def generar_html(df: pd.DataFrame, resumen: dict, nombre: str, ruta: str):
    filas_dup = resumen["filas_duplicadas"]

    filas_resumen = ""
    for col, info in resumen["columnas_detalle"].items():
        tipo      = info["tipo"]
        nulos     = info["nulos"]
        pct_nulos = info["porcentaje_nulos"]
        unicos    = info["valores_unicos"]

        if tipo == "numerico":
            extra = (
                f"min={info['min']} | max={info['max']} | "
                f"media={info['media']} | std={info['std']} | "
                f"ceros={info['ceros']} | negativos={info['negativos']}"
            )
        else:
            top = ", ".join(f"{k} ({v})" for k, v in info.get("valores_frecuentes", {}).items())
            extra = f"Top valores: {top}"

        filas_resumen += f"""
        <tr>
            <td>{col}</td>
            <td>{tipo}</td>
            <td>{nulos} ({pct_nulos}%)</td>
            <td>{unicos}</td>
            <td>{extra}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Perfil - {nombre}</title>
<style>
  body {{ font-family: Arial, sans-serif; margin: 2rem; background: #f9f9f9; }}
  h1 {{ color: #2c3e50; }}
  table {{ border-collapse: collapse; width: 100%; background: white; }}
  th {{ background: #2c3e50; color: white; padding: 8px 12px; text-align: left; }}
  td {{ padding: 8px 12px; border-bottom: 1px solid #ddd; }}
  tr:hover {{ background: #f1f1f1; }}
  .meta {{ background: white; padding: 1rem; margin-bottom: 1rem;
            border-left: 4px solid #2c3e50; }}
</style>
</head>
<body>
<h1>Perfil de tabla: {nombre}</h1>
<div class="meta">
  <strong>Filas:</strong> {resumen["filas"]} &nbsp;|&nbsp;
  <strong>Columnas:</strong> {resumen["columnas"]} &nbsp;|&nbsp;
  <strong>Filas duplicadas:</strong> {filas_dup}
</div>
<table>
  <thead>
    <tr>
      <th>Columna</th><th>Tipo</th><th>Nulos</th>
      <th>Valores unicos</th><th>Estadisticas</th>
    </tr>
  </thead>
  <tbody>{filas_resumen}
  </tbody>
</table>
</body>
</html>"""

    with open(ruta, "w", encoding="utf-8") as f:
        f.write(html)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    os.makedirs(REPORTS_DIR, exist_ok=True)

    resumen_global = {
        "descripcion": (
            "Perfil estadistico del dataset sintetico de e-commerce. "
            "Generado a partir de datos limpios sin anomalias. "
            "Este resumen sera usado por el LLM para proponer reglas de calidad."
        ),
        "tablas": {}
    }

    for nombre, archivo in TABLAS.items():
        print(f"Procesando tabla: {nombre}")
        df = pd.read_csv(os.path.join(RAW_DIR, archivo))
        print(f"  {len(df)} filas, {len(df.columns)} columnas.")

        resumen = perfilar_tabla(df, nombre)
        resumen_global["tablas"][nombre] = resumen

        ruta_html = os.path.join(REPORTS_DIR, f"{nombre}_report.html")
        generar_html(df, resumen, nombre, ruta_html)
        print(f"  Informe HTML guardado: {ruta_html}")

    ruta_json = os.path.join(PROFILING_DIR, "summary.json")
    with open(ruta_json, "w", encoding="utf-8") as f:
        json.dump(resumen_global, f, ensure_ascii=False, indent=2)

    print(f"\nResumen JSON guardado: {ruta_json}")
    print("Profiling completado.")
    print("  Informes HTML -> data/profiling/reports/")
    print("  Resumen JSON  -> data/profiling/summary.json")


if __name__ == "__main__":
    main()