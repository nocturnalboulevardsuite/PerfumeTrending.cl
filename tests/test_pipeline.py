"""
PerfumeTrending.cl — Suite de Pruebas Automatizadas (CI/CD Quality Gate)
========================================================================
Pruebas de integración y validación estructural de la capa de persistencia,
esquema DDL, catálogo maestro JSON y pipeline ETL de auditoría.
"""

import json
import os
import sqlite3
import sys
import unittest

# Asegurar importación de backend y módulos del proyecto
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.database import (
    init_db,
    obtener_catalogo,
    obtener_detalle_perfume,
    obtener_precios_actuales,
    obtener_historico_precios,
    obtener_tiendas_trust,
    auditar_tienda_por_url,
    tienda_comercializa_marca,
    obtener_url_directa_tienda
)
from backend.scraper_periodico import obtener_ultimo_reporte_scraping
from backend.scraper_autonomo import obtener_ultimo_reporte_descubrimiento
from backend.normalizador import (
    extraer_volumen_ml,
    extraer_concentracion,
    limpiar_nombre_perfume,
    es_arabe,
    es_producto_perfume_valido
)


class TestDataArchitecture(unittest.TestCase):
    """Pruebas de integridad estructural para DDL, JSON semilla y persistencia."""

    @classmethod
    def setUpClass(cls):
        """Inicializa y re-puebla la base de datos para asegurar un estado limpio."""
        init_db(force_reseed=True)

    def test_01_schema_sql_exists_and_is_valid(self):
        """Verifica que schema.sql existe y puede ejecutarse en una base de datos en memoria."""
        schema_path = os.path.join(BASE_DIR, "database", "schema.sql")
        self.assertTrue(os.path.exists(schema_path), "database/schema.sql debe existir")

        with open(schema_path, "r", encoding="utf-8") as f:
            ddl = f.read()

        mem_conn = sqlite3.connect(":memory:")
        try:
            mem_conn.executescript(ddl)
            cursor = mem_conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = {r[0] for r in cursor.fetchall()}
            self.assertIn("perfumes", tables)
            self.assertIn("tiendas", tables)
            self.assertIn("precios_registro", tables)
        finally:
            mem_conn.close()

    def test_02_seed_catalogo_json_schema(self):
        """Valida que seed_catalogo.json cumple con la estructura esperada y tipos correctos."""
        seed_path = os.path.join(BASE_DIR, "database", "seed_catalogo.json")
        self.assertTrue(os.path.exists(seed_path), "database/seed_catalogo.json debe existir")

        with open(seed_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertIn("tiendas", data)
        self.assertIn("perfumes", data)
        self.assertGreaterEqual(len(data["tiendas"]), 5, "Debe haber al menos 5 tiendas registradas")
        self.assertGreaterEqual(len(data["perfumes"]), 10, "Debe haber al menos 10 perfumes en catálogo")

        # Validar tiendas
        for t in data["tiendas"]:
            self.assertIn("nombre", t)
            self.assertIn("url_base", t)
            self.assertIn("trust_score", t)
            self.assertGreaterEqual(t["trust_score"], 0)
            self.assertLessEqual(t["trust_score"], 100)

        # Validar perfumes
        for p in data["perfumes"]:
            self.assertIn("id", p)
            self.assertIn("nombre", p)
            self.assertIn("marca", p)
            self.assertIn("precio_referencia", p)
            self.assertIn("enlaces_tiendas", p)
            self.assertGreater(p["precio_referencia"], 0)

    def test_03_catalogo_queries(self):
        """Verifica las consultas principales del catálogo."""
        perfumes = obtener_catalogo()
        self.assertGreaterEqual(len(perfumes), 12)

        # Filtro de búsqueda por texto
        busqueda = obtener_catalogo(busqueda="Sauvage")
        self.assertGreaterEqual(len(busqueda), 1)
        self.assertEqual(busqueda[0]["marca"], "Dior")

        # Filtro por perfumes árabes
        arabes = obtener_catalogo(categoria="arabes")
        self.assertGreaterEqual(len(arabes), 3)
        for p in arabes:
            self.assertEqual(p["es_arabe"], 1)

    def test_04_trust_score_engine(self):
        """Valida el motor antifraude de Trust Score y auditoría por URL."""
        tiendas = obtener_tiendas_trust()
        self.assertGreaterEqual(len(tiendas), 5)
        # Orden descendente por score
        scores = [t["trust_score"] for t in tiendas]
        self.assertEqual(scores, sorted(scores, reverse=True))

        # Auditoría de comercio conocido (Falabella)
        audit_falabella = auditar_tienda_por_url("https://www.falabella.com/producto/123")
        self.assertIsNotNone(audit_falabella)
        self.assertTrue(audit_falabella["es_conocida"])
        self.assertGreaterEqual(audit_falabella["score"], 90)

        # Auditoría de dominio externo desconocido
        audit_externo = auditar_tienda_por_url("https://perfumes-ganga-chile.biz")
        self.assertIsNotNone(audit_externo)
        self.assertFalse(audit_externo["es_conocida"])
        self.assertLess(audit_externo["score"], 70)

    def test_05_precios_y_series_temporales(self):
        """Valida la consistencia de precios actuales e histórico para gráficos."""
        # Tomar el primer perfume (Bleu de Chanel)
        precios = obtener_precios_actuales(1)
        self.assertGreaterEqual(len(precios), 2, "Bleu de Chanel debe tener al menos 2 tiendas")
        for pr in precios:
            self.assertGreater(pr["precio_actual"], 0)
            self.assertTrue(pr["url_producto"].startswith("http"))
            self.assertNotIn("/search", pr["url_producto"])

        historico = obtener_historico_precios(1)
        self.assertGreater(len(historico), 5, "Debe registrar serie histórica para evolución")

    def test_06_etl_scraper_audit_report(self):
        """Verifica que el reporte generado por el scraper existe y contiene telemetría válida."""
        reporte = obtener_ultimo_reporte_scraping()
        self.assertIsNotNone(reporte, "Debe existir data/reportes/ultimo_scraping.json")
        self.assertIn("metadata", reporte)
        self.assertIn("metricas", reporte)
        self.assertIn("estadisticas_tiendas", reporte)
        self.assertEqual(reporte["metadata"]["estado"], "EXITOSO")
        self.assertGreater(reporte["metricas"]["precios_actualizados"], 0)

    def test_07_normalizador_variantes(self):
        """Valida las reglas de extracción NLP y regex para tamaños, concentración y marcas."""
        self.assertEqual(extraer_volumen_ml("Dior Sauvage EDP 60ml Hombre"), 60)
        self.assertEqual(extraer_volumen_ml("Bleu de Chanel 3.4 oz"), 100)
        self.assertEqual(extraer_volumen_ml("Versace Eros 200 ml"), 200)
        self.assertEqual(extraer_concentracion("Dior Sauvage Elixir Spray"), "Elixir")
        self.assertEqual(extraer_concentracion("YSL Libre Eau de Parfum Intense"), "Eau de Parfum Intense")
        self.assertEqual(extraer_concentracion("Acqua Di Gio EDT"), "Eau de Toilette")

        # Limpieza de títulos de e-commerce
        limpio = limpiar_nombre_perfume("Perfume Lattafa Khamrah Unisex Edp 100 Ml Oferta", "Lattafa")
        self.assertEqual(limpio, "Khamrah")

        # Detección de casas árabes y filtros de exclusión
        self.assertTrue(es_arabe("Lattafa", "Khamrah"))
        self.assertFalse(es_arabe("Chanel", "Bleu de Chanel"))
        self.assertFalse(es_producto_perfume_valido("Desodorante en Barra Dior Sauvage 75g"))
        self.assertTrue(es_producto_perfume_valido("Dior Sauvage Eau de Parfum 100ml"))

    def test_08_calculo_precio_por_ml(self):
        """Valida que la base de datos entregue el volumen y calcule el precio por ml."""
        precios = obtener_precios_actuales(1)
        self.assertGreaterEqual(len(precios), 1)
        for p in precios:
            self.assertIn("volumen_ml", p)
            self.assertIn("precio_por_ml", p)
            self.assertGreater(p["volumen_ml"], 0)
            self.assertGreater(p["precio_por_ml"], 0)
            # Validación matemática: $/ml = precio / volumen
            esperado = round(p["precio_actual"] / p["volumen_ml"])
            self.assertAlmostEqual(p["precio_por_ml"], esperado, delta=2)

    def test_09_reporte_descubrimiento_autonomo(self):
        """Verifica la existencia y validez del reporte del crawler autónomo."""
        reporte = obtener_ultimo_reporte_descubrimiento()
        self.assertIsNotNone(reporte, "Debe existir data/reportes/ultimo_descubrimiento.json")
        self.assertIn("metadata", reporte)
        self.assertIn("metricas", reporte)
        self.assertIn("total_productos_analizados", reporte["metricas"])
        self.assertIn("nuevos_perfumes_descubiertos", reporte["metricas"])
        self.assertEqual(reporte["metadata"]["estado"], "EXITOSO")


if __name__ == "__main__":
    unittest.main(verbosity=2)
