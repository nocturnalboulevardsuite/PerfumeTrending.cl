# -*- coding: utf-8 -*-
"""
Pruebas unitarias aisladas para la Política de Frescura de Ofertas (Fase 1):
- Umbrales configurables 3 / 7 / 14 días (`DIAS_OFERTA_FRESCA`, `DIAS_OFERTA_ADVERTENCIA`, `DIAS_OFERTA_OCULTAR`).
- Exclusión de ofertas >7d sin verificar de `mejor_precio` ("Desde $X") y `obtener_remates_reales`.
- Ocultamiento de ofertas en stock >14d sin verificar en `obtener_precios_actuales`.
- Retiro automático a `estado='agotada'` (`en_stock=False`) tras 5 `no_encontrado_en_feed`,
  e inmunidad ante fallos transitorios (`waf`, `timeout`, `parse_error`).
"""

# Importación de librería estándar o dependencia externa (os)
import os
# Importación de librería estándar o dependencia externa (shutil)
import shutil
# Importación de librería estándar o dependencia externa (tempfile)
import tempfile
# Importación de librería estándar o dependencia externa (unittest)
import unittest
# Importación de componentes (datetime, timedelta, timezone) desde el módulo 'datetime'
from datetime import datetime, timedelta, timezone

# Importación de librería estándar o dependencia externa (APP.backend.database)
import APP.backend.database as db_app

# Bloque try/except para manejo seguro de errores y resiliencia operativa
try:
    # Importación de librería estándar o dependencia externa (backend.database)
    import backend.database as db_short
except ImportError:
    # Asignamos 'db_short' con None
    db_short = None


# Definición de función '_patch_db_modules' (parámetros: db_path, db_dir)
def _patch_db_modules(db_path: str, db_dir: str):
    """Aísla ambos alias de módulo (`APP.backend.database` y `backend.database`) contra SQLite temporal."""
    # Asignamos 'originals' con []
    originals = []
    # Recorremos iterativamente cada 'mod' en (m for m in (db_app, db_short) if m is not...
    for mod in (m for m in (db_app, db_short) if m is not None):
        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
        originals.append((
            mod,
            mod.DB_PATH,
            mod.DB_DIR,
            mod.is_supabase_disponible,
            mod.get_supabase,
            mod.DIAS_OFERTA_FRESCA,
            mod.DIAS_OFERTA_ADVERTENCIA,
            mod.DIAS_OFERTA_OCULTAR,
        ))
        # Asignamos 'mod.DB_PATH' con db_path
        mod.DB_PATH = db_path
        # Asignamos 'mod.DB_DIR' con db_dir
        mod.DB_DIR = db_dir
        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
        mod.is_supabase_disponible = lambda: False
        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
        mod.get_supabase = lambda *a, **kw: None
        # Asignamos 'mod.DIAS_OFERTA_FRESCA' con 3.0
        mod.DIAS_OFERTA_FRESCA = 3.0
        # Asignamos 'mod.DIAS_OFERTA_ADVERTENCIA' con 7.0
        mod.DIAS_OFERTA_ADVERTENCIA = 7.0
        # Asignamos 'mod.DIAS_OFERTA_OCULTAR' con 14.0
        mod.DIAS_OFERTA_OCULTAR = 14.0
        # Ejecutamos instrucción: mod.limpiar_cache_catalogo()
        mod.limpiar_cache_catalogo()
    # Retornamos el resultado procesado (originals)
    return originals


# Definición de función '_restore_db_modules' (parámetros: originals)
def _restore_db_modules(originals):
    # Recorremos iterativamente cada '(mod, db_path, db_dir, fn_d...' en originals
    for mod, db_path, db_dir, fn_disp, fn_sb, df, da, do in originals:
        # Asignamos 'mod.DB_PATH' con db_path
        mod.DB_PATH = db_path
        # Asignamos 'mod.DB_DIR' con db_dir
        mod.DB_DIR = db_dir
        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
        mod.is_supabase_disponible = fn_disp
        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
        mod.get_supabase = fn_sb
        # Asignamos 'mod.DIAS_OFERTA_FRESCA' con df
        mod.DIAS_OFERTA_FRESCA = df
        # Asignamos 'mod.DIAS_OFERTA_ADVERTENCIA' con da
        mod.DIAS_OFERTA_ADVERTENCIA = da
        # Asignamos 'mod.DIAS_OFERTA_OCULTAR' con do
        mod.DIAS_OFERTA_OCULTAR = do
        # Ejecutamos instrucción: mod.limpiar_cache_catalogo()
        mod.limpiar_cache_catalogo()


