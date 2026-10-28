"""
PerfumeTrending.cl — Modal Centralizado de Autenticación Segura
===============================================================
Sustituye las 6 copias espagueti del diálogo de acceso en todas las páginas:
- Elimina el falso OTP impreso en pantalla (vulnerabilidad crítica de suplantación).
- Soporta código OTP real por correo electrónico (SMTP SSL) únicamente cuando `SMTP_EMAIL`
  y `SMTP_PASSWORD` están configurados en `st.secrets`, con generación CSPRNG (`secrets`),
  digest HMAC-SHA256 en sesión, expiración en 5 minutos y cero exposición en interfaz.
- Aplica protección contra fuerza bruta por sesión (bloqueo tras fallos repetidos).
- Valida formato de correo electrónico y fortaleza mínima de contraseña (8+ caracteres).
- Hidrata automáticamente perfil y favoritos persistentes desde Supabase Auth / SQLite.
"""

import hashlib
import hmac
import html
import re
import secrets
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import streamlit as st

try:
    from backend.database import (
        crear_usuario,
        obtener_favoritos_Ids_usuario,
        obtener_perfil_usuario,
        verificar_usuario,
    )
except ImportError:
    from APP.backend.database import (
        crear_usuario,
        obtener_favoritos_Ids_usuario,
        obtener_perfil_usuario,
        verificar_usuario,
    )

EMAIL_REGEX = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_SECONDS = 30.0
OTP_TTL_SECONDS = 300.0


def _obtener_credenciales_smtp() -> tuple[str, str]:
    """Lee credenciales SMTP desde `st.secrets` de forma silenciosa y segura."""
    try:
        smtp_email = str(st.secrets.get("SMTP_EMAIL", "") or "").strip()
        smtp_password = str(st.secrets.get("SMTP_PASSWORD", "") or "").strip()
        if smtp_email and smtp_password and "@" in smtp_email:
            return smtp_email, smtp_password
    except Exception:
        pass
    return "", ""


