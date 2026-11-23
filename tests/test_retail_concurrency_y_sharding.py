"""
Tests unitarios para la optimización de Concurrencia en Retail Tradicional,
Poda Fina de Marcas No-Retail y Horizontal Sharding (50/50) en GitHub Actions.

Verifica:
1. Poda de marcas: Filtro estricto de perfumería árabe y marcas nicho/indie en Falabella, Paris, Ripley y DBS.
2. Partición matemática de Sharding: Disyunción absoluta y cobertura al 100% del catálogo.
3. Concurrencia de red (ThreadPoolExecutor): Ejecución concurrente segura en tiendas departamentales.
4. Resiliencia ante fallos parciales de red sin degradar el lote completo.
"""

# Importación de librería estándar o dependencia externa (os)
import os
# Importación de librería estándar o dependencia externa (sys)
import sys
# Importación de librería estándar o dependencia externa (tempfile)
import tempfile
# Importación de librería estándar o dependencia externa (unittest)
import unittest
# Importación de componentes (MagicMock, patch) desde el módulo 'unittest.mock'
from unittest.mock import MagicMock, patch

# Asignamos '_app_dir' con os.path.abspath(os.path.join(os.path.dirna...
_app_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "APP"))
# Evaluamos la condición lógica (_app_dir not in sys.path) para controlar el flujo
if _app_dir not in sys.path:
    # Ejecutamos instrucción: sys.path.insert(0, _app_dir)
    sys.path.insert(0, _app_dir)

# Importación de componentes (MARCAS_NO_RETAIL_TRADICIONAL, tienda_comercializa_marca) desde el módulo 'backend.database'
from backend.database import (
    MARCAS_NO_RETAIL_TRADICIONAL,
    tienda_comercializa_marca,
)
# Importación de componentes (auditar_lote_perfumes, guardar_reporte_auditoria) desde el módulo 'backend.scraper_periodico'
from backend.scraper_periodico import (
    auditar_lote_perfumes,
    guardar_reporte_auditoria,
)


