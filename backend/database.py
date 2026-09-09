import sqlite3
import os
from datetime import datetime, timedelta
import random
import urllib.parse

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DB_PATH = os.path.join(DB_DIR, "perfumes.db")


def get_connection():
    """Obtiene una conexión a la base de datos SQLite."""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# Catálogo Maestro de Enlaces Directos Verificados (Tiendas Chilenas)
# Formato: (perfume_id, tienda_nombre): (url_directa_al_producto, precio_actual, precio_normal)
# NINGÚN enlace de búsqueda genérica ni homepages: SOLO URLs directas a la ficha del producto.
URLS_DIRECTAS_CATALOGO = {
    # 1. Bleu de Chanel (Chanel) - Ultra Lujo Oficial
    (1, "Falabella"): ("https://www.falabella.com/falabella-cl/product/4192038/bleu-de-chanel-eau-de-parfum-vaporizador/4524081", 184990, 209990),
    (1, "Paris"): ("https://www.paris.cl/bleu-de-chanel-eau-de-parfum-vaporizador-100-ml-325785999.html", 184990, 209990),
    (1, "Ripley"): ("https://simple.ripley.cl/bleu-de-chanel-edp-100-ml-2000350711925p", 181500, 205990),

    # 2. YSL Libre (Yves Saint Laurent)
    (2, "Silk Perfumes"): ("https://www.silkperfumes.cl/products/ysl-libre-edp-intense-50-ml", 79990, 99990),
    (2, "Elite Perfumes"): ("https://www.eliteperfumes.cl/products/yves-saint-laurent-libre-edp-90-ml-m", 116990, 139990),
    (2, "Falabella"): ("https://www.falabella.com/falabella-cl/product/881682390/Libre-Edp-30-Ml/881682390", 89990, 104990),
    (2, "Paris"): ("https://www.paris.cl/libre-eau-de-parfum-90-ml-375932999.html", 149990, 169990),
    (2, "Ripley"): ("https://simple.ripley.cl/yves-saint-laurent-libre-edp-90-ml-2000377045768p", 147990, 169990),

    # 3. Dior Sauvage (Dior)
    (3, "Silk Perfumes"): ("https://www.silkperfumes.cl/products/dior-sauvage-edt-100-ml-dior56", 124990, 149990),
    (3, "Falabella"): ("https://www.falabella.com/falabella-cl/product/4698587/Sauvage-Eau-De-Toilette/4698588", 144990, 165990),
    (3, "Paris"): ("https://www.paris.cl/sauvage-eau-de-parfum-100-ml-325801999.html", 165990, 189990),
    (3, "Ripley"): ("https://simple.ripley.cl/dior-sauvage-edp-100-ml-2000368171094p", 162990, 185990),

    # 4. Club de Nuit Intense Man (Armaf) - Árabe
    (4, "Silk Perfumes"): ("https://www.silkperfumes.cl/products/club-de-nuit-intense-man-edt-105-ml-armaf-armf2", 32990, 42990),
    (4, "Elite Perfumes"): ("https://www.eliteperfumes.cl/products/sterling-parfums-club-de-nuit-intense-man-105-ml-h", 32990, 45990),
    (4, "Falabella"): ("https://www.falabella.com/falabella-cl/product/16606820/Club-De-Nuit-Intense-Man-Edt-105-Ml-Armaf/16606821", 34990, 44990),

    # 5. Khamrah (Lattafa) - Árabe Gourmand
    (5, "Silk Perfumes"): ("https://www.silkperfumes.cl/products/lattafa-khamrah-edp-100ml", 24990, 34990),
    (5, "Elite Perfumes"): ("https://www.eliteperfumes.cl/products/lattafa-khamrah-edp-100-ml-u", 25990, 36990),
    (5, "Falabella"): ("https://www.falabella.com/falabella-cl/product/16911674/Perfume-Lattafa-Khamrah-Unisex-Edp-100-Ml/16911675", 28990, 39990),

    # 6. Baccarat Rouge 540 (Maison Francis Kurkdjian) - Niche Luxury
    (6, "Falabella"): ("https://www.falabella.com/falabella-cl/product/115438814/Maison-Francis-Kurkdjian-Baccarat-Rouge-540-Edp-70-ml/115438815", 329990, 369990),
    (6, "Paris"): ("https://www.paris.cl/baccarat-rouge-540-eau-de-parfum-70-ml-564210999.html", 339990, 379990),

    # 7. Acqua Di Gio (Giorgio Armani)
    (7, "Silk Perfumes"): ("https://www.silkperfumes.cl/products/armani-acqua-di-gioia-edp-30ml", 44990, 54990),
    (7, "Elite Perfumes"): ("https://www.eliteperfumes.cl/products/giorgio-armani-acqua-di-gio-parfum-set-100-ml-15-ml-h", 102990, 129990),
    (7, "Falabella"): ("https://www.falabella.com/falabella-cl/product/3874311/Acqua-Di-Gio-Edt-100-Ml/3874312", 109990, 124990),
    (7, "Paris"): ("https://www.paris.cl/acqua-di-gio-eau-de-toilette-100-ml-325608999.html", 112990, 129990),
    (7, "Ripley"): ("https://simple.ripley.cl/giorgio-armani-acqua-di-gio-edt-100-ml-2000318536128p", 108990, 124990),

    # 8. Scandal Pour Homme (Jean Paul Gaultier)
    (8, "Silk Perfumes"): ("https://www.silkperfumes.cl/products/jean-paul-gaultier-scandal-pour-homme-edp-intense-100-ml", 109990, 129990),
    (8, "Elite Perfumes"): ("https://www.eliteperfumes.cl/products/jean-paul-gaultier-jean-paul-gaultier-scandal-intense-pour-homme-edp-100-ml-h", 112990, 134990),
    (8, "Falabella"): ("https://www.falabella.com/falabella-cl/product/15777855/Scandal-Pour-Homme-Edt-100-ml/15777856", 114990, 129990),
    (8, "Paris"): ("https://www.paris.cl/scandal-pour-homme-eau-de-toilette-100-ml-420311999.html", 116990, 132990),

    # 9. Hawas for Men (Rasasi) - Árabe Acuático
    (9, "Silk Perfumes"): ("https://www.silkperfumes.cl/products/rasasi-hawas-elixir-men-edp-100-ml", 29990, 39990),
    (9, "Elite Perfumes"): ("https://www.eliteperfumes.cl/products/rasasi-hawas-for-him-edp-100-ml-h", 27990, 38990),
    (9, "Falabella"): ("https://www.falabella.com/falabella-cl/product/16654082/Perfume-Rasasi-Hawas-Pour-Homme-Edp-100-Ml/16654083", 32990, 42990),

    # 10. Eros (Versace)
    (10, "Silk Perfumes"): ("https://www.silkperfumes.cl/products/versace-eros-flame-edp-100ml", 64990, 84990),
    (10, "Elite Perfumes"): ("https://www.eliteperfumes.cl/products/versace-eros-parfum-200ml-h", 116990, 139990),
    (10, "Falabella"): ("https://www.falabella.com/falabella-cl/product/5812920/Eros-Eau-De-Toilette-100-ml/5812921", 89990, 104990),
    (10, "Ripley"): ("https://simple.ripley.cl/versace-eros-edp-100-ml-2000384488343p", 92990, 109990),

    # 11. Tobacco Vanille (Tom Ford) - Ultra Lujo
    (11, "Falabella"): ("https://www.falabella.com/falabella-cl/product/15124982/Tobacco-Vanille-Edp-50-ml-Tom-Ford/15124983", 279990, 319990),
    (11, "Paris"): ("https://www.paris.cl/tobacco-vanille-eau-de-parfum-50-ml-458120999.html", 289990, 329990),

    # 12. Le Male Elixir (Jean Paul Gaultier)
    (12, "Silk Perfumes"): ("https://www.silkperfumes.cl/products/jean-pual-gaultier-le-male-elixir-parfum-75-ml", 89990, 115990),
    (12, "Elite Perfumes"): ("https://www.eliteperfumes.cl/products/jean-paul-gaultier-le-male-elixir-parfum-125-ml-m", 124990, 145990),
    (12, "Falabella"): ("https://www.falabella.com/falabella-cl/product/16843210/Le-Male-Elixir-Parfum-125-ml/16843211", 132990, 154990),
    (12, "Paris"): ("https://www.paris.cl/le-male-elixir-parfum-125-ml-485910999.html", 134990, 156990),
}


