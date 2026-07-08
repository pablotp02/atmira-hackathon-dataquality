import pandas as pd


def run_rules(dfs, rules):
    """
    Aplica las reglas generadas por el LLM sobre los DataFrames del dataset.

    dfs: diccionario con los DataFrames por nombre de tabla
    rules: lista de reglas generadas por el LLM

    Tipos de regla soportados:
      - null_check
      - positive_check
      - email_check
      - date_order_check
      - delivered_future_check
      - total_check
      - stock_check
    """
    results = []

    # Tipos que requieren campo 'column' para funcionar
    TIPOS_CON_COLUMNA = {"null_check", "positive_check", "email_check"}

    for rule in rules:
        rule_type = rule.get("type")
        column    = rule.get("column")
        tabla     = rule.get("tabla")

        # Ignorar reglas con columna nula cuando el tipo la requiere
        if rule_type in TIPOS_CON_COLUMNA and not column:
            results.append({
                "rule":    rule,
                "errors":  0,
                "detalle": f"Regla ignorada: tipo '{rule_type}' requiere 'column' pero no se especifico",
            })
            continue

        df = dfs.get(tabla)
        if df is None and rule_type not in ("total_check", "stock_check"):
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

        elif rule_type == "delivered_future_check":
            df_temp = df.copy()
            df_temp["fecha_entrega"] = pd.to_datetime(df_temp["fecha_entrega"], errors="coerce")
            fecha_referencia = pd.Timestamp("2025-01-01")
            mask = (df_temp["estado"] == "entregado") & (df_temp["fecha_entrega"] >= fecha_referencia)
            errores = int(mask.sum())
            detalle = (
                f"{errores} pedidos en estado 'entregado' con fecha_entrega "
                f"a partir de {fecha_referencia.date()}"
            )

        elif rule_type == "total_check":
            pedidos = dfs["pedidos"]
            lineas  = dfs["lineas_pedido"]
            calculado = (
                lineas.assign(subtotal=lineas["cantidad"] * lineas["precio_unitario"])
                .groupby("pedido_id")["subtotal"]
                .sum()
                .reset_index()
            )
            merged  = pedidos.merge(calculado, on="pedido_id")
            errores = int((abs(merged["total"] - merged["subtotal"]) > 0.01).sum())
            detalle = f"{errores} pedidos cuyo total no coincide con la suma de sus lineas"

        elif rule_type == "stock_check":
            productos = dfs["productos"]
            lineas    = dfs["lineas_pedido"]
            total_por_producto = (
                lineas.groupby("producto_id")["cantidad"]
                .sum()
                .reset_index(name="total_pedido")
            )
            merged  = productos.merge(total_por_producto, on="producto_id", how="left")
            merged["total_pedido"] = merged["total_pedido"].fillna(0)
            errores = int((merged["total_pedido"] > merged["stock"]).sum())
            detalle = f"{errores} productos con cantidad total pedida superior al stock disponible"


        elif rule_type == "outlier_check":
            column   = rule.get("column", "precio_unitario")
            group_by = rule.get("group_by", "categoria")
            tabla_productos = dfs.get("productos")
            if tabla_productos is None:
                detalle = "Tabla 'productos' no encontrada"
            else:
                df_temp = tabla_productos.copy()
                # Calcular stats solo con precios positivos para evitar que
                # anomalias de precio_negativo distorsionen la media y std
                df_positivos = df_temp[df_temp[column] > 0]
                stats = (
                    df_positivos.groupby(group_by)[column]
                    .agg(["mean", "std"])
                    .reset_index()
                )
                stats.columns = [group_by, "media", "std"]
                df_merged = df_temp.merge(stats, on=group_by)
                df_merged["std"] = df_merged["std"].fillna(0)
                mask = (
                    (df_merged["std"] > 0) &
                    (df_merged[column] > 0) &
                    (abs(df_merged[column] - df_merged["media"]) > 2 * df_merged["std"])
                )
                errores = int(mask.sum())
                detalle = (
                    f"{errores} productos con {column} fuera de 3 desviaciones estandar "
                    f"para su {group_by}"
                )    
        else:
            detalle = f"Tipo de regla '{rule_type}' no soportado por el motor actual"

        results.append({
            "rule":    rule,
            "errors":  errores,
            "detalle": detalle,
        })

    return results