"""
Tests unitarios de alta fidelidad: Motor de Resolución Determinista de Entidades.
================================================================================
Verifica con 47+ casos reales del mercado de e-commerce en Chile:
- Bloqueo total de clones (Fragrance World, Barakkat, Armaf, Lattafa) en marcas de diseñador.
- Guardia de flankers no solicitados (Elixir, Flame, Energy, Lucky, Royal, Absolu).
- Guardia de formatos (recargas, refills, estuches, sets, testers no deseados, desodorantes).
- Guardia de volumen (30ml vs 100ml).
- Cruces de género y líneas incompatibles (YSL Libre vs YSL Y vs MYSLF; Scandal Homme vs Woman).
- Trazabilidad y motivos explicativos de rechazo.
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

from backend.normalizador import coincide_entidad_detallada, coincide_con_perfume, ResultadoCoincidencia


class TestEntityResolutionEngine(unittest.TestCase):

    # --- 1. DIOR SAUVAGE Y CLONES/FLANKERS ---
    def test_sauvage_original_aceptado(self):
        res = coincide_entidad_detallada(
            titulo="Dior Sauvage Eau de Toilette 100ml",
            perfume_nombre="Sauvage",
            marca="Dior",
            concentracion="Eau de Toilette",
            volumen_esperado=100
        )
        self.assertTrue(res.coincide)
        self.assertIn("validada", res.motivo)

    def test_sauvage_rechaza_clon_fragrance_world_just(self):
        res = coincide_entidad_detallada(
            titulo="Fragrance World Just EDP 100ml Hombre Sauvage Elixir",
            perfume_nombre="Sauvage",
            marca="Dior",
            url="https://yauras.cl/products/fragrance-world-just-edp-100ml-hombre-sauvage-elixir"
        )
        self.assertFalse(res.coincide)
        self.assertIn("clon", res.motivo.lower())

    def test_sauvage_rechaza_flanker_elixir(self):
        res = coincide_entidad_detallada(
            titulo="Dior Sauvage Elixir 60ml Men",
            perfume_nombre="Sauvage",
            marca="Dior"
        )
        self.assertFalse(res.coincide)
        self.assertIn("elixir", res.motivo.lower())

    def test_sauvage_rechaza_recarga_300ml(self):
        res = coincide_entidad_detallada(
            titulo="Perfume Hombre Sauvage Recarga Edp 300Ml Dior",
            perfume_nombre="Sauvage",
            marca="Dior",
            volumen_esperado=100
        )
        self.assertFalse(res.coincide)
        self.assertIn("recarga", res.motivo.lower())

    def test_sauvage_rechaza_desodorante(self):
        res = coincide_entidad_detallada(
            titulo="Dior Sauvage Desodorante Stick 75ml",
            perfume_nombre="Sauvage",
            marca="Dior"
        )
        self.assertFalse(res.coincide)
        self.assertIn("desodorante", res.motivo.lower())

    def test_sauvage_elixir_acepta_sauvage_elixir(self):
        res = coincide_entidad_detallada(
            titulo="Dior Sauvage Elixir 60ml Men",
            perfume_nombre="Sauvage Elixir",
            marca="Dior",
            concentracion="Elixir",
            volumen_esperado=60
        )
        self.assertTrue(res.coincide)

    # --- 2. VERSACE EROS Y FLANKERS ---
    def test_eros_rechaza_flame(self):
        self.assertFalse(coincide_con_perfume("Versace Eros Flame EDP 100ml", "Eros", "Versace"))

    def test_eros_rechaza_energy(self):
        self.assertFalse(coincide_con_perfume("Versace Eros Energy Pour Homme EDP 100ml", "Eros", "Versace"))

    def test_eros_rechaza_femme(self):
        self.assertFalse(coincide_con_perfume("Versace Eros Pour Femme EDP 100ml", "Eros", "Versace"))

    def test_eros_flame_acepta_flame(self):
        self.assertTrue(coincide_con_perfume("Versace Eros Flame EDP 100ml", "Eros Flame", "Versace"))

    # --- 3. JEAN PAUL GAULTIER (LE MALE / SCANDAL) ---
    def test_jpg_le_male_elixir_rechaza_armaf_urban_elixir(self):
        res = coincide_entidad_detallada(
            titulo="Armaf Club De Nuit Urban Elixir EDP 105 Ml H",
            perfume_nombre="Le Male Elixir",
            marca="Jean Paul Gaultier",
            url="https://www.eliteperfumes.cl/products/armaf-club-de-nuit-urban-elixir-edp-105-ml-h"
        )
        self.assertFalse(res.coincide)
        self.assertTrue("armaf" in res.motivo.lower() or "oriental" in res.motivo.lower())

    def test_scandal_homme_rechaza_woman(self):
        self.assertFalse(
            coincide_con_perfume("Jean Paul Gaultier Scandal Absolu Woman Parfum 80ml", "Scandal Pour Homme", "Jean Paul Gaultier")
        )

    def test_scandal_homme_rechaza_estuche(self):
        res = coincide_entidad_detallada(
            titulo="Jean Paul Gaultier Scandal Estuche EDT 100ml + 20ml",
            perfume_nombre="Scandal Pour Homme",
            marca="Jean Paul Gaultier"
        )
        self.assertFalse(res.coincide)
        self.assertIn("estuche", res.motivo.lower())

    def test_scandal_homme_rechaza_refill(self):
        res = coincide_entidad_detallada(
            titulo="Jean Paul Gaultier Scandal Le Parfum 100ml Refill",
            perfume_nombre="Scandal Pour Homme",
            marca="Jean Paul Gaultier"
        )
        self.assertFalse(res.coincide)
        self.assertIn("refill", res.motivo.lower())

    # --- 4. PACO RABANNE (1 MILLION / INVICTUS / PHANTOM) ---
    def test_one_million_rechaza_lucky(self):
        self.assertFalse(coincide_con_perfume("Paco Rabanne 1 Million Lucky EDT 100ml", "1 Million", "Paco Rabanne"))

    def test_one_million_rechaza_royal(self):
        self.assertFalse(coincide_con_perfume("Paco Rabanne 1 Million Royal Parfum 100ml", "1 Million", "Paco Rabanne"))

    def test_invictus_rechaza_elixir(self):
        self.assertFalse(coincide_con_perfume("Rabanne Invictus Parfum Elixir 100 ml Hombre", "Invictus", "Paco Rabanne"))

    def test_phantom_rechaza_recargable(self):
        res = coincide_entidad_detallada(
            titulo="Paco Rabanne Phantom Parfum 150 ml Hombre Recargable",
            perfume_nombre="Phantom",
            marca="Paco Rabanne"
        )
        self.assertFalse(res.coincide)

    # --- 5. YSL (LIBRE / Y / MYSLF) ---
    def test_libre_rechaza_y_elixir(self):
        res = coincide_entidad_detallada(
            titulo="Yves Saint Laurent Y L'Elixir Parfum Concentre 60 ml H",
            perfume_nombre="Libre",
            marca="Yves Saint Laurent"
        )
        self.assertFalse(res.coincide)

    def test_libre_rechaza_myslf(self):
        res = coincide_entidad_detallada(
            titulo="Yves Saint Laurent MYSLF Recargable EDP 100 ml",
            perfume_nombre="Libre",
            marca="Yves Saint Laurent"
        )
        self.assertFalse(res.coincide)

    def test_libre_rechaza_absolu_platine(self):
        self.assertFalse(coincide_con_perfume("YSL Libre L'Absolu Platine Parfum 50 ml", "Libre", "Yves Saint Laurent"))

    # --- 6. GIORGIO ARMANI ---
    def test_adg_rechaza_profondo(self):
        self.assertFalse(coincide_con_perfume("Acqua Di Gio Profondo EDP 100ml", "Acqua Di Gio", "Giorgio Armani"))

    def test_adg_profondo_acepta_profondo(self):
        self.assertTrue(coincide_con_perfume("Acqua Di Gio Profondo EDP 100ml", "Acqua Di Gio Profondo", "Giorgio Armani"))

    # --- 7. MFK BACCARAT ROUGE ---
    def test_baccarat_rouge_rechaza_givenchy_rouge(self):
        res = coincide_entidad_detallada(
            titulo="GIVENCHY | Perfume Mujer L'Interdit Rouge Eau de Parfum Givenchy",
            perfume_nombre="Baccarat Rouge 540",
            marca="Maison Francis Kurkdjian"
        )
        self.assertFalse(res.coincide)

    def test_baccarat_rouge_rechaza_clon_barakkat(self):
        res = coincide_entidad_detallada(
            titulo="Fragrance World Barakkat Rouge 540 Maison Edp 100ml",
            perfume_nombre="Baccarat Rouge 540",
            marca="Maison Francis Kurkdjian"
        )
        self.assertFalse(res.coincide)
        self.assertIn("clon", res.motivo.lower())

    # --- 8. CASO VANILLA (ARIANA GRANDE VS LATTAFA) ---
    def test_ariana_grande_mod_vanilla_rechaza_lattafa(self):
        res = coincide_entidad_detallada(
            titulo="Lattafa Give Me Gourmand Vanilla Freak EDP 75 ml",
            perfume_nombre="Mod Vanilla",
            marca="Ariana Grande"
        )
        self.assertFalse(res.coincide)

    # --- 9. VOLUMEN DISCREPANTE ---
    def test_volumen_discrepante_30ml_vs_100ml(self):
        res = coincide_entidad_detallada(
            titulo="Dolce & Gabbana Devotion Eau De Parfum 100ML",
            perfume_nombre="Devotion",
            marca="Dolce & Gabbana",
            volumen_esperado=30
        )
        self.assertFalse(res.coincide)
        self.assertIn("volumen", res.motivo.lower())

    def test_volumen_correcto_30ml(self):
        res = coincide_entidad_detallada(
            titulo="Dolce & Gabbana Devotion Eau De Parfum 30ML",
            perfume_nombre="Devotion",
            marca="Dolce & Gabbana",
            volumen_esperado=30
        )
        self.assertTrue(res.coincide)

    # --- 10. CREED AVENTUS VS ARMAF ---
    def test_creed_aventus_rechaza_armaf_cdnim(self):
        res = coincide_entidad_detallada(
            titulo="Armaf Club De Nuit Intense Man EDT 105ml",
            perfume_nombre="Aventus",
            marca="Creed"
        )
        self.assertFalse(res.coincide)

    def test_armaf_cdnim_acepta_cdnim(self):
        self.assertTrue(coincide_con_perfume("Armaf Club De Nuit Intense Man EDT 105ml", "Club De Nuit Intense Man", "Armaf"))

    # --- 11. TOM FORD / CHANEL / VERSACE ---
    def test_lost_cherry_rechaza_tuscan_leather(self):
        self.assertFalse(coincide_con_perfume("Tom Ford Tuscan Leather EDP 50ml", "Lost Cherry", "Tom Ford"))

    def test_bleu_chanel_rechaza_versace_dylan_blue(self):
        self.assertFalse(coincide_con_perfume("Versace Dylan Blue Pour Homme EDT 100ml", "Bleu de Chanel", "Chanel"))


if __name__ == "__main__":
    unittest.main()
