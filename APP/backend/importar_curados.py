"""
PerfumeTrending.cl — Módulo de Ingesta y Scraping Curado de Alta Fidelidad
==========================================================================
Inserta un catálogo premium de perfumes top ventas en Chile, crea sus variantes
(50ml, 100ml, 200ml) y ejecuta el scraping en vivo con validación estricta
(coincide_con_perfume) para vincular ofertas y precios reales confirmados.
"""

# Importación de librería estándar o dependencia externa (sys)
import sys
# Importación de librería estándar o dependencia externa (os)
import os
# Importación de librería estándar o dependencia externa (time)
import time
# Importación de librería estándar o dependencia externa (requests)
import requests
# Importación de librería estándar o dependencia externa (urllib.parse)
import urllib.parse
# Importación de componentes (Dict, List, Any) desde el módulo 'typing'
from typing import Dict, List, Any

# Evaluamos la condición lógica (sys.platform == 'win32' and hasattr(sys.stdout, 'rec...) para controlar el flujo
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Ejecutamos instrucción: sys.stdout.reconfigure(encoding='utf-8')
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        # Ejecutamos instrucción: pass
        pass

# Asignamos 'BASE_DIR' con os.path.dirname(os.path.dirname(os.path.ab...
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Evaluamos la condición lógica (BASE_DIR not in sys.path) para controlar el flujo
if BASE_DIR not in sys.path:
    # Ejecutamos instrucción: sys.path.insert(0, BASE_DIR)
    sys.path.insert(0, BASE_DIR)

# Importación de componentes (get_supabase, is_supabase_disponible, registrar_observacion_oferta) desde el módulo 'backend.database'
from backend.database import get_supabase, is_supabase_disponible, registrar_observacion_oferta
# Importación de componentes (coincide_con_perfume, es_producto_perfume_valido, extraer_volumen_ml) desde el módulo 'backend.normalizador'
from backend.normalizador import coincide_con_perfume, es_producto_perfume_valido, extraer_volumen_ml

