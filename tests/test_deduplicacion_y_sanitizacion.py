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

import unittest
from unittest.mock import patch
from APP.backend.normalizador import (
    normalizar_marca_canonica,
    limpiar_nombre_perfume,
    es_producto_perfume_valido,
    detectar_formato_oferta,
    MARCAS_INVALIDAS_CATALOGO,
)
from APP.backend.database import registrar_fallo_scraping, init_db, get_db_cursor


class TestDeduplicacionYSanitizacion(unittest.TestCase):

    def setUp(self):
        init_db()

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
        for f in falsas:
            self.assertEqual(
                normalizar_marca_canonica(f),
                "",
                f"La categoría '{f}' debió ser descartada como marca."
            )

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
        for titulo, marca in no_perfumes:
            valido = es_producto_perfume_valido(titulo, marca=marca)
            self.assertFalse(
                valido,
                f"El producto '{titulo}' debió ser marcado como inválido para perfume EDP/EDT."
            )

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
        for raw, marca, esperado in casos:
            limpio = limpiar_nombre_perfume(raw, marca)
            self.assertEqual(
                limpio,
                esperado,
                f"Fallo limpiando '{raw}' con marca '{marca}'. Esperado '{esperado}', obtenido '{limpio}'"
            )

    @patch("APP.backend.database.is_supabase_disponible", return_value=False)
    def test_04_fallo_404_desactiva_inmediatamente_oferta_sqlite(self, _mock_sb):
        # - ¿Qué hace esta prueba?:
        # Valida que un error 404 (página eliminada) apague inmediatamente la oferta
        # (en_stock = False, estado = 'requiere_revision') sin esperar 5 ciclos fallidos.
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("SELECT id FROM tiendas LIMIT 1;")
            t_row = cursor.fetchone()
            tienda_id = t_row["id"] if t_row else 1

            cursor.execute("SELECT id FROM variantes_perfume LIMIT 1;")
            v_row = cursor.fetchone()
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
        self.assertFalse(res.get("en_stock"))
        self.assertEqual(res.get("fallos_consecutivos"), 1)


if __name__ == "__main__":
    unittest.main()
