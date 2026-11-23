"""
PerfumeTrending.cl — Sincronizador de Precios Reales y Enlaces Directos
========================================================================
Propósito del archivo:
Este script se encarga de buscar en vivo los enlaces directos a las fichas de producto
y los precios reales confirmados en los principales comercios de Chile:
- Grandes Tiendas: Falabella, Paris, Ripley.
- Perfumerías Online Especializadas: Silk Perfumes, Elite Perfumes.

¿Para qué sirve en la defensa del proyecto?
Demuestra que la plataforma NO usa datos inventados ni simulaciones aleatorias,
sino que consulta directamente las fuentes oficiales mediante técnicas profesionales
de Web Scraping y consumo de endpoints internos de búsqueda (Shopify Suggest API, Next.js hydration y Schema.org).
"""

# Importación de librería estándar o dependencia externa (json)
import json
# Importación de librería estándar o dependencia externa (logging)
import logging
# Importación de librería estándar o dependencia externa (os)
import os
# Importación de librería estándar o dependencia externa (re)
import re
# Importación de librería estándar o dependencia externa (sys)
import sys
# Importación de librería estándar o dependencia externa (urllib.parse)
import urllib.parse
# Importación de librería estándar o dependencia externa (requests)
import requests
# Importación de componentes (BeautifulSoup) desde el módulo 'bs4'
from bs4 import BeautifulSoup

# Asignamos 'BASE_DIR' con os.path.dirname(os.path.dirname(os.path.ab...
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Evaluamos la condición lógica (BASE_DIR not in sys.path) para controlar el flujo
if BASE_DIR not in sys.path:
    # Ejecutamos instrucción: sys.path.insert(0, BASE_DIR)
    sys.path.insert(0, BASE_DIR)

# Bloque try/except para manejo seguro de errores y resiliencia operativa
try:
    # Importación de componentes (coincide_con_perfume, es_producto_perfume_valido) desde el módulo 'backend.normalizador'
    from backend.normalizador import coincide_con_perfume, es_producto_perfume_valido
except ImportError:
    # Importación de componentes (coincide_con_perfume, es_producto_perfume_valido) desde el módulo 'normalizador'
    from normalizador import coincide_con_perfume, es_producto_perfume_valido

# Configuración del registro de eventos (Logging) para ver en consola qué está pasando paso a paso
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
# Asignamos 'logger' con logging.getLogger('SyncPreciosReales')
logger = logging.getLogger("SyncPreciosReales")

# Encabezados HTTP (Headers) que simulan la petición de un navegador web real (Chrome en Windows)
# Esto es esencial para que los servidores de retail no bloqueen la consulta como tráfico automatizado
HEADERS_BROWSER = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept-Language': 'es-CL,es;q=0.9,en;q=0.8',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

# Encabezados optimizados para endpoints que responden directamente en formato JSON (como Shopify)
HEADERS_API = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json',
}


# Definición de función 'clean_price_str' (parámetros: val_str)
def clean_price_str(val_str: str) -> int:
    """
    Función de utilidad para limpiar texto de precios y convertirlo a un número entero.
    Por ejemplo: transforma '$ 188.100 CLP' o '188.100' en el número entero 188100.
    Si el valor viene vacío o con formato erróneo, retorna 0 de forma segura.
    """
    # Asignamos 'digits' con re.sub('[^\\d]', '', str(val_str))
    digits = re.sub(r'[^\d]', '', str(val_str))
    # Retornamos el resultado procesado (int(digits) if digits else 0)
    return int(digits) if digits else 0


# =============================================================================
# BLOQUE 1: EXTRACCIÓN EN TIENDAS BASADAS EN SHOPIFY (Silk y Elite Perfumes)
# =============================================================================

