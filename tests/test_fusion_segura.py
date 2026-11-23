# -*- coding: utf-8 -*-
"""
Pruebas unitarias aisladas (sin red ni Supabase en vivo) para la fusión segura
de perfumes duplicados (`APP/backend/mantenimiento/fusionar_perfumes.py`).
"""

# Importación de librería estándar o dependencia externa (os)
import os
# Importación de librería estándar o dependencia externa (sys)
import sys
# Importación de librería estándar o dependencia externa (unittest)
import unittest
# Importación de componentes (Any, Dict, List) desde el módulo 'typing'
from typing import Any, Dict, List

# Ejecutamos instrucción: sys.path.insert(0, os.path.abspath('APP'))
sys.path.insert(0, os.path.abspath("APP"))
# Ejecutamos instrucción: sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath("."))

# Importación de componentes (evaluar_compatibilidad_generos_grupo, fusionar_par_perfumes_sb) desde el módulo 'backend.mantenimiento.fusionar_perfumes'
from backend.mantenimiento.fusionar_perfumes import (
    evaluar_compatibilidad_generos_grupo,
    fusionar_par_perfumes_sb,
)


# Definición de clase '_FakeResult' que modela la estructura y lógica del componente
class _FakeResult:
    # Definición de función '__init__' (parámetros: data)
    def __init__(self, data: List[Dict[str, Any]]):
        # Asignamos 'self.data' con data
        self.data = data
        # Asignamos 'self.count' con len(data)
        self.count = len(data)


# Definición de clase '_FakeQuery' que modela la estructura y lógica del componente
class _FakeQuery:
    # Definición de función '__init__' (parámetros: store, op, payload)
    def __init__(self, store: List[Dict[str, Any]], op: str = "select", payload: Any = None):
        # Asignamos 'self._store' con store
        self._store = store
        # Asignamos 'self._op' con op
        self._op = op
        # Asignamos 'self._payload' con payload
        self._payload = payload
        # Asignamos 'self._filters' con []
        self._filters = []
        # Asignamos 'self._limit' con None
        self._limit = None

    # Definición de función 'select' sin parámetros externos
    def select(self, *_args, **_kwargs):
        # Asignamos 'self._op' con 'select'
        self._op = "select"
        # Retornamos el resultado procesado (self)
        return self

    # Definición de función 'update' (parámetros: payload)
    def update(self, payload: Dict[str, Any]):
        # Asignamos 'self._op' con 'update'
        self._op = "update"
        # Asignamos 'self._payload' con payload
        self._payload = payload
        # Retornamos el resultado procesado (self)
        return self

    # Definición de función 'delete' sin parámetros externos
    def delete(self):
        # Asignamos 'self._op' con 'delete'
        self._op = "delete"
        # Retornamos el resultado procesado (self)
        return self

    # Definición de función 'insert' (parámetros: payload)
    def insert(self, payload: Any):
        # Asignamos 'self._op' con 'insert'
        self._op = "insert"
        # Asignamos 'self._payload' con payload
        self._payload = payload
        # Retornamos el resultado procesado (self)
        return self

    # Definición de función 'eq' (parámetros: col, val)
    def eq(self, col: str, val: Any):
        # Ejecutamos instrucción: self._filters.append((col, val))
        self._filters.append((col, val))
        # Retornamos el resultado procesado (self)
        return self

    # Definición de función 'limit' (parámetros: n)
    def limit(self, n: int):
        # Asignamos 'self._limit' con n
        self._limit = n
        # Retornamos el resultado procesado (self)
        return self

    # Definición de función '_matches' (parámetros: row)
    def _matches(self, row: Dict[str, Any]) -> bool:
        # Retornamos el resultado procesado (all((row.get(c) == v for c, v in self._filters)))
        return all(row.get(c) == v for c, v in self._filters)

    # Definición de función 'execute' sin parámetros externos
    def execute(self) -> _FakeResult:
        # Evaluamos la condición lógica (self._op == 'select') para controlar el flujo
        if self._op == "select":
            # Asignamos 'res' con [dict(r) for r in self._store if self._mat...
            res = [dict(r) for r in self._store if self._matches(r)]
            # Evaluamos la condición lógica (self._limit is not None) para controlar el flujo
            if self._limit is not None:
                # Asignamos 'res' con res[:self._limit]
                res = res[: self._limit]
            # Retornamos el resultado procesado (_FakeResult(res))
            return _FakeResult(res)
        # Evaluamos la condición lógica (self._op == 'update') para controlar el flujo
        if self._op == "update":
            # Asignamos 'updated' con []
            updated = []
            # Recorremos iterativamente cada 'r' en self._store
            for r in self._store:
                # Evaluamos la condición lógica (self._matches(r)) para controlar el flujo
                if self._matches(r):
                    # Ejecutamos instrucción: r.update(self._payload)
                    r.update(self._payload)
                    # Ejecutamos instrucción: updated.append(dict(r))
                    updated.append(dict(r))
            # Retornamos el resultado procesado (_FakeResult(updated))
            return _FakeResult(updated)
        # Evaluamos la condición lógica (self._op == 'delete') para controlar el flujo
        if self._op == "delete":
            # Asignamos 'removed' con [dict(r) for r in self._store if self._mat...
            removed = [dict(r) for r in self._store if self._matches(r)]
            # Asignamos 'self._store[:]' con [r for r in self._store if not self._match...
            self._store[:] = [r for r in self._store if not self._matches(r)]
            # Retornamos el resultado procesado (_FakeResult(removed))
            return _FakeResult(removed)
        # Evaluamos la condición lógica (self._op == 'insert') para controlar el flujo
        if self._op == "insert":
            # Asignamos 'items' con self._payload if isinstance(self._payload,...
            items = self._payload if isinstance(self._payload, list) else [self._payload]
            # Recorremos iterativamente cada 'it' en items
            for it in items:
                # Ejecutamos instrucción: self._store.append(dict(it))
                self._store.append(dict(it))
            # Retornamos el resultado procesado (_FakeResult(items))
            return _FakeResult(items)
        # Propagamos excepción explícita ante condición de error detectada
        raise ValueError(f"Operación no soportada: {self._op}")


