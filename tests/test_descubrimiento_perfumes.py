"""
tests/test_descubrimiento_perfumes.py
=====================================
Suite de pruebas unitarias para el Motor de Auto-Descubrimiento Autónomo de Catálogo:
1. Filtro estricto de control de calidad (descarta cremas, clones, testers y decants < 25ml).
2. Normalización canónica de marcas y saneamiento de títulos en nuevos descubrimientos.
3. Ingesta y deduplicación en base de datos mediante `guardar_o_actualizar_perfume_scraped`.
4. Generación y lectura de informes JSON de auditoría ('ultimo_descubrimiento.json').
5. Ejecución del pipeline en memoria RAM mediante `descubrir_nuevos_perfumes_desde_bulk`.
"""

# Importación de librería estándar o dependencia externa (json)
import json
# Importación de librería estándar o dependencia externa (os)
import os
# Importación de librería estándar o dependencia externa (shutil)
import shutil
# Importación de librería estándar o dependencia externa (sys)
import sys
# Importación de librería estándar o dependencia externa (tempfile)
import tempfile
# Importación de librería estándar o dependencia externa (unittest)
import unittest

# Asignamos 'BASE_DIR' con os.path.dirname(os.path.dirname(os.path.ab...
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Evaluamos la condición lógica (BASE_DIR not in sys.path) para controlar el flujo
if BASE_DIR not in sys.path:
    # Ejecutamos instrucción: sys.path.insert(0, BASE_DIR)
    sys.path.insert(0, BASE_DIR)
# Asignamos 'APP_DIR' con os.path.join(BASE_DIR, 'APP')
APP_DIR = os.path.join(BASE_DIR, "APP")
# Evaluamos la condición lógica (APP_DIR not in sys.path) para controlar el flujo
if APP_DIR not in sys.path:
    # Ejecutamos instrucción: sys.path.insert(0, APP_DIR)
    sys.path.insert(0, APP_DIR)

# Importación de componentes (get_db_cursor, guardar_o_actualizar_perfume_scraped, init_db) desde el módulo 'backend.database'
from backend.database import (
    get_db_cursor,
    guardar_o_actualizar_perfume_scraped,
    init_db,
)
# Importación de componentes (es_producto_perfume_valido, extraer_concentracion, extraer_volumen_ml, limpiar_nombre_perfume, ...) desde el módulo 'backend.normalizador'
from backend.normalizador import (
    es_producto_perfume_valido,
    extraer_concentracion,
    extraer_volumen_ml,
    limpiar_nombre_perfume,
    normalizar_marca_canonica,
)
# Importación de componentes (clean_digits, descubrir_nuevos_perfumes_desde_bulk, guardar_reporte_descubrimiento, obtener_ultimo_reporte_descubrimiento) desde el módulo 'backend.scraper_autonomo'
from backend.scraper_autonomo import (
    clean_digits,
    descubrir_nuevos_perfumes_desde_bulk,
    guardar_reporte_descubrimiento,
    obtener_ultimo_reporte_descubrimiento,
)


# Definición de clase 'MockCatalogoTienda' que modela la estructura y lógica del componente
class MockCatalogoTienda:
    """Clase Mock ligera que emula CatalogoTiendaBulk para pruebas en memoria."""
    # Definición de función '__init__' (parámetros: nombre_tienda, items)
    def __init__(self, nombre_tienda: str, items: list):
        # Asignamos 'self.nombre_tienda' con nombre_tienda
        self.nombre_tienda = nombre_tienda
        # Asignamos 'self.todos_items' con items
        self.todos_items = items


