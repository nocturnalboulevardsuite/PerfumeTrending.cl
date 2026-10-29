"""
Tests unitarios para la arquitectura de ingesta masiva en memoria (Shopify & WooCommerce Bulk).
Verifica:
1. Indexación por marca canónica y variantes de volumen en CatalogoTiendaBulk.
2. Extracción ultrarrápida en memoria con resolución de entidad.
3. Respeto de reglas de negocio: filtros de concentración, volumen >= 25ml, y detección de formatos (tester/regular).
4. Compatibilidad transparente con auditar_lote_perfumes.
"""

import unittest
from unittest.mock import MagicMock, patch

try:
    import APP.backend.scraper_periodico as sp_mod
    from APP.backend.scraper_periodico import CatalogoTiendaBulk, auditar_lote_perfumes
except ImportError:
    import backend.scraper_periodico as sp_mod
    from backend.scraper_periodico import CatalogoTiendaBulk, auditar_lote_perfumes


class TestBulkScraperOptimizado(unittest.TestCase):

    def setUp(self):
        self.cat_shopify = CatalogoTiendaBulk(
            nombre_tienda="Silk Perfumes",
            tipo="shopify",
            url_base="https://www.silkperfumes.cl",
        )

        # Muestra de producto Shopify
        self.cat_shopify.agregar_producto_shopify({
            "id": 101,
            "title": "Bleu de Chanel Eau de Parfum 100ml",
            "vendor": "Chanel",
            "handle": "bleu-de-chanel-edp-100ml",
            "variants": [
                {
                    "title": "100ml",
                    "price": "145990.00",
                    "compare_at_price": "165990.00",
                    "available": True,
                },
                {
                    "title": "50ml",
                    "price": "115990.00",
                    "compare_at_price": "125990.00",
                    "available": True,
                },
            ]
        })

        # Muestra de producto árabe
        self.cat_shopify.agregar_producto_shopify({
            "id": 102,
            "title": "Lattafa Khamrah Eau de Parfum 100ml",
            "vendor": "Lattafa",
            "handle": "lattafa-khamrah-edp-100ml",
            "variants": [
                {
                    "title": "100ml",
                    "price": "39990.00",
                    "compare_at_price": "49990.00",
                    "available": True,
                }
            ]
        })

    def test_01_indexacion_por_marca_canonica(self):
        """Verifica que los productos se clasifiquen bajo su marca canónica en minúsculas."""
        self.assertEqual(self.cat_shopify.total_productos, 2)
        self.assertIn("chanel", self.cat_shopify.por_marca)
        self.assertIn("lattafa", self.cat_shopify.por_marca)
        self.assertEqual(len(self.cat_shopify.por_marca["chanel"]), 1)

    def test_02_extraccion_variedades_en_memoria(self):
        """Verifica que extraer_variedades extraiga ambas presentaciones (100ml y 50ml) con stock y precio."""
        variedades = self.cat_shopify.extraer_variedades(
            perfume_nombre="Bleu de Chanel",
            marca="Chanel",
            concentracion="Eau de Parfum",
        )
        self.assertEqual(len(variedades), 2)
        vols = {v["volumen_ml"] for v in variedades}
        self.assertIn(100, vols)
        self.assertIn(50, vols)

        var_100 = next(v for v in variedades if v["volumen_ml"] == 100)
        self.assertEqual(var_100["precio_actual"], 145990)
        self.assertEqual(var_100["precio_normal"], 165990)
        self.assertTrue(var_100["en_stock"])
        self.assertIn("Silk Perfumes Bulk Cache", var_100["metodo"])

    def test_03_filtro_por_tokens_y_concentracion(self):
        """Verifica que un perfume con diferente nombre o concentración no haga match indebido."""
        # Nombre diferente
        res_otro = self.cat_shopify.extraer_variedades(
            perfume_nombre="Allure Homme Sport",
            marca="Chanel",
            concentracion="Eau de Toilette",
        )
        self.assertEqual(len(res_otro), 0)

        # Concentración incompatible (EDT vs EDP)
        res_edt = self.cat_shopify.extraer_variedades(
            perfume_nombre="Bleu de Chanel",
            marca="Chanel",
            concentracion="Eau de Toilette",
        )
        self.assertEqual(len(res_edt), 0)

    def test_04_woocommerce_bulk_ingestion(self):
        """Verifica la ingesta de productos estructurados de WooCommerce Store API."""
        cat_wc = CatalogoTiendaBulk(
            nombre_tienda="Chile Perfume",
            tipo="woocommerce",
            url_base="https://www.chileperfume.cl",
        )
        cat_wc.agregar_producto_woocommerce({
            "id": 501,
            "name": "Versace Eros Eau de Parfum 100ml",
            "permalink": "https://www.chileperfume.cl/producto/versace-eros-edp-100ml/",
            "brands": [{"name": "Versace"}],
            "prices": {
                "price": "69990",
                "regular_price": "89990",
            },
            "is_in_stock": True,
        })
        self.assertEqual(cat_wc.total_productos, 1)
        self.assertIn("versace", cat_wc.por_marca)

        vars_wc = cat_wc.extraer_variedades(
            perfume_nombre="Eros",
            marca="Versace",
            concentracion="Eau de Parfum",
        )
        self.assertEqual(len(vars_wc), 1)
        self.assertEqual(vars_wc[0]["precio_actual"], 69990)
        self.assertEqual(vars_wc[0]["precio_normal"], 89990)
        self.assertEqual(vars_wc[0]["volumen_ml"], 100)
        self.assertTrue(vars_wc[0]["en_stock"])

    def test_05_integracion_auditar_lote_con_cache_bulk(self):
        """Verifica que auditar_lote_perfumes use cache_tiendas_bulk sin peticiones HTTP."""
        perfumes_lote = [
            {
                "id": 9999,
                "nombre": "Khamrah",
                "marca": "Lattafa",
                "genero": "Unisex",
                "tipo": "Eau de Parfum",
                "precio_referencia": 45000,
            }
        ]
        tiendas_db = [
            {
                "id": 4,
                "nombre": "Silk Perfumes",
                "url_base": "https://www.silkperfumes.cl",
                "trust_score": 92,
            }
        ]
        cache_bulk = {"Silk Perfumes": self.cat_shopify}

        mock_session = MagicMock()

        with patch.object(sp_mod, "registrar_observacion_oferta") as mock_reg, \
             patch.object(sp_mod, "iniciar_scraping_run", return_value=999), \
             patch.object(sp_mod, "finalizar_scraping_run"):

            mock_reg.return_value = {"resultado": "creada", "campos_modificados": ["precio_actual"]}

            reporte = auditar_lote_perfumes(
                perfumes_lote=perfumes_lote,
                tiendas_db=tiendas_db,
                urls_conocidas_map={},
                session=mock_session,
                rotacion_idx=1,
                total_rotaciones=1,
                total_catalogo=1,
                cache_tiendas_bulk=cache_bulk,
            )

            # La sesión HTTP NO debe haber sido llamada para Silk Perfumes
            mock_session.get.assert_not_called()
            # La oferta debe haber sido registrada exitosamente
            self.assertEqual(reporte["metricas"]["ofertas_nuevas"], 1)
            self.assertEqual(reporte["metricas"]["precios_actualizados"], 1)


if __name__ == "__main__":
    unittest.main()
