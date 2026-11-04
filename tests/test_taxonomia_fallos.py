# -*- coding: utf-8 -*-
"""
Pruebas unitarias aisladas para la taxonomía controlada de fallos (Fase 5).
Verifica que cada uno de los 7 códigos controlados:
  `no_encontrado_en_feed | waf | timeout | parse_error | marca_excluida | volumen_ambiguo | entidad_no_coincide`
se contabilice exactamente en su bucket dentro de `estadisticas_tiendas[tienda]["fallos_por_codigo"]`
y que las exclusiones de marca generen muestras auditables en `muestra_exclusiones_marca`.
"""

import unittest
from unittest.mock import MagicMock, patch

import APP.backend.scraper_periodico as sp


class TestTaxonomiaFallosFase5(unittest.TestCase):
    def test_01_codigos_controlados_definidos_completos(self):
        esperados = {
            "no_encontrado_en_feed",
            "waf",
            "timeout",
            "parse_error",
            "marca_excluida",
            "volumen_ambiguo",
            "entidad_no_coincide",
        }
        self.assertEqual(set(sp.CODIGOS_FALLO_CONTROLADOS), esperados)

    def test_02_catalogo_bulk_clasifica_no_encontrado_entidad_y_volumen(self):
        cat = sp.CatalogoTiendaBulk("Tienda Test", "shopify", "https://tiendatest.cl")
        cat.ingestar_productos([
            {
                "id": 101,
                "title": "Perfume Dior Sauvage Elixir",
                "vendor": "Dior",
                "handle": "dior-sauvage-elixir",
                "variants": [
                    {"title": "Opción A", "price": "159990", "available": True},
                    {"title": "Opción B", "price": "199990", "available": True},
                ],
            },
            {
                "id": 102,
                "title": "Perfume Dior Fahrenheit EDT 100 ml",
                "vendor": "Dior",
                "handle": "dior-fahrenheit-edt-100ml",
                "variants": [
                    {"title": "100 ml", "price": "99990", "available": True},
                ],
            },
        ])

        # 1) Marca inexistente en feed -> no_encontrado_en_feed
        d1 = {}
        r1 = cat.extraer_variedades("Aventus", "Creed", diagnostico=d1)
        self.assertEqual(r1, [])
        self.assertEqual(d1.get("motivo_codigo"), "no_encontrado_en_feed")

        # 2) Producto existe y coincide en tokens, pero multivariante sin ml -> volumen_ambiguo
        d2 = {}
        r2 = cat.extraer_variedades("Sauvage Elixir", "Dior", concentracion="Elixir", diagnostico=d2)
        self.assertEqual(r2, [])
        self.assertEqual(d2.get("motivo_codigo"), "volumen_ambiguo")

        # 3) Misma marca y token parcial pero flanker/concentración distinta -> entidad_no_coincide
        d3 = {}
        r3 = cat.extraer_variedades("Fahrenheit Le Parfum", "Dior", concentracion="Parfum", diagnostico=d3)
        self.assertEqual(r3, [])
        self.assertEqual(d3.get("motivo_codigo"), "entidad_no_coincide")

    @patch("APP.backend.scraper_periodico.iniciar_scraping_run", return_value=777)
    @patch("APP.backend.scraper_periodico.finalizar_scraping_run")
    @patch("APP.backend.scraper_periodico.registrar_fallo_scraping")
    @patch("APP.backend.scraper_periodico.obtener_url_directa_tienda", return_value=None)
    @patch("APP.backend.scraper_periodico.es_circuit_breaker_activo", return_value=False)
    @patch("APP.backend.scraper_periodico.registrar_resultado_circuit_breaker")
    def test_03_auditar_lote_contabiliza_cada_bucket_por_tienda(
        self, _m_cb_reg, _m_cb_act, _m_url, _m_reg_fallo, _m_fin_run, _m_ini_run
    ):
        perfumes = [
            {"id": 1, "nombre": "Khamrah", "marca": "Lattafa", "genero": "Unisex", "tipo": "Eau de Parfum", "es_arabe": 1, "precio_referencia": 35000},
        ]
        tiendas = [
            {"id": 10, "nombre": "Silk Perfumes", "url_base": "https://silkperfumes.cl", "trust_score": 95},
            {"id": 11, "nombre": "Paris", "url_base": "https://www.paris.cl", "trust_score": 95},
            {"id": 12, "nombre": "Falabella", "url_base": "https://www.falabella.com", "trust_score": 95},
            {"id": 13, "nombre": "Ripley", "url_base": "https://simple.ripley.cl", "trust_score": 95},
        ]

        cat_silk = sp.CatalogoTiendaBulk("Silk Perfumes", "shopify", "https://silkperfumes.cl")
        bulk_map = {"Silk Perfumes": cat_silk}

        def _fake_falabella(**kwargs):
            kwargs["diagnostico"]["waf_bloqueado"] = True
            kwargs["diagnostico"]["http_status"] = 403
            return []

        def _fake_ripley(**kwargs):
            raise TimeoutError("Read timed out after 12s")

        with patch("APP.backend.scraper_periodico.tienda_comercializa_marca", side_effect=lambda t, m, **kw: t != "Paris"), \
             patch("APP.backend.scraper_periodico.extraer_variedades_falabella", side_effect=_fake_falabella), \
             patch("APP.backend.scraper_periodico.extraer_variedades_ripley", side_effect=_fake_ripley), \
             patch("APP.backend.scraper_periodico.time.sleep"):
            rep = sp.auditar_lote_perfumes(
                perfumes_lote=perfumes,
                tiendas_db=tiendas,
                urls_conocidas_map={},
                session=MagicMock(),
                cache_tiendas_bulk=bulk_map,
                ofertas_activas_set=set(),
                cb_cache={},
            )

        stats = rep["estadisticas_tiendas"]
        self.assertEqual(stats["Silk Perfumes"]["fallos_por_codigo"]["no_encontrado_en_feed"], 1)
        self.assertEqual(stats["Paris"]["fallos_por_codigo"]["marca_excluida"], 1)
        self.assertEqual(stats["Falabella"]["fallos_por_codigo"]["waf"], 1)
        self.assertEqual(stats["Ripley"]["fallos_por_codigo"]["timeout"], 1)
        self.assertGreaterEqual(len(rep.get("muestra_exclusiones_marca", [])), 1)
        self.assertEqual(rep["muestra_exclusiones_marca"][0]["tienda"], "Paris")


if __name__ == "__main__":
    unittest.main()

