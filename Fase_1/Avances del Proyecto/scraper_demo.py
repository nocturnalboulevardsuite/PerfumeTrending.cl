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

# Importación de librería estándar o dependencia externa (requests)
import requests
# Importación de componentes (BeautifulSoup) desde el módulo 'bs4'
from bs4 import BeautifulSoup
# Importación de librería estándar o dependencia externa (random)
import random
# Importación de librería estándar o dependencia externa (time)
import time
# Importación de librería estándar o dependencia externa (csv)
import csv
# Importación de librería estándar o dependencia externa (re)
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

# Asignamos 'BASE_URL' con 'https://books.toscrape.com/'
BASE_URL = "https://books.toscrape.com/"


# Definición de función 'obtener_headers' sin parámetros externos
def obtener_headers():
    """Devuelve cabeceras con un User-Agent aleatorio en cada solicitud."""
    # Retornamos el resultado procesado ({'User-Agent': random.choice(USER_AGENTS)})
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
    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
        respuesta = requests.get(url, headers=obtener_headers(), timeout=10)
        # Ejecutamos instrucción: respuesta.raise_for_status()
        respuesta.raise_for_status()  # lanza error si el código HTTP es 4xx/5xx
        # Asignamos 'respuesta.encoding' con 'utf-8'
        respuesta.encoding = "utf-8"
        # Retornamos el resultado procesado (respuesta.text)
        return respuesta.text
    except requests.exceptions.Timeout:
        # Ejecutamos instrucción: print(f'[ERROR] Timeout al conectar con {url}')
        print(f"[ERROR] Timeout al conectar con {url}")
    except requests.exceptions.HTTPError as err:
        # Ejecutamos instrucción: print(f'[ERROR] Error HTTP en {url}: {err}')
        print(f"[ERROR] Error HTTP en {url}: {err}")
    except requests.exceptions.RequestException as err:
        # Ejecutamos instrucción: print(f'[ERROR] Fallo de conexión en {url}: {err}')
        print(f"[ERROR] Fallo de conexión en {url}: {err}")
    # Retornamos el resultado procesado (None)
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
    # Recorremos iterativamente cada 'selector' en selectores
    for selector in selectores:
        # Asignamos 'encontrado' con elemento.select_one(selector)
        encontrado = elemento.select_one(selector)
        # Evaluamos la condición lógica (encontrado) para controlar el flujo
        if encontrado:
            # Retornamos el resultado procesado (encontrado.get_text(strip=True))
            return encontrado.get_text(strip=True)
    # Retornamos el resultado procesado (None)
    return None  # ningún selector funcionó -> se marca como dato faltante


# ----------------------------------------------------------------------
# 4. Extracción y validación de un producto individual
# ----------------------------------------------------------------------
def extraer_producto(card):
    """
    Extrae nombre, precio y disponibilidad de un producto.
    Valida que los datos tengan sentido antes de aceptarlos.
    """
    # Asignamos 'nombre' con extraer_texto_flexible(card, ['h3 a', '.pr...
    nombre = extraer_texto_flexible(card, ["h3 a", ".product_pod h3 a", "a[title]"])
    # Asignamos 'precio_texto' con extraer_texto_flexible(card, ['.price_colo...
    precio_texto = extraer_texto_flexible(card, [".price_color", ".product_price .price_color"])
    # Asignamos 'disponibilidad' con extraer_texto_flexible(card, ['.availabili...
    disponibilidad = extraer_texto_flexible(card, [".availability", ".instock.availability"])

    # Validación simple: si falta el nombre o el precio, el registro es sospechoso
    if not nombre or not precio_texto:
        # Ejecutamos instrucción: print('[AVISO] Producto con datos incompletos, se om...
        print("[AVISO] Producto con datos incompletos, se omite.")
        # Retornamos el resultado procesado (None)
        return None

    # Limpieza robusta del precio extrayendo solo números y punto decimal
    match = re.search(r"[\d.]+", precio_texto)
    # Evaluamos la condición lógica (not match) para controlar el flujo
    if not match:
        # Ejecutamos instrucción: print(f'[AVISO] Precio con formato inesperado: {prec...
        print(f"[AVISO] Precio con formato inesperado: {precio_texto}")
        # Retornamos el resultado procesado (None)
        return None

    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Asignamos 'precio' con float(match.group(0))
        precio = float(match.group(0))
    except ValueError:
        # Ejecutamos instrucción: print(f'[AVISO] No se pudo convertir el precio a núm...
        print(f"[AVISO] No se pudo convertir el precio a número: {precio_texto}")
        # Retornamos el resultado procesado (None)
        return None

    # Retornamos el resultado procesado ({'nombre': nombre, 'precio': precio, 'disponibi...)
    return {
        "nombre": nombre,
        "precio": precio,
        "disponibilidad": disponibilidad or "Desconocida",
    }


