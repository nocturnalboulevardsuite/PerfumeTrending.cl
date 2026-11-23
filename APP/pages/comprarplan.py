"""
PerfumeTrending.cl — Compra del Plan Premium con Mercado Pago (ambiente de prueba)
==================================================================================
- Detección en vivo de marca, tipo (débito/crédito) y banco emisor con el BIN de la tarjeta.
- Pago de prueba REAL con la API de Orders de Mercado Pago: la tarjeta se tokeniza con la
  Public Key y la orden se crea con el Access Token. Los pagos aparecen en el panel de
  Mercado Pago Developers > Pagos de prueba. No se cobra dinero real.
- Si no hay credenciales, el pago se simula (APRO aprueba; OTHE / FUND / SECU rechazan).
- Al aprobarse, el plan se guarda en la base de datos (`actualizar_plan_usuario`) con
  vigencia de 30 días, así que se conserva al cerrar e iniciar sesión.

Configuración (.streamlit/secrets.toml):

    [mercadopago]
    public_key = "APP_USR-..."     # Credenciales de prueba > Public Key
    access_token = "APP_USR-..."   # Credenciales de prueba > Access Token (nunca en el código)
"""

# Importación de librería estándar o dependencia externa (streamlit)
import streamlit as st
# Importación de librería estándar o dependencia externa (sys)
import sys
# Importación de librería estándar o dependencia externa (os)
import os
# Importación de librería estándar o dependencia externa (math)
import math
# Importación de librería estándar o dependencia externa (time)
import time
# Importación de librería estándar o dependencia externa (uuid)
import uuid
# Importación de librería estándar o dependencia externa (json)
import json
# Importación de librería estándar o dependencia externa (urllib.parse)
import urllib.parse
# Importación de librería estándar o dependencia externa (urllib.request)
import urllib.request
# Importación de librería estándar o dependencia externa (urllib.error)
import urllib.error
# Importación de componentes (datetime, date) desde el módulo 'datetime'
from datetime import datetime, date

# Configuración de rutas canónicas para importar backend y ui
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Asignamos 'BASE_DIR' con os.path.dirname(APP_DIR)
BASE_DIR = os.path.dirname(APP_DIR)
# Recorremos iterativamente cada '_p' en (APP_DIR, BASE_DIR)
for _p in (APP_DIR, BASE_DIR):
    # Evaluamos la condición lógica (_p not in sys.path) para controlar el flujo
    if _p not in sys.path:
        # Ejecutamos instrucción: sys.path.insert(0, _p)
        sys.path.insert(0, _p)

# Importación de componentes (PERFUME_SVG_FAVICON, clean_html, escape_html, get_theme_palette, ...) desde el módulo 'ui'
from ui import (
    PERFUME_SVG_FAVICON,
    clean_html as _shared_clean_html,
    escape_html,
    get_theme_palette,
    init_common_session_state,
)
# Importación de componentes (modal_autenticacion) desde el módulo 'auth_email'
from auth_email import modal_autenticacion

# Bloque try/except para manejo seguro de errores y resiliencia operativa
try:
    # Importación de componentes (obtener_perfil_usuario) desde el módulo 'backend.database'
    from backend.database import obtener_perfil_usuario
except Exception:
    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Importación de componentes (obtener_perfil_usuario) desde el módulo 'APP.backend.database'
        from APP.backend.database import obtener_perfil_usuario
    except Exception:
        # Asignamos 'obtener_perfil_usuario' con None
        obtener_perfil_usuario = None

# Persistencia del plan: si backend/database.py define `actualizar_plan_usuario`,
# el plan se guarda en Supabase; si no, queda activo solo durante la sesión.
try:
    # Importación de componentes (actualizar_plan_usuario) desde el módulo 'backend.database'
    from backend.database import actualizar_plan_usuario
except Exception:
    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Importación de componentes (actualizar_plan_usuario) desde el módulo 'APP.backend.database'
        from APP.backend.database import actualizar_plan_usuario
    except Exception:
        # Asignamos 'actualizar_plan_usuario' con None
        actualizar_plan_usuario = None


# Definición de función 'clean_html' (parámetros: html_str)
def clean_html(html_str: str) -> str:
    # Retornamos el resultado procesado (_shared_clean_html(html_str, join_char=' '))
    return _shared_clean_html(html_str, join_char=" ")


# =============================================================================
# 1. CONFIGURACIÓN Y PALETA
# =============================================================================
st.set_page_config(
    page_title="Activar Premium - PerfumeTrending",
    page_icon=PERFUME_SVG_FAVICON,
    layout="wide",
    initial_sidebar_state="collapsed",
)
# Ejecutamos instrucción: init_common_session_state()
init_common_session_state()

# Asignamos 'pal' con get_theme_palette()
pal = get_theme_palette()
# Asignamos 'is_dark' con pal.is_dark
is_dark = pal.is_dark
# Asignamos 'app_bg_css' con pal.app_bg_css
app_bg_css = pal.app_bg_css
# Asignamos 'text_color' con pal.text_color
text_color = pal.text_color
# Asignamos 'subtext_color' con pal.subtext_color
subtext_color = pal.subtext_color
# Asignamos 'btn_bg' con pal.btn_bg
btn_bg = pal.btn_bg
# Asignamos 'btn_text' con pal.btn_text
btn_text = pal.btn_text
# Asignamos 'btn_border' con pal.btn_border
btn_border = pal.btn_border
# Asignamos 'input_bg' con pal.input_bg
input_bg = pal.input_bg
# Asignamos 'input_text' con pal.input_text
input_text = pal.input_text
# Asignamos 'input_border' con pal.input_border
input_border = pal.input_border
# Evaluamos la condición lógica (not is_dark) para controlar el flujo
if not is_dark:
    # Asignamos 'app_bg_css' con 'background: #ffffff !important; backgroun...
    app_bg_css = "background: #ffffff !important; background-color: #ffffff !important;"
    # Asignamos 'text_color' con '#1c1917'
    text_color = "#1c1917"
    # Asignamos 'subtext_color' con '#6b6159'
    subtext_color = "#6b6159"
    # Asignamos 'btn_bg' con '#ffffff'
    btn_bg = "#ffffff"
    # Asignamos 'btn_text' con '#1c1917'
    btn_text = "#1c1917"
    # Asignamos 'btn_border' con '#d6cec5'
    btn_border = "#d6cec5"
    # Asignamos 'input_bg' con '#ffffff'
    input_bg = "#ffffff"
    # Asignamos 'input_text' con '#1c1917'
    input_text = "#1c1917"
    # Asignamos 'input_border' con '#d6cec5'
    input_border = "#d6cec5"

# Asignamos 'card_bg' con btn_bg
card_bg = btn_bg
# Asignamos 'border_color' con 'rgba(255, 255, 255, 0.10)' if is_dark els...
border_color = "rgba(255, 255, 255, 0.10)" if is_dark else "#e6e1db"
# Asignamos 'surface_soft' con 'rgba(255, 255, 255, 0.03)' if is_dark els...
surface_soft = "rgba(255, 255, 255, 0.03)" if is_dark else "#faf8f5"
# Asignamos 'accent' con '#d83737'
accent = "#d83737"
# Asignamos 'gold_plan' con '#e2b857' if is_dark else '#a87b1c'
gold_plan = "#e2b857" if is_dark else "#a87b1c"
# Asignamos 'gold_plan_soft' con 'rgba(226, 184, 87, 0.12)' if is_dark else...
gold_plan_soft = "rgba(226, 184, 87, 0.12)" if is_dark else "rgba(168, 123, 28, 0.08)"
# Asignamos 'ok_green' con '#4ade80' if is_dark else '#15803d'
ok_green = "#4ade80" if is_dark else "#15803d"
# Asignamos 'font_sans' con "'Manrope', -apple-system, BlinkMacSystemF...
font_sans = "'Manrope', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"

# Asignamos 'PRECIO_PREMIUM' con 2000
PRECIO_PREMIUM = 2000

# Tarjetas de prueba oficiales de Mercado Pago Chile (docs: "Tarjetas de prueba").
TARJETAS_PRUEBA = {
    "Débito": {"num": "4023 6535 2391 4373", "venc": "11/30", "cvv": "123"},   # Visa Débito
    "Crédito": {"num": "5416 7526 0258 2580", "venc": "11/30", "cvv": "123"},  # Mastercard
}
# Nombre del titular en el sandbox de Mercado Pago -> resultado del pago
RESULTADOS_SANDBOX = {
    "OTHE": "Pago rechazado por un error general del emisor.",
    "FUND": "Pago rechazado por saldo insuficiente.",
    "SECU": "Pago rechazado: el código de seguridad no es válido.",
    "EXPI": "Pago rechazado por un problema con la fecha de vencimiento.",
    "CALL": "Pago rechazado: el banco requiere autorizar la compra.",
    "LOCK": "Pago rechazado: la tarjeta está bloqueada.",
}


# Definición de función '_mp_access_token' sin parámetros externos
def _mp_access_token():
    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Evaluamos la condición lógica ('mercadopago' in st.secrets) para controlar el flujo
        if "mercadopago" in st.secrets:
            # Asignamos 'tk' con st.secrets['mercadopago'].get('access_token')
            tk = st.secrets["mercadopago"].get("access_token")
            # Evaluamos la condición lógica (tk) para controlar el flujo
            if tk:
                # Retornamos el resultado procesado (str(tk))
                return str(tk)
    except Exception:
        # Ejecutamos instrucción: pass
        pass
    # Retornamos el resultado procesado (os.environ.get('MP_ACCESS_TOKEN') or '')
    return os.environ.get("MP_ACCESS_TOKEN") or ""


