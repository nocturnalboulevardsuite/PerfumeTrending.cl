"""
PerfumeTrending.cl — Sincronizador de Precios Reales y Enlaces Directos
========================================================================
Extrae URLs directas a la ficha del producto y precios 100% reales en vivo
para todas las tiendas (Falabella, Paris, Ripley, Silk Perfumes, Elite Perfumes).
"""

import json
import logging
import os
import re
import sys
import urllib.parse
import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SyncPreciosReales")

HEADERS_BROWSER = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept-Language': 'es-CL,es;q=0.9,en;q=0.8',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

HEADERS_API = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json',
}


def clean_price_str(val_str: str) -> int:
    """Convierte '$ 188.100' o '188100' a entero."""
    digits = re.sub(r'[^\d]', '', str(val_str))
    return int(digits) if digits else 0


def buscar_silk(nombre_perfume: str) -> tuple:
    """Busca en Silk Perfumes vía Shopify Suggest API."""
    try:
        q = urllib.parse.quote(nombre_perfume)
        url = f"https://www.silkperfumes.cl/search/suggest.json?q={q}&resources[type]=product"
        r = requests.get(url, headers=HEADERS_API, timeout=6)
        if r.status_code == 200:
            prods = r.json().get('resources', {}).get('results', {}).get('products', [])
            for p in prods:
                title = p.get('title', '').lower()
                # Verificar coincidencia básica
                tokens = [t.lower() for t in nombre_perfume.split() if len(t) > 3]
                if any(tok in title for tok in tokens):
                    p_url = "https://www.silkperfumes.cl" + p.get('url', '').split('?')[0]
                    precio = int(float(p.get('price', 0)))
                    return p_url, precio
    except Exception as e:
        logger.warning(f"Error buscando Silk para '{nombre_perfume}': {e}")
    return None, None


def buscar_elite(nombre_perfume: str) -> tuple:
    """Busca en Elite Perfumes vía Shopify Suggest API."""
    try:
        q = urllib.parse.quote(nombre_perfume)
        url = f"https://www.eliteperfumes.cl/search/suggest.json?q={q}&resources[type]=product"
        r = requests.get(url, headers=HEADERS_API, timeout=6)
        if r.status_code == 200:
            prods = r.json().get('resources', {}).get('results', {}).get('products', [])
            for p in prods:
                title = p.get('title', '').lower()
                tokens = [t.lower() for t in nombre_perfume.split() if len(t) > 3]
                if any(tok in title for tok in tokens):
                    p_url = "https://www.eliteperfumes.cl" + p.get('url', '').split('?')[0]
                    precio = int(float(p.get('price', 0)))
                    return p_url, precio
    except Exception as e:
        logger.warning(f"Error buscando Elite para '{nombre_perfume}': {e}")
    return None, None


def buscar_falabella(nombre_perfume: str) -> tuple:
    """Busca en Falabella extrayendo __NEXT_DATA__."""
    try:
        q = urllib.parse.quote(nombre_perfume)
        url = f"https://www.falabella.com/falabella-cl/search?Ntt={q}"
        r = requests.get(url, headers=HEADERS_BROWSER, timeout=8)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            tag = soup.find('script', id='__NEXT_DATA__')
            if tag and tag.string:
                data = json.loads(tag.string)
                results = data.get('props', {}).get('pageProps', {}).get('results', [])
                for res in results:
                    name = res.get('displayName', '').lower()
                    tokens = [t.lower() for t in nombre_perfume.split() if len(t) > 3]
                    if any(tok in name for tok in tokens):
                        p_url = res.get('url')
                        prices = res.get('prices', [])
                        if prices and p_url:
                            # Preferir internetPrice o normalPrice
                            raw_p = prices[0].get('price', ['0'])[0]
                            precio = clean_price_str(raw_p)
                            if precio >= 10000:
                                return p_url, precio
    except Exception as e:
        logger.warning(f"Error buscando Falabella para '{nombre_perfume}': {e}")
    return None, None


