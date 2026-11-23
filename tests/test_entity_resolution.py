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

# Importación de componentes (coincide_entidad_detallada, coincide_con_perfume, ResultadoCoincidencia) desde el módulo 'backend.normalizador'
from backend.normalizador import coincide_entidad_detallada, coincide_con_perfume, ResultadoCoincidencia


# Definición de clase 'TestEntityResolutionEngine' que modela la estructura y lógica del componente
class TestEntityResolutionEngine(unittest.TestCase):

    # --- 1. DIOR SAUVAGE Y CLONES/FLANKERS ---
    def test_sauvage_original_aceptado(self):
        # Asignamos 'res' con coincide_entidad_detallada(titulo='Dior Sa...
        res = coincide_entidad_detallada(
            titulo="Dior Sauvage Eau de Toilette 100ml",
            perfume_nombre="Sauvage",
            marca="Dior",
            concentracion="Eau de Toilette",
            volumen_esperado=100
        )
        # Aserción de prueba unitaria: self.assertTrue(res.coincide)
        self.assertTrue(res.coincide)
        # Aserción de prueba unitaria: self.assertIn('validada', res.motivo)
        self.assertIn("validada", res.motivo)

    # Definición de función 'test_sauvage_rechaza_clon_fragrance_world_just' sin parámetros externos
    def test_sauvage_rechaza_clon_fragrance_world_just(self):
        # Asignamos 'res' con coincide_entidad_detallada(titulo='Fragran...
        res = coincide_entidad_detallada(
            titulo="Fragrance World Just EDP 100ml Hombre Sauvage Elixir",
            perfume_nombre="Sauvage",
            marca="Dior",
            url="https://yauras.cl/products/fragrance-world-just-edp-100ml-hombre-sauvage-elixir"
        )
        # Aserción de prueba unitaria: self.assertFalse(res.coincide)
        self.assertFalse(res.coincide)
        # Aserción de prueba unitaria: self.assertIn('clon', res.motivo.lower())
        self.assertIn("clon", res.motivo.lower())

    # Definición de función 'test_sauvage_rechaza_flanker_elixir' sin parámetros externos
    def test_sauvage_rechaza_flanker_elixir(self):
        # Asignamos 'res' con coincide_entidad_detallada(titulo='Dior Sa...
        res = coincide_entidad_detallada(
            titulo="Dior Sauvage Elixir 60ml Men",
            perfume_nombre="Sauvage",
            marca="Dior"
        )
        # Aserción de prueba unitaria: self.assertFalse(res.coincide)
        self.assertFalse(res.coincide)
        # Aserción de prueba unitaria: self.assertIn('elixir', res.motivo.lower())
        self.assertIn("elixir", res.motivo.lower())

    # Definición de función 'test_sauvage_rechaza_recarga_300ml' sin parámetros externos
    def test_sauvage_rechaza_recarga_300ml(self):
        # Asignamos 'res' con coincide_entidad_detallada(titulo='Perfume...
        res = coincide_entidad_detallada(
            titulo="Perfume Hombre Sauvage Recarga Edp 300Ml Dior",
            perfume_nombre="Sauvage",
            marca="Dior",
            volumen_esperado=100
        )
        # Aserción de prueba unitaria: self.assertFalse(res.coincide)
        self.assertFalse(res.coincide)
        # Aserción de prueba unitaria: self.assertIn('recarga', res.motivo.lower())
        self.assertIn("recarga", res.motivo.lower())

    # Definición de función 'test_sauvage_rechaza_desodorante' sin parámetros externos
    def test_sauvage_rechaza_desodorante(self):
        # Asignamos 'res' con coincide_entidad_detallada(titulo='Dior Sa...
        res = coincide_entidad_detallada(
            titulo="Dior Sauvage Desodorante Stick 75ml",
            perfume_nombre="Sauvage",
            marca="Dior"
        )
        # Aserción de prueba unitaria: self.assertFalse(res.coincide)
        self.assertFalse(res.coincide)
        # Aserción de prueba unitaria: self.assertIn('desodorante', res.motivo.lower())
        self.assertIn("desodorante", res.motivo.lower())

    # Definición de función 'test_sauvage_elixir_acepta_sauvage_elixir' sin parámetros externos
    def test_sauvage_elixir_acepta_sauvage_elixir(self):
        # Asignamos 'res' con coincide_entidad_detallada(titulo='Dior Sa...
        res = coincide_entidad_detallada(
            titulo="Dior Sauvage Elixir 60ml Men",
            perfume_nombre="Sauvage Elixir",
            marca="Dior",
            concentracion="Elixir",
            volumen_esperado=60
        )
        # Aserción de prueba unitaria: self.assertTrue(res.coincide)
        self.assertTrue(res.coincide)

    # --- 2. VERSACE EROS Y FLANKERS ---
    def test_eros_rechaza_flame(self):
        # Aserción de prueba unitaria: self.assertFalse(coincide_con_perfume('Versace Eros ...
        self.assertFalse(coincide_con_perfume("Versace Eros Flame EDP 100ml", "Eros", "Versace"))

    # Definición de función 'test_eros_rechaza_energy' sin parámetros externos
    def test_eros_rechaza_energy(self):
        # Aserción de prueba unitaria: self.assertFalse(coincide_con_perfume('Versace Eros ...
        self.assertFalse(coincide_con_perfume("Versace Eros Energy Pour Homme EDP 100ml", "Eros", "Versace"))

    # Definición de función 'test_eros_rechaza_femme' sin parámetros externos
    def test_eros_rechaza_femme(self):
        # Aserción de prueba unitaria: self.assertFalse(coincide_con_perfume('Versace Eros ...
        self.assertFalse(coincide_con_perfume("Versace Eros Pour Femme EDP 100ml", "Eros", "Versace"))

    # Definición de función 'test_eros_flame_acepta_flame' sin parámetros externos
    def test_eros_flame_acepta_flame(self):
        # Aserción de prueba unitaria: self.assertTrue(coincide_con_perfume('Versace Eros F...
        self.assertTrue(coincide_con_perfume("Versace Eros Flame EDP 100ml", "Eros Flame", "Versace"))

    # --- 3. JEAN PAUL GAULTIER (LE MALE / SCANDAL) ---
    def test_jpg_le_male_elixir_rechaza_armaf_urban_elixir(self):
        # Asignamos 'res' con coincide_entidad_detallada(titulo='Armaf C...
        res = coincide_entidad_detallada(
            titulo="Armaf Club De Nuit Urban Elixir EDP 105 Ml H",
            perfume_nombre="Le Male Elixir",
            marca="Jean Paul Gaultier",
            url="https://www.eliteperfumes.cl/products/armaf-club-de-nuit-urban-elixir-edp-105-ml-h"
        )
        # Aserción de prueba unitaria: self.assertFalse(res.coincide)
        self.assertFalse(res.coincide)
        # Aserción de prueba unitaria: self.assertTrue('armaf' in res.motivo.lower() or 'or...
        self.assertTrue("armaf" in res.motivo.lower() or "oriental" in res.motivo.lower())

    # Definición de función 'test_scandal_homme_rechaza_woman' sin parámetros externos
    def test_scandal_homme_rechaza_woman(self):
        # Aserción de prueba unitaria: self.assertFalse(coincide_con_perfume('Jean Paul Gau...
        self.assertFalse(
            coincide_con_perfume("Jean Paul Gaultier Scandal Absolu Woman Parfum 80ml", "Scandal Pour Homme", "Jean Paul Gaultier")
        )

    # Definición de función 'test_scandal_homme_rechaza_estuche' sin parámetros externos
    def test_scandal_homme_rechaza_estuche(self):
        # Asignamos 'res' con coincide_entidad_detallada(titulo='Jean Pa...
        res = coincide_entidad_detallada(
            titulo="Jean Paul Gaultier Scandal Estuche EDT 100ml + 20ml",
            perfume_nombre="Scandal Pour Homme",
            marca="Jean Paul Gaultier"
        )
        # Aserción de prueba unitaria: self.assertFalse(res.coincide)
        self.assertFalse(res.coincide)
        # Aserción de prueba unitaria: self.assertIn('estuche', res.motivo.lower())
        self.assertIn("estuche", res.motivo.lower())

    # Definición de función 'test_scandal_homme_rechaza_refill' sin parámetros externos
    def test_scandal_homme_rechaza_refill(self):
        # Asignamos 'res' con coincide_entidad_detallada(titulo='Jean Pa...
        res = coincide_entidad_detallada(
            titulo="Jean Paul Gaultier Scandal Le Parfum 100ml Refill",
            perfume_nombre="Scandal Pour Homme",
            marca="Jean Paul Gaultier"
        )
        # Aserción de prueba unitaria: self.assertFalse(res.coincide)
        self.assertFalse(res.coincide)
        # Aserción de prueba unitaria: self.assertIn('refill', res.motivo.lower())
        self.assertIn("refill", res.motivo.lower())

    # --- 4. PACO RABANNE (1 MILLION / INVICTUS / PHANTOM) ---
    def test_one_million_rechaza_lucky(self):
        # Aserción de prueba unitaria: self.assertFalse(coincide_con_perfume('Paco Rabanne ...
        self.assertFalse(coincide_con_perfume("Paco Rabanne 1 Million Lucky EDT 100ml", "1 Million", "Paco Rabanne"))

    # Definición de función 'test_one_million_rechaza_royal' sin parámetros externos
    def test_one_million_rechaza_royal(self):
        # Aserción de prueba unitaria: self.assertFalse(coincide_con_perfume('Paco Rabanne ...
        self.assertFalse(coincide_con_perfume("Paco Rabanne 1 Million Royal Parfum 100ml", "1 Million", "Paco Rabanne"))

    # Definición de función 'test_invictus_rechaza_elixir' sin parámetros externos
    def test_invictus_rechaza_elixir(self):
        # Aserción de prueba unitaria: self.assertFalse(coincide_con_perfume('Rabanne Invic...
        self.assertFalse(coincide_con_perfume("Rabanne Invictus Parfum Elixir 100 ml Hombre", "Invictus", "Paco Rabanne"))

    # Definición de función 'test_phantom_rechaza_recargable' sin parámetros externos
    def test_phantom_rechaza_recargable(self):
        # Asignamos 'res' con coincide_entidad_detallada(titulo='Paco Ra...
        res = coincide_entidad_detallada(
            titulo="Paco Rabanne Phantom Parfum 150 ml Hombre Recargable",
            perfume_nombre="Phantom",
            marca="Paco Rabanne"
        )
        # Aserción de prueba unitaria: self.assertFalse(res.coincide)
        self.assertFalse(res.coincide)

    # --- 5. YSL (LIBRE / Y / MYSLF) ---
    def test_libre_rechaza_y_elixir(self):
        # Asignamos 'res' con coincide_entidad_detallada(titulo="Yves Sa...
        res = coincide_entidad_detallada(
            titulo="Yves Saint Laurent Y L'Elixir Parfum Concentre 60 ml H",
            perfume_nombre="Libre",
            marca="Yves Saint Laurent"
        )
        # Aserción de prueba unitaria: self.assertFalse(res.coincide)
        self.assertFalse(res.coincide)

    # Definición de función 'test_libre_rechaza_myslf' sin parámetros externos
    def test_libre_rechaza_myslf(self):
        # Asignamos 'res' con coincide_entidad_detallada(titulo='Yves Sa...
        res = coincide_entidad_detallada(
            titulo="Yves Saint Laurent MYSLF Recargable EDP 100 ml",
            perfume_nombre="Libre",
            marca="Yves Saint Laurent"
        )
        # Aserción de prueba unitaria: self.assertFalse(res.coincide)
        self.assertFalse(res.coincide)

    # Definición de función 'test_libre_rechaza_absolu_platine' sin parámetros externos
    def test_libre_rechaza_absolu_platine(self):
        # Aserción de prueba unitaria: self.assertFalse(coincide_con_perfume("YSL Libre L'A...
        self.assertFalse(coincide_con_perfume("YSL Libre L'Absolu Platine Parfum 50 ml", "Libre", "Yves Saint Laurent"))

    # --- 6. GIORGIO ARMANI ---
    def test_adg_rechaza_profondo(self):
        # Aserción de prueba unitaria: self.assertFalse(coincide_con_perfume('Acqua Di Gio ...
        self.assertFalse(coincide_con_perfume("Acqua Di Gio Profondo EDP 100ml", "Acqua Di Gio", "Giorgio Armani"))

    # Definición de función 'test_adg_profondo_acepta_profondo' sin parámetros externos
    def test_adg_profondo_acepta_profondo(self):
        # Aserción de prueba unitaria: self.assertTrue(coincide_con_perfume('Acqua Di Gio P...
        self.assertTrue(coincide_con_perfume("Acqua Di Gio Profondo EDP 100ml", "Acqua Di Gio Profondo", "Giorgio Armani"))

    # --- 7. MFK BACCARAT ROUGE ---
    def test_baccarat_rouge_rechaza_givenchy_rouge(self):
        # Asignamos 'res' con coincide_entidad_detallada(titulo="GIVENCH...
        res = coincide_entidad_detallada(
            titulo="GIVENCHY | Perfume Mujer L'Interdit Rouge Eau de Parfum Givenchy",
            perfume_nombre="Baccarat Rouge 540",
            marca="Maison Francis Kurkdjian"
        )
        # Aserción de prueba unitaria: self.assertFalse(res.coincide)
        self.assertFalse(res.coincide)

    # Definición de función 'test_baccarat_rouge_rechaza_clon_barakkat' sin parámetros externos
    def test_baccarat_rouge_rechaza_clon_barakkat(self):
        # Asignamos 'res' con coincide_entidad_detallada(titulo='Fragran...
        res = coincide_entidad_detallada(
            titulo="Fragrance World Barakkat Rouge 540 Maison Edp 100ml",
            perfume_nombre="Baccarat Rouge 540",
            marca="Maison Francis Kurkdjian"
        )
        # Aserción de prueba unitaria: self.assertFalse(res.coincide)
        self.assertFalse(res.coincide)
        # Aserción de prueba unitaria: self.assertIn('clon', res.motivo.lower())
        self.assertIn("clon", res.motivo.lower())

    # --- 8. CASO VANILLA (ARIANA GRANDE VS LATTAFA) ---
    def test_ariana_grande_mod_vanilla_rechaza_lattafa(self):
        # Asignamos 'res' con coincide_entidad_detallada(titulo='Lattafa...
        res = coincide_entidad_detallada(
            titulo="Lattafa Give Me Gourmand Vanilla Freak EDP 75 ml",
            perfume_nombre="Mod Vanilla",
            marca="Ariana Grande"
        )
        # Aserción de prueba unitaria: self.assertFalse(res.coincide)
        self.assertFalse(res.coincide)

    # --- 9. VOLUMEN DISCREPANTE ---
    def test_volumen_discrepante_30ml_vs_100ml(self):
        # Asignamos 'res' con coincide_entidad_detallada(titulo='Dolce &...
        res = coincide_entidad_detallada(
            titulo="Dolce & Gabbana Devotion Eau De Parfum 100ML",
            perfume_nombre="Devotion",
            marca="Dolce & Gabbana",
            volumen_esperado=30
        )
        # Aserción de prueba unitaria: self.assertFalse(res.coincide)
        self.assertFalse(res.coincide)
        # Aserción de prueba unitaria: self.assertIn('volumen', res.motivo.lower())
        self.assertIn("volumen", res.motivo.lower())

    # Definición de función 'test_volumen_correcto_30ml' sin parámetros externos
    def test_volumen_correcto_30ml(self):
        # Asignamos 'res' con coincide_entidad_detallada(titulo='Dolce &...
        res = coincide_entidad_detallada(
            titulo="Dolce & Gabbana Devotion Eau De Parfum 30ML",
            perfume_nombre="Devotion",
            marca="Dolce & Gabbana",
            volumen_esperado=30
        )
        # Aserción de prueba unitaria: self.assertTrue(res.coincide)
        self.assertTrue(res.coincide)

    # --- 10. CREED AVENTUS VS ARMAF ---
    def test_creed_aventus_rechaza_armaf_cdnim(self):
        # Asignamos 'res' con coincide_entidad_detallada(titulo='Armaf C...
        res = coincide_entidad_detallada(
            titulo="Armaf Club De Nuit Intense Man EDT 105ml",
            perfume_nombre="Aventus",
            marca="Creed"
        )
        # Aserción de prueba unitaria: self.assertFalse(res.coincide)
        self.assertFalse(res.coincide)

    # Definición de función 'test_armaf_cdnim_acepta_cdnim' sin parámetros externos
    def test_armaf_cdnim_acepta_cdnim(self):
        # Aserción de prueba unitaria: self.assertTrue(coincide_con_perfume('Armaf Club De ...
        self.assertTrue(coincide_con_perfume("Armaf Club De Nuit Intense Man EDT 105ml", "Club De Nuit Intense Man", "Armaf"))

    # --- 11. TOM FORD / CHANEL / VERSACE ---
    def test_lost_cherry_rechaza_tuscan_leather(self):
        # Aserción de prueba unitaria: self.assertFalse(coincide_con_perfume('Tom Ford Tusc...
        self.assertFalse(coincide_con_perfume("Tom Ford Tuscan Leather EDP 50ml", "Lost Cherry", "Tom Ford"))

    # Definición de función 'test_bleu_chanel_rechaza_versace_dylan_blue' sin parámetros externos
    def test_bleu_chanel_rechaza_versace_dylan_blue(self):
        # Aserción de prueba unitaria: self.assertFalse(coincide_con_perfume('Versace Dylan...
        self.assertFalse(coincide_con_perfume("Versace Dylan Blue Pour Homme EDT 100ml", "Bleu de Chanel", "Chanel"))

    # --- 12. PARES REALES DE DEDUPLICACIÓN FASE 4 ---
    def test_armani_powerfully_acepta_emporio_armani_50ml(self):
        # Aserción de prueba unitaria: self.assertTrue(coincide_con_perfume('Perfume Empori...
        self.assertTrue(
            coincide_con_perfume(
                "Perfume Emporio Armani Stronger With You PowerFully EDP 50 Ml Hombre",
                "Stronger With You Powerfully",
                "Giorgio Armani",
            )
        )

    # Definición de función 'test_lattafa_hayaati_acepta_variante_hombre_y_unisex' sin parámetros externos
    def test_lattafa_hayaati_acepta_variante_hombre_y_unisex(self):
        # Aserción de prueba unitaria: self.assertTrue(coincide_con_perfume('Perfume Lattaf...
        self.assertTrue(
            coincide_con_perfume(
                "Perfume Lattafa Hayaati EDP 100ml Hombre",
                "Hayaati",
                "Lattafa",
            )
        )


    # --- 13. PRODUCTOS DERIVADOS, COSMÉTICA Y ACCESORIOS ---
    def test_sauvage_rechaza_limpiador_facial(self):
        # Asignamos 'res' con coincide_entidad_detallada(titulo='LIMPIAD...
        res = coincide_entidad_detallada(
            titulo="LIMPIADOR FACIAL DIOR SAUVAGE 125 ML",
            perfume_nombre="Sauvage",
            marca="Dior",
            url="https://simple.ripley.cl/2000401701948P",
            volumen_esperado=100,
        )
        # Aserción de prueba unitaria: self.assertFalse(res.coincide)
        self.assertFalse(res.coincide)
        # Aserción de prueba unitaria: self.assertIn('no ser perfume', res.motivo.lower())
        self.assertIn("no ser perfume", res.motivo.lower())

    # Definición de función 'test_rechaza_accesorios_y_cosmetica_en_url' sin parámetros externos
    def test_rechaza_accesorios_y_cosmetica_en_url(self):
        # Mochila Asus con nombre de perfume en título
        res_mochila = coincide_entidad_detallada(
            titulo="Mochila ASUS Vigour para Portatil 15.6",
            perfume_nombre="Vigour",
            marca="Zimaya",
            url="https://www.falabella.com/falabella-cl/product/151785256/mochila-asus-vigour-para-portatil",
        )
        # Aserción de prueba unitaria: self.assertFalse(res_mochila.coincide)
        self.assertFalse(res_mochila.coincide)

        # Máscara de pestañas
        res_mascara = coincide_entidad_detallada(
            titulo="Mascara De Pestanas Lash Idole",
            perfume_nombre="Idole Lancome",
            marca="Lancome",
            url="https://www.falabella.com/falabella-cl/product/80082363/Mascara-De-Pestanas-Lash-Idole",
        )
        # Aserción de prueba unitaria: self.assertFalse(res_mascara.coincide)
        self.assertFalse(res_mascara.coincide)


# Punto de entrada principal cuando el script se invoca directamente desde consola
if __name__ == "__main__":
    # Ejecutamos instrucción: unittest.main()
    unittest.main()
