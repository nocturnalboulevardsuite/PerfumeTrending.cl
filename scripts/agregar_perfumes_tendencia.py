"""
Script para agregar perfumes trending de alta demanda al catálogo.
Sincroniza tanto Supabase Cloud como SQLite local para garantizar paridad.
"""
import sys
import os

# Asegurar path de imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "APP")))

from backend.database import get_supabase, is_supabase_disponible, get_connection

NUEVOS_PERFUMES = [
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


def sincronizar_perfumes():
    print("--- Sincronizando Perfumes en Supabase y SQLite ---")
    sb = get_supabase(use_service_role=True)
    conn = get_connection()
    c = conn.cursor()

    perfumes_creados = []

    for item in NUEVOS_PERFUMES:
        nom = item["nombre"]
        marca = item["marca"]

        # 1. Supabase Cloud
        sb_id = None
        if sb and is_supabase_disponible():
            res = sb.table("perfumes").select("id").eq("nombre", nom).eq("marca", marca).execute()
            if res.data:
                sb_id = res.data[0]["id"]
                print(f"[Supabase] Perfume '{nom}' ({marca}) ya existía con ID: {sb_id}")
            else:
                ins = sb.table("perfumes").insert(item).execute()
                if ins.data:
                    sb_id = ins.data[0]["id"]
                    print(f"[Supabase] Creado '{nom}' ({marca}) con ID: {sb_id}")

        # 2. SQLite Local
        c.execute("SELECT id FROM perfumes WHERE nombre = ? AND marca = ?;", (nom, marca))
        row = c.fetchone()
        if row:
            sql_id = row["id"]
            print(f"[SQLite] Perfume '{nom}' ({marca}) ya existía con ID: {sql_id}")
        else:
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
            sql_id = c.lastrowid
            conn.commit()
            print(f"[SQLite] Creado '{nom}' ({marca}) con ID: {sql_id}")

        perfumes_creados.append({
            "id": sb_id or sql_id,
            "nombre": nom,
            "marca": marca,
            "precio_referencia": item["precio_referencia"]
        })

    conn.close()
    return perfumes_creados


if __name__ == "__main__":
    creados = sincronizar_perfumes()
    print(f"\nProceso finalizado. Total perfumes sincronizados: {len(creados)}")
    for p in creados:
        print(f" -> ID: {p['id']} | {p['nombre']} ({p['marca']})")
