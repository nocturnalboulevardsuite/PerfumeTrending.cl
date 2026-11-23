# -*- coding: utf-8 -*-
"""
Pruebas unitarias aisladas para la taxonomía controlada de fallos (Fase 5).
Verifica que cada uno de los 7 códigos controlados:
  `no_encontrado_en_feed | waf | timeout | parse_error | marca_excluida | volumen_ambiguo | entidad_no_coincide`
se contabilice exactamente en su bucket dentro de `estadisticas_tiendas[tienda]["fallos_por_codigo"]`
y que las exclusiones de marca generen muestras auditables en `muestra_exclusiones_marca`.
"""

# Importación de librería estándar o dependencia externa (unittest)
import unittest
# Importación de componentes (MagicMock, patch) desde el módulo 'unittest.mock'
from unittest.mock import MagicMock, patch

# Importación de librería estándar o dependencia externa (APP.backend.scraper_periodico)
import APP.backend.scraper_periodico as sp


# Definición de clase 'TestTaxonomiaFallosFase5' que modela la estructura y lógica del componente
class TestTaxonomiaFallosFase5(unittest.TestCase):
    # Definición de función 'test_01_codigos_controlados_definidos_completos' sin parámetros externos
    def test_01_codigos_controlados_definidos_completos(self):
        # Asignamos 'esperados' con {'no_encontrado_en_feed', 'waf', 'timeout'...
        esperados = {
            "no_encontrado_en_feed",
            "waf",
            "timeout",
            "parse_error",
            "marca_excluida",
            "volumen_ambiguo",
            "entidad_no_coincide",
        }
        # Aserción de prueba unitaria: self.assertEqual(set(sp.CODIGOS_FALLO_CONTROLADOS), ...
        self.assertEqual(set(sp.CODIGOS_FALLO_CONTROLADOS), esperados)

    # Definición de función 'test_02_catalogo_bulk_clasifica_no_encontrado_entidad_y_volumen' sin parámetros externos
    def test_02_catalogo_bulk_clasifica_no_encontrado_entidad_y_volumen(self):
        # Asignamos 'cat' con sp.CatalogoTiendaBulk('Tienda Test', 'shop...
        cat = sp.CatalogoTiendaBulk("Tienda Test", "shopify", "https://tiendatest.cl")
        # Ejecutamos instrucción: cat.ingestar_productos([{'id': 101, 'title': 'Perfum...
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
        # Asignamos 'r1' con cat.extraer_variedades('Aventus', 'Creed',...
        r1 = cat.extraer_variedades("Aventus", "Creed", diagnostico=d1)
        # Aserción de prueba unitaria: self.assertEqual(r1, [])
        self.assertEqual(r1, [])
        # Aserción de prueba unitaria: self.assertEqual(d1.get('motivo_codigo'), 'no_encont...
        self.assertEqual(d1.get("motivo_codigo"), "no_encontrado_en_feed")

        # 2) Producto existe y coincide en tokens, pero multivariante sin ml -> volumen_ambiguo
        d2 = {}
        # Asignamos 'r2' con cat.extraer_variedades('Sauvage Elixir', '...
        r2 = cat.extraer_variedades("Sauvage Elixir", "Dior", concentracion="Elixir", diagnostico=d2)
        # Aserción de prueba unitaria: self.assertEqual(r2, [])
        self.assertEqual(r2, [])
        # Aserción de prueba unitaria: self.assertEqual(d2.get('motivo_codigo'), 'volumen_a...
        self.assertEqual(d2.get("motivo_codigo"), "volumen_ambiguo")

        # 3) Misma marca y token parcial pero flanker/concentración distinta -> entidad_no_coincide
        d3 = {}
        # Asignamos 'r3' con cat.extraer_variedades('Fahrenheit Le Parf...
        r3 = cat.extraer_variedades("Fahrenheit Le Parfum", "Dior", concentracion="Parfum", diagnostico=d3)
        # Aserción de prueba unitaria: self.assertEqual(r3, [])
        self.assertEqual(r3, [])
        # Aserción de prueba unitaria: self.assertEqual(d3.get('motivo_codigo'), 'entidad_n...
        self.assertEqual(d3.get("motivo_codigo"), "entidad_no_coincide")

    # Definición de función 'test_03_auditar_lote_contabiliza_cada_bucket_por_tienda' (parámetros: _m_cb_reg, _m_cb_act, _m_url, _m_reg_fallo, ...)
    @patch("APP.backend.scraper_periodico.iniciar_scraping_run", return_value=777)
    @patch("APP.backend.scraper_periodico.finalizar_scraping_run")
    @patch("APP.backend.scraper_periodico.registrar_fallo_scraping")
    @patch("APP.backend.scraper_periodico.obtener_url_directa_tienda", return_value=None)
    @patch("APP.backend.scraper_periodico.es_circuit_breaker_activo", return_value=False)
    @patch("APP.backend.scraper_periodico.registrar_resultado_circuit_breaker")
    def test_03_auditar_lote_contabiliza_cada_bucket_por_tienda(
        self, _m_cb_reg, _m_cb_act, _m_url, _m_reg_fallo, _m_fin_run, _m_ini_run
    ):
        # Asignamos 'perfumes' con [{'id': 1, 'nombre': 'Khamrah', 'marca': '...
        perfumes = [
            # Configuración de elemento #1 (id='1', nombre='Khamrah', marca='Lattafa')
            {"id": 1, "nombre": "Khamrah", "marca": "Lattafa", "genero": "Unisex", "tipo": "Eau de Parfum", "es_arabe": 1, "precio_referencia": 35000},
        ]
        # Asignamos 'tiendas' con [{'id': 10, 'nombre': 'Silk Perfumes', 'ur...
        tiendas = [
            # Configuración de elemento #1 (id='10', nombre='Silk Perfumes')
            {"id": 10, "nombre": "Silk Perfumes", "url_base": "https://silkperfumes.cl", "trust_score": 95},
            # Configuración de elemento #2 (id='11', nombre='Paris')
            {"id": 11, "nombre": "Paris", "url_base": "https://www.paris.cl", "trust_score": 95},
            # Configuración de elemento #3 (id='12', nombre='Falabella')
            {"id": 12, "nombre": "Falabella", "url_base": "https://www.falabella.com", "trust_score": 95},
            # Configuración de elemento #4 (id='13', nombre='Ripley')
            {"id": 13, "nombre": "Ripley", "url_base": "https://simple.ripley.cl", "trust_score": 95},
        ]

        # Asignamos 'cat_silk' con sp.CatalogoTiendaBulk('Silk Perfumes', 'sh...
        cat_silk = sp.CatalogoTiendaBulk("Silk Perfumes", "shopify", "https://silkperfumes.cl")
        # Asignamos 'bulk_map' con {'Silk Perfumes': cat_silk}
        bulk_map = {"Silk Perfumes": cat_silk}

        # Definición de función '_fake_falabella' sin parámetros externos
        def _fake_falabella(**kwargs):
            # Asignamos 'kwargs['diagnostico']['waf_bloqu...' con True
            kwargs["diagnostico"]["waf_bloqueado"] = True
            # Asignamos 'kwargs['diagnostico']['http_stat...' con 403
            kwargs["diagnostico"]["http_status"] = 403
            # Retornamos el resultado procesado ([])
            return []

        # Definición de función '_fake_ripley' sin parámetros externos
        def _fake_ripley(**kwargs):
            # Propagamos excepción explícita ante condición de error detectada
            raise TimeoutError("Read timed out after 12s")

        # Gestión automática de contexto y recursos para: patch('APP.backend.scraper_periodico.tienda_com...
        with patch("APP.backend.scraper_periodico.tienda_comercializa_marca", side_effect=lambda t, m, **kw: t != "Paris"), \
             patch("APP.backend.scraper_periodico.extraer_variedades_falabella", side_effect=_fake_falabella), \
             patch("APP.backend.scraper_periodico.extraer_variedades_ripley", side_effect=_fake_ripley), \
             patch("APP.backend.scraper_periodico.time.sleep"):
            # Asignamos 'rep' con sp.auditar_lote_perfumes(perfumes_lote=per...
            rep = sp.auditar_lote_perfumes(
                perfumes_lote=perfumes,
                tiendas_db=tiendas,
                urls_conocidas_map={},
                session=MagicMock(),
                cache_tiendas_bulk=bulk_map,
                ofertas_activas_set=set(),
                cb_cache={},
            )

        # Asignamos 'stats' con rep['estadisticas_tiendas']
        stats = rep["estadisticas_tiendas"]
        # Aserción de prueba unitaria: self.assertEqual(stats['Silk Perfumes']['fallos_por_...
        self.assertEqual(stats["Silk Perfumes"]["fallos_por_codigo"]["no_encontrado_en_feed"], 1)
        # Aserción de prueba unitaria: self.assertEqual(stats['Paris']['fallos_por_codigo']...
        self.assertEqual(stats["Paris"]["fallos_por_codigo"]["marca_excluida"], 1)
        # Aserción de prueba unitaria: self.assertEqual(stats['Falabella']['fallos_por_codi...
        self.assertEqual(stats["Falabella"]["fallos_por_codigo"]["waf"], 1)
        # Aserción de prueba unitaria: self.assertEqual(stats['Ripley']['fallos_por_codigo'...
        self.assertEqual(stats["Ripley"]["fallos_por_codigo"]["timeout"], 1)
        # Aserción de prueba unitaria: self.assertGreaterEqual(len(rep.get('muestra_exclusi...
        self.assertGreaterEqual(len(rep.get("muestra_exclusiones_marca", [])), 1)
        # Aserción de prueba unitaria: self.assertEqual(rep['muestra_exclusiones_marca'][0]...
        self.assertEqual(rep["muestra_exclusiones_marca"][0]["tienda"], "Paris")


# Punto de entrada principal cuando el script se invoca directamente desde consola
if __name__ == "__main__":
    # Ejecutamos instrucción: unittest.main()
    unittest.main()

