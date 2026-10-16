"""
Tests unitarios de integridad: Verificación estricta de perfumes y marcas en scrapers.
====================================================================================
Garantiza que el motor de matching y scraping jamás asocie:
- Fragancias de marcas cruzadas (ej: Givenchy con Maison Francis Kurkdjian).
- Flankers incompatibles (ej: Versace Eros Energy con Versace Eros clásico).
- Clones / dupes (ej: Fragrance World Barakkat con Baccarat Rouge 540 original).
- Variantes de género cruzadas (ej: Versace Eros Woman con Versace Eros masculino).
"""

import unittest
import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
APP_DIR = os.path.join(BASE_DIR, "APP")
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from backend.normalizador import coincide_con_perfume, es_producto_perfume_valido


class TestVerificacionScraperPerfumes(unittest.TestCase):

    def test_baccarat_rouge_rechaza_marca_givenchy(self):
        """Descarta productos de otra marca aunque compartan la palabra 'Rouge'."""
        titulo_falabella = "GIVENCHY | Perfume Mujer L'Interdit Rouge Eau de Parfum Givenchy"
        self.assertFalse(
            coincide_con_perfume(titulo_falabella, "Baccarat Rouge 540", "Maison Francis Kurkdjian"),
            "Givenchy L'Interdit Rouge no debe coincidir con Baccarat Rouge 540 de MFK"
        )

    def test_baccarat_rouge_rechaza_clon_barakkat_fragrance_world(self):
        """Descarta clones de Fragrance World cuando se audita la casa original MFK."""
        titulo_clon = "Fragrance World Barakkat Rouge 540 Maison Edp 100ml"
        self.assertFalse(
            coincide_con_perfume(titulo_clon, "Baccarat Rouge 540", "Maison Francis Kurkdjian"),
            "Barakkat de Fragrance World no debe emparejarse con el original de MFK"
        )

    def test_baccarat_rouge_acepta_original(self):
        """Acepta la ficha legítima de Baccarat Rouge 540."""
        titulo_real = "Baccarat Rouge 540 Eau De Parfum 70 Ml"
        self.assertTrue(
            coincide_con_perfume(titulo_real, "Baccarat Rouge 540", "Maison Francis Kurkdjian"),
            "Debe aceptar la fragancia legítima Baccarat Rouge 540"
        )

    def test_eros_rechaza_flanker_energy(self):
        """Descarta el flanker cítrico 'Eros Energy' al auditar el 'Eros' clásico."""
        titulo_energy = "VERSACE | Perfume Hombre Versace Eros Energy Pour Homme EDP 50 ml"
        self.assertFalse(
            coincide_con_perfume(titulo_energy, "Eros", "Versace"),
            "Eros Energy es un flanker diferente y no debe asociarse a Eros clásico"
        )

    def test_eros_rechaza_flanker_flame(self):
        """Descarta el flanker 'Eros Flame' (botella roja) al auditar 'Eros' clásico."""
        titulo_flame = "Perfume Hombre Eros Flame Edp 200 Ml"
        self.assertFalse(
            coincide_con_perfume(titulo_flame, "Eros", "Versace"),
            "Eros Flame es un flanker y no debe asociarse a Eros"
        )

    def test_eros_rechaza_variante_woman(self):
        """Descarta la versión femenina 'Eros Woman' al auditar el perfume masculino."""
        titulo_woman = "Versace Eros Woman Edp 100ml"
        self.assertFalse(
            coincide_con_perfume(titulo_woman, "Eros", "Versace"),
            "Eros Woman no debe asociarse a la ficha masculina de Eros"
        )

    def test_eros_acepta_versiones_validas(self):
        """Acepta las formulaciones legítimas de Versace Eros (EDT, EDP, Parfum)."""
        self.assertTrue(coincide_con_perfume("Versace Eros EDT 50ml", "Eros", "Versace"))
        self.assertTrue(coincide_con_perfume("Versace Eros Men 100ml EDP", "Eros", "Versace"))
        self.assertTrue(coincide_con_perfume("Perfume Eros EDT Hombre 200 ml", "Eros", "Versace"))

    def test_acqua_di_gio_rechaza_profondo(self):
        """Descarta 'Profondo' al auditar la versión base de Acqua Di Gio."""
        self.assertFalse(
            coincide_con_perfume("Acqua Di Gio Profondo EDP 100ml", "Acqua Di Gio", "Giorgio Armani"),
            "Acqua Di Gio Profondo no debe asociarse al Acqua Di Gio clásico"
        )

    def test_acqua_di_gio_profondo_acepta_profondo(self):
        """Acepta 'Profondo' si el perfume canónico buscado sí es Profondo."""
        self.assertTrue(
            coincide_con_perfume("Acqua Di Gio Profondo EDP 100ml", "Acqua Di Gio Profondo Men", "Giorgio Armani")
        )

    def test_descarte_de_imitaciones_y_dupes(self):
        """Verifica que títulos con 'inspirado en' o 'dupe' sean descartados inmediatamente."""
        self.assertFalse(es_producto_perfume_valido("Perfume para dama Aroma Q-05 inspirado en BACCARAT ROUGE"))
        self.assertFalse(coincide_con_perfume("Perfume inspirado en Sauvage Dior 100ml", "Dior Sauvage", "Dior"))


if __name__ == "__main__":
    unittest.main()
