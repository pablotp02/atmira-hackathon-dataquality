import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from src.llm.generate_rules import generate_rules
from src.validation.run_rules import run_rules


def main():
    # 1. Dataset mock para pruebas
    df_mock = pd.DataFrame({
        "edad":   [20, 30, 40, None, 25],
        "precio": [10, 20, -5, 40, 50]   # precio negativo inyectado a mano
    })

    # 2. Envolver en diccionario con nombre de tabla
    dfs_dirty = {"mock": df_mock}

    # 3. Schema y transformacion simplificados para el mock
    schema = "tabla mock con columnas: edad (numerico, no puede ser nula), precio (numerico, debe ser positivo)"
    transformation = "validacion basica de calidad de datos: edad no puede ser nula, precio debe ser mayor que cero"

    # 4. LLM genera reglas
    print("Generando reglas con el LLM...")
    rules_json = generate_rules(schema, transformation)
    rules = rules_json["rules"]
    print(f"Reglas generadas: {len(rules)}")

    # 5. Validar dataset mock con las reglas generadas
    print("Validando dataset...")
    results = run_rules(dfs_dirty, rules)

    # 6. Mostrar resultados
    print("\n=== DATASET MOCK ===")
    print(df_mock)

    print("\n=== REGLAS GENERADAS ===")
    for rule in rules:
        print(f"  [{rule.get('type')}] {rule.get('tabla')}.{rule.get('column', '')} - {rule.get('descripcion', '')}")

    print("\n=== RESULTADOS VALIDACION ===")
    for r in results:
        estado = "FALLO" if r["errors"] > 0 else "OK"
        print(f"  [{estado}] {r['rule'].get('type')} - {r.get('detalle', '')}")


if __name__ == "__main__":
    main()