# ----------------------------------------------------------------------
# 5. Orquestador principal: recorre la página y guarda resultados
# ----------------------------------------------------------------------
def scrapear_catalogo(url, limite_paginas=2):
    # Asignamos 'productos' con []
    productos = []

    # Recorremos iterativamente cada 'pagina' en range(1, limite_paginas + 1)
    for pagina in range(1, limite_paginas + 1):
        # Asignamos 'url_pagina' con f'{url}catalogue/page-{pagina}.html' if pa...
        url_pagina = f"{url}catalogue/page-{pagina}.html" if pagina > 1 else url
        # Ejecutamos instrucción: print(f'\nDescargando página {pagina}: {url_pagina}')
        print(f"\nDescargando página {pagina}: {url_pagina}")

        # Asignamos 'html' con descargar_pagina(url_pagina)
        html = descargar_pagina(url_pagina)
        # Evaluamos la condición lógica (html is None) para controlar el flujo
        if html is None:
            # Ejecutamos instrucción: print(f'[ERROR] No se pudo obtener la página {pagina...
            print(f"[ERROR] No se pudo obtener la página {pagina}, se continúa con la siguiente.")
            # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
            continue

        # Extracción y análisis de nodos del árbol DOM HTML mediante BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        # Asignamos 'tarjetas' con soup.select('.product_pod')
        tarjetas = soup.select(".product_pod")

        # Evaluamos la condición lógica (not tarjetas) para controlar el flujo
        if not tarjetas:
            # Ejecutamos instrucción: print(f'[AVISO] No se encontraron productos en la pá...
            print(f"[AVISO] No se encontraron productos en la página {pagina}. "
                  f"Posible cambio de estructura (DOM).")
            # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
            continue

        # Recorremos iterativamente cada 'card' en tarjetas
        for card in tarjetas:
            # Asignamos 'producto' con extraer_producto(card)
            producto = extraer_producto(card)
            # Evaluamos la condición lógica (producto) para controlar el flujo
            if producto:
                # Ejecutamos instrucción: productos.append(producto)
                productos.append(producto)

        # Pausa entre solicitudes para no sobrecargar el servidor
        time.sleep(random.uniform(1, 2))

    # Retornamos el resultado procesado (productos)
    return productos


# ----------------------------------------------------------------------
# 6. Guardar resultados en CSV
# ----------------------------------------------------------------------
def guardar_csv(productos, nombre_archivo="productos.csv"):
    # Evaluamos la condición lógica (not productos) para controlar el flujo
    if not productos:
        # Ejecutamos instrucción: print('[AVISO] No hay productos para guardar.')
        print("[AVISO] No hay productos para guardar.")
        # Finalizamos la ejecución de la función retornando None
        return

    # Gestión automática de contexto y recursos para: open(nombre_archivo, 'w', newline='', encoding=...
    with open(nombre_archivo, "w", newline="", encoding="utf-8") as f:
        # Asignamos 'writer' con csv.DictWriter(f, fieldnames=['nombre', 'p...
        writer = csv.DictWriter(f, fieldnames=["nombre", "precio", "disponibilidad"])
        # Ejecutamos instrucción: writer.writeheader()
        writer.writeheader()
        # Ejecutamos instrucción: writer.writerows(productos)
        writer.writerows(productos)

    # Ejecutamos instrucción: print(f'\n[OK] {len(productos)} productos guardados ...
    print(f"\n[OK] {len(productos)} productos guardados en {nombre_archivo}")


# ----------------------------------------------------------------------
# Punto de entrada
# ----------------------------------------------------------------------
if __name__ == "__main__":
    # Ejecutamos instrucción: print('=== Demo de Web Scraping — PerfumeTrending ===')
    print("=== Demo de Web Scraping — PerfumeTrending ===")
    # Asignamos 'resultados' con scrapear_catalogo(BASE_URL, limite_paginas=2)
    resultados = scrapear_catalogo(BASE_URL, limite_paginas=2)

    # Ejecutamos instrucción: print(f'\nTotal de productos extraídos: {len(resulta...
    print(f"\nTotal de productos extraídos: {len(resultados)}")
    # Recorremos iterativamente cada 'p' en resultados[:5]
    for p in resultados[:5]:
        # Ejecutamos instrucción: print(f" - {p['nombre']} | ${p['precio']} | {p['disp...
        print(f" - {p['nombre']} | ${p['precio']} | {p['disponibilidad']}")

    # Ejecutamos instrucción: guardar_csv(resultados)
    guardar_csv(resultados)
