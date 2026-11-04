# -*- coding: utf-8 -*-
"""
Pruebas unitarias aisladas para la capa anti-WAF retail (Fase 2).
Verifica:
  1. Sesiones simuladas (`MagicMock`) nunca disparan llamadas reales con `curl_cffi`.
  2. En GitHub Actions sin proxy, Falabella preserva `requests` (evitando el 403 de `curl_cffi` demostrado en `probe_waf`).
  3. Fuera de Actions (o en Paris), un 403 en `requests` cae a `curl_cffi(impersonate='chrome120')`.
  4. En Ripley (`prefer_curl_cffi=True`), `curl_cffi` actúa como cliente primario cuando la sesión es `requests.Session`.
"""

import os
import unittest
from unittest.mock import MagicMock, patch
import requests

import APP.backend.scraper_periodico as sp


class TestWafRetailFase2(unittest.TestCase):
    def test_01_mock_session_no_invoca_curl_cffi_real(self):
        mock_sess = MagicMock()
        mock_resp = MagicMock(status_code=403, text="Forbidden")
        mock_sess.get.return_value = mock_resp

        with patch.object(sp, "curl_requests") as mock_cffi:
            res = sp._peticion_retail_resiliente(
                mock_sess,
                "https://www.paris.cl/perfume-test.html",
                headers={"User-Agent": "Test"},
                timeout=5,
                prefer_curl_cffi=True,
            )
            self.assertIs(res, mock_resp)
            mock_cffi.Session.assert_not_called()

    def test_02_falabella_en_github_actions_preserva_requests_sin_cffi(self):
        real_sess = requests.Session()
        resp_403 = MagicMock(status_code=403, text="Blocked")

        with patch.object(real_sess, "get", return_value=resp_403) as m_get, \
             patch.object(sp, "curl_requests") as mock_cffi, \
             patch.dict(os.environ, {"GITHUB_ACTIONS": "true", "RETAIL_PROXY_URL": ""}, clear=False):
            res = sp._peticion_retail_resiliente(
                real_sess,
                "https://www.falabella.com/falabella-cl/product/123/Test",
                headers={"User-Agent": "Test"},
                timeout=5,
                prefer_curl_cffi=False,
            )
            self.assertEqual(res.status_code, 403)
            m_get.assert_called_once()
            mock_cffi.Session.assert_not_called()

    def test_03_paris_403_usa_fallback_curl_cffi_exitoso(self):
        real_sess = requests.Session()
        resp_403 = MagicMock(status_code=403, text="WAF")
        resp_200 = MagicMock(status_code=200, text="<html>OK</html>")

        mock_ctx = MagicMock()
        mock_ctx.__enter__.return_value.get.return_value = resp_200

        with patch.object(real_sess, "get", return_value=resp_403), \
             patch.object(sp, "curl_requests") as mock_cffi, \
             patch("APP.backend.scraper_periodico.time.sleep"):
            mock_cffi.Session.return_value = mock_ctx
            res = sp._peticion_retail_resiliente(
                real_sess,
                "https://www.paris.cl/perfume-libre-999.html",
                headers={"User-Agent": "Test", "Referer": "https://www.paris.cl/"},
                timeout=5,
                prefer_curl_cffi=False,
            )
            self.assertEqual(res.status_code, 200)
            mock_cffi.Session.assert_called_once()

    def test_04_ripley_usa_curl_cffi_primario_con_sesion_real(self):
        real_sess = requests.Session()
        resp_200 = MagicMock(status_code=200, text="<html>Ripley OK</html>")
        mock_ctx = MagicMock()
        mock_ctx.__enter__.return_value.get.return_value = resp_200

        with patch.object(real_sess, "get") as m_req_get, \
             patch.object(sp, "curl_requests") as mock_cffi:
            mock_cffi.Session.return_value = mock_ctx
            res = sp._peticion_retail_resiliente(
                real_sess,
                "https://simple.ripley.cl/perfume-test-2000p",
                headers={"User-Agent": "Test"},
                timeout=5,
                prefer_curl_cffi=True,
            )
            self.assertEqual(res.status_code, 200)
            m_req_get.assert_not_called()
            mock_cffi.Session.assert_called_once()


if __name__ == "__main__":
    unittest.main()
