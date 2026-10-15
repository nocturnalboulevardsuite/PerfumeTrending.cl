import streamlit as st
import sys
import os
import random

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

try:
    from backend.database import (
        obtener_tiendas,
        crear_usuario,
        verificar_usuario
    )
except ImportError:
    from backend.database import obtener_tiendas
    crear_usuario = None
    verificar_usuario = None

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(
    page_title="PerfumeTrending — Verificación de Confianza",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# HELPER: Limpia espacios/indentaciones iniciales para evitar que Streamlit Markdown convierta HTML en código
def clean_html(html_str: str) -> str:
    return "\n".join(line.strip() for line in html_str.splitlines())

# 2. GESTIÓN DEL TEMA Y ESTADO DE SESIÓN
if "theme" not in st.session_state:
    st.session_state.theme = "dark"

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_info' not in st.session_state:
    st.session_state['user_info'] = None
if 'show_login_modal' not in st.session_state:
    st.session_state['show_login_modal'] = False

# ESTADOS PARA INICIO POR CÓDIGO (OTP)
if 'otp_code_sent' not in st.session_state:
    st.session_state['otp_code_sent'] = False
if 'otp_contact' not in st.session_state:
    st.session_state['otp_contact'] = ""
if 'otp_secret' not in st.session_state:
    st.session_state['otp_secret'] = ""

def toggle_theme():
    st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"

# MODAL FLOTANTE DE INICIO DE SESIÓN Y REGISTRO
@st.dialog("Acceso a PerfumeTrending")
def modal_autenticacion():
    tab_codigo, tab_login, tab_registro = st.tabs(["Inicio por Código", "Iniciar Sesión", "Registrarse"])
    
    # OPCIÓN PREDETERMINADA: INICIO POR CÓDIGO
    with tab_codigo:
        st.markdown("#### Ingresa con tu Correo o Teléfono")
        
        if not st.session_state['otp_code_sent']:
            with st.form("form_send_otp", clear_on_submit=False):
                contact_input = st.text_input("Correo electrónico o número de teléfono", key="otp_contact_input", placeholder="ejemplo@correo.cl o +56912345678")
                btn_send = st.form_submit_button("Enviar código de verificación", use_container_width=True)
                
                if btn_send:
                    if not contact_input.strip():
                        st.error("Por favor ingresa un correo electrónico o teléfono válido.")
                    else:
                        code = str(random.randint(100000, 999999))
                        st.session_state['otp_code_sent'] = True
                        st.session_state['otp_contact'] = contact_input.strip()
                        st.session_state['otp_secret'] = code
                        st.rerun()
        else:
            st.info(f"Un código de verificación ha sido enviado a **{st.session_state['otp_contact']}**")
            st.caption(f"*(Código de prueba rápido: **{st.session_state['otp_secret']}**)*")
            
            with st.form("form_verify_otp", clear_on_submit=False):
                input_code = st.text_input("Ingresa el código de 6 dígitos", key="otp_code_input", placeholder="123456", max_chars=6)
                btn_verify = st.form_submit_button("Verificar e Ingresar", use_container_width=True)
                
                if btn_verify:
                    if input_code.strip() == st.session_state['otp_secret']:
                        contact_str = st.session_state['otp_contact']
                        
                        st.session_state['logged_in'] = True
                        st.session_state['user_info'] = {
                            'nombre': contact_str.split('@')[0] if '@' in contact_str else contact_str,
                            'email': contact_str if '@' in contact_str else f"{contact_str}@usuario.cl",
                            'telefono': contact_str if '@' not in contact_str else '+56 9 1234 5678'
                        }
                        
                        # Resetear estados de login y cerrar modal
                        st.session_state['otp_code_sent'] = False
                        st.session_state['otp_contact'] = ""
                        st.session_state['otp_secret'] = ""
                        st.session_state['show_login_modal'] = False
                        st.rerun()
                    else:
                        st.error("Código incorrecto. Revisa e intenta nuevamente.")
                        
            if st.button("Cambiar correo/teléfono", key="btn_reset_otp", use_container_width=True):
                st.session_state['otp_code_sent'] = False
                st.session_state['otp_contact'] = ""
                st.session_state['otp_secret'] = ""
                st.rerun()

    # OPCIÓN 2: CON TRADICIONAL CORREO / CONTRASEÑA
    with tab_login:
        st.markdown("#### Ingresa a tu cuenta")
        with st.form("form_login_pass", clear_on_submit=False):
            login_email = st.text_input("Correo Electrónico", key="login_email_input", placeholder="usuario@correo.cl")
            login_pass = st.text_input("Contraseña", type="password", key="login_pass_input", placeholder="••••••••")
            btn_login = st.form_submit_button("Ingresar a la plataforma", use_container_width=True)
            
            if btn_login:
                if not login_email or not login_pass:
                    st.error("Por favor ingresa tu correo y contraseña.")
                elif verificar_usuario:
                    exito, usuario_data = verificar_usuario(login_email, login_pass)
                    if exito:
                        st.session_state['logged_in'] = True
                        st.session_state['user_info'] = usuario_data
                        st.session_state['show_login_modal'] = False
                        st.rerun()
                    else:
                        st.error("Correo o contraseña incorrectos.")
                else:
                    st.info("Función de backend en proceso de actualización.")

    # OPCIÓN 3: REGISTRO NUEVO USUARIO
    with tab_registro:
        st.markdown("#### Crea una cuenta nueva")
        with st.form("form_reg_user", clear_on_submit=False):
            reg_nombre = st.text_input("Nombre completo", key="reg_nombre_input", placeholder="Juan Pérez")
            reg_email = st.text_input("Correo Electrónico", key="reg_email_input", placeholder="usuario@correo.cl")
            reg_pass1 = st.text_input("Contraseña", type="password", key="reg_pass1_input", placeholder="••••••••")
            reg_pass2 = st.text_input("Confirmar Contraseña", type="password", key="reg_pass2_input", placeholder="••••••••")
            btn_reg = st.form_submit_button("Crear mi cuenta", use_container_width=True)
            
            if btn_reg:
                if not reg_nombre or not reg_email or not reg_pass1:
                    st.error("Todos los campos son obligatorios.")
                elif reg_pass1 != reg_pass2:
                    st.error("Las contraseñas no coinciden.")
                elif len(reg_pass1) < 6:
                    st.warning("La contraseña debe tener al menos 6 caracteres.")
                elif crear_usuario:
                    exito, msg = crear_usuario(reg_nombre, reg_email, reg_pass1)
                    if exito:
                        st.success("¡Cuenta creada con éxito! Ya puedes iniciar sesión.")
                    else:
                        st.error(msg)
                else:
                    st.info("Función de backend en proceso de actualización.")

is_dark = st.session_state.theme == "dark"

# 3. PALETA DE COLORES Y SVGS
bg_color = "#0c0e12" if is_dark else "#f8f9fa"
card_bg = "#14171d" if is_dark else "#ffffff"
border_color = "#232730" if is_dark else "#e2e8f0"
text_color = "#f3f4f6" if is_dark else "#0f172a"
subtext_color = "#8e95a5" if is_dark else "#64748b"

btn_bg = "#181c24" if is_dark else "#ffffff"
btn_text = "#ffffff" if is_dark else "#18181b"
btn_border = "#2a2e39" if is_dark else "#d1d5db"

input_bg = "#14171d" if is_dark else "#ffffff"
input_text = "#f0f0f0" if is_dark else "#18181b"
input_border = "#2a2e39" if is_dark else "#d1d5db"

# Configuración del Switch
bottle_left_pos = "42px" if is_dark else "-2px"
static_icon_pos = "12px center" if is_dark else "calc(100% - 12px) center"

static_icon_svg = (
    "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23ffffff' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><circle cx='12' cy='12' r='4'/><line x1='12' y1='1' x2='12' y2='3'/><line x1='12' y1='21' x2='12' y2='23'/><line x1='4.22' y1='4.22' x2='5.64' y2='5.64'/><line x1='18.36' y1='18.36' x2='19.78' y2='19.78'/><line x1='1' y1='12' x2='3' y2='12'/><line x1='21' y1='12' x2='23' y2='12'/><line x1='4.22' y1='19.78' x2='5.64' y2='18.36'/><line x1='18.36' y1='5.64' x2='19.78' y2='4.22'/></svg>"
    if is_dark else
    "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23ffffff' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M21 12.79A9 9 0 0 1 11.21 3 7 7 0 0 0 21 12.79z'/></svg>"
)

bottle_svg = (
    "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 50 58'><rect x='18' y='2' width='14' height='7' rx='2' fill='%23ffffff' stroke='%23111111' stroke-width='2.5'/><rect x='21' y='9' width='8' height='5' fill='%23ffffff' stroke='%23111111' stroke-width='2.5'/><circle cx='25' cy='34' r='19' fill='%23ffffff' stroke='%23111111' stroke-width='2.5'/><path d='M21 28a8 8 0 0 0 9 10.5 8.5 8.5 0 0 1-9-10.5z' fill='none' stroke='%23111111' stroke-width='2.2' stroke-linecap='round' stroke-linejoin='round'/></svg>"
    if is_dark else
    "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 50 58'><rect x='18' y='2' width='14' height='7' rx='2' fill='%23ffffff' stroke='%23111111' stroke-width='2.5'/><rect x='21' y='9' width='8' height='5' fill='%23ffffff' stroke='%23111111' stroke-width='2.5'/><circle cx='25' cy='34' r='19' fill='%23ffffff' stroke='%23111111' stroke-width='2.5'/><circle cx='25' cy='34' r='5' fill='none' stroke='%23111111' stroke-width='2'/><line x1='25' y1='23' x2='25' y2='26' stroke='%23111111' stroke-width='2' stroke-linecap='round'/><line x1='25' y1='42' x2='25' y2='45' stroke='%23111111' stroke-width='2' stroke-linecap='round'/><line x1='14' y1='34' x2='17' y2='34' stroke='%23111111' stroke-width='2' stroke-linecap='round'/><line x1='33' y1='34' x2='36' y2='34' stroke='%23111111' stroke-width='2' stroke-linecap='round'/><line x1='17' y1='26' x2='19' y2='28' stroke='%23111111' stroke-width='2' stroke-linecap='round'/><line x1='31' y1='40' x2='33' y2='42' stroke='%23111111' stroke-width='2' stroke-linecap='round'/><line x1='17' y1='42' x2='19' y2='40' stroke='%23111111' stroke-width='2' stroke-linecap='round'/><line x1='31' y1='28' x2='33' y2='26' stroke='%23111111' stroke-width='2' stroke-linecap='round'/></svg>"
)

user_icon_svg = f"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23{btn_text[1:]}' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2'/><circle cx='12' cy='7' r='4'/></svg>"
settings_icon_svg = f"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23{btn_text[1:]}' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.38a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z'/><circle cx='12' cy='12' r='3'/></svg>"
logout_icon_svg = f"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23{btn_text[1:]}' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4'/><polyline points='16 17 21 12 16 7'/><line x1='21' y1='12' x2='9' y2='12'/></svg>"

# ICONOS VECTORIALES DE ALTA PRECISIÓN (ESTILO LINEAR / STRIPE / LUCIDE)
trend_red_svg = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23d83737' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><polyline points='23 6 13.5 15.5 8.5 10.5 1 18'/><polyline points='17 6 23 6 23 12'/></svg>"
shield_red_svg = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23d83737' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z'/><polyline points='9 12 11 14 15 10'/></svg>"
tag_red_svg = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23d83737' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z'/><circle cx='7' cy='7' r='1.5' fill='%23d83737'/></svg>"
home_red_svg = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23d83737' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z'/><polyline points='9 22 9 12 15 12 15 22'/></svg>"
flame_red_svg = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23d83737' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z'/></svg>"
logo_color_encoded = "%238c7b6d"
text_color_encoded = "%23ffffff" if is_dark else "%230f172a"
logo_svg_data = f"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 36 36' fill='none' stroke-linecap='round' stroke-linejoin='round'><path d='M 6.8 21 L 29.2 21 C 30 25 27 32 18 32 C 9 32 6 25 6.8 21 Z' fill='{logo_color_encoded}' /><line x1='6.8' y1='21' x2='29.2' y2='21' stroke='{text_color_encoded}' stroke-width='1.5' /><line x1='18' y1='10' x2='18' y2='30' stroke='{text_color_encoded}' stroke-width='1' /><path d='M 18 32 C 9 32 5 24 7.5 17 C 9 12 13 10 15 10 L 21 10 C 23 10 27 12 28.5 17 C 31 24 27 32 18 32 Z' stroke='{text_color_encoded}' stroke-width='2' /><rect x='15' y='7' width='6' height='3' stroke='{text_color_encoded}' stroke-width='1.5' /><rect x='13' y='3' width='10' height='4' rx='1' stroke='{text_color_encoded}' stroke-width='1.5' /><rect x='16' y='0' width='4' height='3' rx='1' fill='{logo_color_encoded}' stroke='{text_color_encoded}' stroke-width='1' /></svg>"

# 4. ESTILOS CSS CON TIPOGRAFÍA ELEGANTE Y EDITORIAL
css_styles = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,500;0,600;0,700;1,400&family=Inter:wght@300;400;500;600;700&display=swap');

/* CHIPS DE ACCESO RÁPIDO Y PAGE LINKS */
a[data-testid="stPageLink-NavLink"] {{
    background-color: {card_bg} !important;
    border: 1px solid {border_color} !important;
    border-radius: 20px !important;
    padding: 0.45rem 1rem !important;
    box-shadow: none !important;
    width: 100% !important;
    min-height: 0px !important;
    height: auto !important;
    filter: none !important;
    text-decoration: none !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    box-sizing: border-box !important;
}}

a[data-testid="stPageLink-NavLink"] p,
a[data-testid="stPageLink-NavLink"] span {{
    font-size: 0.85rem !important;
    font-weight: 600 !important;
    color: {text_color} !important;
    letter-spacing: 0.2px;
    white-space: nowrap !important;
    text-overflow: clip !important;
    overflow: visible !important;
    margin: 0 !important;
}}

/* DIBUJOS ILUSTRADOS VECTORIALES EN ROJO PARA LOS BOTONES */
a[data-testid="stPageLink-NavLink"][href*="trendhype"],
a[data-testid="stPageLink-NavLink"][href*="trustpage"],
a[data-testid="stPageLink-NavLink"][href*="compararprecios"],
a[data-testid="stPageLink-NavLink"][href$="app.py"],
a[data-testid="stPageLink-NavLink"][href="/"] {{
    position: relative !important;
    padding-left: 2.7rem !important;
    padding-right: 1.1rem !important;
    overflow: hidden !important;
}}

a[data-testid="stPageLink-NavLink"][href*="trendhype"]::before {{
    content: '' !important;
    position: absolute !important;
    left: 14px !important;
    top: 50% !important;
    transform: translateY(-50%) !important;
    width: 17px !important;
    height: 17px !important;
    background-image: url("{trend_red_svg}") !important;
    background-repeat: no-repeat !important;
    background-size: contain !important;
    background-position: center !important;
    z-index: 1 !important;
}}

a[data-testid="stPageLink-NavLink"][href*="trustpage"]::before {{
    content: '' !important;
    position: absolute !important;
    left: 14px !important;
    top: 50% !important;
    transform: translateY(-50%) !important;
    width: 17px !important;
    height: 17px !important;
    background-image: url("{shield_red_svg}") !important;
    background-repeat: no-repeat !important;
    background-size: contain !important;
    background-position: center !important;
    z-index: 1 !important;
}}

a[data-testid="stPageLink-NavLink"][href*="compararprecios"]::before {{
    content: '' !important;
    position: absolute !important;
    left: 14px !important;
    top: 50% !important;
    transform: translateY(-50%) !important;
    width: 17px !important;
    height: 17px !important;
    background-image: url("{tag_red_svg}") !important;
    background-repeat: no-repeat !important;
    background-size: contain !important;
    background-position: center !important;
    z-index: 1 !important;
}}

a[data-testid="stPageLink-NavLink"][href$="app.py"]::before,
a[data-testid="stPageLink-NavLink"][href="/"]::before {{
    content: '' !important;
    position: absolute !important;
    left: 14px !important;
    top: 50% !important;
    transform: translateY(-50%) !important;
    width: 17px !important;
    height: 17px !important;
    background-image: url("{home_red_svg}") !important;
    background-repeat: no-repeat !important;
    background-size: contain !important;
    background-position: center !important;
    z-index: 1 !important;
}}

html, body, [class*="css"], .stApp {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
    background-color: {bg_color} !important;
    color: {text_color} !important;
}}

