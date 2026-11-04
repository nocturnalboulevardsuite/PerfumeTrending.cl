# -*- coding: utf-8 -*-
"""
Pruebas unitarias aisladas (sin red ni Supabase en vivo) para la fusión segura
de perfumes duplicados (`APP/backend/mantenimiento/fusionar_perfumes.py`).
"""

import os
import sys
import unittest
from typing import Any, Dict, List

sys.path.insert(0, os.path.abspath("APP"))
sys.path.insert(0, os.path.abspath("."))

from backend.mantenimiento.fusionar_perfumes import (
    evaluar_compatibilidad_generos_grupo,
    fusionar_par_perfumes_sb,
)


class _FakeResult:
    def __init__(self, data: List[Dict[str, Any]]):
        self.data = data
        self.count = len(data)


class _FakeQuery:
    def __init__(self, store: List[Dict[str, Any]], op: str = "select", payload: Any = None):
        self._store = store
        self._op = op
        self._payload = payload
        self._filters = []
        self._limit = None

    def select(self, *_args, **_kwargs):
        self._op = "select"
        return self

    def update(self, payload: Dict[str, Any]):
        self._op = "update"
        self._payload = payload
        return self

    def delete(self):
        self._op = "delete"
        return self

    def insert(self, payload: Any):
        self._op = "insert"
        self._payload = payload
        return self

    def eq(self, col: str, val: Any):
        self._filters.append((col, val))
        return self

    def limit(self, n: int):
        self._limit = n
        return self

    def _matches(self, row: Dict[str, Any]) -> bool:
        return all(row.get(c) == v for c, v in self._filters)

    def execute(self) -> _FakeResult:
        if self._op == "select":
            res = [dict(r) for r in self._store if self._matches(r)]
            if self._limit is not None:
                res = res[: self._limit]
            return _FakeResult(res)
        if self._op == "update":
            updated = []
            for r in self._store:
                if self._matches(r):
                    r.update(self._payload)
                    updated.append(dict(r))
            return _FakeResult(updated)
        if self._op == "delete":
            removed = [dict(r) for r in self._store if self._matches(r)]
            self._store[:] = [r for r in self._store if not self._matches(r)]
            return _FakeResult(removed)
        if self._op == "insert":
            items = self._payload if isinstance(self._payload, list) else [self._payload]
            for it in items:
                self._store.append(dict(it))
            return _FakeResult(items)
        raise ValueError(f"Operación no soportada: {self._op}")


class _FakeSupabase:
    def __init__(self, tables: Dict[str, List[Dict[str, Any]]], block_precios_update: bool = False):
        self.tables = tables
        self.block_precios_update = block_precios_update

    def table(self, name: str):
        store = self.tables.setdefault(name, [])
        q = _FakeQuery(store)
        if self.block_precios_update and name == "precios_registro":
            def _noop_update(_payload):
                q._op = "select"
                return q

            q.update = _noop_update
        return q


