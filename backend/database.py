import sqlite3
import os
from datetime import datetime, timedelta
import random

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DB_PATH = os.path.join(DB_DIR, "perfumes.db")


def get_connection():
    """Obtiene una conexión a la base de datos SQLite."""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Crea las tablas necesarias si no existen y precarga datos semilla."""
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Tabla de Perfumes
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS perfumes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        marca TEXT NOT NULL,
        genero TEXT DEFAULT 'Unisex',
        tipo TEXT DEFAULT 'Eau de Parfum',
        notas TEXT NOT NULL,
        imagen_url TEXT NOT NULL,
        es_arabe BOOLEAN DEFAULT 0,
        en_tendencia BOOLEAN DEFAULT 0,
        en_remate BOOLEAN DEFAULT 0,
        precio_referencia INTEGER NOT NULL
    )
    """)

    # 2. Tabla de Tiendas Chilenas
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tiendas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL UNIQUE,
        url_base TEXT NOT NULL,
        trust_score INTEGER DEFAULT 85,
        badge TEXT DEFAULT 'Verificado',
        logo_emoji TEXT DEFAULT '🏬'
    )
    """)

    # 3. Tabla de Registro Periódico de Precios (Snapshots históricos)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS precios_registro (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        perfume_id INTEGER NOT NULL,
        tienda_id INTEGER NOT NULL,
        precio_actual INTEGER NOT NULL,
        precio_normal INTEGER NOT NULL,
        en_stock BOOLEAN DEFAULT 1,
        url_producto TEXT NOT NULL,
        fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (perfume_id) REFERENCES perfumes (id),
        FOREIGN KEY (tienda_id) REFERENCES tiendas (id)
    )
    """)

    conn.commit()

    # Si la base de datos está vacía, insertar datos semilla
    cursor.execute("SELECT COUNT(*) FROM perfumes")
    if cursor.fetchone()[0] == 0:
        poblar_datos_semilla(conn)

    conn.close()


