# -*- coding: utf-8 -*-
"""
Tests de Deduplicación, Sanitización de Formatos y Manejo Instantáneo de Errores 404
-----------------------------------------------------------------------------------
Verifica:
1. Rechazo de categorías de tienda (breadcrumbs) como marcas y extracción desde título.
2. Exclusión estricta de ambientadores, body sprays y desodorantes de variantes EDP/EDT.
3. Retiro inmediato (fail-fast) de ofertas que responden HTTP 404 en el registrador de fallos.
4. Limpieza canónica de nombres preservando flankers clave.
"""

# Importación de librería estándar o dependencia externa (unittest)
import unittest
# Importación de componentes (patch) desde el módulo 'unittest.mock'
from unittest.mock import patch
# Importación de componentes (ALIAS_MARCA, generos_compatibles, normalizar_marca_canonica, limpiar_nombre_perfume, ...) desde el módulo 'APP.backend.normalizador'
from APP.backend.normalizador import (
    ALIAS_MARCA,
    generos_compatibles,
    normalizar_marca_canonica,
    limpiar_nombre_perfume,
    es_producto_perfume_valido,
    detectar_formato_oferta,
    MARCAS_INVALIDAS_CATALOGO,
)
# Importación de componentes (registrar_fallo_scraping, init_db, get_db_cursor) desde el módulo 'APP.backend.database'
from APP.backend.database import registrar_fallo_scraping, init_db, get_db_cursor


