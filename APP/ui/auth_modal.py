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

# Importación de librería estándar o dependencia externa (hashlib)
import hashlib
# Importación de librería estándar o dependencia externa (hmac)
import hmac
# Importación de librería estándar o dependencia externa (html)
import html
# Importación de librería estándar o dependencia externa (re)
import re
# Importación de librería estándar o dependencia externa (secrets)
import secrets
# Importación de librería estándar o dependencia externa (smtplib)
import smtplib
# Importación de librería estándar o dependencia externa (time)
import time
# Importación de componentes (MIMEMultipart) desde el módulo 'email.mime.multipart'
from email.mime.multipart import MIMEMultipart
# Importación de componentes (MIMEText) desde el módulo 'email.mime.text'
from email.mime.text import MIMEText
# Importación de librería estándar o dependencia externa (streamlit)
import streamlit as st

# Bloque try/except para manejo seguro de errores y resiliencia operativa
try:
    # Importación de componentes (crear_usuario, obtener_favoritos_Ids_usuario, obtener_perfil_usuario, verificar_usuario) desde el módulo 'backend.database'
    from backend.database import (
        crear_usuario,
        obtener_favoritos_Ids_usuario,
        obtener_perfil_usuario,
        verificar_usuario,
    )
except ImportError:
    # Importación de componentes (crear_usuario, obtener_favoritos_Ids_usuario, obtener_perfil_usuario, verificar_usuario) desde el módulo 'APP.backend.database'
    from APP.backend.database import (
        crear_usuario,
        obtener_favoritos_Ids_usuario,
        obtener_perfil_usuario,
        verificar_usuario,
    )

# Asignamos 'EMAIL_REGEX' con re.compile('^[A-Za-z0-9._%+\\-]+@[A-Za-z0-...
EMAIL_REGEX = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
# Asignamos 'MAX_LOGIN_ATTEMPTS' con 5
MAX_LOGIN_ATTEMPTS = 5
# Asignamos 'LOCKOUT_SECONDS' con 30.0
LOCKOUT_SECONDS = 30.0
# Asignamos 'OTP_TTL_SECONDS' con 300.0
OTP_TTL_SECONDS = 300.0


# Definición de función '_obtener_credenciales_smtp' sin parámetros externos
def _obtener_credenciales_smtp() -> tuple[str, str]:
    """Lee credenciales SMTP desde `st.secrets` de forma silenciosa y segura."""
    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
        smtp_email = str(st.secrets.get("SMTP_EMAIL", "") or "").strip()
        # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
        smtp_password = str(st.secrets.get("SMTP_PASSWORD", "") or "").strip()
        # Evaluamos la condición lógica (smtp_email and smtp_password and ('@' in smtp_email)) para controlar el flujo
        if smtp_email and smtp_password and "@" in smtp_email:
            # Retornamos el resultado procesado ((smtp_email, smtp_password))
            return smtp_email, smtp_password
    except Exception:
        # Ejecutamos instrucción: pass
        pass
    # Retornamos el resultado procesado (('', ''))
    return "", ""