def buscar_paris(nombre_perfume: str) -> tuple:
    """Busca en Paris extrayendo ficha directa y JSON-LD."""
    try:
        q = urllib.parse.quote(nombre_perfume)
        search_url = f"https://www.paris.cl/search?q={q}"
        r = requests.get(search_url, headers=HEADERS_BROWSER, timeout=8)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            for a in soup.find_all('a', href=True):
                href = a.get('href', '')
                tokens = [t.lower() for t in nombre_perfume.split() if len(t) > 3]
                if any(tok in href.lower() for tok in tokens) and '.html' in href:
                    clean_url = "https://www.paris.cl" + href.split('?')[0]
                    # Abrir página para sacar precio JSON-LD
                    r_prod = requests.get(clean_url, headers=HEADERS_BROWSER, timeout=6)
                    if r_prod.status_code == 200:
                        for b in re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', r_prod.text, re.S):
                            if 'Product' in b:
                                d = json.loads(b)
                                offers = d.get('offers', [])
                                if isinstance(offers, list) and offers:
                                    precio = int(float(offers[0].get('price', 0)))
                                    if precio >= 10000:
                                        return clean_url, precio
                                elif isinstance(offers, dict):
                                    precio = int(float(offers.get('price', 0)))
                                    if precio >= 10000:
                                        return clean_url, precio
                    return clean_url, None
    except Exception as e:
        logger.warning(f"Error buscando Paris para '{nombre_perfume}': {e}")
    return None, None


def buscar_ripley(nombre_perfume: str) -> tuple:
    """Busca en Ripley extrayendo ficha directa y precio de página."""
    try:
        q = urllib.parse.quote(nombre_perfume)
        search_url = f"https://simple.ripley.cl/search/{q}"
        r = requests.get(search_url, headers=HEADERS_BROWSER, timeout=8)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            for a in soup.find_all('a', href=True):
                href = a.get('href', '')
                clean_href = href.split('?')[0]
                tokens = [t.lower() for t in nombre_perfume.split() if len(t) > 3]
                if any(tok in clean_href.lower() for tok in tokens) and clean_href.endswith('p'):
                    clean_url = "https://simple.ripley.cl" + clean_href
                    r_prod = requests.get(clean_url, headers=HEADERS_BROWSER, timeout=6)
                    if r_prod.status_code == 200:
                        soup_p = BeautifulSoup(r_prod.text, 'html.parser')
                        p_val = soup_p.find(class_=lambda c: c and 'price-value' in c)
                        if p_val:
                            precio = clean_price_str(p_val.get_text())
                            if precio >= 10000:
                                return clean_url, precio
                    return clean_url, None
    except Exception as e:
        logger.warning(f"Error buscando Ripley para '{nombre_perfume}': {e}")
    return None, None


def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    seed_path = os.path.join(base_dir, "database", "seed_catalogo.json")

    with open(seed_path, "r", encoding="utf-8") as f:
        catalogo = json.load(f)

    logger.info(f"Iniciando sincronización para {len(catalogo['perfumes'])} perfumes...")

    actualizados = 0

    for p in catalogo["perfumes"]:
        nombre = p["nombre"]
        marca = p["marca"]
        busqueda = f"{marca} {nombre}"
        logger.info(f"--- Procesando: {nombre} ({marca}) ---")

        for enlace in p.get("enlaces_tiendas", []):
            tienda = enlace["tienda"]
            url_res, precio_res = None, None

            if tienda == "Falabella":
                url_res, precio_res = buscar_falabella(busqueda)
            elif tienda == "Paris":
                url_res, precio_res = buscar_paris(busqueda)
            elif tienda == "Ripley":
                url_res, precio_res = buscar_ripley(busqueda)
            elif tienda == "Silk Perfumes":
                url_res, precio_res = buscar_silk(nombre)
            elif tienda == "Elite Perfumes":
                url_res, precio_res = buscar_elite(nombre)

            if url_res:
                enlace["url_producto"] = url_res
                logger.info(f"  [{tienda}] Link directo: {url_res}")
            
            if precio_res and precio_res >= 10000:
                enlace["precio_actual"] = precio_res
                # Solo mantener precio_normal si ya tiene un descuento real superior
                p_norm_exist = enlace.get("precio_normal")
                enlace["precio_normal"] = p_norm_exist if (p_norm_exist and p_norm_exist > precio_res) else precio_res
                logger.info(f"  [{tienda}] Precio real actualizado: ${precio_res:,} CLP (Normal: ${enlace['precio_normal']:,})")
                actualizados += 1

    with open(seed_path, "w", encoding="utf-8") as f:
        json.dump(catalogo, f, ensure_ascii=False, indent=2)

    logger.info("Catálogo maestro seed_catalogo.json actualizado con éxito.")

    # Re-sembrar la base de datos SQLite local
    sys.path.insert(0, base_dir)
    from backend.database import init_db
    init_db(force_reseed=True)
    logger.info("Base de datos SQLite sincronizada con precios reales y links directos.")


if __name__ == "__main__":
    main()
