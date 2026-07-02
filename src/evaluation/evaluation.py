"""
Modulo de evaluacion de deteccion de anomalias
Hackathon Atmira - Reto 03: Calidad del dato

Cruza los resultados de run_rules con el injection_log.json
para calcular metricas de deteccion.

Uso:
  from src.evaluation.evaluation import evaluate
"""

# Mapeo entre tipos de anomalia inyectada y tipos de regla que las detectan
MAPEO_ANOMALIA_REGLA = {
    "email_formato_invalido":         ["email_check"],
    "precio_negativo":                ["positive_check"],
    "cantidad_cero":                  ["positive_check"],
    "nulo_en_campo_obligatorio":      ["null_check"],
    "fecha_entrega_anterior_pedido":  ["date_order_check"],
    "total_pedido_incorrecto":        ["total_check"],
    "precio_linea_distinto_catalogo": ["total_check"],
    "pedido_entregado_fecha_futura":  ["delivered_future_check"],  # antes no detectado
}


def evaluate(injection_log: dict, results: list) -> dict:
    """
    Calcula metricas de deteccion comparando anomalias inyectadas con resultados.

    injection_log: contenido del archivo data/dirty/injection_log.json
    results: lista de resultados devuelta por run_rules (solo los que tienen errors > 0)

    Devuelve un diccionario con:
      - total_inyectadas: numero total de anomalias inyectadas
      - tipos_inyectados: tipos de anomalia inyectados y cuantas de cada uno
      - tipos_detectados: tipos de anomalia que el sistema detecto
      - tipos_no_detectados: tipos de anomalia que el sistema no detecto
      - deteccion_por_tipo: detalle de si cada tipo fue detectado o no
      - tasa_deteccion_tipos: porcentaje de tipos detectados sobre total inyectados
      - errores_detectados_total: suma de errores encontrados por run_rules
    """

    # Tipos de regla que detectaron al menos un error
    reglas_con_fallo = set(r["rule"].get("type") for r in results if r["errors"] > 0)

    # Tipos de anomalia inyectados
    tipos_inyectados = injection_log.get("anomalias_por_tipo", {})

    deteccion_por_tipo = {}
    tipos_detectados     = []
    tipos_no_detectados  = []

    for tipo_anomalia, cantidad in tipos_inyectados.items():
        reglas_esperadas = MAPEO_ANOMALIA_REGLA.get(tipo_anomalia, [])
        detectado = any(regla in reglas_con_fallo for regla in reglas_esperadas)

        deteccion_por_tipo[tipo_anomalia] = {
            "cantidad_inyectada": cantidad,
            "reglas_esperadas":   reglas_esperadas,
            "detectado":          detectado,
        }

        if detectado:
            tipos_detectados.append(tipo_anomalia)
        else:
            tipos_no_detectados.append(tipo_anomalia)

    total_tipos    = len(tipos_inyectados)
    num_detectados = len(tipos_detectados)
    tasa_deteccion = round((num_detectados / total_tipos) * 100, 1) if total_tipos > 0 else 0.0

    errores_totales = sum(r["errors"] for r in results if r["errors"] > 0)

    return {
        "total_inyectadas":        injection_log.get("total_anomalias", 0),
        "tipos_inyectados":        tipos_inyectados,
        "tipos_detectados":        tipos_detectados,
        "tipos_no_detectados":     tipos_no_detectados,
        "deteccion_por_tipo":      deteccion_por_tipo,
        "tasa_deteccion_tipos":    tasa_deteccion,
        "errores_detectados_total": errores_totales,
    }


def imprimir_metricas(metricas: dict):
    """
    Imprime las metricas de evaluacion de forma legible.
    """
    print("\n=== METRICAS DE EVALUACION ===")
    print(f"  Anomalias inyectadas:      {metricas['total_inyectadas']}")
    print(f"  Errores detectados:        {metricas['errores_detectados_total']}")
    print(f"  Tipos inyectados:          {len(metricas['tipos_inyectados'])}")
    print(f"  Tipos detectados:          {len(metricas['tipos_detectados'])}")
    print(f"  Tipos no detectados:       {len(metricas['tipos_no_detectados'])}")
    print(f"  Tasa de deteccion:         {metricas['tasa_deteccion_tipos']}%")

    print("\n  Detalle por tipo:")
    for tipo, detalle in metricas["deteccion_por_tipo"].items():
        estado = "DETECTADO" if detalle["detectado"] else "NO DETECTADO"
        print(f"    [{estado}] {tipo} ({detalle['cantidad_inyectada']} anomalias)")

    if metricas["tipos_no_detectados"]:
        print("\n  Tipos no detectados (oportunidades de mejora):")
        for tipo in metricas["tipos_no_detectados"]:
            print(f"    - {tipo}")