def buscar_silk(nombre_perfume: str, marca: str = "") -> tuple:
    """
    Busca un perfume en Silk Perfumes aprovechando el endpoint interno de sugerencias de Shopify.
    Valida estrictamente que el producto devuelto coincida en perfume, marca y sin flankers incompatibles.
    """
    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Armamos la consulta combinando marca y nombre sin repetir la marca si ya viene incluida
        query_str = f"{marca} {nombre_perfume}".strip() if (marca and marca.lower() not in nombre_perfume.lower()) else nombre_perfume.strip()
        # Codificamos el texto para URL segura
        q = urllib.parse.quote(query_str)
        # Endpoint JSON nativo de sugerencias de Shopify en Silk Perfumes
        url = f"https://www.silkperfumes.cl/search/suggest.json?q={q}&resources[type]=product"
        
        # Consultamos la API con timeout de 6 segundos
        r = requests.get(url, headers=HEADERS_API, timeout=6)
        # Evaluamos la condición lógica (r.status_code == 200) para controlar el flujo
        if r.status_code == 200:
            # Extraemos la lista de productos sugeridos
            prods = r.json().get('resources', {}).get('results', {}).get('products', [])
            # Recorremos iterativamente cada 'p' en prods
            for p in prods:
                # Asignamos 'title' con p.get('title', '')
                title = p.get('title', '')
                # Descartamos accesorios, desodorantes, cremas o decants
                if not es_producto_perfume_valido(title):
                    # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                    continue
                # Verificamos coincidencia exacta de marca, modelo y flanker
                if not coincide_con_perfume(title, nombre_perfume, marca):
                    # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                    continue
                # Limpiamos parámetros de consulta de la URL del producto
                p_url = "https://www.silkperfumes.cl" + p.get('url', '').split('?')[0]
                # Asignamos 'precio' con int(float(p.get('price', 0)))
                precio = int(float(p.get('price', 0)))
                # Validamos precio comercial mínimo de $10.000 CLP
                if precio >= 10000:
                    # Retornamos el resultado procesado ((p_url, precio))
                    return p_url, precio
    except Exception as e:
        # Registro de evento diagnóstico en la bitácora (logger) del sistema
        logger.warning(f"Error buscando Silk para '{nombre_perfume}': {e}")
    # Retornamos el resultado procesado ((None, None))
    return None, None


# Definición de función 'buscar_elite' (parámetros: nombre_perfume, marca)
def buscar_elite(nombre_perfume: str, marca: str = "") -> tuple:
    """
    Busca un perfume en Elite Perfumes utilizando la misma arquitectura Shopify Suggest API.
    Valida estrictamente que el producto coincida con el perfume auditado.
    """
    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Construimos la consulta con marca y nombre del perfume
        query_str = f"{marca} {nombre_perfume}".strip() if (marca and marca.lower() not in nombre_perfume.lower()) else nombre_perfume.strip()
        # Asignamos 'q' con urllib.parse.quote(query_str)
        q = urllib.parse.quote(query_str)
        # Endpoint JSON de búsqueda rápida en Elite Perfumes
        url = f"https://www.eliteperfumes.cl/search/suggest.json?q={q}&resources[type]=product"
        
        # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
        r = requests.get(url, headers=HEADERS_API, timeout=6)
        # Evaluamos la condición lógica (r.status_code == 200) para controlar el flujo
        if r.status_code == 200:
            # Asignamos 'prods' con r.json().get('resources', {}).get('results...
            prods = r.json().get('resources', {}).get('results', {}).get('products', [])
            # Recorremos iterativamente cada 'p' en prods
            for p in prods:
                # Asignamos 'title' con p.get('title', '')
                title = p.get('title', '')
                # Validamos que sea un perfume de frasco completo válido
                if not es_producto_perfume_valido(title):
                    # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                    continue
                # Validamos correspondencia de entidad contra el perfume buscado
                if not coincide_con_perfume(title, nombre_perfume, marca):
                    # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                    continue
                # Asignamos 'p_url' con 'https://www.eliteperfumes.cl' + p.get('ur...
                p_url = "https://www.eliteperfumes.cl" + p.get('url', '').split('?')[0]
                # Asignamos 'precio' con int(float(p.get('price', 0)))
                precio = int(float(p.get('price', 0)))
                # Evaluamos la condición lógica (precio >= 10000) para controlar el flujo
                if precio >= 10000:
                    # Retornamos el resultado procesado ((p_url, precio))
                    return p_url, precio
    except Exception as e:
        # Registro de evento diagnóstico en la bitácora (logger) del sistema
        logger.warning(f"Error buscando Elite para '{nombre_perfume}': {e}")
    # Retornamos el resultado procesado ((None, None))
    return None, None


