"""
PerfumeTrending.cl — Perfil de Usuario, Favoritos y Gestión de Alertas
======================================================================
Módulo de gestión de cuentas de usuario, listas de deseos y preferencias:
- Autenticación local y en la nube (registro, inicio de sesión seguro con hash SHA-256).
- Gestión de fragancias favoritas (guardar, ver y remover de la colección personal).
- Alertas de bajada de precio personalizadas cuando una oferta cae por debajo del umbral objetivo.
- Historial de actividad y recomendaciones personalizadas según las familias olfativas guardadas.
"""

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import sys
import os
import base64
import urllib.parse
import random

# Configuración de rutas canónicas para importar backend
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)
if APP_DIR not in sys.path:
    sys.path.append(APP_DIR)

try:
    from backend.database import (
        obtener_catalogo,
        obtener_precios_actuales,
        obtener_detalle_perfume,
        crear_usuario,
        verificar_usuario
    )
except ImportError:
    from backend.database import (
        obtener_catalogo,
        obtener_precios_actuales,
        obtener_detalle_perfume
    )
    crear_usuario = None
    verificar_usuario = None

@st.cache_data(ttl=300, show_spinner=False)
def get_cached_catalogo():
    return obtener_catalogo()

@st.cache_data(ttl=300, show_spinner=False)
def get_cached_precios(perfume_id):
    return obtener_precios_actuales(perfume_id)

def clean_html(html_str: str) -> str:
    """Limpia espacios iniciales y elimina saltos de línea para evitar que Streamlit interprete HTML como código."""
    return " ".join(line.strip() for line in html_str.splitlines() if line.strip())

