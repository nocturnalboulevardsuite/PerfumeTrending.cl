"""
Script para agregar perfumes trending de alta demanda al catálogo.
Sincroniza tanto Supabase Cloud como SQLite local para garantizar paridad.
"""
# Importación de librería estándar o dependencia externa (sys)
import sys
# Importación de librería estándar o dependencia externa (os)
import os

# Asegurar path de imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "APP")))

# Importación de componentes (get_supabase, is_supabase_disponible, get_connection) desde el módulo 'backend.database'
from backend.database import get_supabase, is_supabase_disponible, get_connection

# Asignamos 'NUEVOS_PERFUMES' con [{'nombre': '9 PM', 'marca': 'Afnan', 'gen...
NUEVOS_PERFUMES = [
    # Configuración de elemento #1 (nombre='9 PM', marca='Afnan')
    {
        "nombre": "9 PM",
        "marca": "Afnan",
        "genero": "Hombre",
        "tipo": "Eau de Parfum",
        "notas": "Manzana, Canela, Lavanda Silvestre, Bergamota, Flor de Naranjo, Vainilla, Haba Tonka, Ámbar, Pachulí",
        "imagen_url": "https://images.falabella.com/v3/assets/blt088e6ed3cf8a7e92/bltfaeb16422204c3e5/6504a7372aa0631c77f0c137/124368276_1.jpg",
        "es_arabe": True,
        "en_tendencia": True,
        "en_remate": False,
        "precio_referencia": 49990
    },
    # Configuración de elemento #2 (nombre='Bad Boy Cobalt', marca='Carolina Herrera')
    {
        "nombre": "Bad Boy Cobalt",
        "marca": "Carolina Herrera",
        "genero": "Hombre",
        "tipo": "Eau de Parfum",
        "notas": "Pimienta Rosa, Lavanda, Ciruela Negra, Geranio, Trufa Mineral, Vetiver, Cedro",
        "imagen_url": "https://images.falabella.com/v3/assets/blt088e6ed3cf8a7e92/blt56d7870a256a64bb/620e261ce8d0ad6a86c624d0/16281140_1.jpg",
        "es_arabe": False,
        "en_tendencia": True,
        "en_remate": False,
        "precio_referencia": 109990
    },
    # Configuración de elemento #3 (nombre='Born In Roma Intense', marca='Valentino')
    {
        "nombre": "Born In Roma Intense",
        "marca": "Valentino",
        "genero": "Hombre",
        "tipo": "Eau de Parfum",
        "notas": "Vainilla Bourbon, Ámbar, Lavanda, Vetiver Ahumado",
        "imagen_url": "https://images.falabella.com/v3/assets/blt088e6ed3cf8a7e92/blt8efbc5b1f5fc5c6a/63e15779c9431411516e91f1/16723226_1.jpg",
        "es_arabe": False,
        "en_tendencia": True,
        "en_remate": False,
        "precio_referencia": 119990
    },
    # Configuración de elemento #4 (nombre='Paradoxe', marca='Prada')
    {
        "nombre": "Paradoxe",
        "marca": "Prada",
        "genero": "Mujer",
        "tipo": "Eau de Parfum",
        "notas": "Pera, Mandarina, Bergamota, Flor de Azahar, Jazmín Sambac, Ámbar Ambrofix, Vainilla Bourbon, Almizcle Blanco",
        "imagen_url": "https://images.falabella.com/v3/assets/blt088e6ed3cf8a7e92/blte61cb0a8d626e257/630d0728c7f21256ab5fcf67/16524177_1.jpg",
        "es_arabe": False,
        "en_tendencia": True,
        "en_remate": False,
        "precio_referencia": 125990
    },
    # Configuración de elemento #5 (nombre='Stronger With You Intensely', marca='Giorgio Armani')
    {
        "nombre": "Stronger With You Intensely",
        "marca": "Giorgio Armani",
        "genero": "Hombre",
        "tipo": "Eau de Parfum",
        "notas": "Pimienta Rosa, Enebro, Canela, Lavanda, Salvia, Toffee Acaramelado, Vainilla, Haba Tonka, Gamuza",
        "imagen_url": "https://images.falabella.com/v3/assets/blt088e6ed3cf8a7e92/bltc455ca37cf66e5ff/609d84606eaecb2260682855/14748114_1.jpg",
        "es_arabe": False,
        "en_tendencia": True,
        "en_remate": False,
        "precio_referencia": 114990
    },
    # Configuración de elemento #6 (nombre='MYSLF', marca='Yves Saint Laurent')
    {
        "nombre": "MYSLF",
        "marca": "Yves Saint Laurent",
        "genero": "Hombre",
        "tipo": "Eau de Parfum",
        "notas": "Bergamota de Calabria, Flor de Azahar del Naranjo de Túnez, Ambrofix Amaderado, Pachulí",
        "imagen_url": "https://images.falabella.com/v3/assets/blt088e6ed3cf8a7e92/bltb907153b3b4fca8b/64e8b38743d8383f2a1bcf90/16913508_1.jpg",
        "es_arabe": False,
        "en_tendencia": True,
        "en_remate": False,
        "precio_referencia": 115990
    }
]