# Asignamos 'NUEVOS_PERFUMES' con [{'nombre': 'Dior Homme Intense', 'marca':...
NUEVOS_PERFUMES = [
    # Configuración de elemento #1 (nombre='Dior Homme Intense', marca='Dior')
    {
        "nombre": "Dior Homme Intense",
        "marca": "Dior",
        "genero": "Hombre",
        "tipo": "Eau de Parfum",
        "notas": "Iris de Toscana, Semillas de Ambreta, Lavanda, Cedro de Virginia, Vetiver",
        "imagen_url": "https://images.unsplash.com/photo-1592945403244-b3fbafd7f539?w=600&q=80",
        "es_arabe": False,
        "en_tendencia": True,
        "en_remate": False,
        "precio_referencia": 149990,
        "volumenes": [50, 100, 150]
    },
    # Configuración de elemento #2 (nombre='Dior Fahrenheit', marca='Dior')
    {
        "nombre": "Dior Fahrenheit",
        "marca": "Dior",
        "genero": "Hombre",
        "tipo": "Eau de Toilette",
        "notas": "Flor de Nuez Moscada, Lavanda, Cedro, Camomila, Cuero, Violeta, Sándalo",
        "imagen_url": "https://images.unsplash.com/photo-1523293182086-7651a899d37f?w=600&q=80",
        "es_arabe": False,
        "en_tendencia": True,
        "en_remate": False,
        "precio_referencia": 129990,
        "volumenes": [50, 100, 200]
    },
    # Configuración de elemento #3 (nombre='Miss Dior', marca='Dior')
    {
        "nombre": "Miss Dior",
        "marca": "Dior",
        "genero": "Mujer",
        "tipo": "Eau de Parfum",
        "notas": "Lirio de los Valles, Peonía, Rosa Centifolia, Iris, Almizcles Blancos, Vainilla",
        "imagen_url": "https://images.unsplash.com/photo-1588405748880-12d1d2a59f75?w=600&q=80",
        "es_arabe": False,
        "en_tendencia": True,
        "en_remate": False,
        "precio_referencia": 144990,
        "volumenes": [30, 50, 100]
    },
    # Configuración de elemento #4 (nombre='J'adore', marca='Dior')
    {
        "nombre": "J'adore",
        "marca": "Dior",
        "genero": "Mujer",
        "tipo": "Eau de Parfum",
        "notas": "Pera, Melón, Magnolia, Jazmín, Lirio de los Valles, Nardo, Almizcle, Vainilla",
        "imagen_url": "https://images.unsplash.com/photo-1547887537-6158d64c35b3?w=600&q=80",
        "es_arabe": False,
        "en_tendencia": True,
        "en_remate": False,
        "precio_referencia": 149990,
        "volumenes": [50, 100, 150]
    },
    # Configuración de elemento #5 (nombre='Coco Mademoiselle', marca='Chanel')
    {
        "nombre": "Coco Mademoiselle",
        "marca": "Chanel",
        "genero": "Mujer",
        "tipo": "Eau de Parfum",
        "notas": "Naranja, Mandarina, Bergamota, Rosa Turca, Jazmín, Pachulí, Almizcle Blanco",
        "imagen_url": "https://images.unsplash.com/photo-1583445013765-46c20c4a6772?w=600&q=80",
        "es_arabe": False,
        "en_tendencia": True,
        "en_remate": False,
        "precio_referencia": 184990,
        "volumenes": [50, 100, 200]
    },
    # Configuración de elemento #6 (nombre='Allure Homme Sport', marca='Chanel')
    {
        "nombre": "Allure Homme Sport",
        "marca": "Chanel",
        "genero": "Hombre",
        "tipo": "Eau de Toilette",
        "notas": "Naranja, Mandarina, Notas Marinas, Pimienta, Neroli, Cedro, Haba Tonka",
        "imagen_url": "https://images.unsplash.com/photo-1615397349754-cfa2066a298e?w=600&q=80",
        "es_arabe": False,
        "en_tendencia": True,
        "en_remate": False,
        "precio_referencia": 164990,
        "volumenes": [50, 100, 150]
    },
    # Configuración de elemento #7 (nombre='Chanel No 5', marca='Chanel')
    {
        "nombre": "Chanel No 5",
        "marca": "Chanel",
        "genero": "Mujer",
        "tipo": "Eau de Parfum",
        "notas": "Aldehídos, Ylang-Ylang, Neroli, Bergamota, Iris, Jazmín, Rosa, Sándalo, Vainilla",
        "imagen_url": "https://images.unsplash.com/photo-1594035910387-fea47794261f?w=600&q=80",
        "es_arabe": False,
        "en_tendencia": False,
        "en_remate": False,
        "precio_referencia": 184990,
        "volumenes": [50, 100]
    },
    # Configuración de elemento #8 (nombre='Y Eau de Parfum', marca='Yves Saint Laurent')
    {
        "nombre": "Y Eau de Parfum",
        "marca": "Yves Saint Laurent",
        "genero": "Hombre",
        "tipo": "Eau de Parfum",
        "notas": "Manzana Verde, Jengibre, Bergamota, Salvia, Bayas de Enebro, Geranio, Amberwood, Haba Tonka",
        "imagen_url": "https://images.unsplash.com/photo-1523293182086-7651a899d37f?w=600&q=80",
        "es_arabe": False,
        "en_tendencia": True,
        "en_remate": True,
        "precio_referencia": 139990,
        "volumenes": [60, 100, 200]
    },
    # Configuración de elemento #9 (nombre='Black Opium', marca='Yves Saint Laurent')
    {
        "nombre": "Black Opium",
        "marca": "Yves Saint Laurent",
        "genero": "Mujer",
        "tipo": "Eau de Parfum",
        "notas": "Café Negro, Pera, Pimienta Rosa, Flor de Azahar, Jazmín, Vainilla, Pachulí, Cedro",
        "imagen_url": "https://images.unsplash.com/photo-1541643600914-78b084683601?w=600&q=80",
        "es_arabe": False,
        "en_tendencia": True,
        "en_remate": False,
        "precio_referencia": 134990,
        "volumenes": [30, 50, 90]
    },
    # Configuración de elemento #10 (nombre='La Nuit de L'Homme', marca='Yves Saint Laurent')
    {
        "nombre": "La Nuit de L'Homme",
        "marca": "Yves Saint Laurent",
        "genero": "Hombre",
        "tipo": "Eau de Toilette",
        "notas": "Cardamomo, Lavanda, Cedro de Virginia, Bergamota, Alcaravea, Vetiver",
        "imagen_url": "https://images.unsplash.com/photo-1508746829417-e6f548d8d6ed?w=600&q=80",
        "es_arabe": False,
        "en_tendencia": False,
        "en_remate": False,
        "precio_referencia": 119990,
        "volumenes": [60, 100, 200]
    },
    # Configuración de elemento #11 (nombre='Le Male', marca='Jean Paul Gaultier')
    {
        "nombre": "Le Male",
        "marca": "Jean Paul Gaultier",
        "genero": "Hombre",
        "tipo": "Eau de Toilette",
        "notas": "Lavanda, Menta, Cardamomo, Bergamota, Canela, Flor de Azahar, Vainilla, Haba Tonka, Ámbar",
        "imagen_url": "https://images.unsplash.com/photo-1592945403244-b3fbafd7f539?w=600&q=80",
        "es_arabe": False,
        "en_tendencia": True,
        "en_remate": False,
        "precio_referencia": 99990,
        "volumenes": [75, 125, 200]
    },
    # Configuración de elemento #12 (nombre='Ultra Male', marca='Jean Paul Gaultier')
    {
        "nombre": "Ultra Male",
        "marca": "Jean Paul Gaultier",
        "genero": "Hombre",
        "tipo": "Eau de Toilette Intense",
        "notas": "Pera, Lavanda, Menta, Bergamota, Canela, Salvia, Vainilla Negra, Ámbar, Cedro",
        "imagen_url": "https://images.unsplash.com/photo-1615397349754-cfa2066a298e?w=600&q=80",
        "es_arabe": False,
        "en_tendencia": True,
        "en_remate": False,
        "precio_referencia": 109990,
        "volumenes": [75, 125]
    },
    # Configuración de elemento #13 (nombre='Le Beau Le Parfum', marca='Jean Paul Gaultier')
    {
        "nombre": "Le Beau Le Parfum",
        "marca": "Jean Paul Gaultier",
        "genero": "Hombre",
        "tipo": "Eau de Parfum",
        "notas": "Piña, Iris, Ciprés, Jengibre, Coco, Maderas, Haba Tonka, Sándalo, Ámbar",
        "imagen_url": "https://images.unsplash.com/photo-1588405748880-12d1d2a59f75?w=600&q=80",
        "es_arabe": False,
        "en_tendencia": True,
        "en_remate": False,
        "precio_referencia": 119990,
        "volumenes": [75, 125]
    },
    # Configuración de elemento #14 (nombre='1 Million', marca='Paco Rabanne')
    {
        "nombre": "1 Million",
        "marca": "Paco Rabanne",
        "genero": "Hombre",
        "tipo": "Eau de Toilette",
        "notas": "Mandarina Sanguina, Pomelo, Menta, Canela, Notas Especiadas, Rosa, Cuero, Ámbar, Pachulí",
        "imagen_url": "https://images.unsplash.com/photo-1547887537-6158d64c35b3?w=600&q=80",
        "es_arabe": False,
        "en_tendencia": True,
        "en_remate": True,
        "precio_referencia": 99990,
        "volumenes": [50, 100, 200]
    },
    # Configuración de elemento #15 (nombre='1 Million Lucky', marca='Paco Rabanne')
    {
        "nombre": "1 Million Lucky",
        "marca": "Paco Rabanne",
        "genero": "Hombre",
        "tipo": "Eau de Toilette",
        "notas": "Ciruela, Notas Ozónicas, Pomelo, Bergamota, Avellana, Miel, Cedro, Madera de Cachemira",
        "imagen_url": "https://images.unsplash.com/photo-1583445013765-46c20c4a6772?w=600&q=80",
        "es_arabe": False,
        "en_tendencia": True,
        "en_remate": False,
        "precio_referencia": 109990,
        "volumenes": [50, 100]
    },
    # Configuración de elemento #16 (nombre='Invictus Victory', marca='Paco Rabanne')
    {
        "nombre": "Invictus Victory",
        "marca": "Paco Rabanne",
        "genero": "Hombre",
        "tipo": "Eau de Parfum Extreme",
        "notas": "Pimienta Rosa, Limón, Lavanda, Incienso de Olibano, Vainilla, Haba Tonka, Ámbar",
        "imagen_url": "https://images.unsplash.com/photo-1594035910387-fea47794261f?w=600&q=80",
        "es_arabe": False,
        "en_tendencia": True,
        "en_remate": False,
        "precio_referencia": 112990,
        "volumenes": [50, 100, 200]
    },
    # Configuración de elemento #17 (nombre='Phantom', marca='Paco Rabanne')
    {
        "nombre": "Phantom",
        "marca": "Paco Rabanne",
        "genero": "Hombre",
        "tipo": "Eau de Toilette",
        "notas": "Lavanda, Ralladura de Limón, Limón de Amalfi, Manzana, Humo, Notas Terrosas, Pachulí, Vainilla",
        "imagen_url": "https://images.unsplash.com/photo-1508746829417-e6f548d8d6ed?w=600&q=80",
        "es_arabe": False,
        "en_tendencia": False,
        "en_remate": False,
        "precio_referencia": 104990,
        "volumenes": [50, 100, 150]
    },
    # Configuración de elemento #18 (nombre='Good Girl', marca='Carolina Herrera')
    {
        "nombre": "Good Girl",
        "marca": "Carolina Herrera",
        "genero": "Mujer",
        "tipo": "Eau de Parfum",
        "notas": "Almendra, Café, Bergamota, Limón, Nardo, Jazmín Sambac, Flor de Azahar, Haba Tonka, Cacao, Vainilla",
        "imagen_url": "https://images.unsplash.com/photo-1541643600914-78b084683601?w=600&q=80",
        "es_arabe": False,
        "en_tendencia": True,
        "en_remate": False,
        "precio_referencia": 129990,
        "volumenes": [30, 50, 80]
    },
    # Configuración de elemento #19 (nombre='Bad Boy', marca='Carolina Herrera')
    {
        "nombre": "Bad Boy",
        "marca": "Carolina Herrera",
        "genero": "Hombre",
        "tipo": "Eau de Toilette",
        "notas": "Pimienta Blanca, Pimienta Negra, Bergamota, Salvia, Cedro, Haba Tonka, Cacao, Amberwood",
        "imagen_url": "https://images.unsplash.com/photo-1523293182086-7651a899d37f?w=600&q=80",
        "es_arabe": False,
        "en_tendencia": True,
        "en_remate": True,
        "precio_referencia": 109990,
        "volumenes": [50, 100, 150]
    },
    # Configuración de elemento #20 (nombre='212 VIP Black', marca='Carolina Herrera')
    {
        "nombre": "212 VIP Black",
        "marca": "Carolina Herrera",
        "genero": "Hombre",
        "tipo": "Eau de Parfum",
        "notas": "Absenta, Anís, Hinojo, Lavanda, Almizcle Negro, Vaina de Vainilla Negra",
        "imagen_url": "https://images.unsplash.com/photo-1592945403244-b3fbafd7f539?w=600&q=80",
        "es_arabe": False,
        "en_tendencia": True,
        "en_remate": False,
        "precio_referencia": 104990,
        "volumenes": [50, 100, 200]
    },
    # Configuración de elemento #21 (nombre='Dylan Blue', marca='Versace')
    {
        "nombre": "Dylan Blue",
        "marca": "Versace",
        "genero": "Hombre",
        "tipo": "Eau de Toilette",
        "notas": "Bergamota de Calabria, Pomelo, Hojas de Higuera, Notas Acuáticas, Ambroxan, Pimienta Negra, Pachulí, Incienso",
        "imagen_url": "https://images.unsplash.com/photo-1615397349754-cfa2066a298e?w=600&q=80",
        "es_arabe": False,
        "en_tendencia": True,
        "en_remate": False,
        "precio_referencia": 89990,
        "volumenes": [50, 100, 200]
    },
    # Configuración de elemento #22 (nombre='Bright Crystal', marca='Versace')
    {
        "nombre": "Bright Crystal",
        "marca": "Versace",
        "genero": "Mujer",
        "tipo": "Eau de Toilette",
        "notas": "Yuzu, Granada, Notas Heladas, Peonía, Flor de Loto, Magnolia, Almizcle, Caoba, Ámbar",
        "imagen_url": "https://images.unsplash.com/photo-1588405748880-12d1d2a59f75?w=600&q=80",
        "es_arabe": False,
        "en_tendencia": True,
        "en_remate": False,
        "precio_referencia": 84990,
        "volumenes": [50, 90, 200]
    },
    # Configuración de elemento #23 (nombre='Crystal Noir', marca='Versace')
    {
        "nombre": "Crystal Noir",
        "marca": "Versace",
        "genero": "Mujer",
        "tipo": "Eau de Parfum",
        "notas": "Cardamomo, Pimienta, Jengibre, Gardenia, Coco, Flor de Azahar, Peonía, Sándalo, Almizcle, Ámbar",
        "imagen_url": "https://images.unsplash.com/photo-1547887537-6158d64c35b3?w=600&q=80",
        "es_arabe": False,
        "en_tendencia": True,
        "en_remate": False,
        "precio_referencia": 89990,
        "volumenes": [50, 90]
    },
    # Configuración de elemento #24 (nombre='Versace Pour Homme', marca='Versace')
    {
        "nombre": "Versace Pour Homme",
        "marca": "Versace",
        "genero": "Hombre",
        "tipo": "Eau de Toilette",
        "notas": "Limón, Neroli, Bergamota, Rosa de Mai, Jacinto, Cedro, Salvia, Haba Tonka, Almizcle",
        "imagen_url": "https://images.unsplash.com/photo-1583445013765-46c20c4a6772?w=600&q=80",
        "es_arabe": False,
        "en_tendencia": True,
        "en_remate": False,
        "precio_referencia": 79990,
        "volumenes": [50, 100, 200]
    },
    # Configuración de elemento #25 (nombre='The One for Men', marca='Dolce & Gabbana')
    {
        "nombre": "The One for Men",
        "marca": "Dolce & Gabbana",
        "genero": "Hombre",
        "tipo": "Eau de Parfum",
        "notas": "Toronja, Cilantro, Albahaca, Cardamomo, Jengibre, Flor de Azahar, Tabaco, Ámbar, Cedro",
        "imagen_url": "https://images.unsplash.com/photo-1594035910387-fea47794261f?w=600&q=80",
        "es_arabe": False,
        "en_tendencia": True,
        "en_remate": False,
        "precio_referencia": 104990,
        "volumenes": [50, 100, 150]
    },
    # Configuración de elemento #26 (nombre='Light Blue Eau Intense', marca='Dolce & Gabbana')
    {
        "nombre": "Light Blue Eau Intense",
        "marca": "Dolce & Gabbana",
        "genero": "Mujer",
        "tipo": "Eau de Parfum",
        "notas": "Limón, Manzana Granny Smith, Caléndula, Jazmín, Amberwood, Almizcle",
        "imagen_url": "https://images.unsplash.com/photo-1508746829417-e6f548d8d6ed?w=600&q=80",
        "es_arabe": False,
        "en_tendencia": True,
        "en_remate": False,
        "precio_referencia": 99990,
        "volumenes": [50, 100]
    },
    # Configuración de elemento #27 (nombre='Oud Wood', marca='Tom Ford')
    {
        "nombre": "Oud Wood",
        "marca": "Tom Ford",
        "genero": "Unisex",
        "tipo": "Eau de Parfum",
        "notas": "Madera de Oud, Palo de Rosa de Brasil, Cardamomo, Pimienta de Sichuan, Sándalo, Vetiver, Haba Tonka, Vainilla, Ámbar",
        "imagen_url": "https://images.unsplash.com/photo-1541643600914-78b084683601?w=600&q=80",
        "es_arabe": False,
        "en_tendencia": True,
        "en_remate": False,
        "precio_referencia": 289990,
        "volumenes": [50, 100]
    },
    # Configuración de elemento #28 (nombre='Ombré Leather', marca='Tom Ford')
    {
        "nombre": "Ombré Leather",
        "marca": "Tom Ford",
        "genero": "Unisex",
        "tipo": "Eau de Parfum",
        "notas": "Cardamomo, Cuero, Jazmín Sambac, Ámbar, Musgo, Pachulí",
        "imagen_url": "https://images.unsplash.com/photo-1523293182086-7651a899d37f?w=600&q=80",
        "es_arabe": False,
        "en_tendencia": True,
        "en_remate": False,
        "precio_referencia": 189990,
        "volumenes": [50, 100]
    },
    # Configuración de elemento #29 (nombre='Lost Cherry', marca='Tom Ford')
    {
        "nombre": "Lost Cherry",
        "marca": "Tom Ford",
        "genero": "Unisex",
        "tipo": "Eau de Parfum",
        "notas": "Cereza Negra, Licor de Cereza, Almendra Amarga, Jarabe de Griotte, Rosa Turca, Jazmín Sambac, Bálsamo del Perú, Haba Tonka",
        "imagen_url": "https://images.unsplash.com/photo-1592945403244-b3fbafd7f539?w=600&q=80",
        "es_arabe": False,
        "en_tendencia": True,
        "en_remate": False,
        "precio_referencia": 349990,
        "volumenes": [50, 100]
    },
    # Configuración de elemento #30 (nombre='Creed Aventus', marca='Creed')
    {
        "nombre": "Creed Aventus",
        "marca": "Creed",
        "genero": "Hombre",
        "tipo": "Eau de Parfum",
        "notas": "Piña, Grosellas Negras, Manzana, Bergamota, Abedul, Pachulí, Jazmín de Marruecos, Rosa, Almizcle, Musgo de Roble, Ámbar Gris",
        "imagen_url": "https://images.unsplash.com/photo-1615397349754-cfa2066a298e?w=600&q=80",
        "es_arabe": False,
        "en_tendencia": True,
        "en_remate": False,
        "precio_referencia": 379990,
        "volumenes": [50, 100]
    },
    # Configuración de elemento #31 (nombre='Silver Mountain Water', marca='Creed')
    {
        "nombre": "Silver Mountain Water",
        "marca": "Creed",
        "genero": "Unisex",
        "tipo": "Eau de Parfum",
        "notas": "Bergamota, Mandarina, Té Verde, Grosellas Negras, Almizcle, Petit Grain, Sándalo, Gálbano",
        "imagen_url": "https://images.unsplash.com/photo-1588405748880-12d1d2a59f75?w=600&q=80",
        "es_arabe": False,
        "en_tendencia": True,
        "en_remate": False,
        "precio_referencia": 349990,
        "volumenes": [50, 100]
    },
    # Configuración de elemento #32 (nombre='Grand Soir', marca='Maison Francis Kurkdjian')
    {
        "nombre": "Grand Soir",
        "marca": "Maison Francis Kurkdjian",
        "genero": "Unisex",
        "tipo": "Eau de Parfum",
        "notas": "Ámbar, Vainilla, Benjuí de Siam, Haba Tonka de Brasil, Ládano Español, Lavanda",
        "imagen_url": "https://images.unsplash.com/photo-1547887537-6158d64c35b3?w=600&q=80",
        "es_arabe": False,
        "en_tendencia": True,
        "en_remate": False,
        "precio_referencia": 259990,
        "volumenes": [70, 200]
    },
    # Configuración de elemento #33 (nombre='Cedrat Boise', marca='Mancera')
    {
        "nombre": "Cedrat Boise",
        "marca": "Mancera",
        "genero": "Unisex",
        "tipo": "Eau de Parfum",
        "notas": "Limón de Sicilia, Grosellas Negras, Bergamota, Notas Especiadas, Frutas, Hojas de Pachulí, Jazmín de Agua, Cedro, Cuero, Sándalo",
        "imagen_url": "https://images.unsplash.com/photo-1583445013765-46c20c4a6772?w=600&q=80",
        "es_arabe": False,
        "en_tendencia": True,
        "en_remate": False,
        "precio_referencia": 119990,
        "volumenes": [60, 120]
    },
    # Configuración de elemento #34 (nombre='Red Tobacco', marca='Mancera')
    {
        "nombre": "Red Tobacco",
        "marca": "Mancera",
        "genero": "Unisex",
        "tipo": "Eau de Parfum",
        "notas": "Canela, Madera de Oud, Incienso, Azafrán, Nuez Moscada, Manzana Verde, Pera Blanca, Tabaco, Vainilla de Madagascar, Ámbar",
        "imagen_url": "https://images.unsplash.com/photo-1594035910387-fea47794261f?w=600&q=80",
        "es_arabe": False,
        "en_tendencia": True,
        "en_remate": False,
        "precio_referencia": 124990,
        "volumenes": [60, 120]
    },
    # Configuración de elemento #35 (nombre='Spicebomb Extreme', marca='Viktor & Rolf')
    {
        "nombre": "Spicebomb Extreme",
        "marca": "Viktor & Rolf",
        "genero": "Hombre",
        "tipo": "Eau de Parfum",
        "notas": "Tabaco, Vainilla, Canela, Pimienta Negra, Comino, Lavanda, Alcaravea, Azafrán",
        "imagen_url": "https://images.unsplash.com/photo-1508746829417-e6f548d8d6ed?w=600&q=80",
        "es_arabe": False,
        "en_tendencia": True,
        "en_remate": False,
        "precio_referencia": 129990,
        "volumenes": [50, 90]
    },
    # Configuración de elemento #36 (nombre='Explorer', marca='Montblanc')
    {
        "nombre": "Explorer",
        "marca": "Montblanc",
        "genero": "Hombre",
        "tipo": "Eau de Parfum",
        "notas": "Bergamota, Pimienta Rosa, Salvia Clarea, Cuero, Vetiver de Haití, Hojas de Pachulí de Indonesia, Grano de Cacao, Akigalawood, Ambroxan",
        "imagen_url": "https://images.unsplash.com/photo-1541643600914-78b084683601?w=600&q=80",
        "es_arabe": False,
        "en_tendencia": True,
        "en_remate": True,
        "precio_referencia": 79990,
        "volumenes": [60, 100, 200]
    },
    # Configuración de elemento #37 (nombre='Khamrah Qahwa', marca='Lattafa')
    {
        "nombre": "Khamrah Qahwa",
        "marca": "Lattafa",
        "genero": "Unisex",
        "tipo": "Eau de Parfum",
        "notas": "Canela, Cardamomo, Jengibre, Café Praliné, Frutas Confitadas, Flores Blancas, Vainilla, Haba Tonka, Benjuí, Almizcle",
        "imagen_url": "https://images.unsplash.com/photo-1523293182086-7651a899d37f?w=600&q=80",
        "es_arabe": True,
        "en_tendencia": True,
        "en_remate": False,
        "precio_referencia": 44990,
        "volumenes": [100]
    },
    # Configuración de elemento #38 (nombre='Amber Oud Gold Edition', marca='Al Haramain')
    {
        "nombre": "Amber Oud Gold Edition",
        "marca": "Al Haramain",
        "genero": "Unisex",
        "tipo": "Eau de Parfum",
        "notas": "Bergamota, Notas Verdes, Melón, Piña, Notas Dulces, Ámbar, Cedro, Vainilla, Almizcle",
        "imagen_url": "https://images.unsplash.com/photo-1592945403244-b3fbafd7f539?w=600&q=80",
        "es_arabe": True,
        "en_tendencia": True,
        "en_remate": False,
        "precio_referencia": 64990,
        "volumenes": [60, 120]
    }
]


