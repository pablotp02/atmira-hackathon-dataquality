import pandas as pd


def run_rules(dfs, rules):
    """
    Aplica las reglas generadas por el LLM sobre los DataFrames del dataset.

    dfs: diccionario con los DataFrames por nombre de tabla
         ej. {"pedidos": df_pedidos, "clientes": df_clientes, ...}
    rules: lista de reglas generadas por el LLM
    """
    results = []

    for rule in rules:
        rule_type   = rule.get("type")
        column      = rule.get("column")
        tabla       = rule.get("tabla")
        descripcion = rule.get("descripcion", "")

        df = dfs.get(tabla)
        if df is None:
            results.append({
                "rule":    rule,
                "errors":  0,
                "detalle": f"Tabla '{tabla}' no encontrada"
            })
            continue

        errores = 0
        detalle = ""

        if rule_type == "null_check":
            errores = int(df[column].isnull().sum())
            detalle = f"{errores} filas con nulo en '{column}'"

        elif rule_type == "positive_check":
            errores = int((df[column] <= 0).sum())
            detalle = f"{errores} filas con valor <= 0 en '{column}'"

        elif rule_type == "email_check":
            patron = r"^[^@]+@[^@]+\.[^@]+"
            invalidos = df[~df[column].astype(str).str.match(patron)]
            errores = len(invalidos)
            detalle = f"{errores} emails con formato invalido en '{column}'"

        elif rule_type == "date_order_check":
            col_after  = rule.get("column_after")
            col_before = rule.get("column_before")
            df_temp = df.copy()
            df_temp[col_after]  = pd.to_datetime(df_temp[col_after],  errors="coerce")
            df_temp[col_before] = pd.to_datetime(df_temp[col_before], errors="coerce")
            errores = int((df_temp[col_after] < df_temp[col_before]).sum())
            detalle = f"{errores} filas donde '{col_after}' es anterior a '{col_before}'"

        elif rule_type == "total_check":
            df_lineas = dfs.get("lineas_pedido")
            if df_lineas is None:
                detalle = "Tabla 'lineas_pedido' no encontrada"
            else:
                totales = (
                    df_lineas.groupby("pedido_id")
                    .apply(lambda x: (x["cantidad"] * x["precio_unitario"]).sum(), include_groups=False)
                    .reset_index(name="total_calculado")
                )
                merged = df.merge(totales, on="pedido_id")
                errores = int((abs(merged["total"] - merged["total_calculado"]) > 0.01).sum())
                detalle = f"{errores} pedidos cuyo total no coincide con la suma de sus lineas"

        else:
            detalle = f"Tipo de regla '{rule_type}' no soportado"

        results.append({
            "rule":    rule,
            "errors":  errores,
            "detalle": detalle,
        })

    return results