# Definición de función 'sincronizar_perfumes' sin parámetros externos
def sincronizar_perfumes():
    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    print("--- Sincronizando Perfumes en Supabase y SQLite ---")
    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    sb = get_supabase(use_service_role=True)
    # Asignamos 'conn' con get_connection()
    conn = get_connection()
    # Asignamos 'c' con conn.cursor()
    c = conn.cursor()

    # Asignamos 'perfumes_creados' con []
    perfumes_creados = []

    # Recorremos iterativamente cada 'item' en NUEVOS_PERFUMES
    for item in NUEVOS_PERFUMES:
        # Asignamos 'nom' con item['nombre']
        nom = item["nombre"]
        # Asignamos 'marca' con item['marca']
        marca = item["marca"]

        # 1. Supabase Cloud
        sb_id = None
        # Evaluamos la condición lógica (sb and is_supabase_disponible()) para controlar el flujo
        if sb and is_supabase_disponible():
            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            res = sb.table("perfumes").select("id").eq("nombre", nom).eq("marca", marca).execute()
            # Evaluamos la condición lógica (res.data) para controlar el flujo
            if res.data:
                # Asignamos 'sb_id' con res.data[0]['id']
                sb_id = res.data[0]["id"]
                # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                print(f"[Supabase] Perfume '{nom}' ({marca}) ya existía con ID: {sb_id}")
            else:
                # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                ins = sb.table("perfumes").insert(item).execute()
                # Evaluamos la condición lógica (ins.data) para controlar el flujo
                if ins.data:
                    # Asignamos 'sb_id' con ins.data[0]['id']
                    sb_id = ins.data[0]["id"]
                    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                    print(f"[Supabase] Creado '{nom}' ({marca}) con ID: {sb_id}")

        # 2. SQLite Local
        c.execute("SELECT id FROM perfumes WHERE nombre = ? AND marca = ?;", (nom, marca))
        # Asignamos 'row' con c.fetchone()
        row = c.fetchone()
        # Evaluamos la condición lógica (row) para controlar el flujo
        if row:
            # Asignamos 'sql_id' con row['id']
            sql_id = row["id"]
            # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
            print(f"[SQLite] Perfume '{nom}' ({marca}) ya existía con ID: {sql_id}")
        else:
            # Ejecutamos instrucción: c.execute('\n INSERT INTO perfumes (nombre, marca, g...
            c.execute(
                """
                INSERT INTO perfumes (nombre, marca, genero, tipo, notas, imagen_url, es_arabe, en_tendencia, en_remate, precio_referencia)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    nom,
                    marca,
                    item["genero"],
                    item["tipo"],
                    item["notas"],
                    item["imagen_url"],
                    1 if item["es_arabe"] else 0,
                    1 if item["en_tendencia"] else 0,
                    1 if item["en_remate"] else 0,
                    item["precio_referencia"]
                )
            )
            # Asignamos 'sql_id' con c.lastrowid
            sql_id = c.lastrowid
            # Ejecutamos instrucción: conn.commit()
            conn.commit()
            # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
            print(f"[SQLite] Creado '{nom}' ({marca}) con ID: {sql_id}")

        # Ejecutamos instrucción: perfumes_creados.append({'id': sb_id or sql_id, 'nom...
        perfumes_creados.append({
            "id": sb_id or sql_id,
            "nombre": nom,
            "marca": marca,
            "precio_referencia": item["precio_referencia"]
        })

    # Ejecutamos instrucción: conn.close()
    conn.close()
    # Retornamos el resultado procesado (perfumes_creados)
    return perfumes_creados


# Punto de entrada principal cuando el script se invoca directamente desde consola
if __name__ == "__main__":
    # Asignamos 'creados' con sincronizar_perfumes()
    creados = sincronizar_perfumes()
    # Ejecutamos instrucción: print(f'\nProceso finalizado. Total perfumes sincron...
    print(f"\nProceso finalizado. Total perfumes sincronizados: {len(creados)}")
    # Recorremos iterativamente cada 'p' en creados
    for p in creados:
        # Ejecutamos instrucción: print(f" -> ID: {p['id']} | {p['nombre']} ({p['marca...
        print(f" -> ID: {p['id']} | {p['nombre']} ({p['marca']})")