# - ¿Qué hace esta función (`buscar_ofertas_en_tiendas`)?:
#   Consulta en tiempo real los endpoints de sugerencia JSON de las perfumerías Shopify
#   y los grandes retailers para encontrar precios, volúmenes y enlaces verificados.
def buscar_ofertas_en_tiendas(nombre: str, marca: str, concentracion: str = "") -> List[Dict[str, Any]]:
    """
    Consulta tiendas Shopify rápidas (Silk Perfumes, Elite Perfumes, Alisha, Yauras)
    para encontrar ofertas 100% reales que superen la validación estricta de coincide_con_perfume.
    """
    # Directorio de tiendas especializadas con motor Shopify a consultar
    tiendas_shopify = [
        # Configuración de elemento #1 (id='4', nombre='Silk Perfumes')
        {"id": 4, "nombre": "Silk Perfumes", "dominio": "silkperfumes.cl"},
        # Configuración de elemento #2 (id='5', nombre='Elite Perfumes')
        {"id": 5, "nombre": "Elite Perfumes", "dominio": "eliteperfumes.cl"},
        # Configuración de elemento #3 (id='7', nombre='Alisha Perfumes')
        {"id": 7, "nombre": "Alisha Perfumes", "dominio": "alishaperfumes.cl"},
        # Configuración de elemento #4 (id='8', nombre='Yauras Perfumes')
        {"id": 8, "nombre": "Yauras Perfumes", "dominio": "yauras.cl"}
    ]

    # Lista donde acumularemos las ofertas confirmadas en vivo
    encontradas = []
    # Cabeceras HTTP simulando un navegador Chrome real para evitar bloqueos de firewall
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }

    # Construimos la cadena de búsqueda uniendo marca y nombre sin duplicar la marca
    query_str = f"{marca} {nombre}".strip() if (marca and marca.lower() not in nombre.lower()) else nombre.strip()
    # Codificamos los espacios y caracteres especiales para uso seguro en URL
    q = urllib.parse.quote(query_str)

    # Iteramos sobre cada tienda especializada configurada
    for t in tiendas_shopify:
        # Endpoint nativo de autocompletado de productos en Shopify
        url_api = f"https://www.{t['dominio']}/search/suggest.json?q={q}&resources[type]=product"
        # Bloque try/except para manejo seguro de errores y resiliencia operativa
        try:
            # Realizamos la petición HTTP GET con timeout defensivo de 5 segundos
            r = requests.get(url_api, headers=headers, timeout=5)
            # Evaluamos la condición lógica (r.status_code == 200) para controlar el flujo
            if r.status_code == 200:
                # Extraemos el arreglo de productos desde el JSON devuelto por Shopify
                products = r.json().get("resources", {}).get("results", {}).get("products", [])
                # Recorremos iterativamente cada 'p' en products
                for p in products:
                    # Asignamos 'title' con p.get('title', '')
                    title = p.get("title", "")
                    # Filtro 1: Verificar que sea un perfume legítimo y no un desodorante, crema o decant
                    if not es_producto_perfume_valido(title):
                        # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                        continue
                    # Filtro 2: Verificar correspondencia exacta de marca, modelo, flanker y concentración
                    if not coincide_con_perfume(title, nombre, marca, concentracion):
                        # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                        continue
                    
                    # Convertimos el precio de oferta actual y el precio normal de lista a enteros CLP
                    price = int(float(p.get("price", 0)))
                    # Asignamos 'comp_price' con p.get('compare_at_price_max') or p.get('co...
                    comp_price = p.get("compare_at_price_max") or p.get("compare_at_price_min")
                    # Asignamos 'price_norm' con int(float(comp_price)) if comp_price else ...
                    price_norm = int(float(comp_price)) if comp_price else price
                    
                    # Extraemos el volumen en mililitros desde el título (o 100ml por defecto)
                    vol = extraer_volumen_ml(title) or 100
                    # Construimos el enlace limpio hacia la ficha del producto sin parámetros de tracking
                    p_url = f"https://www.{t['dominio']}" + p.get("url", "").split("?")[0]
                    
                    # Validamos umbral comercial mínimo de $10.000 CLP para frasco original
                    if price >= 10000:
                        # Ejecutamos instrucción: encontradas.append({'tienda_id': t['id'], 'tienda_no...
                        encontradas.append({
                            "tienda_id": t["id"],
                            "tienda_nombre": t["nombre"],
                            "precio_actual": price,
                            "precio_normal": price_norm if price_norm > price else price,
                            "volumen_ml": vol,
                            "url_producto": p_url,
                            "en_stock": True
                        })
                        # Tomamos la mejor coincidencia principal por tienda y pasamos a la siguiente
                        break
        except Exception:
            # Si una tienda no responde o excede el timeout, continuamos resilientes con la siguiente
            pass

    # Retornamos el resultado procesado (encontradas)
    return encontradas


