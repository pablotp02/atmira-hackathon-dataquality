import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import pandas as pd
from src.llm.generate_rules import generate_rules
from src.validation.run_rules import run_rules

RAW_DIR   = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
DIRTY_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "dirty")


def cargar_dfs(directorio):
    return {
        "clientes":      pd.read_csv(os.path.join(directorio, "clientes.csv")),
        "productos":     pd.read_csv(os.path.join(directorio, "productos.csv")),
        "pedidos":       pd.read_csv(os.path.join(directorio, "pedidos.csv")),
        "lineas_pedido": pd.read_csv(os.path.join(directorio, "lineas_pedido.csv")),
    }


def main():
    # 1. Cargar dataset sucio (con anomalias inyectadas)
    print("Cargando dataset...")
    dfs_dirty = cargar_dfs(DIRTY_DIR)

    # 2. Cargar log de anomalias inyectadas (verdad fundamental)
    log_path = os.path.join(DIRTY_DIR, "injection_log.json")
    with open(log_path, "r", encoding="utf-8") as f:
        injection_log = json.load(f)

    total_inyectadas = injection_log["total_anomalias"]
    print(f"Anomalias inyectadas: {total_inyectadas}")

    # 3. Cargar perfil del dataset para el LLM
    summary_path = os.path.join(
        os.path.dirname(__file__), "..", "data", "profiling", "summary.json"
    )
    with open(summary_path, "r", encoding="utf-8") as f:
        summary = json.load(f)

    # 4. LLM genera reglas a partir del perfil y la descripcion de transformaciones
    print("Generando reglas con el LLM...")
    schema = json.dumps(summary, ensure_ascii=False, indent=2)
    transformation = (
        "Transformacion 1 — Calculo del total del pedido: "
        "el campo 'total' en la tabla pedidos debe coincidir con la suma de "
        "(cantidad * precio_unitario) de sus lineas en lineas_pedido agrupadas por pedido_id. "
        "Transformacion 2 — Consistencia referencial: "
        "el campo 'precio_unitario' en lineas_pedido debe coincidir con el 'precio_unitario' "
        "del mismo producto en la tabla productos. "
        "Validaciones adicionales: emails con formato valido en clientes, "
        "precios y cantidades positivos, fechas de entrega posteriores a fechas de pedido, "
        "campos obligatorios sin nulos (estado, cliente_id, producto_id)."
    )

    rules_json = generate_rules(schema, transformation)
    rules = rules_json["rules"]
    print(f"Reglas generadas: {len(rules)}")

    # 5. Validar dataset sucio con las reglas generadas
    print("Validando dataset...")
    results = run_rules(dfs_dirty, rules)

    # 6. Separar resultados con errores
    results_con_fallos = [r for r in results if r["errors"] > 0]
    results_ok         = [r for r in results if r["errors"] == 0]

    # 7. Mostrar resultados
    print("\n=== REGLAS GENERADAS ===")
    for rule in rules:
        print(f"  [{rule.get('type')}] {rule.get('tabla')}.{rule.get('column', '')} - {rule.get('descripcion', '')}")

    print("\n=== RESULTADOS VALIDACION ===")
    for r in results:
        estado = "FALLO" if r["errors"] > 0 else "OK"
        print(f"  [{estado}] {r['rule'].get('type')} - {r.get('detalle', '')}")

    print("\n=== RESUMEN ===")
    print(f"  Total reglas aplicadas:  {len(results)}")
    print(f"  Reglas con fallos:       {len(results_con_fallos)}")
    print(f"  Reglas sin fallos:       {len(results_ok)}")
    print(f"  Anomalias inyectadas:    {total_inyectadas}")
    print(f"  Tipos detectados:        {len(results_con_fallos)}")


if __name__ == "__main__":
    main()