def _enviar_codigo_otp_smtp(destinatario: str, codigo: str) -> bool:
    """Envía un código OTP de 6 dígitos por SMTP SSL sin exponer jamás el código en interfaz."""
    smtp_email, smtp_password = _obtener_credenciales_smtp()
    if not smtp_email or not smtp_password:
        return False

    codigo_safe = html.escape(codigo, quote=True)
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"{codigo_safe} es tu código de acceso a PerfumeTrending"
        msg["From"] = f"PerfumeTrending <{smtp_email}>"
        msg["To"] = destinatario

        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 500px; padding: 20px; border: 1px solid #2a2e39; border-radius: 10px; background-color: #0c0e12; color: #f0f0f0;">
            <h2 style="color: #d83737; margin-bottom: 10px;">PerfumeTrending</h2>
            <p style="font-size: 15px; color: #cccccc;">Hola,</p>
            <p style="font-size: 15px; color: #cccccc;">Tu código de verificación de un solo uso (válido por 5 minutos) es:</p>
            <div style="text-align: center; margin: 25px 0;">
                <span style="font-size: 32px; font-weight: bold; letter-spacing: 6px; color: #ffffff; background-color: #161920; padding: 12px 24px; border-radius: 8px; border: 1px solid #2a2e39;">{codigo_safe}</span>
            </div>
            <p style="font-size: 13px; color: #888890;">Si no solicitaste este acceso, puedes ignorar este mensaje de forma segura.</p>
        </div>
        """
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as server:
            server.login(smtp_email, smtp_password)
            server.sendmail(smtp_email, destinatario, msg.as_string())
        return True
    except Exception:
        return False


def _limpiar_estado_otp() -> None:
    st.session_state["otp_code_sent"] = False
    st.session_state["otp_contact"] = ""
    st.session_state["otp_digest"] = ""
    st.session_state["otp_salt"] = ""
    st.session_state["otp_expires_at"] = 0.0


def _resolver_usuario_otp_verificado(email_clean: str) -> dict:
    """
    Obtiene o aprovisiona el perfil persistente del usuario tras verificar criptográficamente
    la posesión de su casilla de correo vía OTP.
    """
    perfil = obtener_perfil_usuario(email_clean)
    if perfil:
        return perfil

    nombre_base = email_clean.split("@")[0].replace(".", " ").strip().title() or "Usuario"
    pwd_auto = secrets.token_urlsafe(24)
    ok_creado, _ = crear_usuario(nombre_base, email_clean, pwd_auto)
    if ok_creado:
        perfil_nuevo = obtener_perfil_usuario(email_clean)
        if perfil_nuevo:
            return perfil_nuevo
        ok_ver, u_data = verificar_usuario(email_clean, pwd_auto)
        if ok_ver and u_data:
            return u_data

    return {
        "id": email_clean,
        "nombre": nombre_base,
        "email": email_clean,
        "telefono": "",
        "ubicacion": "Santiago, Chile",
        "favoritos": obtener_favoritos_Ids_usuario(email_clean, email=email_clean),
    }


def cerrar_sesion_usuario() -> None:
    """Limpia de forma segura los datos de sesión autenticada."""
    st.session_state["logged_in"] = False
    st.session_state["user_info"] = None
    st.session_state["favoritos"] = []
    st.session_state["show_login_modal"] = False
    st.session_state["show_visual_modal"] = False
    _limpiar_estado_otp()


def hidratar_sesion_usuario(usuario_data: dict) -> None:
    """Carga el usuario autenticado y sincroniza su lista real de favoritos desde la BD."""
    st.session_state["logged_in"] = True
    st.session_state["user_info"] = usuario_data
    st.session_state["login_failed_attempts"] = 0
    st.session_state["login_lockout_until"] = 0.0
    _limpiar_estado_otp()

    favs_meta = usuario_data.get("favoritos")
    if isinstance(favs_meta, list):
        st.session_state["favoritos"] = [int(x) for x in favs_meta if str(x).isdigit()]
    else:
        uid = usuario_data.get("id")
        st.session_state["favoritos"] = obtener_favoritos_Ids_usuario(uid, email=usuario_data.get("email"))


@st.dialog("Acceso a PerfumeTrending")
def modal_autenticacion(btn_border: str = "#2a2e39") -> None:
    """Diálogo único y seguro de Inicio de Sesión, Registro y OTP SMTP verificado."""
    smtp_email, smtp_password = _obtener_credenciales_smtp()
    smtp_activo = bool(smtp_email and smtp_password)

    if smtp_activo:
        tab_codigo, tab_login, tab_registro = st.tabs(
            ["Código por Correo", "Iniciar Sesión", "Crear Cuenta"]
        )
    else:
        tab_codigo = None
        tab_login, tab_registro = st.tabs(["Iniciar Sesión", "Crear Cuenta"])

    now = time.time()
    lockout_until = float(st.session_state.get("login_lockout_until", 0.0) or 0.0)
    is_locked = now < lockout_until

    if tab_codigo is not None:
        with tab_codigo:
            st.markdown("#### Ingresa con código al correo")
            if is_locked:
                rem = int(lockout_until - now) + 1
                st.warning(f"Demasiados intentos fallidos. Espera {rem} segundos antes de volver a intentar.")

            if not st.session_state.get("otp_code_sent", False):
                with st.form("form_send_otp", clear_on_submit=False):
                    contact_input = st.text_input(
                        "Correo electrónico",
                        key="otp_contact_input",
                        placeholder="usuario@correo.cl",
                    )
                    btn_send = st.form_submit_button(
                        "Enviar código de verificación",
                        use_container_width=True,
                        disabled=is_locked,
                    )

                    if btn_send and not is_locked:
                        email_otp = (contact_input or "").strip().lower()
                        if not EMAIL_REGEX.match(email_otp):
                            st.error("Por favor ingresa un correo electrónico válido.")
                            st.session_state["show_login_modal"] = True
                        else:
                            code = f"{secrets.randbelow(900000) + 100000:06d}"
                            salt = secrets.token_hex(16)
                            digest = hmac.new(
                                salt.encode("utf-8"), code.encode("utf-8"), hashlib.sha256
                            ).hexdigest()

                            if _enviar_codigo_otp_smtp(email_otp, code):
                                st.session_state["otp_code_sent"] = True
                                st.session_state["otp_contact"] = email_otp
                                st.session_state["otp_salt"] = salt
                                st.session_state["otp_digest"] = digest
                                st.session_state["otp_expires_at"] = time.time() + OTP_TTL_SECONDS
                                st.session_state["show_login_modal"] = True
                                st.rerun()
                            else:
                                _limpiar_estado_otp()
                                st.error(
                                    "No fue posible enviar el código en este momento. "
                                    "Usa la pestaña 'Iniciar Sesión' con tu contraseña."
                                )
                                st.session_state["show_login_modal"] = True
            else:
                email_dest = st.session_state.get("otp_contact", "")
                st.success(
                    f"Enviamos un código de 6 dígitos a **{email_dest}**. "
                    "Revisa tu bandeja de entrada o carpeta de spam."
                )
                with st.form("form_verify_otp", clear_on_submit=False):
                    input_code = st.text_input(
                        "Código de 6 dígitos",
                        key="otp_code_input",
                        placeholder="123456",
                        max_chars=6,
                    )
                    btn_verify = st.form_submit_button(
                        "Verificar e Ingresar",
                        use_container_width=True,
                        disabled=is_locked,
                    )

                    if btn_verify and not is_locked:
                        exp_at = float(st.session_state.get("otp_expires_at", 0.0) or 0.0)
                        salt = str(st.session_state.get("otp_salt", "") or "")
                        expected_digest = str(st.session_state.get("otp_digest", "") or "")
                        cand = (input_code or "").strip()

                        if time.time() > exp_at or not salt or not expected_digest:
                            _limpiar_estado_otp()
                            st.error("El código ha expirado. Solicita uno nuevo.")
                            st.session_state["show_login_modal"] = True
                        else:
                            cand_digest = hmac.new(
                                salt.encode("utf-8"), cand.encode("utf-8"), hashlib.sha256
                            ).hexdigest()
                            if hmac.compare_digest(cand_digest, expected_digest):
                                u_data = _resolver_usuario_otp_verificado(email_dest)
                                hidratar_sesion_usuario(u_data)
                                st.session_state["show_login_modal"] = False
                                st.rerun()
                            else:
                                intentos = int(st.session_state.get("login_failed_attempts", 0)) + 1
                                st.session_state["login_failed_attempts"] = intentos
                                if intentos >= MAX_LOGIN_ATTEMPTS:
                                    st.session_state["login_lockout_until"] = time.time() + LOCKOUT_SECONDS
                                    st.session_state["login_failed_attempts"] = 0
                                    _limpiar_estado_otp()
                                    st.error("Demasiados intentos inválidos. Espera 30 s y solicita un nuevo código.")
                                else:
                                    st.error("Código incorrecto. Revisa e intenta nuevamente.")
                                st.session_state["show_login_modal"] = True

                if st.button("Cambiar correo electrónico", key="btn_reset_otp", use_container_width=True):
                    _limpiar_estado_otp()
                    st.session_state["show_login_modal"] = True
                    st.rerun()

    with tab_login:
        st.markdown("#### Ingresa a tu cuenta")
        if is_locked:
            rem = int(lockout_until - now) + 1
            st.warning(f"Demasiados intentos fallidos. Espera {rem} segundos antes de volver a intentar.")

        with st.form("form_login_pass", clear_on_submit=False):
            login_email = st.text_input(
                "Correo Electrónico",
                key="login_email_input",
                placeholder="usuario@correo.cl",
            )
            login_pass = st.text_input(
                "Contraseña",
                type="password",
                key="login_pass_input",
                placeholder="••••••••",
            )
            btn_login = st.form_submit_button(
                "Ingresar a la plataforma",
                use_container_width=True,
                disabled=is_locked,
            )

            if btn_login and not is_locked:
                email_clean = (login_email or "").strip().lower()
                if not email_clean or not login_pass:
                    st.error("Por favor ingresa tu correo y contraseña.")
                    st.session_state["show_login_modal"] = True
                elif not EMAIL_REGEX.match(email_clean):
                    st.error("Ingresa un correo electrónico con formato válido.")
                    st.session_state["show_login_modal"] = True
                else:
                    exito, usuario_data = verificar_usuario(email_clean, login_pass)
                    if exito and usuario_data:
                        hidratar_sesion_usuario(usuario_data)
                        st.session_state["show_login_modal"] = False
                        st.rerun()
                    else:
                        intentos = int(st.session_state.get("login_failed_attempts", 0)) + 1
                        st.session_state["login_failed_attempts"] = intentos
                        if intentos >= MAX_LOGIN_ATTEMPTS:
                            st.session_state["login_lockout_until"] = time.time() + LOCKOUT_SECONDS
                            st.session_state["login_failed_attempts"] = 0
                            st.error("Cuenta protegida temporalmente por múltiples intentos fallidos (30 s).")
                        else:
                            st.error("Correo o contraseña incorrectos.")
                        st.session_state["show_login_modal"] = True

    with tab_registro:
        st.markdown("#### Crea una cuenta gratuita")
        st.caption("Guarda tus fragancias favoritas y configura alertas de baja de precio en la nube.")
        with st.form("form_reg_user", clear_on_submit=False):
            reg_nombre = st.text_input(
                "Nombre o alias",
                key="reg_nombre_input",
                placeholder="Juan Pérez",
                max_chars=80,
            )
            reg_email = st.text_input(
                "Correo Electrónico",
                key="reg_email_input",
                placeholder="usuario@correo.cl",
                max_chars=120,
            )
            reg_pass1 = st.text_input(
                "Contraseña (mínimo 8 caracteres)",
                type="password",
                key="reg_pass1_input",
                placeholder="••••••••",
            )
            reg_pass2 = st.text_input(
                "Confirmar Contraseña",
                type="password",
                key="reg_pass2_input",
                placeholder="••••••••",
            )
            btn_reg = st.form_submit_button("Crear mi cuenta", use_container_width=True)

            if btn_reg:
                nombre_clean = (reg_nombre or "").strip()
                email_clean = (reg_email or "").strip().lower()
                if not nombre_clean or not email_clean or not reg_pass1:
                    st.error("Todos los campos son obligatorios.")
                    st.session_state["show_login_modal"] = True
                elif not EMAIL_REGEX.match(email_clean):
                    st.error("Ingresa un correo electrónico válido.")
                    st.session_state["show_login_modal"] = True
                elif reg_pass1 != reg_pass2:
                    st.error("Las contraseñas no coinciden.")
                    st.session_state["show_login_modal"] = True
                elif len(reg_pass1) < 8:
                    st.warning("Por seguridad, la contraseña debe tener al menos 8 caracteres.")
                    st.session_state["show_login_modal"] = True
                else:
                    exito, msg = crear_usuario(nombre_clean, email_clean, reg_pass1)
                    if exito:
                        ok_login, u_data = verificar_usuario(email_clean, reg_pass1)
                        if ok_login and u_data:
                            hidratar_sesion_usuario(u_data)
                            st.session_state["show_login_modal"] = False
                            st.rerun()
                        else:
                            st.success("¡Cuenta creada con éxito! Ya puedes iniciar sesión.")
                            st.session_state["show_login_modal"] = True
                    else:
                        st.error(msg)
                        st.session_state["show_login_modal"] = True

    st.markdown(
        f"<hr style='margin: 14px 0; border: none; border-bottom: 1px solid {btn_border};'>",
        unsafe_allow_html=True,
    )
    if st.button("Cerrar Ventana", key="btn_close_auth_modal", use_container_width=True):
        st.session_state["show_login_modal"] = False
        st.session_state["show_visual_modal"] = False
        st.rerun()
