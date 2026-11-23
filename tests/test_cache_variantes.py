"""
PerfumeTrending.cl — Pruebas de Caché de Variantes en Memoria (Opción 2)
========================================================================
Valida la reducción de consultas N+1 a 'variantes_perfume' en Supabase
utilizando mocks aislados sin conexión a bases de datos de producción.
"""

# Importación de librería estándar o dependencia externa (unittest)
import unittest
# Importación de componentes (MagicMock, patch) desde el módulo 'unittest.mock'
from unittest.mock import MagicMock, patch
# Importación de librería estándar o dependencia externa (os)
import os
# Importación de librería estándar o dependencia externa (sys)
import sys

# Asegurar path
sys.path.insert(0, os.path.abspath("APP"))
# Ejecutamos instrucción: sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath("."))

# Importación de librería estándar o dependencia externa (APP.backend.database)
import APP.backend.database as db_module
# Importación de componentes (limpiar_cache_variantes, precargar_cache_variantes_supabase, registrar_fallo_scraping, registrar_observacion_oferta, ...) desde el módulo 'APP.backend.database'
from APP.backend.database import (
    limpiar_cache_variantes,
    precargar_cache_variantes_supabase,
    registrar_fallo_scraping,
    registrar_observacion_oferta,
    _CACHE_VARIANTE_SUPABASE_POR_TUPLA,
    _CACHE_VARIANTE_DEFECTO_SUPABASE,
)


