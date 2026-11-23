"""
Tests unitarios para la arquitectura de ingesta masiva en memoria (Shopify & WooCommerce Bulk).
Verifica:
1. Indexación por marca canónica y variantes de volumen en CatalogoTiendaBulk.
2. Extracción ultrarrápida en memoria con resolución de entidad.
3. Respeto de reglas de negocio: filtros de concentración, volumen >= 25ml, y detección de formatos (tester/regular).
4. Compatibilidad transparente con auditar_lote_perfumes.
"""

# Importación de librería estándar o dependencia externa (os)
import os
# Importación de librería estándar o dependencia externa (sys)
import sys
# Importación de librería estándar o dependencia externa (unittest)
import unittest
# Importación de componentes (MagicMock, patch) desde el módulo 'unittest.mock'
from unittest.mock import MagicMock, patch

# Asignamos '_app_dir' con os.path.abspath(os.path.join(os.path.dirna...
_app_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "APP"))
# Evaluamos la condición lógica (_app_dir not in sys.path) para controlar el flujo
if _app_dir not in sys.path:
    # Ejecutamos instrucción: sys.path.insert(0, _app_dir)
    sys.path.insert(0, _app_dir)

# Bloque try/except para manejo seguro de errores y resiliencia operativa
try:
    # Importación de componentes (CatalogoTiendaBulk, auditar_lote_perfumes) desde el módulo 'backend.scraper_periodico'
    from backend.scraper_periodico import CatalogoTiendaBulk, auditar_lote_perfumes
except ImportError:
    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Importación de componentes (CatalogoTiendaBulk, auditar_lote_perfumes) desde el módulo 'scraper_periodico'
        from scraper_periodico import CatalogoTiendaBulk, auditar_lote_perfumes
    except ImportError:
        # Importación de componentes (CatalogoTiendaBulk, auditar_lote_perfumes) desde el módulo 'APP.backend.scraper_periodico'
        from APP.backend.scraper_periodico import CatalogoTiendaBulk, auditar_lote_perfumes