# =============================================================================
# BLOQUE 2: EXTRACCIÓN EN RETAILERS TRADICIONALES (Falabella, Paris, Ripley)
# =============================================================================

def buscar_falabella(nombre_perfume: str, marca: str = "") -> tuple:
    """
    Extrae productos de Falabella Chile mediante la inspección de __NEXT_DATA__.
    Valida con precisión estricta de entidad y marca (evita flankers como Eros Energy o marcas cruzadas).
    """
    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Construimos la búsqueda para el motor de Falabella Chile
        query_str = f"{marca} {nombre_perfume}".strip() if (marca and marca.lower() not in nombre_perfume.lower()) else nombre_perfume.strip()
        # Asignamos 'q' con urllib.parse.quote(query_str)
        q = urllib.parse.quote(query_str)
        # Asignamos 'url' con f'https://www.falabella.com/falabella-cl/s...
        url = f"https://www.falabella.com/falabella-cl/search?Ntt={q}"
        # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
        r = requests.get(url, headers=HEADERS_BROWSER, timeout=8)
        
        # Evaluamos la condición lógica (r.status_code == 200) para controlar el flujo
        if r.status_code == 200:
            # Parseamos el árbol DOM HTML y localizamos el bloque de hidratación JSON de Next.js
            soup = BeautifulSoup(r.text, 'html.parser')
            # Extracción y análisis de nodos del árbol DOM HTML mediante BeautifulSoup
            tag = soup.find('script', id='__NEXT_DATA__')
            # Evaluamos la condición lógica (tag and tag.string) para controlar el flujo
            if tag and tag.string:
                # Procesamiento de serialización o deserialización de estructura JSON
                data = json.loads(tag.string)
                # Asignamos 'results' con data.get('props', {}).get('pageProps', {})...
                results = data.get('props', {}).get('pageProps', {}).get('results', [])
                # Recorremos iterativamente cada 'res' en results
                for res in results:
                    # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
                    name = res.get('displayName', '')
                    # Filtramos productos no válidos y validamos correspondencia de entidad
                    if not es_producto_perfume_valido(name):
                        # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                        continue
                    # Evaluamos la condición lógica (not coincide_con_perfume(name, nombre_perfume, marca)) para controlar el flujo
                    if not coincide_con_perfume(name, nombre_perfume, marca):
                        # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                        continue
                    # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
                    p_url = res.get('url')
                    # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
                    prices = res.get('prices', [])
                    # Evaluamos la condición lógica (prices and p_url) para controlar el flujo
                    if prices and p_url:
                        # Extraemos el primer precio disponible y lo convertimos a entero CLP
                        raw_p = prices[0].get('price', ['0'])[0]
                        # Asignamos 'precio' con clean_price_str(raw_p)
                        precio = clean_price_str(raw_p)
                        # Evaluamos la condición lógica (precio >= 10000) para controlar el flujo
                        if precio >= 10000:
                            # Retornamos el resultado procesado ((p_url, precio))
                            return p_url, precio
    except Exception as e:
        # Registro de evento diagnóstico en la bitácora (logger) del sistema
        logger.warning(f"Error buscando Falabella para '{nombre_perfume}': {e}")
    # Retornamos el resultado procesado ((None, None))
    return None, None


