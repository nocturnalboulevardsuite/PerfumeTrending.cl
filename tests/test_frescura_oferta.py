# -*- coding: utf-8 -*-
"""
Pruebas unitarias aisladas para la Política de Frescura de Ofertas (Fase 1):
- Umbrales configurables 3 / 7 / 14 días (`DIAS_OFERTA_FRESCA`, `DIAS_OFERTA_ADVERTENCIA`, `DIAS_OFERTA_OCULTAR`).
- Exclusión de ofertas >7d sin verificar de `mejor_precio` ("Desde $X") y `obtener_remates_reales`.
- Ocultamiento de ofertas en stock >14d sin verificar en `obtener_precios_actuales`.
- Retiro automático a `estado='agotada'` (`en_stock=False`) tras 5 `no_encontrado_en_feed`,
  e inmunidad ante fallos transitorios (`waf`, `timeout`, `parse_error`).
"""

import os
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

import APP.backend.database as db_app

try:
    import backend.database as db_short
except ImportError:
    db_short = None


def _patch_db_modules(db_path: str, db_dir: str):
    """Aísla ambos alias de módulo (`APP.backend.database` y `backend.database`) contra SQLite temporal."""
    originals = []
    for mod in (m for m in (db_app, db_short) if m is not None):
        originals.append((
            mod,
            mod.DB_PATH,
            mod.DB_DIR,
            mod.is_supabase_disponible,
            mod.get_supabase,
        ))
        mod.DB_PATH = db_path
        mod.DB_DIR = db_dir
        mod.is_supabase_disponible = lambda: False
        mod.get_supabase = lambda *a, **kw: None
        mod.limpiar_cache_catalogo()
    return originals


def _restore_db_modules(originals):
    for mod, db_path, db_dir, fn_disp, fn_sb in originals:
        mod.DB_PATH = db_path
        mod.DB_DIR = db_dir
        mod.is_supabase_disponible = fn_disp
        mod.get_supabase = fn_sb
        mod.limpiar_cache_catalogo()


