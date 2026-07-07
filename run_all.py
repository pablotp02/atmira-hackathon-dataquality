"""
Pipeline completo end-to-end
Hackathon Atmira - Reto 03: Calidad del dato

Ejecuta todos los pasos del pipeline en orden:
  1. Generacion del dataset sintetico limpio
  2. Profiling del dataset
  3. Inyeccion de anomalias
  4. Generacion de reglas con el LLM
  5. Ejecucion de fixture tests (validacion de transformaciones)
  6. Validacion del dataset con las reglas
  7. Evaluacion de metricas

Uso:
  python run_all.py                  # seed fija (reproducible)
  python run_all.py --seed=123       # seed personalizada
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import json
import argparse
import pandas as pd
from datetime import datetime
from src.generator.generate_dataset import main as generar_dataset
from src.profiling.profile_dataset import main as generar_profiling
from src.generator.inject_anomalies import main as inyectar_anomalias
from src.llm.generate_rules import generate_rules
from src.validation.run_rules import run_rules
from src.evaluation.evaluation import evaluate, imprimir_metricas
from tests.fixture_runner import run_fixture_tests

DIRTY_DIR    = os.path.join(os.path.dirname(__file__), "data", "dirty")
HISTORY_PATH = os.path.join(os.path.dirname(__file__), "data", "rules_history.json")


def separador(titulo: str):
    print(f"\n{'=' * 60}")
    print(f"  {titulo}")
    print(f"{'=' * 60}")


def cargar_dfs(directorio: str) -> dict:
    return {
        "clientes":      pd.read_csv(os.path.join(directorio, "clientes.csv")),
        "productos":     pd.read_csv(os.path.join(directorio, "productos.csv")),
        "pedidos":       pd.read_csv(os.path.join(directorio, "pedidos.csv")),
        "lineas_pedido": pd.read_csv(os.path.join(directorio, "lineas_pedido.csv")),
    }


def actualizar_historial(seed: int, rules: list, metricas: dict):
    """Acumula las reglas generadas en cada ejecucion para analisis de estabilidad."""
    historial = []
    if os.path.exists(HISTORY_PATH):
        with open(HISTORY_PATH, "r", encoding="utf-8") as f:
            historial = json.load(f)

    historial.append({
        "timestamp":      datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "seed":           seed,
        "rule_types":     [r.get("type") for r in rules],
        "num_reglas":     len(rules),
        "tasa_deteccion": metricas["tasa_deteccion_tipos"],
    })

    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(historial, f, ensure_ascii=False, indent=2)

    print(f"Historial actualizado en data/rules_history.json ({len(historial)} ejecuciones registradas)")


def main(seed_dataset=42, seed_anomalias=99):
    modo = "reproducible (seed fija)" if seed_dataset == 42 else f"aleatorio (seed={seed_dataset})"

    # ── Paso 1: Generacion del dataset ───────────────────────────────────────
    separador("PASO 1 - Generacion del dataset sintetico")
    print(f"Modo: {modo}")
    generar_dataset(seed=seed_dataset)

    # ── Paso 2: Profiling ────────────────────────────────────────────────────
    separador("PASO 2 - Profiling del dataset")
    generar_profiling()

    # ── Paso 3: Inyeccion de anomalias ───────────────────────────────────────
    separador("PASO 3 - Inyeccion de anomalias")
    inyectar_anomalias(seed=seed_anomalias)

    # ── Paso 4: Generacion de reglas con el LLM ──────────────────────────────
    separador("PASO 4 - Generacion de reglas y validacion")

    dfs_dirty = cargar_dfs(DIRTY_DIR)

    log_path = os.path.join(DIRTY_DIR, "injection_log.json")
    with open(log_path, "r", encoding="utf-8") as f:
        injection_log = json.load(f)

    summary_path = os.path.join(
        os.path.dirname(__file__), "data", "profiling", "summary.json"
    )
    with open(summary_path, "r", encoding="utf-8") as f:
        summary = json.load(f)

    print("Generando reglas con el LLM...")
    schema = json.dumps(summary, ensure_ascii=False, indent=2)
    transformation = (
        "Transformacion 1 - Calculo del total del pedido: "
        "el campo 'total' en la tabla pedidos debe coincidir con la suma de "
        "(cantidad * precio_unitario) de sus lineas en lineas_pedido agrupadas por pedido_id. "
        "Transformacion 2 - Consistencia referencial: "
        "el campo 'precio_unitario' en lineas_pedido debe coincidir con el 'precio_unitario' "
        "del mismo producto en la tabla productos. "
        "Validaciones adicionales: emails con formato valido en clientes, "
        "precios y cantidades positivos, fechas de entrega posteriores a fechas de pedido, "
        "campos obligatorios sin nulos (estado, cliente_id, producto_id), "
        "pedidos en estado entregado no pueden tener fecha de entrega futura, "
        "cantidad total pedida de un producto no puede superar su stock disponible, "
        "fecha de registro del cliente no puede ser posterior a su primer pedido."
    )

    rules_json = generate_rules(schema, transformation)
    rules = rules_json["rules"]
    print(f"Reglas generadas: {len(rules)}")

    # Guardar reglas propuestas para revision human-in-the-loop
    rules_propuestas_path = os.path.join(os.path.dirname(__file__), "data", "rules_propuestas.json")
    with open(rules_propuestas_path, "w", encoding="utf-8") as f:
        json.dump(rules, f, ensure_ascii=False, indent=2)
    print("Reglas propuestas guardadas en data/rules_propuestas.json")

    # ── Paso 5: Fixture tests ─────────────────────────────────────────────────
    separador("PASO 5 - Fixture tests generados por el LLM")

    unit_tests        = rules_json.get("unit_tests", [])
    integration_tests = rules_json.get("integration_tests", [])
    edge_cases        = rules_json.get("edge_cases", [])
    uat_tests         = rules_json.get("uat_tests", [])

    todos_los_tests = unit_tests + integration_tests + edge_cases + uat_tests
    print(f"Tests generados: {len(todos_los_tests)} "
          f"(unit={len(unit_tests)}, integration={len(integration_tests)}, "
          f"edge={len(edge_cases)}, uat={len(uat_tests)})")

    fixture_results = run_fixture_tests(todos_los_tests)

    pasados    = sum(1 for r in fixture_results if r["passed"] is True)
    fallados   = sum(1 for r in fixture_results if r["passed"] is False)
    pendientes = sum(1 for r in fixture_results if r["passed"] is None)

    print(f"\nResultados fixture tests: {pasados} OK | {fallados} FALLO | {pendientes} pendientes")
    for r in fixture_results:
        estado = "OK" if r["passed"] is True else "FALLO" if r["passed"] is False else "PENDIENTE"
        print(f"  [{estado}] {r['name']} -> {r['detail']}")

    # ── Paso 6: Validacion del dataset ────────────────────────────────────────
    separador("PASO 6 - Validacion del dataset")

    print("Validando dataset...")
    results = run_rules(dfs_dirty, rules)

    results_con_fallos = [r for r in results if r["errors"] > 0]
    metricas = evaluate(injection_log, results_con_fallos)

    # ── Resultados ────────────────────────────────────────────────────────────
    separador("RESULTADOS")

    print("\nReglas generadas:")
    for rule in rules:
        print(f"  [{rule.get('type')}] {rule.get('tabla')}.{rule.get('column', '')} - {rule.get('descripcion', '')}")

    print("\nResultados de validacion:")
    for r in results:
        estado = "FALLO" if r["errors"] > 0 else "OK"
        print(f"  [{estado}] {r['rule'].get('type')} - {r.get('detalle', '')}")

    imprimir_metricas(metricas)

    # Guardar todo en results.json
    results_path = os.path.join(os.path.dirname(__file__), "data", "results.json")
    os.makedirs(os.path.dirname(results_path), exist_ok=True)
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump({
            "rules":              rules,
            "results":            results,
            "metricas":           metricas,
            "unit_tests":         unit_tests,
            "integration_tests":  integration_tests,
            "edge_cases":         edge_cases,
            "uat_tests":          uat_tests,
            "fixture_results":    fixture_results,
        }, f, ensure_ascii=False, indent=2)
    print("Resultados guardados en data/results.json")

    # Actualizar historial de reglas para analisis de estabilidad
    actualizar_historial(seed_dataset, rules, metricas)

    separador("PIPELINE COMPLETADO")
    print(f"  Modo: {modo}")
    print(f"  Tasa de deteccion final: {metricas['tasa_deteccion_tipos']}%")
    print(f"  Fixture tests: {pasados} OK | {fallados} FALLO | {pendientes} pendientes")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=None,
                        help="Seed para generacion aleatoria. Sin este argumento usa seeds fijas.")
    args = parser.parse_args()

    if args.seed is not None:
        main(seed_dataset=args.seed, seed_anomalias=args.seed + 1)
    else:
        main(seed_dataset=42, seed_anomalias=99)