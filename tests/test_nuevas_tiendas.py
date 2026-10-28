"""
tests/test_nuevas_tiendas.py
============================
Pruebas unitarias para la integración de nuevas tiendas:
- Conector Shopify resiliente (L'Odoro, Mundo Aromas, Cosmetic, Fragante, ComprarEnChile)
- Conector WooCommerce Store API (Chile Perfume, Portal del Perfume, Aromata)
- Normalización, resolución de entidades y detección de variantes
- Rechazo defensivo de cosméticos, decants y clones de inspiración
"""

import json
import os
import unittest
from unittest.mock import MagicMock, patch

from APP.backend.normalizador import (
    coincide_con_perfume,
    detectar_formato_oferta,
    es_producto_perfume_valido,
    extraer_concentracion,
    extraer_genero,
    extraer_volumen_ml,
    limpiar_nombre_perfume,
    normalizar_marca_canonica,
)
from APP.backend.scraper_periodico import (
    coincide_entidad_detallada,
    extraer_variedades_shopify,
    extraer_variedades_woocommerce,
)

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


class TestNuevasTiendasIntegracion(unittest.TestCase):

    def setUp(self):
        with open(os.path.join(FIXTURES_DIR, "shopify_suggest_fixture.json"), "r", encoding="utf-8") as f:
            self.shopify_payload = json.load(f)

        with open(os.path.join(FIXTURES_DIR, "woocommerce_store_api_fixture.json"), "r", encoding="utf-8") as f:
            self.woocommerce_payload = json.load(f)

    def test_normalizacion_titulos_nuevas_tiendas(self):
        """Verifica que los títulos de las nuevas tiendas se normalicen limpiamente sin sesgo de género."""
        # L'Odoro
        t1 = "Tommy Hilfiger Tommy Girl New York EDT 100Ml Mujer"
        self.assertEqual(normalizar_marca_canonica("Tommy Hilfiger"), "Tommy Hilfiger")
        self.assertEqual(extraer_genero(t1), "Mujer")
        self.assertEqual(extraer_concentracion(t1), "Eau de Toilette")
        self.assertEqual(extraer_volumen_ml(t1), 100)

        # Chile Perfume
        t2 = "Christian Dior Sauvage 200ML EDP Hombre"
        self.assertEqual(normalizar_marca_canonica("Christian Dior"), "Dior")
        self.assertEqual(extraer_genero(t2), "Hombre")
        self.assertEqual(extraer_concentracion(t2), "Eau de Parfum")
        self.assertEqual(extraer_volumen_ml(t2), 200)

        # Cosmetic
        t3 = "Perfume My Devotion EDP Intense 100 ml Dolce And Gabbana Mujer"
        self.assertEqual(normalizar_marca_canonica("Dolce And Gabbana"), "Dolce & Gabbana")
        self.assertEqual(extraer_genero(t3), "Mujer")
        self.assertEqual(extraer_volumen_ml(t3), 100)


    def test_marcas_nicho_y_rechazo_disenador(self):
        """Verifica resolución canónica de marcas nicho y rechazo estricto de Diseñador."""
        from APP.backend.normalizador import MARCAS_INVALIDAS_CATALOGO
        
        self.assertEqual(normalizar_marca_canonica("Argos"), "Argos")
        self.assertEqual(normalizar_marca_canonica("eight & bob"), "Eight & Bob")
        self.assertEqual(normalizar_marca_canonica("andy tauer"), "Tauer Perfumes")
        self.assertEqual(normalizar_marca_canonica("bon parfumeur"), "Bon Parfumeur")
        self.assertEqual(normalizar_marca_canonica("stephane humbert lucas"), "Stéphane Humbert Lucas")
        self.assertEqual(normalizar_marca_canonica("ramon monegal"), "Ramón Monegal")
        
        # Validar rechazo de marcas inválidas genéricas
        self.assertIn("diseñador", MARCAS_INVALIDAS_CATALOGO)
        self.assertIn("nicho", MARCAS_INVALIDAS_CATALOGO)

    def test_filtro_defensivo_cosmeticos_y_clones(self):
        """Descarta productos no-perfume, esmaltes y perfumes de inspiración."""
        # Esmalte de uñas de Cosmetic.cl
        self.assertFalse(es_producto_perfume_valido("Vogue Base SOS Uñas Escamadas x 14ml", volumen_min_ml=25))

        # Decant / Discovery Box < 25 ml de Fragante.cl
        self.assertFalse(es_producto_perfume_valido("Sweet Tooth Discovery Box | 5 ml de cada fragancia", volumen_min_ml=25))

        # Inspiración / clon de ComprarEnChile.cl
        self.assertFalse(es_producto_perfume_valido("Martin Lion H35 - Inspiracion Dior Sauvage - EDP 50 ML (H)", volumen_min_ml=25))

    def test_conector_shopify_suggest_mock(self):
        """Prueba extracción y discriminación regular/tester en tiendas Shopify."""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.shopify_payload
        mock_session.get.return_value = mock_response

        variedades = extraer_variedades_shopify(
            session=mock_session,
            dominio="lodoro.cl",
            perfume_nombre="Sauvage",
            marca="Dior",
            volumen_ml_defecto=100,
            concentracion="Eau de Toilette",
            precio_referencia=130000,
        )

        self.assertGreaterEqual(len(variedades), 2)
        # 100 ML regular
        v100 = next((v for v in variedades if v["volumen_ml"] == 100 and v["formato"] == "regular"), None)
        self.assertIsNotNone(v100)
        self.assertEqual(v100["precio_actual"], 129900)
        self.assertTrue(v100["en_stock"])

        # 200 ML regular
        v200 = next((v for v in variedades if v["volumen_ml"] == 200 and v["formato"] == "regular"), None)
        self.assertIsNotNone(v200)
        self.assertEqual(v200["precio_actual"], 179900)
        self.assertTrue(v200["en_stock"])

    def test_conector_woocommerce_store_api_mock(self):
        """Prueba extracción en WooCommerce Store API de Chile Perfume."""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.woocommerce_payload
        mock_session.get.return_value = mock_response

        # Búsqueda de Dior Sauvage EDP
        variedades = extraer_variedades_woocommerce(
            session=mock_session,
            dominio="www.chileperfume.cl",
            perfume_nombre="Sauvage",
            marca="Dior",
            volumen_ml_defecto=100,
            concentracion="Eau de Parfum",
            precio_referencia=160000,
        )

        self.assertGreaterEqual(len(variedades), 2)
        v100 = next((v for v in variedades if v["volumen_ml"] == 100), None)
        self.assertIsNotNone(v100)
        self.assertEqual(v100["precio_actual"], 159990)
        self.assertEqual(v100["precio_normal"], 179990)
        self.assertTrue(v100["en_stock"])

        v200 = next((v for v in variedades if v["volumen_ml"] == 200), None)
        self.assertIsNotNone(v200)
        self.assertEqual(v200["precio_actual"], 219990)
        self.assertTrue(v200["en_stock"])

        # Búsqueda de JPG Le Beau (debe reportar en_stock: False)
        variedades_jpg = extraer_variedades_woocommerce(
            session=mock_session,
            dominio="www.chileperfume.cl",
            perfume_nombre="Le Beau Le Parfum",
            marca="Jean Paul Gaultier",
            volumen_ml_defecto=125,
            concentracion="Eau de Parfum",
            precio_referencia=120000,
        )
        self.assertEqual(len(variedades_jpg), 1)
        self.assertFalse(variedades_jpg[0]["en_stock"])
        self.assertEqual(variedades_jpg[0]["precio_actual"], 119990)


if __name__ == "__main__":
    unittest.main()

