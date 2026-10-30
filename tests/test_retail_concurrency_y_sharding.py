"""
Tests unitarios para la optimización de Concurrencia en Retail Tradicional,
Poda Fina de Marcas No-Retail y Horizontal Sharding (50/50) en GitHub Actions.

Verifica:
1. Poda de marcas: Filtro estricto de perfumería árabe y marcas nicho/indie en Falabella, Paris, Ripley y DBS.
2. Partición matemática de Sharding: Disyunción absoluta y cobertura al 100% del catálogo.
3. Concurrencia de red (ThreadPoolExecutor): Ejecución concurrente segura en tiendas departamentales.
4. Resiliencia ante fallos parciales de red sin degradar el lote completo.
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

_app_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "APP"))
if _app_dir not in sys.path:
    sys.path.insert(0, _app_dir)

from backend.database import (
    MARCAS_NO_RETAIL_TRADICIONAL,
    tienda_comercializa_marca,
)
from backend.scraper_periodico import (
    auditar_lote_perfumes,
    guardar_reporte_auditoria,
)


class TestRetailConcurrencyYSharding(unittest.TestCase):

    def test_01_poda_marcas_retail_tradicional_vs_nicho(self):
        """Verifica que los grandes retailers no consulten marcas nicho o árabes pero sí marcas de diseñador."""
        grandes_almacenes = ["Falabella", "Paris", "Ripley"]
        retail_y_farmacias = ["Falabella", "Paris", "Ripley", "DBS Beauty Store"]
        especializadas = ["Silk Perfumes", "Elite Perfumes", "Al-Haramain Chile"]

        # Marcas tradicionales de diseñador -> DEBEN consultarse en grandes almacenes
        marcas_retail = ["Dior", "Chanel", "Versace", "Giorgio Armani", "Carolina Herrera", "Paco Rabanne"]
        for t in grandes_almacenes:
            for m in marcas_retail:
                self.assertTrue(
                    tienda_comercializa_marca(t, m),
                    f"Se esperaba que {t} comercialice la marca tradicional {m}",
                )

        # Marcas árabes -> NO deben consultarse en retail tradicional ni farmacias
        marcas_arabes = ["Lattafa", "Armaf", "Afnan", "Al Haramain", "Rasasi"]
        for t in retail_y_farmacias:
            for m in marcas_arabes:
                self.assertFalse(
                    tienda_comercializa_marca(t, m, es_arabe_flag=True),
                    f"Se esperaba que {t} omita la marca árabe {m}",
                )

        # Marcas nicho/indie/clon en MARCAS_NO_RETAIL_TRADICIONAL -> NO en retail, SÍ en especializadas
        muestras_nicho = ["Lorenzo Pazzaglia", "Argos", "Bon Parfumeur", "Mancera", "Montale", "Creed", "Xerjoff"]
        for m in muestras_nicho:
            self.assertIn(m.lower(), MARCAS_NO_RETAIL_TRADICIONAL)
            for t in retail_y_farmacias:
                self.assertFalse(
                    tienda_comercializa_marca(t, m),
                    f"{t} no debería consultar la marca nicho/artesanal {m}",
                )
            for t in especializadas:
                self.assertTrue(
                    tienda_comercializa_marca(t, m),
                    f"{t} sí debería comercializar {m}",
                )

    def test_02_particion_matematica_sharding(self):
        """Demuestra que la división por módulo cubre el 100% de los elementos sin solapamiento (disjuntos)."""
        catalogo_total = [{"id": i, "nombre": f"Perfume_{i}"} for i in range(1, 3251)]  # 3250 perfumes
        total_shards = 2

        shard_1 = [p for idx, p in enumerate(catalogo_total) if idx % total_shards == (1 - 1)]
        shard_2 = [p for idx, p in enumerate(catalogo_total) if idx % total_shards == (2 - 1)]

        # 1. Balance equilibrado
        self.assertEqual(len(shard_1), 1625)
        self.assertEqual(len(shard_2), 1625)

        # 2. Conjuntos estrictamente disjuntos (cero duplicidad de trabajo)
        ids_1 = {p["id"] for p in shard_1}
        ids_2 = {p["id"] for p in shard_2}
        self.assertTrue(ids_1.isdisjoint(ids_2))

        # 3. Unión cubre la totalidad del catálogo (100% cobertura)
        self.assertEqual(ids_1 | ids_2, {p["id"] for p in catalogo_total})

    def test_03_particion_matematica_tres_shards(self):
        """Verifica robustez para cualquier cantidad de shards (ej. 3 shards)."""
        catalogo = [{"id": i} for i in range(100)]
        s1 = [p for idx, p in enumerate(catalogo) if idx % 3 == 0]
        s2 = [p for idx, p in enumerate(catalogo) if idx % 3 == 1]
        s3 = [p for idx, p in enumerate(catalogo) if idx % 3 == 2]

        self.assertEqual(len(s1), 34)
        self.assertEqual(len(s2), 33)
        self.assertEqual(len(s3), 33)

        ids_all = {p["id"] for p in s1} | {p["id"] for p in s2} | {p["id"] for p in s3}
        self.assertEqual(ids_all, {p["id"] for p in catalogo})

    def test_04_persistencia_reporte_por_shard(self):
        """Comprueba que guardar_reporte_auditoria soporte ruta_destino personalizada por shard."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            custom_path = os.path.join(tmp_dir, "reporte_shard_1.json")
            reporte_dummy = {
                "actualizaciones": 150,
                "metadata": {
                    "version_etl": "3.3.0",
                    "shard": 1,
                    "total_shards": 2,
                    "estado": "EXITOSO",
                },
            }

            saved_path = guardar_reporte_auditoria(reporte_dummy, ruta_destino=custom_path)
            self.assertEqual(saved_path, custom_path)
            self.assertTrue(os.path.exists(custom_path))

            import json
            with open(custom_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.assertEqual(data["actualizaciones"], 150)
            self.assertEqual(data["metadata"]["shard"], 1)

    @patch("backend.scraper_periodico.registrar_observacion_oferta")
    @patch("backend.scraper_periodico.iniciar_scraping_run")
    @patch("backend.scraper_periodico.finalizar_scraping_run")
    @patch("backend.scraper_periodico.extraer_variedades_falabella")
    @patch("backend.scraper_periodico.extraer_variedades_paris")
    @patch("backend.scraper_periodico.extraer_variedades_ripley")
    def test_05_concurrencia_retail_y_resiliencia_fallos(
        self,
        mock_ripley,
        mock_paris,
        mock_falabella,
        mock_finalizar,
        mock_iniciar,
        mock_reg,
    ):
        """Verifica que las tiendas de retail se ejecuten concurrentemente y que un fallo en una no afecte a las otras."""
        mock_iniciar.return_value = 888
        mock_reg.return_value = {"resultado": "creada", "campos_modificados": ["precio_actual"]}

        # Falabella responde con éxito
        mock_falabella.return_value = [{
            "exito": True,
            "precio_actual": 89990,
            "precio_normal": 109990,
            "url": "https://falabella.com/producto/123",
            "volumen_ml": 100,
            "en_stock": True,
            "formato": "regular",
            "metodo": "Falabella API",
        }]

        # Paris lanza una excepción simulando timeout de red
        mock_paris.side_effect = TimeoutError("Paris Connection Timeout")

        # Ripley responde con éxito
        mock_ripley.return_value = [{
            "exito": True,
            "precio_actual": 92990,
            "precio_normal": 112990,
            "url": "https://ripley.cl/producto/456",
            "volumen_ml": 100,
            "en_stock": True,
            "formato": "regular",
            "metodo": "Ripley API",
        }]

        perfumes_lote = [{
            "id": 10,
            "nombre": "Sauvage",
            "marca": "Dior",
            "tipo": "Eau de Toilette",
            "precio_referencia": 90000,
        }]

        tiendas_db = [
            {"id": 1, "nombre": "Falabella", "trust_score": 95},
            {"id": 2, "nombre": "Paris", "trust_score": 94},
            {"id": 3, "nombre": "Ripley", "trust_score": 93},
        ]

        mock_session = MagicMock()

        resultado = auditar_lote_perfumes(
            perfumes_lote=perfumes_lote,
            tiendas_db=tiendas_db,
            urls_conocidas_map={},
            session=mock_session,
            rotacion_idx=1,
            total_rotaciones=1,
            total_catalogo=1,
        )

        # Los tres extractores de retail deben haber sido llamados en el pool
        mock_falabella.assert_called_once()
        mock_paris.assert_called_once()
        mock_ripley.assert_called_once()

        # Falabella y Ripley registraron ofertas exitosas (2 actualizaciones)
        self.assertEqual(resultado["metricas"]["precios_actualizados"], 2)

        # Paris registró un error pero no detuvo ni canceló el proceso
        self.assertEqual(len(resultado["errores"]), 1)
        self.assertIn("Paris Connection Timeout", resultado["errores"][0])


if __name__ == "__main__":
    unittest.main()
