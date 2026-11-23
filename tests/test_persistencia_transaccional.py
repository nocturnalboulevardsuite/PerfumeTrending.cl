"""
PerfumeTrending.cl — Pruebas de Persistencia Transaccional y Control de Integridad
==================================================================================
Pruebas automatizadas ejecutadas contra base de datos aislada con datos sintéticos.
No utiliza credenciales de producción ni modifica datos reales.
"""

# Importación de librería estándar o dependencia externa (os)
import os
# Importación de librería estándar o dependencia externa (shutil)
import shutil
# Importación de librería estándar o dependencia externa (sqlite3)
import sqlite3
# Importación de librería estándar o dependencia externa (tempfile)
import tempfile
# Importación de librería estándar o dependencia externa (unittest)
import unittest
# Importación de componentes (datetime) desde el módulo 'datetime'
from datetime import datetime

# Configurar entorno de pruebas aislado
TEST_DIR = tempfile.mkdtemp()
# Asignamos 'TEST_DB_PATH' con os.path.join(TEST_DIR, 'test_perfumes.db')
TEST_DB_PATH = os.path.join(TEST_DIR, "test_perfumes.db")

# Sobrescribir DB_PATH y desconectar supabase para aislar completamente las pruebas
import APP.backend.database as db_module
# Asignamos 'db_module.DB_PATH' con TEST_DB_PATH
db_module.DB_PATH = TEST_DB_PATH
# Asignamos 'db_module.DB_DIR' con TEST_DIR
db_module.DB_DIR = TEST_DIR
# Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
db_module.is_supabase_disponible = lambda: False
# Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
db_module.get_supabase = lambda *args, **kwargs: None

# Importación de componentes (init_db, get_connection, get_db_cursor, registrar_observacion_oferta, ...) desde el módulo 'APP.backend.database'
from APP.backend.database import (
    init_db,
    get_connection,
    get_db_cursor,
    registrar_observacion_oferta,
    registrar_fallo_scraping
)


