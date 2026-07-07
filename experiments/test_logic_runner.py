import pandas as pd


def ejecutar_total_check(test):
    """
    Ejecuta un test unitario del cálculo del total de un pedido.
    """

    lineas = pd.DataFrame(test["input"]["lineas"])

    total = (
        lineas["cantidad"] *
        lineas["precio_unitario"]
    ).sum()

    esperado = test["expected"]

    ok = abs(total - esperado) < 0.01

    return ok, f"Esperado={esperado} Calculado={total}"


def ejecutar_date_order(test):
    pedido = test["input"]

    fecha_pedido = pd.to_datetime(pedido["fecha_pedido"])
    fecha_entrega = pd.to_datetime(pedido["fecha_entrega"])

    ok = fecha_entrega >= fecha_pedido

    return ok, (
        f"pedido={fecha_pedido.date()} "
        f"entrega={fecha_entrega.date()}"
    )


def ejecutar_stock(test):
    producto = test["input"]

    ok = producto["cantidad_total"] <= producto["stock"]

    return ok, (
        f"stock={producto['stock']} "
        f"pedido={producto['cantidad_total']}"
    )


RUNNERS = {
    "total_check": ejecutar_total_check,
    "date_order_check": ejecutar_date_order,
    "stock_check": ejecutar_stock,
}


def run_fixture_tests(tests):

    resultados = []

    for test in tests:

        tipo = test["type"]
        nombre = test.get("name", "Sin nombre")

        if tipo not in RUNNERS:

            resultados.append({
                "name": nombre,
                "type": tipo,
                "passed": False,
                "detail": "Tipo no implementado"
            })

            continue

        try:

            ok, detalle = RUNNERS[tipo](test)

        except Exception as e:

            ok = False
            detalle = str(e)

        resultados.append({

            "name": nombre,
            "type": tipo,
            "passed": ok,
            "detail": detalle

        })

    return resultados