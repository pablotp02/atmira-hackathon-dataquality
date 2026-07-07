import pandas as pd


# -------------------------------------------------------------------
# Funciones de comprobación
# -------------------------------------------------------------------

def check_total(dfs):
    pedidos = dfs["pedidos"]
    lineas = dfs["lineas_pedido"]

    calculado = (
        lineas.assign(
            subtotal=lineas["cantidad"] * lineas["precio_unitario"]
        )
        .groupby("pedido_id")["subtotal"]
        .sum()
        .reset_index()
    )

    merged = pedidos.merge(calculado, on="pedido_id")

    errores = (merged["total"] - merged["subtotal"]).abs() > 0.01

    return (
        not errores.any(),
        f"{errores.sum()} pedidos con total incorrecto"
    )


def check_date_order(dfs):
    pedidos = dfs["pedidos"].copy()

    pedidos["fecha_pedido"] = pd.to_datetime(
        pedidos["fecha_pedido"],
        errors="coerce"
    )

    pedidos["fecha_entrega"] = pd.to_datetime(
        pedidos["fecha_entrega"],
        errors="coerce"
    )

    errores = pedidos["fecha_entrega"] < pedidos["fecha_pedido"]

    return (
        not errores.any(),
        f"{errores.sum()} pedidos con fechas inconsistentes"
    )


def check_delivered_future(dfs):
    pedidos = dfs["pedidos"].copy()

    pedidos["fecha_entrega"] = pd.to_datetime(
        pedidos["fecha_entrega"],
        errors="coerce"
    )

    hoy = pd.Timestamp.now().normalize()

    errores = (
        (pedidos["estado"] == "entregado")
        &
        (pedidos["fecha_entrega"] > hoy)
    )

    return (
        not errores.any(),
        f"{errores.sum()} pedidos entregados con fecha futura"
    )


def check_stock(dfs):
    productos = dfs["productos"]
    lineas = dfs["lineas_pedido"]

    total = (
        lineas.groupby("producto_id")["cantidad"]
        .sum()
        .reset_index(name="cantidad_total")
    )

    merged = productos.merge(
        total,
        on="producto_id",
        how="left"
    )

    merged["cantidad_total"] = merged["cantidad_total"].fillna(0)

    errores = merged["cantidad_total"] > merged["stock"]

    return (
        not errores.any(),
        f"{errores.sum()} productos superan el stock"
    )


def check_registration_date(dfs):
    clientes = dfs["clientes"].copy()
    pedidos = dfs["pedidos"].copy()

    clientes["fecha_registro"] = pd.to_datetime(
        clientes["fecha_registro"],
        errors="coerce"
    )

    pedidos["fecha_pedido"] = pd.to_datetime(
        pedidos["fecha_pedido"],
        errors="coerce"
    )

    primer_pedido = (
        pedidos.groupby("cliente_id")["fecha_pedido"]
        .min()
        .reset_index(name="primer_pedido")
    )

    merged = clientes.merge(
        primer_pedido,
        on="cliente_id",
        how="left"
    )

    errores = (
        merged["primer_pedido"].notna()
        &
        (merged["fecha_registro"] > merged["primer_pedido"])
    )

    return (
        not errores.any(),
        f"{errores.sum()} clientes registrados después de comprar"
    )


# -------------------------------------------------------------------
# Dispatcher
# -------------------------------------------------------------------

CHECKS = {
    "total_check": check_total,
    "date_order_check": check_date_order,
    "delivered_future_check": check_delivered_future,
    "stock_check": check_stock,
    "registration_date_check": check_registration_date,
}


# -------------------------------------------------------------------
# Runner
# -------------------------------------------------------------------

def run_generated_tests(dfs, tests):

    resultados = []

    for test in tests:

        tipo = test.get("type")
        nombre = test.get("name", "Sin nombre")

        try:

            if tipo not in CHECKS:

                resultados.append({
                    "name": nombre,
                    "type": tipo,
                    "passed": False,
                    "detail": f"Tipo '{tipo}' no implementado"
                })

                continue

            passed, detail = CHECKS[tipo](dfs)

            resultados.append({
                "name": nombre,
                "type": tipo,
                "passed": passed,
                "detail": detail
            })

        except Exception as e:

            resultados.append({
                "name": nombre,
                "type": tipo,
                "passed": False,
                "detail": str(e)
            })

    return resultados