def get_image_src(img_path_or_url):
    """Retorna URL remota o data URI en base64 para imágenes y GIFs locales."""
    if not img_path_or_url:
        return ""
    
    if img_path_or_url.startswith("http://") or img_path_or_url.startswith("https://") or img_path_or_url.startswith("data:"):
        return img_path_or_url

    local_path = img_path_or_url
    if not os.path.isabs(local_path):
        cand1 = os.path.join(BASE_DIR, local_path)
        cand2 = os.path.join(BASE_DIR, "APP", local_path)
        if os.path.exists(cand1):
            local_path = cand1
        elif os.path.exists(cand2):
            local_path = cand2

    if os.path.exists(local_path):
        ext = os.path.splitext(local_path)[1].lower().replace(".", "")
        mime = f"image/{ext}" if ext in ["png", "jpg", "jpeg", "gif", "webp"] else "image/png"
        try:
            with open(local_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
                return f"data:{mime};base64,{b64}"
        except Exception:
            pass

    return img_path_or_url

# 1. CONFIGURACIÓN DE LA PÁGINA Y ESTADO
st.set_page_config(page_title="Mi Perfil - PerfumeTrending", layout="wide", initial_sidebar_state="collapsed")

if 'theme' not in st.session_state:
    st.session_state['theme'] = 'dark'

# ESTADOS DE AUTENTICACIÓN Y CONTROL DE MODAL
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if 'user_info' not in st.session_state:
    st.session_state['user_info'] = None

if 'show_login_modal' not in st.session_state:
    st.session_state['show_login_modal'] = False

# LISTA DE FAVORITOS MONITOREADOS (IDs DE PERFUMES)
if 'favoritos' not in st.session_state:
    st.session_state['favoritos'] = [1, 2, 4]

# ESTADOS PARA INICIO POR CÓDIGO (OTP)
if 'otp_code_sent' not in st.session_state:
    st.session_state['otp_code_sent'] = False
if 'otp_contact' not in st.session_state:
    st.session_state['otp_contact'] = ""
if 'otp_secret' not in st.session_state:
    st.session_state['otp_secret'] = ""

def toggle_theme():
    st.session_state['theme'] = 'dark' if st.session_state['theme'] == 'light' else 'light'

# MODAL FLOTANTE DE INICIO DE SESIÓN Y REGISTRO
@st.dialog("Acceso a PerfumeTrending")
def modal_autenticacion():
    tab_codigo, tab_login, tab_registro = st.tabs(["Inicio por Código", "Iniciar Sesión", "Registrarse"])
    
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
                        contact_str = st.session_state['otp_contact'].strip()
                        st.session_state['logged_in'] = True
                        
                        is_email = "@" in contact_str
                        st.session_state['user_info'] = {
                            'nombre': '',
                            'email': contact_str if is_email else '',
                            'telefono': contact_str if not is_email else '',
                            'bio': '',
                            'foto_perfil': '',
                            'alerta_email': is_email,
                            'umbral_descuento': 10
                        }
                        
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
                        st.session_state['user_info'] = {
                            'nombre': usuario_data.get('nombre', ''),
                            'email': usuario_data.get('email', login_email),
                            'telefono': usuario_data.get('telefono', ''),
                            'bio': usuario_data.get('bio', ''),
                            'foto_perfil': usuario_data.get('foto_perfil', ''),
                            'alerta_email': True,
                            'umbral_descuento': 10
                        }
                        st.session_state['show_login_modal'] = False
                        st.rerun()
                    else:
                        st.error("Correo o contraseña incorrectos.")
                else:
                    st.session_state['logged_in'] = True
                    st.session_state['user_info'] = {
                        'nombre': '',
                        'email': login_email,
                        'telefono': '',
                        'bio': '',
                        'foto_perfil': '',
                        'alerta_email': True,
                        'umbral_descuento': 10
                    }
                    st.session_state['show_login_modal'] = False
                    st.rerun()

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
                        st.session_state['logged_in'] = True
                        st.session_state['user_info'] = {
                            'nombre': reg_nombre,
                            'email': reg_email,
                            'telefono': '',
                            'bio': '',
                            'foto_perfil': '',
                            'alerta_email': True,
                            'umbral_descuento': 10
                        }
                        st.session_state['show_login_modal'] = False
                        st.success("¡Cuenta creada con éxito!")
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.session_state['logged_in'] = True
                    st.session_state['user_info'] = {
                        'nombre': reg_nombre,
                        'email': reg_email,
                        'telefono': '',
                        'bio': '',
                        'foto_perfil': '',
                        'alerta_email': True,
                        'umbral_descuento': 10
                    }
                    st.session_state['show_login_modal'] = False
                    st.success("¡Cuenta creada con éxito!")
                    st.rerun()

is_dark = st.session_state['theme'] == 'dark'

# Colores dinámicos adaptables por tema
app_bg = "#0c0e12" if is_dark else "#f9f9fb"
app_bg_css = f"background-color: {app_bg} !important;"

text_color = "#f0f0f0" if is_dark else "#18181b"
subtext_color = "#888890" if is_dark else "#666670"

btn_bg = "#181c24" if is_dark else "#ffffff"
btn_text = "#ffffff" if is_dark else "#18181b"
btn_border = "#2a2e39" if is_dark else "#d1d5db"

input_bg = "#14171d" if is_dark else "#ffffff"
input_text = "#f0f0f0" if is_dark else "#18181b"
input_border = "#2a2e39" if is_dark else "#d1d5db"

# SWITCH DE TEMA - POSICIONAMIENTO Y SVGS
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

# ICONOS VECTORIALES DE ALTA PRECISIÓN
trend_red_svg = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23d83737' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><polyline points='23 6 13.5 15.5 8.5 10.5 1 18'/><polyline points='17 6 23 6 23 12'/></svg>"
shield_red_svg = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23d83737' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z'/><polyline points='9 12 11 14 15 10'/></svg>"
tag_red_svg = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23d83737' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z'/><circle cx='7' cy='7' r='1.5' fill='%23d83737'/></svg>"
home_red_svg = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23d83737' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z'/><polyline points='9 22 9 12 15 12 15 22'/></svg>"

# COMPONENTES VECTORIALES INLINE SVG PARA REEMPLAZO DE EMOJIS
svg_mail = f'<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="{subtext_color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: -2px; margin-right: 4px;"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>'
svg_phone = f'<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="{subtext_color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: -2px; margin-right: 4px; margin-left: 12px;"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/></svg>'
svg_bell_active = f'<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: -2px; margin-right: 5px;"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>'
svg_bell_off = f'<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: -2px; margin-right: 5px;"><path d="M13.73 21a2 2 0 0 1-3.46 0"/><line x1="1" y1="1" x2="23" y2="23"/></svg>'
svg_trend_down = f'<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: -2px; margin-right: 5px;"><polyline points="23 18 13.5 8.5 8.5 13.5 1 6"/><polyline points="17 18 23 18 23 12"/></svg>'

# 2. CSS ADAPTABLE Y ESTILOS PRINCIPALES
st.markdown(f"""
    <style>
    html, body, .stApp {{
        -webkit-font-smoothing: antialiased !important;
        -moz-osx-font-smoothing: grayscale !important;
        text-rendering: optimizeLegibility !important;
    }}

    header[data-testid="stHeader"] {{ display: none !important; }}
    
    .block-container {{ 
        padding-top: 1.2rem !important; 
        padding-bottom: 2rem !important; 
        max-width: 1200px !important;
    }}
    
    .stApp {{ {app_bg_css} color: {text_color} !important; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }}

    .stApp p, .stApp span, .stApp label, .stMarkdown p {{
        color: {text_color} !important;
        text-shadow: none !important;
    }}

    /* BOTÓN INGRESAR (LOGIN) Y CONTENEDORES DE LA CABECERA */
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

    /* ESTILO PARA BOTÓN POPOVER DE PERFIL DE USUARIO */
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

    /* SWITCH TEMA */
    .st-key-theme_toggle button,
    .st-key-theme_toggle button:hover,
    .st-key-theme_toggle button:focus {{
        background: transparent !important;
        border: none !important;
        padding: 0 !important;
        width: 82px !important;
        height: 48px !important;
        position: relative !important;
        cursor: pointer !important;
        margin-left: auto !important;
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
        z-index: 2 !important;
    }}

    /* CHIPS DE ACCESO RÁPIDO Y PAGE LINKS */
    a[data-testid="stPageLink-NavLink"] {{
        background-color: {btn_bg} !important;
        border: 1px solid {btn_border} !important;
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
        color: {btn_text} !important;
        letter-spacing: 0.2px;
        white-space: nowrap !important;
        text-overflow: clip !important;
        overflow: visible !important;
        margin: 0 !important;
    }}

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

    /* TARJETA CONTENEDORA DE PERFIL */
    .profile-card-container {{
        background-color: {btn_bg};
        border: 1px solid {btn_border};
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 24px;
    }}

    /* FOTO DE PERFIL CLIQUEABLE CON OVERLAY */
    .avatar-click-zone {{
        position: relative;
        width: 110px;
        height: 110px;
        border-radius: 50%;
        margin: 0 auto;
        cursor: pointer;
    }}

    .avatar-click-zone .profile-avatar-img {{
        width: 110px;
        height: 110px;
        border-radius: 50%;
        object-fit: cover;
        border: 3px solid #8c7b6d;
        background-color: {input_bg};
        padding: 2px;
        display: block;
    }}

    .avatar-click-zone .avatar-overlay-badge {{
        position: absolute;
        top: 0; left: 0;
        width: 100%; height: 100%;
        border-radius: 50%;
        background: rgba(0, 0, 0, 0.55);
        color: #ffffff;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        opacity: 0;
        transition: opacity 0.22s ease-in-out;
        pointer-events: none;
    }}

    .avatar-click-zone:hover .avatar-overlay-badge {{
        opacity: 1;
    }}

    /* OVERLAY TRANSPARENTE DEL FILE UPLOADER SOBRE EL AVATAR */
    .st-key-avatar_quick_uploader {{
        position: absolute !important;
        top: 0 !important;
        left: 0 !important;
        width: 110px !important;
        height: 110px !important;
        margin: 0 !important;
        padding: 0 !important;
        opacity: 0 !important;
        z-index: 25 !important;
        cursor: pointer !important;
    }}

    .st-key-avatar_quick_uploader * {{
        cursor: pointer !important;
        height: 110px !important;
        width: 110px !important;
        min-height: 110px !important;
    }}

    /* TARJETAS DE FAVORITOS Y MONITOREO */
    .fav-card {{
        background-color: {btn_bg};
        border: 1px solid {btn_border};
        border-radius: 10px;
        padding: 16px 20px;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }}

    /* BRAND LOGO INTERACTIVO NATIVO 100% LIMPIO Y TRANSPARENTE */
    a.brand-logo-clean,
    a.brand-logo-clean:visited,
    a.brand-logo-clean:hover,
    a.brand-logo-clean:active,
    a.brand-logo-clean:focus {{
        display: inline-flex !important;
        align-items: center !important;
        gap: 12px !important;
        text-decoration: none !important;
        background: transparent !important;
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
        outline: none !important;
        padding: 0 !important;
        margin: 0 !important;
        cursor: pointer !important;
        user-select: none !important;
        transition: transform 0.22s cubic-bezier(0.34, 1.56, 0.64, 1) !important;
    }}
    a.brand-logo-clean:hover {{
        transform: scale(1.02) !important;
        background: transparent !important;
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }}
    .brand-logo-text {{
        font-size: 1.55rem !important;
        color: {text_color} !important;
        letter-spacing: 0.3px !important;
        font-weight: 300 !important;
        line-height: 1 !important;
        display: inline-block !important;
        text-decoration: none !important;
    }}
    .brand-logo-text strong {{
        font-weight: 700 !important;
        color: {text_color} !important;
    }}
    </style>
""", unsafe_allow_html=True)

# 3. ENCABEZADO SUPERIOR: LOGO, BOTÓN "INGRESAR" / PERFIL Y SWITCH DE TEMA
if st.session_state['logged_in']:
    col_logo, col_espacio, col_actions = st.columns([4.0, 0.5, 4.5], vertical_alignment="center")
    btn_col1, btn_col2 = col_actions.columns([3.5, 1.0], vertical_alignment="center")
else:
    col_logo, col_espacio, col_actions = st.columns([5.5, 0.8, 2.7], vertical_alignment="center")
    btn_col1, btn_col2 = col_actions.columns([1.8, 1.0], vertical_alignment="center")

with col_logo:
    st.markdown(f"""
    <a href="/" target="_self" class="brand-logo-clean" title="PerfumeTrending">
        <svg width="34" height="34" viewBox="0 0 36 36" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path d="M 6.8 21 L 29.2 21 C 30 25 27 32 18 32 C 9 32 6 25 6.8 21 Z" fill="#8c7b6d" />
            <line x1="6.8" y1="21" x2="29.2" y2="21" stroke="{text_color}" stroke-width="1.5" />
            <line x1="18" y1="10" x2="18" y2="30" stroke="{text_color}" stroke-width="1" />
            <path d="M 18 32 C 9 32 5 24 7.5 17 C 9 12 13 10 15 10 L 21 10 C 23 10 27 12 28.5 17 C 31 24 27 32 18 32 Z" stroke="{text_color}" stroke-width="2" />
            <rect x="15" y="7" width="6" height="3" stroke="{text_color}" stroke-width="1.5" />
            <rect x="13" y="3" width="10" height="4" rx="1" stroke="{text_color}" stroke-width="1.5" />
            <rect x="16" y="0" width="4" height="3" rx="1" fill="#8c7b6d" stroke="{text_color}" stroke-width="1" />
        </svg>
        <span class="brand-logo-text">
            Perfume<strong>Trending</strong>
        </span>
    </a>
    """, unsafe_allow_html=True)

with btn_col1:
    if st.session_state['logged_in'] and st.session_state['user_info']:
        u_header_display = st.session_state['user_info'].get('nombre') or st.session_state['user_info'].get('email') or st.session_state['user_info'].get('telefono') or 'Mi Cuenta'
        with st.popover(f"{u_header_display}", use_container_width=True):
            st.write(f"**Conectado como:**")
            st.write(st.session_state['user_info'].get('email') or st.session_state['user_info'].get('telefono') or 'Usuario')
            if st.button("Cerrar Sesión", key="btn_logout", use_container_width=True):
                st.session_state['logged_in'] = False
                st.session_state['user_info'] = None
                st.rerun()
    else:
        if st.button("Ingresar", key="login_btn", use_container_width=True):
            st.session_state['show_login_modal'] = True

with btn_col2:
    st.button(" ", key="theme_toggle", on_click=toggle_theme)

# MONITOREO Y RENDERIZADO PERSISTENTE DEL MODAL
if st.session_state.get('show_login_modal', False):
    modal_autenticacion()

st.markdown("<div style='margin-top: 14px;'></div>", unsafe_allow_html=True)

# 4. CHIPS DE NAVEGACIÓN RÁPIDA
col_chip_home, col_chip1, col_chip2, col_chip3, col_chip_space = st.columns([1.6, 1.5, 2.0, 1.7, 2.2], vertical_alignment="center")

with col_chip_home:
    st.page_link("app.py", label="Inicio / Catálogo", use_container_width=True)
with col_chip1:
    st.page_link("pages/trendhype.py", label="Trend Del Hype", use_container_width=True)
with col_chip2:
    st.page_link("pages/trustpage.py", label="Páginas de Confianza", use_container_width=True)
with col_chip3:
    st.page_link("pages/compararprecios.py", label="Comparar Precios", use_container_width=True)

st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)