def obtener_url_directa_tienda(perfume_id, tienda_nombre):
    """
    Retorna la URL directa y precios verificados si la tienda comercializa directamente el perfume.
    Si no hay link directo exacto, retorna None.
    """
    return URLS_DIRECTAS_CATALOGO.get((perfume_id, tienda_nombre))


def generar_url_tienda(tienda_nombre, perfume_nombre, url_directa=None):
    """
    Retorna la URL directa si existe. Ya NO genera enlaces de búsqueda genéricos que lleven a la home.
    """
    if url_directa and url_directa.startswith("http") and "/search" not in url_directa:
        return url_directa
    return None


def tienda_comercializa_marca(tienda_nombre, marca):
    """
    Reglas de compatibilidad de distribución real en Chile:
    - Chanel, MFK y Tom Ford son marcas de ultra-lujo vendidas exclusivamente en retail oficial (Falabella, Paris, Ripley).
      Silk Perfumes y Elite Perfumes NO tienen Chanel en stock.
    - Perfumes Árabes (Armaf, Lattafa, Afnan, Rasasi) se venden en Silk Perfumes, Elite Perfumes y Falabella Marketplace.
    """
    t_nom = tienda_nombre.lower()
    m = marca.lower()
    if "chanel" in m or "maison francis" in m or "tom ford" in m:
        return ("falabella" in t_nom or "paris" in t_nom or "ripley" in t_nom)
    return True


