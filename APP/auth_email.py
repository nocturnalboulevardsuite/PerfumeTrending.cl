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

import hashlib
import hmac
import html
import os
import re
import secrets
import smtplib
import ssl
import time
from email.message import EmailMessage
from email.utils import formataddr

import streamlit as st

try:
    from backend.database import obtener_perfil_usuario
except Exception:  # pragma: no cover - el backend siempre existe en producción
    obtener_perfil_usuario = None

try:
    from backend.database import actualizar_perfil_usuario
except Exception:  # pragma: no cover
    actualizar_perfil_usuario = None

try:
    from backend.database import agregar_favorito
except Exception:  # pragma: no cover
    agregar_favorito = None


CODIGO_DIGITOS = 6
CODIGO_VIGENCIA_SEG = 10 * 60      # el código vence a los 10 minutos
REENVIO_ESPERA_SEG = 45            # tiempo mínimo entre envíos
MAX_INTENTOS = 5                   # intentos fallidos antes de pedir un código nuevo
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")


# -----------------------------------------------------------------------------
# Configuración SMTP
# -----------------------------------------------------------------------------
def _smtp_config():
    cfg = {}
    try:
        if "smtp" in st.secrets:
            cfg = dict(st.secrets["smtp"])
    except Exception:
        cfg = {}

    def pick(key, env, default=None):
        val = cfg.get(key)
        if val in (None, ""):
            val = os.environ.get(env, default)
        return val

    host = pick("host", "SMTP_HOST")
    user = pick("user", "SMTP_USER")
    password = pick("password", "SMTP_PASSWORD")
    port = int(pick("port", "SMTP_PORT", 587) or 587)
    sender_name = pick("sender_name", "SMTP_SENDER_NAME", "PerfumeTrending")
    sender_email = pick("sender_email", "SMTP_SENDER_EMAIL", user)
    if not (host and user and password and sender_email):
        return None
    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "sender_name": sender_name,
        "sender_email": sender_email,
    }


def smtp_configurado() -> bool:
    return _smtp_config() is not None


# -----------------------------------------------------------------------------
# Código y correo
# -----------------------------------------------------------------------------
def _hash_codigo(codigo: str, sal: str) -> str:
    return hashlib.sha256(f"{sal}:{codigo}".encode("utf-8")).hexdigest()


def _html_correo(codigo: str, nombre: str) -> str:
    saludo = f"Hola {nombre}," if nombre else "Hola,"
    minutos = CODIGO_VIGENCIA_SEG // 60
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


def enviar_codigo_por_correo(destinatario: str, codigo: str, nombre: str = "") -> tuple[bool, str]:
    """Envía el código al correo indicado. Devuelve (ok, mensaje)."""
    cfg = _smtp_config()
    if not cfg:
        return False, (
            "El envío de correos no está configurado. Agrega la sección [smtp] en "
            ".streamlit/secrets.toml (host, port, user, password)."
        )

    msg = EmailMessage()
    msg["Subject"] = f"Tu código de acceso a PerfumeTrending: {codigo}"
    msg["From"] = formataddr((cfg["sender_name"], cfg["sender_email"]))
    msg["To"] = destinatario
    minutos = CODIGO_VIGENCIA_SEG // 60
    msg.set_content(
        f"Tu código de acceso a PerfumeTrending es: {codigo}\n\n"
        f"Vence en {minutos} minutos. Si no lo pediste, ignora este correo."
    )
    msg.add_alternative(_html_correo(codigo, nombre), subtype="html")

    try:
        contexto = ssl.create_default_context()
        if int(cfg["port"]) == 465:
            with smtplib.SMTP_SSL(cfg["host"], cfg["port"], context=contexto, timeout=20) as server:
                server.login(cfg["user"], cfg["password"])
                server.send_message(msg)
        else:
            with smtplib.SMTP(cfg["host"], cfg["port"], timeout=20) as server:
                server.ehlo()
                if server.has_extn("starttls"):
                    server.starttls(context=contexto)
                    server.ehlo()
                server.login(cfg["user"], cfg["password"])
                server.send_message(msg)
        return True, "Código enviado."
    except smtplib.SMTPAuthenticationError:
        return False, "El servidor de correo rechazó el usuario o la contraseña SMTP. Revisa la configuración."
    except smtplib.SMTPRecipientsRefused:
        return False, "Ese correo no acepta mensajes. Revisa que esté bien escrito."
    except Exception as exc:  # red, DNS, puerto bloqueado, etc.
        return False, f"No se pudo enviar el correo ({type(exc).__name__}). Inténtalo de nuevo en unos segundos."