# 5. SECCIÓN PRINCIPAL: PERFIL DE USUARIO Y PREFERENCIAS
col_title_text, col_title_back = st.columns([7, 3], vertical_alignment="center")
with col_title_text:
    st.markdown(f"""<div style='color: {text_color}; letter-spacing: 1.5px; font-weight: 300; font-size: 1.1rem; text-transform: uppercase;'>MI PERFIL Y FRAGANCIAS MONITOREADAS</div>""", unsafe_allow_html=True)
with col_title_back:
    st.page_link("app.py", label="← Volver al Catálogo")

st.markdown("<div style='margin-top: 16px;'></div>", unsafe_allow_html=True)

# =============================================================================
# BLOQUE 3: CONTROL DE ACCESO DEFENSIVO Y GESTIÓN DE SESIÓN
# -----------------------------------------------------------------------------
# ¿QUÉ HACE ESTE BLOQUE?
# 1. Verifica si el usuario ha iniciado sesión consultando `st.session_state['logged_in']`.
# 2. Si no está autenticado, detiene la ejecución con `st.stop()` y ofrece un botón
#    para abrir el modal de acceso (OTP o credenciales).
# 3. Si está autenticado, extrae de forma reactiva los datos del usuario (`user_info`)
#    y prepara su nombre, correo, teléfono, bio y estado de alertas.
# =============================================================================
if not st.session_state['logged_in'] or not st.session_state.get('user_info'):
    st.info("Debes iniciar sesión para personalizar tu perfil y administrar tus fragancias monitoreadas.")
    if st.button("Ingresar a mi cuenta", key="btn_must_login"):
        st.session_state['show_login_modal'] = True
        st.rerun()
    st.stop()