# Definición de clase '_FakeSupabase' que modela la estructura y lógica del componente
class _FakeSupabase:
    # Definición de función '__init__' (parámetros: tables, block_precios_update)
    def __init__(self, tables: Dict[str, List[Dict[str, Any]]], block_precios_update: bool = False):
        # Asignamos 'self.tables' con tables
        self.tables = tables
        # Asignamos 'self.block_precios_update' con block_precios_update
        self.block_precios_update = block_precios_update

    # Definición de función 'table' (parámetros: name)
    def table(self, name: str):
        # Asignamos 'store' con self.tables.setdefault(name, [])
        store = self.tables.setdefault(name, [])
        # Asignamos 'q' con _FakeQuery(store)
        q = _FakeQuery(store)
        # Evaluamos la condición lógica (self.block_precios_update and name == 'precios_regis...) para controlar el flujo
        if self.block_precios_update and name == "precios_registro":
            # Definición de función '_noop_update' (parámetros: _payload)
            def _noop_update(_payload):
                # Asignamos 'q._op' con 'select'
                q._op = "select"
                # Retornamos el resultado procesado (q)
                return q

            # Asignamos 'q.update' con _noop_update
            q.update = _noop_update
        # Retornamos el resultado procesado (q)
        return q


# Definición de clase 'TestFusionSeguraPerfumes' que modela la estructura y lógica del componente
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
        # Aserción de prueba unitaria: self.assertEqual(evaluar_compatibilidad_generos_grup...
        self.assertEqual(evaluar_compatibilidad_generos_grupo(["Unisex", "Hombre", "Mujer"]), (False, ""))

    # - ¿Qué hace este test?:
    #   Simula una fusión completa con favoritos duplicados y exclusivos, notas olfativas
    #   (`perfume_notas`, `perfume_familias_olfativas`, `perfume_notas_importacion`),
    #   variantes solapadas y no solapadas, colisión de tienda en `ofertas_actuales` e
    #   historial en `precios_registro`, comprobando que no queden filas huérfanas.
    def test_fusion_par_reasigna_favoritos_notas_variantes_ofertas_sin_huerfanos(self):
        # Asignamos 'tables' con {'perfumes': [{'id': 100, 'marca': 'Giorgi...
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
        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
        sb = _FakeSupabase(tables)
        # Asignamos 'det' con fusionar_par_perfumes_sb(sb, p_origen=tabl...
        det = fusionar_par_perfumes_sb(
            sb,
            p_origen=tables["perfumes"][1],
            p_destino=tables["perfumes"][0],
            now_iso="2026-11-04T00:00:00+00:00",
        )

        # Aserción de prueba unitaria: self.assertEqual(det['favoritos_reasignados'], 2)
        self.assertEqual(det["favoritos_reasignados"], 2)
        # Aserción de prueba unitaria: self.assertEqual(det['notas_reasignadas'], 4)
        self.assertEqual(det["notas_reasignadas"], 4)
        # Perfume 200 eliminado y solo queda 100
        self.assertEqual([p["id"] for p in tables["perfumes"]], [100])
        # Cero referencias huérfanas a perfume_id=200 o variante_id=20
        self.assertEqual([f for f in tables["favoritos_usuario"] if f["perfume_id"] == 200], [])
        # Aserción de prueba unitaria: self.assertEqual([n for n in tables['perfume_notas']...
        self.assertEqual([n for n in tables["perfume_notas"] if n["perfume_id"] == 200], [])
        # Aserción de prueba unitaria: self.assertEqual([n for n in tables['perfume_notas_i...
        self.assertEqual([n for n in tables["perfume_notas_importacion"] if n["perfume_id"] == 200], [])
        # Aserción de prueba unitaria: self.assertEqual(tables['perfume_notas_importacion']...
        self.assertEqual(tables["perfume_notas_importacion"][0]["perfume_id"], 100)
        # Aserción de prueba unitaria: self.assertEqual(sum((1 for f in tables['perfume_fam...
        self.assertEqual(sum(1 for f in tables["perfume_familias_olfativas"] if f["es_principal"]), 1)
        # Aserción de prueba unitaria: self.assertEqual(sorted(((f['usuario_id'], f['perfum...
        self.assertEqual(sorted((f["usuario_id"], f["perfume_id"]) for f in tables["favoritos_usuario"]), [("u-only-dup", 100), ("u-shared", 100)])
        # Aserción de prueba unitaria: self.assertEqual([v for v in tables['variantes_perfu...
        self.assertEqual([v for v in tables["variantes_perfume"] if v["perfume_id"] == 200], [])
        # Aserción de prueba unitaria: self.assertEqual(sorted((v['id'] for v in tables['va...
        self.assertEqual(sorted(v["id"] for v in tables["variantes_perfume"]), [10, 21])
        # Aserción de prueba unitaria: self.assertTrue(all((pr['perfume_id'] == 100 for pr ...
        self.assertTrue(all(pr["perfume_id"] == 100 for pr in tables["precios_registro"]))
        # Aserción de prueba unitaria: self.assertTrue(all((pr['variante_id'] in (10, 21) f...
        self.assertTrue(all(pr["variante_id"] in (10, 21) for pr in tables["precios_registro"]))

        # La oferta en tienda 4 sobre variante 10 se actualizó con los datos en stock de 2001 ($89.990)
        of_t4 = [o for o in tables["ofertas_actuales"] if o["variante_id"] == 10 and o["tienda_id"] == 4]
        # Aserción de prueba unitaria: self.assertEqual(len(of_t4), 1)
        self.assertEqual(len(of_t4), 1)
        # Aserción de prueba unitaria: self.assertEqual(of_t4[0]['precio_actual'], 89990)
        self.assertEqual(of_t4[0]["precio_actual"], 89990)
        # Aserción de prueba unitaria: self.assertTrue(of_t4[0]['en_stock'])
        self.assertTrue(of_t4[0]["en_stock"])

    # - ¿Qué hace este test?:
    #   Comprueba que si queda cualquier referencia residual en `precios_registro`,
    #   la función lanza `RuntimeError` y NO borra el perfume duplicado.
    def test_aborta_si_quedan_referencias_residuales(self):
        # Asignamos 'tables' con {'perfumes': [{'id': 100, 'marca': 'Dior',...
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
        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
        sb = _FakeSupabase(tables, block_precios_update=True)
        # Gestión automática de contexto y recursos para: self.assertRaises(RuntimeError)
        with self.assertRaises(RuntimeError):
            # Ejecutamos instrucción: fusionar_par_perfumes_sb(sb, p_origen=tables['perfum...
            fusionar_par_perfumes_sb(
                sb,
                p_origen=tables["perfumes"][1],
                p_destino=tables["perfumes"][0],
                now_iso="2026-11-04T00:00:00+00:00",
            )
        # Perfume 200 NO fue borrado
        self.assertEqual(len(tables["perfumes"]), 2)

    # Definición de función 'test_clave_identidad_perfume_casos_difusos' sin parámetros externos
    def test_clave_identidad_perfume_casos_difusos(self):
        # Importación de componentes (clave_identidad_perfume) desde el módulo 'backend.normalizador'
        from backend.normalizador import clave_identidad_perfume

        # Aserción de prueba unitaria: self.assertEqual(clave_identidad_perfume('Miss Dior ...
        self.assertEqual(
            clave_identidad_perfume("Miss Dior Rose & Roses", "Dior", "Eau de Toilette", True),
            clave_identidad_perfume("Miss Dior Rose N Roses", "Dior", "Eau de Toilette", True),
        )
        # Aserción de prueba unitaria: self.assertEqual(clave_identidad_perfume('Eros', 'Ve...
        self.assertEqual(
            clave_identidad_perfume("Eros", "Versace", "Eau de Toilette", True),
            clave_identidad_perfume("Eros Versace", "Versace", "Eau de Toilette", True),
        )
        # Aserción de prueba unitaria: self.assertEqual(clave_identidad_perfume('Freeze In ...
        self.assertEqual(
            clave_identidad_perfume("Freeze In Flames Extrait De", "Riiffs", "Extrait de Parfum", True),
            clave_identidad_perfume("Freeze In Flames", "Riiffs", "Extrait de Parfum", True),
        )
        # Aserción de prueba unitaria: self.assertEqual(clave_identidad_perfume('Dylan Blue...
        self.assertEqual(
            clave_identidad_perfume("Dylan Blue", "Versace", "Eau de Toilette", False),
            clave_identidad_perfume("Dylan Blue Pour Homme", "Versace", "Eau de Toilette", False),
        )
        # Aserción de prueba unitaria: self.assertNotEqual(clave_identidad_perfume('Cloud',...
        self.assertNotEqual(
            clave_identidad_perfume("Cloud", "Ariana Grande", "Eau de Parfum", False),
            clave_identidad_perfume("Cloud Intense", "Ariana Grande", "Eau de Parfum", False),
        )
        # Aserción de prueba unitaria: self.assertNotEqual(clave_identidad_perfume('Scandal...
        self.assertNotEqual(
            clave_identidad_perfume("Scandal", "Jean Paul Gaultier", "Parfum", False),
            clave_identidad_perfume("Scandal Le Parfum", "Jean Paul Gaultier", "Parfum", False),
        )


# Punto de entrada principal cuando el script se invoca directamente desde consola
if __name__ == "__main__":
    # Ejecutamos instrucción: unittest.main()
    unittest.main()