# Definición de función 'buscar_paris' (parámetros: nombre_perfume, marca)
def buscar_paris(nombre_perfume: str, marca: str = "") -> tuple:
    """
    Busca en Paris.cl localizando el enlace del producto y extrayendo metadatos Schema.org.
    """
    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Construimos la consulta de búsqueda para Paris.cl (incluyendo Marketplace)
        query_str = f"{marca} {nombre_perfume}".strip() if (marca and marca.lower() not in nombre_perfume.lower()) else nombre_perfume.strip()
        # Asignamos 'q' con urllib.parse.quote(query_str)
        q = urllib.parse.quote(query_str)
        # Asignamos 'search_url' con f'https://www.paris.cl/search?q={q}'
        search_url = f"https://www.paris.cl/search?q={q}"
        # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
        r = requests.get(search_url, headers=HEADERS_BROWSER, timeout=8)
        
        # Evaluamos la condición lógica (r.status_code == 200) para controlar el flujo
        if r.status_code == 200:
            # Extracción y análisis de nodos del árbol DOM HTML mediante BeautifulSoup
            soup = BeautifulSoup(r.text, 'html.parser')
            # Recorremos los enlaces de productos (.html) devueltos en la grilla de resultados
            for a in soup.find_all('a', href=True):
                # Asignamos 'href' con a.get('href', '')
                href = a.get('href', '')
                # Evaluamos la condición lógica ('.html' in href and (not any((k in href.lower() for ...) para controlar el flujo
                if '.html' in href and not any(k in href.lower() for k in ["login", "cart", "micuenta"]):
                    # Asignamos 'clean_url' con 'https://www.paris.cl' + href.split('?')[0]
                    clean_url = "https://www.paris.cl" + href.split('?')[0]
                    # Descargamos la ficha del producto candidato para leer su JSON-LD Schema.org
                    r_prod = requests.get(clean_url, headers=HEADERS_BROWSER, timeout=6)
                    # Evaluamos la condición lógica (r_prod.status_code == 200) para controlar el flujo
                    if r_prod.status_code == 200:
                        # Recorremos iterativamente cada 'b' en re.findall('<script[^>]*type="application/...
                        for b in re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', r_prod.text, re.S):
                            # Evaluamos la condición lógica ('Product' in b) para controlar el flujo
                            if 'Product' in b:
                                # Procesamiento de serialización o deserialización de estructura JSON
                                d = json.loads(b)
                                # Asignamos 'p_name' con d.get('name', '')
                                p_name = d.get('name', '')
                                # Evaluamos la condición lógica (not es_producto_perfume_valido(p_name)) para controlar el flujo
                                if not es_producto_perfume_valido(p_name):
                                    # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                                    continue
                                # Evaluamos la condición lógica (not coincide_con_perfume(p_name, nombre_perfume, marca)) para controlar el flujo
                                if not coincide_con_perfume(p_name, nombre_perfume, marca):
                                    # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                                    continue
                                # Asignamos 'offers' con d.get('offers', [])
                                offers = d.get('offers', [])
                                # Si Paris entrega múltiples ofertas en JSON-LD (normal, internet, tarjeta), tomamos la menor válida
                                if isinstance(offers, list) and offers:
                                    # Asignamos 'precios_lista' con [int(float(o.get('price', 0))) for o in of...
                                    precios_lista = [
                                        int(float(o.get('price', 0)))
                                        for o in offers
                                        if isinstance(o, dict) and o.get('price') is not None and int(float(o.get('price', 0))) >= 10000
                                    ]
                                    # Evaluamos la condición lógica (precios_lista) para controlar el flujo
                                    if precios_lista:
                                        # Retornamos el resultado procesado ((clean_url, min(precios_lista)))
                                        return clean_url, min(precios_lista)
                                # Evaluamos la condición lógica (isinstance(offers, dict)) para controlar el flujo
                                elif isinstance(offers, dict):
                                    # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
                                    precio = int(float(offers.get('price', 0)))
                                    # Evaluamos la condición lógica (precio >= 10000) para controlar el flujo
                                    if precio >= 10000:
                                        # Retornamos el resultado procesado ((clean_url, precio))
                                        return clean_url, precio
    except Exception as e:
        # Registro de evento diagnóstico en la bitácora (logger) del sistema
        logger.warning(f"Error buscando Paris para '{nombre_perfume}': {e}")
    # Retornamos el resultado procesado ((None, None))
    return None, None


