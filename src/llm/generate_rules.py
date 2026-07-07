from openai import OpenAI
from dotenv import load_dotenv
import os
import json
import re

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def extract_json(text):
    """
    Extrae un JSON aunque el modelo devuelva texto adicional.
    """
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError("No se pudo parsear el JSON devuelto por el modelo.")


def generate_rules(schema, transformation):

    prompt = f"""
Eres un experto en calidad de datos, validación de pipelines ETL y generación automática de casos de prueba.

Analiza el esquema del dataset y la transformación indicada.

Devuelve EXCLUSIVAMENTE un JSON válido.

No escribas explicaciones.
No escribas markdown.
No añadas comentarios.

--------------------------------------------------
REGLAS SOPORTADAS
--------------------------------------------------

Solo puedes utilizar estos tipos:

- null_check
- positive_check
- email_check
- date_order_check
- delivered_future_check
- total_check
- stock_check
- registration_date_check

Cada regla debe tener este formato:

{{
    "type": "...",
    "tabla": "...",
    "descripcion": "..."
}}

Las reglas que necesiten columnas deberán incluir además:

"column"

o

"column_after"
"column_before"

--------------------------------------------------
TESTS
--------------------------------------------------

Además genera automáticamente:

- unit_tests
- integration_tests
- edge_cases
- uat_tests

NO dejes ninguna lista vacía.

Genera al menos 3 elementos por categoría.

Cada test debe tener EXACTAMENTE este formato:

{{
    "type": "total_check | stock_check | date_order_check | delivered_future_check | null_check | positive_check | email_check | registration_date_check",
    "name": "...",
    "description": "...",
    "expected": true
}}

El campo "type" debe coincidir con alguno de los tipos soportados por el motor de validación.

Los tests deben comprobar la lógica del pipeline y no únicamente el formato de los datos.

Ejemplos:

Unit Test:
- comprobar que el total del pedido coincide con la suma de sus líneas.

Integration Test:
- comprobar que el precio_unitario de lineas_pedido coincide con productos.

Edge Case:
- pedido sin líneas
- cantidad cero
- producto sin stock
- cliente sin pedidos

UAT:
- el total mostrado debe ser correcto
- un pedido entregado no puede tener fecha futura
- un cliente debe registrarse antes de comprar

--------------------------------------------------
RESPUESTA
--------------------------------------------------
{

    "type":"total_check",

    "name":"Pedido con dos líneas",

    "description":"Comprobar cálculo del total",

    "input":{

        "lineas":[

            {

                "cantidad":2,

                "precio_unitario":10

            },

            {

                "cantidad":3,

                "precio_unitario":5

            }

        ]

    },

    "expected":35

}



{

    "type":"date_order_check",

    "name":"Entrega posterior",

    "input":{

        "fecha_pedido":"2024-01-01",

        "fecha_entrega":"2024-01-03"

    },

    "expected":true

}



{

    "type":"stock_check",

    "name":"Stock suficiente",

    "input":{

        "stock":100,

        "cantidad_total":80

    },

    "expected":true

}

--------------------------------------------------
SCHEMA
--------------------------------------------------

{schema}

--------------------------------------------------
TRANSFORMACION
--------------------------------------------------

{transformation}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "Eres un experto en calidad de datos y generación automática de reglas de validación y casos de prueba."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.4
    )

    return extract_json(response.choices[0].message.content)