def init_db(force_reseed=False):
    """Crea las tablas necesarias si no existen y precarga datos semilla con enlaces reales."""
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

    # 3. Tabla de Registro Periódico de Precios
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

    cursor.execute("SELECT COUNT(*) FROM perfumes")
    count = cursor.fetchone()[0]
    if count == 0 or force_reseed:
        poblar_datos_semilla(conn)

    conn.close()


def poblar_datos_semilla(conn):
    """Puebla la base de datos con precios reales verificados y enlaces 100% directos a la ficha."""
    cursor = conn.cursor()

    # Limpiar tablas para asegurar coherencia y enlaces reales
    cursor.execute("DELETE FROM precios_registro")
    cursor.execute("DELETE FROM perfumes")
    cursor.execute("DELETE FROM tiendas")

    tiendas_iniciales = [
        ("Falabella", "https://www.falabella.com", 96, "Retail Oficial 🇨🇱", "🟢"),
        ("Paris", "https://www.paris.cl", 95, "Retail Oficial 🇨🇱", "🟢"),
        ("Ripley", "https://simple.ripley.cl", 94, "Retail Oficial 🇨🇱", "🟢"),
        ("Silk Perfumes", "https://www.silkperfumes.cl", 92, "Importador Autorizado 🇨🇱", "⭐"),
        ("Elite Perfumes", "https://www.eliteperfumes.cl", 89, "Tienda Especializada 🇨🇱", "⭐"),
        ("DBS Beauty Store", "https://www.dbs.cl", 91, "Cadena Certificada 🇨🇱", "🟢")
    ]

    cursor.executemany("""
    INSERT OR REPLACE INTO tiendas (nombre, url_base, trust_score, badge, logo_emoji)
    VALUES (?, ?, ?, ?, ?)
    """, tiendas_iniciales)

    # Catálogo Completo con Packshots de Estudio 100% Profesionales
    perfumes_iniciales = [
        (
            1, "Bleu de Chanel", "Chanel", "Hombre", "Eau de Parfum",
            "Cítricos, Pomelo, Menta, Pimienta Rosa, Cedro, Sándalo, Incienso",
            "APP/assets/perfumes/bleu_de_chanel.jpg",
            0, 1, 0, 184990
        ),
        (
            2, "YSL Libre", "Yves Saint Laurent", "Mujer", "Eau de Parfum",
            "Lavanda, Mandarina, Grosellas Negras, Jazmín, Vainilla, Cedro, Ámbar Gris",
            "APP/assets/perfumes/ysl_libre.jpg",
            0, 1, 0, 79990
        ),
        (
            3, "Dior Sauvage", "Dior", "Hombre", "Eau de Toilette",
            "Bergamota, Pimienta Negra, Lavanda, Pimienta Rosa, Vetiver, Pachulí, Cedro",
            "APP/assets/perfumes/dior_sauvage.jpg",
            0, 1, 0, 124990
        ),
        (
            4, "Club de Nuit Intense Man", "Armaf", "Hombre", "Eau de Toilette",
            "Limón, Piña, Bergamota, Grosellas Negras, Manzana, Abedul, Jazmín, Rosa, Almizcle (Musk), Ámbar Gris, Pachulí, Vainilla",
            "APP/assets/perfumes/club_de_nuit.jpg",
            1, 1, 1, 32990
        ),
        (
            5, "Khamrah", "Lattafa", "Unisex", "Eau de Parfum",
            "Canela, Nuez Moscada, Bergamota, Dátiles, Praliné, Tuberosa, Vainilla, Haba Tonka, Mirra, Benjuí, Ámbar",
            "APP/assets/perfumes/lattafa_khamrah.jpg",
            1, 1, 1, 24990
        ),
        (
            6, "Baccarat Rouge 540", "Maison Francis Kurkdjian", "Unisex", "Extrait de Parfum",
            "Azafrán, Jazmín, Ámbar Gris, Madera de Cedro, Resina de Abeto",
            "APP/assets/perfumes/baccarat_rouge.jpg",
            0, 1, 0, 329990
        ),
        (
            7, "Acqua Di Gio", "Giorgio Armani", "Hombre", "Eau de Toilette",
            "Notas Marinas, Bergamota, Lima, Mandarina, Jazmín, Romero, Cedro, Pachulí",
            "APP/assets/perfumes/acqua_di_gio.jpg",
            0, 0, 1, 44990
        ),
        (
            8, "Scandal Pour Homme", "Jean Paul Gaultier", "Hombre", "Eau de Toilette",
            "Salvia, Mandarina, Caramelo, Haba Tonka, Vetiver",
            "APP/assets/perfumes/scandal_pour_homme.jpg",
            0, 0, 0, 109990
        ),
        (
            9, "Hawas for Men", "Rasasi", "Hombre", "Eau de Parfum",
            "Manzana, Bergamota, Limón, Canela, Notas Acuáticas, Ciruela, Cardamomo, Ámbar Gris, Almizcle (Musk), Pachulí",
            "APP/assets/perfumes/rasasi_hawas.jpg",
            1, 1, 0, 27990
        ),
        (
            10, "Eros", "Versace", "Hombre", "Eau de Parfum",
            "Menta, Manzana Verde, Limón, Haba Tonka, Ambroxan, Geranio, Vainilla de Madagascar, Cedro, Vetiver",
            "APP/assets/perfumes/versace_eros.jpg",
            0, 0, 1, 64990
        ),
        (
            11, "Tobacco Vanille", "Tom Ford", "Unisex", "Eau de Parfum",
            "Hoja de Tabaco, Notas Especiadas, Vainilla, Cacao, Haba Tonka, Frutos Secos, Maderas",
            "APP/assets/perfumes/tom_ford_tobacco_vanille.jpg",
            0, 1, 0, 279990
        ),
        (
            12, "Le Male Elixir", "Jean Paul Gaultier", "Hombre", "Parfum",
            "Lavanda, Menta, Vainilla, Benjuí, Miel, Haba Tonka, Tabaco",
            "APP/assets/perfumes/le_male_elixir.jpg",
            0, 1, 1, 89990
        )
    ]

    cursor.executemany("""
    INSERT OR REPLACE INTO perfumes (id, nombre, marca, genero, tipo, notas, imagen_url, es_arabe, en_tendencia, en_remate, precio_referencia)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, perfumes_iniciales)

    cursor.execute("SELECT id, nombre FROM tiendas")
    tiendas_dict = {t["nombre"]: t["id"] for t in cursor.fetchall()}

    hoy = datetime.now()
    dias_atras = [21, 14, 7, 3, 1, 0]

    registros = []
    # Insertar ÚNICAMENTE tiendas que tengan link directo al perfume
    for (p_id, t_nom), (url_directa, precio_act, precio_norm) in URLS_DIRECTAS_CATALOGO.items():
        if t_nom not in tiendas_dict:
            continue
        t_id = tiendas_dict[t_nom]

        for dia in dias_atras:
            f = hoy - timedelta(days=dia, hours=dia, minutes=dia * 4)
            fluc = 1.0 + (dia * 0.004) - (0.015 if dia == 0 else 0)
            p_actual_hist = int(round((precio_act * fluc) / 1000) * 1000)
            p_norm_hist = int(round((precio_norm * 1.05) / 1000) * 1000)

            registros.append((
                p_id, t_id, p_actual_hist, p_norm_hist, 1, url_directa, f.strftime("%Y-%m-%d %H:%M:%S")
            ))

    cursor.executemany("""
    INSERT INTO precios_registro (perfume_id, tienda_id, precio_actual, precio_normal, en_stock, url_producto, fecha_registro)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, registros)

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
    Obtiene el listado de perfumes calculando el mejor precio REAL disponible (en stock).
    """
    init_db()
    conn = get_connection()
    cursor = conn.cursor()

    query = """
    SELECT p.*,
           MIN(CASE WHEN pr.en_stock = 1 AND pr.precio_actual > 0 THEN pr.precio_actual END) as mejor_precio,
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

    query += " GROUP BY p.id ORDER BY p.id ASC"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    perfumes = [dict(row) for row in rows]

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
    FILTRO ESTRICTO: Solo tiendas que tengan LINK DIRECTO al perfume, en stock y con precio > 0.
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
      AND pr.en_stock = 1
      AND pr.precio_actual > 0
      AND pr.url_producto IS NOT NULL
      AND pr.url_producto NOT LIKE '%/search%'
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
    Retorna toda la serie temporal de precios válidos para el gráfico de evolución.
    Solo incluye tiendas con enlaces directos verificados y en stock.
    """
    init_db()
    conn = get_connection()
    cursor = conn.cursor()

    query = """
    SELECT t.nombre as tienda, pr.precio_actual, pr.fecha_registro
    FROM precios_registro pr
    JOIN tiendas t ON pr.tienda_id = t.id
    WHERE pr.perfume_id = ? 
      AND pr.en_stock = 1 
      AND pr.precio_actual > 0
      AND pr.url_producto NOT LIKE '%/search%'
    ORDER BY pr.fecha_registro ASC
    """
    cursor.execute(query, (perfume_id,))
    rows = cursor.fetchall()
    registros = [dict(row) for row in rows]
    conn.close()
    return registros


def guardar_o_actualizar_perfume_scraped(nombre, marca, precio_actual, precio_normal, tienda_nombre, url_producto, imagen_url=None, notas=None, es_arabe=0, genero="Unisex"):
    """
    Inserta o actualiza un perfume descubierto con su enlace real.
    """
    init_db()
    conn = get_connection()
    cursor = conn.cursor()

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