# Definición de función 'buscar_ripley' (parámetros: nombre_perfume, marca)
def buscar_ripley(nombre_perfume: str, marca: str = "") -> tuple:
    """
    Busca en simple.ripley.cl validando correspondencia estricta antes de aceptar enlaces directos.
    """
    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Construimos la URL de búsqueda en Ripley Chile
        query_str = f"{marca} {nombre_perfume}".strip() if (marca and marca.lower() not in nombre_perfume.lower()) else nombre_perfume.strip()
        # Asignamos 'q' con urllib.parse.quote(query_str)
        q = urllib.parse.quote(query_str)
        # Asignamos 'search_url' con f'https://simple.ripley.cl/search/{q}'
        search_url = f"https://simple.ripley.cl/search/{q}"
        # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
        r = requests.get(search_url, headers=HEADERS_BROWSER, timeout=8)
        
        # Evaluamos la condición lógica (r.status_code == 200) para controlar el flujo
        if r.status_code == 200:
            # Extracción y análisis de nodos del árbol DOM HTML mediante BeautifulSoup
            soup = BeautifulSoup(r.text, 'html.parser')
            # Buscamos enlaces hacia fichas de producto en el DOM de Ripley
            for a in soup.find_all('a', href=True):
                # Asignamos 'href' con a.get('href', '')
                href = a.get('href', '')
                # Asignamos 'clean_href' con href.split('?')[0]
                clean_href = href.split('?')[0]
                # Evaluamos la condición lógica (clean_href.endswith('p') or '-mpm' in clean_href.low...) para controlar el flujo
                if clean_href.endswith('p') or '-mpm' in clean_href.lower():
                    # Asignamos 'clean_url' con 'https://simple.ripley.cl' + clean_href
                    clean_url = "https://simple.ripley.cl" + clean_href
                    # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
                    r_prod = requests.get(clean_url, headers=HEADERS_BROWSER, timeout=6)
                    # Evaluamos la condición lógica (r_prod.status_code == 200) para controlar el flujo
                    if r_prod.status_code == 200:
                        # Extracción y análisis de nodos del árbol DOM HTML mediante BeautifulSoup
                        soup_p = BeautifulSoup(r_prod.text, 'html.parser')
                        # Validar nombre del producto en el PDP
                        name_tag = soup_p.find('h1') or soup_p.find(class_=lambda c: c and 'product-name' in c)
                        # Asignamos 'prod_title' con name_tag.get_text().strip() if name_tag el...
                        prod_title = name_tag.get_text().strip() if name_tag else clean_href.replace('-', ' ')
                        # Evaluamos la condición lógica (not es_producto_perfume_valido(prod_title)) para controlar el flujo
                        if not es_producto_perfume_valido(prod_title):
                            # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                            continue
                        # Evaluamos la condición lógica (not coincide_con_perfume(prod_title, nombre_perfume,...) para controlar el flujo
                        if not coincide_con_perfume(prod_title, nombre_perfume, marca):
                            # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                            continue
                        # Extracción y análisis de nodos del árbol DOM HTML mediante BeautifulSoup
                        p_val = soup_p.find(class_=lambda c: c and 'price-value' in c)
                        # Evaluamos la condición lógica (p_val) para controlar el flujo
                        if p_val:
                            # Asignamos 'precio' con clean_price_str(p_val.get_text())
                            precio = clean_price_str(p_val.get_text())
                            # Evaluamos la condición lógica (precio >= 10000) para controlar el flujo
                            if precio >= 10000:
                                # Retornamos el resultado procesado ((clean_url, precio))
                                return clean_url, precio
    except Exception as e:
        # Registro de evento diagnóstico en la bitácora (logger) del sistema
        logger.warning(f"Error buscando Ripley para '{nombre_perfume}': {e}")
    # Retornamos el resultado procesado ((None, None))
    return None, None


# =============================================================================
# BLOQUE 3: ORQUESTADOR PRINCIPAL (ETL de Sincronización)
# =============================================================================