header[data-testid="stHeader"] {{ display: none !important; }}

.block-container {{ 
    padding-top: 1.2rem !important; 
    padding-bottom: 2rem !important; 
    max-width: 1200px !important;
}}

/* BOTÓN DE INGRESO Y PERFIL */
.st-key-login_btn, .st-key-theme_toggle {{
    display: flex !important;
    align-items: center !important;
    height: 100% !important;
}}

.st-key-login_btn button {{
    background-color: {btn_bg} !important;
    color: {btn_text} !important;
    border: 1px solid {btn_border} !important;
    border-radius: 8px !important;
    height: 44px !important;
    min-height: 44px !important;
    padding: 0 0.8rem 0 2.2rem !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    background-image: url("{user_icon_svg}") !important;
    background-repeat: no-repeat !important;
    background-position: 10px center !important;
    background-size: 18px 18px !important;
    font-size: 0.95rem !important;
    margin: 0 !important;
    white-space: nowrap !important;
}}

.st-key-login_btn button p {{
    font-size: 0.95rem !important;
    line-height: 1 !important;
    margin: 0 !important;
    color: {btn_text} !important;
    font-weight: 600 !important;
    white-space: nowrap !important;
}}

/* ESTILO PARA BOTÓN POPOVER DE PERFIL */
div[data-testid="stPopover"],
div[data-testid="stPopover"] > button,
button[data-testid="stPopoverButton"],
div[data-testid="stPopover"] button {{
    background-color: {btn_bg} !important;
    color: {btn_text} !important;
    border: 1px solid {btn_border} !important;
    border-radius: 8px !important;
    min-height: 44px !important;
    transition: transform 0.22s ease, background-color 0.15s ease !important;
}}