# Definición de clase 'TestDescubrimientoPerfumes' que modela la estructura y lógica del componente
class TestDescubrimientoPerfumes(unittest.TestCase):
    # Definición de función 'setUp' sin parámetros externos
    def setUp(self):
        # Desactivar Supabase antes de init_db para garantizar aislamiento 100% sobre SQLite local en pruebas
        self._old_env_disable = os.environ.get("SUPABASE_DISABLE")
        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
        os.environ["SUPABASE_DISABLE"] = "true"
        # Ejecutamos instrucción: init_db()
        init_db()
        # Asignamos 'self.temp_dir' con tempfile.mkdtemp()
        self.temp_dir = tempfile.mkdtemp()
        # Asignamos 'self.reporte_temp' con os.path.join(self.temp_dir, 'test_descubri...
        self.reporte_temp = os.path.join(self.temp_dir, "test_descubrimiento.json")
        # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
        self._limpiar_sqlite_test_rows()

    # Definición de función 'tearDown' sin parámetros externos
    def tearDown(self):
        # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
        self._limpiar_sqlite_test_rows()
        # Evaluamos la condición lógica (self._old_env_disable is not None) para controlar el flujo
        if self._old_env_disable is not None:
            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            os.environ["SUPABASE_DISABLE"] = self._old_env_disable
        else:
            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            os.environ.pop("SUPABASE_DISABLE", None)
        # Evaluamos la condición lógica (os.path.exists(self.temp_dir)) para controlar el flujo
        if os.path.exists(self.temp_dir):
            # Ejecutamos instrucción: shutil.rmtree(self.temp_dir, ignore_errors=True)
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    # Definición de función '_limpiar_sqlite_test_rows' sin parámetros externos
    def _limpiar_sqlite_test_rows(self):
        # Bloque try/except para manejo seguro de errores y resiliencia operativa
        try:
            # Gestión automática de contexto y recursos para: get_db_cursor(commit=True)
            with get_db_cursor(commit=True) as cur:
                # Ejecutamos instrucción: cur.execute("SELECT id FROM perfumes WHERE nombre LI...
                cur.execute("SELECT id FROM perfumes WHERE nombre LIKE '%Test Unitaria%' OR nombre LIKE '%Inedita Novedad%' OR nombre LIKE '%Test Debug%';")
                # Asignamos 'pids' con [r['id'] for r in cur.fetchall()]
                pids = [r["id"] for r in cur.fetchall()]
                # Recorremos iterativamente cada 'pid' en pids
                for pid in pids:
                    # Ejecutamos instrucción: cur.execute('DELETE FROM ofertas_actuales WHERE vari...
                    cur.execute("DELETE FROM ofertas_actuales WHERE variante_id IN (SELECT id FROM variantes_perfume WHERE perfume_id = ?);", (pid,))
                    # Ejecutamos instrucción: cur.execute('DELETE FROM precios_registro WHERE vari...
                    cur.execute("DELETE FROM precios_registro WHERE variante_id IN (SELECT id FROM variantes_perfume WHERE perfume_id = ?);", (pid,))
                    # Ejecutamos instrucción: cur.execute('DELETE FROM variantes_perfume WHERE per...
                    cur.execute("DELETE FROM variantes_perfume WHERE perfume_id = ?;", (pid,))
                    # Ejecutamos instrucción: cur.execute('DELETE FROM perfumes WHERE id = ?;', (p...
                    cur.execute("DELETE FROM perfumes WHERE id = ?;", (pid,))
        except Exception:
            # Ejecutamos instrucción: pass
            pass

    # Definición de función 'test_clean_digits' sin parámetros externos
    def test_clean_digits(self):
        """Verifica que clean_digits extraiga solo números enteros sin fallar ante caracteres o None."""
        # Aserción de prueba unitaria: self.assertEqual(clean_digits('$59.990 CLP'), 59990)
        self.assertEqual(clean_digits("$59.990 CLP"), 59990)
        # Aserción de prueba unitaria: self.assertEqual(clean_digits('Desde 120.000'), 120000)
        self.assertEqual(clean_digits("Desde 120.000"), 120000)
        # Aserción de prueba unitaria: self.assertEqual(clean_digits(None), 0)
        self.assertEqual(clean_digits(None), 0)
        # Aserción de prueba unitaria: self.assertEqual(clean_digits('Agotado'), 0)
        self.assertEqual(clean_digits("Agotado"), 0)

    # Definición de función 'test_filtro_calidad_descarta_no_perfumes_y_clones' sin parámetros externos
    def test_filtro_calidad_descarta_no_perfumes_y_clones(self):
        """Verifica que cosméticos, clones y presentaciones menores a 25ml sean rechazados."""
        # Cosméticos / accesorios
        self.assertFalse(es_producto_perfume_valido("Crema Corporal Hidratante 200ml", marca="Chanel"))
        # Aserción de prueba unitaria: self.assertFalse(es_producto_perfume_valido('Shampoo...
        self.assertFalse(es_producto_perfume_valido("Shampoo Reparador 250ml", marca="Dior"))
        # Aserción de prueba unitaria: self.assertFalse(es_producto_perfume_valido('Desodor...
        self.assertFalse(es_producto_perfume_valido("Desodorante Antitranspirante Roll-On", marca="Versace"))
        # Aserción de prueba unitaria: self.assertFalse(es_producto_perfume_valido('Reloj C...
        self.assertFalse(es_producto_perfume_valido("Reloj Cronógrafo Deportivo", marca="Hugo Boss"))

        # Decants y muestras diminutas (< 25ml)
        self.assertFalse(es_producto_perfume_valido("Decant Muestra Vial 5ml Sauvage", marca="Dior", volumen_min_ml=25))
        # Aserción de prueba unitaria: self.assertFalse(es_producto_perfume_valido('Muestra...
        self.assertFalse(es_producto_perfume_valido("Muestra 10ml Eros Flame", marca="Versace", volumen_min_ml=25))

        # Fragancias legítimas (>= 25ml)
        self.assertTrue(es_producto_perfume_valido("Sauvage Eau de Toilette 100ml", marca="Dior", volumen_min_ml=25))
        # Aserción de prueba unitaria: self.assertTrue(es_producto_perfume_valido('Club de ...
        self.assertTrue(es_producto_perfume_valido("Club de Nuit Intense Man 105ml", marca="Armaf", volumen_min_ml=25))
        # Aserción de prueba unitaria: self.assertTrue(es_producto_perfume_valido('Khamrah ...
        self.assertTrue(es_producto_perfume_valido("Khamrah Eau de Parfum 100ml", marca="Lattafa", volumen_min_ml=25))

    # Definición de función 'test_normalizacion_de_marca_y_limpieza_de_nombre' sin parámetros externos
    def test_normalizacion_de_marca_y_limpieza_de_nombre(self):
        """Verifica que nuevos perfumes tengan marcas canónicas y nombres limpios sin ruido comercial."""
        # Asignamos 'marca_raw' con 'lattafa perfumes'
        marca_raw = "lattafa perfumes"
        # Asignamos 'nombre_raw' con 'Lattafa Khamrah Eau de Parfum 100ml Origi...
        nombre_raw = "Lattafa Khamrah Eau de Parfum 100ml Original Oferta"

        # Asignamos 'marca_canon' con normalizar_marca_canonica(marca_raw)
        marca_canon = normalizar_marca_canonica(marca_raw)
        # Aserción de prueba unitaria: self.assertEqual(marca_canon, 'Lattafa')
        self.assertEqual(marca_canon, "Lattafa")

        # Asignamos 'nombre_limpio' con limpiar_nombre_perfume(nombre_raw, marca_c...
        nombre_limpio = limpiar_nombre_perfume(nombre_raw, marca_canon)
        # Aserción de prueba unitaria: self.assertEqual(nombre_limpio, 'Khamrah')
        self.assertEqual(nombre_limpio, "Khamrah")
        # Aserción de prueba unitaria: self.assertEqual(extraer_volumen_ml(nombre_raw), 100)
        self.assertEqual(extraer_volumen_ml(nombre_raw), 100)
        # Aserción de prueba unitaria: self.assertEqual(extraer_concentracion(nombre_raw), ...
        self.assertEqual(extraer_concentracion(nombre_raw), "Eau de Parfum")

    # Definición de función 'test_guardar_o_actualizar_perfume_scraped_en_db' sin parámetros externos
    def test_guardar_o_actualizar_perfume_scraped_en_db(self):
        """Verifica la inserción de un nuevo perfume en SQLite y que no se duplique al reintentar."""
        # Asignamos 'nombre_test' con 'Fragancia Test Unitaria 2026'
        nombre_test = "Fragancia Test Unitaria 2026"
        # Asignamos 'marca_test' con 'Versace'
        marca_test = "Versace"
        # Asignamos 'tienda_test' con 'Silk Perfumes'
        tienda_test = "Silk Perfumes"
        # Asignamos 'url_test' con 'https://www.silkperfumes.cl/products/frag...
        url_test = "https://www.silkperfumes.cl/products/fragancia-test-2026"

        # 1. Primera inserción: debe ser nuevo
        res1 = guardar_o_actualizar_perfume_scraped(
            nombre=nombre_test,
            marca=marca_test,
            precio_actual=49990,
            precio_normal=69990,
            tienda_nombre=tienda_test,
            url_producto=url_test,
            volumen_ml=100,
            tipo="Eau de Parfum",
            genero="Unisex",
            en_stock=True,
        )
        # Aserción de prueba unitaria: self.assertTrue(res1.get('exito'))
        self.assertTrue(res1.get("exito"))
        # Aserción de prueba unitaria: self.assertTrue(res1.get('es_nuevo'))
        self.assertTrue(res1.get("es_nuevo"))
        # Asignamos 'perfume_id' con res1.get('perfume_id')
        perfume_id = res1.get("perfume_id")
        # Aserción de prueba unitaria: self.assertIsNotNone(perfume_id)
        self.assertIsNotNone(perfume_id)

        # 2. Segunda inserción con la misma identidad: deduplica, es_nuevo = False
        res2 = guardar_o_actualizar_perfume_scraped(
            nombre=nombre_test,
            marca=marca_test,
            precio_actual=47990,
            precio_normal=69990,
            tienda_nombre=tienda_test,
            url_producto=url_test,
            volumen_ml=100,
            tipo="Eau de Parfum",
            genero="Unisex",
            en_stock=True,
        )
        # Aserción de prueba unitaria: self.assertTrue(res2.get('exito'))
        self.assertTrue(res2.get("exito"))
        # Aserción de prueba unitaria: self.assertFalse(res2.get('es_nuevo'))
        self.assertFalse(res2.get("es_nuevo"))
        # Aserción de prueba unitaria: self.assertEqual(res2.get('perfume_id'), perfume_id)
        self.assertEqual(res2.get("perfume_id"), perfume_id)

    # Definición de función 'test_guardar_o_actualizar_rechaza_precios_o_volumenes_invalidos' sin parámetros externos
    def test_guardar_o_actualizar_rechaza_precios_o_volumenes_invalidos(self):
        """Verifica que precios fuera de rango comercial o volúmenes < 25ml sean rechazados."""
        # Precio sospechoso o placeholder
        res_p_basso = guardar_o_actualizar_perfume_scraped(
            nombre="Perfume Sospechoso", marca="Dior", precio_actual=500, precio_normal=1000,
            tienda_nombre="Tienda X", url_producto="https://tienda.cl/p"
        )
        # Aserción de prueba unitaria: self.assertFalse(res_p_basso.get('exito'))
        self.assertFalse(res_p_basso.get("exito"))

        # Volumen descartado (< 25ml)
        res_vol_bajo = guardar_o_actualizar_perfume_scraped(
            nombre="Decant 10ml", marca="Dior", precio_actual=15000, precio_normal=20000,
            volumen_ml=10, tienda_nombre="Tienda X", url_producto="https://tienda.cl/p"
        )
        # Aserción de prueba unitaria: self.assertFalse(res_vol_bajo.get('exito'))
        self.assertFalse(res_vol_bajo.get("exito"))

    # Definición de función 'test_guardar_y_obtener_reporte_descubrimiento' sin parámetros externos
    def test_guardar_y_obtener_reporte_descubrimiento(self):
        """Verifica que el informe JSON se genere, serialice y lea con integridad."""
        # Asignamos 'reporte_mock' con {'metadata': {'version': '3.3.0', 'sistema...
        reporte_mock = {
            "metadata": {
                "version": "3.3.0",
                "sistema": "Test Discovery Engine",
                "fecha_ejecucion": "2026-10-30 12:00:00",
                "duracion_segundos": 1.45,
                "estado": "EXITOSO",
            },
            "metricas": {
                "total_productos_analizados": 150,
                "descartados_no_perfume": 30,
                "nuevos_perfumes_descubiertos": 12,
                "precios_variantes_registrados": 18,
                "errores_totales": 0,
            },
            "muestras_nuevas": [
                {"nombre": "Yara Candy", "marca": "Lattafa", "precio": 32990}
            ],
            "errores": [],
        }

        # Asignamos 'path_guardado' con guardar_reporte_descubrimiento(reporte_moc...
        path_guardado = guardar_reporte_descubrimiento(reporte_mock, ruta_destino=self.reporte_temp)
        # Aserción de prueba unitaria: self.assertTrue(os.path.exists(path_guardado))
        self.assertTrue(os.path.exists(path_guardado))

        # Asignamos 'reporte_leido' con obtener_ultimo_reporte_descubrimiento(ruta...
        reporte_leido = obtener_ultimo_reporte_descubrimiento(ruta_destino=self.reporte_temp)
        # Aserción de prueba unitaria: self.assertIsNotNone(reporte_leido)
        self.assertIsNotNone(reporte_leido)
        # Aserción de prueba unitaria: self.assertEqual(reporte_leido['metricas']['nuevos_p...
        self.assertEqual(reporte_leido["metricas"]["nuevos_perfumes_descubiertos"], 12)
        # Aserción de prueba unitaria: self.assertEqual(reporte_leido['metricas']['descarta...
        self.assertEqual(reporte_leido["metricas"]["descartados_no_perfume"], 30)
        # Aserción de prueba unitaria: self.assertEqual(len(reporte_leido['muestras_nuevas'...
        self.assertEqual(len(reporte_leido["muestras_nuevas"]), 1)

    # Definición de función 'test_descubrir_nuevos_perfumes_desde_bulk' sin parámetros externos
    def test_descubrir_nuevos_perfumes_desde_bulk(self):
        """Verifica el flujo completo de descubrimiento en memoria RAM sobre catálogo bulk emulado."""
        # Asignamos 'items_mock' con [{'title': 'Fragancia Inedita Novedad 2026...
        items_mock = [
            # 1. Producto válido legítimo (Nueva fragancia de prueba)
            {
                "title": "Fragancia Inedita Novedad 2026 Eau de Parfum 100ml",
                "vendor": "Lattafa",
                "marca": "Lattafa",
                "url": "https://www.silkperfumes.cl/products/fragancia-inedita-2026",
                "formato": "regular",
                "variants": [{"price": 34990, "compare_at_price": 45990, "available": True, "title": "100ml"}],
            },
            # 2. Cosmético no perfume (debe descartarse)
            {
                "title": "Bálsamo After Shave Hidratante 100ml",
                "vendor": "Lattafa",
                "marca": "Lattafa",
                "url": "https://www.silkperfumes.cl/products/after-shave-lattafa",
                "formato": "regular",
                "variants": [{"price": 12990, "available": True, "title": "100ml"}],
            },
            # 3. Clon / imitación no auténtica (debe descartarse)
            {
                "title": "Inspirado en Baccarat Rouge 540 100ml",
                "vendor": "Loris",
                "marca": "",
                "url": "https://www.silkperfumes.cl/products/inspiracion-540",
                "formato": "regular",
                "variants": [{"price": 9990, "available": True, "title": "100ml"}],
            },
            # 4. Decant < 25ml (debe descartarse)
            {
                "title": "Muestra Decant Fragancia Inedita 5ml",
                "vendor": "Lattafa",
                "marca": "Lattafa",
                "url": "https://www.silkperfumes.cl/products/decant-5ml",
                "formato": "regular",
                "variants": [{"price": 4990, "available": True, "title": "5ml"}],
            },
        ]

        # Asignamos 'cat_mock' con MockCatalogoTienda('Silk Perfumes', items_...
        cat_mock = MockCatalogoTienda("Silk Perfumes", items_mock)
        # Asignamos 'cache_bulk' con {'silk_perfumes': cat_mock}
        cache_bulk = {"silk_perfumes": cat_mock}

        # Asignamos 'rep' con descubrir_nuevos_perfumes_desde_bulk(cache...
        rep = descubrir_nuevos_perfumes_desde_bulk(
            cache_tiendas_bulk=cache_bulk,
            limite_nuevos_por_tienda=10,
            reporte_path=self.reporte_temp,
        )

        # Asignamos 'm' con rep['metricas']
        m = rep["metricas"]
        # Aserción de prueba unitaria: self.assertEqual(m['total_productos_analizados'], 4)
        self.assertEqual(m["total_productos_analizados"], 4)
        # Aserción de prueba unitaria: self.assertEqual(m['descartados_no_perfume'], 3)
        self.assertEqual(m["descartados_no_perfume"], 3)  # Aftershave, Clon Loris, Decant 5ml
        # Aserción de prueba unitaria: self.assertEqual(m['nuevos_perfumes_descubiertos'], 1)
        self.assertEqual(m["nuevos_perfumes_descubiertos"], 1)  # Fragancia Inedita Novedad 2026
        # Aserción de prueba unitaria: self.assertEqual(len(rep['muestras_nuevas']), 1)
        self.assertEqual(len(rep["muestras_nuevas"]), 1)
        # Aserción de prueba unitaria: self.assertIn('Novedad 2026', rep['muestras_nuevas']...
        self.assertIn("Novedad 2026", rep["muestras_nuevas"][0]["nombre"])
        # Aserción de prueba unitaria: self.assertEqual(rep['muestras_nuevas'][0]['marca'],...
        self.assertEqual(rep["muestras_nuevas"][0]["marca"], "Lattafa")


# Punto de entrada principal cuando el script se invoca directamente desde consola
if __name__ == "__main__":
    # Ejecutamos instrucción: unittest.main()
    unittest.main()