# -----------------------------------------------------------------------------
# Estado del flujo
# -----------------------------------------------------------------------------
def _reset_flujo():
    for k in ("_otp_stage", "_otp_email", "_otp_nombre", "_otp_hash", "_otp_sal",
              "_otp_expira", "_otp_intentos", "_otp_ultimo_envio", "_otp_error", "_otp_info"):
        st.session_state.pop(k, None)


def _generar_y_enviar(email: str, nombre: str) -> tuple[bool, str]:
    ahora = time.time()
    ultimo = float(st.session_state.get("_otp_ultimo_envio") or 0)
    espera = REENVIO_ESPERA_SEG - (ahora - ultimo)
    if ultimo and espera > 0 and st.session_state.get("_otp_email") == email:
        return False, f"Espera {int(espera) + 1} segundos antes de pedir otro código."

    codigo = f"{secrets.randbelow(10 ** CODIGO_DIGITOS):0{CODIGO_DIGITOS}d}"
    ok, mensaje = enviar_codigo_por_correo(email, codigo, nombre)
    if not ok:
        return False, mensaje

    sal = secrets.token_hex(8)
    st.session_state["_otp_email"] = email
    st.session_state["_otp_nombre"] = nombre
    st.session_state["_otp_sal"] = sal
    st.session_state["_otp_hash"] = _hash_codigo(codigo, sal)
    st.session_state["_otp_expira"] = ahora + CODIGO_VIGENCIA_SEG
    st.session_state["_otp_intentos"] = 0
    st.session_state["_otp_ultimo_envio"] = ahora
    st.session_state["_otp_stage"] = "code"
    return True, mensaje


def _verificar(codigo_ingresado: str) -> tuple[bool, str]:
    codigo_ingresado = re.sub(r"\D", "", codigo_ingresado or "")
    if len(codigo_ingresado) != CODIGO_DIGITOS:
        return False, f"El código tiene {CODIGO_DIGITOS} dígitos."
    if time.time() > float(st.session_state.get("_otp_expira") or 0):
        return False, "El código venció. Pide uno nuevo."
    intentos = int(st.session_state.get("_otp_intentos") or 0)
    if intentos >= MAX_INTENTOS:
        return False, "Demasiados intentos. Pide un código nuevo."
    esperado = st.session_state.get("_otp_hash") or ""
    recibido = _hash_codigo(codigo_ingresado, st.session_state.get("_otp_sal") or "")
    if not hmac.compare_digest(esperado, recibido):
        st.session_state["_otp_intentos"] = intentos + 1
        restantes = MAX_INTENTOS - intentos - 1
        return False, f"Código incorrecto. Te quedan {restantes} intento{'s' if restantes != 1 else ''}."
    return True, "ok"


def _iniciar_sesion(email: str, nombre: str):
    """Deja la sesión iniciada con la misma estructura que usa el resto de la app."""
    perfil = None
    if obtener_perfil_usuario:
        try:
            perfil = obtener_perfil_usuario(email)
        except Exception:
            perfil = None

    info = {"id": email, "email": email, "nombre": nombre}
    if isinstance(perfil, dict) and perfil:
        info.update({k: v for k, v in perfil.items() if v not in (None, "")})
        info.setdefault("email", email)
        if not info.get("id"):
            info["id"] = email
    elif actualizar_perfil_usuario:
        # Cuenta nueva: se registra el perfil básico con el correo como identificador.
        try:
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
            pass

    st.session_state["logged_in"] = True
    st.session_state["user_info"] = info
    st.session_state["_perfil_cloud_synced"] = False
    st.session_state["favoritos"] = []
    st.session_state.pop("_favoritos_cargados_para", None)

    # Si antes de iniciar sesión tocó un corazón, se guarda ese favorito ahora.
    pendiente = st.session_state.pop("_fav_pendiente", None)
    if pendiente is not None and agregar_favorito:
        try:
            agregar_favorito(info.get("id") or email, int(pendiente))
            st.session_state["_fav_aviso"] = ("Iniciaste sesión y guardamos la fragancia en tus favoritos.", "❤️")
        except Exception:
            pass
    if "_fav_aviso" not in st.session_state:
        st.session_state["_fav_aviso"] = ("Has ingresado a tu cuenta.", "✅")


# -----------------------------------------------------------------------------
# Estilos del modal de acceso
# -----------------------------------------------------------------------------
def _paleta_modal():
    """Colores según el tema activo (oscuro por defecto si no se puede leer la paleta)."""
    try:
        from ui import get_theme_palette
        pal = get_theme_palette()
        oscuro = bool(pal.is_dark)
    except Exception:
        oscuro = True
    if oscuro:
        return {"text": "#f5f5f4", "sub": "#a8a29e", "border": "rgba(255,255,255,0.12)",
                "field": "rgba(255,255,255,0.04)", "soft": "rgba(255,255,255,0.06)"}
    return {"text": "#1c1917", "sub": "#6b6159", "border": "#e2dcd5",
            "field": "#ffffff", "soft": "#f6f3ef"}