div[data-testid="stPopover"] button p,
div[data-testid="stPopover"] button span,
button[data-testid="stPopoverButton"] p,
button[data-testid="stPopoverButton"] span {{
    color: {btn_text} !important;
    font-weight: 600 !important;
    white-space: nowrap !important;
}}

div[data-testid="stPopoverBody"],
div[data-testid="stPopoverContent"] {{
    background-color: {input_bg} !important;
    border: 1px solid {btn_border} !important;
    border-radius: 8px !important;
    color: {text_color} !important;
}}

/* CONTENEDOR Y BOTÓN POPOVER DE USUARIO CON DIBUJO HTML/SVG */
.user-popover-container div[data-testid="stPopover"],
.user-popover-container div[data-testid="stPopover"] > button,
.user-popover-container button[data-testid="stPopoverButton"] {{
    padding-left: 2.3rem !important;
    background-image: url("{user_icon_svg}") !important;
    background-repeat: no-repeat !important;
    background-position: 12px center !important;
    background-size: 18px 18px !important;
}}

/* BOTÓN CERRAR SESIÓN Y MI PERFIL CON DIBUJOS VECTORIALES HTML/SVG */
.st-key-btn_go_profile button {{
    padding-left: 2.5rem !important;
    background-image: url("{settings_icon_svg}") !important;
    background-repeat: no-repeat !important;
    background-position: 14px center !important;
    background-size: 18px 18px !important;
}}