def poblar_datos_semilla(conn):
    """Puebla la base de datos con tiendas chilenas, perfumes iniciales e historial periódico."""
    cursor = conn.cursor()

    tiendas_iniciales = [
        ("Falabella", "https://www.falabella.com", 96, "Retail Oficial 🇨🇱", "🟢"),
        ("Paris", "https://www.paris.cl", 95, "Retail Oficial 🇨🇱", "🟢"),
        ("Ripley", "https://simple.ripley.cl", 94, "Retail Oficial 🇨🇱", "🟢"),
        ("Silk Perfumes", "https://www.silkperfumes.cl", 92, "Importador Autorizado 🇨🇱", "⭐"),
        ("Elite Perfumes", "https://www.eliteperfumes.cl", 89, "Tienda Especializada 🇨🇱", "⭐"),
        ("DBS Beauty Store", "https://www.dbs.cl", 91, "Cadena Certificada 🇨🇱", "🟢")
    ]

    cursor.executemany("""
    INSERT OR IGNORE INTO tiendas (nombre, url_base, trust_score, badge, logo_emoji)
    VALUES (?, ?, ?, ?, ?)
    """, tiendas_iniciales)

    perfumes_iniciales = [
        (
            "Bleu de Chanel", "Chanel", "Hombre", "Eau de Parfum",
            "Cítricos, Pomelo, Menta, Pimienta Rosa, Cedro, Sándalo, Incienso",
            "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=500&q=80",
            0, 1, 0, 180000
        ),
        (
            "YSL Libre", "Yves Saint Laurent", "Mujer", "Eau de Parfum",
            "Lavanda, Mandarina, Grosellas Negras, Jazmín, Vainilla, Cedro, Ámbar Gris",
            "https://images.unsplash.com/photo-1592945403244-b3fbafd7f539?w=500&q=80",
            0, 1, 0, 150000
        ),
        (
            "Dior Sauvage", "Dior", "Hombre", "Eau de Toilette",
            "Bergamota, Pimienta Negra, Lavanda, Pimienta Rosa, Vetiver, Pachulí, Cedro",
            "https://images.unsplash.com/photo-1588405748880-12d1d2a59f75?w=500&q=80",
            0, 1, 0, 165000
        ),
        (
            "Club de Nuit Intense Man", "Armaf", "Hombre", "Eau de Toilette",
            "Limón, Piña, Bergamota, Grosellas Negras, Manzana, Abedul, Jazmín, Rosa, Almizcle (Musk), Ámbar Gris, Pachulí, Vainilla",
            "https://images.unsplash.com/photo-1594035910387-fea47794261f?w=500&q=80",
            1, 1, 1, 45000
        ),
        (
            "Khamrah", "Lattafa", "Unisex", "Eau de Parfum",
            "Canela, Nuez Moscada, Bergamota, Dátiles, Praliné, Tuberosa, Vainilla, Haba Tonka, Mirra, Benjuí, Ámbar",
            "https://images.unsplash.com/photo-1547887537-6158d64c35b3?w=500&q=80",
            1, 1, 1, 55000
        ),
        (
            "Baccarat Rouge 540", "Maison Francis Kurkdjian", "Unisex", "Extrait de Parfum",
            "Azafrán, Jazmín, Ámbar Gris, Madera de Cedro, Resina de Abeto",
            "https://images.unsplash.com/photo-1583445013765-46c20c4a6772?w=500&q=80",
            0, 1, 0, 320000
        ),
        (
            "Acqua Di Gio", "Giorgio Armani", "Hombre", "Eau de Toilette",
            "Notas Marinas, Bergamota, Lima, Mandarina, Jazmín, Romero, Cedro, Pachulí",
            "https://images.unsplash.com/photo-1595425970377-c9703cf48b6d?w=500&q=80",
            0, 0, 1, 110000
        ),
        (
            "Scandal Pour Homme", "Jean Paul Gaultier", "Hombre", "Eau de Toilette",
            "Salvia, Mandarina, Caramelo, Haba Tonka, Vetiver",
            "https://images.unsplash.com/photo-1616949755610-8c9bbc08f138?w=500&q=80",
            0, 0, 0, 135000
        ),
        (
            "Hawas for Men", "Rasasi", "Hombre", "Eau de Parfum",
            "Manzana, Bergamota, Limón, Canela, Notas Acuáticas, Ciruela, Cardamomo, Ámbar Gris, Almizcle (Musk), Pachulí",
            "https://images.unsplash.com/photo-1523293182086-7651a899d37f?w=500&q=80",
            1, 1, 0, 65000
        ),
        (
            "Eros", "Versace", "Hombre", "Eau de Parfum",
            "Menta, Manzana Verde, Limón, Haba Tonka, Ambroxan, Geranio, Vainilla de Madagascar, Cedro, Vetiver",
            "https://images.unsplash.com/photo-1508746829417-e6f548d8d6ed?w=500&q=80",
            0, 0, 1, 125000
        )
    ]

    cursor.executemany("""
    INSERT INTO perfumes (nombre, marca, genero, tipo, notas, imagen_url, es_arabe, en_tendencia, en_remate, precio_referencia)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, perfumes_iniciales)

    conn.commit()

    # Generar snapshots periódicos simulados de las últimas 3 semanas para tener análisis temporal
    cursor.execute("SELECT id, precio_referencia FROM perfumes")
    perfumes_db = cursor.fetchall()
    cursor.execute("SELECT id, nombre, url_base FROM tiendas")
    tiendas_db = cursor.fetchall()

    hoy = datetime.now()
    dias_atras = [21, 14, 7, 3, 1, 0]  # Registros periódicos: hace 3 semanas, 2 semanas, 1 semana, etc.

    registros_historicos = []
    for p in perfumes_db:
        p_id = p["id"]
        precio_ref = p["precio_referencia"]

        for tienda in tiendas_db:
            t_id = tienda["id"]
            # Variación base por tienda (ej. Silk/Elite suelen tener precios más competitivos)
            factor_tienda = 0.88 if tienda["nombre"] in ["Silk Perfumes", "Elite Perfumes"] else 1.0
            
            for dia in dias_atras:
                fecha = hoy - timedelta(days=dia, hours=random.randint(0, 12), minutes=random.randint(0, 59))
                # Fluctuación de precio en cada análisis periódico (-8% a +5%)
                fluc = 1.0 + random.uniform(-0.08, 0.05)
                precio_actual = int(round((precio_ref * factor_tienda * fluc) / 1000) * 1000)
                precio_normal = int(round((precio_ref * factor_tienda * 1.15) / 1000) * 1000)
                en_stock = 1 if (random.random() > 0.08) else 0

                registros_historicos.append((
                    p_id, t_id, precio_actual, precio_normal, en_stock,
                    f"{tienda['url_base']}/producto/{p_id}",
                    fecha.strftime("%Y-%m-%d %H:%M:%S")
                ))

    cursor.executemany("""
    INSERT INTO precios_registro (perfume_id, tienda_id, precio_actual, precio_normal, en_stock, url_producto, fecha_registro)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, registros_historicos)

    conn.commit()


