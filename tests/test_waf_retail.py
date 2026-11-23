# -*- coding: utf-8 -*-
"""
Pruebas unitarias aisladas para la capa anti-WAF retail (Fase 2).
Verifica:
  1. Sesiones simuladas (`MagicMock`) nunca disparan llamadas reales con `curl_cffi`.
  2. En GitHub Actions sin proxy, Falabella preserva `requests` (evitando el 403 de `curl_cffi` demostrado en `probe_waf`).
  3. Fuera de Actions (o en Paris), un 403 en `requests` cae a `curl_cffi(impersonate='chrome120')`.
  4. En Ripley (`prefer_curl_cffi=True`), `curl_cffi` actúa como cliente primario cuando la sesión es `requests.Session`.
"""

# Importación de librería estándar o dependencia externa (os)
import os
# Importación de librería estándar o dependencia externa (unittest)
import unittest
# Importación de componentes (MagicMock, patch) desde el módulo 'unittest.mock'
from unittest.mock import MagicMock, patch
# Importación de librería estándar o dependencia externa (requests)
import requests

# Importación de librería estándar o dependencia externa (APP.backend.scraper_periodico)
import APP.backend.scraper_periodico as sp


# Definición de clase 'TestWafRetailFase2' que modela la estructura y lógica del componente
class TestWafRetailFase2(unittest.TestCase):
    # Definición de función 'test_01_mock_session_no_invoca_curl_cffi_real' sin parámetros externos
    def test_01_mock_session_no_invoca_curl_cffi_real(self):
        # Asignamos 'mock_sess' con MagicMock()
        mock_sess = MagicMock()
        # Asignamos 'mock_resp' con MagicMock(status_code=403, text='Forbidden')
        mock_resp = MagicMock(status_code=403, text="Forbidden")
        # Asignamos 'mock_sess.get.return_value' con mock_resp
        mock_sess.get.return_value = mock_resp

        # Gestión automática de contexto y recursos para: patch.object(sp, 'curl_requests')
        with patch.object(sp, "curl_requests") as mock_cffi:
            # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
            res = sp._peticion_retail_resiliente(
                mock_sess,
                "https://www.paris.cl/perfume-test.html",
                headers={"User-Agent": "Test"},
                timeout=5,
                prefer_curl_cffi=True,
            )
            # Aserción de prueba unitaria: self.assertIs(res, mock_resp)
            self.assertIs(res, mock_resp)
            # Ejecutamos instrucción: mock_cffi.Session.assert_not_called()
            mock_cffi.Session.assert_not_called()

    # Definición de función 'test_02_falabella_en_github_actions_preserva_requests_sin_cffi' sin parámetros externos
    def test_02_falabella_en_github_actions_preserva_requests_sin_cffi(self):
        # Asignamos 'real_sess' con requests.Session()
        real_sess = requests.Session()
        # Asignamos 'resp_403' con MagicMock(status_code=403, text='Blocked')
        resp_403 = MagicMock(status_code=403, text="Blocked")

        # Gestión automática de contexto y recursos para: patch.object(real_sess, 'get', return_value=res...
        with patch.object(real_sess, "get", return_value=resp_403) as m_get, \
             patch.object(sp, "curl_requests") as mock_cffi, \
             patch.dict(os.environ, {"GITHUB_ACTIONS": "true", "RETAIL_PROXY_URL": ""}, clear=False):
            # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
            res = sp._peticion_retail_resiliente(
                real_sess,
                "https://www.falabella.com/falabella-cl/product/123/Test",
                headers={"User-Agent": "Test"},
                timeout=5,
                prefer_curl_cffi=False,
            )
            # Aserción de prueba unitaria: self.assertEqual(res.status_code, 403)
            self.assertEqual(res.status_code, 403)
            # Ejecutamos instrucción: m_get.assert_called_once()
            m_get.assert_called_once()
            # Ejecutamos instrucción: mock_cffi.Session.assert_not_called()
            mock_cffi.Session.assert_not_called()

    # Definición de función 'test_03_paris_403_usa_fallback_curl_cffi_exitoso' sin parámetros externos
    def test_03_paris_403_usa_fallback_curl_cffi_exitoso(self):
        # Asignamos 'real_sess' con requests.Session()
        real_sess = requests.Session()
        # Asignamos 'resp_403' con MagicMock(status_code=403, text='WAF')
        resp_403 = MagicMock(status_code=403, text="WAF")
        # Asignamos 'resp_200' con MagicMock(status_code=200, text='<html>OK<...
        resp_200 = MagicMock(status_code=200, text="<html>OK</html>")

        # Asignamos 'mock_ctx' con MagicMock()
        mock_ctx = MagicMock()
        # Asignamos 'mock_ctx.__enter__.return_value....' con resp_200
        mock_ctx.__enter__.return_value.get.return_value = resp_200

        # Gestión automática de contexto y recursos para: patch.object(real_sess, 'get', return_value=res...
        with patch.object(real_sess, "get", return_value=resp_403), \
             patch.object(sp, "curl_requests") as mock_cffi, \
             patch("APP.backend.scraper_periodico.time.sleep"):
            # Asignamos 'mock_cffi.Session.return_value' con mock_ctx
            mock_cffi.Session.return_value = mock_ctx
            # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
            res = sp._peticion_retail_resiliente(
                real_sess,
                "https://www.paris.cl/perfume-libre-999.html",
                headers={"User-Agent": "Test", "Referer": "https://www.paris.cl/"},
                timeout=5,
                prefer_curl_cffi=False,
            )
            # Aserción de prueba unitaria: self.assertEqual(res.status_code, 200)
            self.assertEqual(res.status_code, 200)
            # Ejecutamos instrucción: mock_cffi.Session.assert_called_once()
            mock_cffi.Session.assert_called_once()

    # Definición de función 'test_04_ripley_usa_curl_cffi_primario_con_sesion_real' sin parámetros externos
    def test_04_ripley_usa_curl_cffi_primario_con_sesion_real(self):
        # Asignamos 'real_sess' con requests.Session()
        real_sess = requests.Session()
        # Asignamos 'resp_200' con MagicMock(status_code=200, text='<html>Rip...
        resp_200 = MagicMock(status_code=200, text="<html>Ripley OK</html>")
        # Asignamos 'mock_ctx' con MagicMock()
        mock_ctx = MagicMock()
        # Asignamos 'mock_ctx.__enter__.return_value....' con resp_200
        mock_ctx.__enter__.return_value.get.return_value = resp_200

        # Gestión automática de contexto y recursos para: patch.object(real_sess, 'get')
        with patch.object(real_sess, "get") as m_req_get, \
             patch.object(sp, "curl_requests") as mock_cffi:
            # Asignamos 'mock_cffi.Session.return_value' con mock_ctx
            mock_cffi.Session.return_value = mock_ctx
            # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
            res = sp._peticion_retail_resiliente(
                real_sess,
                "https://simple.ripley.cl/perfume-test-2000p",
                headers={"User-Agent": "Test"},
                timeout=5,
                prefer_curl_cffi=True,
            )
            # Aserción de prueba unitaria: self.assertEqual(res.status_code, 200)
            self.assertEqual(res.status_code, 200)
            # Ejecutamos instrucción: m_req_get.assert_not_called()
            m_req_get.assert_not_called()
            # Ejecutamos instrucción: mock_cffi.Session.assert_called_once()
            mock_cffi.Session.assert_called_once()


# Punto de entrada principal cuando el script se invoca directamente desde consola
if __name__ == "__main__":
    # Ejecutamos instrucción: unittest.main()
    unittest.main()