.st-key-btn_logout button {{
    padding-left: 2.5rem !important;
    background-image: url("{logout_icon_svg}") !important;
    background-repeat: no-repeat !important;
    background-position: 14px center !important;
    background-size: 18px 18px !important;
}}

/* TARJETA DE PRODUCTO MINIMALISTA */
.product-card {{
    background-color: {card_bg};
    border: 1px solid {border_color};
    border-radius: 16px;
    padding: 36px 32px 28px 32px;
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
}}

.product-title {{
    font-family: 'Cormorant Garamond', serif;
    font-size: 1.8rem;
    font-weight: 600;
    letter-spacing: 2px;
    margin: 20px 0 2px 0;
    text-transform: uppercase;
    color: {text_color};
}}

.product-subtitle {{
    font-size: 0.72rem;
    color: {subtext_color};
    font-weight: 500;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    margin-bottom: 28px;
}}

/* NOTAS OLFATIVAS */
.notes-container {{
    width: 100%;
    text-align: left;
    border-top: 1px solid {border_color};
    padding-top: 20px;
}}

.note-item {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 0;
    border-bottom: 1px dashed {border_color};
}}

.note-item:last-child {{
    border-bottom: none;
}}

.note-label {{
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 1.2px;
    color: {subtext_color};
    text-transform: uppercase;
}}