def _estilos_modal():
    c = _paleta_modal()
    accent = "#d83737"
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


_ICONO_ERROR = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>'
_ICONO_OK = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>'
_ICONO_CANDADO = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/></svg>'


def _mensaje(texto: str, tipo: str = "error"):
    icono = _ICONO_OK if tipo == "ok" else _ICONO_ERROR
    st.markdown(
        f'<div class="pt-auth-msg pt-auth-msg-{tipo}">{icono}<div>{html.escape(texto)}</div></div>',
        unsafe_allow_html=True,
    )


def _encabezado(paso: int, titulo: str, texto_html: str):
    pasos = "".join(f'<div class="{"on" if i <= paso else ""}"></div>' for i in (1, 2))
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
    _estilos_modal()
    stage = st.session_state.get("_otp_stage", "email")
    minutos = CODIGO_VIGENCIA_SEG // 60

    if stage == "email":
        _encabezado(
            1,
            "Ingresa con tu correo",
            f"Te enviaremos un código de {CODIGO_DIGITOS} dígitos. Si es tu primera vez, la cuenta se crea automáticamente.",
        )
        if not smtp_configurado():
            _mensaje("El envío de códigos por correo aún no está configurado en el servidor.", "warn")

        email = st.text_input(
            "Correo electrónico",
            value=st.session_state.get("_otp_email", ""),
            placeholder="tucorreo@ejemplo.cl",
            key="_otp_input_email",
        )
        nombre = st.text_input(
            "Nombre (opcional)",
            value=st.session_state.get("_otp_nombre", ""),
            placeholder="Ej: Camila Rojas",
            max_chars=80,
            key="_otp_input_nombre",
        )
        if st.session_state.get("_otp_error"):
            _mensaje(st.session_state.pop("_otp_error"), "error")

        if st.button("Enviar código", key="_otp_btn_enviar", type="primary", use_container_width=True):
            email_limpio = (email or "").strip().lower()
            if not EMAIL_RE.match(email_limpio):
                st.session_state["_otp_error"] = "Escribe un correo válido, por ejemplo nombre@correo.cl."
            else:
                with st.spinner("Enviando código..."):
                    ok, mensaje = _generar_y_enviar(email_limpio, (nombre or "").strip())
                if ok:
                    st.session_state["_otp_info"] = "Código enviado."
                else:
                    st.session_state["_otp_error"] = mensaje
            st.rerun(scope="fragment")

        st.markdown(
            f'<div class="pt-auth-foot">{_ICONO_CANDADO}<div>Sin contraseñas. El código vence en {minutos} minutos.</div></div>',
            unsafe_allow_html=True,
        )
        return

    # --- Etapa 2: ingresar el código recibido ---
    email = st.session_state.get("_otp_email", "")
    _encabezado(
        2,
        "Revisa tu correo",
        f"Escribe el código de {CODIGO_DIGITOS} dígitos que enviamos a <b>{html.escape(email)}</b>. "
        "Si no aparece, revisa la carpeta de spam.",
    )
    if st.session_state.get("_otp_info"):
        _mensaje(st.session_state.pop("_otp_info"), "ok")

    codigo = st.text_input(
        "Código de acceso",
        max_chars=CODIGO_DIGITOS,
        placeholder="000000",
        key="_otp_input_codigo",
        label_visibility="collapsed",
    )
    if st.session_state.get("_otp_error"):
        _mensaje(st.session_state.pop("_otp_error"), "error")

    if st.button("Ingresar", key="_otp_btn_verificar", type="primary", use_container_width=True):
        ok, mensaje = _verificar(codigo)
        if ok:
            nombre = st.session_state.get("_otp_nombre", "")
            _iniciar_sesion(email, nombre)
            _reset_flujo()
            st.session_state.pop("_otp_input_codigo", None)
            st.rerun()
        else:
            st.session_state["_otp_error"] = mensaje
            st.rerun(scope="fragment")

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("Reenviar código", key="_otp_btn_reenviar", use_container_width=True):
            with st.spinner("Enviando un código nuevo..."):
                ok, mensaje = _generar_y_enviar(email, st.session_state.get("_otp_nombre", ""))
            if ok:
                st.session_state["_otp_info"] = "Te enviamos un código nuevo."
            else:
                st.session_state["_otp_error"] = mensaje
            st.rerun(scope="fragment")
    with col_b:
        if st.button("Cambiar correo", key="_otp_btn_cambiar", use_container_width=True):
            st.session_state["_otp_stage"] = "email"
            st.rerun(scope="fragment")
