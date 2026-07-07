"""
Fixture Runner — Ejecutor de tests generados automaticamente por el LLM
Hackathon Atmira - Reto 03: Calidad del dato

Ejecuta los tests generados por el LLM contra funciones reales de transformacion.
Cada test tiene un input conocido y un resultado esperado.

Tipos soportados:
  - total_check
  - stock_check
  - date_order_check
  - delivered_future_check
"""

from datetime import datetime


# ── Ejecutores por tipo ───────────────────────────────────────────────────────

def ejecutar_total_check(test: dict) -> tuple[bool, str]:
    """
    Verifica que el total de un pedido coincide con la suma de sus lineas.
    Input esperado: {"lineas": [{"cantidad": N, "precio_unitario": X}, ...]}
    Expected: numero (el total esperado)
    """
    input_data = test.get("input", {})
    lineas     = input_data.get("lineas", [])
    expected   = test.get("expected")

    if not lineas:
        return False, "No se proporcionaron lineas en el input"

    calculado = round(
        sum(l.get("cantidad", 0) * l.get("precio_unitario", 0) for l in lineas), 2
    )

    if isinstance(expected, bool):
        ok = calculado > 0
        return ok, f"Total calculado={calculado} (se esperaba positivo={expected})"

    ok = abs(calculado - float(expected)) < 0.01
    return ok, f"Esperado={expected} | Calculado={calculado}"


def ejecutar_stock_check(test: dict) -> tuple[bool, str]:
    """
    Verifica que la cantidad pedida no supera el stock disponible.
    Input esperado: {"stock": N, "cantidad_total": M}
    Expected: true (suficiente stock) o false (stock insuficiente)
    """
    input_data     = test.get("input", {})
    stock          = input_data.get("stock", 0)
    cantidad_total = input_data.get("cantidad_total", 0)
    expected       = test.get("expected", True)

    resultado = cantidad_total <= stock
    ok        = resultado == expected
    return ok, (
        f"Stock={stock} | Cantidad pedida={cantidad_total} | "
        f"Suficiente={resultado} | Esperado={expected}"
    )


def ejecutar_date_order_check(test: dict) -> tuple[bool, str]:
    """
    Verifica que la fecha de entrega es posterior a la fecha de pedido.
    Input esperado: {"fecha_pedido": "YYYY-MM-DD", "fecha_entrega": "YYYY-MM-DD"}
    Expected: true (fechas correctas) o false (entrega anterior al pedido)
    """
    input_data    = test.get("input", {})
    fecha_pedido  = input_data.get("fecha_pedido")
    fecha_entrega = input_data.get("fecha_entrega")
    expected      = test.get("expected", True)

    if not fecha_pedido or not fecha_entrega:
        return False, "Faltan fechas en el input"

    try:
        fp = datetime.strptime(fecha_pedido,  "%Y-%m-%d")
        fe = datetime.strptime(fecha_entrega, "%Y-%m-%d")
    except ValueError as e:
        return False, f"Formato de fecha invalido: {e}"

    resultado = fe >= fp
    ok        = resultado == expected
    return ok, (
        f"fecha_pedido={fecha_pedido} | fecha_entrega={fecha_entrega} | "
        f"Valido={resultado} | Esperado={expected}"
    )


def ejecutar_delivered_future_check(test: dict) -> tuple[bool, str]:
    """
    Verifica que un pedido entregado no tiene fecha de entrega futura.
    Input esperado: {"estado": "entregado", "fecha_entrega": "YYYY-MM-DD"}
    Expected: true (dato correcto) o false (anomalia)
    """
    input_data    = test.get("input", {})
    estado        = input_data.get("estado", "")
    fecha_entrega = input_data.get("fecha_entrega", "")
    expected      = test.get("expected", True)

    if not fecha_entrega:
        return False, "Falta fecha_entrega en el input"

    try:
        fe        = datetime.strptime(fecha_entrega, "%Y-%m-%d")
        fecha_ref = datetime(2025, 1, 1)
    except ValueError as e:
        return False, f"Formato de fecha invalido: {e}"

    es_valido = not (estado == "entregado" and fe >= fecha_ref)
    ok        = es_valido == expected
    return ok, (
        f"estado={estado} | fecha_entrega={fecha_entrega} | "
        f"Valido={es_valido} | Esperado={expected}"
    )

def ejecutar_email_check(test: dict) -> tuple[bool, str]:
    """
    Verifica que un email tiene formato valido.
    Input esperado: {"email": "usuario@ejemplo.com"}
    Expected: true (email valido) o false (email invalido)
    """
    import re
    input_data = test.get("input", {})
    email      = input_data.get("email", "")
    expected   = test.get("expected", True)

    patron    = r"^[^@]+@[^@]+\.[^@]+"
    resultado = bool(re.match(patron, email))
    ok        = resultado == expected
    return ok, f"Email='{email}' | Valido={resultado} | Esperado={expected}"


def ejecutar_positive_check(test: dict) -> tuple[bool, str]:
    """
    Verifica que un valor numerico es positivo.
    Input esperado: {"valor": -5}
    Expected: true (positivo) o false (negativo o cero)
    """
    input_data = test.get("input", {})
    valor      = input_data.get("valor", 0)
    expected   = test.get("expected", True)

    resultado = valor > 0
    ok        = resultado == expected
    return ok, f"Valor={valor} | Positivo={resultado} | Esperado={expected}"


# ── Dispatcher ────────────────────────────────────────────────────────────────

RUNNERS = {
    "total_check":            ejecutar_total_check,
    "stock_check":            ejecutar_stock_check,
    "date_order_check":       ejecutar_date_order_check,
    "delivered_future_check": ejecutar_delivered_future_check,
    "email_check":            ejecutar_email_check,
    "positive_check":         ejecutar_positive_check,
}


# ── Runner principal ──────────────────────────────────────────────────────────

def run_fixture_tests(tests: list) -> list:
    """
    Ejecuta una lista de tests generados por el LLM.

    Cada test debe tener:
      - type: tipo de validacion
      - name: nombre del test
      - description: descripcion
      - input: datos de entrada conocidos
      - expected: resultado esperado

    Devuelve lista de resultados con:
      - name, type, passed, detail
    """
    results = []

    for test in tests:
        tipo        = test.get("type")
        nombre      = test.get("name", "sin nombre")
        descripcion = test.get("description", "")

        runner = RUNNERS.get(tipo)

        if runner is None:
            results.append({
                "name":        nombre,
                "type":        tipo,
                "description": descripcion,
                "passed":      None,
                "detail":      f"Tipo '{tipo}' no soportado por el runner — pendiente de implementacion",
            })
            continue

        if "input" not in test:
            results.append({
                "name":        nombre,
                "type":        tipo,
                "description": descripcion,
                "passed":      None,
                "detail":      "El test no incluye campo 'input' — no ejecutable",
            })
            continue

        try:
            passed, detail = runner(test)
            results.append({
                "name":        nombre,
                "type":        tipo,
                "description": descripcion,
                "passed":      passed,
                "detail":      detail,
            })
        except Exception as e:
            results.append({
                "name":        nombre,
                "type":        tipo,
                "description": descripcion,
                "passed":      False,
                "detail":      f"Error al ejecutar el test: {e}",
            })

    return results