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
    except (json.JSONDecodeError, ValueError):
        # intenta limpiar formato ```json ... ```
        import re

        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())

        raise ValueError("No se pudo parsear JSON")


def generate_rules(schema, transformation):

    prompt = f"""
Eres un experto en calidad de datos y testing de pipelines.

Genera reglas de validacion para este pipeline.

Devuelve SOLO JSON valido SIN texto adicional.
No expliques nada. No añadas texto.

Las reglas en el array "rules" deben seguir EXACTAMENTE este formato,
usando solo estos tipos soportados:

- null_check:      campo no puede ser nulo
  ejemplo: {{"type": "null_check", "column": "estado", "tabla": "pedidos", "descripcion": "El estado es obligatorio"}}

- positive_check:  campo debe ser mayor que cero
  ejemplo: {{"type": "positive_check", "column": "precio_unitario", "tabla": "productos", "descripcion": "El precio debe ser positivo"}}

- email_check:     campo debe tener formato de email valido
  ejemplo: {{"type": "email_check", "column": "email", "tabla": "clientes", "descripcion": "El email debe tener formato valido"}}

- date_order_check: una fecha debe ser posterior a otra
  ejemplo: {{"type": "date_order_check", "column_after": "fecha_entrega", "column_before": "fecha_pedido", "tabla": "pedidos", "descripcion": "La entrega debe ser posterior al pedido"}}

- total_check:     el total del pedido debe coincidir con la suma de sus lineas
  ejemplo: {{"type": "total_check", "tabla": "pedidos", "descripcion": "El total debe coincidir con la suma de lineas_pedido"}}

Formato de respuesta:

{{
  "rules": [],
  "unit_tests": [],
  "integration_tests": [],
  "edge_cases": [],
  "uat_tests": []
}}

SCHEMA:
{schema}

TRANSFORMACION:
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