.note-value {{
    font-size: 0.85rem;
    font-weight: 500;
    color: {text_color};
}}

/* TABLA DE COMPARACIÓN */
.trust-table-container {{
    background-color: {card_bg};
    border: 1px solid {border_color};
    border-radius: 16px;
    padding: 12px;
}}

table.trust-table {{
    width: 100%;
    border-collapse: separate;
    border-spacing: 0 8px;
}}

table.trust-table th {{
    padding: 12px 18px;
    font-size: 0.68rem;
    font-weight: 700;
    text-transform: uppercase;
    color: {subtext_color};
    letter-spacing: 1.5px;
    border-bottom: 1px solid {border_color};
    text-align: left;
}}

table.trust-table td {{
    padding: 16px 18px;
    background-color: {bg_color};
    border-top: 1px solid {border_color};
    border-bottom: 1px solid {border_color};
    vertical-align: middle;
}}

table.trust-table tr td:first-child {{
    border-left: 1px solid {border_color};
    border-top-left-radius: 10px;
    border-bottom-left-radius: 10px;
    font-weight: 500;
    font-size: 0.75rem;
    color: {subtext_color};
}}

table.trust-table tr td:last-child {{
    border-right: 1px solid {border_color};
    border-top-right-radius: 10px;
    border-bottom-right-radius: 10px;
    text-align: right;
}}

.store-title {{
    font-weight: 600;
    font-size: 0.85rem;
    letter-spacing: 0.8px;
    text-transform: uppercase;
    color: {text_color};
}}

.price-tag {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    font-size: 1rem;
    font-weight: 600;
    color: {text_color};
}}

/* BADGES DE ESTADO */
.status-badge-safe {{
    display: inline-flex;
    align-items: center;
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
    background: rgba(34, 197, 94, 0.08);
    color: #22c55e;
    border: 1px solid rgba(34, 197, 94, 0.2);
}}

.status-badge-danger {{
    display: inline-flex;
    align-items: center;
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
    background: rgba(239, 68, 68, 0.08);
    color: #ef4444;
    border: 1px solid rgba(239, 68, 68, 0.2);
}}

/* BOTONES ACCIÓN MINIMALISTAS */
.btn-buy-now {{
    background: {text_color};
    color: {bg_color} !important;
    font-weight: 600;
    font-size: 0.7rem;
    letter-spacing: 1px;
    padding: 9px 18px;
    border-radius: 8px;
    text-decoration: none !important;
    display: inline-block;
    text-transform: uppercase;
    transition: opacity 0.2s ease;
}}

.btn-buy-now:hover {{
    opacity: 0.85;
}}

.btn-buy-disabled {{
    background: transparent;
    color: {subtext_color} !important;
    border: 1px solid {border_color};
    font-weight: 600;
    font-size: 0.7rem;
    letter-spacing: 1px;
    padding: 9px 18px;
    border-radius: 8px;
    text-decoration: none !important;
    display: inline-block;
    text-transform: uppercase;
    cursor: not-allowed;
    opacity: 0.6;
}}