# Definición de clase 'TestFrescuraOferta' que modela la estructura y lógica del componente
class TestFrescuraOferta(unittest.TestCase):
    # Definición de función 'setUpClass' (parámetros: cls)
    @classmethod
    def setUpClass(cls):
        # Asignamos 'cls.tmp_dir' con tempfile.mkdtemp(prefix='pt_frescura_')
        cls.tmp_dir = tempfile.mkdtemp(prefix="pt_frescura_")
        # Asignamos 'cls.tmp_db' con os.path.join(cls.tmp_dir, 'frescura.db')
        cls.tmp_db = os.path.join(cls.tmp_dir, "frescura.db")
        # Asignamos 'cls._orig' con _patch_db_modules(cls.tmp_db, cls.tmp_dir)
        cls._orig = _patch_db_modules(cls.tmp_db, cls.tmp_dir)
        # Ejecutamos instrucción: db_app.init_db(force_reseed=False)
        db_app.init_db(force_reseed=False)

        # Gestión automática de contexto y recursos para: db_app.get_db_cursor(commit=True)
        with db_app.get_db_cursor(commit=True) as cur:
            # Recorremos iterativamente cada '(tid, tnom)' en [(1, 'Tienda Fresca'), (2, 'Tienda Recient...
            for tid, tnom in [(1, "Tienda Fresca"), (2, "Tienda Reciente"), (3, "Tienda Stale 10d"), (4, "Tienda Obsoleta 18d")]:
                # Ejecutamos instrucción: cur.execute('INSERT OR REPLACE INTO tiendas (id, nom...
                cur.execute(
                    "INSERT OR REPLACE INTO tiendas (id, nombre, url_base, trust_score) VALUES (?, ?, ?, 92);",
                    (tid, tnom, f"https://tienda{tid}.cl"),
                )
            # Ejecutamos instrucción: cur.execute("\n INSERT OR REPLACE INTO perfumes (id,...
            cur.execute(
                """
                INSERT OR REPLACE INTO perfumes (id, nombre, marca, genero, tipo, notas, imagen_url, precio_referencia)
                VALUES (501, 'Perfume Frescura Test', 'Maison Test', 'Hombre', 'Eau de Parfum', 'Bergamota', '', 120000);
                """
            )
            # Ejecutamos instrucción: cur.execute("\n INSERT OR REPLACE INTO variantes_per...
            cur.execute(
                """
                INSERT OR REPLACE INTO variantes_perfume (id, perfume_id, concentracion, volumen_ml, formato, slug, activa)
                VALUES (601, 501, 'Eau de Parfum', 100.0, 'regular', 'perfume-501-100ml', 1),
                       (602, 501, 'Eau de Parfum', 50.0, 'regular', 'perfume-501-50ml', 1);
                """
            )

    # Definición de función 'tearDownClass' (parámetros: cls)
    @classmethod
    def tearDownClass(cls):
        # Ejecutamos instrucción: _restore_db_modules(cls._orig)
        _restore_db_modules(cls._orig)
        # Ejecutamos instrucción: shutil.rmtree(cls.tmp_dir, ignore_errors=True)
        shutil.rmtree(cls.tmp_dir, ignore_errors=True)

    # Definición de función 'setUp' sin parámetros externos
    def setUp(self):
        # Gestión automática de contexto y recursos para: db_app.get_db_cursor(commit=True)
        with db_app.get_db_cursor(commit=True) as cur:
            # Ejecutamos instrucción: cur.execute('DELETE FROM ofertas_actuales;')
            cur.execute("DELETE FROM ofertas_actuales;")
            # Ejecutamos instrucción: cur.execute('DELETE FROM precios_registro;')
            cur.execute("DELETE FROM precios_registro;")
        # Ejecutamos instrucción: db_app.limpiar_cache_catalogo()
        db_app.limpiar_cache_catalogo()

    # Definición de función 'test_01_clasificacion_umbrales_3_7_14_dias' sin parámetros externos
    def test_01_clasificacion_umbrales_3_7_14_dias(self):
        # Asignamos 'now' con datetime(2026, 11, 4, 12, 0, 0, tzinfo=tim...
        now = datetime(2026, 11, 4, 12, 0, 0, tzinfo=timezone.utc)
        # Asignamos 'ts_1d' con (now - timedelta(days=1)).isoformat()
        ts_1d = (now - timedelta(days=1)).isoformat()
        # Asignamos 'ts_5d' con (now - timedelta(days=5)).strftime('%Y-%m-...
        ts_5d = (now - timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S")
        # Asignamos 'ts_10d' con (now - timedelta(days=10)).isoformat().rep...
        ts_10d = (now - timedelta(days=10)).isoformat().replace("+00:00", "Z")
        # Asignamos 'ts_16d' con (now - timedelta(days=16)).isoformat()
        ts_16d = (now - timedelta(days=16)).isoformat()

        # Asignamos 'd1' con db_app.calcular_dias_sin_verificar(ts_1d, ...
        d1 = db_app.calcular_dias_sin_verificar(ts_1d, now_utc=now)
        # Asignamos 'd5' con db_app.calcular_dias_sin_verificar(ts_5d, ...
        d5 = db_app.calcular_dias_sin_verificar(ts_5d, now_utc=now)
        # Asignamos 'd10' con db_app.calcular_dias_sin_verificar(ts_10d,...
        d10 = db_app.calcular_dias_sin_verificar(ts_10d, now_utc=now)
        # Asignamos 'd16' con db_app.calcular_dias_sin_verificar(ts_16d,...
        d16 = db_app.calcular_dias_sin_verificar(ts_16d, now_utc=now)

        # Aserción de prueba unitaria: self.assertEqual(db_app.clasificar_frescura_oferta(d...
        self.assertEqual(db_app.clasificar_frescura_oferta(d1), "fresca")
        # Aserción de prueba unitaria: self.assertEqual(db_app.clasificar_frescura_oferta(d...
        self.assertEqual(db_app.clasificar_frescura_oferta(d5), "reciente")
        # Aserción de prueba unitaria: self.assertEqual(db_app.clasificar_frescura_oferta(d...
        self.assertEqual(db_app.clasificar_frescura_oferta(d10), "desactualizada")
        # Aserción de prueba unitaria: self.assertEqual(db_app.clasificar_frescura_oferta(d...
        self.assertEqual(db_app.clasificar_frescura_oferta(d16), "obsoleta")

        # Aserción de prueba unitaria: self.assertTrue(db_app.es_oferta_elegible_mejor_prec...
        self.assertTrue(db_app.es_oferta_elegible_mejor_precio(d5))
        # Aserción de prueba unitaria: self.assertFalse(db_app.es_oferta_elegible_mejor_pre...
        self.assertFalse(db_app.es_oferta_elegible_mejor_precio(d10))
        # Aserción de prueba unitaria: self.assertTrue(db_app.es_oferta_visible(d10, en_sto...
        self.assertTrue(db_app.es_oferta_visible(d10, en_stock=True))
        # Aserción de prueba unitaria: self.assertFalse(db_app.es_oferta_visible(d16, en_st...
        self.assertFalse(db_app.es_oferta_visible(d16, en_stock=True))
        # Aserción de prueba unitaria: self.assertTrue(db_app.es_oferta_visible(d16, en_sto...
        self.assertTrue(db_app.es_oferta_visible(d16, en_stock=False))

    # Definición de función 'test_02_exclusion_mejor_precio_7d_y_ocultamiento_14d' sin parámetros externos
    def test_02_exclusion_mejor_precio_7d_y_ocultamiento_14d(self):
        # Asignamos 'now' con datetime.now(timezone.utc)
        now = datetime.now(timezone.utc)
        # Asignamos 'ts_1d' con (now - timedelta(days=1)).strftime('%Y-%m-...
        ts_1d = (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        # Asignamos 'ts_5d' con (now - timedelta(days=5)).strftime('%Y-%m-...
        ts_5d = (now - timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S")
        # Asignamos 'ts_10d' con (now - timedelta(days=10)).strftime('%Y-%m...
        ts_10d = (now - timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S")
        # Asignamos 'ts_18d' con (now - timedelta(days=18)).strftime('%Y-%m...
        ts_18d = (now - timedelta(days=18)).strftime("%Y-%m-%d %H:%M:%S")

        # Gestión automática de contexto y recursos para: db_app.get_db_cursor(commit=True)
        with db_app.get_db_cursor(commit=True) as cur:
            # Asignamos 'ofertas' con [(601, 1, 92000, 120000, 1, 'https://tiend...
            ofertas = [
                (601, 1, 92000, 120000, 1, "https://tienda1.cl/p", "activa", ts_1d),
                (601, 2, 85000, 120000, 1, "https://tienda2.cl/p", "activa", ts_5d),
                (601, 3, 60000, 120000, 1, "https://tienda3.cl/p", "activa", ts_10d),
                (601, 4, 40000, 120000, 1, "https://tienda4.cl/p", "activa", ts_18d),
            ]
            # Recorremos iterativamente cada '(vid, tid, pa, pn, st, url,...' en ofertas
            for vid, tid, pa, pn, st, url, est, ts in ofertas:
                # Ejecutamos instrucción: cur.execute('\n INSERT INTO ofertas_actuales (\n var...
                cur.execute(
                    """
                    INSERT INTO ofertas_actuales (
                        variante_id, tienda_id, precio_actual, precio_normal, en_stock,
                        url_producto, estado, ultima_verificacion_exitosa, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (vid, tid, pa, pn, st, url, est, ts, ts),
                )

        # Asignamos 'precios' con db_app.obtener_precios_actuales(501)
        precios = db_app.obtener_precios_actuales(501)
        # Asignamos 'tiendas_visibles' con {p['tienda_id']: p for p in precios}
        tiendas_visibles = {p["tienda_id"]: p for p in precios}

        # >14d (tienda 4) debe quedar oculta
        self.assertNotIn(4, tiendas_visibles)
        # 10d (tienda 3) sigue visible pero marcada desactualizada y excluida de mejor precio
        self.assertIn(3, tiendas_visibles)
        # Aserción de prueba unitaria: self.assertEqual(tiendas_visibles[3]['nivel_frescura...
        self.assertEqual(tiendas_visibles[3]["nivel_frescura"], "desactualizada")
        # Aserción de prueba unitaria: self.assertTrue(tiendas_visibles[3]['excluida_mejor_...
        self.assertTrue(tiendas_visibles[3]["excluida_mejor_precio"])
        # 5d (tienda 2) es reciente y sí compite
        self.assertEqual(tiendas_visibles[2]["nivel_frescura"], "reciente")
        # Aserción de prueba unitaria: self.assertFalse(tiendas_visibles[2]['excluida_mejor...
        self.assertFalse(tiendas_visibles[2]["excluida_mejor_precio"])

        # En el catálogo, "Desde $X" (mejor_precio) debe ser 85.000 (tienda 2, 5d), NUNCA 60.000 (10d) ni 40.000 (18d)
        cat = db_app.obtener_catalogo(busqueda="Frescura Test")
        # Aserción de prueba unitaria: self.assertEqual(len(cat), 1)
        self.assertEqual(len(cat), 1)
        # Aserción de prueba unitaria: self.assertEqual(cat[0]['mejor_precio'], 85000)
        self.assertEqual(cat[0]["mejor_precio"], 85000)

        # En remates reales, la oferta de 10d (50% dcto) queda excluida y entra la de 5d
        remates = db_app.obtener_remates_reales(limite=10, force_refresh=True)
        # Asignamos 'tiendas_remates' con [r['tienda'] for r in remates]
        tiendas_remates = [r["tienda"] for r in remates]
        # Aserción de prueba unitaria: self.assertNotIn('Tienda Stale 10d', tiendas_remates)
        self.assertNotIn("Tienda Stale 10d", tiendas_remates)
        # Aserción de prueba unitaria: self.assertNotIn('Tienda Obsoleta 18d', tiendas_rema...
        self.assertNotIn("Tienda Obsoleta 18d", tiendas_remates)
        # Aserción de prueba unitaria: self.assertIn('Tienda Reciente', tiendas_remates)
        self.assertIn("Tienda Reciente", tiendas_remates)

    # Definición de función 'test_03_retiro_5_ausencias_feed_vs_inmunidad_waf_timeout' sin parámetros externos
    def test_03_retiro_5_ausencias_feed_vs_inmunidad_waf_timeout(self):
        # Asignamos 'now_s' con datetime.now(timezone.utc).strftime('%Y-%m...
        now_s = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        # Gestión automática de contexto y recursos para: db_app.get_db_cursor(commit=True)
        with db_app.get_db_cursor(commit=True) as cur:
            # Oferta activa en variante secundaria (50ml = id 602)
            cur.execute(
                """
                INSERT INTO ofertas_actuales (
                    variante_id, tienda_id, precio_actual, precio_normal, en_stock,
                    url_producto, estado, ultima_verificacion_exitosa, fallos_consecutivos, updated_at
                ) VALUES (602, 1, 59990, 79990, 1, 'https://tienda1.cl/50ml', 'activa', ?, 0, ?);
                """,
                (now_s, now_s),
            )

        # 6 bloqueos WAF / timeouts NO deben incrementar fallos_consecutivos ni agotar la oferta
        for codigo in ("waf", "waf", "timeout", "parse_error", "waf", "timeout"):
            # Asignamos 'r_tr' con db_app.registrar_fallo_scraping(tienda_id=...
            r_tr = db_app.registrar_fallo_scraping(
                tienda_id=1,
                perfume_id=501,
                variante_id=602,
                mensaje="HTTP 403 Cloudflare Challenge",
                motivo_codigo=codigo,
            )
            # Aserción de prueba unitaria: self.assertEqual(r_tr['resultado'], 'fallo_transitor...
            self.assertEqual(r_tr["resultado"], "fallo_transitorio")
            # Aserción de prueba unitaria: self.assertEqual(r_tr['fallos_consecutivos'], 0)
            self.assertEqual(r_tr["fallos_consecutivos"], 0)
            # Aserción de prueba unitaria: self.assertTrue(r_tr['en_stock'])
            self.assertTrue(r_tr["en_stock"])

        # 4 ausencias reales en feed mantienen activa, la 5ta la retira a 'agotada' con en_stock=False
        for intento in range(1, 5):
            # Asignamos 'r_f' con db_app.registrar_fallo_scraping(tienda_id=...
            r_f = db_app.registrar_fallo_scraping(
                tienda_id=1,
                perfume_id=501,
                mensaje="Producto ausente en feed JSON",
                motivo_codigo="no_encontrado_en_feed",
            )
            # Aserción de prueba unitaria: self.assertEqual(r_f['fallos_consecutivos'], intento)
            self.assertEqual(r_f["fallos_consecutivos"], intento)
            # Aserción de prueba unitaria: self.assertEqual(r_f['estado'], 'activa')
            self.assertEqual(r_f["estado"], "activa")
            # Aserción de prueba unitaria: self.assertTrue(r_f['en_stock'])
            self.assertTrue(r_f["en_stock"])

        # Asignamos 'r_5' con db_app.registrar_fallo_scraping(tienda_id=...
        r_5 = db_app.registrar_fallo_scraping(
            tienda_id=1,
            perfume_id=501,
            mensaje="Producto ausente en feed JSON",
            motivo_codigo="no_encontrado_en_feed",
        )
        # Aserción de prueba unitaria: self.assertEqual(r_5['fallos_consecutivos'], 5)
        self.assertEqual(r_5["fallos_consecutivos"], 5)
        # Aserción de prueba unitaria: self.assertEqual(r_5['estado'], 'agotada')
        self.assertEqual(r_5["estado"], "agotada")
        # Aserción de prueba unitaria: self.assertFalse(r_5['en_stock'])
        self.assertFalse(r_5["en_stock"])


# Punto de entrada principal cuando el script se invoca directamente desde consola
if __name__ == "__main__":
    # Ejecutamos instrucción: unittest.main()
    unittest.main()