class TestFrescuraOferta(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp_dir = tempfile.mkdtemp(prefix="pt_frescura_")
        cls.tmp_db = os.path.join(cls.tmp_dir, "frescura.db")
        cls._orig = _patch_db_modules(cls.tmp_db, cls.tmp_dir)
        db_app.init_db(force_reseed=False)

        with db_app.get_db_cursor(commit=True) as cur:
            for tid, tnom in [(1, "Tienda Fresca"), (2, "Tienda Reciente"), (3, "Tienda Stale 10d"), (4, "Tienda Obsoleta 18d")]:
                cur.execute(
                    "INSERT OR REPLACE INTO tiendas (id, nombre, url_base, trust_score) VALUES (?, ?, ?, 92);",
                    (tid, tnom, f"https://tienda{tid}.cl"),
                )
            cur.execute(
                """
                INSERT OR REPLACE INTO perfumes (id, nombre, marca, genero, tipo, notas, imagen_url, precio_referencia)
                VALUES (501, 'Perfume Frescura Test', 'Maison Test', 'Hombre', 'Eau de Parfum', 'Bergamota', '', 120000);
                """
            )
            cur.execute(
                """
                INSERT OR REPLACE INTO variantes_perfume (id, perfume_id, concentracion, volumen_ml, formato, slug, activa)
                VALUES (601, 501, 'Eau de Parfum', 100.0, 'regular', 'perfume-501-100ml', 1),
                       (602, 501, 'Eau de Parfum', 50.0, 'regular', 'perfume-501-50ml', 1);
                """
            )

    @classmethod
    def tearDownClass(cls):
        _restore_db_modules(cls._orig)
        shutil.rmtree(cls.tmp_dir, ignore_errors=True)

    def setUp(self):
        with db_app.get_db_cursor(commit=True) as cur:
            cur.execute("DELETE FROM ofertas_actuales;")
            cur.execute("DELETE FROM precios_registro;")
        db_app.limpiar_cache_catalogo()

    def test_01_clasificacion_umbrales_3_7_14_dias(self):
        now = datetime(2026, 11, 4, 12, 0, 0, tzinfo=timezone.utc)
        ts_1d = (now - timedelta(days=1)).isoformat()
        ts_5d = (now - timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S")
        ts_10d = (now - timedelta(days=10)).isoformat().replace("+00:00", "Z")
        ts_16d = (now - timedelta(days=16)).isoformat()

        d1 = db_app.calcular_dias_sin_verificar(ts_1d, now_utc=now)
        d5 = db_app.calcular_dias_sin_verificar(ts_5d, now_utc=now)
        d10 = db_app.calcular_dias_sin_verificar(ts_10d, now_utc=now)
        d16 = db_app.calcular_dias_sin_verificar(ts_16d, now_utc=now)

        self.assertEqual(db_app.clasificar_frescura_oferta(d1), "fresca")
        self.assertEqual(db_app.clasificar_frescura_oferta(d5), "reciente")
        self.assertEqual(db_app.clasificar_frescura_oferta(d10), "desactualizada")
        self.assertEqual(db_app.clasificar_frescura_oferta(d16), "obsoleta")

        self.assertTrue(db_app.es_oferta_elegible_mejor_precio(d5))
        self.assertFalse(db_app.es_oferta_elegible_mejor_precio(d10))
        self.assertTrue(db_app.es_oferta_visible(d10, en_stock=True))
        self.assertFalse(db_app.es_oferta_visible(d16, en_stock=True))
        self.assertTrue(db_app.es_oferta_visible(d16, en_stock=False))

    def test_02_exclusion_mejor_precio_7d_y_ocultamiento_14d(self):
        now = datetime.now(timezone.utc)
        ts_1d = (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        ts_5d = (now - timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S")
        ts_10d = (now - timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S")
        ts_18d = (now - timedelta(days=18)).strftime("%Y-%m-%d %H:%M:%S")

        with db_app.get_db_cursor(commit=True) as cur:
            ofertas = [
                (601, 1, 92000, 120000, 1, "https://tienda1.cl/p", "activa", ts_1d),
                (601, 2, 85000, 120000, 1, "https://tienda2.cl/p", "activa", ts_5d),
                (601, 3, 60000, 120000, 1, "https://tienda3.cl/p", "activa", ts_10d),
                (601, 4, 40000, 120000, 1, "https://tienda4.cl/p", "activa", ts_18d),
            ]
            for vid, tid, pa, pn, st, url, est, ts in ofertas:
                cur.execute(
                    """
                    INSERT INTO ofertas_actuales (
                        variante_id, tienda_id, precio_actual, precio_normal, en_stock,
                        url_producto, estado, ultima_verificacion_exitosa, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (vid, tid, pa, pn, st, url, est, ts, ts),
                )

        precios = db_app.obtener_precios_actuales(501)
        tiendas_visibles = {p["tienda_id"]: p for p in precios}

        # >14d (tienda 4) debe quedar oculta
        self.assertNotIn(4, tiendas_visibles)
        # 10d (tienda 3) sigue visible pero marcada desactualizada y excluida de mejor precio
        self.assertIn(3, tiendas_visibles)
        self.assertEqual(tiendas_visibles[3]["nivel_frescura"], "desactualizada")
        self.assertTrue(tiendas_visibles[3]["excluida_mejor_precio"])
        # 5d (tienda 2) es reciente y sí compite
        self.assertEqual(tiendas_visibles[2]["nivel_frescura"], "reciente")
        self.assertFalse(tiendas_visibles[2]["excluida_mejor_precio"])

        # En el catálogo, "Desde $X" (mejor_precio) debe ser 85.000 (tienda 2, 5d), NUNCA 60.000 (10d) ni 40.000 (18d)
        cat = db_app.obtener_catalogo(busqueda="Frescura Test")
        self.assertEqual(len(cat), 1)
        self.assertEqual(cat[0]["mejor_precio"], 85000)

        # En remates reales, la oferta de 10d (50% dcto) queda excluida y entra la de 5d
        remates = db_app.obtener_remates_reales(limite=10, force_refresh=True)
        tiendas_remates = [r["tienda"] for r in remates]
        self.assertNotIn("Tienda Stale 10d", tiendas_remates)
        self.assertNotIn("Tienda Obsoleta 18d", tiendas_remates)
        self.assertIn("Tienda Reciente", tiendas_remates)

    def test_03_retiro_5_ausencias_feed_vs_inmunidad_waf_timeout(self):
        now_s = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
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
            r_tr = db_app.registrar_fallo_scraping(
                tienda_id=1,
                perfume_id=501,
                variante_id=602,
                mensaje="HTTP 403 Cloudflare Challenge",
                motivo_codigo=codigo,
            )
            self.assertEqual(r_tr["resultado"], "fallo_transitorio")
            self.assertEqual(r_tr["fallos_consecutivos"], 0)
            self.assertTrue(r_tr["en_stock"])

        # 4 ausencias reales en feed mantienen activa, la 5ta la retira a 'agotada' con en_stock=False
        for intento in range(1, 5):
            r_f = db_app.registrar_fallo_scraping(
                tienda_id=1,
                perfume_id=501,
                mensaje="Producto ausente en feed JSON",
                motivo_codigo="no_encontrado_en_feed",
            )
            self.assertEqual(r_f["fallos_consecutivos"], intento)
            self.assertEqual(r_f["estado"], "activa")
            self.assertTrue(r_f["en_stock"])

        r_5 = db_app.registrar_fallo_scraping(
            tienda_id=1,
            perfume_id=501,
            mensaje="Producto ausente en feed JSON",
            motivo_codigo="no_encontrado_en_feed",
        )
        self.assertEqual(r_5["fallos_consecutivos"], 5)
        self.assertEqual(r_5["estado"], "agotada")
        self.assertFalse(r_5["en_stock"])


if __name__ == "__main__":
    unittest.main()
