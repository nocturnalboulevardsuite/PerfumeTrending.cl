"""
Tests unitarios de integridad: Verificación estricta de perfumes y marcas en scrapers.
====================================================================================
Garantiza que el motor de matching y scraping jamás asocie:
- Fragancias de marcas cruzadas (ej: Givenchy con Maison Francis Kurkdjian).
- Flankers incompatibles (ej: Versace Eros Energy con Versace Eros clásico).
- Clones / dupes (ej: Fragrance World Barakkat con Baccarat Rouge 540 original).
- Variantes de género cruzadas (ej: Versace Eros Woman con Versace Eros masculino).
"""

# Importación de librería estándar o dependencia externa (unittest)
import unittest
# Importación de librería estándar o dependencia externa (sys)
import sys
# Importación de librería estándar o dependencia externa (os)
import os

# Asignamos 'BASE_DIR' con os.path.dirname(os.path.dirname(os.path.ab...
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Evaluamos la condición lógica (BASE_DIR not in sys.path) para controlar el flujo
if BASE_DIR not in sys.path:
    # Ejecutamos instrucción: sys.path.insert(0, BASE_DIR)
    sys.path.insert(0, BASE_DIR)
# Asignamos 'APP_DIR' con os.path.join(BASE_DIR, 'APP')
APP_DIR = os.path.join(BASE_DIR, "APP")
# Evaluamos la condición lógica (APP_DIR not in sys.path) para controlar el flujo
if APP_DIR not in sys.path:
    # Ejecutamos instrucción: sys.path.insert(0, APP_DIR)
    sys.path.insert(0, APP_DIR)

# Importación de componentes (coincide_con_perfume, es_producto_perfume_valido) desde el módulo 'backend.normalizador'
from backend.normalizador import coincide_con_perfume, es_producto_perfume_valido


