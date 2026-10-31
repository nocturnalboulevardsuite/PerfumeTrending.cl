"""
PerfumeTrending.cl — Pruebas de Scrapers: Errores no inventan precios ni stock
=============================================================================
Verifica que las fallas de scraping (HTTP 403, 500, timeout, HTML roto) no
generen registros ficticios de precios ni conviertan estados agotados en disponibles.
"""

import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch
import json

# Configurar entorno de pruebas aislado
TEST_DIR = tempfile.mkdtemp()
TEST_DB_PATH = os.path.join(TEST_DIR, "test_scrapers.db")

import APP.backend.database as db_module
db_module.DB_PATH = TEST_DB_PATH
db_module.DB_DIR = TEST_DIR
db_module.is_supabase_disponible = lambda: False
db_module.get_supabase = lambda *args, **kwargs: None

from APP.backend.database import (
    init_db,
    get_db_cursor,
    registrar_observacion_oferta,
    registrar_fallo_scraping
)
from APP.backend.scraper_periodico import (
    extraer_precio_shopify,
    extraer_precio_falabella,
    extraer_precio_paris,
    extraer_precio_ripley,
    extraer_variedades_ripley
)
from APP.backend.normalizador import coincide_con_perfume, es_producto_perfume_valido


class TestScrapersFallosYStock(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db(force_reseed=False)
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("""
            INSERT OR REPLACE INTO tiendas (id, nombre, url_base, trust_score)
            VALUES (101, 'Falabella', 'https://www.falabella.com', 96);
            """)
            cursor.execute("""
            INSERT OR REPLACE INTO perfumes (id, nombre, marca, genero, tipo, notas, imagen_url, precio_referencia)
            VALUES (202, 'Bleu de Chanel Mock', 'Chanel', 'Hombre', 'Eau de Parfum', 'Cítricos', 'http://img.cl/b.jpg', 180000);
            """)
            cursor.execute("""
            INSERT OR REPLACE INTO variantes_perfume (id, perfume_id, concentracion, volumen_ml, formato, slug, activa)
            VALUES (303, 202, 'Eau de Parfum', 100.0, 'regular', 'bleu-mock-100ml', 1);
            """)

    @classmethod
    def tearDownClass(cls):
        try:
            shutil.rmtree(TEST_DIR)
        except Exception:
            pass

    def setUp(self):
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("DELETE FROM ofertas_actuales WHERE variante_id = 303;")
            cursor.execute("DELETE FROM precios_registro WHERE variante_id = 303;")

    def test_01_error_conexion_shopify_no_inventa_precios(self):
        """Verifica que si Shopify lanza timeout o conexión fallida, el extractor retorna exito=False."""
        mock_session = MagicMock()
        mock_session.get.side_effect = Exception("Connection Timeout tras 10s")

        res = extraer_precio_shopify(
            session=mock_session,
            dominio="silkperfumes.cl",
            perfume_nombre="Bleu de Chanel Mock",
            marca="Chanel",
            volumen_ml=100
        )
        self.assertFalse(res.get("exito"))
        self.assertNotIn("precio_actual", res)
        self.assertNotIn("en_stock", res)

    def test_02_falabella_404_o_500_retorna_falso_y_no_forja_stock(self):
        """Verifica que ante un HTTP 500 en Falabella, el extractor falla limpiamente."""
        mock_session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_session.get.return_value = mock_resp

        res = extraer_precio_falabella(
            session=mock_session,
            url_directa="https://www.falabella.com/producto/123",
            perfume_nombre="Bleu de Chanel Mock",
            volumen_ml=100
        )
        self.assertFalse(res.get("exito"))

    def test_03_falabella_producto_agotado_detecta_stock_falso(self):
        """Verifica que si Falabella reporta isOutOfStock=True en NEXT_DATA, el stock extraído es estrictamente False."""
        mock_session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = """
        <html>
        <script id="__NEXT_DATA__" type="application/json">
        {
            "props": {
                "pageProps": {
                    "productData": {
                        "isOutOfStock": true,
                        "prices": [{"type": "internetPrice", "price": ["89990"]}],
                        "variants": [
                            {
                                "isOutOfStock": true,
                                "prices": [{"type": "internetPrice", "price": ["89990"]}]
                            }
                        ]
                    }
                }
            }
        }
        </script>
        </html>
        """
        mock_session.get.return_value = mock_resp

        res = extraer_precio_falabella(
            session=mock_session,
            url_directa="https://www.falabella.com/producto/123",
            perfume_nombre="Bleu de Chanel Mock",
            volumen_ml=100
        )
        self.assertTrue(res.get("exito"))
        self.assertEqual(res.get("precio_actual"), 89990)
        self.assertFalse(res.get("en_stock"), "El producto con isOutOfStock=True debe marcarse como en_stock=False")

    def test_03b_falabella_variante_sin_ispurchaseable_detecta_agotado(self):
        """Verifica que en Falabella Next.js, una talla sin isPurchaseable y con availabilityLabels vacíos se marque como agotada."""
        mock_session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = json.dumps({
            "props": {
                "pageProps": {
                    "productData": {
                        "isOutOfStock": False,
                        "name": "BLEU DE CHANEL Eau de Parfum Vaporizador",
                        "variants": [
                            {
                                "id": "4192038",
                                "name": "BLEU DE CHANEL Eau de Parfum Vaporizador 50ml",
                                "attributes": {"size": "50"},
                                "isOutOfStock": None,
                                "isPurchaseable": None,
                                "isOnlineSellable": None,
                                "availabilityLabels": {"homeDeliveryShipping": "", "pickUpFromStoreShipping": ""},
                                "prices": [{"type": "internetPrice", "price": ["145.200"]}]
                            },
                            {
                                "id": "4192040",
                                "name": "BLEU DE CHANEL Eau de Parfum Vaporizador 100ml",
                                "attributes": {"size": "100"},
                                "isOutOfStock": None,
                                "isPurchaseable": True,
                                "isOnlineSellable": True,
                                "availabilityLabels": {"homeDeliveryShipping": "Despacho a domicilio"},
                                "prices": [{"type": "internetPrice", "price": ["181.500"]}]
                            }
                        ]
                    }
                }
            }
        })
        mock_resp.text = f"<html><script id=\"__NEXT_DATA__\" type=\"application/json\">{mock_resp.text}</script></html>"
        mock_session.get.return_value = mock_resp

        res_50 = extraer_precio_falabella(
            session=mock_session,
            url_directa="https://www.falabella.com/producto/123",
            perfume_nombre="BLEU DE CHANEL",
            volumen_ml=50
        )
        self.assertTrue(res_50.get("exito"))
        self.assertFalse(res_50.get("en_stock"), "La variante de 50ml sin isPurchaseable debe quedar como en_stock=False")

        res_100 = extraer_precio_falabella(
            session=mock_session,
            url_directa="https://www.falabella.com/producto/123",
            perfume_nombre="BLEU DE CHANEL",
            volumen_ml=100
        )
        self.assertTrue(res_100.get("exito"))
        self.assertTrue(res_100.get("en_stock"), "La variante de 100ml con isPurchaseable=True debe quedar como en_stock=True")

    def test_04_paris_producto_agotado_detecta_stock_falso(self):
        """Verifica que si Paris reporta OutOfStock en Schema.org JSON-LD, en_stock es False."""
        mock_session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = """
        <html>
        <script type="application/ld+json">
        {
            "@type": "Product",
            "name": "Bleu de Chanel Mock",
            "offers": [{
                "price": "99990",
                "availability": "https://schema.org/OutOfStock"
            }]
        }
        </script>
        </html>
        """
        mock_session.get.return_value = mock_resp

        res = extraer_precio_paris(
            session=mock_session,
            url_directa="https://www.paris.cl/bleu-mock.html",
            perfume_nombre="Bleu de Chanel Mock",
            volumen_ml=100
        )
        self.assertTrue(res.get("exito"))
        self.assertEqual(res.get("precio_actual"), 99990)
        self.assertFalse(res.get("en_stock"), "La oferta con disponibilidad OutOfStock debe reportar en_stock=False")

    def test_05_ripley_producto_agotado_en_dom(self):
        """Verifica que si Ripley muestra texto 'Agotado' o 'Sin stock' en el DOM, se detecta en_stock=False."""
        mock_session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = """
        <html>
        <div class="price-value">$ 110.000</div>
        <div class="product-status">Producto Agotado</div>
        </html>
        """
        mock_session.get.return_value = mock_resp

        res = extraer_precio_ripley(
            session=mock_session,
            url_directa="https://simple.ripley.cl/bleu-mock-p",
            perfume_nombre="Bleu de Chanel Mock",
            volumen_ml=100
        )
        self.assertTrue(res.get("exito"))
        self.assertEqual(res.get("precio_actual"), 110000)
        self.assertFalse(res.get("en_stock"), "DOM con 'Producto Agotado' debe retornar en_stock=False")

    def test_06_ripley_variantes_pdp_extrae_stock_y_volumen_exacto(self):
        """Verifica que extraer_variedades_ripley procesa múltiples variantes con volúmenes y stock exactos."""
        import json
        mock_session = MagicMock()

        # Mock de búsqueda Ripley
        search_html = """
        <html><script id="__NEXT_DATA__" type="application/json">
        {"props": {"pageProps": {"findabilityProps": {"data": {"products": [
            {"name": "Bleu de Chanel Eau de Parfum Vaporizador", "parentProductID": "2000349451349p", "url": "/bleu-de-chanel-p", "priceNumber": 145200, "inStock": true}
        ]}}}}}
        </script></html>
        """
        # Mock de ficha técnica PDP Ripley con 3 variantes (50ml, 100ml, 150ml)
        pdp_html = """
        <html><script id="__NEXT_DATA__" type="application/json">
        {"props": {"pageProps": {"detailProps": {"data": {"product": {
            "name": "Bleu de Chanel Eau de Parfum Vaporizador",
            "canonicalSlug": "bleu-de-chanel-pdp",
            "variants": [
                {
                    "sku": "SKU50",
                    "definingAttribute": [{"identifier": "contenido_perfume", "value": "50 ml"}],
                    "price": {"sale": {"valueNumber": 145200}, "master": {"valueNumber": 145200}},
                    "stock": true,
                    "notBuyable": false,
                    "notSelectable": false,
                    "statusUI": "Disponible"
                },
                {
                    "sku": "SKU100",
                    "definingAttribute": [{"identifier": "contenido_perfume", "value": "100 ml"}],
                    "price": {"sale": {"valueNumber": 181500}, "master": {"valueNumber": 181500}},
                    "stock": false,
                    "notBuyable": false,
                    "notSelectable": true,
                    "statusUI": "Sin stock"
                },
                {
                    "sku": "SKU150",
                    "definingAttribute": [{"identifier": "contenido_perfume", "value": "150 ml"}],
                    "price": {"sale": {"valueNumber": 225500}, "master": {"valueNumber": 225500}},
                    "stock": false,
                    "notBuyable": false,
                    "notSelectable": true,
                    "statusUI": "Sin stock"
                }
            ]
        }}}}}}
        </script></html>
        """

        mock_resp_search = MagicMock(status_code=200, text=search_html)
        mock_resp_pdp = MagicMock(status_code=200, text=pdp_html)
        mock_session.get.side_effect = [mock_resp_search, mock_resp_pdp]

        with patch("APP.backend.scraper_periodico.curl_requests", None):
            res_list = extraer_variedades_ripley(
                session=mock_session,
                url_directa=None,
                perfume_nombre="Bleu de Chanel",
                marca="Chanel",
                concentracion="Eau de Parfum"
            )

        self.assertEqual(len(res_list), 1)  # Fallback a search card si curl_requests es None
        # Ahora con curl_requests simulado
        mock_curl_session = MagicMock()
        mock_curl_session.get.side_effect = [mock_resp_search, mock_resp_pdp]
        mock_curl_module = MagicMock()
        mock_curl_module.Session.return_value = mock_curl_session

        with patch("APP.backend.scraper_periodico.curl_requests", mock_curl_module):
            vars_curl = extraer_variedades_ripley(
                session=mock_session,
                url_directa=None,
                perfume_nombre="Bleu de Chanel",
                marca="Chanel",
                concentracion="Eau de Parfum"
            )

        self.assertEqual(len(vars_curl), 3)
        # 50ml: Disponible
        v50 = [v for v in vars_curl if v["volumen_ml"] == 50][0]
        self.assertEqual(v50["precio_actual"], 145200)
        self.assertTrue(v50["en_stock"])

        # 100ml: Agotado / Sin stock
        v100 = [v for v in vars_curl if v["volumen_ml"] == 100][0]
        self.assertEqual(v100["precio_actual"], 181500)
        self.assertFalse(v100["en_stock"], "100ml con statusUI Sin stock debe reportar en_stock=False")

        # 150ml: Agotado / Sin stock
        v150 = [v for v in vars_curl if v["volumen_ml"] == 150][0]
        self.assertEqual(v150["precio_actual"], 225500)
        self.assertFalse(v150["en_stock"], "150ml con statusUI Sin stock debe reportar en_stock=False")

    def test_07_coincidencia_concentracion_evita_cruces_edp_edt(self):
        """Verifica que el normalizador no empareja EDT con EDP ni accesorios de afeitado."""
        self.assertFalse(coincide_con_perfume(
            "Bleu de Chanel Eau de Toilette Vaporizador 100ml",
            "Bleu de Chanel",
            "Chanel",
            concentracion="Eau de Parfum"
        ))
        self.assertTrue(coincide_con_perfume(
            "Bleu de Chanel Eau de Parfum Vaporizador 100ml",
            "Bleu de Chanel",
            "Chanel",
            concentracion="Eau de Parfum"
        ))
        self.assertFalse(es_producto_perfume_valido("Bleu de Chanel Bálsamo Después del Afeitado"))
        self.assertFalse(es_producto_perfume_valido("Bleu de Chanel Twist and Spray Recargas"))


if __name__ == "__main__":
    unittest.main()