# Definición de clase 'TestPersistenciaTransaccional' que modela la estructura y lógica del componente
class TestPersistenciaTransaccional(unittest.TestCase):
    # Definición de función 'setUpClass' (parámetros: cls)
    @classmethod
    def setUpClass(cls):
        # Asegurar esquema inicial
        init_db(force_reseed=False)
        # Insertar datos sintéticos de prueba
        with get_db_cursor(commit=True) as cursor:
            # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
            cursor.execute("""
            INSERT OR REPLACE INTO tiendas (id, nombre, url_base, trust_score)
            VALUES (999, 'Tienda Test Mock', 'https://www.tiendamock.cl', 95);
            """)
            # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
            cursor.execute("""
            INSERT OR REPLACE INTO perfumes (id, nombre, marca, genero, tipo, notas, imagen_url, precio_referencia)
            VALUES (888, 'Fragancia Sintética Test', 'MockBrand', 'Unisex', 'Eau de Parfum', 'Vainilla, Cedro', 'http://img.cl/1.jpg', 50000);
            """)
            # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
            cursor.execute("""
            INSERT OR REPLACE INTO variantes_perfume (id, perfume_id, concentracion, volumen_ml, formato, slug, activa)
            VALUES (777, 888, 'Eau de Parfum', 100.0, 'regular', 'fragancia-sintetica-test-100ml', 1);
            """)

    # Definición de función 'tearDownClass' (parámetros: cls)
    @classmethod
    def tearDownClass(cls):
        # Bloque try/except para manejo seguro de errores y resiliencia operativa
        try:
            # Ejecutamos instrucción: shutil.rmtree(TEST_DIR)
            shutil.rmtree(TEST_DIR)
        except Exception:
            # Ejecutamos instrucción: pass
            pass

    # Definición de función 'setUp' sin parámetros externos
    def setUp(self):
        # Limpiar ofertas y precios de prueba antes de cada test
        with get_db_cursor(commit=True) as cursor:
            # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
            cursor.execute("DELETE FROM ofertas_actuales WHERE variante_id = 777;")
            # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
            cursor.execute("DELETE FROM precios_registro WHERE variante_id = 777;")

    # Definición de función 'test_01_primera_observacion_crea_oferta_e_historial' sin parámetros externos
    def test_01_primera_observacion_crea_oferta_e_historial(self):
        """Verifica que la primera observación válida crea la oferta viva y su correspondiente registro histórico."""
        # Asignamos 'obs' con {'variante_id': 777, 'perfume_id': 888, 't...
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
        # Asignamos 'res' con registrar_observacion_oferta(obs)
        res = registrar_observacion_oferta(obs)
        # Aserción de prueba unitaria: self.assertEqual(res['resultado'], 'creada')
        self.assertEqual(res["resultado"], "creada")
        # Aserción de prueba unitaria: self.assertEqual(res['tipo_evento'], 'observacion_in...
        self.assertEqual(res["tipo_evento"], "observacion_inicial")
        # Aserción de prueba unitaria: self.assertEqual(res['precio_nuevo'], 45000)
        self.assertEqual(res["precio_nuevo"], 45000)
        # Aserción de prueba unitaria: self.assertTrue(res['stock_nuevo'])
        self.assertTrue(res["stock_nuevo"])

        # Verificar en base de datos
        with get_db_cursor() as cursor:
            # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
            cursor.execute("SELECT * FROM ofertas_actuales WHERE variante_id = 777 AND tienda_id = 999;")
            # Asignamos 'oferta' con cursor.fetchone()
            oferta = cursor.fetchone()
            # Aserción de prueba unitaria: self.assertIsNotNone(oferta)
            self.assertIsNotNone(oferta)
            # Aserción de prueba unitaria: self.assertEqual(oferta['precio_actual'], 45000)
            self.assertEqual(oferta["precio_actual"], 45000)
            # Aserción de prueba unitaria: self.assertEqual(oferta['precio_normal'], 55000)
            self.assertEqual(oferta["precio_normal"], 55000)
            # Aserción de prueba unitaria: self.assertEqual(oferta['en_stock'], 1)
            self.assertEqual(oferta["en_stock"], 1)
            # Aserción de prueba unitaria: self.assertEqual(oferta['estado'], 'activa')
            self.assertEqual(oferta["estado"], "activa")

            # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
            cursor.execute("SELECT COUNT(*) FROM precios_registro WHERE variante_id = 777;")
            # Asignamos 'count_hist' con cursor.fetchone()[0]
            count_hist = cursor.fetchone()[0]
            # Aserción de prueba unitaria: self.assertEqual(count_hist, 1)
            self.assertEqual(count_hist, 1)

    # Definición de función 'test_02_observacion_identica_no_crea_historial_redundante' sin parámetros externos
    def test_02_observacion_identica_no_crea_historial_redundante(self):
        """Verifica que observaciones repetidas sin cambios solo actualizan timestamps y no duplican historial."""
        # Asignamos 'obs' con {'variante_id': 777, 'perfume_id': 888, 't...
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
        # Asignamos 'res1' con registrar_observacion_oferta(obs)
        res1 = registrar_observacion_oferta(obs)
        # Aserción de prueba unitaria: self.assertEqual(res1['resultado'], 'creada')
        self.assertEqual(res1["resultado"], "creada")

        # Segunda llamada con idénticos valores
        res2 = registrar_observacion_oferta(obs)
        # Aserción de prueba unitaria: self.assertEqual(res2['resultado'], 'sin_cambios')
        self.assertEqual(res2["resultado"], "sin_cambios")
        # Aserción de prueba unitaria: self.assertIsNone(res2['tipo_evento'])
        self.assertIsNone(res2["tipo_evento"])

        # Historial debe seguir teniendo exactamente 1 registro
        with get_db_cursor() as cursor:
            # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
            cursor.execute("SELECT COUNT(*) FROM precios_registro WHERE variante_id = 777;")
            # Asignamos 'count_hist' con cursor.fetchone()[0]
            count_hist = cursor.fetchone()[0]
            # Aserción de prueba unitaria: self.assertEqual(count_hist, 1)
            self.assertEqual(count_hist, 1)

    # Definición de función 'test_03_cambio_de_precio_registra_evento_y_actualiza_oferta' sin parámetros externos
    def test_03_cambio_de_precio_registra_evento_y_actualiza_oferta(self):
        """Verifica que una baja o subida de precio genera un evento 'cambio_precio' y actualiza la oferta viva."""
        # Asignamos 'obs_inicial' con {'variante_id': 777, 'perfume_id': 888, 't...
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
        # Ejecutamos instrucción: registrar_observacion_oferta(obs_inicial)
        registrar_observacion_oferta(obs_inicial)

        # Variación de precio a 39.990
        obs_cambio = dict(obs_inicial)
        # Asignamos 'obs_cambio['precio_actual']' con 39990
        obs_cambio["precio_actual"] = 39990

        # Asignamos 'res' con registrar_observacion_oferta(obs_cambio)
        res = registrar_observacion_oferta(obs_cambio)
        # Aserción de prueba unitaria: self.assertEqual(res['resultado'], 'actualizada')
        self.assertEqual(res["resultado"], "actualizada")
        # Aserción de prueba unitaria: self.assertEqual(res['tipo_evento'], 'cambio_precio')
        self.assertEqual(res["tipo_evento"], "cambio_precio")
        # Aserción de prueba unitaria: self.assertEqual(res['precio_anterior'], 45000)
        self.assertEqual(res["precio_anterior"], 45000)
        # Aserción de prueba unitaria: self.assertEqual(res['precio_nuevo'], 39990)
        self.assertEqual(res["precio_nuevo"], 39990)

        # Gestión automática de contexto y recursos para: get_db_cursor()
        with get_db_cursor() as cursor:
            # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
            cursor.execute("SELECT precio_actual FROM ofertas_actuales WHERE variante_id = 777;")
            # Asignamos 'p_act' con cursor.fetchone()[0]
            p_act = cursor.fetchone()[0]
            # Aserción de prueba unitaria: self.assertEqual(p_act, 39990)
            self.assertEqual(p_act, 39990)

            # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
            cursor.execute("SELECT COUNT(*) FROM precios_registro WHERE variante_id = 777;")
            # Asignamos 'count_hist' con cursor.fetchone()[0]
            count_hist = cursor.fetchone()[0]
            # Aserción de prueba unitaria: self.assertEqual(count_hist, 2)
            self.assertEqual(count_hist, 2)

    # Definición de función 'test_04_cambio_de_stock_actualiza_estado_y_registra_evento' sin parámetros externos
    def test_04_cambio_de_stock_actualiza_estado_y_registra_evento(self):
        """Verifica que cuando un producto pasa a agotado (en_stock=False), se registra 'cambio_stock' y estado='agotada'."""
        # Asignamos 'obs_inicial' con {'variante_id': 777, 'perfume_id': 888, 't...
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
        # Ejecutamos instrucción: registrar_observacion_oferta(obs_inicial)
        registrar_observacion_oferta(obs_inicial)

        # Producto se agota
        obs_agotado = dict(obs_inicial)
        # Asignamos 'obs_agotado['en_stock']' con False
        obs_agotado["en_stock"] = False

        # Asignamos 'res' con registrar_observacion_oferta(obs_agotado)
        res = registrar_observacion_oferta(obs_agotado)
        # Aserción de prueba unitaria: self.assertEqual(res['resultado'], 'actualizada')
        self.assertEqual(res["resultado"], "actualizada")
        # Aserción de prueba unitaria: self.assertEqual(res['tipo_evento'], 'cambio_stock')
        self.assertEqual(res["tipo_evento"], "cambio_stock")
        # Aserción de prueba unitaria: self.assertFalse(res['stock_nuevo'])
        self.assertFalse(res["stock_nuevo"])

        # Gestión automática de contexto y recursos para: get_db_cursor()
        with get_db_cursor() as cursor:
            # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
            cursor.execute("SELECT en_stock, estado FROM ofertas_actuales WHERE variante_id = 777;")
            # Asignamos 'row' con cursor.fetchone()
            row = cursor.fetchone()
            # Aserción de prueba unitaria: self.assertEqual(row['en_stock'], 0)
            self.assertEqual(row["en_stock"], 0)
            # Aserción de prueba unitaria: self.assertEqual(row['estado'], 'agotada')
            self.assertEqual(row["estado"], "agotada")

    # Definición de función 'test_05_cambio_multiple_simultaneo' sin parámetros externos
    def test_05_cambio_multiple_simultaneo(self):
        """Verifica que cambios simultáneos de precio, stock y URL producen un evento coherente 'cambio_multiple'."""
        # Asignamos 'obs_inicial' con {'variante_id': 777, 'perfume_id': 888, 't...
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
        # Ejecutamos instrucción: registrar_observacion_oferta(obs_inicial)
        registrar_observacion_oferta(obs_inicial)

        # Asignamos 'obs_multiple' con {'variante_id': 777, 'perfume_id': 888, 't...
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
        # Asignamos 'res' con registrar_observacion_oferta(obs_multiple)
        res = registrar_observacion_oferta(obs_multiple)
        # Aserción de prueba unitaria: self.assertEqual(res['resultado'], 'actualizada')
        self.assertEqual(res["resultado"], "actualizada")
        # Aserción de prueba unitaria: self.assertEqual(res['tipo_evento'], 'cambio_multiple')
        self.assertEqual(res["tipo_evento"], "cambio_multiple")
        # Aserción de prueba unitaria: self.assertIn('precio_actual', res['campos_modificad...
        self.assertIn("precio_actual", res["campos_modificados"])
        # Aserción de prueba unitaria: self.assertIn('en_stock', res['campos_modificados'])
        self.assertIn("en_stock", res["campos_modificados"])
        # Aserción de prueba unitaria: self.assertIn('url_producto', res['campos_modificado...
        self.assertIn("url_producto", res["campos_modificados"])

    # Definición de función 'test_06_fallo_de_scraping_no_altera_datos_confirmados' sin parámetros externos
    def test_06_fallo_de_scraping_no_altera_datos_confirmados(self):
        """Verifica que registrar_fallo_scraping incrementa fallos_consecutivos pero NO altera precio, stock ni URL."""
        # Asignamos 'obs_inicial' con {'variante_id': 777, 'perfume_id': 888, 't...
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
        # Ejecutamos instrucción: registrar_observacion_oferta(obs_inicial)
        registrar_observacion_oferta(obs_inicial)

        # Simular fallo de scraping (timeout o HTTP 500)
        res_fallo = registrar_fallo_scraping(
            tienda_id=999,
            variante_id=777,
            mensaje="Timeout 504 Gateway Timeout tras 10s de espera"
        )
        # Aserción de prueba unitaria: self.assertEqual(res_fallo['resultado'], 'fallo_regi...
        self.assertEqual(res_fallo["resultado"], "fallo_registrado")
        # Aserción de prueba unitaria: self.assertEqual(res_fallo['fallos_consecutivos'], 1)
        self.assertEqual(res_fallo["fallos_consecutivos"], 1)
        # Aserción de prueba unitaria: self.assertEqual(res_fallo['precio_actual'], 45000)
        self.assertEqual(res_fallo["precio_actual"], 45000)
        # Aserción de prueba unitaria: self.assertTrue(res_fallo['en_stock'])
        self.assertTrue(res_fallo["en_stock"])

        # Verificar que la oferta viva mantiene intacto precio, stock y URL
        with get_db_cursor() as cursor:
            # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
            cursor.execute("SELECT * FROM ofertas_actuales WHERE variante_id = 777 AND tienda_id = 999;")
            # Asignamos 'oferta' con cursor.fetchone()
            oferta = cursor.fetchone()
            # Aserción de prueba unitaria: self.assertEqual(oferta['precio_actual'], 45000)
            self.assertEqual(oferta["precio_actual"], 45000)
            # Aserción de prueba unitaria: self.assertEqual(oferta['en_stock'], 1)
            self.assertEqual(oferta["en_stock"], 1)
            # Aserción de prueba unitaria: self.assertEqual(oferta['url_producto'], 'https://ww...
            self.assertEqual(oferta["url_producto"], "https://www.tiendamock.cl/productos/fragancia-test-100ml")
            # Aserción de prueba unitaria: self.assertEqual(oferta['fallos_consecutivos'], 1)
            self.assertEqual(oferta["fallos_consecutivos"], 1)
            # Aserción de prueba unitaria: self.assertIn('Timeout 504', oferta['ultimo_error'])
            self.assertIn("Timeout 504", oferta["ultimo_error"])

            # Historial no debe haber crecido por el fallo
            cursor.execute("SELECT COUNT(*) FROM precios_registro WHERE variante_id = 777;")
            # Asignamos 'count_hist' con cursor.fetchone()[0]
            count_hist = cursor.fetchone()[0]
            # Aserción de prueba unitaria: self.assertEqual(count_hist, 1)
            self.assertEqual(count_hist, 1)

    # Definición de función 'test_07_precio_invalido_lanza_excepcion_y_no_deja_cambios_parciales' sin parámetros externos
    def test_07_precio_invalido_lanza_excepcion_y_no_deja_cambios_parciales(self):
        """Verifica que observaciones con precio negativo o cero son rechazadas de inmediato."""
        # Asignamos 'obs_invalida' con {'variante_id': 777, 'perfume_id': 888, 't...
        obs_invalida = {
            "variante_id": 777,
            "perfume_id": 888,
            "tienda_id": 999,
            "precio_actual": -1000,
            "en_stock": True,
            "url_producto": "https://www.tiendamock.cl/p/1"
        }
        # Gestión automática de contexto y recursos para: self.assertRaises(ValueError)
        with self.assertRaises(ValueError):
            # Ejecutamos instrucción: registrar_observacion_oferta(obs_invalida)
            registrar_observacion_oferta(obs_invalida)

        # Base de datos debe estar vacía para esa variante
        with get_db_cursor() as cursor:
            # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
            cursor.execute("SELECT COUNT(*) FROM ofertas_actuales WHERE variante_id = 777;")
            # Aserción de prueba unitaria: self.assertEqual(cursor.fetchone()[0], 0)
            self.assertEqual(cursor.fetchone()[0], 0)

    # Definición de función 'test_08_stock_desconocido_es_rechazado' sin parámetros externos
    def test_08_stock_desconocido_es_rechazado(self):
        """Verifica que el stock no puede ser None (debe ser explícito True o False)."""
        # Asignamos 'obs_stock_null' con {'variante_id': 777, 'perfume_id': 888, 't...
        obs_stock_null = {
            "variante_id": 777,
            "perfume_id": 888,
            "tienda_id": 999,
            "precio_actual": 45000,
            "en_stock": None,
            "url_producto": "https://www.tiendamock.cl/p/1"
        }
        # Gestión automática de contexto y recursos para: self.assertRaises(ValueError)
        with self.assertRaises(ValueError):
            # Ejecutamos instrucción: registrar_observacion_oferta(obs_stock_null)
            registrar_observacion_oferta(obs_stock_null)

    # Definición de función 'test_09_url_invalida_es_rechazada' sin parámetros externos
    def test_09_url_invalida_es_rechazada(self):
        """Verifica que se exija una URL válida que comience con http:// o https://."""
        # Asignamos 'obs_url_mala' con {'variante_id': 777, 'perfume_id': 888, 't...
        obs_url_mala = {
            "variante_id": 777,
            "perfume_id": 888,
            "tienda_id": 999,
            "precio_actual": 45000,
            "en_stock": True,
            "url_producto": "javascript:alert(1)"
        }
        # Gestión automática de contexto y recursos para: self.assertRaises(ValueError)
        with self.assertRaises(ValueError):
            # Ejecutamos instrucción: registrar_observacion_oferta(obs_url_mala)
            registrar_observacion_oferta(obs_url_mala)


# Punto de entrada principal cuando el script se invoca directamente desde consola
if __name__ == "__main__":
    # Ejecutamos instrucción: unittest.main()
    unittest.main()
