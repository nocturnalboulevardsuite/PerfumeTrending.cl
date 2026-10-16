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

import json
import logging
import os
import re
import sys
import urllib.parse
import requests
from bs4 import BeautifulSoup

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

try:
    from backend.normalizador import coincide_con_perfume, es_producto_perfume_valido
except ImportError:
    from normalizador import coincide_con_perfume, es_producto_perfume_valido

# Configuración del registro de eventos (Logging) para ver en consola qué está pasando paso a paso
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
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


def clean_price_str(val_str: str) -> int:
    """
    Función de utilidad para limpiar texto de precios y convertirlo a un número entero.
    Por ejemplo: transforma '$ 188.100 CLP' o '188.100' en el número entero 188100.
    Si el valor viene vacío o con formato erróneo, retorna 0 de forma segura.
    """
    digits = re.sub(r'[^\d]', '', str(val_str))
    return int(digits) if digits else 0


# =============================================================================
# BLOQUE 1: EXTRACCIÓN EN TIENDAS BASADAS EN SHOPIFY (Silk y Elite Perfumes)
# =============================================================================

def buscar_silk(nombre_perfume: str, marca: str = "") -> tuple:
    """
    Busca un perfume en Silk Perfumes aprovechando el endpoint interno de sugerencias de Shopify.
    Valida estrictamente que el producto devuelto coincida en perfume, marca y sin flankers incompatibles.
    """
    try:
        query_str = f"{marca} {nombre_perfume}".strip() if (marca and marca.lower() not in nombre_perfume.lower()) else nombre_perfume.strip()
        q = urllib.parse.quote(query_str)
        url = f"https://www.silkperfumes.cl/search/suggest.json?q={q}&resources[type]=product"
        
        r = requests.get(url, headers=HEADERS_API, timeout=6)
        if r.status_code == 200:
            prods = r.json().get('resources', {}).get('results', {}).get('products', [])
            for p in prods:
                title = p.get('title', '')
                if not es_producto_perfume_valido(title):
                    continue
                if not coincide_con_perfume(title, nombre_perfume, marca):
                    continue
                p_url = "https://www.silkperfumes.cl" + p.get('url', '').split('?')[0]
                precio = int(float(p.get('price', 0)))
                if precio >= 10000:
                    return p_url, precio
    except Exception as e:
        logger.warning(f"Error buscando Silk para '{nombre_perfume}': {e}")
    return None, None


def buscar_elite(nombre_perfume: str, marca: str = "") -> tuple:
    """
    Busca un perfume en Elite Perfumes utilizando la misma arquitectura Shopify Suggest API.
    Valida estrictamente que el producto coincida con el perfume auditado.
    """
    try:
        query_str = f"{marca} {nombre_perfume}".strip() if (marca and marca.lower() not in nombre_perfume.lower()) else nombre_perfume.strip()
        q = urllib.parse.quote(query_str)
        url = f"https://www.eliteperfumes.cl/search/suggest.json?q={q}&resources[type]=product"
        
        r = requests.get(url, headers=HEADERS_API, timeout=6)
        if r.status_code == 200:
            prods = r.json().get('resources', {}).get('results', {}).get('products', [])
            for p in prods:
                title = p.get('title', '')
                if not es_producto_perfume_valido(title):
                    continue
                if not coincide_con_perfume(title, nombre_perfume, marca):
                    continue
                p_url = "https://www.eliteperfumes.cl" + p.get('url', '').split('?')[0]
                precio = int(float(p.get('price', 0)))
                if precio >= 10000:
                    return p_url, precio
    except Exception as e:
        logger.warning(f"Error buscando Elite para '{nombre_perfume}': {e}")
    return None, None


# =============================================================================
# BLOQUE 2: EXTRACCIÓN EN RETAILERS TRADICIONALES (Falabella, Paris, Ripley)
# =============================================================================

def buscar_falabella(nombre_perfume: str, marca: str = "") -> tuple:
    """
    Extrae productos de Falabella Chile mediante la inspección de __NEXT_DATA__.
    Valida con precisión estricta de entidad y marca (evita flankers como Eros Energy o marcas cruzadas).
    """
    try:
        query_str = f"{marca} {nombre_perfume}".strip() if (marca and marca.lower() not in nombre_perfume.lower()) else nombre_perfume.strip()
        q = urllib.parse.quote(query_str)
        url = f"https://www.falabella.com/falabella-cl/search?Ntt={q}"
        r = requests.get(url, headers=HEADERS_BROWSER, timeout=8)
        
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            tag = soup.find('script', id='__NEXT_DATA__')
            if tag and tag.string:
                data = json.loads(tag.string)
                results = data.get('props', {}).get('pageProps', {}).get('results', [])
                for res in results:
                    name = res.get('displayName', '')
                    if not es_producto_perfume_valido(name):
                        continue
                    if not coincide_con_perfume(name, nombre_perfume, marca):
                        continue
                    p_url = res.get('url')
                    prices = res.get('prices', [])
                    if prices and p_url:
                        raw_p = prices[0].get('price', ['0'])[0]
                        precio = clean_price_str(raw_p)
                        if precio >= 10000:
                            return p_url, precio
    except Exception as e:
        logger.warning(f"Error buscando Falabella para '{nombre_perfume}': {e}")
    return None, None


