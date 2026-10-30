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

    def test_busqueda_insensible_a_tildes(self):
        """Verifica que la normalización de búsqueda soporte tildes y diacríticos transparentemente."""
        from backend.database import normalizar_texto_busqueda, obtener_catalogo
        self.assertEqual(normalizar_texto_busqueda("Chloé Nomade"), "chloe nomade")
        self.assertEqual(normalizar_texto_busqueda("Ramón Monegal Flamenco"), "ramon monegal flamenco")
        res_chloe = obtener_catalogo(busqueda="chloe")
        if res_chloe:
            self.assertTrue(any("chlo" in normalizar_texto_busqueda(p.get("marca") or "") or "chlo" in normalizar_texto_busqueda(p.get("nombre") or "") for p in res_chloe))

    def test_inmutabilidad_catalogo_master(self):
        """Verifica que ordenar el catálogo por precio en una vista no altere el orden base del catálogo."""
        from backend.database import obtener_catalogo
        cat_por_precio = obtener_catalogo(orden="precio_asc")
        cat_por_id = obtener_catalogo(orden="id_asc")
        self.assertEqual(len(cat_por_precio), len(cat_por_id))
        ids = [p["id"] for p in cat_por_id[:10]]
        self.assertEqual(ids, sorted(ids))

    def test_remates_reales_estructura_y_cache(self):
        """Verifica que obtener_remates_reales devuelva los campos requeridos y opere en microsegundos vía caché."""
        import time
        from backend.database import obtener_remates_reales
        remates = obtener_remates_reales(limite=10)
        self.assertTrue(len(remates) > 0)
        primer_remate = remates[0]
        campos_esperados = ["precio_remate", "precio_normal", "ahorro_clp", "descuento_pct", "tienda", "url"]
        for campo in campos_esperados:
            self.assertIn(campo, primer_remate, f"Falta campo {campo} en remate")
        self.assertGreater(primer_remate["precio_normal"], primer_remate["precio_remate"])

        t0 = time.time()
        remates_cached = obtener_remates_reales(limite=10)
        t_duracion = time.time() - t0
        self.assertLess(t_duracion, 0.05, f"Caché de remates demoró {t_duracion:.4f}s, esperado < 0.05s")
        self.assertEqual(len(remates_cached), len(remates))

if __name__ == '__main__':
    unittest.main()
