# -*- coding: utf-8 -*-
"""
Pruebas unitarias aisladas para Observabilidad CI y Auditoría 2-Strikes (Fase 6).
"""

# Importación de librería estándar o dependencia externa (unittest)
import unittest
# Importación de componentes (STRIKE_1_TAG, STRIKE_2_TAG, clasificar_respuesta_http, decidir_accion_histeresis) desde el módulo 'APP.backend.auditoria_enlaces'
from APP.backend.auditoria_enlaces import (
    STRIKE_1_TAG,
    STRIKE_2_TAG,
    clasificar_respuesta_http,
    decidir_accion_histeresis,
)
# Importación de componentes (evaluar_salud_tienda, generar_markdown_y_alertas) desde el módulo 'APP.backend.mantenimiento.resumen_salud_ci'
from APP.backend.mantenimiento.resumen_salud_ci import (
    evaluar_salud_tienda,
    generar_markdown_y_alertas,
)


# Definición de clase 'TestAuditoriaYSaludCIFase6' que modela la estructura y lógica del componente
class TestAuditoriaYSaludCIFase6(unittest.TestCase):
    # Definición de función 'test_01_histeresis_dos_strikes_y_recuperacion' sin parámetros externos
    def test_01_histeresis_dos_strikes_y_recuperacion(self):
        # 1er 404 -> solo marca STRIKE 1, no apaga stock
        d1 = decidir_accion_histeresis("DEAD_404", "HTTP 404", None)
        # Aserción de prueba unitaria: self.assertEqual(d1['accion'], 'marcar_strike_1')
        self.assertEqual(d1["accion"], "marcar_strike_1")
        # Aserción de prueba unitaria: self.assertNotIn('en_stock', d1['payload'])
        self.assertNotIn("en_stock", d1["payload"])
        # Aserción de prueba unitaria: self.assertIn(STRIKE_1_TAG, d1['payload']['ultimo_er...
        self.assertIn(STRIKE_1_TAG, d1["payload"]["ultimo_error"])

        # 2do 404 consecutivo -> desactiva oferta
        d2 = decidir_accion_histeresis("DEAD_404", "HTTP 404", d1["payload"]["ultimo_error"])
        # Aserción de prueba unitaria: self.assertEqual(d2['accion'], 'desactivar_strike_2')
        self.assertEqual(d2["accion"], "desactivar_strike_2")
        # Aserción de prueba unitaria: self.assertFalse(d2['payload']['en_stock'])
        self.assertFalse(d2["payload"]["en_stock"])
        # Aserción de prueba unitaria: self.assertEqual(d2['payload']['estado'], 'requiere_...
        self.assertEqual(d2["payload"]["estado"], "requiere_revision")
        # Aserción de prueba unitaria: self.assertIn(STRIKE_2_TAG, d2['payload']['ultimo_er...
        self.assertIn(STRIKE_2_TAG, d2["payload"]["ultimo_error"])

        # Si tras Strike 1 vuelve a dar 200 OK -> limpia el strike
        d_rec = decidir_accion_histeresis("OK_200", "OK", d1["payload"]["ultimo_error"])
        # Aserción de prueba unitaria: self.assertEqual(d_rec['accion'], 'limpiar_strike')
        self.assertEqual(d_rec["accion"], "limpiar_strike")
        # Aserción de prueba unitaria: self.assertIsNone(d_rec['payload']['ultimo_error'])
        self.assertIsNone(d_rec["payload"]["ultimo_error"])

    # Definición de función 'test_02_inmunidad_ante_waf_403_429_y_timeout' sin parámetros externos
    def test_02_inmunidad_ante_waf_403_429_y_timeout(self):
        # Asignamos 'err_prev' con f'{STRIKE_1_TAG} DEAD_404: previo'
        err_prev = f"{STRIKE_1_TAG} DEAD_404: previo"
        # Recorremos iterativamente cada 'codigo' en ('WAF_403', 'RATE_LIMIT_429', 'TIMEOUT', '...
        for codigo in ("WAF_403", "RATE_LIMIT_429", "TIMEOUT", "SERVER_ERR_503"):
            # Asignamos 'dec' con decidir_accion_histeresis(codigo, 'Transit...
            dec = decidir_accion_histeresis(codigo, "Transitorio", err_prev)
            # Aserción de prueba unitaria: self.assertEqual(dec['accion'], 'ignorar_transitorio')
            self.assertEqual(dec["accion"], "ignorar_transitorio")
            # Aserción de prueba unitaria: self.assertEqual(dec['payload'], {})
            self.assertEqual(dec["payload"], {})

    # Definición de función 'test_03_clasificar_respuesta_redirect_home_y_soft_404' sin parámetros externos
    def test_03_clasificar_respuesta_redirect_home_y_soft_404(self):
        # Asignamos '(st_home, _)' con clasificar_respuesta_http('https://tiendat...
        st_home, _ = clasificar_respuesta_http(
            "https://tiendatest.cl/products/perfume-agotado",
            200,
            "https://tiendatest.cl/",
            "<html>Home</html>",
        )
        # Aserción de prueba unitaria: self.assertEqual(st_home, 'REDIRECT_HOME')
        self.assertEqual(st_home, "REDIRECT_HOME")

        # Asignamos '(st_s404, _)' con clasificar_respuesta_http('https://tiendat...
        st_s404, _ = clasificar_respuesta_http(
            "https://tiendatest.cl/products/perfume-eliminado",
            200,
            "https://tiendatest.cl/products/perfume-eliminado",
            "<html><h1>Página no encontrada</h1></html>",
        )
        # Aserción de prueba unitaria: self.assertEqual(st_s404, 'SOFT_404')
        self.assertEqual(st_s404, "SOFT_404")

    # Definición de función 'test_04_resumen_salud_ci_emite_warning_bajo_20_pct_sin_contar_ausentes' sin parámetros externos
    def test_04_resumen_salud_ci_emite_warning_bajo_20_pct_sin_contar_ausentes(self):
        # Tienda sana: 100 consultas, 80 ausentes en feed, 18 éxitos de 20 efectivos (90%) -> sin alarma
        ev_ok = evaluar_salud_tienda(
            "Silk Perfumes",
            {
                "consultas": 100,
                "exitos_en_vivo": 18,
                "bloqueos_waf": 0,
                "fallos_por_codigo": {"no_encontrado_en_feed": 80, "entidad_no_coincide": 2},
            },
        )
        # Aserción de prueba unitaria: self.assertFalse(ev_ok['alarma_baja_salud'])
        self.assertFalse(ev_ok["alarma_baja_salud"])
        # Aserción de prueba unitaria: self.assertEqual(ev_ok['pct_exito_efectivo'], 90.0)
        self.assertEqual(ev_ok["pct_exito_efectivo"], 90.0)

        # Tienda bloqueada: 50 consultas, 0 éxitos, 50 WAF -> 0% < 20% -> dispara ::warning::
        rep = {
            "metadata": {"estado": "EXITOSO", "duracion_segundos": 42},
            "metricas": {"perfumes_auditados": 50, "total_perfumes_catalogo": 800, "precios_actualizados": 18},
            "estadisticas_tiendas": {
                "Silk Perfumes": {
                    "consultas": 100,
                    "exitos_en_vivo": 18,
                    "bloqueos_waf": 0,
                    "fallos_por_codigo": {"no_encontrado_en_feed": 80},
                },
                "Paris": {
                    "consultas": 50,
                    "exitos_en_vivo": 0,
                    "bloqueos_waf": 50,
                    "fallos_por_codigo": {"waf": 50},
                },
            },
        }
        # Asignamos '(md, warnings)' con generar_markdown_y_alertas(rep, shard_labe...
        md, warnings = generar_markdown_y_alertas(rep, shard_label="1")
        # Aserción de prueba unitaria: self.assertIn('Salud del Scraper Nocturno (Shard 1)'...
        self.assertIn("Salud del Scraper Nocturno (Shard 1)", md)
        # Aserción de prueba unitaria: self.assertEqual(len(warnings), 1)
        self.assertEqual(len(warnings), 1)
        # Aserción de prueba unitaria: self.assertTrue(warnings[0].startswith('::warning ti...
        self.assertTrue(warnings[0].startswith("::warning title=Salud baja en Paris"))


# Punto de entrada principal cuando el script se invoca directamente desde consola
if __name__ == "__main__":
    # Ejecutamos instrucción: unittest.main()
    unittest.main()