# Definición de clase 'TestDeduplicacionYSanitizacion' que modela la estructura y lógica del componente
class TestDeduplicacionYSanitizacion(unittest.TestCase):

    # Definición de función 'setUp' sin parámetros externos
    def setUp(self):
        # Ejecutamos instrucción: init_db()
        init_db()

    # Definición de función 'test_01_marcas_falsas_retornan_vacio_y_se_descartan' sin parámetros externos
    def test_01_marcas_falsas_retornan_vacio_y_se_descartan(self):
        # - ¿Qué hace esta prueba?:
        # Verifica que cualquier categoría web ('Perfumes femeninos', 'Tester Mujer', etc.)
        # sea identificada como inválida y retornada como cadena vacía para evitar
        # fragmentar el catálogo en marcas espurias.
        falsas = [
            "Perfumes femeninos",
            "Perfumes masculinos",
            "Perfumes unisex",
            "Tester Mujer",
            "Tester Hombre",
            "Testers",
            "Tester",
            "Perfume Mujer",
            "Perfume Hombre",
            "Fragancia",
        ]
        # Recorremos iterativamente cada 'f' en falsas
        for f in falsas:
            # Aserción de prueba unitaria: self.assertEqual(normalizar_marca_canonica(f), '', f...
            self.assertEqual(
                normalizar_marca_canonica(f),
                "",
                f"La categoría '{f}' debió ser descartada como marca."
            )

    # Definición de función 'test_02_exclusion_estricta_de_body_sprays_y_ambientales' sin parámetros externos
    def test_02_exclusion_estricta_de_body_sprays_y_ambientales(self):
        # - ¿Qué hace esta prueba?:
        # Comprueba que productos que no son frascos individuales de perfume (ambientales,
        # sprays corporales, velas) sean excluidos del flujo principal de perfumes.
        no_perfumes = [
            ("Lattafa Badee Al Oud Sublime All Over Spray 150ml", "Lattafa"),
            ("Desodorante Ambiental Lattafa 300 ml", "Lattafa"),
            ("Perfume Ambiental Badee Al Oud 300ml", "Lattafa"),
            ("Victoria's Secret Body Mist 250ml", "Victoria's Secret"),
            ("Armaf Club De Nuit Body Spray 200ml", "Armaf"),
            ("Vela Aromatica Scented Candle 100g", "Dior"),
        ]
        # Recorremos iterativamente cada '(titulo, marca)' en no_perfumes
        for titulo, marca in no_perfumes:
            # Asignamos 'valido' con es_producto_perfume_valido(titulo, marca=m...
            valido = es_producto_perfume_valido(titulo, marca=marca)
            # Aserción de prueba unitaria: self.assertFalse(valido, f"El producto '{titulo}' de...
            self.assertFalse(
                valido,
                f"El producto '{titulo}' debió ser marcado como inválido para perfume EDP/EDT."
            )

    # Definición de función 'test_03_limpieza_de_nombres_con_conectores_de_marca' sin parámetros externos
    def test_03_limpieza_de_nombres_con_conectores_de_marca(self):
        # - ¿Qué hace esta prueba?:
        # Verifica que títulos de e-commerce como 'Badee Al Oud Sublime de Lattafa'
        # o 'Eros de Versace' se canonicen exactamente sin duplicar la marca ni crear islas.
        casos = [
            ("Badee Al Oud Sublime De Lattafa EDP", "Lattafa", "Badee Al Oud Sublime"),
            ("Lattafa Badee Al Oud Sublime EDP 100 ml Unisex", "Lattafa", "Badee Al Oud Sublime"),
            ("Eros De Versace Eau De Toilette 100ml", "Versace", "Eros"),
            ("Sauvage Eau de Parfum de Dior 100ml", "Dior", "Sauvage"),
        ]
        # Recorremos iterativamente cada '(raw, marca, esperado)' en casos
        for raw, marca, esperado in casos:
            # Asignamos 'limpio' con limpiar_nombre_perfume(raw, marca)
            limpio = limpiar_nombre_perfume(raw, marca)
            # Aserción de prueba unitaria: self.assertEqual(limpio, esperado, f"Fallo limpiando...
            self.assertEqual(
                limpio,
                esperado,
                f"Fallo limpiando '{raw}' con marca '{marca}'. Esperado '{esperado}', obtenido '{limpio}'"
            )

    # Definición de función 'test_04_fallo_404_desactiva_inmediatamente_oferta_sqlite' (parámetros: _mock_sb)
    @patch("APP.backend.database.is_supabase_disponible", return_value=False)
    def test_04_fallo_404_desactiva_inmediatamente_oferta_sqlite(self, _mock_sb):
        # - ¿Qué hace esta prueba?:
        # Valida que un error 404 (página eliminada) apague inmediatamente la oferta
        # (en_stock = False, estado = 'requiere_revision') sin esperar 5 ciclos fallidos.
        with get_db_cursor(commit=True) as cursor:
            # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
            cursor.execute("SELECT id FROM tiendas LIMIT 1;")
            # Asignamos 't_row' con cursor.fetchone()
            t_row = cursor.fetchone()
            # Asignamos 'tienda_id' con t_row['id'] if t_row else 1
            tienda_id = t_row["id"] if t_row else 1

            # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
            cursor.execute("SELECT id FROM variantes_perfume LIMIT 1;")
            # Asignamos 'v_row' con cursor.fetchone()
            v_row = cursor.fetchone()
            # Asignamos 'variante_id' con v_row['id'] if v_row else 1
            variante_id = v_row["id"] if v_row else 1

            # Insertar oferta activa de prueba con 0 fallos
            cursor.execute("""
            INSERT OR REPLACE INTO ofertas_actuales (
                id, variante_id, tienda_id, precio_actual, precio_normal, en_stock, estado, fallos_consecutivos
            ) VALUES (99999, ?, ?, 29990, 39990, 1, 'activa', 0);
            """, (variante_id, tienda_id))

        # Registrar fallo 404 (simulando que el producto fue borrado en la tienda)
        res = registrar_fallo_scraping(
            tienda_id=tienda_id,
            variante_id=variante_id,
            mensaje="HTTP 404 Not Found: La página ya no existe en el catálogo",
        )

        # Debe marcar de inmediato requiere_revision y en_stock = False con solo 1 fallo
        self.assertEqual(res.get("estado"), "requiere_revision")
        # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
        self.assertFalse(res.get("en_stock"))
        # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
        self.assertEqual(res.get("fallos_consecutivos"), 1)

    # Definición de función 'test_05_alias_marca_declarativos_y_armani_powerfully_x3' sin parámetros externos
    def test_05_alias_marca_declarativos_y_armani_powerfully_x3(self):
        # - ¿Qué hace esta prueba?:
        # Verifica que las 3 variantes reales de Armani Stronger With You Powerfully y sub-marcas
        # de ALIAS_MARCA colapsen exactamente al mismo nombre canónico sin prefijos residuales.
        self.assertIn("Giorgio Armani", ALIAS_MARCA)
        # Asignamos 'variantes_armani' con [('Stronger With You Powerfully EDP', 'Gio...
        variantes_armani = [
            ("Stronger With You Powerfully EDP", "Giorgio Armani"),
            ("Armani Stronger With You Powerfully EDP", "Giorgio Armani"),
            ("Stronger With You Powerfully De Emporio Armani EDP", "Giorgio Armani"),
            ("Perfume Emporio Armani Stronger With You PowerFully EDP 50 Ml Hombre", "Emporio Armani"),
        ]
        # Asignamos 'nombres' con {limpiar_nombre_perfume(raw, m) for raw, m...
        nombres = {limpiar_nombre_perfume(raw, m) for raw, m in variantes_armani}
        # Aserción de prueba unitaria: self.assertEqual(nombres, {'Stronger With You Powerf...
        self.assertEqual(nombres, {"Stronger With You Powerfully"})

        # Asignamos 'otros_alias' con [('Christian Dior Sauvage EDP 100ml', 'Dio...
        otros_alias = [
            ("Christian Dior Sauvage EDP 100ml", "Dior", "Sauvage"),
            ("YSL Libre Eau de Parfum 90ml Mujer", "Yves Saint Laurent", "Libre"),
            ("D&G Light Blue EDT 100ml", "Dolce & Gabbana", "Light Blue"),
            ("Thierry Mugler Angel EDP 50ml", "Mugler", "Angel"),
            ("MFK Baccarat Rouge 540 EDP 70ml", "Maison Francis Kurkdjian", "Baccarat Rouge 540"),
            ("Rabanne 1 Million EDT 100ml", "Paco Rabanne", "1 Million"),
        ]
        # Recorremos iterativamente cada '(raw, marca, esp)' en otros_alias
        for raw, marca, esp in otros_alias:
            # Aserción de prueba unitaria: self.assertEqual(limpiar_nombre_perfume(raw, marca),...
            self.assertEqual(limpiar_nombre_perfume(raw, marca), esp)

    # Definición de función 'test_06_compatibilidad_generos_y_pares_reales_catalogo' sin parámetros externos
    def test_06_compatibilidad_generos_y_pares_reales_catalogo(self):
        # - ¿Qué hace esta prueba?:
        # Verifica la regla de compatibilidad de géneros en los pares reales detectados en §1:
        # Romance (Mujer/Unisex), Hayaati (Hombre/Unisex), 212 VIP (Mujer/Unisex) se unifican
        # conservando el género específico, mientras Hombre vs Mujer jamás se fusiona automáticamente.
        self.assertEqual(generos_compatibles("Mujer", "Unisex"), (True, "Mujer"))
        # Aserción de prueba unitaria: self.assertEqual(generos_compatibles('Unisex', 'Homb...
        self.assertEqual(generos_compatibles("Unisex", "Hombre"), (True, "Hombre"))
        # Aserción de prueba unitaria: self.assertEqual(generos_compatibles('Unisex', 'Unis...
        self.assertEqual(generos_compatibles("Unisex", "Unisex"), (True, "Unisex"))
        # Aserción de prueba unitaria: self.assertEqual(generos_compatibles('Hombre', 'Muje...
        self.assertEqual(generos_compatibles("Hombre", "Mujer"), (False, ""))
        # Aserción de prueba unitaria: self.assertEqual(generos_compatibles('Mujer', 'Hombr...
        self.assertEqual(generos_compatibles("Mujer", "Hombre"), (False, ""))

        # Asignamos 'pares_reales' con [('Ralph Lauren', 'Romance EDP 100ml Mujer...
        pares_reales = [
            ("Ralph Lauren", "Romance EDP 100ml Mujer", "Mujer", "Ralph Lauren Romance EDP 100ml", "Unisex", "Mujer"),
            ("Lattafa", "Lattafa Hayaati EDP 100ml Hombre", "Hombre", "Hayaati EDP 100ml Unisex", "Unisex", "Hombre"),
            ("Carolina Herrera", "212 VIP EDP 80ml Mujer", "Mujer", "Carolina Herrera 212 VIP EDP", "Unisex", "Mujer"),
        ]
        # Recorremos iterativamente cada '(marca, t1, g1, t2, g2, g_e...' en pares_reales
        for marca, t1, g1, t2, g2, g_esperado in pares_reales:
            # Asignamos 'k1' con (normalizar_marca_canonica(marca).lower(),...
            k1 = (normalizar_marca_canonica(marca).lower(), limpiar_nombre_perfume(t1, marca).lower())
            # Asignamos 'k2' con (normalizar_marca_canonica(marca).lower(),...
            k2 = (normalizar_marca_canonica(marca).lower(), limpiar_nombre_perfume(t2, marca).lower())
            # Aserción de prueba unitaria: self.assertEqual(k1, k2)
            self.assertEqual(k1, k2)
            # Asignamos '(ok, g_res)' con generos_compatibles(g1, g2)
            ok, g_res = generos_compatibles(g1, g2)
            # Aserción de prueba unitaria: self.assertTrue(ok)
            self.assertTrue(ok)
            # Aserción de prueba unitaria: self.assertEqual(g_res, g_esperado)
            self.assertEqual(g_res, g_esperado)


# Punto de entrada principal cuando el script se invoca directamente desde consola
if __name__ == "__main__":
    # Ejecutamos instrucción: unittest.main()
    unittest.main()