# Definición de clase 'TestCacheVariantesSupabase' que modela la estructura y lógica del componente
class TestCacheVariantesSupabase(unittest.TestCase):
    # Definición de función 'setUp' sin parámetros externos
    def setUp(self):
        # Ejecutamos instrucción: limpiar_cache_variantes()
        limpiar_cache_variantes()

    # Definición de función 'tearDown' sin parámetros externos
    def tearDown(self):
        # Ejecutamos instrucción: limpiar_cache_variantes()
        limpiar_cache_variantes()

    # Definición de función 'test_precargar_cache_correctitud' sin parámetros externos
    def test_precargar_cache_correctitud(self):
        """Verifica que la precarga puebla correctamente tuplas y variantes por defecto."""
        # Asignamos 'filas' con [{'id': 101, 'perfume_id': 1, 'volumen_ml'...
        filas = [
            # Configuración de elemento #1 (id='101')
            {"id": 101, "perfume_id": 1, "volumen_ml": 100, "formato": "regular"},
            # Configuración de elemento #2 (id='102')
            {"id": 102, "perfume_id": 1, "volumen_ml": 50, "formato": "regular"},
            # Configuración de elemento #3 (id='103')
            {"id": 103, "perfume_id": 1, "volumen_ml": 100, "formato": "tester"},
            # Configuración de elemento #4 (id='201')
            {"id": 201, "perfume_id": 2, "volumen_ml": 100, "formato": "regular"},
        ]
        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
        cargadas = precargar_cache_variantes_supabase(filas)
        # Aserción de prueba unitaria: self.assertEqual(cargadas, 4)
        self.assertEqual(cargadas, 4)

        # Distinción de formatos y volúmenes para el mismo perfume
        self.assertEqual(_CACHE_VARIANTE_SUPABASE_POR_TUPLA[(1, 100, "regular")], 101)
        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
        self.assertEqual(_CACHE_VARIANTE_SUPABASE_POR_TUPLA[(1, 50, "regular")], 102)
        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
        self.assertEqual(_CACHE_VARIANTE_SUPABASE_POR_TUPLA[(1, 100, "tester")], 103)
        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
        self.assertEqual(_CACHE_VARIANTE_SUPABASE_POR_TUPLA[(2, 100, "regular")], 201)

        # Variante por defecto (la primera vista para cada perfume)
        self.assertEqual(_CACHE_VARIANTE_DEFECTO_SUPABASE[1], 101)
        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
        self.assertEqual(_CACHE_VARIANTE_DEFECTO_SUPABASE[2], 201)

    # Definición de función 'test_medicion_consultas_registrar_fallo_con_y_sin_cache' sin parámetros externos
    def test_medicion_consultas_registrar_fallo_con_y_sin_cache(self):
        """
        Mide la cantidad de consultas a 'variantes_perfume' al reportar 15 tiendas fallidas
        para un mismo perfume.
        """
        # Asignamos 'queries_ejecutadas' con 0
        queries_ejecutadas = 0

        # Asignamos 'mock_sb' con MagicMock()
        mock_sb = MagicMock()
        # Asignamos 'mock_table' con MagicMock()
        mock_table = MagicMock()
        # Asignamos 'mock_select' con MagicMock()
        mock_select = MagicMock()
        # Asignamos 'mock_eq' con MagicMock()
        mock_eq = MagicMock()
        # Asignamos 'mock_limit' con MagicMock()
        mock_limit = MagicMock()

        # Definición de función 'contar_execute' sin parámetros externos
        def contar_execute():
            # Ejecutamos instrucción: nonlocal queries_ejecutadas
            nonlocal queries_ejecutadas
            # Actualizamos acumulativamente el valor de 'queries_ejecutadas'
            queries_ejecutadas += 1
            # Retornamos el resultado procesado (MagicMock(data=[{'id': 555}]))
            return MagicMock(data=[{"id": 555}])

        # Asignamos 'mock_limit.execute' con contar_execute
        mock_limit.execute = contar_execute
        # Asignamos 'mock_eq.limit.return_value' con mock_limit
        mock_eq.limit.return_value = mock_limit
        # Asignamos 'mock_select.eq.return_value' con mock_eq
        mock_select.eq.return_value = mock_eq
        # Asignamos 'mock_table.select.return_value' con mock_select
        mock_table.select.return_value = mock_select
        # Asignamos 'mock_sb.table.return_value' con mock_table
        mock_sb.table.return_value = mock_table
        # Asignamos 'mock_sb.rpc.return_value.execute...' con MagicMock(data={'resultado': 'fallo_regist...
        mock_sb.rpc.return_value.execute.return_value = MagicMock(data={"resultado": "fallo_registrado"})

        # Simular supabase disponible con nuestro mock
        with patch.object(db_module, "get_supabase", return_value=mock_sb), \
             patch.object(db_module, "is_supabase_disponible", return_value=True):

            # Caso A: Con caché vacía y 15 tiendas fallidas para el perfume 1
            for tienda_id in range(1, 16):
                # Ejecutamos instrucción: registrar_fallo_scraping(tienda_id=tienda_id, perfum...
                registrar_fallo_scraping(tienda_id=tienda_id, perfume_id=1, mensaje="No encontrado")

            # La primera llamada consulta Supabase y la guarda; las 14 siguientes son cache hits
            self.assertEqual(queries_ejecutadas, 1, "Solo debió consultar 1 vez a Supabase gracias a la caché")
            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            self.assertEqual(_CACHE_VARIANTE_DEFECTO_SUPABASE[1], 555)

            # Caso B: Con precarga previa para perfume 2
            precargar_cache_variantes_supabase([{"id": 777, "perfume_id": 2, "volumen_ml": 100, "formato": "regular"}])
            # Asignamos 'queries_antes_p2' con queries_ejecutadas
            queries_antes_p2 = queries_ejecutadas

            # Recorremos iterativamente cada 'tienda_id' en range(1, 16)
            for tienda_id in range(1, 16):
                # Ejecutamos instrucción: registrar_fallo_scraping(tienda_id=tienda_id, perfum...
                registrar_fallo_scraping(tienda_id=tienda_id, perfume_id=2, mensaje="No encontrado")

            # Cero consultas adicionales a 'variantes_perfume' porque estaba precargado
            self.assertEqual(queries_ejecutadas - queries_antes_p2, 0, "Con precarga debe haber 0 consultas a variantes_perfume")

    # Definición de función 'test_medicion_consultas_registrar_observacion_con_cache' sin parámetros externos
    def test_medicion_consultas_registrar_observacion_con_cache(self):
        """
        Mide consultas a 'variantes_perfume' al registrar 5 ofertas para el mismo perfume/volumen.
        """
        # Asignamos 'queries_ejecutadas' con 0
        queries_ejecutadas = 0

        # Asignamos 'mock_sb' con MagicMock()
        mock_sb = MagicMock()
        # Asignamos 'mock_table' con MagicMock()
        mock_table = MagicMock()
        # Asignamos 'mock_select' con MagicMock()
        mock_select = MagicMock()
        # Asignamos 'mock_eq1' con MagicMock()
        mock_eq1 = MagicMock()
        # Asignamos 'mock_eq2' con MagicMock()
        mock_eq2 = MagicMock()
        # Asignamos 'mock_eq3' con MagicMock()
        mock_eq3 = MagicMock()
        # Asignamos 'mock_limit' con MagicMock()
        mock_limit = MagicMock()

        # Definición de función 'contar_execute' sin parámetros externos
        def contar_execute():
            # Ejecutamos instrucción: nonlocal queries_ejecutadas
            nonlocal queries_ejecutadas
            # Actualizamos acumulativamente el valor de 'queries_ejecutadas'
            queries_ejecutadas += 1
            # Retornamos el resultado procesado (MagicMock(data=[{'id': 888}]))
            return MagicMock(data=[{"id": 888}])

        # Asignamos 'mock_limit.execute' con contar_execute
        mock_limit.execute = contar_execute
        # Asignamos 'mock_eq3.limit.return_value' con mock_limit
        mock_eq3.limit.return_value = mock_limit
        # Asignamos 'mock_eq2.eq.return_value' con mock_eq3
        mock_eq2.eq.return_value = mock_eq3
        # Asignamos 'mock_eq1.eq.return_value' con mock_eq2
        mock_eq1.eq.return_value = mock_eq2
        # Asignamos 'mock_select.eq.return_value' con mock_eq1
        mock_select.eq.return_value = mock_eq1
        # Asignamos 'mock_table.select.return_value' con mock_select
        mock_table.select.return_value = mock_select
        # Asignamos 'mock_sb.table.return_value' con mock_table
        mock_sb.table.return_value = mock_table
        # Asignamos 'mock_sb.rpc.return_value.execute...' con MagicMock(data={'resultado': 'actualizada'})
        mock_sb.rpc.return_value.execute.return_value = MagicMock(data={"resultado": "actualizada"})

        # Gestión automática de contexto y recursos para: patch.object(db_module, 'get_supabase', return_...
        with patch.object(db_module, "get_supabase", return_value=mock_sb), \
             patch.object(db_module, "is_supabase_disponible", return_value=True):

            # Recorremos iterativamente cada 'tienda_id' en range(1, 6)
            for tienda_id in range(1, 6):
                # Asignamos 'res' con registrar_observacion_oferta({'perfume_id'...
                res = registrar_observacion_oferta({
                    "perfume_id": 42,
                    "tienda_id": tienda_id,
                    "precio_actual": 89990,
                    "volumen_ml": 100,
                    "formato": "regular",
                    "en_stock": True,
                    "url_producto": "https://tienda.cl/producto/42",
                })
                # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
                self.assertEqual(res.get("resultado"), "actualizada")

            # De las 5 tiendas, solo 1 debió consultar la tabla variantes_perfume
            self.assertEqual(queries_ejecutadas, 1, "Solo 1 consulta a variantes_perfume para 5 observaciones idénticas")

    # Definición de función 'test_limpiar_cache' sin parámetros externos
    def test_limpiar_cache(self):
        """Verifica que limpiar_cache_variantes vacía ambas estructuras."""
        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
        _CACHE_VARIANTE_SUPABASE_POR_TUPLA[(1, 100, "regular")] = 999
        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
        _CACHE_VARIANTE_DEFECTO_SUPABASE[1] = 999
        # Ejecutamos instrucción: limpiar_cache_variantes()
        limpiar_cache_variantes()
        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
        self.assertEqual(len(_CACHE_VARIANTE_SUPABASE_POR_TUPLA), 0)
        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
        self.assertEqual(len(_CACHE_VARIANTE_DEFECTO_SUPABASE), 0)


# Punto de entrada principal cuando el script se invoca directamente desde consola
if __name__ == "__main__":
    # Ejecutamos instrucción: unittest.main()
    unittest.main()