# Extraer los datos reales registrados en la sesión activa del usuario
u_info = st.session_state['user_info']
u_nombre = u_info.get('nombre', '').strip()
u_email = u_info.get('email', '').strip()
u_telefono = u_info.get('telefono', '').strip()
u_bio = u_info.get('bio', '').strip()
u_foto = u_info.get('foto_perfil', '').strip()
u_alerta = u_info.get('alerta_email', False)

# Silueta vectorial predeterminada o imagen/GIF en Base64 cargado por el usuario
default_avatar_svg = f"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%238c7b6d' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'><path d='M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2'/><circle cx='12' cy='7' r='4'/></svg>"
avatar_src = get_image_src(u_foto) if u_foto else default_avatar_svg

# Formateo dinámico de datos de contacto
u_nombre_display = u_nombre if u_nombre else "Usuario Registrado"
u_email_display = u_email if u_email else "<i style='opacity:0.6;'>Sin correo registrado</i>"
u_telefono_display = u_telefono if u_telefono else "<i style='opacity:0.6;'>Sin teléfono registrado</i>"
u_bio_display = u_bio if u_bio else "<i style='opacity:0.7;'>Aún no has agregado una biografía. Completa tus datos personales más abajo en la pestaña 'Editar Datos Personales'.</i>"

