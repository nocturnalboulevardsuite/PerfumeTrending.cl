import unittest
import sys, os
sys.path.insert(0, os.path.abspath("APP"))
sys.path.insert(0, os.path.abspath("."))
from backend.database import obtener_precios_actuales

class TestSortingAndVols(unittest.TestCase):
    def test_bleu_de_chanel_stock_first(self):
        precios = obtener_precios_actuales(1)
        self.assertTrue(len(precios) > 0)
        
        # Test 100ml filter
        vols_100 = [t for t in precios if int(round(float(t.get('volumen_ml') or 100))) == 100]
        self.assertEqual(len(vols_100), 3) # Paris, Falabella, Ripley
        
        # Sort key: stock first, then price
        sorted_vols = sorted(
            vols_100,
            key=lambda x: (0 if bool(x.get('en_stock', True)) else 1, x.get('precio_actual', 0) if x.get('precio_actual', 0) > 0 else 999999999)
        )
        
        # The first item MUST be in stock
        self.assertTrue(sorted_vols[0]['en_stock'])
        
        # Verify all in-stock items appear before any out-of-stock items
        seen_out = False
        for item in sorted_vols:
            if not item.get('en_stock', True):
                seen_out = True
            elif seen_out:
                self.fail(f"In-stock item {item['tienda_nombre']} found after out-of-stock item!")

    def test_sort_order_all_perfume_2(self):
        precios = obtener_precios_actuales(2)
        sorted_precios = sorted(
            precios,
            key=lambda x: (0 if bool(x.get('en_stock', True)) else 1, x.get('precio_actual', 0) if x.get('precio_actual', 0) > 0 else 999999999)
        )
        
        # Verify all en_stock=True come before any en_stock=False
        seen_out_of_stock = False
        for p in sorted_precios:
            if not p.get('en_stock', True):
                seen_out_of_stock = True
            if seen_out_of_stock:
                self.assertFalse(p.get('en_stock', True), "In-stock item found after out-of-stock item!")

    def test_obtener_catalogo_real_price(self):
        from backend.database import obtener_catalogo
        catalogo = obtener_catalogo()
        self.assertTrue(len(catalogo) > 0)
        bleu = next((p for p in catalogo if p['id'] == 1), None)
        self.assertIsNotNone(bleu)
        precios_bleu = obtener_precios_actuales(1)
        esperado_min = min(
            p['precio_actual']
            for p in precios_bleu
            if p.get('en_stock') and p.get('formato', 'regular') != 'tester' and (p.get('volumen_ml') or 100) >= 25
        )
        self.assertEqual(bleu['mejor_precio'], esperado_min)

if __name__ == '__main__':
    unittest.main()
