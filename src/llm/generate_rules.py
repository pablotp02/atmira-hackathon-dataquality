from openai import OpenAI
import os
import json

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_rules(schema, transformation):

    prompt = f"""
Eres un experto en calidad de datos y testing de pipelines.

Genera reglas de validación para este pipeline.

Devuelve SOLO JSON válido.

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
            {"role": "system", "content": "Eres un generador de tests de datos"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2
    )

    return json.loads(response.choices[0].message.content)