# Definición de clase 'TestVerificacionScraperPerfumes' que modela la estructura y lógica del componente
class TestVerificacionScraperPerfumes(unittest.TestCase):

    # Definición de función 'test_baccarat_rouge_rechaza_marca_givenchy' sin parámetros externos
    def test_baccarat_rouge_rechaza_marca_givenchy(self):
        """Descarta productos de otra marca aunque compartan la palabra 'Rouge'."""
        # Asignamos 'titulo_falabella' con "GIVENCHY | Perfume Mujer L'Interdit Rouge...
        titulo_falabella = "GIVENCHY | Perfume Mujer L'Interdit Rouge Eau de Parfum Givenchy"
        # Aserción de prueba unitaria: self.assertFalse(coincide_con_perfume(titulo_falabel...
        self.assertFalse(
            coincide_con_perfume(titulo_falabella, "Baccarat Rouge 540", "Maison Francis Kurkdjian"),
            "Givenchy L'Interdit Rouge no debe coincidir con Baccarat Rouge 540 de MFK"
        )

    # Definición de función 'test_baccarat_rouge_rechaza_clon_barakkat_fragrance_world' sin parámetros externos
    def test_baccarat_rouge_rechaza_clon_barakkat_fragrance_world(self):
        """Descarta clones de Fragrance World cuando se audita la casa original MFK."""
        # Asignamos 'titulo_clon' con 'Fragrance World Barakkat Rouge 540 Maison...
        titulo_clon = "Fragrance World Barakkat Rouge 540 Maison Edp 100ml"
        # Aserción de prueba unitaria: self.assertFalse(coincide_con_perfume(titulo_clon, '...
        self.assertFalse(
            coincide_con_perfume(titulo_clon, "Baccarat Rouge 540", "Maison Francis Kurkdjian"),
            "Barakkat de Fragrance World no debe emparejarse con el original de MFK"
        )

    # Definición de función 'test_baccarat_rouge_acepta_original' sin parámetros externos
    def test_baccarat_rouge_acepta_original(self):
        """Acepta la ficha legítima de Baccarat Rouge 540."""
        # Asignamos 'titulo_real' con 'Baccarat Rouge 540 Eau De Parfum 70 Ml'
        titulo_real = "Baccarat Rouge 540 Eau De Parfum 70 Ml"
        # Aserción de prueba unitaria: self.assertTrue(coincide_con_perfume(titulo_real, 'B...
        self.assertTrue(
            coincide_con_perfume(titulo_real, "Baccarat Rouge 540", "Maison Francis Kurkdjian"),
            "Debe aceptar la fragancia legítima Baccarat Rouge 540"
        )

    # Definición de función 'test_eros_rechaza_flanker_energy' sin parámetros externos
    def test_eros_rechaza_flanker_energy(self):
        """Descarta el flanker cítrico 'Eros Energy' al auditar el 'Eros' clásico."""
        # Asignamos 'titulo_energy' con 'VERSACE | Perfume Hombre Versace Eros Ene...
        titulo_energy = "VERSACE | Perfume Hombre Versace Eros Energy Pour Homme EDP 50 ml"
        # Aserción de prueba unitaria: self.assertFalse(coincide_con_perfume(titulo_energy,...
        self.assertFalse(
            coincide_con_perfume(titulo_energy, "Eros", "Versace"),
            "Eros Energy es un flanker diferente y no debe asociarse a Eros clásico"
        )

    # Definición de función 'test_eros_rechaza_flanker_flame' sin parámetros externos
    def test_eros_rechaza_flanker_flame(self):
        """Descarta el flanker 'Eros Flame' (botella roja) al auditar 'Eros' clásico."""
        # Asignamos 'titulo_flame' con 'Perfume Hombre Eros Flame Edp 200 Ml'
        titulo_flame = "Perfume Hombre Eros Flame Edp 200 Ml"
        # Aserción de prueba unitaria: self.assertFalse(coincide_con_perfume(titulo_flame, ...
        self.assertFalse(
            coincide_con_perfume(titulo_flame, "Eros", "Versace"),
            "Eros Flame es un flanker y no debe asociarse a Eros"
        )

    # Definición de función 'test_eros_rechaza_variante_woman' sin parámetros externos
    def test_eros_rechaza_variante_woman(self):
        """Descarta la versión femenina 'Eros Woman' al auditar el perfume masculino."""
        # Asignamos 'titulo_woman' con 'Versace Eros Woman Edp 100ml'
        titulo_woman = "Versace Eros Woman Edp 100ml"
        # Aserción de prueba unitaria: self.assertFalse(coincide_con_perfume(titulo_woman, ...
        self.assertFalse(
            coincide_con_perfume(titulo_woman, "Eros", "Versace"),
            "Eros Woman no debe asociarse a la ficha masculina de Eros"
        )

    # Definición de función 'test_eros_acepta_versiones_validas' sin parámetros externos
    def test_eros_acepta_versiones_validas(self):
        """Acepta las formulaciones legítimas de Versace Eros (EDT, EDP, Parfum)."""
        # Aserción de prueba unitaria: self.assertTrue(coincide_con_perfume('Versace Eros E...
        self.assertTrue(coincide_con_perfume("Versace Eros EDT 50ml", "Eros", "Versace"))
        # Aserción de prueba unitaria: self.assertTrue(coincide_con_perfume('Versace Eros M...
        self.assertTrue(coincide_con_perfume("Versace Eros Men 100ml EDP", "Eros", "Versace"))
        # Aserción de prueba unitaria: self.assertTrue(coincide_con_perfume('Perfume Eros E...
        self.assertTrue(coincide_con_perfume("Perfume Eros EDT Hombre 200 ml", "Eros", "Versace"))

    # Definición de función 'test_acqua_di_gio_rechaza_profondo' sin parámetros externos
    def test_acqua_di_gio_rechaza_profondo(self):
        """Descarta 'Profondo' al auditar la versión base de Acqua Di Gio."""
        # Aserción de prueba unitaria: self.assertFalse(coincide_con_perfume('Acqua Di Gio ...
        self.assertFalse(
            coincide_con_perfume("Acqua Di Gio Profondo EDP 100ml", "Acqua Di Gio", "Giorgio Armani"),
            "Acqua Di Gio Profondo no debe asociarse al Acqua Di Gio clásico"
        )

    # Definición de función 'test_acqua_di_gio_profondo_acepta_profondo' sin parámetros externos
    def test_acqua_di_gio_profondo_acepta_profondo(self):
        """Acepta 'Profondo' si el perfume canónico buscado sí es Profondo."""
        # Aserción de prueba unitaria: self.assertTrue(coincide_con_perfume('Acqua Di Gio P...
        self.assertTrue(
            coincide_con_perfume("Acqua Di Gio Profondo EDP 100ml", "Acqua Di Gio Profondo Men", "Giorgio Armani")
        )

    # Definición de función 'test_descarte_de_imitaciones_y_dupes' sin parámetros externos
    def test_descarte_de_imitaciones_y_dupes(self):
        """Verifica que títulos con 'inspirado en' o 'dupe' sean descartados inmediatamente."""
        # Aserción de prueba unitaria: self.assertFalse(es_producto_perfume_valido('Perfume...
        self.assertFalse(es_producto_perfume_valido("Perfume para dama Aroma Q-05 inspirado en BACCARAT ROUGE"))
        # Aserción de prueba unitaria: self.assertFalse(coincide_con_perfume('Perfume inspi...
        self.assertFalse(coincide_con_perfume("Perfume inspirado en Sauvage Dior 100ml", "Dior Sauvage", "Dior"))


# Punto de entrada principal cuando el script se invoca directamente desde consola
if __name__ == "__main__":
    # Ejecutamos instrucción: unittest.main()
    unittest.main()
