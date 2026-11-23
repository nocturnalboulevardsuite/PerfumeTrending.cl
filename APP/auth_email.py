"""
PerfumeTrending.cl — Inicio de sesión real con correo electrónico y código (OTP)
================================================================================
Flujo:
1. El usuario escribe su correo (y opcionalmente su nombre si es una cuenta nueva).
2. Se genera un código de 6 dígitos, se guarda solo su hash (SHA-256 + sal) con vencimiento,
   y se envía DE VERDAD al correo mediante SMTP (Gmail, Outlook, Zoho, SendGrid, Brevo, etc.).
3. El usuario escribe el código recibido; si coincide y no ha vencido, la sesión queda iniciada
   en `st.session_state['logged_in']` / `st.session_state['user_info']`, igual que antes.

Configuración (archivo .streamlit/secrets.toml o variables de entorno):

    [smtp]
    host = "smtp.gmail.com"
    port = 587                      # 587 = STARTTLS, 465 = SSL
    user = "tucorreo@gmail.com"
    password = "contraseña de aplicación de 16 letras"
    sender_name = "PerfumeTrending"
    # sender_email = "no-responder@tudominio.cl"   (opcional, por defecto = user)

Variables de entorno equivalentes: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD,
SMTP_SENDER_NAME, SMTP_SENDER_EMAIL.
"""

# Importación de librería estándar o dependencia externa (hashlib)
import hashlib
# Importación de librería estándar o dependencia externa (hmac)
import hmac
# Importación de librería estándar o dependencia externa (html)
import html
# Importación de librería estándar o dependencia externa (os)
import os
# Importación de librería estándar o dependencia externa (re)
import re
# Importación de librería estándar o dependencia externa (secrets)
import secrets
# Importación de librería estándar o dependencia externa (smtplib)
import smtplib
# Importación de librería estándar o dependencia externa (ssl)
import ssl
# Importación de librería estándar o dependencia externa (time)
import time
# Importación de componentes (EmailMessage) desde el módulo 'email.message'
from email.message import EmailMessage
# Importación de componentes (formataddr) desde el módulo 'email.utils'
from email.utils import formataddr

# Importación de librería estándar o dependencia externa (streamlit)
import streamlit as st

# Bloque try/except para manejo seguro de errores y resiliencia operativa
try:
    # Importación de componentes (obtener_perfil_usuario) desde el módulo 'backend.database'
    from backend.database import obtener_perfil_usuario
except Exception:  # pragma: no cover - el backend siempre existe en producción
    # Asignamos 'obtener_perfil_usuario' con None
    obtener_perfil_usuario = None

# Bloque try/except para manejo seguro de errores y resiliencia operativa
try:
    # Importación de componentes (actualizar_perfil_usuario) desde el módulo 'backend.database'
    from backend.database import actualizar_perfil_usuario
except Exception:  # pragma: no cover
    # Asignamos 'actualizar_perfil_usuario' con None
    actualizar_perfil_usuario = None

# Bloque try/except para manejo seguro de errores y resiliencia operativa
try:
    # Importación de componentes (agregar_favorito) desde el módulo 'backend.database'
    from backend.database import agregar_favorito
except Exception:  # pragma: no cover
    # Asignamos 'agregar_favorito' con None
    agregar_favorito = None


# Asignamos 'CODIGO_DIGITOS' con 6
CODIGO_DIGITOS = 6
# Asignamos 'CODIGO_VIGENCIA_SEG' con 10 * 60
CODIGO_VIGENCIA_SEG = 10 * 60      # el código vence a los 10 minutos
# Asignamos 'REENVIO_ESPERA_SEG' con 45
REENVIO_ESPERA_SEG = 45            # tiempo mínimo entre envíos
# Asignamos 'MAX_INTENTOS' con 5
MAX_INTENTOS = 5                   # intentos fallidos antes de pedir un código nuevo
# Asignamos 'EMAIL_RE' con re.compile('^[A-Za-z0-9._%+\\-]+@[A-Za-z0-...
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")


