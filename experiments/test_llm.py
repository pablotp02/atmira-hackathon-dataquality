from src.llm.generate_rules import generate_rules

schema = """
clientes(id, edad)
pedidos(id, cliente_id, total)
lineas_pedido(id, pedido_id, cantidad, precio_unitario)
"""

transformation = """
total_pedido = sum(cantidad * precio_unitario)
cliente_score = gasto_total + numero_compras
"""

rules = generate_rules(schema, transformation)

print(rules)