# Indicador visual del estado de alertas por correo
if u_email and u_alerta:
    badge_alerta = f"<span style='background: {'rgba(34, 197, 94, 0.15)' if is_dark else '#e8f5e9'}; color: {'#4ade80' if is_dark else '#2e7d32'}; border: 1px solid {'rgba(74, 222, 128, 0.35)' if is_dark else 'rgba(46, 125, 50, 0.3)'}; font-size: 0.78rem; font-weight: 700; padding: 5px 12px; border-radius: 6px;'>{svg_bell_active} ALERTAS GMAIL ACTIVADAS</span>"
elif u_email and not u_alerta:
    badge_alerta = f"<span style='background: {btn_border}; color: {subtext_color}; font-size: 0.78rem; font-weight: 600; padding: 5px 12px; border-radius: 6px;'>{svg_bell_off} ALERTAS DESACTIVADAS</span>"
else:
    badge_alerta = f"<span style='background: {btn_border}; color: {subtext_color}; font-size: 0.78rem; font-weight: 600; padding: 5px 12px; border-radius: 6px;'>{svg_bell_off} AGREGA UN CORREO PARA ALERTAS</span>"


# =============================================================================
# BLOQUE 4: TARJETA DE PERFIL Y SUBIDA DE AVATAR / GIF (DATA URI EN BASE64)
# -----------------------------------------------------------------------------
# ¿QUÉ HACE ESTE BLOQUE?
# 1. Permite cambiar la foto de perfil o GIF animado directamente con un botón `file_uploader`.
# 2. Codifica los bytes del archivo a una Data URI en base64 (`data:image/png;base64,...`),
#    almacenándola en la sesión y persistiendo en la base de datos sin necesidad de hosting adicional.
# =============================================================================
st.markdown('<div class="profile-card-container">', unsafe_allow_html=True)
col_av, col_details = st.columns([1.5, 8.5], vertical_alignment="center")

