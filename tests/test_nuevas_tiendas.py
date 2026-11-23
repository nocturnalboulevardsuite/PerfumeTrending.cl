"""
tests/test_nuevas_tiendas.py
============================
Pruebas unitarias para la integración de nuevas tiendas:
- Conector Shopify resiliente (L'Odoro, Mundo Aromas, Cosmetic, Fragante, ComprarEnChile)
- Conector WooCommerce Store API (Chile Perfume, Portal del Perfume, Aromata)
- Normalización, resolución de entidades y detección de variantes
- Rechazo defensivo de cosméticos, decants y clones de inspiración
"""

# Importación de librería estándar o dependencia externa (json)
import json
# Importación de librería estándar o dependencia externa (os)
import os
# Importación de librería estándar o dependencia externa (unittest)
import unittest
# Importación de componentes (MagicMock, patch) desde el módulo 'unittest.mock'
from unittest.mock import MagicMock, patch

# Importación de componentes (coincide_con_perfume, detectar_formato_oferta, es_producto_perfume_valido, extraer_concentracion, ...) desde el módulo 'APP.backend.normalizador'
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
# Importación de componentes (coincide_entidad_detallada, extraer_variedades_shopify, extraer_variedades_woocommerce) desde el módulo 'APP.backend.scraper_periodico'
from APP.backend.scraper_periodico import (
    coincide_entidad_detallada,
    extraer_variedades_shopify,
    extraer_variedades_woocommerce,
)

# Asignamos 'FIXTURES_DIR' con os.path.join(os.path.dirname(__file__), 'f...
FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