class TestFusionSeguraPerfumes(unittest.TestCase):
    # - ¿Qué hace este test?:
    #   Verifica que las reglas de compatibilidad de género unifiquen Unisex con Hombre/Mujer,
    #   pero bloqueen cualquier fusión automática entre Hombre y Mujer.
    def test_compatibilidad_generos_pares_reales(self):
        # Romance (Mujer / Unisex) y 212 VIP (Mujer / Unisex)
        self.assertEqual(evaluar_compatibilidad_generos_grupo(["Mujer", "Unisex"]), (True, "Mujer"))
        # Hayaati (Hombre / Unisex) y Stronger With You Powerfully x3 (Hombre / Unisex / Hombre)
        self.assertEqual(evaluar_compatibilidad_generos_grupo(["Hombre", "Unisex", "Hombre"]), (True, "Hombre"))
        # Conflicto explícito Hombre vs Mujer -> jamás fusionar automáticamente
        self.assertEqual(evaluar_compatibilidad_generos_grupo(["Hombre", "Mujer"]), (False, ""))
        self.assertEqual(evaluar_compatibilidad_generos_grupo(["Unisex", "Hombre", "Mujer"]), (False, ""))

    # - ¿Qué hace este test?:
    #   Simula una fusión completa con favoritos duplicados y exclusivos, notas olfativas
    #   (`perfume_notas`, `perfume_familias_olfativas`, `perfume_notas_importacion`),
    #   variantes solapadas y no solapadas, colisión de tienda en `ofertas_actuales` e
    #   historial en `precios_registro`, comprobando que no queden filas huérfanas.
    def test_fusion_par_reasigna_favoritos_notas_variantes_ofertas_sin_huerfanos(self):
        tables = {
            "perfumes": [
                {"id": 100, "marca": "Giorgio Armani", "nombre": "Stronger With You Powerfully", "genero": "Hombre", "tipo": "Eau de Parfum"},
                {"id": 200, "marca": "Giorgio Armani", "nombre": "Armani Stronger With You Powerfully", "genero": "Unisex", "tipo": "Eau de Parfum"},
            ],
            "favoritos_usuario": [
                {"id": 1, "usuario_id": "u-shared", "perfume_id": 100},
                {"id": 2, "usuario_id": "u-shared", "perfume_id": 200},  # Colisión UNIQUE(usuario_id, perfume_id)
                {"id": 3, "usuario_id": "u-only-dup", "perfume_id": 200},  # Debe moverse a 100
            ],
            "perfume_notas": [
                {"id": 11, "perfume_id": 100, "nota_id": 7, "etapa": "salida"},
                {"id": 12, "perfume_id": 200, "nota_id": 7, "etapa": "salida"},  # Colisión UNIQUE(perfume_id, nota_id, etapa)
                {"id": 13, "perfume_id": 200, "nota_id": 9, "etapa": "fondo"},   # Debe moverse a 100
            ],
            "perfume_familias_olfativas": [
                {"id": 21, "perfume_id": 100, "familia_id": 3, "es_principal": True},
                {"id": 22, "perfume_id": 200, "familia_id": 5, "es_principal": True},  # Se mueve pero es_principal pasa a False
            ],
            "perfume_notas_importacion": [
                {"id": 45, "perfume_id": 200, "texto_original": "Notas aromáticas exclusivas", "estado": "pendiente"},
            ],
            "variantes_perfume": [
                {"id": 10, "perfume_id": 100, "volumen_ml": 100.0, "formato": "regular"},
                {"id": 20, "perfume_id": 200, "volumen_ml": 100.0, "formato": "regular"},  # Solapada con id=10
                {"id": 21, "perfume_id": 200, "volumen_ml": 50.0, "formato": "regular"},   # Exclusiva -> se mueve entera
            ],
            "ofertas_actuales": [
                {
                    "id": 1001, "variante_id": 10, "tienda_id": 4,
                    "precio_actual": 95990, "precio_normal": 120000,
                    "en_stock": False, "estado": "agotada",
                    "ultima_verificacion_exitosa": "2026-11-01T00:00:00+00:00",
                    "url_producto": "https://silk.cl/old",
                },
                {
                    "id": 2001, "variante_id": 20, "tienda_id": 4,
                    "precio_actual": 89990, "precio_normal": 120000,
                    "en_stock": True, "estado": "activa",
                    "ultima_verificacion_exitosa": "2026-11-03T12:00:00+00:00",
                    "url_producto": "https://silk.cl/fresh",
                },
                {
                    "id": 2002, "variante_id": 20, "tienda_id": 12,
                    "precio_actual": 82990, "precio_normal": 165980,
                    "en_stock": True, "estado": "activa",
                    "ultima_verificacion_exitosa": "2026-11-03T12:00:00+00:00",
                    "url_producto": "https://mundoaromas.cl/p",
                },
                {
                    "id": 2003, "variante_id": 21, "tienda_id": 12,
                    "precio_actual": 69990, "precio_normal": 99990,
                    "en_stock": True, "estado": "activa",
                    "ultima_verificacion_exitosa": "2026-11-03T12:00:00+00:00",
                    "url_producto": "https://mundoaromas.cl/p50",
                },
            ],
            "precios_registro": [
                {"id": 501, "perfume_id": 200, "variante_id": 20, "precio_actual": 89990},
                {"id": 502, "perfume_id": 200, "variante_id": 21, "precio_actual": 69990},
            ],
        }
        sb = _FakeSupabase(tables)
        det = fusionar_par_perfumes_sb(
            sb,
            p_origen=tables["perfumes"][1],
            p_destino=tables["perfumes"][0],
            now_iso="2026-11-04T00:00:00+00:00",
        )

        self.assertEqual(det["favoritos_reasignados"], 2)
        self.assertEqual(det["notas_reasignadas"], 4)
        # Perfume 200 eliminado y solo queda 100
        self.assertEqual([p["id"] for p in tables["perfumes"]], [100])
        # Cero referencias huérfanas a perfume_id=200 o variante_id=20
        self.assertEqual([f for f in tables["favoritos_usuario"] if f["perfume_id"] == 200], [])
        self.assertEqual([n for n in tables["perfume_notas"] if n["perfume_id"] == 200], [])
        self.assertEqual([n for n in tables["perfume_notas_importacion"] if n["perfume_id"] == 200], [])
        self.assertEqual(tables["perfume_notas_importacion"][0]["perfume_id"], 100)
        self.assertEqual(sum(1 for f in tables["perfume_familias_olfativas"] if f["es_principal"]), 1)
        self.assertEqual(sorted((f["usuario_id"], f["perfume_id"]) for f in tables["favoritos_usuario"]), [("u-only-dup", 100), ("u-shared", 100)])
        self.assertEqual([v for v in tables["variantes_perfume"] if v["perfume_id"] == 200], [])
        self.assertEqual(sorted(v["id"] for v in tables["variantes_perfume"]), [10, 21])
        self.assertTrue(all(pr["perfume_id"] == 100 for pr in tables["precios_registro"]))
        self.assertTrue(all(pr["variante_id"] in (10, 21) for pr in tables["precios_registro"]))

        # La oferta en tienda 4 sobre variante 10 se actualizó con los datos en stock de 2001 ($89.990)
        of_t4 = [o for o in tables["ofertas_actuales"] if o["variante_id"] == 10 and o["tienda_id"] == 4]
        self.assertEqual(len(of_t4), 1)
        self.assertEqual(of_t4[0]["precio_actual"], 89990)
        self.assertTrue(of_t4[0]["en_stock"])

    # - ¿Qué hace este test?:
    #   Comprueba que si queda cualquier referencia residual en `precios_registro`,
    #   la función lanza `RuntimeError` y NO borra el perfume duplicado.
    def test_aborta_si_quedan_referencias_residuales(self):
        tables = {
            "perfumes": [
                {"id": 100, "marca": "Dior", "nombre": "Sauvage", "genero": "Hombre", "tipo": "Eau de Parfum"},
                {"id": 200, "marca": "Dior", "nombre": "Sauvage", "genero": "Unisex", "tipo": "Eau de Parfum"},
            ],
            "favoritos_usuario": [],
            "variantes_perfume": [],
            "ofertas_actuales": [],
            "precios_registro": [
                {"id": 900, "perfume_id": 200, "variante_id": None, "precio_actual": 99990},
            ],
        }
        sb = _FakeSupabase(tables, block_precios_update=True)
        with self.assertRaises(RuntimeError):
            fusionar_par_perfumes_sb(
                sb,
                p_origen=tables["perfumes"][1],
                p_destino=tables["perfumes"][0],
                now_iso="2026-11-04T00:00:00+00:00",
            )
        # Perfume 200 NO fue borrado
        self.assertEqual(len(tables["perfumes"]), 2)


if __name__ == "__main__":
    unittest.main()
