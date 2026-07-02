"""
Dataset sintético de e-commerce — Generador de datos limpios
Hackathon Atmira — Reto 03: Calidad del dato

Genera 4 CSV en data/raw/:
  - clientes.csv
  - productos.csv
  - pedidos.csv
  - lineas_pedido.csv

Uso:
  python src/generator/generate_dataset.py
"""

import os
import random
import pandas as pd
from faker import Faker
from datetime import datetime, timedelta

# ── Configuración ────────────────────────────────────────────────────────────

SEED = 42
random.seed(SEED)

fake = Faker("es_ES")
fake.seed_instance(SEED)

NUM_CLIENTES      = 200
NUM_PRODUCTOS     = 50
NUM_PEDIDOS       = 500
MIN_LINEAS        = 1
MAX_LINEAS        = 6   # líneas por pedido
FECHA_INICIO      = datetime(2023, 1, 1)
FECHA_FIN         = datetime(2024, 12, 1)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "raw")

# ── Helpers ──────────────────────────────────────────────────────────────────

def fecha_aleatoria(inicio: datetime, fin: datetime) -> datetime:
    delta = fin - inicio
    return inicio + timedelta(days=random.randint(0, delta.days))


def redondear(valor: float) -> float:
    return round(valor, 2)


# ── Generadores ──────────────────────────────────────────────────────────────

def generar_clientes(n: int) -> pd.DataFrame:
    registros = []
    emails_usados = set()

    for i in range(1, n + 1):
        while True:
            email = fake.email()
            if email not in emails_usados:
                emails_usados.add(email)
                break

        fecha_nac = fake.date_of_birth(minimum_age=18, maximum_age=80)
        fecha_reg = fecha_aleatoria(FECHA_INICIO, FECHA_FIN)

        registros.append({
            "cliente_id":       i,
            "nombre":           fake.name(),
            "email":            email,
            "fecha_registro":   fecha_reg.strftime("%Y-%m-%d"),
            "pais":             random.choice(["ES", "ES", "ES", "MX", "AR", "CO"]),
            "fecha_nacimiento": fecha_nac.strftime("%Y-%m-%d"),
        })

    return pd.DataFrame(registros)


def generar_productos(n: int) -> pd.DataFrame:
    categorias = {
        "Electrónica":    (50,   1500),
        "Ropa":           (10,   120),
        "Hogar":          (15,   400),
        "Deportes":       (20,   300),
        "Alimentación":   (2,    80),
        "Libros":         (5,    60),
        "Juguetes":       (8,    150),
    }

    nombres_por_cat = {
        "Electrónica":  ["Auriculares BT", "Teclado mecánico", "Ratón gaming",
                         "Monitor 24\"", "Webcam HD", "SSD 1TB", "Hub USB-C",
                         "Altavoz portátil", "Tablet 10\"", "Cargador rápido"],
        "Ropa":         ["Camiseta básica", "Pantalón vaquero", "Sudadera", "Zapatillas",
                         "Chaqueta impermeable", "Calcetines pack 5", "Gorra visera"],
        "Hogar":        ["Lámpara escritorio", "Funda nórdica", "Set sartenes",
                         "Organizador cajones", "Humidificador", "Difusor aromas"],
        "Deportes":     ["Esterilla yoga", "Mancuernas 5kg", "Cuerda saltar",
                         "Botella térmica", "Banda resistencia", "Rodillo espuma"],
        "Alimentación": ["Café molido 500g", "Aceite oliva 1L", "Miel 350g",
                         "Proteína whey 1kg", "Té verde 100 sobres"],
        "Libros":       ["Python para todos", "Clean Code", "El Quijote",
                         "Hábitos atómicos", "Sapiens"],
        "Juguetes":     ["Puzzle 1000 piezas", "LEGO City", "Muñeca articulada",
                         "Coche teledirigido", "Set construcción madera"],
    }

    registros = []
    prod_id = 1

    for cat, (precio_min, precio_max) in categorias.items():
        nombres = nombres_por_cat[cat]
        num = max(1, round(n * (1 / len(categorias))))
        for j in range(num):
            nombre = nombres[j % len(nombres)]
            if j >= len(nombres):
                nombre += f" v{j // len(nombres) + 2}"
            registros.append({
                "producto_id":     prod_id,
                "nombre":          nombre,
                "categoria":       cat,
                "precio_unitario": redondear(random.uniform(precio_min, precio_max)),
                "stock":           random.randint(0, 200),
            })
            prod_id += 1
            if prod_id > n:
                break
        if prod_id > n:
            break

    # Rellenar hasta n si faltan
    while len(registros) < n:
        cat = random.choice(list(categorias.keys()))
        precio_min, precio_max = categorias[cat]
        registros.append({
            "producto_id":     prod_id,
            "nombre":          f"Producto extra {prod_id}",
            "categoria":       cat,
            "precio_unitario": redondear(random.uniform(precio_min, precio_max)),
            "stock":           random.randint(0, 200),
        })
        prod_id += 1

    return pd.DataFrame(registros[:n])


