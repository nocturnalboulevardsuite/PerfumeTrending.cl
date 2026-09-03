"""
PerfumeTrending — Demo de Web Scraping
----------------------------------------
Script simple que demuestra las técnicas descritas en la Fase 1 del proyecto:
  - Código modular (funciones separadas por responsabilidad)
  - Manejo robusto de errores (try/except)
  - Selectores flexibles (con fallback si uno falla)
  - Rotación de User-Agents (cabeceras)
  - Validación básica de datos extraídos

Sitio usado: https://books.toscrape.com
Este es un sitio público diseñado específicamente para practicar scraping
de forma legal y sin restricciones, ya que no es una tienda real.
La misma lógica se aplicaría luego a tiendas de perfumería chilenas.
"""

import requests
from bs4 import BeautifulSoup
import random
import time
import csv
import re

# ----------------------------------------------------------------------
# 1. Configuración: rotación de User-Agents
# ----------------------------------------------------------------------
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

BASE_URL = "https://books.toscrape.com/"


def obtener_headers():
    """Devuelve cabeceras con un User-Agent aleatorio en cada solicitud."""
    return {"User-Agent": random.choice(USER_AGENTS)}


# ----------------------------------------------------------------------
# 2. Descarga de la página con manejo de errores
# ----------------------------------------------------------------------
def descargar_pagina(url):
    """
    Descarga el HTML de una URL.
    Si falla (timeout, error de conexión, código HTTP distinto de 200),
    devuelve None en vez de detener todo el programa.
    """
    try:
        respuesta = requests.get(url, headers=obtener_headers(), timeout=10)
        respuesta.raise_for_status()  # lanza error si el código HTTP es 4xx/5xx
        respuesta.encoding = "utf-8"
        return respuesta.text
    except requests.exceptions.Timeout:
        print(f"[ERROR] Timeout al conectar con {url}")
    except requests.exceptions.HTTPError as err:
        print(f"[ERROR] Error HTTP en {url}: {err}")
    except requests.exceptions.RequestException as err:
        print(f"[ERROR] Fallo de conexión en {url}: {err}")
    return None


# ----------------------------------------------------------------------
# 3. Selectores flexibles: intenta varias formas de encontrar un dato
# ----------------------------------------------------------------------
def extraer_texto_flexible(elemento, selectores):
    """
    Prueba una lista de selectores en orden hasta encontrar uno que funcione.
    Simula lo que pasaría si una tienda cambia el nombre de una clase CSS:
    el scraper no se rompe, solo prueba la siguiente alternativa.
    """
    for selector in selectores:
        encontrado = elemento.select_one(selector)
        if encontrado:
            return encontrado.get_text(strip=True)
    return None  # ningún selector funcionó -> se marca como dato faltante


# ----------------------------------------------------------------------
# 4. Extracción y validación de un producto individual
# ----------------------------------------------------------------------
def extraer_producto(card):
    """
    Extrae nombre, precio y disponibilidad de un producto.
    Valida que los datos tengan sentido antes de aceptarlos.
    """
    nombre = extraer_texto_flexible(card, ["h3 a", ".product_pod h3 a", "a[title]"])
    precio_texto = extraer_texto_flexible(card, [".price_color", ".product_price .price_color"])
    disponibilidad = extraer_texto_flexible(card, [".availability", ".instock.availability"])

    # Validación simple: si falta el nombre o el precio, el registro es sospechoso
    if not nombre or not precio_texto:
        print("[AVISO] Producto con datos incompletos, se omite.")
        return None

    # Limpieza robusta del precio extrayendo solo números y punto decimal
    match = re.search(r"[\d.]+", precio_texto)
    if not match:
        print(f"[AVISO] Precio con formato inesperado: {precio_texto}")
        return None

    try:
        precio = float(match.group(0))
    except ValueError:
        print(f"[AVISO] No se pudo convertir el precio a número: {precio_texto}")
        return None

    return {
        "nombre": nombre,
        "precio": precio,
        "disponibilidad": disponibilidad or "Desconocida",
    }


# ----------------------------------------------------------------------
# 5. Orquestador principal: recorre la página y guarda resultados
# ----------------------------------------------------------------------
def scrapear_catalogo(url, limite_paginas=2):
    productos = []

    for pagina in range(1, limite_paginas + 1):
        url_pagina = f"{url}catalogue/page-{pagina}.html" if pagina > 1 else url
        print(f"\nDescargando página {pagina}: {url_pagina}")

        html = descargar_pagina(url_pagina)
        if html is None:
            print(f"[ERROR] No se pudo obtener la página {pagina}, se continúa con la siguiente.")
            continue

        soup = BeautifulSoup(html, "html.parser")
        tarjetas = soup.select(".product_pod")

        if not tarjetas:
            print(f"[AVISO] No se encontraron productos en la página {pagina}. "
                  f"Posible cambio de estructura (DOM).")
            continue

        for card in tarjetas:
            producto = extraer_producto(card)
            if producto:
                productos.append(producto)

        # Pausa entre solicitudes para no sobrecargar el servidor
        time.sleep(random.uniform(1, 2))

    return productos


# ----------------------------------------------------------------------
# 6. Guardar resultados en CSV
# ----------------------------------------------------------------------
def guardar_csv(productos, nombre_archivo="productos.csv"):
    if not productos:
        print("[AVISO] No hay productos para guardar.")
        return

    with open(nombre_archivo, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["nombre", "precio", "disponibilidad"])
        writer.writeheader()
        writer.writerows(productos)

    print(f"\n[OK] {len(productos)} productos guardados en {nombre_archivo}")


# ----------------------------------------------------------------------
# Punto de entrada
# ----------------------------------------------------------------------
if __name__ == "__main__":
    print("=== Demo de Web Scraping — PerfumeTrending ===")
    resultados = scrapear_catalogo(BASE_URL, limite_paginas=2)

    print(f"\nTotal de productos extraídos: {len(resultados)}")
    for p in resultados[:5]:
        print(f" - {p['nombre']} | ${p['precio']} | {p['disponibilidad']}")

    guardar_csv(resultados)
