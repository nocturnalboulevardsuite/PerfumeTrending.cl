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

import json
import os
import shutil
import sys
import tempfile
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
APP_DIR = os.path.join(BASE_DIR, "APP")
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from backend.database import (
    get_db_cursor,
    guardar_o_actualizar_perfume_scraped,
    init_db,
)
from backend.normalizador import (
    es_producto_perfume_valido,
    extraer_concentracion,
    extraer_volumen_ml,
    limpiar_nombre_perfume,
    normalizar_marca_canonica,
)
from backend.scraper_autonomo import (
    clean_digits,
    descubrir_nuevos_perfumes_desde_bulk,
    guardar_reporte_descubrimiento,
    obtener_ultimo_reporte_descubrimiento,
)


class MockCatalogoTienda:
    """Clase Mock ligera que emula CatalogoTiendaBulk para pruebas en memoria."""
    def __init__(self, nombre_tienda: str, items: list):
        self.nombre_tienda = nombre_tienda
        self.todos_items = items


class TestDescubrimientoPerfumes(unittest.TestCase):
    def setUp(self):
        # Desactivar Supabase antes de init_db para garantizar aislamiento 100% sobre SQLite local en pruebas
        self._old_env_disable = os.environ.get("SUPABASE_DISABLE")
        os.environ["SUPABASE_DISABLE"] = "true"
        init_db()
        self.temp_dir = tempfile.mkdtemp()
        self.reporte_temp = os.path.join(self.temp_dir, "test_descubrimiento.json")
        self._limpiar_sqlite_test_rows()

    def tearDown(self):
        self._limpiar_sqlite_test_rows()
        if self._old_env_disable is not None:
            os.environ["SUPABASE_DISABLE"] = self._old_env_disable
        else:
            os.environ.pop("SUPABASE_DISABLE", None)
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _limpiar_sqlite_test_rows(self):
        try:
            with get_db_cursor(commit=True) as cur:
                cur.execute("SELECT id FROM perfumes WHERE nombre LIKE '%Test Unitaria%' OR nombre LIKE '%Inedita Novedad%' OR nombre LIKE '%Test Debug%';")
                pids = [r["id"] for r in cur.fetchall()]
                for pid in pids:
                    cur.execute("DELETE FROM ofertas_actuales WHERE variante_id IN (SELECT id FROM variantes_perfume WHERE perfume_id = ?);", (pid,))
                    cur.execute("DELETE FROM precios_registro WHERE variante_id IN (SELECT id FROM variantes_perfume WHERE perfume_id = ?);", (pid,))
                    cur.execute("DELETE FROM variantes_perfume WHERE perfume_id = ?;", (pid,))
                    cur.execute("DELETE FROM perfumes WHERE id = ?;", (pid,))
        except Exception:
            pass

    def test_clean_digits(self):
        """Verifica que clean_digits extraiga solo números enteros sin fallar ante caracteres o None."""
        self.assertEqual(clean_digits("$59.990 CLP"), 59990)
        self.assertEqual(clean_digits("Desde 120.000"), 120000)
        self.assertEqual(clean_digits(None), 0)
        self.assertEqual(clean_digits("Agotado"), 0)

    def test_filtro_calidad_descarta_no_perfumes_y_clones(self):
        """Verifica que cosméticos, clones y presentaciones menores a 25ml sean rechazados."""
        # Cosméticos / accesorios
        self.assertFalse(es_producto_perfume_valido("Crema Corporal Hidratante 200ml", marca="Chanel"))
        self.assertFalse(es_producto_perfume_valido("Shampoo Reparador 250ml", marca="Dior"))
        self.assertFalse(es_producto_perfume_valido("Desodorante Antitranspirante Roll-On", marca="Versace"))
        self.assertFalse(es_producto_perfume_valido("Reloj Cronógrafo Deportivo", marca="Hugo Boss"))

        # Decants y muestras diminutas (< 25ml)
        self.assertFalse(es_producto_perfume_valido("Decant Muestra Vial 5ml Sauvage", marca="Dior", volumen_min_ml=25))
        self.assertFalse(es_producto_perfume_valido("Muestra 10ml Eros Flame", marca="Versace", volumen_min_ml=25))

        # Fragancias legítimas (>= 25ml)
        self.assertTrue(es_producto_perfume_valido("Sauvage Eau de Toilette 100ml", marca="Dior", volumen_min_ml=25))
        self.assertTrue(es_producto_perfume_valido("Club de Nuit Intense Man 105ml", marca="Armaf", volumen_min_ml=25))
        self.assertTrue(es_producto_perfume_valido("Khamrah Eau de Parfum 100ml", marca="Lattafa", volumen_min_ml=25))

    def test_normalizacion_de_marca_y_limpieza_de_nombre(self):
        """Verifica que nuevos perfumes tengan marcas canónicas y nombres limpios sin ruido comercial."""
        marca_raw = "lattafa perfumes"
        nombre_raw = "Lattafa Khamrah Eau de Parfum 100ml Original Oferta"

        marca_canon = normalizar_marca_canonica(marca_raw)
        self.assertEqual(marca_canon, "Lattafa")

        nombre_limpio = limpiar_nombre_perfume(nombre_raw, marca_canon)
        self.assertEqual(nombre_limpio, "Khamrah")
        self.assertEqual(extraer_volumen_ml(nombre_raw), 100)
        self.assertEqual(extraer_concentracion(nombre_raw), "Eau de Parfum")

    def test_guardar_o_actualizar_perfume_scraped_en_db(self):
        """Verifica la inserción de un nuevo perfume en SQLite y que no se duplique al reintentar."""
        nombre_test = "Fragancia Test Unitaria 2026"
        marca_test = "Versace"
        tienda_test = "Silk Perfumes"
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
        self.assertTrue(res1.get("exito"))
        self.assertTrue(res1.get("es_nuevo"))
        perfume_id = res1.get("perfume_id")
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
        self.assertTrue(res2.get("exito"))
        self.assertFalse(res2.get("es_nuevo"))
        self.assertEqual(res2.get("perfume_id"), perfume_id)

    def test_guardar_o_actualizar_rechaza_precios_o_volumenes_invalidos(self):
        """Verifica que precios fuera de rango comercial o volúmenes < 25ml sean rechazados."""
        # Precio sospechoso o placeholder
        res_p_basso = guardar_o_actualizar_perfume_scraped(
            nombre="Perfume Sospechoso", marca="Dior", precio_actual=500, precio_normal=1000,
            tienda_nombre="Tienda X", url_producto="https://tienda.cl/p"
        )
        self.assertFalse(res_p_basso.get("exito"))

        # Volumen descartado (< 25ml)
        res_vol_bajo = guardar_o_actualizar_perfume_scraped(
            nombre="Decant 10ml", marca="Dior", precio_actual=15000, precio_normal=20000,
            volumen_ml=10, tienda_nombre="Tienda X", url_producto="https://tienda.cl/p"
        )
        self.assertFalse(res_vol_bajo.get("exito"))

    def test_guardar_y_obtener_reporte_descubrimiento(self):
        """Verifica que el informe JSON se genere, serialice y lea con integridad."""
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

        path_guardado = guardar_reporte_descubrimiento(reporte_mock, ruta_destino=self.reporte_temp)
        self.assertTrue(os.path.exists(path_guardado))

        reporte_leido = obtener_ultimo_reporte_descubrimiento(ruta_destino=self.reporte_temp)
        self.assertIsNotNone(reporte_leido)
        self.assertEqual(reporte_leido["metricas"]["nuevos_perfumes_descubiertos"], 12)
        self.assertEqual(reporte_leido["metricas"]["descartados_no_perfume"], 30)
        self.assertEqual(len(reporte_leido["muestras_nuevas"]), 1)

    def test_descubrir_nuevos_perfumes_desde_bulk(self):
        """Verifica el flujo completo de descubrimiento en memoria RAM sobre catálogo bulk emulado."""
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

        cat_mock = MockCatalogoTienda("Silk Perfumes", items_mock)
        cache_bulk = {"silk_perfumes": cat_mock}

        rep = descubrir_nuevos_perfumes_desde_bulk(
            cache_tiendas_bulk=cache_bulk,
            limite_nuevos_por_tienda=10,
            reporte_path=self.reporte_temp,
        )

        m = rep["metricas"]
        self.assertEqual(m["total_productos_analizados"], 4)
        self.assertEqual(m["descartados_no_perfume"], 3)  # Aftershave, Clon Loris, Decant 5ml
        self.assertEqual(m["nuevos_perfumes_descubiertos"], 1)  # Fragancia Inedita Novedad 2026
        self.assertEqual(len(rep["muestras_nuevas"]), 1)
        self.assertIn("Novedad 2026", rep["muestras_nuevas"][0]["nombre"])
        self.assertEqual(rep["muestras_nuevas"][0]["marca"], "Lattafa")


if __name__ == "__main__":
    unittest.main()