def registrar_precio(perfume_id, tienda_id, precio_actual, precio_normal, en_stock, url_producto, fecha=None):
    """Inserta una captura periódica de precio para un perfume en una tienda específica."""
    conn = get_connection()
    cursor = conn.cursor()
    if fecha is None:
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
    INSERT INTO precios_registro (perfume_id, tienda_id, precio_actual, precio_normal, en_stock, url_producto, fecha_registro)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (perfume_id, tienda_id, precio_actual, precio_normal, int(en_stock), url_producto, fecha))

    conn.commit()
    conn.close()


def obtener_catalogo(busqueda=None, esencias=None, categoria=None):
    """
    Obtiene el listado de perfumes aplicando filtros de texto, notas olfativas o categorías
    y calculando el mejor precio actual detectado por el scraper.
    """
    init_db()
    conn = get_connection()
    cursor = conn.cursor()

    query = """
    SELECT p.*,
           MIN(pr.precio_actual) as mejor_precio,
           MAX(pr.fecha_registro) as ultima_actualizacion
    FROM perfumes p
    LEFT JOIN precios_registro pr ON p.id = pr.perfume_id
    WHERE 1=1
    """
    params = []

    if busqueda:
        query += " AND (p.nombre LIKE ? OR p.marca LIKE ?)"
        params.extend([f"%{busqueda}%", f"%{busqueda}%"])

    if categoria == "arabes":
        query += " AND p.es_arabe = 1"
    elif categoria == "remates":
        query += " AND p.en_remate = 1"

    query += " GROUP BY p.id"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    perfumes = [dict(row) for row in rows]

    # Filtrar por notas de esencias en memoria si se seleccionaron
    if esencias:
        perfumes_filtrados = []
        for p in perfumes:
            notas_p = [n.strip().lower() for n in p["notas"].split(",")]
            if any(any(es.lower() in nota for nota in notas_p) for es in esencias):
                perfumes_filtrados.append(p)
        perfumes = perfumes_filtrados

    conn.close()
    return perfumes


def obtener_detalle_perfume(perfume_id):
    """Retorna información completa del perfume."""
    init_db()
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM perfumes WHERE id = ?", (perfume_id,))
    row = cursor.fetchone()
    perfume = dict(row) if row else None
    conn.close()
    return perfume


def obtener_precios_actuales(perfume_id):
    """
    Retorna el precio más reciente registrado en cada tienda para el perfume dado.
    """
    init_db()
    conn = get_connection()
    cursor = conn.cursor()

    query = """
    SELECT t.id as tienda_id, t.nombre as tienda_nombre, t.url_base, t.trust_score, t.badge, t.logo_emoji,
           pr.precio_actual, pr.precio_normal, pr.en_stock, pr.url_producto, pr.fecha_registro
    FROM tiendas t
    JOIN precios_registro pr ON t.id = pr.tienda_id
    WHERE pr.perfume_id = ?
      AND pr.fecha_registro = (
          SELECT MAX(fecha_registro)
          FROM precios_registro
          WHERE perfume_id = ? AND tienda_id = t.id
      )
    ORDER BY pr.precio_actual ASC
    """
    cursor.execute(query, (perfume_id, perfume_id))
    rows = cursor.fetchall()
    precios = [dict(row) for row in rows]
    conn.close()
    return precios


