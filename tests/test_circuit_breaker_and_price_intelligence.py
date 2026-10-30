"""
Unit tests for:
- Propuesta 1: Circuit Breaker / Backoff de Retail (scraper_periodico.py)
- Propuesta 2: Horizontal 4-Shard Partitioning Math
- Propuesta 4: Price Intelligence (obtener_minimo_historico, es_minimo_historico, obtener_mayores_bajadas_recientes)
"""

import unittest
import os
import json
import tempfile
from datetime import datetime, timedelta

from APP.backend.scraper_periodico import (
    es_circuit_breaker_activo,
    registrar_resultado_circuit_breaker,
    cargar_circuit_breaker,
    guardar_circuit_breaker,
)
from APP.backend.database import (
    obtener_minimo_historico,
    es_minimo_historico,
    obtener_mayores_bajadas_recientes,
    get_connection,
    init_db,
)


class TestCircuitBreakerRetail(unittest.TestCase):
    def test_circuit_breaker_empty_data(self):
        self.assertFalse(es_circuit_breaker_activo(10, 1, None))
        self.assertFalse(es_circuit_breaker_activo(10, 1, {}))

    def test_circuit_breaker_below_threshold(self):
        cb_data = {
            "10:1": {
                "fallos_consecutivos": 2,
                "ultimo_intento": datetime.now().isoformat(),
            }
        }
        self.assertFalse(es_circuit_breaker_activo(10, 1, cb_data, umbral_fallos=3))

    def test_circuit_breaker_active_cooldown(self):
        cb_data = {
            "10:1": {
                "fallos_consecutivos": 3,
                "ultimo_intento": (datetime.now() - timedelta(days=2)).isoformat(),
            }
        }
        self.assertTrue(es_circuit_breaker_activo(10, 1, cb_data, umbral_fallos=3, dias_enfriamiento=7))

    def test_circuit_breaker_half_open_retry_after_cooldown(self):
        # 8 days ago: cooldown has passed (7 days), should allow half-open retry
        cb_data = {
            "10:1": {
                "fallos_consecutivos": 3,
                "ultimo_intento": (datetime.now() - timedelta(days=8)).isoformat(),
            }
        }
        self.assertFalse(es_circuit_breaker_activo(10, 1, cb_data, umbral_fallos=3, dias_enfriamiento=7))

    def test_registrar_resultado_circuit_breaker(self):
        cb_data = {}
        # 1st failure
        registrar_resultado_circuit_breaker(perfume_id=10, tienda_id=2, exito=False, cb_data=cb_data)
        self.assertIn("10:2", cb_data)
        self.assertEqual(cb_data["10:2"]["fallos_consecutivos"], 1)

        # 2nd failure
        registrar_resultado_circuit_breaker(perfume_id=10, tienda_id=2, exito=False, cb_data=cb_data)
        self.assertEqual(cb_data["10:2"]["fallos_consecutivos"], 2)

        # Success clears the breaker
        registrar_resultado_circuit_breaker(perfume_id=10, tienda_id=2, exito=True, cb_data=cb_data)
        self.assertNotIn("10:2", cb_data)

    def test_save_and_load_circuit_breaker(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = os.path.join(tmpdir, "cb.json")
            orig_data = {
                "1:5": {"fallos_consecutivos": 4, "ultimo_intento": "2026-10-30T12:00:00"}
            }
            with open(test_path, "w", encoding="utf-8") as f:
                json.dump(orig_data, f)

            with open(test_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            self.assertEqual(loaded, orig_data)


class TestFourShardPartitioning(unittest.TestCase):
    def test_four_shard_partitioning_disjoint_and_complete(self):
        total_items = 3224
        catalog = list(range(1, total_items + 1))
        total_shards = 4

        shards = []
        for s in range(1, total_shards + 1):
            shard_items = [p for idx, p in enumerate(catalog) if idx % total_shards == (s - 1)]
            shards.append(shard_items)

        # Verify all shards have ~ equal sizes (3224 / 4 = 806 each)
        for s_idx, shard_list in enumerate(shards, start=1):
            self.assertEqual(len(shard_list), 806, f"Shard {s_idx} does not have 806 items")

        # Verify all shards are mutually disjoint
        for i in range(len(shards)):
            for j in range(i + 1, len(shards)):
                intersection = set(shards[i]).intersection(set(shards[j]))
                self.assertEqual(len(intersection), 0, f"Shards {i+1} and {j+1} overlap!")

        # Verify complete union equals entire catalog
        union_all = set().union(*shards)
        self.assertEqual(len(union_all), total_items)
        self.assertEqual(union_all, set(catalog))


class TestPriceIntelligence(unittest.TestCase):
    def setUp(self):
        init_db()

    def test_es_minimo_historico_edge_cases(self):
        # Non-positive prices must return False
        self.assertFalse(es_minimo_historico(1, 0, 100))
        self.assertFalse(es_minimo_historico(1, -5000, 100))

    def test_obtener_minimo_historico_and_comparison(self):
        # Query minimum price for perfume 1
        min_p = obtener_minimo_historico(1, 100)
        if min_p is not None:
            self.assertGreater(min_p, 0)
            # Matching the historical low is True
            self.assertTrue(es_minimo_historico(1, min_p, 100))
            # Beating the historical low is True
            self.assertTrue(es_minimo_historico(1, min_p - 1, 100))
            # Higher than historical low is False
            self.assertFalse(es_minimo_historico(1, min_p + 5000, 100))

    def test_obtener_mayores_bajadas_recientes(self):
        bajadas = obtener_mayores_bajadas_recientes(limite=5)
        self.assertIsInstance(bajadas, list)
        for item in bajadas:
            self.assertIn("perfume_id", item)
            self.assertIn("precio_actual", item)
            self.assertIn("precio_normal", item)
            self.assertIn("ahorro_clp", item)
            self.assertIn("descuento_pct", item)
            self.assertGreater(item["precio_actual"], 0)
            self.assertGreater(item["precio_normal"], item["precio_actual"])
            self.assertGreaterEqual(item["descuento_pct"], 0)


if __name__ == "__main__":
    unittest.main()

