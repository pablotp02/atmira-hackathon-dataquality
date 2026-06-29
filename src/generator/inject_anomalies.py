"""
Modulo de inyeccion de anomalias en el dataset de e-commerce
Hackathon Atmira - Reto 03: Calidad del dato

Lee los 4 CSV limpios de data/raw/ e inyecta anomalias controladas.
Genera:
  - CSVs sucios en data/dirty/
  - Registro de anomalias en data/dirty/injection_log.json

El registro es la "verdad fundamental" que usara el modulo de evaluacion
para calcular que porcentaje de anomalias detecto el sistema.

Uso:
  python src/generator/inject_anomalies.py
"""

import os
import json
import random
import pandas as pd
from datetime import datetime, timedelta

# ── Configuracion ─────────────────────────────────────────────────────────────

SEED = 99
random.seed(SEED)

RAW_DIR   = os.path.join(os.path.dirname(__file__), "..", "..", "data", "raw")
DIRTY_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "dirty")

# Numero de anomalias a inyectar por tipo
NUM_ANOMALIAS = {
    "email_formato_invalido":         5,
    "precio_negativo":                5,
    "cantidad_cero":                  5,
    "nulo_en_campo_obligatorio":      5,
    "fecha_entrega_anterior_pedido":  5,
    "total_pedido_incorrecto":        5,
    "precio_linea_distinto_catalogo": 5,
    "pedido_entregado_fecha_futura":  5,
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def registrar(log: list, tipo: str, tabla: str, columna: str, fila_id: int,
              valor_original, valor_nuevo, descripcion: str):
    log.append({
        "tipo":             tipo,
        "tabla":            tabla,
        "columna":          columna,
        "fila_id":          fila_id,
        "valor_original":   str(valor_original),
        "valor_nuevo":      str(valor_nuevo),
        "descripcion":      descripcion,
    })


def ids_aleatorios(df: pd.DataFrame, id_col: str, n: int) -> list:
    return random.sample(df[id_col].tolist(), min(n, len(df)))


# ── Anomalias triviales (estadisticas) ───────────────────────────────────────

def inyectar_email_invalido(clientes: pd.DataFrame, log: list, n: int):
    """Email sin @ ni dominio valido."""
    ids = ids_aleatorios(clientes, "cliente_id", n)
    for cid in ids:
        idx = clientes[clientes["cliente_id"] == cid].index[0]
        original = clientes.at[idx, "email"]
        nuevo = original.replace("@", "").replace(".com", "").replace(".net", "").replace(".org", "")
        clientes.at[idx, "email"] = nuevo
        registrar(log, "email_formato_invalido", "clientes", "email", cid,
                  original, nuevo, "Email sin @ ni dominio valido")
    return clientes


def inyectar_precio_negativo(productos: pd.DataFrame, log: list, n: int):
    """Precio unitario negativo en productos."""
    ids = ids_aleatorios(productos, "producto_id", n)
    for pid in ids:
        idx = productos[productos["producto_id"] == pid].index[0]
        original = productos.at[idx, "precio_unitario"]
        nuevo = round(-abs(original), 2)
        productos.at[idx, "precio_unitario"] = nuevo
        registrar(log, "precio_negativo", "productos", "precio_unitario", pid,
                  original, nuevo, "Precio unitario negativo")
    return productos


def inyectar_cantidad_cero(lineas: pd.DataFrame, log: list, n: int):
    """Cantidad 0 en lineas de pedido."""
    ids = ids_aleatorios(lineas, "linea_id", n)
    for lid in ids:
        idx = lineas[lineas["linea_id"] == lid].index[0]
        original = lineas.at[idx, "cantidad"]
        lineas.at[idx, "cantidad"] = 0
        registrar(log, "cantidad_cero", "lineas_pedido", "cantidad", lid,
                  original, 0, "Cantidad 0 en linea de pedido")
    return lineas


def inyectar_nulo_obligatorio(pedidos: pd.DataFrame, log: list, n: int):
    """Estado nulo en pedidos (campo obligatorio)."""
    ids = ids_aleatorios(pedidos, "pedido_id", n)
    for pid in ids:
        idx = pedidos[pedidos["pedido_id"] == pid].index[0]
        original = pedidos.at[idx, "estado"]
        pedidos.at[idx, "estado"] = None
        registrar(log, "nulo_en_campo_obligatorio", "pedidos", "estado", pid,
                  original, None, "Campo obligatorio 'estado' con valor nulo")
    return pedidos


# ── Anomalias interesantes (contexto de negocio) ──────────────────────────────

def inyectar_fecha_entrega_anterior(pedidos: pd.DataFrame, log: list, n: int):
    """Fecha de entrega anterior a la fecha de pedido — imposible temporalmente."""
    ids = ids_aleatorios(pedidos, "pedido_id", n)
    for pid in ids:
        idx = pedidos[pedidos["pedido_id"] == pid].index[0]
        fecha_pedido_str = pedidos.at[idx, "fecha_pedido"]
        fecha_pedido = datetime.strptime(fecha_pedido_str, "%Y-%m-%d")
        dias_antes = random.randint(1, 15)
        nueva_fecha = (fecha_pedido - timedelta(days=dias_antes)).strftime("%Y-%m-%d")
        original = pedidos.at[idx, "fecha_entrega"]
        pedidos.at[idx, "fecha_entrega"] = nueva_fecha
        registrar(log, "fecha_entrega_anterior_pedido", "pedidos", "fecha_entrega", pid,
                  original, nueva_fecha,
                  f"Fecha de entrega ({nueva_fecha}) anterior a fecha de pedido ({fecha_pedido_str})")
    return pedidos


def inyectar_total_incorrecto(pedidos: pd.DataFrame, log: list, n: int):
    """Total del pedido que no coincide con la suma de sus lineas — error de transformacion."""
    ids = ids_aleatorios(pedidos, "pedido_id", n)
    for pid in ids:
        idx = pedidos[pedidos["pedido_id"] == pid].index[0]
        original = pedidos.at[idx, "total"]
        # Alteramos el total entre un 10% y un 40% del valor real
        factor = random.uniform(0.6, 0.9)
        nuevo = round(original * factor, 2)
        pedidos.at[idx, "total"] = nuevo
        registrar(log, "total_pedido_incorrecto", "pedidos", "total", pid,
                  original, nuevo,
                  f"Total del pedido modificado ({original} -> {nuevo}). "
                  f"No coincide con la suma de sus lineas.")
    return pedidos


def inyectar_precio_linea_distinto(lineas: pd.DataFrame, productos: pd.DataFrame,
                                    log: list, n: int):
    """Precio en linea_pedido distinto al precio del catalogo — inconsistencia referencial."""
    ids = ids_aleatorios(lineas, "linea_id", n)
    for lid in ids:
        idx = lineas[lineas["linea_id"] == lid].index[0]
        pid = lineas.at[idx, "producto_id"]
        precio_catalogo = productos.loc[productos["producto_id"] == pid, "precio_unitario"].values[0]
        original = lineas.at[idx, "precio_unitario"]
        # Precio distinto al catalogo (multiplicamos por un factor aleatorio)
        factor = random.choice([0.5, 1.5, 2.0, 0.25])
        nuevo = round(precio_catalogo * factor, 2)
        lineas.at[idx, "precio_unitario"] = nuevo
        registrar(log, "precio_linea_distinto_catalogo", "lineas_pedido", "precio_unitario", lid,
                  original, nuevo,
                  f"Precio en linea ({nuevo}) distinto al catalogo ({precio_catalogo}) "
                  f"para producto_id={pid}. Sin descuento registrado.")
    return lineas


def inyectar_entregado_fecha_futura(pedidos: pd.DataFrame, log: list, n: int):
    """Pedido en estado 'entregado' con fecha de entrega en el futuro."""
    # Solo pedidos en estado 'entregado'
    candidatos = pedidos[pedidos["estado"] == "entregado"]["pedido_id"].tolist()
    ids = random.sample(candidatos, min(n, len(candidatos)))
    fecha_futura_base = datetime(2026, 1, 1)

    for pid in ids:
        idx = pedidos[pedidos["pedido_id"] == pid].index[0]
        original = pedidos.at[idx, "fecha_entrega"]
        dias = random.randint(30, 180)
        nueva_fecha = (fecha_futura_base + timedelta(days=dias)).strftime("%Y-%m-%d")
        pedidos.at[idx, "fecha_entrega"] = nueva_fecha
        registrar(log, "pedido_entregado_fecha_futura", "pedidos", "fecha_entrega", pid,
                  original, nueva_fecha,
                  f"Pedido marcado como 'entregado' pero fecha_entrega ({nueva_fecha}) es futura")
    return pedidos


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    os.makedirs(DIRTY_DIR, exist_ok=True)

    print("Cargando dataset limpio...")
    clientes  = pd.read_csv(os.path.join(RAW_DIR, "clientes.csv"))
    productos = pd.read_csv(os.path.join(RAW_DIR, "productos.csv"))
    pedidos   = pd.read_csv(os.path.join(RAW_DIR, "pedidos.csv"))
    lineas    = pd.read_csv(os.path.join(RAW_DIR, "lineas_pedido.csv"))

    log = []

    print("Inyectando anomalias triviales...")
    clientes  = inyectar_email_invalido(clientes, log, NUM_ANOMALIAS["email_formato_invalido"])
    productos = inyectar_precio_negativo(productos, log, NUM_ANOMALIAS["precio_negativo"])
    lineas    = inyectar_cantidad_cero(lineas, log, NUM_ANOMALIAS["cantidad_cero"])
    pedidos   = inyectar_nulo_obligatorio(pedidos, log, NUM_ANOMALIAS["nulo_en_campo_obligatorio"])

    print("Inyectando anomalias de contexto de negocio...")
    pedidos = inyectar_fecha_entrega_anterior(pedidos, log, NUM_ANOMALIAS["fecha_entrega_anterior_pedido"])
    pedidos = inyectar_total_incorrecto(pedidos, log, NUM_ANOMALIAS["total_pedido_incorrecto"])
    lineas  = inyectar_precio_linea_distinto(lineas, productos, log, NUM_ANOMALIAS["precio_linea_distinto_catalogo"])
    pedidos = inyectar_entregado_fecha_futura(pedidos, log, NUM_ANOMALIAS["pedido_entregado_fecha_futura"])

    print("Guardando CSVs sucios...")
    clientes.to_csv(os.path.join(DIRTY_DIR, "clientes.csv"), index=False)
    productos.to_csv(os.path.join(DIRTY_DIR, "productos.csv"), index=False)
    pedidos.to_csv(os.path.join(DIRTY_DIR, "pedidos.csv"), index=False)
    lineas.to_csv(os.path.join(DIRTY_DIR, "lineas_pedido.csv"), index=False)

    # Guardar registro de anomalias
    registro = {
        "descripcion": (
            "Registro de anomalias inyectadas en el dataset. "
            "Cada entrada representa un error introducido de forma controlada. "
            "Este archivo es la verdad fundamental para el modulo de evaluacion."
        ),
        "total_anomalias": len(log),
        "anomalias_por_tipo": {},
        "detalle": log,
    }

    for entrada in log:
        tipo = entrada["tipo"]
        registro["anomalias_por_tipo"][tipo] = registro["anomalias_por_tipo"].get(tipo, 0) + 1

    ruta_log = os.path.join(DIRTY_DIR, "injection_log.json")
    with open(ruta_log, "w", encoding="utf-8") as f:
        json.dump(registro, f, ensure_ascii=False, indent=2)

    print("\nDataset sucio generado en data/dirty/")
    print(f"Total de anomalias inyectadas: {len(log)}")
    print("\nDesglose por tipo:")
    for tipo, cantidad in registro["anomalias_por_tipo"].items():
        print(f"  {tipo}: {cantidad}")
    print(f"\nRegistro guardado en: {ruta_log}")


if __name__ == "__main__":
    main()