# Definición de función '_post_json' (parámetros: url, payload, headers)
def _post_json(url, payload, headers=None):
    """POST JSON con urllib. Devuelve (codigo_http, respuesta_dict) incluso si la API responde con error."""
    # Procesamiento de serialización o deserialización de estructura JSON
    cuerpo = json.dumps(payload).encode("utf-8")
    # Asignamos 'h' con {'Content-Type': 'application/json', 'Acce...
    h = {"Content-Type": "application/json", "Accept": "application/json", "User-Agent": "PerfumeTrending/1.0"}
    # Ejecutamos instrucción: h.update(headers or {})
    h.update(headers or {})
    # Asignamos 'req' con urllib.request.Request(url, data=cuerpo, h...
    req = urllib.request.Request(url, data=cuerpo, headers=h, method="POST")
    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Gestión automática de contexto y recursos para: urllib.request.urlopen(req, timeout=20)
        with urllib.request.urlopen(req, timeout=20) as resp:
            # Retornamos el resultado procesado ((resp.status, json.loads(resp.read().decode('ut...)
            return resp.status, json.loads(resp.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as err:
        # Bloque try/except para manejo seguro de errores y resiliencia operativa
        try:
            # Retornamos el resultado procesado ((err.code, json.loads(err.read().decode('utf-8'...)
            return err.code, json.loads(err.read().decode("utf-8") or "{}")
        except Exception:
            # Retornamos el resultado procesado ((err.code, {}))
            return err.code, {}


# Definición de función '_error_mp' (parámetros: data)
def _error_mp(data):
    """Extrae un mensaje legible de una respuesta de error de Mercado Pago."""
    # Evaluamos la condición lógica (not isinstance(data, dict)) para controlar el flujo
    if not isinstance(data, dict):
        # Retornamos el resultado procesado ('')
        return ""
    # Asignamos 'errores' con data.get('errors') or data.get('cause') or []
    errores = data.get("errors") or data.get("cause") or []
    # Evaluamos la condición lógica (isinstance(errores, list) and errores) para controlar el flujo
    if isinstance(errores, list) and errores:
        # Asignamos 'e' con errores[0] or {}
        e = errores[0] or {}
        # Retornamos el resultado procesado (str(e.get('message') or e.get('description') or...)
        return str(e.get("message") or e.get("description") or e.get("code") or "")
    # Retornamos el resultado procesado (str(data.get('message') or data.get('error') or...)
    return str(data.get("message") or data.get("error") or "")


# Asignamos '_DETALLES_RECHAZO' con {'cc_rejected_other_reason': 'el emisor re...
_DETALLES_RECHAZO = {
    "cc_rejected_other_reason": "el emisor rechazó el pago",
    "rejected_by_issuer": "el emisor rechazó el pago",
    "card_insufficient_amount": "saldo insuficiente",
    "cc_rejected_insufficient_amount": "saldo insuficiente",
    "bad_filled_card_data": "los datos de la tarjeta son incorrectos",
    "cc_rejected_bad_filled_security_code": "el código de seguridad no es válido",
    "invalid_card_token": "el token de la tarjeta venció, intente nuevamente",
    "card_disabled": "la tarjeta está deshabilitada",
    "high_risk": "el pago fue rechazado por prevención de fraude",
    "amount_limit_exceeded": "el monto supera el límite de la tarjeta",
    "max_attempts_exceeded": "se superó el número de intentos",
}


# Definición de función 'pagar_con_mercadopago' (parámetros: public_key, access_token, numero, nombre, ...)
def pagar_con_mercadopago(public_key, access_token, numero, nombre, venc, cvv, documento, info, referencia):
    """Pago de prueba REAL en el ambiente de prueba de Mercado Pago (API de Orders).
    1) Tokeniza la tarjeta con la Public Key.  2) Crea y procesa la orden con el Access Token.
    Devuelve dict con: ok, estado, detalle, orden_id, pago_id, mensaje."""
    # Asignamos '(mes, anio)' con parsear_vencimiento(venc)
    mes, anio = parsear_vencimiento(venc)
    # Asignamos '(cod, tok)' con _post_json(f'https://api.mercadopago.com/v...
    cod, tok = _post_json(
        f"https://api.mercadopago.com/v1/card_tokens?public_key={urllib.parse.quote(public_key)}",
        {
            "card_number": numero,
            "expiration_month": mes,
            "expiration_year": anio,
            "security_code": cvv,
            "cardholder": {"name": nombre, "identification": {"type": "otro", "number": documento or "123456789"}},
        },
    )
    # Asignamos 'token' con tok.get('id') if isinstance(tok, dict) els...
    token = tok.get("id") if isinstance(tok, dict) else None
    # Evaluamos la condición lógica (cod >= 300 or not token) para controlar el flujo
    if cod >= 300 or not token:
        # Retornamos el resultado procesado ({'ok': False, 'mensaje': 'Mercado Pago no pudo ...)
        return {"ok": False, "mensaje": "Mercado Pago no pudo validar la tarjeta" + (f": {_error_mp(tok)}" if _error_mp(tok) else ".")}

    # Asignamos 'pm_id' con (info or {}).get('id') or ''
    pm_id = (info or {}).get("id") or ""
    # Asignamos 'pm_tipo' con (info or {}).get('tipo') or 'credit_card'
    pm_tipo = (info or {}).get("tipo") or "credit_card"
    # Evaluamos la condición lógica (not pm_id) para controlar el flujo
    if not pm_id:
        # Asignamos 'marca' con (info or {}).get('marca', '')
        marca = (info or {}).get("marca", "")
        # Asignamos 'base' con {'Visa': 'visa', 'Mastercard': 'master', '...
        base = {"Visa": "visa", "Mastercard": "master", "American Express": "amex", "Diners Club": "diners"}.get(marca, "visa")
        # Asignamos 'pm_id' con 'deb' + base if pm_tipo == 'debit_card' an...
        pm_id = ("deb" + base) if pm_tipo == "debit_card" and base in ("visa", "master") else base

    # Asignamos 'monto' con str(PRECIO_PREMIUM)
    monto = str(PRECIO_PREMIUM)
    # Asignamos '(cod, orden)' con _post_json('https://api.mercadopago.com/v1...
    cod, orden = _post_json(
        "https://api.mercadopago.com/v1/orders",
        {
            "type": "online",
            "processing_mode": "automatic",
            "external_reference": referencia,
            "total_amount": monto,
            "description": "PerfumeTrending - Plan Premium (1 mes)",
            # En el ambiente de prueba Mercado Pago exige un correo terminado en @testuser.com
            "payer": {"email": "test@testuser.com"},
            "transactions": {"payments": [{
                "amount": monto,
                "payment_method": {"id": pm_id, "type": pm_tipo, "token": token, "installments": 1},
            }]},
        },
        headers={"Authorization": f"Bearer {access_token}", "X-Idempotency-Key": uuid.uuid4().hex},
    )
    # Evaluamos la condición lógica (not isinstance(orden, dict) or not orden) para controlar el flujo
    if not isinstance(orden, dict) or not orden:
        # Retornamos el resultado procesado ({'ok': False, 'mensaje': f'Mercado Pago no resp...)
        return {"ok": False, "mensaje": f"Mercado Pago no respondió (HTTP {cod})."}
    # Evaluamos la condición lógica (cod in (401, 403)) para controlar el flujo
    if cod in (401, 403):
        # Retornamos el resultado procesado ({'ok': False, 'mensaje': 'El Access Token de Me...)
        return {"ok": False, "mensaje": "El Access Token de Mercado Pago no es válido. Revise secrets.toml."}

    # Asignamos 'datos' con orden.get('data') if isinstance(orden.get(...
    datos = orden.get("data") if isinstance(orden.get("data"), dict) else orden
    # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
    pagos = ((datos.get("transactions") or {}).get("payments") or [{}])
    # Asignamos 'pago' con pagos[0] if pagos else {}
    pago = pagos[0] if pagos else {}
    # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
    estado = datos.get("status") or pago.get("status") or ""
    # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
    detalle = pago.get("status_detail") or datos.get("status_detail") or ""
    # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
    resultado = {
        "estado": estado, "detalle": detalle,
        "orden_id": datos.get("id", ""), "pago_id": pago.get("id", ""),
    }
    # Evaluamos la condición lógica (estado == 'processed' and detalle in ('accredited', '')) para controlar el flujo
    if estado == "processed" and detalle in ("accredited", ""):
        # Ejecutamos instrucción: resultado.update(ok=True, mensaje='Pago aprobado por...
        resultado.update(ok=True, mensaje="Pago aprobado por Mercado Pago.")
    # Evaluamos la condición lógica (estado in ('action_required', 'processing')) para controlar el flujo
    elif estado in ("action_required", "processing"):
        # Ejecutamos instrucción: resultado.update(ok=False, mensaje='El pago quedó pe...
        resultado.update(ok=False, mensaje="El pago quedó pendiente en Mercado Pago. Intente con otra tarjeta.")
    # Evaluamos la condición lógica (estado == 'failed' or detalle) para controlar el flujo
    elif estado == "failed" or detalle:
        # Asignamos 'motivo' con _DETALLES_RECHAZO.get(detalle, detalle.rep...
        motivo = _DETALLES_RECHAZO.get(detalle, detalle.replace("_", " ") if detalle else "")
        # Ejecutamos instrucción: resultado.update(ok=False, mensaje='Pago rechazado p...
        resultado.update(ok=False, mensaje="Pago rechazado por Mercado Pago" + (f": {motivo}." if motivo else "."))
    else:
        # Asignamos 'msg' con _error_mp(orden)
        msg = _error_mp(orden)
        # Ejecutamos instrucción: resultado.update(ok=False, mensaje='Mercado Pago no ...
        resultado.update(ok=False, mensaje="Mercado Pago no pudo procesar el pago" + (f": {msg}" if msg else f" (HTTP {cod})."))
    # Retornamos el resultado procesado (resultado)
    return resultado


# Definición de función '_mp_public_key' sin parámetros externos
def _mp_public_key():
    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Evaluamos la condición lógica ('mercadopago' in st.secrets) para controlar el flujo
        if "mercadopago" in st.secrets:
            # Asignamos 'pk' con st.secrets['mercadopago'].get('public_key')
            pk = st.secrets["mercadopago"].get("public_key")
            # Evaluamos la condición lógica (pk) para controlar el flujo
            if pk:
                # Retornamos el resultado procesado (str(pk))
                return str(pk)
    except Exception:
        # Ejecutamos instrucción: pass
        pass
    # Retornamos el resultado procesado (os.environ.get('MP_PUBLIC_KEY') or '')
    return os.environ.get("MP_PUBLIC_KEY") or ""


# Definición de función 'sello_verificado' (parámetros: size)
def sello_verificado(size=22):
    """Insignia Premium verificada: sello ondulado naranjo (estilo verificado de Instagram)
    con un frasco de perfume negro y naranjo en el centro y un aura naranja animada.
    Es un SVG vectorial con animaciones SMIL, así que se anima tanto incrustado en HTML
    como usado de imagen (data URI)."""
    # Asignamos 'pts' con []
    pts = []
    # Recorremos iterativamente cada 'i' en range(24)
    for i in range(24):
        # Asignamos 'r' con 11 if i % 2 == 0 else 9.4
        r = 11 if i % 2 == 0 else 9.4
        # Asignamos 'a' con math.pi * i / 12 - math.pi / 2
        a = math.pi * i / 12 - math.pi / 2
        # Ejecutamos instrucción: pts.append(f'{12 + r * math.cos(a):.2f},{12 + r * ma...
        pts.append(f"{12 + r * math.cos(a):.2f},{12 + r * math.sin(a):.2f}")
    # Retornamos el resultado procesado (f'''<svg xmlns="http://www.w3.org/2000/svg" wid...)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="-5 -5 34 34" '
        'role="img" aria-label="Premium verificado" style="overflow:visible">'
        '<defs>'
        '<radialGradient id="ptSealAura" cx="0.5" cy="0.5" r="0.5">'
        '<stop offset="0.55" stop-color="#ff7a1a" stop-opacity="0.75"/>'
        '<stop offset="0.78" stop-color="#ff5a00" stop-opacity="0.28"/>'
        '<stop offset="1" stop-color="#ff7a1a" stop-opacity="0"/>'
        '</radialGradient>'
        '<linearGradient id="ptSealRing" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0" stop-color="#ffc46e"/><stop offset="0.35" stop-color="#ff8a1f"/>'
        '<stop offset="0.7" stop-color="#e8590c"/><stop offset="1" stop-color="#ffb04a"/>'
        '<animateTransform attributeName="gradientTransform" type="rotate" '
        'from="0 0.5 0.5" to="360 0.5 0.5" dur="5s" repeatCount="indefinite"/>'
        '</linearGradient>'
        '<linearGradient id="ptSealLiquid" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#ffb04a"/><stop offset="1" stop-color="#ff6a00"/>'
        '</linearGradient>'
        '</defs>'
        # Aura naranja que respira
        '<circle cx="12" cy="12" r="14" fill="url(#ptSealAura)">'
        '<animate attributeName="r" values="13.5;17;13.5" dur="2.6s" repeatCount="indefinite"/>'
        '<animate attributeName="opacity" values="0.5;1;0.5" dur="2.6s" repeatCount="indefinite"/>'
        '</circle>'
        # Sello ondulado con degradado naranjo en rotación
        f'<polygon points="{" ".join(pts)}" fill="url(#ptSealRing)" stroke="url(#ptSealRing)" '
        'stroke-width="1.4" stroke-linejoin="round"/>'
        # Frasco de perfume: tapa, cuello y cuerpo negros con detalles naranjos
        '<rect x="10.4" y="4.9" width="3.2" height="2.1" rx="0.55" fill="#111111"/>'
        '<rect x="10.4" y="4.9" width="3.2" height="0.65" rx="0.3" fill="#ff9a3c"/>'
        '<rect x="11.15" y="6.9" width="1.7" height="1.2" fill="#111111"/>'
        '<rect x="8" y="8" width="8" height="10.4" rx="2.4" fill="#111111" stroke="#ffd3a1" stroke-width="0.45"/>'
        '<rect x="9" y="12.6" width="6" height="4.8" rx="1.5" fill="url(#ptSealLiquid)">'
        '<animate attributeName="y" values="12.6;12.1;12.6" dur="2.6s" repeatCount="indefinite"/>'
        '<animate attributeName="height" values="4.8;5.3;4.8" dur="2.6s" repeatCount="indefinite"/>'
        '</rect>'
        '<path d="M9.5 9.5 V11.3" stroke="#ffffff" stroke-opacity="0.65" stroke-width="0.7" stroke-linecap="round"/>'
        '</svg>'
    )