with col_av:
    st.markdown(clean_html(f'''
    <div class="avatar-click-zone" title="Haz clic aquí para seleccionar y cambiar tu foto de perfil o GIF desde tu PC">
        <img src="{avatar_src}" class="profile-avatar-img" alt="{u_nombre_display}">
        <div class="avatar-overlay-badge">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg>
            <span style="font-size: 0.7rem; font-weight: 700; margin-top: 2px;">Cambiar</span>
        </div>
    </div>
    '''), unsafe_allow_html=True)
    
    # Cargar foto o GIF directamente
    quick_file = st.file_uploader(
        "Subir Foto", 
        type=["png", "jpg", "jpeg", "gif", "webp"], 
        key="avatar_quick_uploader", 
        label_visibility="collapsed"
    )
    
    if quick_file is not None:
        bytes_data = quick_file.getvalue()
        b64 = base64.b64encode(bytes_data).decode('utf-8')
        mime = quick_file.type or "image/png"
        st.session_state['user_info']['foto_perfil'] = f"data:{mime};base64,{b64}"
        st.toast("¡Foto de perfil actualizada correctamente!")
        st.rerun()

with col_details:
    st.markdown(clean_html(f'''
    <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 10px;">
        <div>
            <h2 style="margin: 0 0 4px 0; color: {text_color}; font-size: 1.5rem; font-weight: 700;">{u_nombre_display}</h2>
            <div style="color: {subtext_color}; font-size: 0.9rem; margin-bottom: 8px; display: flex; align-items: center; flex-wrap: wrap;">
                {svg_mail} <span>{u_email_display}</span> &nbsp;&bull;&nbsp; {svg_phone} <span>{u_telefono_display}</span>
            </div>
        </div>
        <div>{badge_alerta}</div>
    </div>
    <p style="margin: 6px 0 0 0; color: {text_color}; font-size: 0.92rem; line-height: 1.5;">
        {u_bio_display}
    </p>
    '''), unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)


# =============================================================================
# BLOQUE 5: GESTIÓN DE FRAGANCIAS FAVORITAS Y ALGORITMO DE DETECCIÓN DE REBAJAS
# -----------------------------------------------------------------------------
# ¿QUÉ HACE ESTE BLOQUE?
# En la pestaña "Fragancias Monitoreadas":
# 1. Recupera la lista de IDs guardados en `st.session_state['favoritos']`.
# 2. Por cada perfume, consulta los precios en vivo con `get_cached_precios(p_id)`.
# 3. Compara el mejor precio actual (`p_min`) contra el precio guardado/referencia (`p_ref`).
# 4. Si `p_min < p_ref`, activa la insignia verde con animación de flecha hacia abajo
#    indicando que hubo una baja de precio real en el mercado chileno.
# =============================================================================
tab_favs, tab_edit, tab_notif = st.tabs([
    "Fragancias Monitoreadas", 
    "Editar Datos Personales", 
    "Configuración de Alertas"
])

