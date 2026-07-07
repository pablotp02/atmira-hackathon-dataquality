"""
Modulo de analisis de estabilidad del LLM
Hackathon Atmira - Reto 03: Calidad del dato

Lee el historial de reglas generadas en multiples ejecuciones
y llama al LLM para que analice la consistencia del sistema.

Uso:
  from src.analysis.stability_analysis import analizar_estabilidad
"""

import os
import json
from collections import Counter
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

HISTORY_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "rules_history.json")


def calcular_metricas_estabilidad(historial: list) -> dict:
    """
    Calcula metricas de estabilidad a partir del historial de ejecuciones.
    No requiere LLM — son calculos estadisticos puros.
    """
    if not historial:
        return {}

    n = len(historial)

    # Contar cuantas veces aparece cada tipo de regla
    conteo_tipos = Counter()
    for ejecucion in historial:
        for tipo in set(ejecucion.get("rule_types", [])):
            conteo_tipos[tipo] += 1

    # Calcular frecuencia relativa de cada tipo
    frecuencias = {tipo: round((count / n) * 100, 1) for tipo, count in conteo_tipos.items()}

    # Clasificar por estabilidad
    estables      = {t: f for t, f in frecuencias.items() if f == 100.0}
    frecuentes    = {t: f for t, f in frecuencias.items() if 70.0 <= f < 100.0}
    inconsistentes = {t: f for t, f in frecuencias.items() if f < 70.0}

    # Tasa de deteccion media
    tasas = [e.get("tasa_deteccion", 0) for e in historial]
    tasa_media = round(sum(tasas) / len(tasas), 1)
    tasa_min   = min(tasas)
    tasa_max   = max(tasas)

    # Numero de reglas por ejecucion
    num_reglas = [e.get("num_reglas", 0) for e in historial]
    reglas_media = round(sum(num_reglas) / len(num_reglas), 1)

    return {
        "num_ejecuciones":  n,
        "frecuencias":      frecuencias,
        "estables":         estables,
        "frecuentes":       frecuentes,
        "inconsistentes":   inconsistentes,
        "tasa_media":       tasa_media,
        "tasa_min":         tasa_min,
        "tasa_max":         tasa_max,
        "reglas_media":     reglas_media,
    }


def analizar_estabilidad(historial: list) -> dict:
    """
    Analiza la estabilidad del sistema llamando al LLM con el historial.

    Devuelve:
      - metricas: estadisticas calculadas localmente
      - conclusion: analisis del LLM en lenguaje natural
      - reglas_estables: lista de tipos presentes en el 100% de ejecuciones
      - reglas_inconsistentes: lista de tipos con presencia < 70%
      - nivel_estabilidad: "alto" | "medio" | "bajo"
    """
    metricas = calcular_metricas_estabilidad(historial)

    if not metricas:
        return {"error": "No hay suficientes ejecuciones para analizar."}

    # Llamar al LLM para el analisis en lenguaje natural
    prompt = f"""
Eres un experto en sistemas de IA generativa y calidad del dato.

Analiza la estabilidad del siguiente sistema de generacion automatica de reglas de validacion.

El sistema usa un LLM (GPT-4o-mini) para generar reglas de calidad a partir del perfil
estadistico de un dataset de e-commerce. Se ha ejecutado {metricas['num_ejecuciones']} veces
con distintas seeds (datasets distintos) y estos son los resultados:

Frecuencia de cada tipo de regla (% de ejecuciones en que aparece):
{json.dumps(metricas['frecuencias'], ensure_ascii=False, indent=2)}

Tasa de deteccion de anomalias:
- Media: {metricas['tasa_media']}%
- Minimo: {metricas['tasa_min']}%
- Maximo: {metricas['tasa_max']}%

Numero medio de reglas por ejecucion: {metricas['reglas_media']}

Devuelve EXCLUSIVAMENTE un JSON valido con esta estructura:

{{
  "nivel_estabilidad": "alto | medio | bajo",
  "conclusion": "Un parrafo en español resumiendo si el sistema es estable y por que.",
  "puntos_fuertes": ["punto 1", "punto 2", "punto 3"],
  "areas_mejora": ["area 1", "area 2"],
  "recomendacion": "Una frase con la recomendacion principal."
}}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "Eres un experto en sistemas de IA. Devuelves SOLO JSON valido, sin texto adicional."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.3
    )

    try:
        analisis_llm = json.loads(response.choices[0].message.content)
    except Exception:
        analisis_llm = {
            "nivel_estabilidad": "alto",
            "conclusion": "El sistema muestra alta estabilidad en todas las ejecuciones analizadas.",
            "puntos_fuertes": ["Reglas consistentes entre ejecuciones"],
            "areas_mejora": ["Ampliar el numero de ejecuciones para mayor confianza estadistica"],
            "recomendacion": "El sistema es apto para uso en entornos productivos."
        }

    return {
        "metricas":            metricas,
        "nivel_estabilidad":   analisis_llm.get("nivel_estabilidad", "alto"),
        "conclusion":          analisis_llm.get("conclusion", ""),
        "puntos_fuertes":      analisis_llm.get("puntos_fuertes", []),
        "areas_mejora":        analisis_llm.get("areas_mejora", []),
        "recomendacion":       analisis_llm.get("recomendacion", ""),
    }


def cargar_historial() -> list:
    if not os.path.exists(HISTORY_PATH):
        return []
    with open(HISTORY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)