# -----------------------------------------------------------------------------
# Configuración SMTP
# -----------------------------------------------------------------------------
def _smtp_config():
    # Asignamos 'cfg' con {}
    cfg = {}
    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Evaluamos la condición lógica ('smtp' in st.secrets) para controlar el flujo
        if "smtp" in st.secrets:
            # Asignamos 'cfg' con dict(st.secrets['smtp'])
            cfg = dict(st.secrets["smtp"])
    except Exception:
        # Asignamos 'cfg' con {}
        cfg = {}

    # Definición de función 'pick' (parámetros: key, env, default)
    def pick(key, env, default=None):
        # Asignamos 'val' con cfg.get(key)
        val = cfg.get(key)
        # Evaluamos la condición lógica (val in (None, '')) para controlar el flujo
        if val in (None, ""):
            # Asignamos 'val' con os.environ.get(env, default)
            val = os.environ.get(env, default)
        # Retornamos el resultado procesado (val)
        return val

    # Asignamos 'host' con pick('host', 'SMTP_HOST')
    host = pick("host", "SMTP_HOST")
    # Asignamos 'user' con pick('user', 'SMTP_USER')
    user = pick("user", "SMTP_USER")
    # Asignamos 'password' con pick('password', 'SMTP_PASSWORD')
    password = pick("password", "SMTP_PASSWORD")
    # Asignamos 'port' con int(pick('port', 'SMTP_PORT', 587) or 587)
    port = int(pick("port", "SMTP_PORT", 587) or 587)
    # Asignamos 'sender_name' con pick('sender_name', 'SMTP_SENDER_NAME', 'P...
    sender_name = pick("sender_name", "SMTP_SENDER_NAME", "PerfumeTrending")
    # Asignamos 'sender_email' con pick('sender_email', 'SMTP_SENDER_EMAIL', ...
    sender_email = pick("sender_email", "SMTP_SENDER_EMAIL", user)
    # Evaluamos la condición lógica (not (host and user and password and sender_email)) para controlar el flujo
    if not (host and user and password and sender_email):
        # Retornamos el resultado procesado (None)
        return None
    # Retornamos el resultado procesado ({'host': host, 'port': port, 'user': user, 'pas...)
    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "sender_name": sender_name,
        "sender_email": sender_email,
    }


# Definición de función 'smtp_configurado' sin parámetros externos
def smtp_configurado() -> bool:
    # Retornamos el resultado procesado (_smtp_config() is not None)
    return _smtp_config() is not None


# -----------------------------------------------------------------------------
# Código y correo
# -----------------------------------------------------------------------------
def _hash_codigo(codigo: str, sal: str) -> str:
    # Retornamos el resultado procesado (hashlib.sha256(f'{sal}:{codigo}'.encode('utf-8'...)
    return hashlib.sha256(f"{sal}:{codigo}".encode("utf-8")).hexdigest()


