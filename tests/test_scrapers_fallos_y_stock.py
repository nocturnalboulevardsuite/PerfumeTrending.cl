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

# Configurar entorno de pruebas aislado
TEST_DIR = tempfile.mkdtemp()
TEST_DB_PATH = os.path.join(TEST_DIR, "test_scrapers.db")

import APP.backend.database as db_module
db_module.DB_PATH = TEST_DB_PATH
db_module.DB_DIR = TEST_DIR

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
    extraer_precio_ripley
)


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


if __name__ == "__main__":
    unittest.main()