# Definición de clase 'TestBulkScraperOptimizado' que modela la estructura y lógica del componente
class TestBulkScraperOptimizado(unittest.TestCase):

    # Definición de función 'setUp' sin parámetros externos
    def setUp(self):
        # Asignamos 'self.cat_shopify' con CatalogoTiendaBulk(nombre_tienda='Silk Per...
        self.cat_shopify = CatalogoTiendaBulk(
            nombre_tienda="Silk Perfumes",
            tipo="shopify",
            url_base="https://www.silkperfumes.cl",
        )

        # Muestra de producto Shopify
        self.raw_shopify_prod = {
            "id": 101,
            "title": "Versace Eros Flame EDP 100ml",
            "vendor": "Versace",
            "handle": "versace-eros-flame-edp-100ml",
            "variants": [
                {
                    "id": 1001,
                    "title": "100ml",
                    "price": "59990",
                    "compare_at_price": "79990",
                    "available": True,
                },
                {
                    "id": 1002,
                    "title": "50ml",
                    "price": "44990",
                    "compare_at_price": "59990",
                    "available": True,
                }
            ],
            "tags": ["hombre", "perfumeria"],
        }

    # Definición de función 'test_01_indexacion_por_marca_canonica' sin parámetros externos
    def test_01_indexacion_por_marca_canonica(self):
        """Verifica que el producto se indexe bajo la marca canónica normalizada en minúsculas."""
        # Ejecutamos instrucción: self.cat_shopify.ingestar_productos([self.raw_shopif...
        self.cat_shopify.ingestar_productos([self.raw_shopify_prod])
        # Aserción de prueba unitaria: self.assertEqual(self.cat_shopify.total_productos, 1)
        self.assertEqual(self.cat_shopify.total_productos, 1)
        # Aserción de prueba unitaria: self.assertIn('versace', self.cat_shopify.por_marca)
        self.assertIn("versace", self.cat_shopify.por_marca)
        # Aserción de prueba unitaria: self.assertEqual(len(self.cat_shopify.por_marca['ver...
        self.assertEqual(len(self.cat_shopify.por_marca["versace"]), 1)

    # Definición de función 'test_02_extraccion_variedades_en_memoria' sin parámetros externos
    def test_02_extraccion_variedades_en_memoria(self):
        """Extrae ambas variantes (100ml y 50ml) respetando precios, URLs y stock sin llamadas HTTP."""
        # Ejecutamos instrucción: self.cat_shopify.ingestar_productos([self.raw_shopif...
        self.cat_shopify.ingestar_productos([self.raw_shopify_prod])

        # Asignamos 'res' con self.cat_shopify.extraer_variedades(perfum...
        res = self.cat_shopify.extraer_variedades(
            perfume_nombre="Eros Flame",
            marca="Versace",
            volumen_ml_defecto=100,
            concentracion="Eau de Parfum",
        )

        # Aserción de prueba unitaria: self.assertEqual(len(res), 2)
        self.assertEqual(len(res), 2)
        # Asignamos 'vols' con {v['volumen_ml'] for v in res}
        vols = {v["volumen_ml"] for v in res}
        # Aserción de prueba unitaria: self.assertEqual(vols, {100, 50})
        self.assertEqual(vols, {100, 50})

        # Asignamos 'v100' con next((v for v in res if v['volumen_ml'] ==...
        v100 = next(v for v in res if v["volumen_ml"] == 100)
        # Aserción de prueba unitaria: self.assertEqual(v100['precio_actual'], 59990)
        self.assertEqual(v100["precio_actual"], 59990)
        # Aserción de prueba unitaria: self.assertEqual(v100['precio_normal'], 79990)
        self.assertEqual(v100["precio_normal"], 79990)
        # Aserción de prueba unitaria: self.assertTrue(v100['en_stock'])
        self.assertTrue(v100["en_stock"])
        # Aserción de prueba unitaria: self.assertEqual(v100['formato'], 'regular')
        self.assertEqual(v100["formato"], "regular")
        # Aserción de prueba unitaria: self.assertEqual(v100['metodo'], 'Silk Perfumes Bulk...
        self.assertEqual(v100["metodo"], "Silk Perfumes Bulk Cache")

    # Definición de función 'test_03_filtro_concentracion_y_tokens' sin parámetros externos
    def test_03_filtro_concentracion_y_tokens(self):
        """No debe emparejar Eros EDT si el catálogo busca Eros Flame EDP."""
        # Asignamos 'prod_distinto' con {'id': 102, 'title': 'Versace Eros EDT 100...
        prod_distinto = {
            "id": 102,
            "title": "Versace Eros EDT 100ml",
            "vendor": "Versace",
            "handle": "versace-eros-edt-100ml",
            "variants": [
                {
                    "id": 1003,
                    "title": "100ml",
                    "price": "49990",
                    "available": True,
                }
            ],
        }
        # Ejecutamos instrucción: self.cat_shopify.ingestar_productos([prod_distinto])
        self.cat_shopify.ingestar_productos([prod_distinto])

        # Asignamos 'res' con self.cat_shopify.extraer_variedades(perfum...
        res = self.cat_shopify.extraer_variedades(
            perfume_nombre="Eros Flame",
            marca="Versace",
            volumen_ml_defecto=100,
            concentracion="Eau de Parfum",
        )
        # Aserción de prueba unitaria: self.assertEqual(len(res), 0)
        self.assertEqual(len(res), 0)

    # Definición de función 'test_04_woocommerce_bulk_ingestion' sin parámetros externos
    def test_04_woocommerce_bulk_ingestion(self):
        """Verifica la ingesta masiva y parsing de tiendas WooCommerce."""
        # Asignamos 'cat_woo' con CatalogoTiendaBulk(nombre_tienda='Portal d...
        cat_woo = CatalogoTiendaBulk(
            nombre_tienda="Portal del Perfume",
            tipo="woocommerce",
            url_base="https://portaldelperfume.cl",
        )

        # Asignamos 'woo_prod' con {'id': 201, 'name': 'Armaf Club De Nuit In...
        woo_prod = {
            "id": 201,
            "name": "Armaf Club De Nuit Intense Man EDT 105ml",
            "permalink": "https://portaldelperfume.cl/producto/club-de-nuit-intense-man-edt/",
            "price": "34990",
            "regular_price": "45990",
            "stock_status": "instock",
            "categories": [{"name": "Armaf"}],
        }
        # Ejecutamos instrucción: cat_woo.ingestar_productos([woo_prod])
        cat_woo.ingestar_productos([woo_prod])

        # Asignamos 'res' con cat_woo.extraer_variedades(perfume_nombre=...
        res = cat_woo.extraer_variedades(
            perfume_nombre="Club De Nuit Intense Man",
            marca="Armaf",
            volumen_ml_defecto=105,
            concentracion="Eau de Toilette",
        )

        # Aserción de prueba unitaria: self.assertEqual(len(res), 1)
        self.assertEqual(len(res), 1)
        # Aserción de prueba unitaria: self.assertEqual(res[0]['volumen_ml'], 105)
        self.assertEqual(res[0]["volumen_ml"], 105)
        # Aserción de prueba unitaria: self.assertEqual(res[0]['precio_actual'], 34990)
        self.assertEqual(res[0]["precio_actual"], 34990)
        # Aserción de prueba unitaria: self.assertEqual(res[0]['precio_normal'], 45990)
        self.assertEqual(res[0]["precio_normal"], 45990)
        # Aserción de prueba unitaria: self.assertTrue(res[0]['en_stock'])
        self.assertTrue(res[0]["en_stock"])

    # Definición de función 'test_05_integracion_auditar_lote_con_cache_bulk' (parámetros: mock_finalizar, mock_iniciar, mock_reg)
    @patch("backend.scraper_periodico.registrar_observacion_oferta")
    @patch("backend.scraper_periodico.iniciar_scraping_run")
    @patch("backend.scraper_periodico.finalizar_scraping_run")
    def test_05_integracion_auditar_lote_con_cache_bulk(
        self, mock_finalizar, mock_iniciar, mock_reg
    ):
        """Comprueba que auditar_lote_perfumes consulta la caché en memoria y no hace peticiones HTTP para tiendas bulk."""
        # Asignamos 'mock_iniciar.return_value' con 999
        mock_iniciar.return_value = 999
        # Asignamos 'mock_reg.return_value' con {'resultado': 'creada', 'campos_modificado...
        mock_reg.return_value = {"resultado": "creada", "campos_modificados": ["precio_actual"]}

        # Ejecutamos instrucción: self.cat_shopify.ingestar_productos([self.raw_shopif...
        self.cat_shopify.ingestar_productos([self.raw_shopify_prod])
        # Asignamos 'cache_bulk' con {'Silk Perfumes': self.cat_shopify}
        cache_bulk = {"Silk Perfumes": self.cat_shopify}

        # Asignamos 'perfumes_lote' con [{'id': 1, 'nombre': 'Eros Flame', 'marca'...
        perfumes_lote = [
            # Configuración de elemento #1 (id='1', nombre='Eros Flame', marca='Versace')
            {
                "id": 1,
                "nombre": "Eros Flame",
                "marca": "Versace",
                "tipo": "Eau de Parfum",
                "precio_referencia": 60000,
            }
        ]
        # Asignamos 'tiendas_db' con [{'id': 10, 'nombre': 'Silk Perfumes', 'tr...
        tiendas_db = [
            # Configuración de elemento #1 (id='10', nombre='Silk Perfumes')
            {"id": 10, "nombre": "Silk Perfumes", "trust_score": 92}
        ]

        # Asignamos 'mock_session' con MagicMock()
        mock_session = MagicMock()

        # Asignamos 'resultado' con auditar_lote_perfumes(perfumes_lote=perfum...
        resultado = auditar_lote_perfumes(
            perfumes_lote=perfumes_lote,
            tiendas_db=tiendas_db,
            urls_conocidas_map={},
            session=mock_session,
            rotacion_idx=1,
            total_rotaciones=1,
            total_catalogo=1,
            cache_tiendas_bulk=cache_bulk,
        )

        # Debe actualizar con la oferta encontrada en memoria
        self.assertEqual(resultado["metricas"]["precios_actualizados"], 2)
        # La sesión HTTP NO debe haber hecho ningún get porque todo se resolvió en RAM
        mock_session.get.assert_not_called()


# Punto de entrada principal cuando el script se invoca directamente desde consola
if __name__ == "__main__":
    # Ejecutamos instrucción: unittest.main()
    unittest.main()
