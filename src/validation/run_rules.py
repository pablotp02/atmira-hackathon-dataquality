import pandas as pd

def run_rules(df, rules):

    results = []

    for rule in rules:

        # ejemplo simple de reglas tipo texto
        if "no nulos" in rule.lower():
            col = rule.split(" ")[0]
            errors = df[df[col].isnull()]
            results.append({
                "rule": rule,
                "errors": len(errors)
            })

        elif "positivo" in rule.lower():
            col = rule.split(" ")[0]
            errors = df[df[col] <= 0]
            results.append({
                "rule": rule,
                "errors": len(errors)
            })

    return results