/* SWITCH FLOTANTE (IGUAL A APP.PY) */
.st-key-theme_toggle,
.st-key-theme_toggle div[data-testid="stButton"] {{
    background: transparent !important;
    background-color: transparent !important;
    display: flex !important;
    align-items: center !important;
    justify-content: flex-end !important;
}}

.st-key-theme_toggle div[data-testid="stButton"] > button,
.st-key-theme_toggle button,
.st-key-theme_toggle button:hover,
.st-key-theme_toggle button:focus,
.st-key-theme_toggle button:active,
.st-key-theme_toggle button:focus-visible,
div[data-testid="stElementContainer"].st-key-theme_toggle button {{
    background: transparent !important;
    background-color: transparent !important;
    border: none !important;
    box-shadow: none !important;
    outline: none !important;
    padding: 0 !important;
    width: 82px !important;
    height: 48px !important;
    min-height: 48px !important;
    position: relative !important;
    cursor: pointer !important;
    overflow: visible !important;
    margin-left: auto !important;
    margin-right: 0 !important;
    display: block !important;
    transform: none !important;
}}

.st-key-theme_toggle button * {{ display: none !important; }}

.st-key-theme_toggle button::before {{
    content: '' !important;
    position: absolute !important;
    top: 7px !important; left: 0 !important;
    width: 80px !important; height: 36px !important;
    background-color: #2b2c34 !important;
    border: 2px solid #1a1b20 !important;
    border-radius: 20px !important;
    box-shadow: inset 0 2px 5px rgba(0,0,0,0.4) !important;
    box-sizing: border-box !important;
    background-image: url("{static_icon_svg}") !important;
    background-repeat: no-repeat !important;
    background-position: {static_icon_pos} !important;
    background-size: 18px 18px !important;
    transition: all 0.3s ease !important;
}}

.st-key-theme_toggle button::after {{
    content: '' !important;
    position: absolute !important;
    top: -1px !important;
    left: {bottle_left_pos} !important;
    width: 40px !important; height: 46px !important;
    background-image: url("{bottle_svg}") !important;
    background-repeat: no-repeat !important;
    background-size: contain !important;
    transition: left 0.35s cubic-bezier(0.34, 1.56, 0.64, 1) !important;
    filter: drop-shadow(2px 3px 4px rgba(0,0,0,0.3)) !important;
    z-index: 2 !important;
}}

/* BRAND LOGO INTERACTIVO NATIVO */
.st-key-btn_logo_home,
.st-key-btn_logo_home > div {{
    display: inline-block !important;
    width: fit-content !important;
}}
.st-key-btn_logo_home button {{
    background: transparent !important;
    background-color: transparent !important;
    border: none !important;
    box-shadow: none !important;
    outline: none !important;
    padding: 0 0 0 46px !important;
    margin: 0 !important;
    height: 44px !important;
    min-height: 44px !important;
    display: inline-flex !important;
    align-items: center !important;
    cursor: pointer !important;
    position: relative !important;
    transform: none !important;
    background-image: url("{logo_svg_data}") !important;
    background-repeat: no-repeat !important;
    background-position: left center !important;
    background-size: 34px 34px !important;
    transition: transform 0.22s cubic-bezier(0.34, 1.56, 0.64, 1) !important;
}}
.st-key-btn_logo_home button:hover {{
    background: transparent !important;
    background-color: transparent !important;
    border: none !important;
    box-shadow: none !important;
    outline: none !important;
    background-image: url("{logo_svg_data}") !important;
    background-repeat: no-repeat !important;
    background-position: left center !important;
    background-size: 34px 34px !important;
    transform: scale(1.03) !important;
}}
.st-key-btn_logo_home button p {{
    font-size: 1.5rem !important;
    letter-spacing: 0.3px !important;
    color: {text_color} !important;
    font-weight: 300 !important;
    margin: 0 !important;
    line-height: 1 !important;
    display: inline !important;
}}
.st-key-btn_logo_home button p strong {{
    font-weight: 700 !important;
    color: {text_color} !important;
}}

