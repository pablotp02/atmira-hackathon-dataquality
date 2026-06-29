def run_rules(df, rules):

    results = []

    for rule in rules:

        field = rule["field"]
        condition = rule["condition"]

        if ">=" in condition:
            value = float(condition.split(">=")[1])
            errors = df[df[field] < value]

        elif "<=" in condition:
            value = float(condition.split("<=")[1])
            errors = df[df[field] > value]

        else:
            errors = []

        results.append({
            "rule": rule,
            "errors": len(errors)
        })

    return results