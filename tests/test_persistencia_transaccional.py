"""
PerfumeTrending.cl — Pruebas de Persistencia Transaccional y Control de Integridad
==================================================================================
Pruebas automatizadas ejecutadas contra base de datos aislada con datos sintéticos.
No utiliza credenciales de producción ni modifica datos reales.
"""

import os
import shutil
import sqlite3
import tempfile
import unittest
from datetime import datetime

# Configurar entorno de pruebas aislado
TEST_DIR = tempfile.mkdtemp()
TEST_DB_PATH = os.path.join(TEST_DIR, "test_perfumes.db")

# Sobrescribir DB_PATH para aislar completamente las pruebas
import APP.backend.database as db_module
db_module.DB_PATH = TEST_DB_PATH
db_module.DB_DIR = TEST_DIR

from APP.backend.database import (
    init_db,
    get_connection,
    get_db_cursor,
    registrar_observacion_oferta,
    registrar_fallo_scraping
)


class TestPersistenciaTransaccional(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Asegurar esquema inicial
        init_db(force_reseed=False)
        # Insertar datos sintéticos de prueba
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("""
            INSERT OR REPLACE INTO tiendas (id, nombre, url_base, trust_score)
            VALUES (999, 'Tienda Test Mock', 'https://www.tiendamock.cl', 95);
            """)
            cursor.execute("""
            INSERT OR REPLACE INTO perfumes (id, nombre, marca, genero, tipo, notas, imagen_url, precio_referencia)
            VALUES (888, 'Fragancia Sintética Test', 'MockBrand', 'Unisex', 'Eau de Parfum', 'Vainilla, Cedro', 'http://img.cl/1.jpg', 50000);
            """)
            cursor.execute("""
            INSERT OR REPLACE INTO variantes_perfume (id, perfume_id, concentracion, volumen_ml, formato, slug, activa)
            VALUES (777, 888, 'Eau de Parfum', 100.0, 'regular', 'fragancia-sintetica-test-100ml', 1);
            """)

    @classmethod
    def tearDownClass(cls):
        try:
            shutil.rmtree(TEST_DIR)
        except Exception:
            pass

    def setUp(self):
        # Limpiar ofertas y precios de prueba antes de cada test
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("DELETE FROM ofertas_actuales WHERE variante_id = 777;")
            cursor.execute("DELETE FROM precios_registro WHERE variante_id = 777;")

    def test_01_primera_observacion_crea_oferta_e_historial(self):
        """Verifica que la primera observación válida crea la oferta viva y su correspondiente registro histórico."""
        obs = {
            "variante_id": 777,
            "perfume_id": 888,
            "tienda_id": 999,
            "precio_actual": 45000,
            "precio_normal": 55000,
            "en_stock": True,
            "url_producto": "https://www.tiendamock.cl/productos/fragancia-test-100ml",
            "volumen_ml": 100
        }
        res = registrar_observacion_oferta(obs)
        self.assertEqual(res["resultado"], "creada")
        self.assertEqual(res["tipo_evento"], "observacion_inicial")
        self.assertEqual(res["precio_nuevo"], 45000)
        self.assertTrue(res["stock_nuevo"])

        # Verificar en base de datos
        with get_db_cursor() as cursor:
            cursor.execute("SELECT * FROM ofertas_actuales WHERE variante_id = 777 AND tienda_id = 999;")
            oferta = cursor.fetchone()
            self.assertIsNotNone(oferta)
            self.assertEqual(oferta["precio_actual"], 45000)
            self.assertEqual(oferta["precio_normal"], 55000)
            self.assertEqual(oferta["en_stock"], 1)
            self.assertEqual(oferta["estado"], "activa")

            cursor.execute("SELECT COUNT(*) FROM precios_registro WHERE variante_id = 777;")
            count_hist = cursor.fetchone()[0]
            self.assertEqual(count_hist, 1)

    def test_02_observacion_identica_no_crea_historial_redundante(self):
        """Verifica que observaciones repetidas sin cambios solo actualizan timestamps y no duplican historial."""
        obs = {
            "variante_id": 777,
            "perfume_id": 888,
            "tienda_id": 999,
            "precio_actual": 45000,
            "precio_normal": 55000,
            "en_stock": True,
            "url_producto": "https://www.tiendamock.cl/productos/fragancia-test-100ml",
            "volumen_ml": 100
        }
        res1 = registrar_observacion_oferta(obs)
        self.assertEqual(res1["resultado"], "creada")

        # Segunda llamada con idénticos valores
        res2 = registrar_observacion_oferta(obs)
        self.assertEqual(res2["resultado"], "sin_cambios")
        self.assertIsNone(res2["tipo_evento"])

        # Historial debe seguir teniendo exactamente 1 registro
        with get_db_cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM precios_registro WHERE variante_id = 777;")
            count_hist = cursor.fetchone()[0]
            self.assertEqual(count_hist, 1)

    def test_03_cambio_de_precio_registra_evento_y_actualiza_oferta(self):
        """Verifica que una baja o subida de precio genera un evento 'cambio_precio' y actualiza la oferta viva."""
        obs_inicial = {
            "variante_id": 777,
            "perfume_id": 888,
            "tienda_id": 999,
            "precio_actual": 45000,
            "precio_normal": 55000,
            "en_stock": True,
            "url_producto": "https://www.tiendamock.cl/productos/fragancia-test-100ml",
            "volumen_ml": 100
        }
        registrar_observacion_oferta(obs_inicial)

        # Variación de precio a 39.990
        obs_cambio = dict(obs_inicial)
        obs_cambio["precio_actual"] = 39990

        res = registrar_observacion_oferta(obs_cambio)
        self.assertEqual(res["resultado"], "actualizada")
        self.assertEqual(res["tipo_evento"], "cambio_precio")
        self.assertEqual(res["precio_anterior"], 45000)
        self.assertEqual(res["precio_nuevo"], 39990)

        with get_db_cursor() as cursor:
            cursor.execute("SELECT precio_actual FROM ofertas_actuales WHERE variante_id = 777;")
            p_act = cursor.fetchone()[0]
            self.assertEqual(p_act, 39990)

            cursor.execute("SELECT COUNT(*) FROM precios_registro WHERE variante_id = 777;")
            count_hist = cursor.fetchone()[0]
            self.assertEqual(count_hist, 2)

    def test_04_cambio_de_stock_actualiza_estado_y_registra_evento(self):
        """Verifica que cuando un producto pasa a agotado (en_stock=False), se registra 'cambio_stock' y estado='agotada'."""
        obs_inicial = {
            "variante_id": 777,
            "perfume_id": 888,
            "tienda_id": 999,
            "precio_actual": 45000,
            "precio_normal": 55000,
            "en_stock": True,
            "url_producto": "https://www.tiendamock.cl/productos/fragancia-test-100ml",
            "volumen_ml": 100
        }
        registrar_observacion_oferta(obs_inicial)

        # Producto se agota
        obs_agotado = dict(obs_inicial)
        obs_agotado["en_stock"] = False

        res = registrar_observacion_oferta(obs_agotado)
        self.assertEqual(res["resultado"], "actualizada")
        self.assertEqual(res["tipo_evento"], "cambio_stock")
        self.assertFalse(res["stock_nuevo"])

        with get_db_cursor() as cursor:
            cursor.execute("SELECT en_stock, estado FROM ofertas_actuales WHERE variante_id = 777;")
            row = cursor.fetchone()
            self.assertEqual(row["en_stock"], 0)
            self.assertEqual(row["estado"], "agotada")

    def test_05_cambio_multiple_simultaneo(self):
        """Verifica que cambios simultáneos de precio, stock y URL producen un evento coherente 'cambio_multiple'."""
        obs_inicial = {
            "variante_id": 777,
            "perfume_id": 888,
            "tienda_id": 999,
            "precio_actual": 45000,
            "precio_normal": 55000,
            "en_stock": True,
            "url_producto": "https://www.tiendamock.cl/productos/fragancia-test-100ml",
            "volumen_ml": 100
        }
        registrar_observacion_oferta(obs_inicial)

        obs_multiple = {
            "variante_id": 777,
            "perfume_id": 888,
            "tienda_id": 999,
            "precio_actual": 42000,
            "precio_normal": 55000,
            "en_stock": False,
            "url_producto": "https://www.tiendamock.cl/productos/fragancia-test-v2",
            "volumen_ml": 100
        }
        res = registrar_observacion_oferta(obs_multiple)
        self.assertEqual(res["resultado"], "actualizada")
        self.assertEqual(res["tipo_evento"], "cambio_multiple")
        self.assertIn("precio_actual", res["campos_modificados"])
        self.assertIn("en_stock", res["campos_modificados"])
        self.assertIn("url_producto", res["campos_modificados"])

    def test_06_fallo_de_scraping_no_altera_datos_confirmados(self):
        """Verifica que registrar_fallo_scraping incrementa fallos_consecutivos pero NO altera precio, stock ni URL."""
        obs_inicial = {
            "variante_id": 777,
            "perfume_id": 888,
            "tienda_id": 999,
            "precio_actual": 45000,
            "precio_normal": 55000,
            "en_stock": True,
            "url_producto": "https://www.tiendamock.cl/productos/fragancia-test-100ml",
            "volumen_ml": 100
        }
        registrar_observacion_oferta(obs_inicial)

        # Simular fallo de scraping (timeout o HTTP 500)
        res_fallo = registrar_fallo_scraping(
            tienda_id=999,
            variante_id=777,
            mensaje="Timeout 504 Gateway Timeout tras 10s de espera"
        )
        self.assertEqual(res_fallo["resultado"], "fallo_registrado")
        self.assertEqual(res_fallo["fallos_consecutivos"], 1)
        self.assertEqual(res_fallo["precio_actual"], 45000)
        self.assertTrue(res_fallo["en_stock"])

        # Verificar que la oferta viva mantiene intacto precio, stock y URL
        with get_db_cursor() as cursor:
            cursor.execute("SELECT * FROM ofertas_actuales WHERE variante_id = 777 AND tienda_id = 999;")
            oferta = cursor.fetchone()
            self.assertEqual(oferta["precio_actual"], 45000)
            self.assertEqual(oferta["en_stock"], 1)
            self.assertEqual(oferta["url_producto"], "https://www.tiendamock.cl/productos/fragancia-test-100ml")
            self.assertEqual(oferta["fallos_consecutivos"], 1)
            self.assertIn("Timeout 504", oferta["ultimo_error"])

            # Historial no debe haber crecido por el fallo
            cursor.execute("SELECT COUNT(*) FROM precios_registro WHERE variante_id = 777;")
            count_hist = cursor.fetchone()[0]
            self.assertEqual(count_hist, 1)

    def test_07_precio_invalido_lanza_excepcion_y_no_deja_cambios_parciales(self):
        """Verifica que observaciones con precio negativo o cero son rechazadas de inmediato."""
        obs_invalida = {
            "variante_id": 777,
            "perfume_id": 888,
            "tienda_id": 999,
            "precio_actual": -1000,
            "en_stock": True,
            "url_producto": "https://www.tiendamock.cl/p/1"
        }
        with self.assertRaises(ValueError):
            registrar_observacion_oferta(obs_invalida)

        # Base de datos debe estar vacía para esa variante
        with get_db_cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM ofertas_actuales WHERE variante_id = 777;")
            self.assertEqual(cursor.fetchone()[0], 0)

    def test_08_stock_desconocido_es_rechazado(self):
        """Verifica que el stock no puede ser None (debe ser explícito True o False)."""
        obs_stock_null = {
            "variante_id": 777,
            "perfume_id": 888,
            "tienda_id": 999,
            "precio_actual": 45000,
            "en_stock": None,
            "url_producto": "https://www.tiendamock.cl/p/1"
        }
        with self.assertRaises(ValueError):
            registrar_observacion_oferta(obs_stock_null)

    def test_09_url_invalida_es_rechazada(self):
        """Verifica que se exija una URL válida que comience con http:// o https://."""
        obs_url_mala = {
            "variante_id": 777,
            "perfume_id": 888,
            "tienda_id": 999,
            "precio_actual": 45000,
            "en_stock": True,
            "url_producto": "javascript:alert(1)"
        }
        with self.assertRaises(ValueError):
            registrar_observacion_oferta(obs_url_mala)


if __name__ == "__main__":
    unittest.main()