/* CHIP REMATES */
.st-key-chip_remates button {{
    background-color: {card_bg} !important;
    border: 1px solid {border_color} !important;
    border-radius: 20px !important;
    padding: 0.45rem 1rem 0.45rem 2.7rem !important;
    box-shadow: none !important;
    width: 100% !important;
    min-height: 0px !important;
    height: auto !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    box-sizing: border-box !important;
    font-size: 0.85rem !important;
    font-weight: 600 !important;
    color: {text_color} !important;
    letter-spacing: 0.2px;
    white-space: nowrap !important;
    cursor: pointer !important;
    position: relative !important;
    transition: transform 0.22s cubic-bezier(0.34, 1.56, 0.64, 1) !important;
}}
.st-key-chip_remates button:hover {{
    transform: scale(1.04) !important;
}}
.st-key-chip_remates button::before {{
    content: '' !important;
    position: absolute !important;
    left: 14px !important;
    top: 50% !important;
    transform: translateY(-50%) !important;
    width: 17px !important;
    height: 17px !important;
    background-image: url("{flame_red_svg}") !important;
    background-repeat: no-repeat !important;
    background-size: contain !important;
    background-position: center !important;
    z-index: 1 !important;
}}
</style>
"""
st.markdown(clean_html(css_styles), unsafe_allow_html=True)

# 5. HEADER (LOGO + INICIO DE SESIÓN DINÁMICO + SWITCH COPIADO EXACTO DE APP.PY)
if st.session_state['logged_in']:
    col_logo, col_espacio, col_actions = st.columns([4.0, 0.5, 4.5], vertical_alignment="center")
    btn_col1, btn_col2 = col_actions.columns([3.5, 1.0], vertical_alignment="center")
else:
    col_logo, col_espacio, col_actions = st.columns([5.5, 0.8, 2.7], vertical_alignment="center")
    btn_col1, btn_col2 = col_actions.columns([1.8, 1.0], vertical_alignment="center")

with col_logo:
    st.button("Perfume**Trending**", key="btn_logo_home", on_click=lambda: st.switch_page("app.py"))

with btn_col1:
    if st.session_state['logged_in']:
        user_display = st.session_state['user_info'].get('nombre') or st.session_state['user_info'].get('email', 'Usuario')
        st.markdown('<div class="user-popover-container">', unsafe_allow_html=True)
        with st.popover(f"{user_display}", use_container_width=True):
            st.write(f"**Conectado como:**")
            st.write(st.session_state['user_info'].get('email', ''))
            st.markdown("<div style='margin-top: 8px;'></div>", unsafe_allow_html=True)
            
            # ACOPLE DIRECTO A LA PÁGINA DE PERFIL CON DIBUJO VECTORIAL SVG
            if st.button("Mi Perfil y Alertas", key="btn_go_profile", use_container_width=True):
                st.switch_page("pages/perfil.py")
                
            if st.button("Cerrar Sesión", key="btn_logout", use_container_width=True):
                st.session_state['logged_in'] = False
                st.session_state['user_info'] = None
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        if st.button("Ingresar", key="login_btn", use_container_width=True):
            st.session_state['show_login_modal'] = True

with btn_col2:
    st.button(" ", key="theme_toggle", on_click=toggle_theme)

# MONITOREO Y RENDERIZADO PERSISTENTE DEL MODAL
if st.session_state.get('show_login_modal', False):
    modal_autenticacion()

st.markdown("<div style='margin-top: 14px;'></div>", unsafe_allow_html=True)

# CHIPS DE NAVEGACIÓN RÁPIDA
col_chip_home, col_chip1, col_chip2, col_chip3, col_chip_remates = st.columns([1.6, 1.5, 2.0, 1.7, 1.8], vertical_alignment="center")

with col_chip_home:
    st.page_link("app.py", label="Inicio / Catálogo", use_container_width=True)
with col_chip1:
    st.page_link("pages/trendhype.py", label="Trend Del Hype", use_container_width=True)
with col_chip2:
    st.page_link("pages/trustpage.py", label="Páginas de Confianza", use_container_width=True)
with col_chip3:
    st.page_link("pages/compararprecios.py", label="Comparar Precios", use_container_width=True)
with col_chip_remates:
    if st.button("Remates & Flash", key="chip_remates", use_container_width=True):
        st.session_state["filtro_catalogo_remates"] = True
        st.switch_page("app.py")

st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
col_sub_title, col_sub_back = st.columns([7, 3], vertical_alignment="center")
with col_sub_title:
    st.markdown(f"<div style='color: {subtext_color}; font-size: 0.85rem; font-weight: 600; text-transform: uppercase; letter-spacing: 1px;'>AUDITORÍA DE TIENDAS Y SEGURIDAD</div>", unsafe_allow_html=True)
with col_sub_back:
    st.page_link("app.py", label="← Volver al Catálogo")

st.markdown(f"<hr style='border: none; border-top: 1px solid {border_color}; margin: 16px 0 24px 0;' />", unsafe_allow_html=True)

# 6. ESTRUCTURA PRINCIPAL
left_col, right_col = st.columns([1, 1.4], gap="large")

# --- COLUMNA IZQUIERDA: TARJETA DE PRODUCTO MINIMALISTA ---
with left_col:
    bottle_sketch_svg = f"""
    <svg viewBox="0 0 200 240" fill="none" xmlns="http://www.w3.org/2000/svg" style="width: 100%; height: auto; max-width: 160px;">
        <path d="M70 20 L130 20 L145 35 L145 55 L130 70 L70 70 L55 55 L55 35 Z" stroke="{text_color}" stroke-width="1.8" fill="{card_bg}"/>
        <rect x="75" y="70" width="50" height="15" stroke="{text_color}" stroke-width="1.2" fill="{card_bg}"/>
        <path d="M40 85 L160 85 L175 110 L175 210 L160 225 L40 225 L25 210 L25 110 Z" stroke="{text_color}" stroke-width="1.8" fill="{card_bg}"/>
        <rect x="55" y="115" width="90" height="65" stroke="{border_color}" stroke-width="1" fill="{bg_color}"/>
        <text x="100" y="132" font-size="5.5" font-weight="600" fill="{subtext_color}" text-anchor="middle" letter-spacing="1">SKETCHED SCENTS</text>
        <text x="100" y="150" font-size="9.5" font-weight="700" fill="{text_color}" text-anchor="middle" letter-spacing="1.5">MIDNIGHT</text>
        <text x="100" y="163" font-size="9.5" font-weight="700" fill="{text_color}" text-anchor="middle" letter-spacing="1.5">OUD</text>
        <text x="100" y="174" font-size="5" fill="{subtext_color}" text-anchor="middle">EAU DE PARFUM</text>
    </svg>
    """

    card_left_html = f"""
    <div class="product-card">
        <div style="width: 100%; display: flex; justify-content: center; margin-bottom: 12px;">
            {bottle_sketch_svg}
        </div>
        <div class="product-title">MIDNIGHT OUD</div>
        <div class="product-subtitle">EAU DE PARFUM — 50 ML / 1.7 OZ</div>
        
        <div class="notes-container">
            <div class="note-item">
                <span class="note-label">NOTA DE SALIDA</span>
                <span class="note-value">Madera de Oud Natural</span>
            </div>
            <div class="note-item">
                <span class="note-label">NOTA DE CORAZÓN</span>
                <span class="note-value">Rosa de Bulgaria</span>
            </div>
            <div class="note-item">
                <span class="note-label">NOTA DE FONDO</span>
                <span class="note-value">Ámbar Ahumado</span>
            </div>
        </div>
    </div>
    """
    st.markdown(clean_html(card_left_html), unsafe_allow_html=True)

# --- COLUMNA DERECHA: TABLA DE VERIFICACIÓN EN ESPAÑOL ---
with right_col:
    tiendas_auditadas = obtener_tiendas()
    
    filas_html = []
    for idx, t in enumerate(tiendas_auditadas, 1):
        num_str = f"{idx:02d}"
        score = t.get('trust_score', 95)
        badge_status = '<span class="status-badge-safe">VERIFICADO</span>' if score >= 85 else '<span class="status-badge-danger">AUDITORÍA</span>'
        accion_html = f'<a href="{t.get("url_base", "#")}" target="_blank" rel="noopener noreferrer" class="btn-buy-now">VISITAR</a>'
        
        fila = f"""
        <tr>
            <td>{num_str}</td>
            <td>
                <div class="store-title">{t['nombre'].upper()}</div>
                <div style="font-size: 0.65rem; color: {subtext_color};">{t.get('badge', 'Comercio Oficial')} &bull; RUT: {t.get('rut', 'Verificado')}</div>
            </td>
            <td><span class="price-tag">{score}/100</span></td>
            <td>{badge_status}</td>
            <td>{accion_html}</td>
        </tr>
        """
        filas_html.append(fila)

    # Fila de ejemplo de comercio de alto riesgo no verificado para alertar a compradores
    num_alerta = f"{len(tiendas_auditadas) + 1:02d}"
    fila_riesgo = f"""
    <tr>
        <td>{num_alerta}</td>
        <td>
            <div class="store-title">VENDEDOR NO AUDITADO</div>
            <div style="font-size: 0.65rem; color: #ef4444;">Sin RUT tributario ni boleta legal</div>
        </td>
        <td><span class="price-tag" style="color: #ef4444;">38/100</span></td>
        <td><span class="status-badge-danger">ALTO RIESGO</span></td>
        <td><span class="btn-buy-disabled">BLOQUEADO</span></td>
    </tr>
    """
    filas_html.append(fila_riesgo)

    table_html = f"""
    <div class="trust-table-container">
        <table class="trust-table">
            <thead>
                <tr>
                    <th style="width: 8%;">#</th>
                    <th style="width: 36%;">COMERCIO AUDITADO</th>
                    <th style="width: 18%;">CONFIANZA</th>
                    <th style="width: 22%;">ESTADO</th>
                    <th style="width: 16%; text-align: right;">ACCIÓN</th>
                </tr>
            </thead>
            <tbody>
                {''.join(filas_html)}
            </tbody>
        </table>
    </div>
    """
    st.markdown(clean_html(table_html), unsafe_allow_html=True)
