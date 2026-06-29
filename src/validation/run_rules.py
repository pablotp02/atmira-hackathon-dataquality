def run_rules(df, rules):

    results = []

    for rule in rules:

        # RULE ES DICT → NO STRING
        rule_type = rule.get("type")
        column = rule.get("column")

        if rule_type == "null_check":
            errors = df[df[column].isnull()]
            results.append({
                "rule": rule,
                "errors": len(errors)
            })

        elif rule_type == "positive_check":
            errors = df[df[column] <= 0]
            results.append({
                "rule": rule,
                "errors": len(errors)
            })

    return results