def buscar_paris(nombre_perfume: str, marca: str = "") -> tuple:
    """
    Busca en Paris.cl localizando el enlace del producto y extrayendo metadatos Schema.org.
    """
    try:
        query_str = f"{marca} {nombre_perfume}".strip() if (marca and marca.lower() not in nombre_perfume.lower()) else nombre_perfume.strip()
        q = urllib.parse.quote(query_str)
        search_url = f"https://www.paris.cl/search?q={q}"
        r = requests.get(search_url, headers=HEADERS_BROWSER, timeout=8)
        
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            for a in soup.find_all('a', href=True):
                href = a.get('href', '')
                if '.html' in href and not any(k in href.lower() for k in ["login", "cart", "micuenta"]):
                    clean_url = "https://www.paris.cl" + href.split('?')[0]
                    r_prod = requests.get(clean_url, headers=HEADERS_BROWSER, timeout=6)
                    if r_prod.status_code == 200:
                        for b in re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', r_prod.text, re.S):
                            if 'Product' in b:
                                d = json.loads(b)
                                p_name = d.get('name', '')
                                if not es_producto_perfume_valido(p_name):
                                    continue
                                if not coincide_con_perfume(p_name, nombre_perfume, marca):
                                    continue
                                offers = d.get('offers', [])
                                if isinstance(offers, list) and offers:
                                    precio = int(float(offers[0].get('price', 0)))
                                    if precio >= 10000:
                                        return clean_url, precio
                                elif isinstance(offers, dict):
                                    precio = int(float(offers.get('price', 0)))
                                    if precio >= 10000:
                                        return clean_url, precio
    except Exception as e:
        logger.warning(f"Error buscando Paris para '{nombre_perfume}': {e}")
    return None, None


def buscar_ripley(nombre_perfume: str, marca: str = "") -> tuple:
    """
    Busca en simple.ripley.cl validando correspondencia estricta antes de aceptar enlaces directos.
    """
    try:
        query_str = f"{marca} {nombre_perfume}".strip() if (marca and marca.lower() not in nombre_perfume.lower()) else nombre_perfume.strip()
        q = urllib.parse.quote(query_str)
        search_url = f"https://simple.ripley.cl/search/{q}"
        r = requests.get(search_url, headers=HEADERS_BROWSER, timeout=8)
        
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            for a in soup.find_all('a', href=True):
                href = a.get('href', '')
                clean_href = href.split('?')[0]
                if clean_href.endswith('p'):
                    clean_url = "https://simple.ripley.cl" + clean_href
                    r_prod = requests.get(clean_url, headers=HEADERS_BROWSER, timeout=6)
                    if r_prod.status_code == 200:
                        soup_p = BeautifulSoup(r_prod.text, 'html.parser')
                        # Validar nombre del producto en el PDP
                        name_tag = soup_p.find('h1') or soup_p.find(class_=lambda c: c and 'product-name' in c)
                        prod_title = name_tag.get_text().strip() if name_tag else clean_href.replace('-', ' ')
                        if not es_producto_perfume_valido(prod_title):
                            continue
                        if not coincide_con_perfume(prod_title, nombre_perfume, marca):
                            continue
                        p_val = soup_p.find(class_=lambda c: c and 'price-value' in c)
                        if p_val:
                            precio = clean_price_str(p_val.get_text())
                            if precio >= 10000:
                                return clean_url, precio
    except Exception as e:
        logger.warning(f"Error buscando Ripley para '{nombre_perfume}': {e}")
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
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    seed_path = os.path.join(base_dir, "database", "seed_catalogo.json")

    # 1. Lectura del archivo JSON de catálogo
    with open(seed_path, "r", encoding="utf-8") as f:
        catalogo = json.load(f)

    logger.info(f"Iniciando sincronización para {len(catalogo['perfumes'])} perfumes...")

    actualizados = 0

    # 2. Bucle de procesamiento por perfume
    for p in catalogo["perfumes"]:
        nombre = p["nombre"]
        marca = p["marca"]
        logger.info(f"--- Procesando: {nombre} ({marca}) ---")

        # 3. Recorremos cada tienda registrada para este perfume
        for enlace in p.get("enlaces_tiendas", []):
            tienda = enlace["tienda"]
            url_res, precio_res = None, None

            # Enrutamiento según el comercio correspondiente
            if tienda == "Falabella":
                url_res, precio_res = buscar_falabella(nombre, marca)
            elif tienda == "Paris":
                url_res, precio_res = buscar_paris(nombre, marca)
            elif tienda == "Ripley":
                url_res, precio_res = buscar_ripley(nombre, marca)
            elif tienda == "Silk Perfumes":
                url_res, precio_res = buscar_silk(nombre, marca)
            elif tienda == "Elite Perfumes":
                url_res, precio_res = buscar_elite(nombre, marca)

            # Si encontramos URL directa, la guardamos
            if url_res:
                enlace["url_producto"] = url_res
                logger.info(f"  [{tienda}] Link directo: {url_res}")
            
            # Si encontramos un precio real confirmado, actualizamos el catálogo
            if precio_res and precio_res >= 10000:
                enlace["precio_actual"] = precio_res
                # Si no existía precio normal o era menor, preservamos coherencia
                p_norm_exist = enlace.get("precio_normal")
                enlace["precio_normal"] = p_norm_exist if (p_norm_exist and p_norm_exist > precio_res) else precio_res
                logger.info(f"  [{tienda}] Precio real actualizado: ${precio_res:,} CLP (Normal: ${enlace['precio_normal']:,})")
                actualizados += 1

    # 4. Guardamos el catálogo actualizado con indentación limpia
    with open(seed_path, "w", encoding="utf-8") as f:
        json.dump(catalogo, f, ensure_ascii=False, indent=2)

    logger.info("Catálogo maestro seed_catalogo.json actualizado con éxito.")

    # 5. Sincronizamos la base de datos local SQLite con los nuevos datos
    sys.path.insert(0, base_dir)
    from backend.database import init_db
    init_db(force_reseed=True)
    logger.info("Base de datos SQLite sincronizada con precios reales y links directos.")


# Punto de entrada si se ejecuta directamente desde terminal
if __name__ == "__main__":
    main()