# =============================================================================
# 2. DETECCIÓN DE LA TARJETA (MERCADO PAGO) Y VALIDACIONES
# =============================================================================
def solo_digitos(valor):
    # Retornamos el resultado procesado (''.join((ch for ch in str(valor or '') if ch.is...)
    return "".join(ch for ch in str(valor or "") if ch.isdigit())


# Definición de función 'luhn_valido' (parámetros: numero)
def luhn_valido(numero):
    # Evaluamos la condición lógica (not numero) para controlar el flujo
    if not numero:
        # Retornamos el resultado procesado (False)
        return False
    # Asignamos 'total' con 0
    total = 0
    # Recorremos iterativamente cada '(i, d)' en enumerate(reversed(numero))
    for i, d in enumerate(reversed(numero)):
        # Asignamos 'n' con int(d)
        n = int(d)
        # Evaluamos la condición lógica (i % 2 == 1) para controlar el flujo
        if i % 2 == 1:
            # Actualizamos acumulativamente el valor de 'n'
            n *= 2
            # Evaluamos la condición lógica (n > 9) para controlar el flujo
            if n > 9:
                # Actualizamos acumulativamente el valor de 'n'
                n -= 9
        # Actualizamos acumulativamente el valor de 'total'
        total += n
    # Retornamos el resultado procesado (total % 10 == 0)
    return total % 10 == 0


# Asignamos '_NOMBRES_MARCA' con {'visa': 'Visa', 'debvisa': 'Visa', 'maste...
_NOMBRES_MARCA = {
    "visa": "Visa", "debvisa": "Visa", "master": "Mastercard", "debmaster": "Mastercard",
    "amex": "American Express", "diners": "Diners Club", "magna": "Magna", "redcompra": "Redcompra",
}


# Definición de función '_deteccion_local' (parámetros: bin_)
def _deteccion_local(bin_):
    """Detección por prefijo cuando Mercado Pago no está disponible (no conoce el banco)."""
    # Asignamos 'd' con {'fuente': 'local', 'marca': '', 'tipo': '...
    d = {"fuente": "local", "marca": "", "tipo": "", "emisor": "", "logo": "", "largo": 16, "cvv": 3}
    # Evaluamos la condición lógica (bin_.startswith('4')) para controlar el flujo
    if bin_.startswith("4"):
        # Asignamos 'd['marca']' con 'Visa'
        d["marca"] = "Visa"
    # Evaluamos la condición lógica (bin_[:2] in ('51', '52', '53', '54', '55') or (len(b...) para controlar el flujo
    elif bin_[:2] in ("51", "52", "53", "54", "55") or (len(bin_) >= 4 and 2221 <= int(bin_[:4]) <= 2720):
        # Asignamos 'd['marca']' con 'Mastercard'
        d["marca"] = "Mastercard"
    # Evaluamos la condición lógica (bin_[:2] in ('34', '37')) para controlar el flujo
    elif bin_[:2] in ("34", "37"):
        # Ejecutamos instrucción: d.update(marca='American Express', largo=15, cvv=4)
        d.update(marca="American Express", largo=15, cvv=4)
    # Evaluamos la condición lógica (bin_[:2] in ('36', '38') or bin_[:3] in ('300', '301...) para controlar el flujo
    elif bin_[:2] in ("36", "38") or bin_[:3] in ("300", "301", "302", "303", "304", "305"):
        # Ejecutamos instrucción: d.update(marca='Diners Club', largo=14)
        d.update(marca="Diners Club", largo=14)
    # Retornamos el resultado procesado (d)
    return d


