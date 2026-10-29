"""
Tests unitarios para la arquitectura de ingesta masiva en memoria (Shopify & WooCommerce Bulk).
Verifica:
1. Indexación por marca canónica y variantes de volumen en CatalogoTiendaBulk.
2. Extracción ultrarrápida en memoria con resolución de entidad.
3. Respeto de reglas de negocio: filtros de concentración, volumen >= 25ml, y detección de formatos (tester/regular).
4. Compatibilidad transparente con auditar_lote_perfumes.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

_app_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "APP"))
if _app_dir not in sys.path:
    sys.path.insert(0, _app_dir)

try:
    from backend.scraper_periodico import CatalogoTiendaBulk, auditar_lote_perfumes
except ImportError:
    try:
        from scraper_periodico import CatalogoTiendaBulk, auditar_lote_perfumes
    except ImportError:
        from APP.backend.scraper_periodico import CatalogoTiendaBulk, auditar_lote_perfumes


class TestBulkScraperOptimizado(unittest.TestCase):

    def setUp(self):
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

    def test_01_indexacion_por_marca_canonica(self):
        """Verifica que el producto se indexe bajo la marca canónica normalizada en minúsculas."""
        self.cat_shopify.ingestar_productos([self.raw_shopify_prod])
        self.assertEqual(self.cat_shopify.total_productos, 1)
        self.assertIn("versace", self.cat_shopify.por_marca)
        self.assertEqual(len(self.cat_shopify.por_marca["versace"]), 1)

    def test_02_extraccion_variedades_en_memoria(self):
        """Extrae ambas variantes (100ml y 50ml) respetando precios, URLs y stock sin llamadas HTTP."""
        self.cat_shopify.ingestar_productos([self.raw_shopify_prod])

        res = self.cat_shopify.extraer_variedades(
            perfume_nombre="Eros Flame",
            marca="Versace",
            volumen_ml_defecto=100,
            concentracion="Eau de Parfum",
        )

        self.assertEqual(len(res), 2)
        vols = {v["volumen_ml"] for v in res}
        self.assertEqual(vols, {100, 50})

        v100 = next(v for v in res if v["volumen_ml"] == 100)
        self.assertEqual(v100["precio_actual"], 59990)
        self.assertEqual(v100["precio_normal"], 79990)
        self.assertTrue(v100["en_stock"])
        self.assertEqual(v100["formato"], "regular")
        self.assertEqual(v100["metodo"], "Silk Perfumes Bulk Cache")

    def test_03_filtro_concentracion_y_tokens(self):
        """No debe emparejar Eros EDT si el catálogo busca Eros Flame EDP."""
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
        self.cat_shopify.ingestar_productos([prod_distinto])

        res = self.cat_shopify.extraer_variedades(
            perfume_nombre="Eros Flame",
            marca="Versace",
            volumen_ml_defecto=100,
            concentracion="Eau de Parfum",
        )
        self.assertEqual(len(res), 0)

    def test_04_woocommerce_bulk_ingestion(self):
        """Verifica la ingesta masiva y parsing de tiendas WooCommerce."""
        cat_woo = CatalogoTiendaBulk(
            nombre_tienda="Portal del Perfume",
            tipo="woocommerce",
            url_base="https://portaldelperfume.cl",
        )

        woo_prod = {
            "id": 201,
            "name": "Armaf Club De Nuit Intense Man EDT 105ml",
            "permalink": "https://portaldelperfume.cl/producto/club-de-nuit-intense-man-edt/",
            "price": "34990",
            "regular_price": "45990",
            "stock_status": "instock",
            "categories": [{"name": "Armaf"}],
        }
        cat_woo.ingestar_productos([woo_prod])

        res = cat_woo.extraer_variedades(
            perfume_nombre="Club De Nuit Intense Man",
            marca="Armaf",
            volumen_ml_defecto=105,
            concentracion="Eau de Toilette",
        )

        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["volumen_ml"], 105)
        self.assertEqual(res[0]["precio_actual"], 34990)
        self.assertEqual(res[0]["precio_normal"], 45990)
        self.assertTrue(res[0]["en_stock"])

    @patch("backend.scraper_periodico.registrar_observacion_oferta")
    @patch("backend.scraper_periodico.iniciar_scraping_run")
    @patch("backend.scraper_periodico.finalizar_scraping_run")
    def test_05_integracion_auditar_lote_con_cache_bulk(
        self, mock_finalizar, mock_iniciar, mock_reg
    ):
        """Comprueba que auditar_lote_perfumes consulta la caché en memoria y no hace peticiones HTTP para tiendas bulk."""
        mock_iniciar.return_value = 999
        mock_reg.return_value = {"resultado": "creada", "campos_modificados": ["precio_actual"]}

        self.cat_shopify.ingestar_productos([self.raw_shopify_prod])
        cache_bulk = {"Silk Perfumes": self.cat_shopify}

        perfumes_lote = [
            {
                "id": 1,
                "nombre": "Eros Flame",
                "marca": "Versace",
                "tipo": "Eau de Parfum",
                "precio_referencia": 60000,
            }
        ]
        tiendas_db = [
            {"id": 10, "nombre": "Silk Perfumes", "trust_score": 92}
        ]

        mock_session = MagicMock()

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


if __name__ == "__main__":
    unittest.main()