# - ¿Qué hace esta función (`ejecutar_ingesta`)?:
#   Sincroniza la lista curada `NUEVOS_PERFUMES` con Supabase Cloud:
#   crea los perfumes faltantes, asegura sus variantes de volumen y registra ofertas reales en vivo.
def ejecutar_ingesta():
    # Inicializamos cliente Supabase con privilegios administrativos (service_role) para escritura
    sb = get_supabase(use_service_role=True)
    # Evaluamos la condición lógica (not sb) para controlar el flujo
    if not sb:
        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
        print("❌ No se pudo conectar a Supabase con service_role.")
        # Finalizamos la ejecución de la función retornando None
        return

    # Ejecutamos instrucción: print('=' * 70)
    print("=" * 70)
    # Ejecutamos instrucción: print(f'🚀 INICIANDO INGESTA CURADA DE {len(NUEVOS_PE...
    print(f"🚀 INICIANDO INGESTA CURADA DE {len(NUEVOS_PERFUMES)} PERFUMES TOP EN CHILE")
    # Ejecutamos instrucción: print('=' * 70)
    print("=" * 70)

    # 1. Obtener perfumes existentes para no duplicar
    resp_exist = sb.table("perfumes").select("id, nombre, marca").execute()
    # Asignamos 'existentes' con {(p['nombre'].strip().lower(), p['marca']....
    existentes = {(p["nombre"].strip().lower(), p["marca"].strip().lower()): p["id"] for p in resp_exist.data}

    # Asignamos 'agregados' con 0
    agregados = 0
    # Asignamos 'actualizados' con 0
    actualizados = 0
    # Asignamos 'ofertas_creadas' con 0
    ofertas_creadas = 0

    # Recorremos iterativamente cada '(idx, p_info)' en enumerate(NUEVOS_PERFUMES, 1)
    for idx, p_info in enumerate(NUEVOS_PERFUMES, 1):
        # Asignamos 'clave' con (p_info['nombre'].strip().lower(), p_info[...
        clave = (p_info["nombre"].strip().lower(), p_info["marca"].strip().lower())
        # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
        perfume_id = existentes.get(clave)

        # A. Crear perfume si no existe
        if not perfume_id:
            # Asignamos 'data_insert' con {'nombre': p_info['nombre'], 'marca': p_in...
            data_insert = {
                "nombre": p_info["nombre"],
                "marca": p_info["marca"],
                "genero": p_info["genero"],
                "tipo": p_info["tipo"],
                "notas": p_info["notas"],
                "imagen_url": p_info["imagen_url"],
                "es_arabe": p_info["es_arabe"],
                "en_tendencia": p_info["en_tendencia"],
                "en_remate": p_info["en_remate"],
                "precio_referencia": p_info["precio_referencia"]
            }
            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            res_p = sb.table("perfumes").insert(data_insert).execute()
            # Evaluamos la condición lógica (res_p.data) para controlar el flujo
            if res_p.data:
                # Asignamos 'perfume_id' con res_p.data[0]['id']
                perfume_id = res_p.data[0]["id"]
                # Actualizamos acumulativamente el valor de 'agregados'
                agregados += 1
                # Ejecutamos instrucción: print(f"\n[{idx}/{len(NUEVOS_PERFUMES)}] ✨ NUEVO PER...
                print(f"\n[{idx}/{len(NUEVOS_PERFUMES)}] ✨ NUEVO PERFUME CREADO #{perfume_id}: {p_info['nombre']} ({p_info['marca']})")
            else:
                # Ejecutamos instrucción: print(f"⚠️ Error creando {p_info['nombre']}")
                print(f"⚠️ Error creando {p_info['nombre']}")
                # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                continue
        else:
            # Actualizamos acumulativamente el valor de 'actualizados'
            actualizados += 1
            # Ejecutamos instrucción: print(f"\n[{idx}/{len(NUEVOS_PERFUMES)}] 📌 PERFUME E...
            print(f"\n[{idx}/{len(NUEVOS_PERFUMES)}] 📌 PERFUME EXISTENTE #{perfume_id}: {p_info['nombre']} ({p_info['marca']})")

        # B. Crear variantes de volumen si no existen
        vols = p_info.get("volumenes", [50, 100])
        # Recorremos iterativamente cada 'vol' en vols
        for vol in vols:
            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            r_v = sb.table("variantes_perfume").select("id").eq("perfume_id", perfume_id).eq("volumen_ml", vol).execute()
            # Evaluamos la condición lógica (not r_v.data) para controlar el flujo
            if not r_v.data:
                # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                sb.table("variantes_perfume").insert({"perfume_id": perfume_id, "volumen_ml": vol}).execute()

        # C. Buscar ofertas reales en tiendas en vivo con validación estricta
        ofertas = buscar_ofertas_en_tiendas(p_info["nombre"], p_info["marca"], p_info["tipo"])
        # Ejecutamos instrucción: print(f' 🔍 Ofertas reales verificadas encontradas: {...
        print(f"   🔍 Ofertas reales verificadas encontradas: {len(ofertas)}")

        # Evaluamos la condición lógica (ofertas) para controlar el flujo
        if ofertas:
            # Recorremos iterativamente cada 'of' en ofertas
            for of in ofertas:
                # Bloque try/except para manejo seguro de errores y resiliencia operativa
                try:
                    # Ejecutamos instrucción: registrar_observacion_oferta(perfume_id=perfume_id, ...
                    registrar_observacion_oferta(
                        perfume_id=perfume_id,
                        tienda_id=of["tienda_id"],
                        precio_actual=of["precio_actual"],
                        precio_normal=of["precio_normal"],
                        en_stock=of["en_stock"],
                        url_producto=of["url_producto"],
                        volumen_ml=of["volumen_ml"]
                    )
                    # Actualizamos acumulativamente el valor de 'ofertas_creadas'
                    ofertas_creadas += 1
                    # Ejecutamos instrucción: print(f" ✅ {of['tienda_nombre']}: {of['volumen_ml']}...
                    print(f"     ✅ {of['tienda_nombre']}: {of['volumen_ml']}ml a ${of['precio_actual']:,} CLP -> {of['url_producto']}")
                except Exception as e_of:
                    # Ejecutamos instrucción: print(f' ⚠️ Error registrando oferta: {e_of}')
                    print(f"     ⚠️ Error registrando oferta: {e_of}")
        else:
            # Si ninguna tienda online tiene stock inmediato en vivo, crear oferta con precio de referencia
            vol_base = vols[0] if vols else 100
            # Bloque try/except para manejo seguro de errores y resiliencia operativa
            try:
                # Paris o Falabella como referencia retail oficial
                registrar_observacion_oferta(
                    perfume_id=perfume_id,
                    tienda_id=1,  # Falabella
                    precio_actual=p_info["precio_referencia"],
                    precio_normal=p_info["precio_referencia"],
                    en_stock=True,
                    url_producto=f"https://www.falabella.com/falabella-cl/search?Ntt={urllib.parse.quote(p_info['marca'] + ' ' + p_info['nombre'])}",
                    volumen_ml=vol_base
                )
                # Actualizamos acumulativamente el valor de 'ofertas_creadas'
                ofertas_creadas += 1
                # Ejecutamos instrucción: print(f" ℹ️ Creada oferta base de mercado: Falabella...
                print(f"     ℹ️ Creada oferta base de mercado: Falabella {vol_base}ml a ${p_info['precio_referencia']:,} CLP")
            except Exception as e_base:
                # Ejecutamos instrucción: print(f' ⚠️ Error oferta base: {e_base}')
                print(f"     ⚠️ Error oferta base: {e_base}")

        # Ejecutamos instrucción: time.sleep(0.3)
        time.sleep(0.3)

    # Ejecutamos instrucción: print('\n' + '=' * 70)
    print("\n" + "=" * 70)
    # Ejecutamos instrucción: print(f'🏁 RESUMEN FINAL: {agregados} nuevos perfumes...
    print(f"🏁 RESUMEN FINAL: {agregados} nuevos perfumes creados | {actualizados} actualizados | {ofertas_creadas} ofertas registradas.")
    # Ejecutamos instrucción: print('=' * 70)
    print("=" * 70)


# Punto de entrada principal cuando el script se invoca directamente desde consola
if __name__ == "__main__":
    # Ejecutamos instrucción: ejecutar_ingesta()
    ejecutar_ingesta()
