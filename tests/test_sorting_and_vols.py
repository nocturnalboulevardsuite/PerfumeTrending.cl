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
        candidatos_frescos = [
            p['precio_actual']
            for p in precios_bleu
            if p.get('en_stock')
            and p.get('formato', 'regular') != 'tester'
            and (p.get('volumen_ml') or 100) >= 25
            and not p.get('excluida_mejor_precio')
        ]
        esperado_min = min(candidatos_frescos) if candidatos_frescos else None
        self.assertEqual(bleu['mejor_precio'], esperado_min)

    # - ¿Qué hace este test?:
    #   Verifica que la normalización diacrítica con unicodedata funcione correctamente
    #   y que buscar sin tildes (ej. 'chloe') encuentre marcas o perfumes con tildes ('Chloé').
    def test_busqueda_insensible_a_tildes(self):
        """Verifica que la normalización de búsqueda soporte tildes y diacríticos transparentemente."""
        from backend.database import normalizar_texto_busqueda, obtener_catalogo
        self.assertEqual(normalizar_texto_busqueda("Chloé Nomade"), "chloe nomade")
        self.assertEqual(normalizar_texto_busqueda("Ramón Monegal Flamenco"), "ramon monegal flamenco")
        res_chloe = obtener_catalogo(busqueda="chloe")
        if res_chloe:
            self.assertTrue(any("chlo" in normalizar_texto_busqueda(p.get("marca") or "") or "chlo" in normalizar_texto_busqueda(p.get("nombre") or "") for p in res_chloe))

    # - ¿Qué hace este test?:
    #   Verifica que ordenar el catálogo por precio en una vista no altere ni mute
    #   el orden base por ID del catálogo maestro almacenado en memoria RAM.
    def test_inmutabilidad_catalogo_master(self):
        """Verifica que ordenar el catálogo por precio en una vista no altere el orden base del catálogo."""
        from backend.database import obtener_catalogo
        cat_por_precio = obtener_catalogo(orden="precio_asc")
        cat_por_id = obtener_catalogo(orden="id_asc")
        self.assertEqual(len(cat_por_precio), len(cat_por_id))
        ids = [p["id"] for p in cat_por_id[:10]]
        self.assertEqual(ids, sorted(ids))

    # - ¿Qué hace este test?:
    #   Verifica que obtener_remates_reales retorne los campos esperados por la UI
    #   y comprueba que la segunda consulta se resuelva en microsegundos (<0.05s) mediante caché RAM.
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


