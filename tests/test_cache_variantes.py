"""
PerfumeTrending.cl — Pruebas de Caché de Variantes en Memoria (Opción 2)
========================================================================
Valida la reducción de consultas N+1 a 'variantes_perfume' en Supabase
utilizando mocks aislados sin conexión a bases de datos de producción.
"""

import unittest
from unittest.mock import MagicMock, patch
import os
import sys

# Asegurar path
sys.path.insert(0, os.path.abspath("APP"))
sys.path.insert(0, os.path.abspath("."))

import APP.backend.database as db_module
from APP.backend.database import (
    limpiar_cache_variantes,
    precargar_cache_variantes_supabase,
    registrar_fallo_scraping,
    registrar_observacion_oferta,
    _CACHE_VARIANTE_SUPABASE_POR_TUPLA,
    _CACHE_VARIANTE_DEFECTO_SUPABASE,
)


class TestCacheVariantesSupabase(unittest.TestCase):
    def setUp(self):
        limpiar_cache_variantes()

    def tearDown(self):
        limpiar_cache_variantes()

    def test_precargar_cache_correctitud(self):
        """Verifica que la precarga puebla correctamente tuplas y variantes por defecto."""
        filas = [
            {"id": 101, "perfume_id": 1, "volumen_ml": 100, "formato": "regular"},
            {"id": 102, "perfume_id": 1, "volumen_ml": 50, "formato": "regular"},
            {"id": 103, "perfume_id": 1, "volumen_ml": 100, "formato": "tester"},
            {"id": 201, "perfume_id": 2, "volumen_ml": 100, "formato": "regular"},
        ]
        cargadas = precargar_cache_variantes_supabase(filas)
        self.assertEqual(cargadas, 4)

        # Distinción de formatos y volúmenes para el mismo perfume
        self.assertEqual(_CACHE_VARIANTE_SUPABASE_POR_TUPLA[(1, 100, "regular")], 101)
        self.assertEqual(_CACHE_VARIANTE_SUPABASE_POR_TUPLA[(1, 50, "regular")], 102)
        self.assertEqual(_CACHE_VARIANTE_SUPABASE_POR_TUPLA[(1, 100, "tester")], 103)
        self.assertEqual(_CACHE_VARIANTE_SUPABASE_POR_TUPLA[(2, 100, "regular")], 201)

        # Variante por defecto (la primera vista para cada perfume)
        self.assertEqual(_CACHE_VARIANTE_DEFECTO_SUPABASE[1], 101)
        self.assertEqual(_CACHE_VARIANTE_DEFECTO_SUPABASE[2], 201)

    def test_medicion_consultas_registrar_fallo_con_y_sin_cache(self):
        """
        Mide la cantidad de consultas a 'variantes_perfume' al reportar 15 tiendas fallidas
        para un mismo perfume.
        """
        queries_ejecutadas = 0

        mock_sb = MagicMock()
        mock_table = MagicMock()
        mock_select = MagicMock()
        mock_eq = MagicMock()
        mock_limit = MagicMock()

        def contar_execute():
            nonlocal queries_ejecutadas
            queries_ejecutadas += 1
            return MagicMock(data=[{"id": 555}])

        mock_limit.execute = contar_execute
        mock_eq.limit.return_value = mock_limit
        mock_select.eq.return_value = mock_eq
        mock_table.select.return_value = mock_select
        mock_sb.table.return_value = mock_table
        mock_sb.rpc.return_value.execute.return_value = MagicMock(data={"resultado": "fallo_registrado"})

        # Simular supabase disponible con nuestro mock
        with patch.object(db_module, "get_supabase", return_value=mock_sb), \
             patch.object(db_module, "is_supabase_disponible", return_value=True):

            # Caso A: Con caché vacía y 15 tiendas fallidas para el perfume 1
            for tienda_id in range(1, 16):
                registrar_fallo_scraping(tienda_id=tienda_id, perfume_id=1, mensaje="No encontrado")

            # La primera llamada consulta Supabase y la guarda; las 14 siguientes son cache hits
            self.assertEqual(queries_ejecutadas, 1, "Solo debió consultar 1 vez a Supabase gracias a la caché")
            self.assertEqual(_CACHE_VARIANTE_DEFECTO_SUPABASE[1], 555)

            # Caso B: Con precarga previa para perfume 2
            precargar_cache_variantes_supabase([{"id": 777, "perfume_id": 2, "volumen_ml": 100, "formato": "regular"}])
            queries_antes_p2 = queries_ejecutadas

            for tienda_id in range(1, 16):
                registrar_fallo_scraping(tienda_id=tienda_id, perfume_id=2, mensaje="No encontrado")

            # Cero consultas adicionales a 'variantes_perfume' porque estaba precargado
            self.assertEqual(queries_ejecutadas - queries_antes_p2, 0, "Con precarga debe haber 0 consultas a variantes_perfume")

    def test_medicion_consultas_registrar_observacion_con_cache(self):
        """
        Mide consultas a 'variantes_perfume' al registrar 5 ofertas para el mismo perfume/volumen.
        """
        queries_ejecutadas = 0

        mock_sb = MagicMock()
        mock_table = MagicMock()
        mock_select = MagicMock()
        mock_eq1 = MagicMock()
        mock_eq2 = MagicMock()
        mock_eq3 = MagicMock()
        mock_limit = MagicMock()

        def contar_execute():
            nonlocal queries_ejecutadas
            queries_ejecutadas += 1
            return MagicMock(data=[{"id": 888}])

        mock_limit.execute = contar_execute
        mock_eq3.limit.return_value = mock_limit
        mock_eq2.eq.return_value = mock_eq3
        mock_eq1.eq.return_value = mock_eq2
        mock_select.eq.return_value = mock_eq1
        mock_table.select.return_value = mock_select
        mock_sb.table.return_value = mock_table
        mock_sb.rpc.return_value.execute.return_value = MagicMock(data={"resultado": "actualizada"})

        with patch.object(db_module, "get_supabase", return_value=mock_sb), \
             patch.object(db_module, "is_supabase_disponible", return_value=True):

            for tienda_id in range(1, 6):
                res = registrar_observacion_oferta({
                    "perfume_id": 42,
                    "tienda_id": tienda_id,
                    "precio_actual": 89990,
                    "volumen_ml": 100,
                    "formato": "regular",
                    "en_stock": True,
                    "url_producto": "https://tienda.cl/producto/42",
                })
                self.assertEqual(res.get("resultado"), "actualizada")

            # De las 5 tiendas, solo 1 debió consultar la tabla variantes_perfume
            self.assertEqual(queries_ejecutadas, 1, "Solo 1 consulta a variantes_perfume para 5 observaciones idénticas")

    def test_limpiar_cache(self):
        """Verifica que limpiar_cache_variantes vacía ambas estructuras."""
        _CACHE_VARIANTE_SUPABASE_POR_TUPLA[(1, 100, "regular")] = 999
        _CACHE_VARIANTE_DEFECTO_SUPABASE[1] = 999
        limpiar_cache_variantes()
        self.assertEqual(len(_CACHE_VARIANTE_SUPABASE_POR_TUPLA), 0)
        self.assertEqual(len(_CACHE_VARIANTE_DEFECTO_SUPABASE), 0)


if __name__ == "__main__":
    unittest.main()