def generar_pedidos_y_lineas(
    clientes: pd.DataFrame,
    productos: pd.DataFrame,
    num_pedidos: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:

    estados = ["pendiente", "enviado", "entregado", "cancelado"]
    pesos_estado = [0.10, 0.20, 0.60, 0.10]

    pedidos_rows    = []
    lineas_rows     = []
    linea_id        = 1

    for pedido_id in range(1, num_pedidos + 1):
        cliente_id   = random.choice(clientes["cliente_id"].tolist())
        fecha_pedido = fecha_aleatoria(FECHA_INICIO, FECHA_FIN)
        estado       = random.choices(estados, weights=pesos_estado, k=1)[0]

        # Fecha de entrega: siempre POSTERIOR a la fecha de pedido (dataset limpio)
        dias_entrega = random.randint(1, 30)
        fecha_entrega = fecha_pedido + timedelta(days=dias_entrega)

        # Generar líneas de este pedido
        num_lineas    = random.randint(MIN_LINEAS, MAX_LINEAS)
        prods_pedido  = productos.sample(n=min(num_lineas, len(productos)), random_state=pedido_id)
        total_pedido  = 0.0

        for _, prod in prods_pedido.iterrows():
            cantidad       = random.randint(1, 5)
            precio_linea   = prod["precio_unitario"]  # precio real del catálogo
            subtotal       = redondear(cantidad * precio_linea)
            total_pedido  += subtotal

            lineas_rows.append({
                "linea_id":        linea_id,
                "pedido_id":       pedido_id,
                "producto_id":     prod["producto_id"],
                "cantidad":        cantidad,
                "precio_unitario": precio_linea,
            })
            linea_id += 1

        pedidos_rows.append({
            "pedido_id":     pedido_id,
            "cliente_id":    cliente_id,
            "fecha_pedido":  fecha_pedido.strftime("%Y-%m-%d"),
            "fecha_entrega": fecha_entrega.strftime("%Y-%m-%d"),
            "estado":        estado,
            "total":         redondear(total_pedido),
        })

    return pd.DataFrame(pedidos_rows), pd.DataFrame(lineas_rows)


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("Generando clientes...")
    clientes = generar_clientes(NUM_CLIENTES)

    print("Generando productos...")
    productos = generar_productos(NUM_PRODUCTOS)

    print("Generando pedidos y líneas de pedido...")
    pedidos, lineas = generar_pedidos_y_lineas(clientes, productos, NUM_PEDIDOS)

    # Guardar CSVs
    clientes.to_csv(os.path.join(OUTPUT_DIR, "clientes.csv"), index=False)
    productos.to_csv(os.path.join(OUTPUT_DIR, "productos.csv"), index=False)
    pedidos.to_csv(os.path.join(OUTPUT_DIR, "pedidos.csv"), index=False)
    lineas.to_csv(os.path.join(OUTPUT_DIR, "lineas_pedido.csv"), index=False)

    # Resumen
    print("\n Dataset generado correctamente en data/raw/")
    print(f"   clientes.csv      → {len(clientes)} filas")
    print(f"   productos.csv     → {len(productos)} filas")
    print(f"   pedidos.csv       → {len(pedidos)} filas")
    print(f"   lineas_pedido.csv → {len(lineas)} filas")

    # Validación rápida: comprobad que los totales cuadran (dataset limpio = 0 errores)
    lineas_agg = (
        lineas.groupby("pedido_id")
        .apply(lambda df: (df["cantidad"] * df["precio_unitario"]).sum(), include_groups=False)
        .reset_index(name="total_calculado")
    )
    merged = pedidos.merge(lineas_agg, on="pedido_id")
    merged["diferencia"] = (merged["total"] - merged["total_calculado"]).abs()
    errores = merged[merged["diferencia"] > 0.01]

    if errores.empty:
        print("\n Validación interna: todos los totales de pedido cuadran con sus líneas.")
    else:
        print(f"\n Hay {len(errores)} pedidos con total inconsistente (no debería ocurrir en el dataset limpio).")


if __name__ == "__main__":
    main()