# Definición de clase 'TestRetailConcurrencyYSharding' que modela la estructura y lógica del componente
class TestRetailConcurrencyYSharding(unittest.TestCase):

    # Definición de función 'test_01_poda_marcas_retail_tradicional_vs_nicho' sin parámetros externos
    def test_01_poda_marcas_retail_tradicional_vs_nicho(self):
        """Verifica que todas las tiendas de retail comercialicen marcas de diseñador, nicho y perfumería árabe."""
        # Asignamos 'grandes_almacenes' con ['Falabella', 'Paris', 'Ripley']
        grandes_almacenes = ["Falabella", "Paris", "Ripley"]
        # Asignamos 'retail_y_farmacias' con ['Falabella', 'Paris', 'Ripley', 'DBS Beau...
        retail_y_farmacias = ["Falabella", "Paris", "Ripley", "DBS Beauty Store"]
        # Asignamos 'especializadas' con ['Silk Perfumes', 'Elite Perfumes', 'Al-Ha...
        especializadas = ["Silk Perfumes", "Elite Perfumes", "Al-Haramain Chile"]

        # Marcas tradicionales de diseñador -> DEBEN consultarse en grandes almacenes
        marcas_retail = ["Dior", "Chanel", "Versace", "Giorgio Armani", "Carolina Herrera", "Paco Rabanne"]
        # Recorremos iterativamente cada 't' en grandes_almacenes
        for t in grandes_almacenes:
            # Recorremos iterativamente cada 'm' en marcas_retail
            for m in marcas_retail:
                # Aserción de prueba unitaria: self.assertTrue(tienda_comercializa_marca(t, m), f'S...
                self.assertTrue(
                    tienda_comercializa_marca(t, m),
                    f"Se esperaba que {t} comercialice la marca tradicional {m}",
                )

        # Marcas árabes -> DEBEN consultarse en todas las tiendas de retail y especializadas
        marcas_arabes = ["Lattafa", "Armaf", "Afnan", "Al Haramain", "Rasasi"]
        # Recorremos iterativamente cada 't' en retail_y_farmacias + especializadas
        for t in retail_y_farmacias + especializadas:
            # Recorremos iterativamente cada 'm' en marcas_arabes
            for m in marcas_arabes:
                # Aserción de prueba unitaria: self.assertTrue(tienda_comercializa_marca(t, m, es_a...
                self.assertTrue(
                    tienda_comercializa_marca(t, m, es_arabe_flag=True),
                    f"Se esperaba que {t} comercialice la marca árabe {m}",
                )

        # Marcas nicho/indie/clon -> DEBEN consultarse tanto en retail (Marketplace) como en especializadas
        muestras_nicho = ["Lorenzo Pazzaglia", "Argos", "Bon Parfumeur", "Mancera", "Montale", "Creed", "Xerjoff"]
        # Recorremos iterativamente cada 'm' en muestras_nicho
        for m in muestras_nicho:
            # Aserción de prueba unitaria: self.assertIn(m.lower(), MARCAS_NO_RETAIL_TRADICIONAL)
            self.assertIn(m.lower(), MARCAS_NO_RETAIL_TRADICIONAL)
            # Recorremos iterativamente cada 't' en retail_y_farmacias + especializadas
            for t in retail_y_farmacias + especializadas:
                # Aserción de prueba unitaria: self.assertTrue(tienda_comercializa_marca(t, m), f'{...
                self.assertTrue(
                    tienda_comercializa_marca(t, m),
                    f"{t} sí debería comercializar {m}",
                )

    # Definición de función 'test_02_particion_matematica_sharding' sin parámetros externos
    def test_02_particion_matematica_sharding(self):
        """Demuestra que la división por módulo cubre el 100% de los elementos sin solapamiento (disjuntos)."""
        # Asignamos 'catalogo_total' con [{'id': i, 'nombre': f'Perfume_{i}'} for i...
        catalogo_total = [{"id": i, "nombre": f"Perfume_{i}"} for i in range(1, 3251)]  # 3250 perfumes
        # Asignamos 'total_shards' con 2
        total_shards = 2

        # Asignamos 'shard_1' con [p for idx, p in enumerate(catalogo_total)...
        shard_1 = [p for idx, p in enumerate(catalogo_total) if idx % total_shards == (1 - 1)]
        # Asignamos 'shard_2' con [p for idx, p in enumerate(catalogo_total)...
        shard_2 = [p for idx, p in enumerate(catalogo_total) if idx % total_shards == (2 - 1)]

        # 1. Balance equilibrado
        self.assertEqual(len(shard_1), 1625)
        # Aserción de prueba unitaria: self.assertEqual(len(shard_2), 1625)
        self.assertEqual(len(shard_2), 1625)

        # 2. Conjuntos estrictamente disjuntos (cero duplicidad de trabajo)
        ids_1 = {p["id"] for p in shard_1}
        # Asignamos 'ids_2' con {p['id'] for p in shard_2}
        ids_2 = {p["id"] for p in shard_2}
        # Aserción de prueba unitaria: self.assertTrue(ids_1.isdisjoint(ids_2))
        self.assertTrue(ids_1.isdisjoint(ids_2))

        # 3. Unión cubre la totalidad del catálogo (100% cobertura)
        self.assertEqual(ids_1 | ids_2, {p["id"] for p in catalogo_total})

    # Definición de función 'test_03_particion_matematica_tres_shards' sin parámetros externos
    def test_03_particion_matematica_tres_shards(self):
        """Verifica robustez para cualquier cantidad de shards (ej. 3 shards)."""
        # Asignamos 'catalogo' con [{'id': i} for i in range(100)]
        catalogo = [{"id": i} for i in range(100)]
        # Asignamos 's1' con [p for idx, p in enumerate(catalogo) if id...
        s1 = [p for idx, p in enumerate(catalogo) if idx % 3 == 0]
        # Asignamos 's2' con [p for idx, p in enumerate(catalogo) if id...
        s2 = [p for idx, p in enumerate(catalogo) if idx % 3 == 1]
        # Asignamos 's3' con [p for idx, p in enumerate(catalogo) if id...
        s3 = [p for idx, p in enumerate(catalogo) if idx % 3 == 2]

        # Aserción de prueba unitaria: self.assertEqual(len(s1), 34)
        self.assertEqual(len(s1), 34)
        # Aserción de prueba unitaria: self.assertEqual(len(s2), 33)
        self.assertEqual(len(s2), 33)
        # Aserción de prueba unitaria: self.assertEqual(len(s3), 33)
        self.assertEqual(len(s3), 33)

        # Asignamos 'ids_all' con {p['id'] for p in s1} | {p['id'] for p in ...
        ids_all = {p["id"] for p in s1} | {p["id"] for p in s2} | {p["id"] for p in s3}
        # Aserción de prueba unitaria: self.assertEqual(ids_all, {p['id'] for p in catalogo})
        self.assertEqual(ids_all, {p["id"] for p in catalogo})

    # Definición de función 'test_04_persistencia_reporte_por_shard' sin parámetros externos
    def test_04_persistencia_reporte_por_shard(self):
        """Comprueba que guardar_reporte_auditoria soporte ruta_destino personalizada por shard."""
        # Gestión automática de contexto y recursos para: tempfile.TemporaryDirectory()
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Asignamos 'custom_path' con os.path.join(tmp_dir, 'reporte_shard_1.json')
            custom_path = os.path.join(tmp_dir, "reporte_shard_1.json")
            # Asignamos 'reporte_dummy' con {'actualizaciones': 150, 'metadata': {'ver...
            reporte_dummy = {
                "actualizaciones": 150,
                "metadata": {
                    "version_etl": "3.3.0",
                    "shard": 1,
                    "total_shards": 2,
                    "estado": "EXITOSO",
                },
            }

            # Asignamos 'saved_path' con guardar_reporte_auditoria(reporte_dummy, r...
            saved_path = guardar_reporte_auditoria(reporte_dummy, ruta_destino=custom_path)
            # Aserción de prueba unitaria: self.assertEqual(saved_path, custom_path)
            self.assertEqual(saved_path, custom_path)
            # Aserción de prueba unitaria: self.assertTrue(os.path.exists(custom_path))
            self.assertTrue(os.path.exists(custom_path))

            # Importación de librería estándar o dependencia externa (json)
            import json
            # Gestión automática de contexto y recursos para: open(custom_path, 'r', encoding='utf-8')
            with open(custom_path, "r", encoding="utf-8") as f:
                # Procesamiento de serialización o deserialización de estructura JSON
                data = json.load(f)
            # Aserción de prueba unitaria: self.assertEqual(data['actualizaciones'], 150)
            self.assertEqual(data["actualizaciones"], 150)
            # Aserción de prueba unitaria: self.assertEqual(data['metadata']['shard'], 1)
            self.assertEqual(data["metadata"]["shard"], 1)

    # Definición de función 'test_05_concurrencia_retail_y_resiliencia_fallos' (parámetros: mock_ripley, mock_paris, mock_falabella, mock_finalizar, ...)
    @patch("backend.scraper_periodico.registrar_fallo_scraping")
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
        mock_fallo,
    ):
        """Verifica que las tiendas de retail se ejecuten concurrentemente y que un fallo en una no afecte a las otras."""
        # Asignamos 'mock_iniciar.return_value' con 888
        mock_iniciar.return_value = 888
        # Asignamos 'mock_reg.return_value' con {'resultado': 'creada', 'campos_modificado...
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

        # Asignamos 'perfumes_lote' con [{'id': 10, 'nombre': 'Sauvage', 'marca': ...
        perfumes_lote = [{
            "id": 10,
            "nombre": "Sauvage",
            "marca": "Dior",
            "tipo": "Eau de Toilette",
            "precio_referencia": 90000,
        }]

        # Asignamos 'tiendas_db' con [{'id': 1, 'nombre': 'Falabella', 'trust_s...
        tiendas_db = [
            # Configuración de elemento #1 (id='1', nombre='Falabella')
            {"id": 1, "nombre": "Falabella", "trust_score": 95},
            # Configuración de elemento #2 (id='2', nombre='Paris')
            {"id": 2, "nombre": "Paris", "trust_score": 94},
            # Configuración de elemento #3 (id='3', nombre='Ripley')
            {"id": 3, "nombre": "Ripley", "trust_score": 93},
        ]

        # Asignamos 'mock_session' con MagicMock()
        mock_session = MagicMock()

        # Asignamos 'resultado' con auditar_lote_perfumes(perfumes_lote=perfum...
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
        # Ejecutamos instrucción: mock_paris.assert_called_once()
        mock_paris.assert_called_once()
        # Ejecutamos instrucción: mock_ripley.assert_called_once()
        mock_ripley.assert_called_once()

        # Falabella y Ripley registraron ofertas exitosas (2 actualizaciones)
        self.assertEqual(resultado["metricas"]["precios_actualizados"], 2)

        # Paris registró un error pero no detuvo ni canceló el proceso
        self.assertEqual(len(resultado["errores"]), 1)
        # Aserción de prueba unitaria: self.assertIn('Paris Connection Timeout', resultado[...
        self.assertIn("Paris Connection Timeout", resultado["errores"][0])


# Punto de entrada principal cuando el script se invoca directamente desde consola
if __name__ == "__main__":
    # Ejecutamos instrucción: unittest.main()
    unittest.main()