def main():
    """
    Función Principal:
    1. Carga el catálogo semilla de perfumes desde 'database/seed_catalogo.json'.
    2. Itera sobre cada perfume y consulta sus tiendas asociadas en vivo.
    3. Si encuentra un link directo y precio real en vivo, actualiza los datos.
    4. Guarda los resultados en el JSON y re-inicializa la base de datos local SQLite.
    """
    # Asignamos 'base_dir' con os.path.dirname(os.path.dirname(os.path.ab...
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # Asignamos 'seed_path' con os.path.join(base_dir, 'database', 'seed_c...
    seed_path = os.path.join(base_dir, "database", "seed_catalogo.json")

    # 1. Lectura del archivo JSON de catálogo
    with open(seed_path, "r", encoding="utf-8") as f:
        # Procesamiento de serialización o deserialización de estructura JSON
        catalogo = json.load(f)

    # Registro de evento diagnóstico en la bitácora (logger) del sistema
    logger.info(f"Iniciando sincronización para {len(catalogo['perfumes'])} perfumes...")

    # Asignamos 'actualizados' con 0
    actualizados = 0

    # 2. Bucle de procesamiento por perfume
    for p in catalogo["perfumes"]:
        # Asignamos 'nombre' con p['nombre']
        nombre = p["nombre"]
        # Asignamos 'marca' con p['marca']
        marca = p["marca"]
        # Registro de evento diagnóstico en la bitácora (logger) del sistema
        logger.info(f"--- Procesando: {nombre} ({marca}) ---")

        # 3. Recorremos cada tienda registrada para este perfume
        for enlace in p.get("enlaces_tiendas", []):
            # Asignamos 'tienda' con enlace['tienda']
            tienda = enlace["tienda"]
            # Asignamos '(url_res, precio_res)' con (None, None)
            url_res, precio_res = None, None

            # Enrutamiento según el comercio correspondiente
            if tienda == "Falabella":
                # Asignamos '(url_res, precio_res)' con buscar_falabella(nombre, marca)
                url_res, precio_res = buscar_falabella(nombre, marca)
            # Evaluamos la condición lógica (tienda == 'Paris') para controlar el flujo
            elif tienda == "Paris":
                # Asignamos '(url_res, precio_res)' con buscar_paris(nombre, marca)
                url_res, precio_res = buscar_paris(nombre, marca)
            # Evaluamos la condición lógica (tienda == 'Ripley') para controlar el flujo
            elif tienda == "Ripley":
                # Asignamos '(url_res, precio_res)' con buscar_ripley(nombre, marca)
                url_res, precio_res = buscar_ripley(nombre, marca)
            # Evaluamos la condición lógica (tienda == 'Silk Perfumes') para controlar el flujo
            elif tienda == "Silk Perfumes":
                # Asignamos '(url_res, precio_res)' con buscar_silk(nombre, marca)
                url_res, precio_res = buscar_silk(nombre, marca)
            # Evaluamos la condición lógica (tienda == 'Elite Perfumes') para controlar el flujo
            elif tienda == "Elite Perfumes":
                # Asignamos '(url_res, precio_res)' con buscar_elite(nombre, marca)
                url_res, precio_res = buscar_elite(nombre, marca)

            # Si encontramos URL directa, la guardamos
            if url_res:
                # Asignamos 'enlace['url_producto']' con url_res
                enlace["url_producto"] = url_res
                # Registro de evento diagnóstico en la bitácora (logger) del sistema
                logger.info(f"  [{tienda}] Link directo: {url_res}")
            
            # Si encontramos un precio real confirmado, actualizamos el catálogo
            if precio_res and precio_res >= 10000:
                # Asignamos 'enlace['precio_actual']' con precio_res
                enlace["precio_actual"] = precio_res
                # Si no existía precio normal o era menor, preservamos coherencia
                p_norm_exist = enlace.get("precio_normal")
                # Asignamos 'enlace['precio_normal']' con p_norm_exist if p_norm_exist and p_norm_ex...
                enlace["precio_normal"] = p_norm_exist if (p_norm_exist and p_norm_exist > precio_res) else precio_res
                # Registro de evento diagnóstico en la bitácora (logger) del sistema
                logger.info(f"  [{tienda}] Precio real actualizado: ${precio_res:,} CLP (Normal: ${enlace['precio_normal']:,})")
                # Actualizamos acumulativamente el valor de 'actualizados'
                actualizados += 1

    # 4. Guardamos el catálogo actualizado con indentación limpia
    with open(seed_path, "w", encoding="utf-8") as f:
        # Procesamiento de serialización o deserialización de estructura JSON
        json.dump(catalogo, f, ensure_ascii=False, indent=2)

    # Registro de evento diagnóstico en la bitácora (logger) del sistema
    logger.info("Catálogo maestro seed_catalogo.json actualizado con éxito.")

    # 5. Sincronizamos la base de datos local SQLite con los nuevos datos
    sys.path.insert(0, base_dir)
    # Importación de componentes (init_db) desde el módulo 'backend.database'
    from backend.database import init_db
    # Ejecutamos instrucción: init_db(force_reseed=True)
    init_db(force_reseed=True)
    # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
    logger.info("Base de datos SQLite sincronizada con precios reales y links directos.")


# Punto de entrada si se ejecuta directamente desde terminal
if __name__ == "__main__":
    # Ejecutamos instrucción: main()
    main()
