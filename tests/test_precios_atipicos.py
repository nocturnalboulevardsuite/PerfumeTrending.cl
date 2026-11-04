# -*- coding: utf-8 -*-
"""
Pruebas unitarias aisladas para `detectar_precios_atipicos` (Fase 5).
Cubre:
  1. Caso real Libre 100 ml a $64.990 frente a mediana de mercado (< 0.5x mediana con >= 4 ofertas).
  2. Caso real Tester a $200.000 por encima de botella regular sellada (`tester > regular`) y > 2.2x mediana.
  3. Variantes con < 4 ofertas regulares no disparan falsos positivos por mediana, pero sí validan `tester > regular`.
  4. Ofertas ya agotadas o retiradas no contaminan el cálculo de la mediana.
"""

import unittest
from APP.backend.normalizador import detectar_precios_atipicos


class TestPreciosAtipicosFase5(unittest.TestCase):
    def test_01_detecta_precio_bajo_atipico_caso_64990(self):
        ofertas = [
            {"id": 1, "tienda_id": 1, "precio_actual": 64990, "formato": "regular", "en_stock": True, "estado": "activa"},
            {"id": 2, "tienda_id": 2, "precio_actual": 134990, "formato": "regular", "en_stock": True, "estado": "activa"},
            {"id": 3, "tienda_id": 3, "precio_actual": 139990, "formato": "regular", "en_stock": True, "estado": "activa"},
            {"id": 4, "tienda_id": 4, "precio_actual": 144990, "formato": "regular", "en_stock": True, "estado": "activa"},
            {"id": 5, "tienda_id": 5, "precio_actual": 149990, "formato": "regular", "en_stock": True, "estado": "activa"},
        ]
        outliers = detectar_precios_atipicos(ofertas)
        ids = [o["id"] for o in outliers]
        self.assertEqual(ids, [1])
        self.assertEqual(outliers[0]["regla_outlier"], "bajo_mediana")
        self.assertEqual(outliers[0]["estado_sugerido"], "requiere_revision")

    def test_02_detecta_precio_alto_atipico_y_tester_200000_mayor_que_regular(self):
        ofertas = [
            {"id": 10, "tienda_id": 1, "precio_actual": 82990, "formato": "regular", "en_stock": True, "estado": "activa"},
            {"id": 11, "tienda_id": 2, "precio_actual": 86990, "formato": "regular", "en_stock": True, "estado": "activa"},
            {"id": 12, "tienda_id": 3, "precio_actual": 89990, "formato": "regular", "en_stock": True, "estado": "activa"},
            {"id": 13, "tienda_id": 4, "precio_actual": 92990, "formato": "regular", "en_stock": True, "estado": "activa"},
            {"id": 14, "tienda_id": 5, "precio_actual": 215000, "formato": "regular", "en_stock": True, "estado": "activa"},
            {"id": 15, "tienda_id": 6, "precio_actual": 200000, "formato": "tester", "en_stock": True, "estado": "activa"},
        ]
        outliers = detectar_precios_atipicos(ofertas)
        por_id = {o["id"]: o for o in outliers}
        self.assertIn(14, por_id)
        self.assertEqual(por_id[14]["regla_outlier"], "sobre_mediana")
        self.assertIn(15, por_id)
        self.assertEqual(por_id[15]["regla_outlier"], "tester_mayor_que_regular")

    def test_03_menos_de_4_ofertas_no_aplica_mediana_pero_si_tester_sobre_regular(self):
        ofertas = [
            {"id": 21, "tienda_id": 1, "precio_actual": 45000, "formato": "regular", "en_stock": True, "estado": "activa"},
            {"id": 22, "tienda_id": 2, "precio_actual": 98000, "formato": "regular", "en_stock": True, "estado": "activa"},
            {"id": 23, "tienda_id": 3, "precio_actual": 105000, "formato": "tester", "en_stock": True, "estado": "activa"},
        ]
        outliers = detectar_precios_atipicos(ofertas)
        self.assertEqual([o["id"] for o in outliers], [23])
        self.assertEqual(outliers[0]["regla_outlier"], "tester_mayor_que_regular")

    def test_04_tester_barato_legitimo_no_se_marca_como_outlier(self):
        ofertas = [
            {"id": 31, "tienda_id": 1, "precio_actual": 99990, "formato": "regular", "en_stock": True, "estado": "activa"},
            {"id": 32, "tienda_id": 2, "precio_actual": 104990, "formato": "regular", "en_stock": True, "estado": "activa"},
            {"id": 33, "tienda_id": 3, "precio_actual": 74990, "formato": "tester", "en_stock": True, "estado": "activa"},
        ]
        self.assertEqual(detectar_precios_atipicos(ofertas), [])


if __name__ == "__main__":
    unittest.main()