# Definición de clase 'TestNuevasTiendasIntegracion' que modela la estructura y lógica del componente
class TestNuevasTiendasIntegracion(unittest.TestCase):

    # Definición de función 'setUp' sin parámetros externos
    def setUp(self):
        # Gestión automática de contexto y recursos para: open(os.path.join(FIXTURES_DIR, 'shopify_sugges...
        with open(os.path.join(FIXTURES_DIR, "shopify_suggest_fixture.json"), "r", encoding="utf-8") as f:
            # Procesamiento de serialización o deserialización de estructura JSON
            self.shopify_payload = json.load(f)

        # Gestión automática de contexto y recursos para: open(os.path.join(FIXTURES_DIR, 'woocommerce_st...
        with open(os.path.join(FIXTURES_DIR, "woocommerce_store_api_fixture.json"), "r", encoding="utf-8") as f:
            # Procesamiento de serialización o deserialización de estructura JSON
            self.woocommerce_payload = json.load(f)

    # Definición de función 'test_normalizacion_titulos_nuevas_tiendas' sin parámetros externos
    def test_normalizacion_titulos_nuevas_tiendas(self):
        """Verifica que los títulos de las nuevas tiendas se normalicen limpiamente sin sesgo de género."""
        # L'Odoro
        t1 = "Tommy Hilfiger Tommy Girl New York EDT 100Ml Mujer"
        # Aserción de prueba unitaria: self.assertEqual(normalizar_marca_canonica('Tommy Hi...
        self.assertEqual(normalizar_marca_canonica("Tommy Hilfiger"), "Tommy Hilfiger")
        # Aserción de prueba unitaria: self.assertEqual(extraer_genero(t1), 'Mujer')
        self.assertEqual(extraer_genero(t1), "Mujer")
        # Aserción de prueba unitaria: self.assertEqual(extraer_concentracion(t1), 'Eau de ...
        self.assertEqual(extraer_concentracion(t1), "Eau de Toilette")
        # Aserción de prueba unitaria: self.assertEqual(extraer_volumen_ml(t1), 100)
        self.assertEqual(extraer_volumen_ml(t1), 100)

        # Chile Perfume
        t2 = "Christian Dior Sauvage 200ML EDP Hombre"
        # Aserción de prueba unitaria: self.assertEqual(normalizar_marca_canonica('Christia...
        self.assertEqual(normalizar_marca_canonica("Christian Dior"), "Dior")
        # Aserción de prueba unitaria: self.assertEqual(extraer_genero(t2), 'Hombre')
        self.assertEqual(extraer_genero(t2), "Hombre")
        # Aserción de prueba unitaria: self.assertEqual(extraer_concentracion(t2), 'Eau de ...
        self.assertEqual(extraer_concentracion(t2), "Eau de Parfum")
        # Aserción de prueba unitaria: self.assertEqual(extraer_volumen_ml(t2), 200)
        self.assertEqual(extraer_volumen_ml(t2), 200)

        # Cosmetic
        t3 = "Perfume My Devotion EDP Intense 100 ml Dolce And Gabbana Mujer"
        # Aserción de prueba unitaria: self.assertEqual(normalizar_marca_canonica('Dolce An...
        self.assertEqual(normalizar_marca_canonica("Dolce And Gabbana"), "Dolce & Gabbana")
        # Aserción de prueba unitaria: self.assertEqual(extraer_genero(t3), 'Mujer')
        self.assertEqual(extraer_genero(t3), "Mujer")
        # Aserción de prueba unitaria: self.assertEqual(extraer_volumen_ml(t3), 100)
        self.assertEqual(extraer_volumen_ml(t3), 100)


    # Definición de función 'test_marcas_nicho_y_rechazo_disenador' sin parámetros externos
    def test_marcas_nicho_y_rechazo_disenador(self):
        """Verifica resolución canónica de marcas nicho y rechazo estricto de Diseñador."""
        # Importación de componentes (MARCAS_INVALIDAS_CATALOGO) desde el módulo 'APP.backend.normalizador'
        from APP.backend.normalizador import MARCAS_INVALIDAS_CATALOGO
        
        # Aserción de prueba unitaria: self.assertEqual(normalizar_marca_canonica('Argos'),...
        self.assertEqual(normalizar_marca_canonica("Argos"), "Argos")
        # Aserción de prueba unitaria: self.assertEqual(normalizar_marca_canonica('eight & ...
        self.assertEqual(normalizar_marca_canonica("eight & bob"), "Eight & Bob")
        # Aserción de prueba unitaria: self.assertEqual(normalizar_marca_canonica('andy tau...
        self.assertEqual(normalizar_marca_canonica("andy tauer"), "Tauer Perfumes")
        # Aserción de prueba unitaria: self.assertEqual(normalizar_marca_canonica('bon parf...
        self.assertEqual(normalizar_marca_canonica("bon parfumeur"), "Bon Parfumeur")
        # Aserción de prueba unitaria: self.assertEqual(normalizar_marca_canonica('stephane...
        self.assertEqual(normalizar_marca_canonica("stephane humbert lucas"), "Stéphane Humbert Lucas")
        # Aserción de prueba unitaria: self.assertEqual(normalizar_marca_canonica('ramon mo...
        self.assertEqual(normalizar_marca_canonica("ramon monegal"), "Ramón Monegal")
        
        # Validar rechazo de marcas inválidas genéricas
        self.assertIn("diseñador", MARCAS_INVALIDAS_CATALOGO)
        # Aserción de prueba unitaria: self.assertIn('nicho', MARCAS_INVALIDAS_CATALOGO)
        self.assertIn("nicho", MARCAS_INVALIDAS_CATALOGO)

    # Definición de función 'test_filtro_defensivo_cosmeticos_y_clones' sin parámetros externos
    def test_filtro_defensivo_cosmeticos_y_clones(self):
        """Descarta productos no-perfume, esmaltes y perfumes de inspiración."""
        # Esmalte de uñas de Cosmetic.cl
        self.assertFalse(es_producto_perfume_valido("Vogue Base SOS Uñas Escamadas x 14ml", volumen_min_ml=25))

        # Decant / Discovery Box < 25 ml de Fragante.cl
        self.assertFalse(es_producto_perfume_valido("Sweet Tooth Discovery Box | 5 ml de cada fragancia", volumen_min_ml=25))

        # Inspiración / clon de ComprarEnChile.cl
        self.assertFalse(es_producto_perfume_valido("Martin Lion H35 - Inspiracion Dior Sauvage - EDP 50 ML (H)", volumen_min_ml=25))

    # Definición de función 'test_conector_shopify_suggest_mock' sin parámetros externos
    def test_conector_shopify_suggest_mock(self):
        """Prueba extracción y discriminación regular/tester en tiendas Shopify."""
        # Asignamos 'mock_session' con MagicMock()
        mock_session = MagicMock()
        # Asignamos 'mock_response' con MagicMock()
        mock_response = MagicMock()
        # Asignamos 'mock_response.status_code' con 200
        mock_response.status_code = 200
        # Asignamos 'mock_response.json.return_value' con self.shopify_payload
        mock_response.json.return_value = self.shopify_payload
        # Asignamos 'mock_session.get.return_value' con mock_response
        mock_session.get.return_value = mock_response

        # Asignamos 'variedades' con extraer_variedades_shopify(session=mock_se...
        variedades = extraer_variedades_shopify(
            session=mock_session,
            dominio="lodoro.cl",
            perfume_nombre="Sauvage",
            marca="Dior",
            volumen_ml_defecto=100,
            concentracion="Eau de Toilette",
            precio_referencia=130000,
        )

        # Aserción de prueba unitaria: self.assertGreaterEqual(len(variedades), 2)
        self.assertGreaterEqual(len(variedades), 2)
        # 100 ML regular
        v100 = next((v for v in variedades if v["volumen_ml"] == 100 and v["formato"] == "regular"), None)
        # Aserción de prueba unitaria: self.assertIsNotNone(v100)
        self.assertIsNotNone(v100)
        # Aserción de prueba unitaria: self.assertEqual(v100['precio_actual'], 129900)
        self.assertEqual(v100["precio_actual"], 129900)
        # Aserción de prueba unitaria: self.assertTrue(v100['en_stock'])
        self.assertTrue(v100["en_stock"])

        # 200 ML regular
        v200 = next((v for v in variedades if v["volumen_ml"] == 200 and v["formato"] == "regular"), None)
        # Aserción de prueba unitaria: self.assertIsNotNone(v200)
        self.assertIsNotNone(v200)
        # Aserción de prueba unitaria: self.assertEqual(v200['precio_actual'], 179900)
        self.assertEqual(v200["precio_actual"], 179900)
        # Aserción de prueba unitaria: self.assertTrue(v200['en_stock'])
        self.assertTrue(v200["en_stock"])

    # Definición de función 'test_conector_woocommerce_store_api_mock' sin parámetros externos
    def test_conector_woocommerce_store_api_mock(self):
        """Prueba extracción en WooCommerce Store API de Chile Perfume."""
        # Asignamos 'mock_session' con MagicMock()
        mock_session = MagicMock()
        # Asignamos 'mock_response' con MagicMock()
        mock_response = MagicMock()
        # Asignamos 'mock_response.status_code' con 200
        mock_response.status_code = 200
        # Asignamos 'mock_response.json.return_value' con self.woocommerce_payload
        mock_response.json.return_value = self.woocommerce_payload
        # Asignamos 'mock_session.get.return_value' con mock_response
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

        # Aserción de prueba unitaria: self.assertGreaterEqual(len(variedades), 2)
        self.assertGreaterEqual(len(variedades), 2)
        # Asignamos 'v100' con next((v for v in variedades if v['volumen_...
        v100 = next((v for v in variedades if v["volumen_ml"] == 100), None)
        # Aserción de prueba unitaria: self.assertIsNotNone(v100)
        self.assertIsNotNone(v100)
        # Aserción de prueba unitaria: self.assertEqual(v100['precio_actual'], 159990)
        self.assertEqual(v100["precio_actual"], 159990)
        # Aserción de prueba unitaria: self.assertEqual(v100['precio_normal'], 179990)
        self.assertEqual(v100["precio_normal"], 179990)
        # Aserción de prueba unitaria: self.assertTrue(v100['en_stock'])
        self.assertTrue(v100["en_stock"])

        # Asignamos 'v200' con next((v for v in variedades if v['volumen_...
        v200 = next((v for v in variedades if v["volumen_ml"] == 200), None)
        # Aserción de prueba unitaria: self.assertIsNotNone(v200)
        self.assertIsNotNone(v200)
        # Aserción de prueba unitaria: self.assertEqual(v200['precio_actual'], 219990)
        self.assertEqual(v200["precio_actual"], 219990)
        # Aserción de prueba unitaria: self.assertTrue(v200['en_stock'])
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
        # Aserción de prueba unitaria: self.assertEqual(len(variedades_jpg), 1)
        self.assertEqual(len(variedades_jpg), 1)
        # Aserción de prueba unitaria: self.assertFalse(variedades_jpg[0]['en_stock'])
        self.assertFalse(variedades_jpg[0]["en_stock"])
        # Aserción de prueba unitaria: self.assertEqual(variedades_jpg[0]['precio_actual'],...
        self.assertEqual(variedades_jpg[0]["precio_actual"], 119990)


# Punto de entrada principal cuando el script se invoca directamente desde consola
if __name__ == "__main__":
    # Ejecutamos instrucción: unittest.main()
    unittest.main()