# Definición de función '_pedir_json' (parámetros: url)
def _pedir_json(url):
    # Asignamos 'req' con urllib.request.Request(url, headers={'Acce...
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "PerfumeTrending/1.0"})
    # Gestión automática de contexto y recursos para: urllib.request.urlopen(req, timeout=6)
    with urllib.request.urlopen(req, timeout=6) as resp:
        # Retornamos el resultado procesado (json.loads(resp.read().decode('utf-8')))
        return json.loads(resp.read().decode("utf-8"))


# Definición de función 'detectar_tarjeta' (parámetros: bin_, public_key)
@st.cache_data(ttl=3600, show_spinner=False)
def detectar_tarjeta(bin_: str, public_key: str):
    """Consulta a Mercado Pago la marca, el tipo y el banco emisor a partir del BIN."""
    # Evaluamos la condición lógica (len(bin_) < 6) para controlar el flujo
    if len(bin_) < 6:
        # Retornamos el resultado procesado (None)
        return None
    # Evaluamos la condición lógica (public_key) para controlar el flujo
    if public_key:
        # Bloque try/except para manejo seguro de errores y resiliencia operativa
        try:
            # Asignamos 'q' con urllib.parse.urlencode({'public_key': publ...
            q = urllib.parse.urlencode({
                "public_key": public_key, "bins": bin_, "marketplace": "NONE", "status": "active",
            })
            # Asignamos 'data' con _pedir_json(f'https://api.mercadopago.com/...
            data = _pedir_json(f"https://api.mercadopago.com/v1/payment_methods/search?{q}")
            # Asignamos 'resultados' con data.get('results') if isinstance(data, di...
            resultados = data.get("results") if isinstance(data, dict) else None
            # Evaluamos la condición lógica (resultados) para controlar el flujo
            if resultados:
                # Asignamos 'pm' con resultados[0]
                pm = resultados[0]
                # Asignamos 'ajustes' con (pm.get('settings') or [{}])[0] or {}
                ajustes = (pm.get("settings") or [{}])[0] or {}
                # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
                largo = (ajustes.get("card_number") or {}).get("length") or 16
                # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
                cvv = (ajustes.get("security_code") or {}).get("length") or 3
                # Retornamos el resultado procesado ({'fuente': 'mercadopago', 'id': pm.get('id', ''...)
                return {
                    "fuente": "mercadopago",
                    "id": pm.get("id", ""),
                    "marca": _NOMBRES_MARCA.get(pm.get("id", ""), pm.get("name", "")),
                    "tipo": pm.get("payment_type_id", ""),
                    "emisor": (pm.get("issuer") or {}).get("name", ""),
                    "logo": pm.get("secure_thumbnail") or pm.get("thumbnail") or "",
                    "largo": int(largo),
                    "cvv": int(cvv),
                }
        except Exception:
            # Ejecutamos instrucción: pass
            pass
        # Respaldo: el recurso de cuotas también informa medio de pago, tipo y emisor
        try:
            # Asignamos 'q' con urllib.parse.urlencode({'public_key': publ...
            q = urllib.parse.urlencode({"public_key": public_key, "bin": bin_, "amount": PRECIO_PREMIUM})
            # Asignamos 'data' con _pedir_json(f'https://api.mercadopago.com/...
            data = _pedir_json(f"https://api.mercadopago.com/v1/payment_methods/installments?{q}")
            # Evaluamos la condición lógica (isinstance(data, list) and data) para controlar el flujo
            if isinstance(data, list) and data:
                # Asignamos 'it' con data[0]
                it = data[0]
                # Asignamos 'local' con _deteccion_local(bin_)
                local = _deteccion_local(bin_)
                # Asignamos 'pm_id' con it.get('payment_method_id', '')
                pm_id = it.get("payment_method_id", "")
                # Retornamos el resultado procesado ({'fuente': 'mercadopago', 'id': pm_id, 'marca':...)
                return {
                    "fuente": "mercadopago",
                    "id": pm_id,
                    "marca": _NOMBRES_MARCA.get(pm_id, local["marca"] or pm_id.title()),
                    "tipo": it.get("payment_type_id", ""),
                    "emisor": (it.get("issuer") or {}).get("name", ""),
                    "logo": (it.get("issuer") or {}).get("secure_thumbnail", "") or "",
                    "largo": local["largo"],
                    "cvv": local["cvv"],
                }
        except Exception:
            # Ejecutamos instrucción: pass
            pass
    # Asignamos 'd' con _deteccion_local(bin_)
    d = _deteccion_local(bin_)
    # Asignamos 'd['fuente']' con 'local_sin_mp' if public_key else 'local'
    d["fuente"] = "local_sin_mp" if public_key else "local"
    # Retornamos el resultado procesado (d)
    return d


# Definición de función 'tipo_legible' (parámetros: tipo)
def tipo_legible(tipo):
    # Retornamos el resultado procesado ({'debit_card': 'Débito', 'credit_card': 'Crédit...)
    return {"debit_card": "Débito", "credit_card": "Crédito", "prepaid_card": "Prepago"}.get(tipo, "")


# Definición de función 'formatear_numero' (parámetros: numero, largo)
def formatear_numero(numero, largo):
    """Agrupa como en la tarjeta física: 4-6-5 para American Express, 4-4-4-4 para el resto."""
    # Asignamos 'relleno' con (numero + '•' * max(0, largo - len(numero)...
    relleno = (numero + "•" * max(0, largo - len(numero)))[:largo]
    # Evaluamos la condición lógica (largo == 15) para controlar el flujo
    if largo == 15:
        # Retornamos el resultado procesado (f'{relleno[:4]} {relleno[4:10]} {relleno[10:]}')
        return f"{relleno[:4]} {relleno[4:10]} {relleno[10:]}"
    # Evaluamos la condición lógica (largo == 14) para controlar el flujo
    if largo == 14:
        # Retornamos el resultado procesado (f'{relleno[:4]} {relleno[4:10]} {relleno[10:]}')
        return f"{relleno[:4]} {relleno[4:10]} {relleno[10:]}"
    # Retornamos el resultado procesado (' '.join((relleno[i:i + 4] for i in range(0, le...)
    return " ".join(relleno[i:i + 4] for i in range(0, len(relleno), 4))


# Definición de función 'parsear_vencimiento' (parámetros: valor)
def parsear_vencimiento(valor):
    # Asignamos 'd' con solo_digitos(valor)
    d = solo_digitos(valor)
    # Evaluamos la condición lógica (len(d) != 4) para controlar el flujo
    if len(d) != 4:
        # Retornamos el resultado procesado (None)
        return None
    # Asignamos '(mes, anio)' con (int(d[:2]), 2000 + int(d[2:]))
    mes, anio = int(d[:2]), 2000 + int(d[2:])
    # Evaluamos la condición lógica (not 1 <= mes <= 12) para controlar el flujo
    if not 1 <= mes <= 12:
        # Retornamos el resultado procesado (None)
        return None
    # Retornamos el resultado procesado ((mes, anio))
    return mes, anio


# Definición de función 'validar' (parámetros: numero, nombre, venc, cvv, ...)
def validar(numero, nombre, venc, cvv, info):
    # Asignamos 'errores' con []
    errores = []
    # Asignamos 'largo' con (info or {}).get('largo', 16)
    largo = (info or {}).get("largo", 16)
    # Asignamos 'largo_cvv' con (info or {}).get('cvv', 3)
    largo_cvv = (info or {}).get("cvv", 3)
    # Evaluamos la condición lógica (len(numero) != largo or not luhn_valido(numero)) para controlar el flujo
    if len(numero) != largo or not luhn_valido(numero):
        # Ejecutamos instrucción: errores.append('El número de tarjeta no es válido.')
        errores.append("El número de tarjeta no es válido.")
    # Evaluamos la condición lógica (info and (not info.get('marca'))) para controlar el flujo
    elif info and not info.get("marca"):
        # Ejecutamos instrucción: errores.append('No reconocemos la marca de esta tarj...
        errores.append("No reconocemos la marca de esta tarjeta.")
    # Evaluamos la condición lógica (len(nombre.strip()) < 3) para controlar el flujo
    if len(nombre.strip()) < 3:
        # Ejecutamos instrucción: errores.append('Ingrese el nombre del titular tal co...
        errores.append("Ingrese el nombre del titular tal como aparece en la tarjeta.")
    # Asignamos 'v' con parsear_vencimiento(venc)
    v = parsear_vencimiento(venc)
    # Asignamos 'hoy' con date.today()
    hoy = date.today()
    # Evaluamos la condición lógica (not v) para controlar el flujo
    if not v:
        # Ejecutamos instrucción: errores.append('La fecha de vencimiento debe tener e...
        errores.append("La fecha de vencimiento debe tener el formato MM/AA.")
    # Evaluamos la condición lógica ((v[1], v[0]) < (hoy.year, hoy.month)) para controlar el flujo
    elif (v[1], v[0]) < (hoy.year, hoy.month):
        # Ejecutamos instrucción: errores.append('La tarjeta está vencida.')
        errores.append("La tarjeta está vencida.")
    # Evaluamos la condición lógica (len(cvv) != largo_cvv) para controlar el flujo
    if len(cvv) != largo_cvv:
        # Ejecutamos instrucción: errores.append(f'El código de seguridad (CVV) debe t...
        errores.append(f"El código de seguridad (CVV) debe tener {largo_cvv} dígitos.")
    # Retornamos el resultado procesado (errores)
    return errores