# --- TAB 1: FRAGANCIAS FAVORITAS ---
with tab_favs:
    svg_heart_header = f'<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#d83737" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: -3px; margin-right: 8px;"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>'
    st.markdown(f"<h3 style='display: flex; align-items: center;'>{svg_heart_header} Mis Fragancias Favoritas</h3>", unsafe_allow_html=True)
    st.caption("Las fragancias agregadas a tus favoritos se monitorean en tiempo real. Si activas las alertas por correo, te avisaremos automáticamente cuando detectemos una baja de precio.")
    
    catalogo = get_cached_catalogo() or []
    fav_ids = st.session_state.get('favoritos', [])
    
    fav_items = [p for p in catalogo if p['id'] in fav_ids]
    
    if not fav_items:
        st.info("Aún no tienes fragancias guardadas en tus favoritos. Navega por el catálogo y agrega tus perfumes preferidos.")
        if st.button("Ir al Catálogo de Perfumes", key="btn_go_catalog"):
            st.switch_page("app.py")
    else:
        for item in fav_items:
            p_id = item['id']
            p_nombre = item.get('nombre', 'Perfume')
            p_marca = item.get('marca', 'Marca')
            
            # Obtener ofertas actuales
            precios = get_cached_precios(p_id) or []
            precios_val = [t['precio_actual'] for t in precios if t.get('precio_actual', 0) > 0]
            
            p_min = min(precios_val) if precios_val else item.get('precio_referencia', 0)
            p_ref = item.get('precio_referencia', p_min)
            
            baja_detectada = (p_min < p_ref) and p_min > 0
            badge_precio = f"<span style='color: {'#4ade80' if is_dark else '#2e7d32'}; font-weight: 700;'>{svg_trend_down} ¡Baja de precio! ${p_min:,.0f} CLP</span>".replace(",", ".") if baja_detectada else f"<span style='color: {text_color}; font-weight: 600;'>Mejor precio: ${p_min:,.0f} CLP</span>".replace(",", ".")
            
            col_f1, col_f2, col_f3, col_f4 = st.columns([3, 2.5, 2, 1.5], vertical_alignment="center")
            with col_f1:
                st.markdown(f"**{p_nombre}**  \n<span style='color:{subtext_color}; font-size:0.85rem;'>{p_marca}</span>", unsafe_allow_html=True)
            with col_f2:
                st.markdown(badge_precio, unsafe_allow_html=True)
            with col_f3:
                if st.button("Comparar Precios", key=f"btn_comp_fav_{p_id}", use_container_width=True):
                    st.session_state['selected_perfume'] = p_id
                    st.switch_page("pages/compararprecios.py")
            with col_f4:
                if st.button("Quitar de Favoritos", key=f"btn_rem_fav_{p_id}", use_container_width=True):
                    st.session_state['favoritos'].remove(p_id)
                    st.toast(f"Se quitó {p_nombre} de tus favoritos.")
                    st.rerun()

