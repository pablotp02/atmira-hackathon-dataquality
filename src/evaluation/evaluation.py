# src/evaluation/evaluation.py

def evaluate(injected_errors, detected_errors):
    """
    injected_errors: lista de errores reales que has metido
    detected_errors: lista de errores que el sistema ha encontrado
    """

    injected_set = set(injected_errors)
    detected_set = set(detected_errors)

    true_positives = injected_set.intersection(detected_set)

    recall = len(true_positives) / len(injected_set) if injected_set else 0

    precision = len(true_positives) / len(detected_set) if detected_set else 0

    return {
        "recall": recall,
        "precision": precision,
        "true_positives": len(true_positives),
        "injected": len(injected_set),
        "detected": len(detected_set)
    }