# Definición de función 'usar_tarjeta_prueba' (parámetros: tipo)
def usar_tarjeta_prueba(tipo):
    # Asignamos 't' con TARJETAS_PRUEBA[tipo]
    t = TARJETAS_PRUEBA[tipo]
    # Asignamos 'st.session_state['cp_num']' con t['num']
    st.session_state["cp_num"] = t["num"]
    # Asignamos 'st.session_state['cp_nombre']' con 'APRO'
    st.session_state["cp_nombre"] = "APRO"
    # Asignamos 'st.session_state['cp_venc']' con t['venc']
    st.session_state["cp_venc"] = t["venc"]
    # Asignamos 'st.session_state['cp_cvv']' con t['cvv']
    st.session_state["cp_cvv"] = t["cvv"]
    # Asignamos 'st.session_state['cp_doc']' con '123456789'
    st.session_state["cp_doc"] = "123456789"
    # Asignamos 'st.session_state['cp_tipo']' con tipo
    st.session_state["cp_tipo"] = tipo
    # Asignamos 'st.session_state['_cp_ultimo_bin']' con solo_digitos(t['num'])[:8]
    st.session_state["_cp_ultimo_bin"] = solo_digitos(t["num"])[:8]


# Definición de función '_fecha_vigencia' (parámetros: iso_txt)
def _fecha_vigencia(iso_txt):
    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Retornamos el resultado procesado (datetime.fromisoformat(str(iso_txt).replace('Z'...)
        return datetime.fromisoformat(str(iso_txt).replace("Z", "+00:00")).strftime("%d-%m-%Y")
    except Exception:
        # Retornamos el resultado procesado ('30 días desde hoy')
        return "30 días desde hoy"


# Definición de función 'volver_a_planes' sin parámetros externos
def volver_a_planes():
    # Asignamos 'st.session_state['current_page']' con 'planes_page'
    st.session_state["current_page"] = "planes_page"


# =============================================================================
# 3. ESTILOS
# =============================================================================
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap');
header[data-testid="stHeader"] {{ display: none !important; }}
.block-container {{ padding-top: 1.6rem !important; max-width: 1080px !important; }}
.stApp {{ {app_bg_css} color: {text_color} !important; font-family: {font_sans}; }}
[data-testid="stAppViewContainer"], [data-testid="stMain"] {{ background: transparent !important; }}
.stApp p, .stApp label, .stMarkdown p {{ color: {text_color} !important; font-family: {font_sans} !important; }}

.cp-title {{ font-size: clamp(1.6rem, 3vw, 2.1rem); font-weight: 800; letter-spacing: -0.025em; color: {text_color}; line-height: 1.1; }}
.cp-lede {{ font-size: 0.98rem; color: {subtext_color}; margin-top: 8px; max-width: 60ch; line-height: 1.5; }}
.cp-step {{ font-size: 1rem; font-weight: 800; color: {text_color}; margin: 22px 0 10px; }}

/* Selector Débito / Crédito */
div[data-testid="stRadio"] div[role="radiogroup"] {{
    display: grid !important; grid-template-columns: 1fr 1fr; gap: 10px;
}}
div[data-testid="stRadio"] div[role="radiogroup"] > label {{
    margin: 0 !important; padding: 13px 16px !important;
    border: 1.5px solid {btn_border}; border-radius: 14px; background: {surface_soft};
    cursor: pointer; transition: border-color 0.18s ease, background-color 0.18s ease;
}}
div[data-testid="stRadio"] div[role="radiogroup"] > label:has(input:checked) {{
    border-color: {gold_plan}; background: {gold_plan_soft};
}}
div[data-testid="stRadio"] div[role="radiogroup"] > label p {{ font-weight: 700 !important; }}

/* Tarjeta visual */
.cp-card {{
    position: relative; overflow: hidden; box-sizing: border-box;
    width: 100%; max-width: 420px; aspect-ratio: 1.586 / 1; margin: 6px 0 18px;
    border-radius: 18px; padding: 22px 24px; color: #fff;
    display: flex; flex-direction: column; justify-content: space-between;
    box-shadow: 0 24px 44px -22px rgba(0,0,0,0.6);
    font-family: {font_sans};
}}
.cp-card-credito {{ background: linear-gradient(135deg, #2b2620 0%, #14110d 55%, #3a2f1c 100%); }}
.cp-card-debito {{ background: linear-gradient(135deg, #8f1f2a 0%, #4a0f18 60%, #2a0910 100%); }}
.cp-card::before {{
    content: ""; position: absolute; width: 280px; height: 280px; border-radius: 50%;
    right: -90px; top: -120px; background: radial-gradient(circle, rgba(226,184,87,0.30), transparent 65%);
}}
.cp-card-row {{ display: flex; justify-content: space-between; align-items: center; position: relative; }}
.cp-card-bank {{ font-size: 0.95rem; font-weight: 800; letter-spacing: -0.01em; }}
.cp-card-type {{ font-size: 0.72rem; font-weight: 700; opacity: 0.8; letter-spacing: 0.4px; }}
.cp-chip {{ width: 42px; height: 31px; border-radius: 6px; background: linear-gradient(135deg, #f3d488, #b8892a); position: relative; }}
.cp-chip::after {{ content: ""; position: absolute; inset: 7px 9px; border: 1px solid rgba(60,40,10,0.45); border-radius: 3px; }}
.cp-card-num {{ font-size: clamp(1.05rem, 2.6vw, 1.4rem); font-weight: 700; letter-spacing: 2px; font-variant-numeric: tabular-nums; position: relative; }}
.cp-card-label {{ font-size: 0.62rem; opacity: 0.65; letter-spacing: 0.4px; }}
.cp-card-val {{ font-size: 0.88rem; font-weight: 700; letter-spacing: 0.5px; max-width: 230px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.cp-card-brand {{ font-size: 1.15rem; font-weight: 800; font-style: italic; letter-spacing: -0.02em; }}

/* Campos */
[data-testid="stTextInputRootElement"], div[data-baseweb="input"] {{
    background-color: {input_bg} !important; border: 1px solid {input_border} !important;
    border-radius: 12px !important; min-height: 46px !important;
}}
[data-testid="stTextInputRootElement"]:focus-within, div[data-baseweb="input"]:focus-within {{
    border-color: {gold_plan} !important; box-shadow: 0 0 0 3px {gold_plan_soft} !important;
}}
[data-testid="stTextInputRootElement"] input, div[data-baseweb="input"] input {{
    color: {input_text} !important; background: transparent !important; font-size: 0.98rem !important;
}}
[data-testid="stWidgetLabel"] p {{ font-size: 0.84rem !important; font-weight: 600 !important; color: {subtext_color} !important; }}

.cp-card-logo {{ height: 26px; background: #fff; border-radius: 6px; padding: 3px 6px; }}
.cp-detect {{ display: flex; align-items: center; gap: 8px; font-size: 0.84rem; margin: -6px 0 12px 2px; color: {subtext_color}; }}
.cp-detect b {{ color: {text_color}; }}
.cp-detect-dot {{ width: 8px; height: 8px; border-radius: 50%; flex: 0 0 8px; }}
.cp-detect-mp .cp-detect-dot {{ background: #22c55e; box-shadow: 0 0 0 3px rgba(34,197,94,0.18); }}
.cp-detect-local .cp-detect-dot {{ background: {subtext_color}; }}
div.st-key-btn_cp_demo_deb div.stButton > button,
div.st-key-btn_cp_demo_cred div.stButton > button {{ min-height: 40px !important; border-style: dashed !important; }}
div.st-key-btn_cp_demo_deb div.stButton > button p,
div.st-key-btn_cp_demo_cred div.stButton > button p {{ font-size: 0.86rem !important; }}

/* Nota de tarjetas de prueba */
.cp-demo {{
    border: 1px dashed {gold_plan}; background: {gold_plan_soft}; border-radius: 14px;
    padding: 12px 16px; font-size: 0.86rem; color: {text_color}; line-height: 1.55; margin-bottom: 10px;
}}
.cp-demo b {{ font-variant-numeric: tabular-nums; }}

/* Botones */
div.stButton > button {{
    border-radius: 12px !important; min-height: 46px !important;
    background: transparent !important; border: 1.5px solid {btn_border} !important; box-shadow: none !important;
}}
div.stButton > button p {{ color: {btn_text} !important; font-weight: 700 !important; }}
div.stButton > button:hover {{ border-color: {gold_plan} !important; }}
div.st-key-btn_pagar div.stButton > button {{
    min-height: 54px !important; border: 1px solid #c99a2f !important;
    background: linear-gradient(135deg, #f7dc8f 0%, #e2b857 45%, #b98a26 100%) !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.55), 0 12px 26px -14px #c9992f !important;
}}
div.st-key-btn_pagar div.stButton > button p {{ color: #2a1f05 !important; font-size: 1.02rem !important; }}
div.st-key-btn_pagar div.stButton > button:hover {{ filter: brightness(1.05); }}

/* Resumen */
.cp-summary {{
    border: 1px solid {gold_plan}; border-radius: 20px; padding: 24px;
    background: linear-gradient(180deg, {gold_plan_soft} 0%, transparent 60%), {card_bg};
    box-shadow: 0 22px 44px -30px {gold_plan};
}}
.cp-sum-name {{ font-size: 1.3rem; font-weight: 800; color: {gold_plan}; }}
.cp-sum-for {{ font-size: 0.86rem; color: {subtext_color}; margin-top: 2px; }}
.cp-sum-list {{ margin: 18px 0; display: flex; flex-direction: column; gap: 10px; }}
.cp-sum-item {{ display: flex; gap: 10px; font-size: 0.9rem; color: {text_color}; line-height: 1.4; }}
.cp-sum-dot {{ flex: 0 0 18px; height: 18px; border-radius: 50%; background: {gold_plan}; display: inline-flex; align-items: center; justify-content: center; margin-top: 1px; }}
.cp-sum-line {{ display: flex; justify-content: space-between; font-size: 0.9rem; color: {subtext_color}; padding: 8px 0; border-top: 1px solid {border_color}; }}
.cp-sum-total {{ display: flex; justify-content: space-between; align-items: baseline; padding-top: 12px; border-top: 1px solid {border_color}; }}
.cp-sum-total-label {{ font-size: 0.95rem; font-weight: 700; color: {text_color}; }}
.cp-sum-total-val {{ font-size: 1.6rem; font-weight: 800; color: {text_color}; letter-spacing: -0.02em; font-variant-numeric: tabular-nums; }}
.cp-secure {{ display: flex; gap: 8px; align-items: flex-start; font-size: 0.8rem; color: {subtext_color}; margin-top: 14px; line-height: 1.45; }}

/* Éxito */
.cp-success {{
    max-width: 560px; margin: 10px auto 0; text-align: center;
    border: 1px solid {gold_plan}; border-radius: 22px; padding: 34px 28px 26px;
    background: linear-gradient(180deg, {gold_plan_soft} 0%, transparent 55%), {card_bg};
}}
.cp-success-seal {{ display: flex; justify-content: center; margin-bottom: 14px; }}
.cp-success-title {{ font-size: 1.6rem; font-weight: 800; color: {text_color}; letter-spacing: -0.02em; }}
.cp-success-text {{ font-size: 0.95rem; color: {subtext_color}; margin: 8px auto 20px; max-width: 42ch; line-height: 1.5; }}
.cp-receipt {{ text-align: left; border-top: 1px dashed {border_color}; padding-top: 14px; }}
.cp-receipt-row {{ display: flex; justify-content: space-between; gap: 12px; font-size: 0.88rem; padding: 5px 0; color: {subtext_color}; }}
.cp-receipt-row b {{ color: {text_color}; font-variant-numeric: tabular-nums; }}

@media (max-width: 768px) {{
    .block-container {{ padding-left: 0.9rem !important; padding-right: 0.9rem !important; }}
    div[data-testid="stColumn"] {{ width: 100% !important; flex: 1 1 100% !important; }}
}}
</style>
""", unsafe_allow_html=True)

# Asignamos 'svg_check_dark' con '<svg width="10" height="10" viewBox="0 0 ...
svg_check_dark = '<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#2a1f05" stroke-width="3.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="20 6 9 17 4 12"/></svg>'
# Asignamos 'svg_lock' con f'<svg width="15" height="15" viewBox="0 0...
svg_lock = f'<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="{subtext_color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" style="flex:0 0 15px; margin-top:1px;"><rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/></svg>'


# =============================================================================
# 4. ENCABEZADO
# =============================================================================
c_back, _ = st.columns([2.2, 7.8])
# Gestión automática de contexto y recursos para: c_back
with c_back:
    # Evaluamos la condición lógica (st.button('‹ Volver a planes', key='btn_volver_plane...) para controlar el flujo
    if st.button("‹ Volver a planes", key="btn_volver_planes", use_container_width=True, on_click=volver_a_planes):
        # Ejecutamos instrucción: st.switch_page('app.py')
        st.switch_page("app.py")

# Evaluamos la condición lógica (st.session_state.get('show_login_modal')) para controlar el flujo
if st.session_state.get("show_login_modal"):
    # Asignamos 'st.session_state['show_login_mod...' con False
    st.session_state["show_login_modal"] = False
    # Ejecutamos instrucción: modal_autenticacion()
    modal_autenticacion()

# Usuario sin sesión: no puede comprar
if not st.session_state.get("logged_in") or not st.session_state.get("user_info"):
    # Renderizado de componente visual o control interactivo en la interfaz Streamlit
    st.markdown(clean_html("""
        <div class="cp-title">Activar Premium</div>
        <div class="cp-lede">Para contratar el plan Premium es necesario iniciar sesión con su cuenta.</div>
    """), unsafe_allow_html=True)
    # Renderizado de componente visual o control interactivo en la interfaz Streamlit
    st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)
    # Renderizado de componente visual o control interactivo en la interfaz Streamlit
    c_login, _ = st.columns([2.4, 7.6])
    # Gestión automática de contexto y recursos para: c_login
    with c_login:
        # Evaluamos la condición lógica (st.button('Iniciar sesión', key='btn_cp_login', use_...) para controlar el flujo
        if st.button("Iniciar sesión", key="btn_cp_login", use_container_width=True):
            # Asignamos 'st.session_state['show_login_mod...' con True
            st.session_state["show_login_modal"] = True
            # Ejecutamos instrucción: st.rerun()
            st.rerun()
    # Ejecutamos instrucción: st.stop()
    st.stop()

# Asignamos 'user_info' con st.session_state['user_info']
user_info = st.session_state["user_info"]
# Asignamos 'u_ident' con user_info.get('id') or user_info.get('email')
u_ident = user_info.get("id") or user_info.get("email")
# Asignamos 'u_plan' con str(user_info.get('plan') or 'free').strip...
u_plan = str(user_info.get("plan") or "free").strip().lower()
# Asignamos 'recibo' con st.session_state.get('cp_recibo')
recibo = st.session_state.get("cp_recibo")


# =============================================================================
# 5. PANTALLA DE ÉXITO (o usuario que ya es Premium)
# =============================================================================
if u_plan in ("premium", "vip", "socios_vip"):
    # Evaluamos la condición lógica (recibo) para controlar el flujo
    if recibo:
        # Asignamos 'filas' con ''.join((f'<div class="cp-receipt-row"><di...
        filas = "".join(
            f'<div class="cp-receipt-row"><div>{k}</div><b>{escape_html(v)}</b></div>'
            for k, v in [
                ("N.º de orden", recibo["orden"]),
                ("Fecha", recibo["fecha"]),
                ("Medio de pago", f'{recibo["tipo"]} {recibo["marca"]} terminada en {recibo["last4"]}'),
                ("Total pagado", f'${recibo["monto"]:,.0f} CLP'.replace(",", ".")),
                ("Procesado por", recibo.get("procesador", "Simulado")),
                ("Vigente hasta", _fecha_vigencia(st.session_state["user_info"].get("plan_vence_en"))),
            ] + ([("Orden Mercado Pago", recibo["mp_orden"])] if recibo.get("mp_orden") else [])
        )
        # Asignamos '(titulo, texto)' con ('Pago aprobado', 'Su cuenta ahora es Prem...
        titulo, texto = "Pago aprobado", "Su cuenta ahora es Premium verificada. Ya puede activar las alertas de precio desde su perfil."
        # Evaluamos la condición lógica (recibo.get('guardado') is False) para controlar el flujo
        if recibo.get("guardado") is False:
            # Actualizamos acumulativamente el valor de 'texto'
            texto += " Atención: el plan está activo en esta sesión, pero no se pudo guardar en la base de datos (" + str(recibo.get("guardado_msg", "")) + ")."
    else:
        # Asignamos 'filas' con ''
        filas = ""
        # Asignamos '(titulo, texto)' con ('Su cuenta ya es Premium', 'El plan Premi...
        titulo, texto = "Su cuenta ya es Premium", "El plan Premium está activo y su perfil muestra la insignia de verificado."

    # Renderizado de componente visual o control interactivo en la interfaz Streamlit
    st.markdown(clean_html(f"""
        <div class="cp-success">
            <div class="cp-success-seal">{sello_verificado(76)}</div>
            <div class="cp-success-title">{titulo}</div>
            <div class="cp-success-text">{texto}</div>
            {f'<div class="cp-receipt">{filas}</div>' if filas else ''}
        </div>
    """), unsafe_allow_html=True)
    # Renderizado de componente visual o control interactivo en la interfaz Streamlit
    st.markdown("<div style='margin-top:18px;'></div>", unsafe_allow_html=True)
    # Renderizado de componente visual o control interactivo en la interfaz Streamlit
    _, c1, c2, _ = st.columns([1.2, 2, 2, 1.2])
    # Gestión automática de contexto y recursos para: c1
    with c1:
        # Evaluamos la condición lógica (st.button('Ir a mi perfil', key='btn_cp_perfil', use...) para controlar el flujo
        if st.button("Ir a mi perfil", key="btn_cp_perfil", use_container_width=True):
            # Ejecutamos instrucción: st.switch_page('pages/perfil.py')
            st.switch_page("pages/perfil.py")
    # Gestión automática de contexto y recursos para: c2
    with c2:
        # Evaluamos la condición lógica (st.button('Volver al catálogo', key='btn_cp_catalogo...) para controlar el flujo
        if st.button("Volver al catálogo", key="btn_cp_catalogo", use_container_width=True):
            # Asignamos 'st.session_state['current_page']' con 'home'
            st.session_state["current_page"] = "home"
            # Ejecutamos instrucción: st.switch_page('app.py')
            st.switch_page("app.py")
    # Ejecutamos instrucción: st.stop()
    st.stop()


# =============================================================================
# 6. CHECKOUT
# =============================================================================
st.markdown(clean_html("""
    <div class="cp-title">Activar Premium</div>
    <div class="cp-lede">Complete los datos de su tarjeta para activar las alertas de precio de sus fragancias favoritas.</div>
"""), unsafe_allow_html=True)

# Asignamos 'MP_PK' con _mp_public_key()
MP_PK = _mp_public_key()

# Detección con los dígitos ya escritos (antes de dibujar los campos)
num_actual = solo_digitos(st.session_state.get("cp_num", ""))[:19]
# Asignamos 'bin_actual' con num_actual[:8]
bin_actual = num_actual[:8]
# Asignamos 'info' con detectar_tarjeta(bin_actual, MP_PK) if len...
info = detectar_tarjeta(bin_actual, MP_PK) if len(bin_actual) >= 6 else None

# Si cambia la tarjeta, el selector Débito / Crédito se ajusta solo al tipo que informa Mercado Pago
if info and bin_actual != st.session_state.get("_cp_ultimo_bin"):
    # Asignamos 'st.session_state['_cp_ultimo_bin']' con bin_actual
    st.session_state["_cp_ultimo_bin"] = bin_actual
    # Evaluamos la condición lógica (tipo_legible(info.get('tipo')) in ('Débito', 'Crédito')) para controlar el flujo
    if tipo_legible(info.get("tipo")) in ("Débito", "Crédito"):
        # Asignamos 'st.session_state['cp_tipo']' con tipo_legible(info.get('tipo'))
        st.session_state["cp_tipo"] = tipo_legible(info.get("tipo"))

# Renderizado de componente visual o control interactivo en la interfaz Streamlit
col_pago, col_resumen = st.columns([6, 4], gap="large")

# Gestión automática de contexto y recursos para: col_pago
with col_pago:
    # Renderizado de componente visual o control interactivo en la interfaz Streamlit
    st.markdown("<div class='cp-step'>Medio de pago</div>", unsafe_allow_html=True)
    # Asignamos 'tipo' con st.radio('Tipo de tarjeta', ['Débito', 'Cr...
    tipo = st.radio("Tipo de tarjeta", ["Débito", "Crédito"], horizontal=True, key="cp_tipo", label_visibility="collapsed")

    # Asignamos 'largo' con (info or {}).get('largo', 16)
    largo = (info or {}).get("largo", 16)
    # Asignamos 'num_fmt' con escape_html(formatear_numero(num_actual[:l...
    num_fmt = escape_html(formatear_numero(num_actual[:largo], largo))
    # Asignamos 'nombre_prev' con escape_html((st.session_state.get('cp_nomb...
    nombre_prev = escape_html((st.session_state.get("cp_nombre") or "NOMBRE DEL TITULAR").upper())
    # Asignamos 'venc_prev' con escape_html(st.session_state.get('cp_venc'...
    venc_prev = escape_html(st.session_state.get("cp_venc") or "MM/AA")
    # Asignamos 'marca_txt' con escape_html((info or {}).get('marca', ''))
    marca_txt = escape_html((info or {}).get("marca", ""))
    # Asignamos 'emisor_txt' con escape_html((info or {}).get('emisor') or ...
    emisor_txt = escape_html((info or {}).get("emisor") or "Su banco")
    # Asignamos 'logo' con (info or {}).get('logo', '')
    logo = (info or {}).get("logo", "")
    # Asignamos 'marca_html' con f'<img class="cp-card-logo" src="{escape_h...
    marca_html = (
        f'<img class="cp-card-logo" src="{escape_html(logo)}" alt="{marca_txt}">' if logo.startswith("https://")
        else f'<div class="cp-card-brand">{marca_txt}</div>'
    )
    # Asignamos 'clase_tarjeta' con 'cp-card-debito' if tipo == 'Débito' else ...
    clase_tarjeta = "cp-card-debito" if tipo == "Débito" else "cp-card-credito"

    # Renderizado de componente visual o control interactivo en la interfaz Streamlit
    st.markdown(clean_html(f"""
        <div class="cp-card {clase_tarjeta}" aria-hidden="true">
            <div class="cp-card-row">
                <div class="cp-card-bank">{emisor_txt}</div>
                <div class="cp-card-type">{tipo.upper()}</div>
            </div>
            <div class="cp-card-row"><div class="cp-chip"></div></div>
            <div class="cp-card-num">{num_fmt}</div>
            <div class="cp-card-row">
                <div>
                    <div class="cp-card-label">TITULAR</div>
                    <div class="cp-card-val">{nombre_prev}</div>
                </div>
                <div>
                    <div class="cp-card-label">VENCE</div>
                    <div class="cp-card-val">{venc_prev}</div>
                </div>
                {marca_html}
            </div>
        </div>
    """), unsafe_allow_html=True)

    # Renderizado de componente visual o control interactivo en la interfaz Streamlit
    st.markdown(clean_html("""
        <div class="cp-demo">
            Ambiente de prueba de Mercado Pago: no se realiza ningún cargo real. Las tarjetas de prueba
            son las oficiales de Mercado Pago Chile y se rellenan con un clic. Con el titular <b>APRO</b>
            el pago se aprueba; con <b>OTHE</b>, <b>FUND</b> o <b>SECU</b> se rechaza.
        </div>
    """), unsafe_allow_html=True)
    # Renderizado de componente visual o control interactivo en la interfaz Streamlit
    c_deb, c_cred, _ = st.columns([2, 2, 1.4])
    # Gestión automática de contexto y recursos para: c_deb
    with c_deb:
        # Renderizado de componente visual o control interactivo en la interfaz Streamlit
        st.button("Usar débito de prueba", key="btn_cp_demo_deb", on_click=usar_tarjeta_prueba, args=("Débito",), use_container_width=True)
    # Gestión automática de contexto y recursos para: c_cred
    with c_cred:
        # Renderizado de componente visual o control interactivo en la interfaz Streamlit
        st.button("Usar crédito de prueba", key="btn_cp_demo_cred", on_click=usar_tarjeta_prueba, args=("Crédito",), use_container_width=True)

    # Renderizado de componente visual o control interactivo en la interfaz Streamlit
    st.markdown("<div class='cp-step'>Datos de la tarjeta</div>", unsafe_allow_html=True)
    # Renderizado de componente visual o control interactivo en la interfaz Streamlit
    st.text_input("Número de tarjeta", key="cp_num", placeholder="0000 0000 0000 0000", max_chars=23)

    # Estado de la detección
    if info:
        # Asignamos 'detalle' con ' '.join((x for x in [info.get('marca', ''...
        detalle = " ".join(x for x in [info.get("marca", ""), tipo_legible(info.get("tipo"))] if x)
        # Evaluamos la condición lógica (info.get('emisor')) para controlar el flujo
        if info.get("emisor"):
            # Actualizamos acumulativamente el valor de 'detalle'
            detalle += f", {info['emisor']}"
        # Evaluamos la condición lógica (info['fuente'] == 'mercadopago') para controlar el flujo
        if info["fuente"] == "mercadopago":
            # Renderizado de componente visual o control interactivo en la interfaz Streamlit
            st.markdown(f"<div class='cp-detect cp-detect-mp'><div class='cp-detect-dot'></div><div>Mercado Pago detectó: <b>{escape_html(detalle)}</b></div></div>", unsafe_allow_html=True)
        # Evaluamos la condición lógica (info.get('marca')) para controlar el flujo
        elif info.get("marca"):
            # Asignamos 'nota' con 'Mercado Pago no respondió, detección loca...
            nota = "Mercado Pago no respondió, detección local" if info["fuente"] == "local_sin_mp" else "Detección local (Mercado Pago no configurado)"
            # Renderizado de componente visual o control interactivo en la interfaz Streamlit
            st.markdown(f"<div class='cp-detect cp-detect-local'><div class='cp-detect-dot'></div><div>{nota}: <b>{escape_html(detalle)}</b></div></div>", unsafe_allow_html=True)
        else:
            # Renderizado de componente visual o control interactivo en la interfaz Streamlit
            st.markdown("<div class='cp-detect cp-detect-local'><div class='cp-detect-dot'></div><div>Marca no reconocida.</div></div>", unsafe_allow_html=True)

    # Renderizado de componente visual o control interactivo en la interfaz Streamlit
    st.text_input("Nombre del titular", key="cp_nombre", placeholder="Como aparece en la tarjeta", max_chars=40)
    # Renderizado de componente visual o control interactivo en la interfaz Streamlit
    c_venc, c_cvv = st.columns(2)
    # Gestión automática de contexto y recursos para: c_venc
    with c_venc:
        # Renderizado de componente visual o control interactivo en la interfaz Streamlit
        st.text_input("Vencimiento", key="cp_venc", placeholder="MM/AA", max_chars=5)
    # Gestión automática de contexto y recursos para: c_cvv
    with c_cvv:
        # Renderizado de componente visual o control interactivo en la interfaz Streamlit
        st.text_input("CVV", key="cp_cvv", placeholder="123", max_chars=4, type="password")
    # Renderizado de componente visual o control interactivo en la interfaz Streamlit
    st.text_input("RUT o documento del titular", key="cp_doc", placeholder="12345678-9", max_chars=15)

    # Renderizado de componente visual o control interactivo en la interfaz Streamlit
    st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
    # Renderizado de componente visual o control interactivo en la interfaz Streamlit
    pagar = st.button("Pagar $2.000 CLP", key="btn_pagar", use_container_width=True)

    # Evaluamos la condición lógica (pagar) para controlar el flujo
    if pagar:
        # Asignamos 'numero' con solo_digitos(st.session_state.get('cp_num'))
        numero = solo_digitos(st.session_state.get("cp_num"))
        # Asignamos 'nombre' con (st.session_state.get('cp_nombre') or '')....
        nombre = (st.session_state.get("cp_nombre") or "").strip()
        # Asignamos 'venc' con st.session_state.get('cp_venc') or ''
        venc = st.session_state.get("cp_venc") or ""
        # Asignamos 'cvv' con solo_digitos(st.session_state.get('cp_cvv'))
        cvv = solo_digitos(st.session_state.get("cp_cvv"))
        # Asignamos 'documento' con ''.join((ch for ch in str(st.session_state...
        documento = "".join(ch for ch in str(st.session_state.get("cp_doc") or "") if ch.isalnum())
        # Asignamos 'info_pago' con detectar_tarjeta(numero[:8], MP_PK) if len...
        info_pago = detectar_tarjeta(numero[:8], MP_PK) if len(numero) >= 6 else None
        # Asignamos 'errores' con validar(numero, nombre, venc, cvv, info_pago)
        errores = validar(numero, nombre, venc, cvv, info_pago)
        # Evaluamos la condición lógica (not documento) para controlar el flujo
        if not documento:
            # Ejecutamos instrucción: errores.append('Ingrese el RUT o documento del titul...
            errores.append("Ingrese el RUT o documento del titular.")

        # Evaluamos la condición lógica (errores) para controlar el flujo
        if errores:
            # Ejecutamos instrucción: st.error('\n\n'.join(errores))
            st.error("\n\n".join(errores))
        else:
            # Asignamos 'referencia' con 'PT-' + uuid.uuid4().hex[:8].upper()
            referencia = "PT-" + uuid.uuid4().hex[:8].upper()
            # Asignamos 'MP_TOKEN' con _mp_access_token()
            MP_TOKEN = _mp_access_token()
            # Evaluamos la condición lógica (MP_PK and MP_TOKEN) para controlar el flujo
            if MP_PK and MP_TOKEN:
                # Gestión automática de contexto y recursos para: st.spinner('Procesando pago con Mercado Pago...')
                with st.spinner("Procesando pago con Mercado Pago..."):
                    # Bloque try/except para manejo seguro de errores y resiliencia operativa
                    try:
                        # Asignamos 'res' con pagar_con_mercadopago(MP_PK, MP_TOKEN, num...
                        res = pagar_con_mercadopago(MP_PK, MP_TOKEN, numero, nombre, venc, cvv, documento, info_pago, referencia)
                    except Exception as exc:
                        # Asignamos 'res' con {'ok': False, 'mensaje': f'No se pudo cone...
                        res = {"ok": False, "mensaje": f"No se pudo conectar con Mercado Pago ({type(exc).__name__})."}
                # Asignamos 'fuente_pago' con 'Mercado Pago (ambiente de prueba)'
                fuente_pago = "Mercado Pago (ambiente de prueba)"
            else:
                # Gestión automática de contexto y recursos para: st.spinner('Procesando pago...')
                with st.spinner("Procesando pago..."):
                    # Ejecutamos instrucción: time.sleep(1.6)
                    time.sleep(1.6)
                # Asignamos 'rechazo' con RESULTADOS_SANDBOX.get(nombre.upper())
                rechazo = RESULTADOS_SANDBOX.get(nombre.upper())
                # Asignamos 'res' con {'ok': not rechazo, 'mensaje': rechazo + '...
                res = {"ok": not rechazo, "mensaje": (rechazo + " Intente con otra tarjeta.") if rechazo else ""}
                # Asignamos 'fuente_pago' con 'Simulado (Mercado Pago no configurado)'
                fuente_pago = "Simulado (Mercado Pago no configurado)"

            # Evaluamos la condición lógica (not res.get('ok')) para controlar el flujo
            if not res.get("ok"):
                # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
                st.error(res.get("mensaje") or "El pago fue rechazado.")
            else:
                # Pago aprobado: activar el plan en la sesión y en la base de datos si existe la función
                st.session_state["user_info"]["plan"] = "premium"
                # Asignamos '(guardado_ok, guardado_msg)' con (False, 'La base de datos no tiene la func...
                guardado_ok, guardado_msg = False, "La base de datos no tiene la función de planes."
                # Evaluamos la condición lógica (actualizar_plan_usuario and u_ident) para controlar el flujo
                if actualizar_plan_usuario and u_ident:
                    # Bloque try/except para manejo seguro de errores y resiliencia operativa
                    try:
                        # Asignamos '(guardado_ok, guardado_msg)' con actualizar_plan_usuario(u_ident, 'premium'...
                        guardado_ok, guardado_msg = actualizar_plan_usuario(
                            u_ident, "premium",
                            email=user_info.get("email"),
                            nombre=user_info.get("nombre"),
                        )
                    except Exception as exc:
                        # Asignamos '(guardado_ok, guardado_msg)' con (False, f'Error al guardar el plan ({type(...
                        guardado_ok, guardado_msg = False, f"Error al guardar el plan ({type(exc).__name__})."
                # Evaluamos la condición lógica (guardado_ok and obtener_perfil_usuario) para controlar el flujo
                if guardado_ok and obtener_perfil_usuario:
                    # Bloque try/except para manejo seguro de errores y resiliencia operativa
                    try:
                        # Asignamos 'perfil_nuevo' con obtener_perfil_usuario(user_info.get('emai...
                        perfil_nuevo = obtener_perfil_usuario(user_info.get("email") or u_ident) or {}
                        # Recorremos iterativamente cada 'k' en ('id', 'plan', 'plan_activado_en', 'plan_v...
                        for k in ("id", "plan", "plan_activado_en", "plan_vence_en"):
                            # Evaluamos la condición lógica (perfil_nuevo.get(k)) para controlar el flujo
                            if perfil_nuevo.get(k):
                                # Asignamos 'st.session_state['user_info'][k]' con perfil_nuevo[k]
                                st.session_state["user_info"][k] = perfil_nuevo[k]
                    except Exception:
                        # Ejecutamos instrucción: pass
                        pass
                # Asignamos 'st.session_state['cp_recibo']' con {'orden': referencia, 'fecha': datetime.no...
                st.session_state["cp_recibo"] = {
                    "orden": referencia,
                    "fecha": datetime.now().strftime("%d-%m-%Y %H:%M"),
                    "tipo": tipo_legible((info_pago or {}).get("tipo")) or tipo,
                    "marca": (info_pago or {}).get("marca") or "Tarjeta",
                    "last4": numero[-4:],
                    "monto": PRECIO_PREMIUM,
                    "procesador": fuente_pago,
                    "mp_orden": res.get("orden_id", ""),
                    "guardado": guardado_ok,
                    "guardado_msg": guardado_msg,
                }
                # Los datos de la tarjeta no se conservan
                for k in ("cp_num", "cp_nombre", "cp_venc", "cp_cvv", "cp_doc", "_cp_ultimo_bin"):
                    # Ejecutamos instrucción: st.session_state.pop(k, None)
                    st.session_state.pop(k, None)
                # Ejecutamos instrucción: st.rerun()
                st.rerun()

# Gestión automática de contexto y recursos para: col_resumen
with col_resumen:
    # Renderizado de componente visual o control interactivo en la interfaz Streamlit
    st.markdown("<div class='cp-step'>Resumen</div>", unsafe_allow_html=True)
    # Asignamos 'items' con ''.join((f'<div class="cp-sum-item"><div c...
    items = "".join(
        f'<div class="cp-sum-item"><div class="cp-sum-dot">{svg_check_dark}</div><div>{t}</div></div>'
        for t in [
            "Incluye todos los beneficios del plan Free",
            "Notificación cuando un perfume favorito baja de precio",
            "Detalle de la tienda y del nuevo precio",
            "Insignia de usuario Premium verificado",
        ]
    )
    # Renderizado de componente visual o control interactivo en la interfaz Streamlit
    st.markdown(clean_html(f"""
        <div class="cp-summary">
            <div class="cp-sum-name">Plan Premium</div>
            <div class="cp-sum-for">Suscripción mensual</div>
            <div class="cp-sum-list">{items}</div>
            <div class="cp-sum-line"><div>Plan Premium (1 mes)</div><div>$2.000</div></div>
            <div class="cp-sum-total">
                <div class="cp-sum-total-label">Total</div>
                <div class="cp-sum-total-val">$2.000 CLP</div>
            </div>
            <div class="cp-secure">{svg_lock}<div>Detección de tarjeta con Mercado Pago. Solo se consultan los primeros dígitos; el número completo no se envía ni se almacena.</div></div>
        </div>
    """), unsafe_allow_html=True)
