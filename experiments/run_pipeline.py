import sys
import os
from src.llm.generate_rules import generate_rules
from src.evaluation.inject_errors import inject_errors
from src.validation.run_rules import run_rules
from src.evaluation.evaluation import evaluate
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd


def main():

    # 1. Dataset simple (puede ser mock por ahora)
    df = pd.DataFrame({
        "edad": [20, 30, 40, None, 25],
        "precio": [10, 20, 30, 40, 50]
    })

    # 2. Inyectar errores
    df_dirty = inject_errors(df)

    # 3. LLM genera reglas
    schema = "edad, precio"
    transformation = "validación básica de calidad de datos"

    rules_json = generate_rules(schema, transformation)
    rules = rules_json["rules"]

    # 4. Validar dataset
    results = run_rules(df_dirty, rules)

    # 5. Extraer errores detectados
    detected_errors = [r["rule"] for r in results if r["errors"] > 0]

    # 6. Métricas (simulación simple)
    injected_errors = ["edad_null", "precio_negativo"]

    metrics = evaluate(injected_errors, detected_errors)

    print("\n=== DATASET CON ERRORES ===")
    print(df_dirty)

    print("\n=== REGLAS GENERADAS ===")
    print(rules)

    print("\n=== RESULTADOS VALIDACIÓN ===")
    print(results)

    print("\n=== MÉTRICAS FINALES ===")
    print(metrics)


if __name__ == "__main__":
    main()