class TestResolucionEstrictaVolumenFase3(unittest.TestCase):
    # - ¿Qué hace esta suite de tests?:
    #   Verifica que ningún extractor ni helper invente 100 ml por defecto ante títulos sin volumen
    #   (como 'Default Title' en Shopify), preserve multivariantes reales y rechace contradicciones.

    def test_extraer_volumen_ml_opcional_no_inventa_100(self):
        from backend.normalizador import extraer_volumen_ml, extraer_volumen_ml_opcional

        self.assertIsNone(extraer_volumen_ml_opcional("Default Title"))
        self.assertIsNone(extraer_volumen_ml_opcional("Bleu de Chanel Eau de Parfum Vaporizador"))
        self.assertEqual(extraer_volumen_ml_opcional("Perfume X 50 ml"), 50)
        # Retrocompatibilidad explícita de extraer_volumen_ml cuando se pide default
        self.assertEqual(extraer_volumen_ml("Default Title", default=100), 100)

    def test_resolver_volumen_slug_50ml(self):
        from backend.normalizador import resolver_volumen_oferta

        vol = resolver_volumen_oferta(
            titulo_variante="Default Title",
            titulo_producto="Perfume Emporio Armani Stronger With You PowerFully EDP Hombre",
            url_slug="https://mundoaromas.cl/products/perfume-emporio-armani-stronger-with-you-powerfully-edp-50-ml-hombre",
            volumen_ml_defecto=100,
            n_variantes_producto=1,
            es_tester=False,
        )
        self.assertEqual(vol, 50)

    def test_resolver_volumen_sin_volumen_multivariante_retorna_none(self):
        from backend.normalizador import resolver_volumen_oferta

        vol = resolver_volumen_oferta(
            titulo_variante="Opción A",
            titulo_producto="Perfume Sauvage Eau de Parfum",
            url_slug="https://tienda.cl/products/sauvage-edp",
            volumen_ml_defecto=100,
            n_variantes_producto=3,
            es_tester=False,
        )
        self.assertIsNone(vol)

    def test_resolver_volumen_univariante_con_default_30_y_sin_default(self):
        from backend.normalizador import resolver_volumen_oferta

        vol_30 = resolver_volumen_oferta(
            titulo_variante="Default Title",
            titulo_producto="Perfume Libre Eau de Parfum",
            url_slug="https://tienda.cl/products/libre-edp",
            volumen_ml_defecto=30,
            n_variantes_producto=1,
            es_tester=False,
        )
        self.assertEqual(vol_30, 30)

        vol_none = resolver_volumen_oferta(
            titulo_variante="Default Title",
            titulo_producto="Perfume Libre Eau de Parfum",
            url_slug="https://tienda.cl/products/libre-edp",
            volumen_ml_defecto=None,
            n_variantes_producto=1,
            es_tester=False,
        )
        self.assertIsNone(vol_none)

    def test_regresion_armani_mundo_aromas_50ml_no_cae_en_100ml(self):
        from backend.scraper_periodico import CatalogoTiendaBulk

        cat = CatalogoTiendaBulk("Mundo Aromas", "shopify", "https://mundoaromas.cl")
        cat.ingestar_productos([
            {
                "title": "Perfume Emporio Armani Stronger With You PowerFully EDP 50 Ml Hombre",
                "vendor": "Emporio Armani",
                "handle": "perfume-emporio-armani-stronger-with-you-powerfully-edp-50-ml-hombre",
                "images": [],
                "variants": [
                    {
                        "title": "Default Title",
                        "price": "82990",
                        "compare_at_price": "165980",
                        "available": True,
                    }
                ],
            },
            # Producto multivariante legítimo bajo URL con -100ml: debe preservar 50 y 100
            {
                "title": "Bleu de Chanel Eau de Parfum",
                "vendor": "Chanel",
                "handle": "bleu-de-chanel-edp-100ml",
                "images": [],
                "variants": [
                    {"title": "50 ml", "price": "129990", "compare_at_price": None, "available": True},
                    {"title": "100 ml", "price": "169990", "compare_at_price": None, "available": True},
                ],
            },
            # Producto univariante contradictorio (título 100ml vs slug 50-ml): debe descartarse
            {
                "title": "Sauvage Eau de Parfum 100 ml",
                "vendor": "Dior",
                "handle": "sauvage-eau-de-parfum-50-ml",
                "images": [],
                "variants": [
                    {"title": "Default Title", "price": "99990", "compare_at_price": None, "available": True},
                ],
            },
        ])

        res_armani = cat.extraer_variedades(
            perfume_nombre="Stronger With You Powerfully",
            marca="Giorgio Armani",
            volumen_ml_defecto=100,
            concentracion="Eau de Parfum",
        )
        self.assertEqual(len(res_armani), 1)
        self.assertEqual(res_armani[0]["volumen_ml"], 50)
        self.assertEqual(res_armani[0]["precio_actual"], 82990)

        res_bleu = cat.extraer_variedades(
            perfume_nombre="Bleu de Chanel",
            marca="Chanel",
            volumen_ml_defecto=100,
            concentracion="Eau de Parfum",
        )
        self.assertEqual(sorted(v["volumen_ml"] for v in res_bleu), [50, 100])

        diag = {}
        res_contradictorio = cat.extraer_variedades(
            perfume_nombre="Sauvage",
            marca="Dior",
            volumen_ml_defecto=100,
            concentracion="Eau de Parfum",
            diagnostico=diag,
        )
        self.assertEqual(res_contradictorio, [])
        self.assertGreaterEqual(diag.get("exclusiones_volumen_ambiguo", 0), 1)


if __name__ == '__main__':
    unittest.main()
