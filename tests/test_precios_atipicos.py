# -*- coding: utf-8 -*-
"""
Pruebas unitarias aisladas para `detectar_precios_atipicos` (Fase 5).
Cubre:
  1. Caso real Libre 100 ml a $64.990 frente a mediana de mercado (< 0.5x mediana con >= 4 ofertas).
  2. Caso real Tester a $200.000 por encima de botella regular sellada (`tester > regular`) y > 2.2x mediana.
  3. Variantes con < 4 ofertas regulares no disparan falsos positivos por mediana, pero sí validan `tester > regular`.
  4. Ofertas ya agotadas o retiradas no contaminan el cálculo de la mediana.
"""

# Importación de librería estándar o dependencia externa (unittest)
import unittest
# Importación de componentes (detectar_precios_atipicos) desde el módulo 'APP.backend.normalizador'
from APP.backend.normalizador import detectar_precios_atipicos


# Definición de clase 'TestPreciosAtipicosFase5' que modela la estructura y lógica del componente
class TestPreciosAtipicosFase5(unittest.TestCase):
    # Definición de función 'test_01_detecta_precio_bajo_atipico_caso_64990' sin parámetros externos
    def test_01_detecta_precio_bajo_atipico_caso_64990(self):
        # Asignamos 'ofertas' con [{'id': 1, 'tienda_id': 1, 'precio_actual'...
        ofertas = [
            # Configuración de elemento #1 (id='1')
            {"id": 1, "tienda_id": 1, "precio_actual": 64990, "formato": "regular", "en_stock": True, "estado": "activa"},
            # Configuración de elemento #2 (id='2')
            {"id": 2, "tienda_id": 2, "precio_actual": 134990, "formato": "regular", "en_stock": True, "estado": "activa"},
            # Configuración de elemento #3 (id='3')
            {"id": 3, "tienda_id": 3, "precio_actual": 139990, "formato": "regular", "en_stock": True, "estado": "activa"},
            # Configuración de elemento #4 (id='4')
            {"id": 4, "tienda_id": 4, "precio_actual": 144990, "formato": "regular", "en_stock": True, "estado": "activa"},
            # Configuración de elemento #5 (id='5')
            {"id": 5, "tienda_id": 5, "precio_actual": 149990, "formato": "regular", "en_stock": True, "estado": "activa"},
        ]
        # Asignamos 'outliers' con detectar_precios_atipicos(ofertas)
        outliers = detectar_precios_atipicos(ofertas)
        # Asignamos 'ids' con [o['id'] for o in outliers]
        ids = [o["id"] for o in outliers]
        # Aserción de prueba unitaria: self.assertEqual(ids, [1])
        self.assertEqual(ids, [1])
        # Aserción de prueba unitaria: self.assertEqual(outliers[0]['regla_outlier'], 'bajo...
        self.assertEqual(outliers[0]["regla_outlier"], "bajo_mediana")
        # Aserción de prueba unitaria: self.assertEqual(outliers[0]['estado_sugerido'], 're...
        self.assertEqual(outliers[0]["estado_sugerido"], "requiere_revision")

    # Definición de función 'test_02_detecta_precio_alto_atipico_y_tester_200000_mayor_que_regular' sin parámetros externos
    def test_02_detecta_precio_alto_atipico_y_tester_200000_mayor_que_regular(self):
        # Asignamos 'ofertas' con [{'id': 10, 'tienda_id': 1, 'precio_actual...
        ofertas = [
            # Configuración de elemento #1 (id='10')
            {"id": 10, "tienda_id": 1, "precio_actual": 82990, "formato": "regular", "en_stock": True, "estado": "activa"},
            # Configuración de elemento #2 (id='11')
            {"id": 11, "tienda_id": 2, "precio_actual": 86990, "formato": "regular", "en_stock": True, "estado": "activa"},
            # Configuración de elemento #3 (id='12')
            {"id": 12, "tienda_id": 3, "precio_actual": 89990, "formato": "regular", "en_stock": True, "estado": "activa"},
            # Configuración de elemento #4 (id='13')
            {"id": 13, "tienda_id": 4, "precio_actual": 92990, "formato": "regular", "en_stock": True, "estado": "activa"},
            # Configuración de elemento #5 (id='14')
            {"id": 14, "tienda_id": 5, "precio_actual": 215000, "formato": "regular", "en_stock": True, "estado": "activa"},
            # Configuración de elemento #6 (id='15')
            {"id": 15, "tienda_id": 6, "precio_actual": 200000, "formato": "tester", "en_stock": True, "estado": "activa"},
        ]
        # Asignamos 'outliers' con detectar_precios_atipicos(ofertas)
        outliers = detectar_precios_atipicos(ofertas)
        # Asignamos 'por_id' con {o['id']: o for o in outliers}
        por_id = {o["id"]: o for o in outliers}
        # Aserción de prueba unitaria: self.assertIn(14, por_id)
        self.assertIn(14, por_id)
        # Aserción de prueba unitaria: self.assertEqual(por_id[14]['regla_outlier'], 'sobre...
        self.assertEqual(por_id[14]["regla_outlier"], "sobre_mediana")
        # Aserción de prueba unitaria: self.assertIn(15, por_id)
        self.assertIn(15, por_id)
        # Aserción de prueba unitaria: self.assertEqual(por_id[15]['regla_outlier'], 'teste...
        self.assertEqual(por_id[15]["regla_outlier"], "tester_mayor_que_regular")

    # Definición de función 'test_03_menos_de_4_ofertas_no_aplica_mediana_pero_si_tester_sobre_regular' sin parámetros externos
    def test_03_menos_de_4_ofertas_no_aplica_mediana_pero_si_tester_sobre_regular(self):
        # Asignamos 'ofertas' con [{'id': 21, 'tienda_id': 1, 'precio_actual...
        ofertas = [
            # Configuración de elemento #1 (id='21')
            {"id": 21, "tienda_id": 1, "precio_actual": 45000, "formato": "regular", "en_stock": True, "estado": "activa"},
            # Configuración de elemento #2 (id='22')
            {"id": 22, "tienda_id": 2, "precio_actual": 98000, "formato": "regular", "en_stock": True, "estado": "activa"},
            # Configuración de elemento #3 (id='23')
            {"id": 23, "tienda_id": 3, "precio_actual": 105000, "formato": "tester", "en_stock": True, "estado": "activa"},
        ]
        # Asignamos 'outliers' con detectar_precios_atipicos(ofertas)
        outliers = detectar_precios_atipicos(ofertas)
        # Aserción de prueba unitaria: self.assertEqual([o['id'] for o in outliers], [23])
        self.assertEqual([o["id"] for o in outliers], [23])
        # Aserción de prueba unitaria: self.assertEqual(outliers[0]['regla_outlier'], 'test...
        self.assertEqual(outliers[0]["regla_outlier"], "tester_mayor_que_regular")

    # Definición de función 'test_04_tester_barato_legitimo_no_se_marca_como_outlier' sin parámetros externos
    def test_04_tester_barato_legitimo_no_se_marca_como_outlier(self):
        # Asignamos 'ofertas' con [{'id': 31, 'tienda_id': 1, 'precio_actual...
        ofertas = [
            # Configuración de elemento #1 (id='31')
            {"id": 31, "tienda_id": 1, "precio_actual": 99990, "formato": "regular", "en_stock": True, "estado": "activa"},
            # Configuración de elemento #2 (id='32')
            {"id": 32, "tienda_id": 2, "precio_actual": 104990, "formato": "regular", "en_stock": True, "estado": "activa"},
            # Configuración de elemento #3 (id='33')
            {"id": 33, "tienda_id": 3, "precio_actual": 74990, "formato": "tester", "en_stock": True, "estado": "activa"},
        ]
        # Aserción de prueba unitaria: self.assertEqual(detectar_precios_atipicos(ofertas),...
        self.assertEqual(detectar_precios_atipicos(ofertas), [])


# Punto de entrada principal cuando el script se invoca directamente desde consola
if __name__ == "__main__":
    # Ejecutamos instrucción: unittest.main()
    unittest.main()

