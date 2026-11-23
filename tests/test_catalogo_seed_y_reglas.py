"""
PerfumeTrending.cl — Pruebas de Catálogo Canónico de Notas y Familias
====================================================================
Verifica que el seed contenga exactamente 12 familias y 107 notas olfativas
canónicas según la especificación técnica, sin duplicados ni referencias rotas.
"""

# Importación de librería estándar o dependencia externa (os)
import os
# Importación de librería estándar o dependencia externa (re)
import re
# Importación de librería estándar o dependencia externa (unittest)
import unittest

# Asignamos 'BASE_DIR' con os.path.dirname(os.path.dirname(os.path.ab...
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
MIGRATION_PATH = os.path.join(BASE_DIR, "supabase", "migrations", "20261015000004_seed_familias_y_notas.sql")


# Definición de clase 'TestCatalogoSeedYReglas' que modela la estructura y lógica del componente
class TestCatalogoSeedYReglas(unittest.TestCase):
    # Definición de función 'setUpClass' (parámetros: cls)
    @classmethod
    def setUpClass(cls):
        # Gestión automática de contexto y recursos para: open(MIGRATION_PATH, 'r', encoding='utf-8')
        with open(MIGRATION_PATH, "r", encoding="utf-8") as f:
            # Asignamos 'cls.sql_content' con f.read()
            cls.sql_content = f.read()

    # Definición de función 'test_01_conteo_exacto_familias_de_notas' sin parámetros externos
    def test_01_conteo_exacto_familias_de_notas(self):
        """Verifica que el seed defina exactamente 12 familias de notas olfativas."""
        # Extraer bloques de familias_notas
        matches = re.findall(r"\('([a-z0-9\-]+)',\s*'([^']+)',\s*'([^']+)',\s*'([^']+)',\s*(\d+)\)", self.sql_content)
        # Aserción de prueba unitaria: self.assertEqual(len(matches), 12, f'Se esperaban 12...
        self.assertEqual(len(matches), 12, f"Se esperaban 12 familias de notas; encontradas: {len(matches)}")

        # Verificar unicidad de slugs y órdenes 1 a 12
        slugs = [m[0] for m in matches]
        # Asignamos 'ordenes' con [int(m[4]) for m in matches]
        ordenes = [int(m[4]) for m in matches]
        # Aserción de prueba unitaria: self.assertEqual(len(set(slugs)), 12, 'Los slugs de ...
        self.assertEqual(len(set(slugs)), 12, "Los slugs de las familias deben ser únicos")
        # Aserción de prueba unitaria: self.assertEqual(sorted(ordenes), list(range(1, 13))...
        self.assertEqual(sorted(ordenes), list(range(1, 13)), "Los órdenes deben ser correlativos del 1 al 12")

    # Definición de función 'test_02_conteo_exacto_notas_olfativas' sin parámetros externos
    def test_02_conteo_exacto_notas_olfativas(self):
        """Verifica que el seed defina exactamente 107 notas olfativas canónicas."""
        # Extraer líneas de notas dentro del bloque WITH d
        # Formato: ('familia_slug', 'slug', 'nombre', ARRAY[...])
        pattern = r"\('([a-z0-9\-]+)',\s*'([a-z0-9\-]+)',\s*'([^']+)',\s*ARRAY\[(.*?)\](?:::text\[\])?\)"
        # Asignamos 'matches' con re.findall(pattern, self.sql_content)
        matches = re.findall(pattern, self.sql_content)
        # Aserción de prueba unitaria: self.assertEqual(len(matches), 107, f'Se esperaban e...
        self.assertEqual(len(matches), 107, f"Se esperaban exactamente 107 notas olfativas; encontradas: {len(matches)}")

        # Verificar unicidad de slugs de notas
        slugs = [m[1] for m in matches]
        # Aserción de prueba unitaria: self.assertEqual(len(set(slugs)), 107, 'Cada nota ol...
        self.assertEqual(len(set(slugs)), 107, "Cada nota olfativa debe tener un slug unívoco")

    # Definición de función 'test_03_conteo_por_cada_familia' sin parámetros externos
    def test_03_conteo_por_cada_familia(self):
        """Verifica que la distribución de notas coincida con el desglose del documento técnico."""
        # Desglose esperado:
        # Cítricos: 9
        # Frutales: 15
        # Florales clásicos: 10
        # Flores blancas: 7
        # Herbales: 13
        # Especias: 10
        # Gourmand: 9
        # Maderas: 7
        # Resinas: 7
        # Almizcles: 5
        # Licorosas: 7
        # Moléculas y cuero: 8
        distribucion_esperada = {
            "citricos-hesperides": 9,
            "frutales-bayas": 15,
            "florales-clasicos-nobles": 10,
            "flores-blancas-solares": 7,
            "herbales-aromaticos-verdes": 13,
            "especias-calidas-frescas": 10,
            "gourmand-dulces": 9,
            "maderas-nobles": 7,
            "resinas-balsamicos": 7,
            "almizcles-animalicos": 5,
            "licorosas-bebidas": 7,
            "moleculas-cuero-vanguardia": 8,
        }

        # Asignamos 'pattern' con "\\('([a-z0-9\\-]+)',\\s*'([a-z0-9\\-]+)',...
        pattern = r"\('([a-z0-9\-]+)',\s*'([a-z0-9\-]+)',\s*'([^']+)',\s*ARRAY\[(.*?)\](?:::text\[\])?\)"
        # Asignamos 'matches' con re.findall(pattern, self.sql_content)
        matches = re.findall(pattern, self.sql_content)

        # Importación de componentes (Counter) desde el módulo 'collections'
        from collections import Counter
        # Asignamos 'conteo_real' con Counter([m[0] for m in matches])
        conteo_real = Counter([m[0] for m in matches])

        # Recorremos iterativamente cada '(fam_slug, cant_esperada)' en distribucion_esperada.items()
        for fam_slug, cant_esperada in distribucion_esperada.items():
            # Aserción de prueba unitaria: self.assertEqual(conteo_real.get(fam_slug, 0), cant_...
            self.assertEqual(
                conteo_real.get(fam_slug, 0),
                cant_esperada,
                f"Familia '{fam_slug}' debía tener {cant_esperada} notas, pero tiene {conteo_real.get(fam_slug, 0)}"
            )

    # Definición de función 'test_04_conteo_familias_olfativas_generales' sin parámetros externos
    def test_04_conteo_familias_olfativas_generales(self):
        """Verifica que se definan las 10 familias olfativas macro editoriales."""
        # Asignamos 'pattern' con "\\('([a-z0-9\\-]+)',\\s*'([^']+)',\\s*'([...
        pattern = r"\('([a-z0-9\-]+)',\s*'([^']+)',\s*'([^']+)'\)"
        # Buscar en el bloque de familias_olfativas
        bloque_general = self.sql_content.split("Familias Olfativas Generales")[-1]
        # Asignamos 'matches' con re.findall(pattern, bloque_general)
        matches = re.findall(pattern, bloque_general)
        # Aserción de prueba unitaria: self.assertEqual(len(matches), 10, f'Se esperaban 10...
        self.assertEqual(len(matches), 10, f"Se esperaban 10 familias generales; encontradas: {len(matches)}")


# Punto de entrada principal cuando el script se invoca directamente desde consola
if __name__ == "__main__":
    # Ejecutamos instrucción: unittest.main()
    unittest.main()