# Definición de función '_html_correo' (parámetros: codigo, nombre)
def _html_correo(codigo: str, nombre: str) -> str:
    # Asignamos 'saludo' con f'Hola {nombre},' if nombre else 'Hola,'
    saludo = f"Hola {nombre}," if nombre else "Hola,"
    # Asignamos 'minutos' con CODIGO_VIGENCIA_SEG // 60
    minutos = CODIGO_VIGENCIA_SEG // 60
    # Retornamos el resultado procesado (f'<!doctype html>\n<html lang="es">\n<body styl...)
    return f"""\
<!doctype html>
<html lang="es">
<body style="margin:0;padding:0;background:#f6f4f1;font-family:Arial,Helvetica,sans-serif;color:#1c1917;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f6f4f1;padding:32px 12px;">
    <tr><td align="center">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:480px;background:#ffffff;border:1px solid #e6e1db;border-radius:16px;padding:32px;">
        <tr><td style="font-size:22px;"><span style="font-weight:300;">Perfume</span><strong>Trending</strong></td></tr>
        <tr><td style="padding-top:24px;font-size:16px;line-height:1.5;">{saludo}<br>usa este código para ingresar a tu cuenta:</td></tr>
        <tr><td align="center" style="padding:24px 0;">
          <div style="display:inline-block;font-size:34px;font-weight:800;letter-spacing:10px;background:#fbf3f3;color:#d83737;border:1px solid #f1caca;border-radius:12px;padding:14px 22px;">{codigo}</div>
        </td></tr>
        <tr><td style="font-size:14px;line-height:1.5;color:#6b6159;">El código vence en {minutos} minutos. Si no pediste este código, puedes ignorar este correo: nadie podrá entrar a tu cuenta sin él.</td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


# Definición de función 'enviar_codigo_por_correo' (parámetros: destinatario, codigo, nombre)
def enviar_codigo_por_correo(destinatario: str, codigo: str, nombre: str = "") -> tuple[bool, str]:
    """Envía el código al correo indicado. Devuelve (ok, mensaje)."""
    # Asignamos 'cfg' con _smtp_config()
    cfg = _smtp_config()
    # Evaluamos la condición lógica (not cfg) para controlar el flujo
    if not cfg:
        # Retornamos el resultado procesado ((False, 'El envío de correos no está configurad...)
        return False, (
            "El envío de correos no está configurado. Agrega la sección [smtp] en "
            ".streamlit/secrets.toml (host, port, user, password)."
        )

    # Asignamos 'msg' con EmailMessage()
    msg = EmailMessage()
    # Asignamos 'msg['Subject']' con f'Tu código de acceso a PerfumeTrending: {...
    msg["Subject"] = f"Tu código de acceso a PerfumeTrending: {codigo}"
    # Asignamos 'msg['From']' con formataddr((cfg['sender_name'], cfg['sende...
    msg["From"] = formataddr((cfg["sender_name"], cfg["sender_email"]))
    # Asignamos 'msg['To']' con destinatario
    msg["To"] = destinatario
    # Asignamos 'minutos' con CODIGO_VIGENCIA_SEG // 60
    minutos = CODIGO_VIGENCIA_SEG // 60
    # Ejecutamos instrucción: msg.set_content(f'Tu código de acceso a PerfumeTrend...
    msg.set_content(
        f"Tu código de acceso a PerfumeTrending es: {codigo}\n\n"
        f"Vence en {minutos} minutos. Si no lo pediste, ignora este correo."
    )
    # Ejecutamos instrucción: msg.add_alternative(_html_correo(codigo, nombre), su...
    msg.add_alternative(_html_correo(codigo, nombre), subtype="html")

    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Asignamos 'contexto' con ssl.create_default_context()
        contexto = ssl.create_default_context()
        # Evaluamos la condición lógica (int(cfg['port']) == 465) para controlar el flujo
        if int(cfg["port"]) == 465:
            # Gestión automática de contexto y recursos para: smtplib.SMTP_SSL(cfg['host'], cfg['port'], cont...
            with smtplib.SMTP_SSL(cfg["host"], cfg["port"], context=contexto, timeout=20) as server:
                # Ejecutamos instrucción: server.login(cfg['user'], cfg['password'])
                server.login(cfg["user"], cfg["password"])
                # Ejecutamos instrucción: server.send_message(msg)
                server.send_message(msg)
        else:
            # Gestión automática de contexto y recursos para: smtplib.SMTP(cfg['host'], cfg['port'], timeout=20)
            with smtplib.SMTP(cfg["host"], cfg["port"], timeout=20) as server:
                # Ejecutamos instrucción: server.ehlo()
                server.ehlo()
                # Evaluamos la condición lógica (server.has_extn('starttls')) para controlar el flujo
                if server.has_extn("starttls"):
                    # Ejecutamos instrucción: server.starttls(context=contexto)
                    server.starttls(context=contexto)
                    # Ejecutamos instrucción: server.ehlo()
                    server.ehlo()
                # Ejecutamos instrucción: server.login(cfg['user'], cfg['password'])
                server.login(cfg["user"], cfg["password"])
                # Ejecutamos instrucción: server.send_message(msg)
                server.send_message(msg)
        # Retornamos el resultado procesado ((True, 'Código enviado.'))
        return True, "Código enviado."
    except smtplib.SMTPAuthenticationError:
        # Retornamos el resultado procesado ((False, 'El servidor de correo rechazó el usuar...)
        return False, "El servidor de correo rechazó el usuario o la contraseña SMTP. Revisa la configuración."
    except smtplib.SMTPRecipientsRefused:
        # Retornamos el resultado procesado ((False, 'Ese correo no acepta mensajes. Revisa ...)
        return False, "Ese correo no acepta mensajes. Revisa que esté bien escrito."
    except Exception as exc:  # red, DNS, puerto bloqueado, etc.
        # Retornamos el resultado procesado ((False, f'No se pudo enviar el correo ({type(ex...)
        return False, f"No se pudo enviar el correo ({type(exc).__name__}). Inténtalo de nuevo en unos segundos."


# -----------------------------------------------------------------------------
# Estado del flujo
# -----------------------------------------------------------------------------
def _reset_flujo():
    # Recorremos iterativamente cada 'k' en ('_otp_stage', '_otp_email', '_otp_nombre'...
    for k in ("_otp_stage", "_otp_email", "_otp_nombre", "_otp_hash", "_otp_sal",
              "_otp_expira", "_otp_intentos", "_otp_ultimo_envio", "_otp_error", "_otp_info"):
        # Ejecutamos instrucción: st.session_state.pop(k, None)
        st.session_state.pop(k, None)


# Definición de función '_generar_y_enviar' (parámetros: email, nombre)
def _generar_y_enviar(email: str, nombre: str) -> tuple[bool, str]:
    # Asignamos 'ahora' con time.time()
    ahora = time.time()
    # Asignamos 'ultimo' con float(st.session_state.get('_otp_ultimo_en...
    ultimo = float(st.session_state.get("_otp_ultimo_envio") or 0)
    # Asignamos 'espera' con REENVIO_ESPERA_SEG - (ahora - ultimo)
    espera = REENVIO_ESPERA_SEG - (ahora - ultimo)
    # Evaluamos la condición lógica (ultimo and espera > 0 and (st.session_state.get('_ot...) para controlar el flujo
    if ultimo and espera > 0 and st.session_state.get("_otp_email") == email:
        # Retornamos el resultado procesado ((False, f'Espera {int(espera) + 1} segundos ant...)
        return False, f"Espera {int(espera) + 1} segundos antes de pedir otro código."

    # Asignamos 'codigo' con f'{secrets.randbelow(10 ** CODIGO_DIGITOS)...
    codigo = f"{secrets.randbelow(10 ** CODIGO_DIGITOS):0{CODIGO_DIGITOS}d}"
    # Asignamos '(ok, mensaje)' con enviar_codigo_por_correo(email, codigo, no...
    ok, mensaje = enviar_codigo_por_correo(email, codigo, nombre)
    # Evaluamos la condición lógica (not ok) para controlar el flujo
    if not ok:
        # Retornamos el resultado procesado ((False, mensaje))
        return False, mensaje

    # Asignamos 'sal' con secrets.token_hex(8)
    sal = secrets.token_hex(8)
    # Asignamos 'st.session_state['_otp_email']' con email
    st.session_state["_otp_email"] = email
    # Asignamos 'st.session_state['_otp_nombre']' con nombre
    st.session_state["_otp_nombre"] = nombre
    # Asignamos 'st.session_state['_otp_sal']' con sal
    st.session_state["_otp_sal"] = sal
    # Asignamos 'st.session_state['_otp_hash']' con _hash_codigo(codigo, sal)
    st.session_state["_otp_hash"] = _hash_codigo(codigo, sal)
    # Asignamos 'st.session_state['_otp_expira']' con ahora + CODIGO_VIGENCIA_SEG
    st.session_state["_otp_expira"] = ahora + CODIGO_VIGENCIA_SEG
    # Asignamos 'st.session_state['_otp_intentos']' con 0
    st.session_state["_otp_intentos"] = 0
    # Asignamos 'st.session_state['_otp_ultimo_en...' con ahora
    st.session_state["_otp_ultimo_envio"] = ahora
    # Asignamos 'st.session_state['_otp_stage']' con 'code'
    st.session_state["_otp_stage"] = "code"
    # Retornamos el resultado procesado ((True, mensaje))
    return True, mensaje


# Definición de función '_verificar' (parámetros: codigo_ingresado)
def _verificar(codigo_ingresado: str) -> tuple[bool, str]:
    # Asignamos 'codigo_ingresado' con re.sub('\\D', '', codigo_ingresado or '')
    codigo_ingresado = re.sub(r"\D", "", codigo_ingresado or "")
    # Evaluamos la condición lógica (len(codigo_ingresado) != CODIGO_DIGITOS) para controlar el flujo
    if len(codigo_ingresado) != CODIGO_DIGITOS:
        # Retornamos el resultado procesado ((False, f'El código tiene {CODIGO_DIGITOS} dígi...)
        return False, f"El código tiene {CODIGO_DIGITOS} dígitos."
    # Evaluamos la condición lógica (time.time() > float(st.session_state.get('_otp_expir...) para controlar el flujo
    if time.time() > float(st.session_state.get("_otp_expira") or 0):
        # Retornamos el resultado procesado ((False, 'El código venció. Pide uno nuevo.'))
        return False, "El código venció. Pide uno nuevo."
    # Asignamos 'intentos' con int(st.session_state.get('_otp_intentos') ...
    intentos = int(st.session_state.get("_otp_intentos") or 0)
    # Evaluamos la condición lógica (intentos >= MAX_INTENTOS) para controlar el flujo
    if intentos >= MAX_INTENTOS:
        # Retornamos el resultado procesado ((False, 'Demasiados intentos. Pide un código nu...)
        return False, "Demasiados intentos. Pide un código nuevo."
    # Asignamos 'esperado' con st.session_state.get('_otp_hash') or ''
    esperado = st.session_state.get("_otp_hash") or ""
    # Asignamos 'recibido' con _hash_codigo(codigo_ingresado, st.session_...
    recibido = _hash_codigo(codigo_ingresado, st.session_state.get("_otp_sal") or "")
    # Evaluamos la condición lógica (not hmac.compare_digest(esperado, recibido)) para controlar el flujo
    if not hmac.compare_digest(esperado, recibido):
        # Asignamos 'st.session_state['_otp_intentos']' con intentos + 1
        st.session_state["_otp_intentos"] = intentos + 1
        # Asignamos 'restantes' con MAX_INTENTOS - intentos - 1
        restantes = MAX_INTENTOS - intentos - 1
        # Retornamos el resultado procesado ((False, f"Código incorrecto. Te quedan {restant...)
        return False, f"Código incorrecto. Te quedan {restantes} intento{'s' if restantes != 1 else ''}."
    # Retornamos el resultado procesado ((True, 'ok'))
    return True, "ok"


# Definición de función '_iniciar_sesion' (parámetros: email, nombre)
def _iniciar_sesion(email: str, nombre: str):
    """Deja la sesión iniciada con la misma estructura que usa el resto de la app."""
    # Asignamos 'perfil' con None
    perfil = None
    # Evaluamos la condición lógica (obtener_perfil_usuario) para controlar el flujo
    if obtener_perfil_usuario:
        # Bloque try/except para manejo seguro de errores y resiliencia operativa
        try:
            # Asignamos 'perfil' con obtener_perfil_usuario(email)
            perfil = obtener_perfil_usuario(email)
        except Exception:
            # Asignamos 'perfil' con None
            perfil = None

    # Asignamos 'info' con {'id': email, 'email': email, 'nombre': no...
    info = {"id": email, "email": email, "nombre": nombre}
    # Evaluamos la condición lógica (isinstance(perfil, dict) and perfil) para controlar el flujo
    if isinstance(perfil, dict) and perfil:
        # Ejecutamos instrucción: info.update({k: v for k, v in perfil.items() if v no...
        info.update({k: v for k, v in perfil.items() if v not in (None, "")})
        # Ejecutamos instrucción: info.setdefault('email', email)
        info.setdefault("email", email)
        # Evaluamos la condición lógica (not info.get('id')) para controlar el flujo
        if not info.get("id"):
            # Asignamos 'info['id']' con email
            info["id"] = email
    # Evaluamos la condición lógica (actualizar_perfil_usuario) para controlar el flujo
    elif actualizar_perfil_usuario:
        # Cuenta nueva: se registra el perfil básico con el correo como identificador.
        try:
            # Ejecutamos instrucción: actualizar_perfil_usuario(email, nombre=nombre or ''...
            actualizar_perfil_usuario(
                email,
                nombre=nombre or "",
                email=email,
                telefono="",
                bio="",
                foto_perfil="",
                ubicacion="Santiago, Chile",
            )
        except Exception:
            # Ejecutamos instrucción: pass
            pass

    # Asignamos 'st.session_state['logged_in']' con True
    st.session_state["logged_in"] = True
    # Asignamos 'st.session_state['user_info']' con info
    st.session_state["user_info"] = info
    # Asignamos 'st.session_state['_perfil_cloud_...' con False
    st.session_state["_perfil_cloud_synced"] = False
    # Asignamos 'st.session_state['favoritos']' con []
    st.session_state["favoritos"] = []
    # Ejecutamos instrucción: st.session_state.pop('_favoritos_cargados_para', None)
    st.session_state.pop("_favoritos_cargados_para", None)

    # Si antes de iniciar sesión tocó un corazón, se guarda ese favorito ahora.
    pendiente = st.session_state.pop("_fav_pendiente", None)
    # Evaluamos la condición lógica (pendiente is not None and agregar_favorito) para controlar el flujo
    if pendiente is not None and agregar_favorito:
        # Bloque try/except para manejo seguro de errores y resiliencia operativa
        try:
            # Ejecutamos instrucción: agregar_favorito(info.get('id') or email, int(pendie...
            agregar_favorito(info.get("id") or email, int(pendiente))
            # Asignamos 'st.session_state['_fav_aviso']' con ('Iniciaste sesión y guardamos la fraganci...
            st.session_state["_fav_aviso"] = ("Iniciaste sesión y guardamos la fragancia en tus favoritos.", "❤️")
        except Exception:
            # Ejecutamos instrucción: pass
            pass
    # Evaluamos la condición lógica ('_fav_aviso' not in st.session_state) para controlar el flujo
    if "_fav_aviso" not in st.session_state:
        # Asignamos 'st.session_state['_fav_aviso']' con ('Has ingresado a tu cuenta.', '✅')
        st.session_state["_fav_aviso"] = ("Has ingresado a tu cuenta.", "✅")


# -----------------------------------------------------------------------------
# Estilos del modal de acceso
# -----------------------------------------------------------------------------
def _paleta_modal():
    """Colores según el tema activo (oscuro por defecto si no se puede leer la paleta)."""
    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Importación de componentes (get_theme_palette) desde el módulo 'ui'
        from ui import get_theme_palette
        # Asignamos 'pal' con get_theme_palette()
        pal = get_theme_palette()
        # Asignamos 'oscuro' con bool(pal.is_dark)
        oscuro = bool(pal.is_dark)
    except Exception:
        # Asignamos 'oscuro' con True
        oscuro = True
    # Evaluamos la condición lógica (oscuro) para controlar el flujo
    if oscuro:
        # Retornamos el resultado procesado ({'text': '#f5f5f4', 'sub': '#a8a29e', 'border':...)
        return {"text": "#f5f5f4", "sub": "#a8a29e", "border": "rgba(255,255,255,0.12)",
                "field": "rgba(255,255,255,0.04)", "soft": "rgba(255,255,255,0.06)"}
    # Retornamos el resultado procesado ({'text': '#1c1917', 'sub': '#6b6159', 'border':...)
    return {"text": "#1c1917", "sub": "#6b6159", "border": "#e2dcd5",
            "field": "#ffffff", "soft": "#f6f3ef"}


# Definición de función '_estilos_modal' sin parámetros externos
def _estilos_modal():
    # Asignamos 'c' con _paleta_modal()
    c = _paleta_modal()
    # Asignamos 'accent' con '#d83737'
    accent = "#d83737"
    # Renderizado de componente visual o control interactivo en la interfaz Streamlit
    st.markdown(f"""