# Definición de función '_enviar_codigo_otp_smtp' (parámetros: destinatario, codigo)
def _enviar_codigo_otp_smtp(destinatario: str, codigo: str) -> bool:
    """Envía un código OTP de 6 dígitos por SMTP SSL sin exponer jamás el código en interfaz."""
    # Asignamos '(smtp_email, smtp_password)' con _obtener_credenciales_smtp()
    smtp_email, smtp_password = _obtener_credenciales_smtp()
    # Evaluamos la condición lógica (not smtp_email or not smtp_password) para controlar el flujo
    if not smtp_email or not smtp_password:
        # Retornamos el resultado procesado (False)
        return False

    # Asignamos 'codigo_safe' con html.escape(codigo, quote=True)
    codigo_safe = html.escape(codigo, quote=True)
    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Asignamos 'msg' con MIMEMultipart('alternative')
        msg = MIMEMultipart("alternative")
        # Asignamos 'msg['Subject']' con f'{codigo_safe} es tu código de acceso a P...
        msg["Subject"] = f"{codigo_safe} es tu código de acceso a PerfumeTrending"
        # Asignamos 'msg['From']' con f'PerfumeTrending <{smtp_email}>'
        msg["From"] = f"PerfumeTrending <{smtp_email}>"
        # Asignamos 'msg['To']' con destinatario
        msg["To"] = destinatario

        # Asignamos 'html_content' con f'\n <div style="font-family: Arial, sans-...
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
        # Ejecutamos instrucción: msg.attach(MIMEText(html_content, 'html', 'utf-8'))
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        # Gestión automática de contexto y recursos para: smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout...
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as server:
            # Ejecutamos instrucción: server.login(smtp_email, smtp_password)
            server.login(smtp_email, smtp_password)
            # Ejecutamos instrucción: server.sendmail(smtp_email, destinatario, msg.as_str...
            server.sendmail(smtp_email, destinatario, msg.as_string())
        # Retornamos el resultado procesado (True)
        return True
    except Exception:
        # Retornamos el resultado procesado (False)
        return False


# Definición de función '_limpiar_estado_otp' sin parámetros externos
def _limpiar_estado_otp() -> None:
    # Asignamos 'st.session_state['otp_code_sent']' con False
    st.session_state["otp_code_sent"] = False
    # Asignamos 'st.session_state['otp_contact']' con ''
    st.session_state["otp_contact"] = ""
    # Asignamos 'st.session_state['otp_digest']' con ''
    st.session_state["otp_digest"] = ""
    # Asignamos 'st.session_state['otp_salt']' con ''
    st.session_state["otp_salt"] = ""
    # Asignamos 'st.session_state['otp_expires_at']' con 0.0
    st.session_state["otp_expires_at"] = 0.0


# Definición de función '_resolver_usuario_otp_verificado' (parámetros: email_clean)
def _resolver_usuario_otp_verificado(email_clean: str) -> dict:
    """
    Obtiene o aprovisiona el perfil persistente del usuario tras verificar criptográficamente
    la posesión de su casilla de correo vía OTP.
    """
    # Asignamos 'perfil' con obtener_perfil_usuario(email_clean)
    perfil = obtener_perfil_usuario(email_clean)
    # Evaluamos la condición lógica (perfil) para controlar el flujo
    if perfil:
        # Retornamos el resultado procesado (perfil)
        return perfil

    # Asignamos 'nombre_base' con email_clean.split('@')[0].replace('.', ' '...
    nombre_base = email_clean.split("@")[0].replace(".", " ").strip().title() or "Usuario"
    # Asignamos 'pwd_auto' con secrets.token_urlsafe(24)
    pwd_auto = secrets.token_urlsafe(24)
    # Asignamos '(ok_creado, _)' con crear_usuario(nombre_base, email_clean, pw...
    ok_creado, _ = crear_usuario(nombre_base, email_clean, pwd_auto)
    # Evaluamos la condición lógica (ok_creado) para controlar el flujo
    if ok_creado:
        # Asignamos 'perfil_nuevo' con obtener_perfil_usuario(email_clean)
        perfil_nuevo = obtener_perfil_usuario(email_clean)
        # Evaluamos la condición lógica (perfil_nuevo) para controlar el flujo
        if perfil_nuevo:
            # Retornamos el resultado procesado (perfil_nuevo)
            return perfil_nuevo
        # Asignamos '(ok_ver, u_data)' con verificar_usuario(email_clean, pwd_auto)
        ok_ver, u_data = verificar_usuario(email_clean, pwd_auto)
        # Evaluamos la condición lógica (ok_ver and u_data) para controlar el flujo
        if ok_ver and u_data:
            # Retornamos el resultado procesado (u_data)
            return u_data

    # Retornamos el resultado procesado ({'id': email_clean, 'nombre': nombre_base, 'ema...)
    return {
        "id": email_clean,
        "nombre": nombre_base,
        "email": email_clean,
        "telefono": "",
        "ubicacion": "Santiago, Chile",
        "favoritos": obtener_favoritos_Ids_usuario(email_clean, email=email_clean),
    }


