from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()
import os
import json

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def extract_json(text):
    """
    Extrae JSON aunque el modelo devuelva texto extra.
    """
    try:
        return json.loads(text)
    except:
        # intenta limpiar formato ```json ... ```
        import re

        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())

        raise ValueError("No se pudo parsear JSON")


def generate_rules(schema, transformation):

    prompt = f"""
Eres un experto en calidad de datos y testing de pipelines.

Genera reglas de validación para este pipeline.

Devuelve SOLO JSON válido SIN texto adicional.

Si no puedes generar JSON válido, intenta de nuevo internamente.
No expliques nada.
No añadas texto.

Formato:

{{
  "rules": [],
  "unit_tests": [],
  "integration_tests": [],
  "edge_cases": [],
  "uat_tests": []
}}

SCHEMA:
{schema}

TRANSFORMACIÓN:
{transformation}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Eres un generador de tests de datos estructurados"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2
    )

    return extract_json(response.choices[0].message.content)