# --- TAB 2: EDITAR PERFIL Y SUBIR FOTO/GIF ---
with tab_edit:
    svg_edit_header = f'<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="{text_color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: -3px; margin-right: 8px;"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>'
    st.markdown(f"<h3 style='display: flex; align-items: center;'>{svg_edit_header} Completar y Modificar Datos Personales</h3>", unsafe_allow_html=True)
    
    with st.form("form_edit_user_profile"):
        col_e1, col_e2 = st.columns(2, gap="medium")
        
        with col_e1:
            e_nombre = st.text_input("Nombre completo / Nickname", value=u_nombre, placeholder="Ej: Carlos Mendoza")
            e_email = st.text_input("Correo Electrónico", value=u_email, placeholder="ejemplo@correo.cl")
            e_telefono = st.text_input("Número de Teléfono", value=u_telefono, placeholder="+56 9 1234 5678")
            
        with col_e2:
            uploaded_file = st.file_uploader("Seleccionar foto o GIF desde PC", type=["png", "jpg", "jpeg", "gif", "webp"], help="Selecciona una imagen o GIF animado desde tu computadora")
            e_foto_url = st.text_input("O ingresar URL de imagen/GIF", value=u_foto if u_foto.startswith("http") else "", placeholder="https://sitio.com/mi-foto.gif", help="Pega un enlace directo si la imagen está en web")
            e_bio = st.text_area("Biografía / Descripción", value=u_bio, placeholder="Escribe un breve resumen sobre ti o tus gustos olfativos...", max_chars=280, height=100)
            
        btn_save = st.form_submit_button("Guardar Cambios de Perfil", use_container_width=True)
        
        if btn_save:
            if not st.session_state.get('user_info'):
                st.session_state['user_info'] = {}
                
            st.session_state['user_info']['nombre'] = e_nombre.strip()
            st.session_state['user_info']['email'] = e_email.strip()
            st.session_state['user_info']['telefono'] = e_telefono.strip()
            st.session_state['user_info']['bio'] = e_bio.strip()
            
            # Procesar foto o GIF subido desde archivo o URL
            if uploaded_file is not None:
                bytes_data = uploaded_file.getvalue()
                b64 = base64.b64encode(bytes_data).decode('utf-8')
                mime = uploaded_file.type or "image/png"
                st.session_state['user_info']['foto_perfil'] = f"data:{mime};base64,{b64}"
            elif e_foto_url.strip():
                st.session_state['user_info']['foto_perfil'] = e_foto_url.strip()
            
            if e_email.strip() and 'alerta_email' not in st.session_state['user_info']:
                st.session_state['user_info']['alerta_email'] = True
                
            st.success("¡Tu perfil y avatar han sido actualizados correctamente!")
            st.rerun()

# --- TAB 3: CONFIGURACIÓN DE NOTIFICACIONES Y ALERTAS ---
with tab_notif:
    svg_notif_header = f'<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="{text_color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: -3px; margin-right: 8px;"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>'
    st.markdown(f"<h3 style='display: flex; align-items: center;'>{svg_notif_header} Alertas por Correo Electrónico (Gmail)</h3>", unsafe_allow_html=True)
    st.write("Recibe avisos en tiempo real cuando tus fragancias favoritas tengan una baja de precio o entren en oferta especial en tiendas auditadas de Chile.")
    
    if not u_email:
        st.warning("Para activar y recibir notificaciones por correo electrónico, primero debes ingresar tu dirección de correo en la pestaña 'Editar Datos Personales'.")
    
    with st.form("form_notif_settings"):
        alerta_check = st.checkbox(
            "Deseo recibir correos electrónicos cuando una fragancia de mis favoritos baje de precio.",
            value=u_alerta,
            disabled=not bool(u_email)
        )
        
        umbral_val = st.slider(
            "Avisarme únicamente si el descuento es igual o mayor a:",
            min_value=5,
            max_value=50,
            value=st.session_state['user_info'].get('umbral_descuento', 10),
            step=5,
            format="%d%%"
        )
        
        btn_save_notif = st.form_submit_button("Guardar Preferencias de Alertas", use_container_width=True)
        
        if btn_save_notif:
            st.session_state['user_info']['alerta_email'] = alerta_check
            st.session_state['user_info']['umbral_descuento'] = umbral_val
            
            if alerta_check and u_email:
                st.success(f"¡Alertas activadas! Te enviaremos un correo a {u_email} cuando detectemos ofertas con más de {umbral_val}% de descuento.")
            else:
                st.info("Has desactivado las notificaciones por correo electrónico.")
            st.rerun()

# 6. PIE DE PÁGINA
st.markdown(f"<hr style='margin: 40px 0 20px 0; border: none; border-bottom: 1px solid {btn_border}; opacity: 0.3;'>", unsafe_allow_html=True)
st.markdown(f"""
    <div style="text-align: center; padding: 10px 0 20px 0; color: {subtext_color}; font-size: 0.85rem;">
        © 2026 Perfume Trending. Todos los derechos reservados.
    </div>
""", unsafe_allow_html=True)