# Definición de función 'cerrar_sesion_usuario' sin parámetros externos
def cerrar_sesion_usuario() -> None:
    """Limpia de forma segura los datos de sesión autenticada."""
    # Asignamos 'st.session_state['logged_in']' con False
    st.session_state["logged_in"] = False
    # Asignamos 'st.session_state['user_info']' con None
    st.session_state["user_info"] = None
    # Asignamos 'st.session_state['favoritos']' con []
    st.session_state["favoritos"] = []
    # Asignamos 'st.session_state['show_login_mod...' con False
    st.session_state["show_login_modal"] = False
    # Asignamos 'st.session_state['show_visual_mo...' con False
    st.session_state["show_visual_modal"] = False
    # Ejecutamos instrucción: _limpiar_estado_otp()
    _limpiar_estado_otp()


# Definición de función 'hidratar_sesion_usuario' (parámetros: usuario_data)
def hidratar_sesion_usuario(usuario_data: dict) -> None:
    """Carga el usuario autenticado y sincroniza su lista real de favoritos desde la BD."""
    # Asignamos 'st.session_state['logged_in']' con True
    st.session_state["logged_in"] = True
    # Asignamos 'st.session_state['user_info']' con usuario_data
    st.session_state["user_info"] = usuario_data
    # Asignamos 'st.session_state['login_failed_a...' con 0
    st.session_state["login_failed_attempts"] = 0
    # Asignamos 'st.session_state['login_lockout_...' con 0.0
    st.session_state["login_lockout_until"] = 0.0
    # Ejecutamos instrucción: _limpiar_estado_otp()
    _limpiar_estado_otp()

    # Asignamos 'favs_meta' con usuario_data.get('favoritos')
    favs_meta = usuario_data.get("favoritos")
    # Evaluamos la condición lógica (isinstance(favs_meta, list)) para controlar el flujo
    if isinstance(favs_meta, list):
        # Asignamos 'st.session_state['favoritos']' con [int(x) for x in favs_meta if str(x).isdig...
        st.session_state["favoritos"] = [int(x) for x in favs_meta if str(x).isdigit()]
    else:
        # Asignamos 'uid' con usuario_data.get('id')
        uid = usuario_data.get("id")
        # Asignamos 'st.session_state['favoritos']' con obtener_favoritos_Ids_usuario(uid, email=u...
        st.session_state["favoritos"] = obtener_favoritos_Ids_usuario(uid, email=usuario_data.get("email"))