<style>
div[role="dialog"]:has(.pt-auth) {{ border-radius: 20px !important; }}
div[role="dialog"]:has(.pt-auth) h2 {{ font-size: 1rem !important; font-weight: 700 !important; color: {c["sub"]} !important; }}
.pt-auth {{ font-family: 'Manrope', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
.pt-auth-steps {{ display: flex; gap: 6px; margin: 0 0 18px; }}
.pt-auth-steps div {{ height: 4px; flex: 1; border-radius: 999px; background: {c["soft"]}; }}
.pt-auth-steps div.on {{ background: {accent}; }}
.pt-auth-title {{ font-size: 1.45rem; font-weight: 800; letter-spacing: -0.02em; color: {c["text"]}; line-height: 1.2; }}
.pt-auth-text {{ font-size: 0.92rem; color: {c["sub"]}; line-height: 1.5; margin: 6px 0 16px; }}
.pt-auth-text b {{ color: {c["text"]}; font-weight: 700; }}
.pt-auth-msg {{
    display: flex; align-items: flex-start; gap: 8px; font-size: 0.86rem; line-height: 1.45;
    padding: 10px 12px; border-radius: 12px; margin: 2px 0 12px;
    animation: pt-auth-msg-in 0.25s ease-out both;
}}
.pt-auth-msg svg {{ flex: 0 0 16px; margin-top: 1px; }}
.pt-auth-msg-error {{ background: rgba(216, 55, 55, 0.10); color: {"#fca5a5" if c["text"] == "#f5f5f4" else "#b91c1c"}; border: 1px solid rgba(216, 55, 55, 0.30); }}
.pt-auth-msg-ok {{ background: rgba(255, 122, 26, 0.10); color: {"#fdba74" if c["text"] == "#f5f5f4" else "#c2410c"}; border: 1px solid rgba(255, 122, 26, 0.32); }}
.pt-auth-msg-warn {{ background: {c["soft"]}; color: {c["sub"]}; border: 1px solid {c["border"]}; }}
@keyframes pt-auth-msg-in {{ from {{ opacity: 0; transform: translateY(-4px); }} to {{ opacity: 1; transform: none; }} }}
.pt-auth-foot {{ display: flex; align-items: center; justify-content: center; gap: 6px; font-size: 0.78rem; color: {c["sub"]}; margin-top: 14px; }}

/* Campos */
div[role="dialog"]:has(.pt-auth) [data-testid="stWidgetLabel"] p {{ font-size: 0.82rem !important; font-weight: 600 !important; color: {c["sub"]} !important; }}
div[role="dialog"]:has(.pt-auth) [data-testid="stTextInputRootElement"],
div[role="dialog"]:has(.pt-auth) div[data-baseweb="input"] {{
    background: {c["field"]} !important; border: 1px solid {c["border"]} !important;
    border-radius: 12px !important; min-height: 48px !important; box-shadow: none !important;
}}
div[role="dialog"]:has(.pt-auth) [data-testid="stTextInputRootElement"]:focus-within,
div[role="dialog"]:has(.pt-auth) div[data-baseweb="input"]:focus-within {{
    border-color: {accent} !important; box-shadow: 0 0 0 3px rgba(216, 55, 55, 0.15) !important;
}}
div[role="dialog"]:has(.pt-auth) input {{ font-size: 0.98rem !important; color: {c["text"]} !important; background: transparent !important; }}
div[role="dialog"] .st-key-_otp_input_codigo input {{
    text-align: center !important; font-size: 1.7rem !important; font-weight: 800 !important;
    letter-spacing: 0.45em !important; padding-left: 0.45em !important; font-variant-numeric: tabular-nums !important;
}}
div[role="dialog"] .st-key-_otp_input_codigo [data-testid="stTextInputRootElement"],
div[role="dialog"] .st-key-_otp_input_codigo div[data-baseweb="input"] {{ min-height: 60px !important; }}
div[role="dialog"]:has(.pt-auth) [data-testid="InputInstructions"] {{ display: none !important; }}

/* Botón principal */
div[role="dialog"] .st-key-_otp_btn_enviar button,
div[role="dialog"] .st-key-_otp_btn_verificar button {{
    background: {accent} !important; border: 1px solid {accent} !important; border-radius: 12px !important;
    min-height: 50px !important; box-shadow: 0 10px 22px -14px {accent} !important;
    transition: background-color 0.18s ease, transform 0.18s ease !important;
}}
div[role="dialog"] .st-key-_otp_btn_enviar button:hover,
div[role="dialog"] .st-key-_otp_btn_verificar button:hover {{ background: #b92d2d !important; border-color: #b92d2d !important; transform: translateY(-1px); }}
div[role="dialog"] .st-key-_otp_btn_enviar button p,
div[role="dialog"] .st-key-_otp_btn_verificar button p {{ color: #ffffff !important; font-weight: 700 !important; font-size: 0.98rem !important; }}

/* Acciones secundarias como enlaces */
div[role="dialog"] .st-key-_otp_btn_reenviar button,
div[role="dialog"] .st-key-_otp_btn_cambiar button {{
    background: transparent !important; border: none !important; box-shadow: none !important; min-height: 36px !important;
}}
div[role="dialog"] .st-key-_otp_btn_reenviar button p,
div[role="dialog"] .st-key-_otp_btn_cambiar button p {{ color: {c["sub"]} !important; font-weight: 600 !important; font-size: 0.86rem !important; }}
div[role="dialog"] .st-key-_otp_btn_reenviar button:hover p,
div[role="dialog"] .st-key-_otp_btn_cambiar button:hover p {{ color: {c["text"]} !important; text-decoration: underline; }}
</style>
""", unsafe_allow_html=True)


# Asignamos '_ICONO_ERROR' con '<svg width="16" height="16" viewBox="0 0 ...
_ICONO_ERROR = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>'
# Asignamos '_ICONO_OK' con '<svg width="16" height="16" viewBox="0 0 ...
_ICONO_OK = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>'
# Asignamos '_ICONO_CANDADO' con '<svg width="13" height="13" viewBox="0 0 ...
_ICONO_CANDADO = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/></svg>'


# Definición de función '_mensaje' (parámetros: texto, tipo)
def _mensaje(texto: str, tipo: str = "error"):
    # Asignamos 'icono' con _ICONO_OK if tipo == 'ok' else _ICONO_ERROR
    icono = _ICONO_OK if tipo == "ok" else _ICONO_ERROR
    # Renderizado de componente visual o control interactivo en la interfaz Streamlit
    st.markdown(
        f'<div class="pt-auth-msg pt-auth-msg-{tipo}">{icono}<div>{html.escape(texto)}</div></div>',
        unsafe_allow_html=True,
    )


# Definición de función '_encabezado' (parámetros: paso, titulo, texto_html)
def _encabezado(paso: int, titulo: str, texto_html: str):
    # Asignamos 'pasos' con ''.join((f'''<div class="{('on' if i <= pa...
    pasos = "".join(f'<div class="{"on" if i <= paso else ""}"></div>' for i in (1, 2))
    # Renderizado de componente visual o control interactivo en la interfaz Streamlit
    st.markdown(
        f'<div class="pt-auth"><div class="pt-auth-steps">{pasos}</div>'
        f'<div class="pt-auth-title">{titulo}</div><div class="pt-auth-text">{texto_html}</div></div>',
        unsafe_allow_html=True,
    )


# -----------------------------------------------------------------------------
# Modal de acceso (reemplaza al anterior y se usa en todas las páginas)
# -----------------------------------------------------------------------------
@st.dialog("Ingresar a PerfumeTrending")
def modal_autenticacion():
    # Ejecutamos instrucción: _estilos_modal()
    _estilos_modal()
    # Asignamos 'stage' con st.session_state.get('_otp_stage', 'email')
    stage = st.session_state.get("_otp_stage", "email")
    # Asignamos 'minutos' con CODIGO_VIGENCIA_SEG // 60
    minutos = CODIGO_VIGENCIA_SEG // 60

    # Evaluamos la condición lógica (stage == 'email') para controlar el flujo
    if stage == "email":
        # Ejecutamos instrucción: _encabezado(1, 'Ingresa con tu correo', f'Te enviare...
        _encabezado(
            1,
            "Ingresa con tu correo",
            f"Te enviaremos un código de {CODIGO_DIGITOS} dígitos. Si es tu primera vez, la cuenta se crea automáticamente.",
        )
        # Evaluamos la condición lógica (not smtp_configurado()) para controlar el flujo
        if not smtp_configurado():
            # Ejecutamos instrucción: _mensaje('El envío de códigos por correo aún no está...
            _mensaje("El envío de códigos por correo aún no está configurado en el servidor.", "warn")

        # Renderizado de componente visual o control interactivo en la interfaz Streamlit
        email = st.text_input(
            "Correo electrónico",
            value=st.session_state.get("_otp_email", ""),
            placeholder="tucorreo@ejemplo.cl",
            key="_otp_input_email",
        )
        # Renderizado de componente visual o control interactivo en la interfaz Streamlit
        nombre = st.text_input(
            "Nombre (opcional)",
            value=st.session_state.get("_otp_nombre", ""),
            placeholder="Ej: Camila Rojas",
            max_chars=80,
            key="_otp_input_nombre",
        )
        # Evaluamos la condición lógica (st.session_state.get('_otp_error')) para controlar el flujo
        if st.session_state.get("_otp_error"):
            # Ejecutamos instrucción: _mensaje(st.session_state.pop('_otp_error'), 'error')
            _mensaje(st.session_state.pop("_otp_error"), "error")

        # Evaluamos la condición lógica (st.button('Enviar código', key='_otp_btn_enviar', ty...) para controlar el flujo
        if st.button("Enviar código", key="_otp_btn_enviar", type="primary", use_container_width=True):
            # Asignamos 'email_limpio' con (email or '').strip().lower()
            email_limpio = (email or "").strip().lower()
            # Evaluamos la condición lógica (not EMAIL_RE.match(email_limpio)) para controlar el flujo
            if not EMAIL_RE.match(email_limpio):
                # Asignamos 'st.session_state['_otp_error']' con 'Escribe un correo válido, por ejemplo nom...
                st.session_state["_otp_error"] = "Escribe un correo válido, por ejemplo nombre@correo.cl."
            else:
                # Gestión automática de contexto y recursos para: st.spinner('Enviando código...')
                with st.spinner("Enviando código..."):
                    # Asignamos '(ok, mensaje)' con _generar_y_enviar(email_limpio, (nombre or...
                    ok, mensaje = _generar_y_enviar(email_limpio, (nombre or "").strip())
                # Evaluamos la condición lógica (ok) para controlar el flujo
                if ok:
                    # Asignamos 'st.session_state['_otp_info']' con 'Código enviado.'
                    st.session_state["_otp_info"] = "Código enviado."
                else:
                    # Asignamos 'st.session_state['_otp_error']' con mensaje
                    st.session_state["_otp_error"] = mensaje
            # Ejecutamos instrucción: st.rerun(scope='fragment')
            st.rerun(scope="fragment")

        # Renderizado de componente visual o control interactivo en la interfaz Streamlit
        st.markdown(
            f'<div class="pt-auth-foot">{_ICONO_CANDADO}<div>Sin contraseñas. El código vence en {minutos} minutos.</div></div>',
            unsafe_allow_html=True,
        )
        # Finalizamos la ejecución de la función retornando None
        return

    # --- Etapa 2: ingresar el código recibido ---
    email = st.session_state.get("_otp_email", "")
    # Ejecutamos instrucción: _encabezado(2, 'Revisa tu correo', f'Escribe el códi...
    _encabezado(
        2,
        "Revisa tu correo",
        f"Escribe el código de {CODIGO_DIGITOS} dígitos que enviamos a <b>{html.escape(email)}</b>. "
        "Si no aparece, revisa la carpeta de spam.",
    )
    # Evaluamos la condición lógica (st.session_state.get('_otp_info')) para controlar el flujo
    if st.session_state.get("_otp_info"):
        # Ejecutamos instrucción: _mensaje(st.session_state.pop('_otp_info'), 'ok')
        _mensaje(st.session_state.pop("_otp_info"), "ok")

    # Renderizado de componente visual o control interactivo en la interfaz Streamlit
    codigo = st.text_input(
        "Código de acceso",
        max_chars=CODIGO_DIGITOS,
        placeholder="000000",
        key="_otp_input_codigo",
        label_visibility="collapsed",
    )
    # Evaluamos la condición lógica (st.session_state.get('_otp_error')) para controlar el flujo
    if st.session_state.get("_otp_error"):
        # Ejecutamos instrucción: _mensaje(st.session_state.pop('_otp_error'), 'error')
        _mensaje(st.session_state.pop("_otp_error"), "error")

    # Evaluamos la condición lógica (st.button('Ingresar', key='_otp_btn_verificar', type...) para controlar el flujo
    if st.button("Ingresar", key="_otp_btn_verificar", type="primary", use_container_width=True):
        # Asignamos '(ok, mensaje)' con _verificar(codigo)
        ok, mensaje = _verificar(codigo)
        # Evaluamos la condición lógica (ok) para controlar el flujo
        if ok:
            # Asignamos 'nombre' con st.session_state.get('_otp_nombre', '')
            nombre = st.session_state.get("_otp_nombre", "")
            # Ejecutamos instrucción: _iniciar_sesion(email, nombre)
            _iniciar_sesion(email, nombre)
            # Ejecutamos instrucción: _reset_flujo()
            _reset_flujo()
            # Ejecutamos instrucción: st.session_state.pop('_otp_input_codigo', None)
            st.session_state.pop("_otp_input_codigo", None)
            # Ejecutamos instrucción: st.rerun()
            st.rerun()
        else:
            # Asignamos 'st.session_state['_otp_error']' con mensaje
            st.session_state["_otp_error"] = mensaje
            # Ejecutamos instrucción: st.rerun(scope='fragment')
            st.rerun(scope="fragment")

    # Renderizado de componente visual o control interactivo en la interfaz Streamlit
    col_a, col_b = st.columns(2)
    # Gestión automática de contexto y recursos para: col_a
    with col_a:
        # Evaluamos la condición lógica (st.button('Reenviar código', key='_otp_btn_reenviar'...) para controlar el flujo
        if st.button("Reenviar código", key="_otp_btn_reenviar", use_container_width=True):
            # Gestión automática de contexto y recursos para: st.spinner('Enviando un código nuevo...')
            with st.spinner("Enviando un código nuevo..."):
                # Asignamos '(ok, mensaje)' con _generar_y_enviar(email, st.session_state....
                ok, mensaje = _generar_y_enviar(email, st.session_state.get("_otp_nombre", ""))
            # Evaluamos la condición lógica (ok) para controlar el flujo
            if ok:
                # Asignamos 'st.session_state['_otp_info']' con 'Te enviamos un código nuevo.'
                st.session_state["_otp_info"] = "Te enviamos un código nuevo."
            else:
                # Asignamos 'st.session_state['_otp_error']' con mensaje
                st.session_state["_otp_error"] = mensaje
            # Ejecutamos instrucción: st.rerun(scope='fragment')
            st.rerun(scope="fragment")
    # Gestión automática de contexto y recursos para: col_b
    with col_b:
        # Evaluamos la condición lógica (st.button('Cambiar correo', key='_otp_btn_cambiar', ...) para controlar el flujo
        if st.button("Cambiar correo", key="_otp_btn_cambiar", use_container_width=True):
            # Asignamos 'st.session_state['_otp_stage']' con 'email'
            st.session_state["_otp_stage"] = "email"
            # Ejecutamos instrucción: st.rerun(scope='fragment')
            st.rerun(scope="fragment")
