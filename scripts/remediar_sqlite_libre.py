"""
Script de remediación para SQLite perfumes.db:
Corrige el volumen de Falabella para YSL Libre:
- $86.990 corresponde a la botella de 30ml ($2.900/ml), no a la de 90ml.
- $176.990 corresponde a la botella de 90ml ($1.967/ml).
- $125.990 corresponde a la botella de 50ml.
- $157.990 corresponde a la botella de 100ml (recarga).
"""
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "APP")))
from backend.database import get_connection

def remediar_sqlite():
    conn = get_connection()
    c = conn.cursor()

    # 1. Obtener id de Falabella en tiendas
    c.execute("SELECT id FROM tiendas WHERE nombre = 'Falabella';")
    fal_row = c.fetchone()
    if not fal_row:
        print("Falabella no encontrada en tiendas")
        return
    fal_id = fal_row["id"]
    print(f"ID de Falabella en SQLite: {fal_id}")

    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 2. Corregir registros donde $86.990 fue incorrectamente asignado a 90ml
    c.execute("""
        UPDATE precios_registro
        SET volumen_ml = 30
        WHERE perfume_id = 2 
          AND tienda_id = ? 
          AND precio_actual = 86990 
          AND volumen_ml = 90;
    """, (fal_id,))
    modificados = c.rowcount
    print(f"Registros de Falabella corregidos a 30ml ($86.990): {modificados}")

    # 3. Insertar el precio real de 90ml ($176.990) si no existe en la fecha más reciente
    c.execute("""
        SELECT id FROM precios_registro
        WHERE perfume_id = 2 AND tienda_id = ? AND volumen_ml = 90 AND precio_actual = 176990;
    """, (fal_id,))
    if not c.fetchone():
        c.execute("""
            INSERT INTO precios_registro (perfume_id, tienda_id, precio_actual, precio_normal, en_stock, volumen_ml, url_producto, fecha_registro)
            VALUES (2, ?, 176990, 176990, 1, 90, 'https://www.falabella.com/falabella-cl/product/8472576/perfume-mujer-libre-edp-yves-saint-laurent', ?);
        """, (fal_id, ahora))
        print("Insertado registro real de 90ml ($176.990) para Falabella.")

    # 4. Insertar también 50ml y 100ml de Falabella
    c.execute("""
        SELECT id FROM precios_registro WHERE perfume_id = 2 AND tienda_id = ? AND volumen_ml = 50;
    """, (fal_id,))
    if not c.fetchone():
        c.execute("""
            INSERT INTO precios_registro (perfume_id, tienda_id, precio_actual, precio_normal, en_stock, volumen_ml, url_producto, fecha_registro)
            VALUES (2, ?, 125990, 125990, 1, 50, 'https://www.falabella.com/falabella-cl/product/8472576/perfume-mujer-libre-edp-yves-saint-laurent', ?);
        """, (fal_id, ahora))
        print("Insertado registro de 50ml ($125.990) para Falabella.")

    conn.commit()

    # 5. Verificar cómo responde obtener_precios_actuales desde SQLite
    print("\n=== VERIFICANDO OBTENER_PRECIOS_ACTUALES PARA YSL LIBRE EN SQLITE ===")
    c.execute("""
        SELECT t.nombre, pr.precio_actual, pr.precio_normal, pr.volumen_ml,
               ROUND(CAST(pr.precio_actual AS REAL) / pr.volumen_ml) as precio_por_ml
        FROM precios_registro pr
        JOIN tiendas t ON t.id = pr.tienda_id
        WHERE pr.perfume_id = 2
          AND pr.fecha_registro = (
              SELECT MAX(fecha_registro) FROM precios_registro
              WHERE perfume_id = 2 AND tienda_id = t.id AND ABS(volumen_ml - pr.volumen_ml) < 1
          )
        ORDER BY pr.volumen_ml ASC, pr.precio_actual ASC;
    """)
    for r in c.fetchall():
        print(f"  {r['nombre']:<16} | {r['volumen_ml']}ml | ${r['precio_actual']:,} | $/ml: ${r['precio_por_ml']:,}")

    conn.close()

if __name__ == "__main__":
    remediar_sqlite()