# Definición de función 'modal_autenticacion' (parámetros: btn_border)
@st.dialog("Acceso a PerfumeTrending")
def modal_autenticacion(btn_border: str = "#2a2e39") -> None:
    """Diálogo único y seguro de Inicio de Sesión, Registro y OTP SMTP verificado."""
    # Asignamos '(smtp_email, smtp_password)' con _obtener_credenciales_smtp()
    smtp_email, smtp_password = _obtener_credenciales_smtp()
    # Asignamos 'smtp_activo' con bool(smtp_email and smtp_password)
    smtp_activo = bool(smtp_email and smtp_password)

    # Evaluamos la condición lógica (smtp_activo) para controlar el flujo
    if smtp_activo:
        # Asignamos '(tab_codigo, tab_login, tab_regi...' con st.tabs(['Código por Correo', 'Iniciar Ses...
        tab_codigo, tab_login, tab_registro = st.tabs(
            ["Código por Correo", "Iniciar Sesión", "Crear Cuenta"]
        )
    else:
        # Asignamos 'tab_codigo' con None
        tab_codigo = None
        # Asignamos '(tab_login, tab_registro)' con st.tabs(['Iniciar Sesión', 'Crear Cuenta'])
        tab_login, tab_registro = st.tabs(["Iniciar Sesión", "Crear Cuenta"])

    # Asignamos 'now' con time.time()
    now = time.time()
    # Asignamos 'lockout_until' con float(st.session_state.get('login_lockout_...
    lockout_until = float(st.session_state.get("login_lockout_until", 0.0) or 0.0)
    # Asignamos 'is_locked' con now < lockout_until
    is_locked = now < lockout_until

    # Evaluamos la condición lógica (tab_codigo is not None) para controlar el flujo
    if tab_codigo is not None:
        # Gestión automática de contexto y recursos para: tab_codigo
        with tab_codigo:
            # Renderizado de componente visual o control interactivo en la interfaz Streamlit
            st.markdown("#### Ingresa con código al correo")
            # Evaluamos la condición lógica (is_locked) para controlar el flujo
            if is_locked:
                # Asignamos 'rem' con int(lockout_until - now) + 1
                rem = int(lockout_until - now) + 1
                # Ejecutamos instrucción: st.warning(f'Demasiados intentos fallidos. Espera {r...
                st.warning(f"Demasiados intentos fallidos. Espera {rem} segundos antes de volver a intentar.")

            # Evaluamos la condición lógica (not st.session_state.get('otp_code_sent', False)) para controlar el flujo
            if not st.session_state.get("otp_code_sent", False):
                # Gestión automática de contexto y recursos para: st.form('form_send_otp', clear_on_submit=False)
                with st.form("form_send_otp", clear_on_submit=False):
                    # Renderizado de componente visual o control interactivo en la interfaz Streamlit
                    contact_input = st.text_input(
                        "Correo electrónico",
                        key="otp_contact_input",
                        placeholder="usuario@correo.cl",
                    )
                    # Asignamos 'btn_send' con st.form_submit_button('Enviar código de ve...
                    btn_send = st.form_submit_button(
                        "Enviar código de verificación",
                        use_container_width=True,
                        disabled=is_locked,
                    )

                    # Evaluamos la condición lógica (btn_send and (not is_locked)) para controlar el flujo
                    if btn_send and not is_locked:
                        # Asignamos 'email_otp' con (contact_input or '').strip().lower()
                        email_otp = (contact_input or "").strip().lower()
                        # Evaluamos la condición lógica (not EMAIL_REGEX.match(email_otp)) para controlar el flujo
                        if not EMAIL_REGEX.match(email_otp):
                            # Ejecutamos instrucción: st.error('Por favor ingresa un correo electrónico vá...
                            st.error("Por favor ingresa un correo electrónico válido.")
                            # Asignamos 'st.session_state['show_login_mod...' con True
                            st.session_state["show_login_modal"] = True
                        else:
                            # Asignamos 'code' con f'{secrets.randbelow(900000) + 100000:06d}'
                            code = f"{secrets.randbelow(900000) + 100000:06d}"
                            # Asignamos 'salt' con secrets.token_hex(16)
                            salt = secrets.token_hex(16)
                            # Asignamos 'digest' con hmac.new(salt.encode('utf-8'), code.encode...
                            digest = hmac.new(
                                salt.encode("utf-8"), code.encode("utf-8"), hashlib.sha256
                            ).hexdigest()

                            # Evaluamos la condición lógica (_enviar_codigo_otp_smtp(email_otp, code)) para controlar el flujo
                            if _enviar_codigo_otp_smtp(email_otp, code):
                                # Asignamos 'st.session_state['otp_code_sent']' con True
                                st.session_state["otp_code_sent"] = True
                                # Asignamos 'st.session_state['otp_contact']' con email_otp
                                st.session_state["otp_contact"] = email_otp
                                # Asignamos 'st.session_state['otp_salt']' con salt
                                st.session_state["otp_salt"] = salt
                                # Asignamos 'st.session_state['otp_digest']' con digest
                                st.session_state["otp_digest"] = digest
                                # Asignamos 'st.session_state['otp_expires_at']' con time.time() + OTP_TTL_SECONDS
                                st.session_state["otp_expires_at"] = time.time() + OTP_TTL_SECONDS
                                # Asignamos 'st.session_state['show_login_mod...' con True
                                st.session_state["show_login_modal"] = True
                                # Ejecutamos instrucción: st.rerun()
                                st.rerun()
                            else:
                                # Ejecutamos instrucción: _limpiar_estado_otp()
                                _limpiar_estado_otp()
                                # Ejecutamos instrucción: st.error("No fue posible enviar el código en este mo...
                                st.error(
                                    "No fue posible enviar el código en este momento. "
                                    "Usa la pestaña 'Iniciar Sesión' con tu contraseña."
                                )
                                # Asignamos 'st.session_state['show_login_mod...' con True
                                st.session_state["show_login_modal"] = True
            else:
                # Asignamos 'email_dest' con st.session_state.get('otp_contact', '')
                email_dest = st.session_state.get("otp_contact", "")
                # Ejecutamos instrucción: st.success(f'Enviamos un código de 6 dígitos a **{em...
                st.success(
                    f"Enviamos un código de 6 dígitos a **{email_dest}**. "
                    "Revisa tu bandeja de entrada o carpeta de spam."
                )
                # Gestión automática de contexto y recursos para: st.form('form_verify_otp', clear_on_submit=False)
                with st.form("form_verify_otp", clear_on_submit=False):
                    # Renderizado de componente visual o control interactivo en la interfaz Streamlit
                    input_code = st.text_input(
                        "Código de 6 dígitos",
                        key="otp_code_input",
                        placeholder="123456",
                        max_chars=6,
                    )
                    # Asignamos 'btn_verify' con st.form_submit_button('Verificar e Ingresa...
                    btn_verify = st.form_submit_button(
                        "Verificar e Ingresar",
                        use_container_width=True,
                        disabled=is_locked,
                    )

                    # Evaluamos la condición lógica (btn_verify and (not is_locked)) para controlar el flujo
                    if btn_verify and not is_locked:
                        # Asignamos 'exp_at' con float(st.session_state.get('otp_expires_at...
                        exp_at = float(st.session_state.get("otp_expires_at", 0.0) or 0.0)
                        # Asignamos 'salt' con str(st.session_state.get('otp_salt', '') o...
                        salt = str(st.session_state.get("otp_salt", "") or "")
                        # Asignamos 'expected_digest' con str(st.session_state.get('otp_digest', '')...
                        expected_digest = str(st.session_state.get("otp_digest", "") or "")
                        # Asignamos 'cand' con (input_code or '').strip()
                        cand = (input_code or "").strip()

                        # Evaluamos la condición lógica (time.time() > exp_at or not salt or (not expected_di...) para controlar el flujo
                        if time.time() > exp_at or not salt or not expected_digest:
                            # Ejecutamos instrucción: _limpiar_estado_otp()
                            _limpiar_estado_otp()
                            # Ejecutamos instrucción: st.error('El código ha expirado. Solicita uno nuevo.')
                            st.error("El código ha expirado. Solicita uno nuevo.")
                            # Asignamos 'st.session_state['show_login_mod...' con True
                            st.session_state["show_login_modal"] = True
                        else:
                            # Asignamos 'cand_digest' con hmac.new(salt.encode('utf-8'), cand.encode...
                            cand_digest = hmac.new(
                                salt.encode("utf-8"), cand.encode("utf-8"), hashlib.sha256
                            ).hexdigest()
                            # Evaluamos la condición lógica (hmac.compare_digest(cand_digest, expected_digest)) para controlar el flujo
                            if hmac.compare_digest(cand_digest, expected_digest):
                                # Asignamos 'u_data' con _resolver_usuario_otp_verificado(email_dest)
                                u_data = _resolver_usuario_otp_verificado(email_dest)
                                # Ejecutamos instrucción: hidratar_sesion_usuario(u_data)
                                hidratar_sesion_usuario(u_data)
                                # Asignamos 'st.session_state['show_login_mod...' con False
                                st.session_state["show_login_modal"] = False
                                # Ejecutamos instrucción: st.rerun()
                                st.rerun()
                            else:
                                # Asignamos 'intentos' con int(st.session_state.get('login_failed_att...
                                intentos = int(st.session_state.get("login_failed_attempts", 0)) + 1
                                # Asignamos 'st.session_state['login_failed_a...' con intentos
                                st.session_state["login_failed_attempts"] = intentos
                                # Evaluamos la condición lógica (intentos >= MAX_LOGIN_ATTEMPTS) para controlar el flujo
                                if intentos >= MAX_LOGIN_ATTEMPTS:
                                    # Asignamos 'st.session_state['login_lockout_...' con time.time() + LOCKOUT_SECONDS
                                    st.session_state["login_lockout_until"] = time.time() + LOCKOUT_SECONDS
                                    # Asignamos 'st.session_state['login_failed_a...' con 0
                                    st.session_state["login_failed_attempts"] = 0
                                    # Ejecutamos instrucción: _limpiar_estado_otp()
                                    _limpiar_estado_otp()
                                    # Ejecutamos instrucción: st.error('Demasiados intentos inválidos. Espera 30 s...
                                    st.error("Demasiados intentos inválidos. Espera 30 s y solicita un nuevo código.")
                                else:
                                    # Ejecutamos instrucción: st.error('Código incorrecto. Revisa e intenta nuevam...
                                    st.error("Código incorrecto. Revisa e intenta nuevamente.")
                                # Asignamos 'st.session_state['show_login_mod...' con True
                                st.session_state["show_login_modal"] = True

                # Evaluamos la condición lógica (st.button('Cambiar correo electrónico', key='btn_res...) para controlar el flujo
                if st.button("Cambiar correo electrónico", key="btn_reset_otp", use_container_width=True):
                    # Ejecutamos instrucción: _limpiar_estado_otp()
                    _limpiar_estado_otp()
                    # Asignamos 'st.session_state['show_login_mod...' con True
                    st.session_state["show_login_modal"] = True
                    # Ejecutamos instrucción: st.rerun()
                    st.rerun()

    # Gestión automática de contexto y recursos para: tab_login
    with tab_login:
        # Renderizado de componente visual o control interactivo en la interfaz Streamlit
        st.markdown("#### Ingresa a tu cuenta")
        # Evaluamos la condición lógica (is_locked) para controlar el flujo
        if is_locked:
            # Asignamos 'rem' con int(lockout_until - now) + 1
            rem = int(lockout_until - now) + 1
            # Ejecutamos instrucción: st.warning(f'Demasiados intentos fallidos. Espera {r...
            st.warning(f"Demasiados intentos fallidos. Espera {rem} segundos antes de volver a intentar.")

        # Gestión automática de contexto y recursos para: st.form('form_login_pass', clear_on_submit=False)
        with st.form("form_login_pass", clear_on_submit=False):
            # Renderizado de componente visual o control interactivo en la interfaz Streamlit
            login_email = st.text_input(
                "Correo Electrónico",
                key="login_email_input",
                placeholder="usuario@correo.cl",
            )
            # Renderizado de componente visual o control interactivo en la interfaz Streamlit
            login_pass = st.text_input(
                "Contraseña",
                type="password",
                key="login_pass_input",
                placeholder="••••••••",
            )
            # Asignamos 'btn_login' con st.form_submit_button('Ingresar a la plata...
            btn_login = st.form_submit_button(
                "Ingresar a la plataforma",
                use_container_width=True,
                disabled=is_locked,
            )

            # Evaluamos la condición lógica (btn_login and (not is_locked)) para controlar el flujo
            if btn_login and not is_locked:
                # Asignamos 'email_clean' con (login_email or '').strip().lower()
                email_clean = (login_email or "").strip().lower()
                # Evaluamos la condición lógica (not email_clean or not login_pass) para controlar el flujo
                if not email_clean or not login_pass:
                    # Ejecutamos instrucción: st.error('Por favor ingresa tu correo y contraseña.')
                    st.error("Por favor ingresa tu correo y contraseña.")
                    # Asignamos 'st.session_state['show_login_mod...' con True
                    st.session_state["show_login_modal"] = True
                # Evaluamos la condición lógica (not EMAIL_REGEX.match(email_clean)) para controlar el flujo
                elif not EMAIL_REGEX.match(email_clean):
                    # Ejecutamos instrucción: st.error('Ingresa un correo electrónico con formato ...
                    st.error("Ingresa un correo electrónico con formato válido.")
                    # Asignamos 'st.session_state['show_login_mod...' con True
                    st.session_state["show_login_modal"] = True
                else:
                    # Asignamos '(exito, usuario_data)' con verificar_usuario(email_clean, login_pass)
                    exito, usuario_data = verificar_usuario(email_clean, login_pass)
                    # Evaluamos la condición lógica (exito and usuario_data) para controlar el flujo
                    if exito and usuario_data:
                        # Ejecutamos instrucción: hidratar_sesion_usuario(usuario_data)
                        hidratar_sesion_usuario(usuario_data)
                        # Asignamos 'st.session_state['show_login_mod...' con False
                        st.session_state["show_login_modal"] = False
                        # Ejecutamos instrucción: st.rerun()
                        st.rerun()
                    else:
                        # Asignamos 'intentos' con int(st.session_state.get('login_failed_att...
                        intentos = int(st.session_state.get("login_failed_attempts", 0)) + 1
                        # Asignamos 'st.session_state['login_failed_a...' con intentos
                        st.session_state["login_failed_attempts"] = intentos
                        # Evaluamos la condición lógica (intentos >= MAX_LOGIN_ATTEMPTS) para controlar el flujo
                        if intentos >= MAX_LOGIN_ATTEMPTS:
                            # Asignamos 'st.session_state['login_lockout_...' con time.time() + LOCKOUT_SECONDS
                            st.session_state["login_lockout_until"] = time.time() + LOCKOUT_SECONDS
                            # Asignamos 'st.session_state['login_failed_a...' con 0
                            st.session_state["login_failed_attempts"] = 0
                            # Ejecutamos instrucción: st.error('Cuenta protegida temporalmente por múltipl...
                            st.error("Cuenta protegida temporalmente por múltiples intentos fallidos (30 s).")
                        else:
                            # Ejecutamos instrucción: st.error('Correo o contraseña incorrectos.')
                            st.error("Correo o contraseña incorrectos.")
                        # Asignamos 'st.session_state['show_login_mod...' con True
                        st.session_state["show_login_modal"] = True

    # Gestión automática de contexto y recursos para: tab_registro
    with tab_registro:
        # Renderizado de componente visual o control interactivo en la interfaz Streamlit
        st.markdown("#### Crea una cuenta gratuita")
        # Ejecutamos instrucción: st.caption('Guarda tus fragancias favoritas y config...
        st.caption("Guarda tus fragancias favoritas y configura alertas de baja de precio en la nube.")
        # Gestión automática de contexto y recursos para: st.form('form_reg_user', clear_on_submit=False)
        with st.form("form_reg_user", clear_on_submit=False):
            # Renderizado de componente visual o control interactivo en la interfaz Streamlit
            reg_nombre = st.text_input(
                "Nombre o alias",
                key="reg_nombre_input",
                placeholder="Juan Pérez",
                max_chars=80,
            )
            # Renderizado de componente visual o control interactivo en la interfaz Streamlit
            reg_email = st.text_input(
                "Correo Electrónico",
                key="reg_email_input",
                placeholder="usuario@correo.cl",
                max_chars=120,
            )
            # Renderizado de componente visual o control interactivo en la interfaz Streamlit
            reg_pass1 = st.text_input(
                "Contraseña (mínimo 8 caracteres)",
                type="password",
                key="reg_pass1_input",
                placeholder="••••••••",
            )
            # Renderizado de componente visual o control interactivo en la interfaz Streamlit
            reg_pass2 = st.text_input(
                "Confirmar Contraseña",
                type="password",
                key="reg_pass2_input",
                placeholder="••••••••",
            )
            # Asignamos 'btn_reg' con st.form_submit_button('Crear mi cuenta', u...
            btn_reg = st.form_submit_button("Crear mi cuenta", use_container_width=True)

            # Evaluamos la condición lógica (btn_reg) para controlar el flujo
            if btn_reg:
                # Asignamos 'nombre_clean' con (reg_nombre or '').strip()
                nombre_clean = (reg_nombre or "").strip()
                # Asignamos 'email_clean' con (reg_email or '').strip().lower()
                email_clean = (reg_email or "").strip().lower()
                # Evaluamos la condición lógica (not nombre_clean or not email_clean or (not reg_pass1)) para controlar el flujo
                if not nombre_clean or not email_clean or not reg_pass1:
                    # Ejecutamos instrucción: st.error('Todos los campos son obligatorios.')
                    st.error("Todos los campos son obligatorios.")
                    # Asignamos 'st.session_state['show_login_mod...' con True
                    st.session_state["show_login_modal"] = True
                # Evaluamos la condición lógica (not EMAIL_REGEX.match(email_clean)) para controlar el flujo
                elif not EMAIL_REGEX.match(email_clean):
                    # Ejecutamos instrucción: st.error('Ingresa un correo electrónico válido.')
                    st.error("Ingresa un correo electrónico válido.")
                    # Asignamos 'st.session_state['show_login_mod...' con True
                    st.session_state["show_login_modal"] = True
                # Evaluamos la condición lógica (reg_pass1 != reg_pass2) para controlar el flujo
                elif reg_pass1 != reg_pass2:
                    # Ejecutamos instrucción: st.error('Las contraseñas no coinciden.')
                    st.error("Las contraseñas no coinciden.")
                    # Asignamos 'st.session_state['show_login_mod...' con True
                    st.session_state["show_login_modal"] = True
                # Evaluamos la condición lógica (len(reg_pass1) < 8) para controlar el flujo
                elif len(reg_pass1) < 8:
                    # Ejecutamos instrucción: st.warning('Por seguridad, la contraseña debe tener ...
                    st.warning("Por seguridad, la contraseña debe tener al menos 8 caracteres.")
                    # Asignamos 'st.session_state['show_login_mod...' con True
                    st.session_state["show_login_modal"] = True
                else:
                    # Asignamos '(exito, msg)' con crear_usuario(nombre_clean, email_clean, r...
                    exito, msg = crear_usuario(nombre_clean, email_clean, reg_pass1)
                    # Evaluamos la condición lógica (exito) para controlar el flujo
                    if exito:
                        # Asignamos '(ok_login, u_data)' con verificar_usuario(email_clean, reg_pass1)
                        ok_login, u_data = verificar_usuario(email_clean, reg_pass1)
                        # Evaluamos la condición lógica (ok_login and u_data) para controlar el flujo
                        if ok_login and u_data:
                            # Ejecutamos instrucción: hidratar_sesion_usuario(u_data)
                            hidratar_sesion_usuario(u_data)
                            # Asignamos 'st.session_state['show_login_mod...' con False
                            st.session_state["show_login_modal"] = False
                            # Ejecutamos instrucción: st.rerun()
                            st.rerun()
                        else:
                            # Ejecutamos instrucción: st.success('¡Cuenta creada con éxito! Ya puedes inic...
                            st.success("¡Cuenta creada con éxito! Ya puedes iniciar sesión.")
                            # Asignamos 'st.session_state['show_login_mod...' con True
                            st.session_state["show_login_modal"] = True
                    else:
                        # Ejecutamos instrucción: st.error(msg)
                        st.error(msg)
                        # Asignamos 'st.session_state['show_login_mod...' con True
                        st.session_state["show_login_modal"] = True

    # Renderizado de componente visual o control interactivo en la interfaz Streamlit
    st.markdown(
        f"<hr style='margin: 14px 0; border: none; border-bottom: 1px solid {btn_border};'>",
        unsafe_allow_html=True,
    )
    # Evaluamos la condición lógica (st.button('Cerrar Ventana', key='btn_close_auth_moda...) para controlar el flujo
    if st.button("Cerrar Ventana", key="btn_close_auth_modal", use_container_width=True):
        # Asignamos 'st.session_state['show_login_mod...' con False
        st.session_state["show_login_modal"] = False
        # Asignamos 'st.session_state['show_visual_mo...' con False
        st.session_state["show_visual_modal"] = False
        # Ejecutamos instrucción: st.rerun()
        st.rerun()