def obtener_historico_precios(perfume_id):
    """
    Retorna toda la serie temporal de precios para armar el gráfico de análisis periódico.
    """
    init_db()
    conn = get_connection()
    cursor = conn.cursor()

    query = """
    SELECT t.nombre as tienda, pr.precio_actual, pr.fecha_registro
    FROM precios_registro pr
    JOIN tiendas t ON pr.tienda_id = t.id
    WHERE pr.perfume_id = ?
    ORDER BY pr.fecha_registro ASC
    """
    cursor.execute(query, (perfume_id,))
    rows = cursor.fetchall()
    registros = [dict(row) for row in rows]
    conn.close()
    return registros


def guardar_o_actualizar_perfume_scraped(nombre, marca, precio_actual, precio_normal, tienda_nombre, url_producto, imagen_url=None, notas=None, es_arabe=0, genero="Unisex"):
    """
    Recibe un perfume extraído por el scraper.
    Si el perfume no existe en la base de datos, lo crea automáticamente.
    Luego, registra el nuevo snapshot periódico de precio.
    """
    init_db()
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Obtener o registrar la tienda
    cursor.execute("SELECT id FROM tiendas WHERE LOWER(nombre) = LOWER(?)", (tienda_nombre,))
    row_tienda = cursor.fetchone()
    if row_tienda:
        tienda_id = row_tienda["id"]
    else:
        cursor.execute("""
        INSERT INTO tiendas (nombre, url_base, trust_score, badge, logo_emoji)
        VALUES (?, ?, 90, 'Tienda Verificada 🇨🇱', '🏬')
        """, (tienda_nombre, url_producto.split('/')[0] + "//" + url_producto.split('/')[2] if '://' in url_producto else 'https://'))
        tienda_id = cursor.lastrowid

    # 2. Buscar si el perfume ya existe (por nombre y marca parecidos)
    cursor.execute("""
    SELECT id, precio_referencia FROM perfumes 
    WHERE LOWER(nombre) = LOWER(?) OR LOWER(nombre) LIKE ?
    """, (nombre.strip(), f"%{nombre.strip()}%"))
    row_perfume = cursor.fetchone()

    es_nuevo = False
    if row_perfume:
        perfume_id = row_perfume["id"]
    else:
        es_nuevo = True
        img = imagen_url or "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=500&q=80"
        notas_texto = notas or "Cítricos, Maderas, Almizcle"
        cursor.execute("""
        INSERT INTO perfumes (nombre, marca, genero, tipo, notas, imagen_url, es_arabe, en_tendencia, en_remate, precio_referencia)
        VALUES (?, ?, ?, 'Eau de Parfum', ?, ?, ?, 1, 0, ?)
        """, (nombre.strip(), marca.strip() or "Diseñador", genero, notas_texto, img, es_arabe, precio_actual))
        perfume_id = cursor.lastrowid

    # 3. Registrar el snapshot de precio periódico con timestamp actual
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
    INSERT INTO precios_registro (perfume_id, tienda_id, precio_actual, precio_normal, en_stock, url_producto, fecha_registro)
    VALUES (?, ?, ?, ?, 1, ?, ?)
    """, (perfume_id, tienda_id, precio_actual, precio_normal, url_producto, fecha_actual))

    conn.commit()
    conn.close()
    return {"perfume_id": perfume_id, "es_nuevo": es_nuevo, "fecha": fecha_actual}


def obtener_tiendas():
    """Retorna la lista de tiendas registradas."""
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tiendas ORDER BY trust_score DESC")
    rows = cursor.fetchall()
    tiendas = [dict(row) for row in rows]
    conn.close()
    return tiendas

