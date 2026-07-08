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
Eres un experto en calidad de datos, validacion de pipelines ETL y generacion automatica de casos de prueba.

Analiza el esquema del dataset y la transformacion indicada.

Devuelve EXCLUSIVAMENTE un JSON valido con esta estructura exacta:

{{
  "rules": [...],
  "unit_tests": [...],
  "integration_tests": [...],
  "edge_cases": [...],
  "uat_tests": [...]
}}

No escribas explicaciones. No escribas markdown. No anadas comentarios fuera del JSON.

--------------------------------------------------
REGLAS (campo "rules")
--------------------------------------------------

Genera entre 8 y 12 reglas. Usa solo estos tipos y formatos EXACTOS:

null_check - campo obligatorio que no puede ser nulo. DEBE incluir "column":
{{"type": "null_check", "column": "estado", "tabla": "pedidos", "descripcion": "El campo estado no puede ser nulo."}}

positive_check - campo que debe ser mayor que cero. DEBE incluir "column":
{{"type": "positive_check", "column": "precio_unitario", "tabla": "productos", "descripcion": "El precio debe ser positivo."}}

email_check - campo con formato de email valido. DEBE incluir "column":
{{"type": "email_check", "column": "email", "tabla": "clientes", "descripcion": "El email debe tener formato valido."}}

date_order_check - una fecha debe ser posterior a otra. DEBE incluir "column_after" y "column_before":
{{"type": "date_order_check", "column_after": "fecha_entrega", "column_before": "fecha_pedido", "tabla": "pedidos", "descripcion": "La entrega debe ser posterior al pedido."}}

delivered_future_check - pedido entregado no puede tener fecha futura. SIN column:
{{"type": "delivered_future_check", "tabla": "pedidos", "descripcion": "Un pedido entregado no puede tener fecha futura."}}

total_check - total del pedido debe coincidir con suma de lineas. SIN column:
{{"type": "total_check", "tabla": "pedidos", "descripcion": "El total debe coincidir con la suma de lineas_pedido."}}

stock_check - cantidad pedida no puede superar el stock. SIN column:
{{"type": "stock_check", "tabla": "productos", "descripcion": "La cantidad pedida no puede superar el stock disponible."}}

registration_date_check - fecha de registro no puede ser posterior al primer pedido. SIN column:
{{"type": "registration_date_check", "tabla": "clientes", "descripcion": "La fecha de registro no puede ser posterior al primer pedido."}}

outlier_check - precio unitario fuera de 3 desviaciones estandar para su categoria. SIN column, requiere group_by:
{{"type": "outlier_check", "column": "precio_unitario", "group_by": "categoria", "tabla": "productos", "descripcion": "El precio unitario no debe ser un outlier estadistico para su categoria"}}

CRITICO: Para null_check, positive_check y email_check el campo "column" es OBLIGATORIO.
Una regla de estos tipos sin "column" sera ignorada por el motor de validacion.

--------------------------------------------------
TESTS (campos "unit_tests", "integration_tests", "edge_cases", "uat_tests")
--------------------------------------------------

IMPORTANTE: Genera al menos 3 tests por categoria. Ninguna lista puede estar vacia.

Cada test DEBE tener EXACTAMENTE estos 5 campos:

{{
  "type": "total_check | stock_check | date_order_check | delivered_future_check",
  "name": "nombre corto del test",
  "description": "que comprueba este test",
  "input": {{ ... datos de entrada conocidos ... }},
  "expected": true | false | numero
}}

El campo "input" es OBLIGATORIO. Sin el no se puede ejecutar el test.

Formatos de input segun el tipo:

Para total_check:
"input": {{"lineas": [{{"cantidad": 2, "precio_unitario": 10.0}}, {{"cantidad": 3, "precio_unitario": 5.0}}]}}
"expected": 35.0

Para stock_check:
"input": {{"stock": 100, "cantidad_total": 80}}
"expected": true

Para date_order_check:
"input": {{"fecha_pedido": "2024-01-01", "fecha_entrega": "2024-01-10"}}
"expected": true

Para delivered_future_check:
"input": {{"estado": "entregado", "fecha_entrega": "2024-06-01"}}
"expected": true

--------------------------------------------------
EJEMPLOS COMPLETOS DE TESTS
--------------------------------------------------

Unit test correcto:
{{
  "type": "total_check",
  "name": "Pedido con dos lineas",
  "description": "El total debe ser 2x10 + 3x5 = 35",
  "input": {{"lineas": [{{"cantidad": 2, "precio_unitario": 10.0}}, {{"cantidad": 3, "precio_unitario": 5.0}}]}},
  "expected": 35.0
}}

Edge case correcto:
{{
  "type": "stock_check",
  "name": "Stock insuficiente",
  "description": "Cuando la cantidad pedida supera el stock debe dar false",
  "input": {{"stock": 5, "cantidad_total": 20}},
  "expected": false
}}

UAT test correcto:
{{
  "type": "delivered_future_check",
  "name": "Pedido entregado con fecha futura",
  "description": "Un pedido entregado no puede tener fecha de entrega futura",
  "input": {{"estado": "entregado", "fecha_entrega": "2026-06-01"}},
  "expected": false
}}

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
                "content": "Eres un experto en calidad de datos. Devuelves SOLO JSON valido, sin texto adicional ni markdown."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.2
    )

    return extract_json(response.choices[0].message.content)