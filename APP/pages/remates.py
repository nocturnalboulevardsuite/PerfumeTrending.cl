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
    from backend.database import obtener_catalogo
    obtener_precios_actuales = None
    obtener_detalle_perfume = None
    crear_usuario = None
    verificar_usuario = None

@st.cache_data(ttl=300, show_spinner=False)
def get_cached_catalogo():
    return obtener_catalogo()

def clean_html(html_str: str) -> str:
    """Limpia espacios iniciales y elimina saltos de línea para evitar que Streamlit interprete HTML como código."""
    return " ".join(line.strip() for line in html_str.splitlines() if line.strip())

def resolver_url_oferta(tienda_nombre: str, perfume_nombre: str, url_prod: str = "", url_base: str = "") -> str:
    """Retorna la URL directa a la oferta o realiza la búsqueda directa en la tienda."""
    if url_prod and url_prod.startswith("http") and url_prod != "#":
        return url_prod

    t = (tienda_nombre or "").lower()
    q = urllib.parse.quote(perfume_nombre.strip())

    if "falabella" in t:
        return f"https://www.falabella.com/falabella-cl/search?Ntt={q}"
    elif "paris" in t:
        return f"https://www.paris.cl/search?q={q}"
    elif "ripley" in t:
        return f"https://simple.ripley.cl/search/{q}"
    elif "silk" in t:
        return f"https://www.silkperfumes.cl/search?q={q}"
    elif "elite" in t:
        return f"https://www.eliteperfumes.cl/search?q={q}"
    elif "alisha" in t:
        return f"https://www.alisha.cl/search?q={q}"
    elif "dbs" in t:
        return f"https://www.dbs.cl/search?q={q}"

    return url_base or "#"

def get_image_src(img_path_or_url):
    """Retorna URL remota o data URI en base64 para imágenes locales."""
    if not img_path_or_url:
        return "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=500&q=80"
    
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
        mime = "image/png" if ext == "png" else "image/jpeg"
        try:
            with open(local_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
                return f"data:{mime};base64,{b64}"
        except Exception:
            pass

    return img_path_or_url

# 1. CONFIGURACIÓN DE LA PÁGINA Y ESTADO
st.set_page_config(page_title="Remates de Último Minuto - PerfumeTrending", layout="wide", initial_sidebar_state="collapsed")

if 'theme' not in st.session_state:
    st.session_state['theme'] = 'dark'

# ESTADOS DE AUTENTICACIÓN Y CONTROL DE MODAL
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

if 'selected_perfume' not in st.session_state:
    st.session_state['selected_perfume'] = None

def toggle_theme():
    st.session_state['theme'] = 'dark' if st.session_state['theme'] == 'light' else 'light'

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

is_dark = st.session_state['theme'] == 'dark'

# Colores dinámicos adaptables por tema
app_bg = "#0c0e12" if is_dark else "#f9f9fb"
app_bg_css = f"background-color: {app_bg} !important;"

card_bg = "#14171d" if is_dark else "#ffffff"
border_color = "#2a2e39" if is_dark else "#e4e4e7"
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
settings_icon_svg = f"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23{btn_text[1:]}' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.38a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z'/><circle cx='12' cy='12' r='3'/></svg>"
logout_icon_svg = f"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23{btn_text[1:]}' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4'/><polyline points='16 17 21 12 16 7'/><line x1='21' y1='12' x2='9' y2='12'/></svg>"

# ICONOS VECTORIALES DE NAVEGACIÓN
trend_red_svg = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23d83737' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><polyline points='23 6 13.5 15.5 8.5 10.5 1 18'/><polyline points='17 6 23 6 23 12'/></svg>"
shield_red_svg = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23d83737' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z'/><polyline points='9 12 11 14 15 10'/></svg>"
tag_red_svg = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23d83737' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z'/><circle cx='7' cy='7' r='1.5' fill='%23d83737'/></svg>"
home_red_svg = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23d83737' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z'/><polyline points='9 22 9 12 15 12 15 22'/></svg>"
flame_red_svg = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23d83737' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 3.5z'/></svg>"

# 2. CSS ADAPTABLE Y ESTILOS DE LA PÁGINA
st.markdown(f"""
    <style>
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

    /* BOTONES GENERALES SOBRIOS (IGUAL A APP.PY) */
    div.stButton > button {{
        background-color: {btn_bg} !important;
        border: 1px solid {btn_border} !important;
        color: {btn_text} !important;
        border-radius: 8px !important;
        transition: transform 0.22s cubic-bezier(0.34, 1.56, 0.64, 1), background-color 0.15s ease, border-color 0.15s ease !important;
        outline: none !important;
    }}

    div.stButton > button p {{
        color: {btn_text} !important;
        font-weight: 600 !important;
    }}

    /* BOTONES DE ACCIÓN ROJOS EXCLUSIVOS PARA LAS TARJETAS DE REMATES */
    div[data-testid="stElementContainer"] div.stButton button[key*="btn_remate_"],
    div.stButton > button[key*="btn_remate_"] {{
        background-color: #d83737 !important;
        color: #ffffff !important;
        border: 1px solid #d83737 !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
        font-size: 0.9rem !important;
        box-shadow: 0 4px 12px rgba(216, 55, 55, 0.25) !important;
        transition: transform 0.25s ease, background-color 0.2s ease, box-shadow 0.25s ease !important;
    }}

    div[data-testid="stElementContainer"] div.stButton button[key*="btn_remate_"] p,
    div.stButton > button[key*="btn_remate_"] p {{
        color: #ffffff !important;
        font-weight: 700 !important;
    }}

    div[data-testid="stElementContainer"] div.stButton button[key*="btn_remate_"]:hover,
    div.stButton > button[key*="btn_remate_"]:hover {{
        background-color: #be2e2e !important;
        border-color: #be2e2e !important;
        color: #ffffff !important;
        transform: scale(1.03) translateY(-2px) !important;
        box-shadow: 0 6px 16px rgba(216, 55, 55, 0.38) !important;
    }}

    /* BOTÓN INGRESAR Y CABECERA */
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

    /* ESTILO PARA BOTÓN POPOVER Y DESPLEGABLE DE PERFIL */
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

    .user-popover-container div[data-testid="stPopover"],
    .user-popover-container div[data-testid="stPopover"] > button,
    .user-popover-container button[data-testid="stPopoverButton"] {{
        padding-left: 2.3rem !important;
        background-image: url("{user_icon_svg}") !important;
        background-repeat: no-repeat !important;
        background-position: 12px center !important;
        background-size: 18px 18px !important;
    }}

    /* BOTONES DENTRO DEL POPOVER DE PERFIL */
    .st-key-btn_go_profile button {{
        background-color: {btn_bg} !important;
        border: 1px solid {btn_border} !important;
        color: {btn_text} !important;
        padding-left: 2.5rem !important;
        background-image: url("{settings_icon_svg}") !important;
        background-repeat: no-repeat !important;
        background-position: 14px center !important;
        background-size: 18px 18px !important;
    }}

    .st-key-btn_go_profile button p {{
        color: {btn_text} !important;
    }}

    .st-key-btn_logout button {{
        background-color: {btn_bg} !important;
        border: 1px solid {btn_border} !important;
        color: {btn_text} !important;
        padding-left: 2.5rem !important;
        background-image: url("{logout_icon_svg}") !important;
        background-repeat: no-repeat !important;
        background-position: 14px center !important;
        background-size: 18px 18px !important;
    }}

    .st-key-btn_logout button p {{
        color: {btn_text} !important;
    }}

    /* SWITCH DE TEMA BOTELLA */
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

    /* CHIPS DE NAVEGACIÓN Y PAGE LINKS CON DIBUJOS ROJOS */
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
    a[data-testid="stPageLink-NavLink"][href*="remates"],
    a[data-testid="stPageLink-NavLink"][href$="app.py"],
    a[data-testid="stPageLink-NavLink"][href="/"] {{
        position: relative !important;
        padding-left: 2.7rem !important;
        padding-right: 1.1rem !important;
        overflow: hidden !important;
    }}

    a[data-testid="stPageLink-NavLink"][href*="trendhype"]::before {{
        content: '' !important; position: absolute !important; left: 14px !important; top: 50% !important;
        transform: translateY(-50%) !important; width: 17px !important; height: 17px !important;
        background-image: url("{trend_red_svg}") !important; background-repeat: no-repeat !important;
        background-size: contain !important; background-position: center !important; z-index: 1 !important;
    }}

    a[data-testid="stPageLink-NavLink"][href*="trustpage"]::before {{
        content: '' !important; position: absolute !important; left: 14px !important; top: 50% !important;
        transform: translateY(-50%) !important; width: 17px !important; height: 17px !important;
        background-image: url("{shield_red_svg}") !important; background-repeat: no-repeat !important;
        background-size: contain !important; background-position: center !important; z-index: 1 !important;
    }}

    a[data-testid="stPageLink-NavLink"][href*="compararprecios"]::before {{
        content: '' !important; position: absolute !important; left: 14px !important; top: 50% !important;
        transform: translateY(-50%) !important; width: 17px !important; height: 17px !important;
        background-image: url("{tag_red_svg}") !important; background-repeat: no-repeat !important;
        background-size: contain !important; background-position: center !important; z-index: 1 !important;
    }}

    a[data-testid="stPageLink-NavLink"][href*="remates"]::before {{
        content: '' !important; position: absolute !important; left: 14px !important; top: 50% !important;
        transform: translateY(-50%) !important; width: 17px !important; height: 17px !important;
        background-image: url("{flame_red_svg}") !important; background-repeat: no-repeat !important;
        background-size: contain !important; background-position: center !important; z-index: 1 !important;
    }}

    a[data-testid="stPageLink-NavLink"][href$="app.py"]::before,
    a[data-testid="stPageLink-NavLink"][href="/"]::before {{
        content: '' !important; position: absolute !important; left: 14px !important; top: 50% !important;
        transform: translateY(-50%) !important; width: 17px !important; height: 17px !important;
        background-image: url("{home_red_svg}") !important; background-repeat: no-repeat !important;
        background-size: contain !important; background-position: center !important; z-index: 1 !important;
    }}

    /* TARJETAS DEDICADAS DE REMATE */
    .remate-card {{
        background-color: {card_bg};
        border: 2px solid {border_color};
        border-radius: 14px;
        padding: 16px;
        position: relative;
        margin-bottom: 20px;
        box-shadow: 0 4px 14px rgba(0,0,0,0.12);
        transition: transform 0.3s cubic-bezier(0.25, 0.8, 0.25, 1), border-color 0.3s ease, box-shadow 0.3s ease;
    }}

    .remate-card:hover {{
        transform: translateY(-6px);
        border-color: #d83737;
        box-shadow: 0 12px 24px rgba(216, 55, 55, 0.22);
    }}

    .badge-discount {{
        position: absolute;
        top: 12px;
        left: 12px;
        background: linear-gradient(135deg, #d83737 0%, #a81722 100%);
        color: #ffffff;
        font-weight: 900;
        font-size: 0.85rem;
        padding: 4px 10px;
        border-radius: 6px;
        letter-spacing: 0.5px;
        box-shadow: 0 2px 6px rgba(216, 55, 55, 0.4);
        z-index: 2;
    }}

    .badge-timer {{
        position: absolute;
        top: 12px;
        right: 12px;
        background-color: {app_bg};
        border: 1px solid {border_color};
        color: #eab308;
        font-weight: 700;
        font-size: 0.78rem;
        padding: 3px 8px;
        border-radius: 6px;
        display: flex;
        align-items: center;
        gap: 4px;
        z-index: 2;
    }}

    .remate-img-box {{
        width: 100%;
        height: 150px;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-top: 24px;
        margin-bottom: 12px;
    }}

    .remate-img-box img {{
        max-height: 100%;
        max-width: 100%;
        object-fit: contain;
        transition: transform 0.3s ease;
    }}

    .remate-card:hover .remate-img-box img {{
        transform: scale(1.08);
    }}

    .remate-title {{
        font-size: 1.05rem;
        font-weight: 700;
        color: {text_color};
        margin-bottom: 4px;
        text-align: center;
    }}

    .remate-brand {{
        font-size: 0.8rem;
        color: {subtext_color};
        text-transform: uppercase;
        letter-spacing: 0.8px;
        text-align: center;
        margin-bottom: 12px;
    }}

    .remate-store-row {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        background-color: {app_bg};
        padding: 8px 12px;
        border-radius: 8px;
        border: 1px solid {border_color};
        margin-bottom: 12px;
        font-size: 0.82rem;
    }}

    .price-box {{
        text-align: center;
        margin-bottom: 14px;
    }}

    .old-price-line {{
        text-decoration: line-through;
        color: {subtext_color};
        font-size: 0.9rem;
        margin-right: 8px;
    }}

    .deal-price {{
        font-size: 1.35rem;
        font-weight: 900;
        color: #22c55e;
    }}

    .stock-badge {{
        font-size: 0.75rem;
        color: #ef4444;
        font-weight: 700;
        text-align: center;
        margin-bottom: 10px;
    }}
    </style>
""", unsafe_allow_html=True)

# 3. ENCABEZADO SUPERIOR: LOGO, PERFIL Y SWITCH DE TEMA
if st.session_state['logged_in']:
    col_logo, col_espacio, col_actions = st.columns([4.0, 0.5, 4.5], vertical_alignment="center")
    btn_col1, btn_col2 = col_actions.columns([3.5, 1.0], vertical_alignment="center")
else:
    col_logo, col_espacio, col_actions = st.columns([5.5, 0.8, 2.7], vertical_alignment="center")
    btn_col1, btn_col2 = col_actions.columns([1.8, 1.0], vertical_alignment="center")

with col_logo:
    logo_color = "#8c7b6d"
    logo_html = f"""<a href="/" target="_top" style="text-decoration: none; display: inline-flex; align-items: center; gap: 12px; cursor: pointer; width: fit-content;"><svg width="34" height="34" viewBox="0 0 36 36" fill="none" stroke-linecap="round" stroke-linejoin="round"><path d="M 6.8 21 L 29.2 21 C 30 25 27 32 18 32 C 9 32 6 25 6.8 21 Z" fill="{logo_color}" /><line x1="6.8" y1="21" x2="29.2" y2="21" stroke="{text_color}" stroke-width="1.5" /><line x1="18" y1="10" x2="18" y2="30" stroke="{text_color}" stroke-width="1" /><path d="M 18 32 C 9 32 5 24 7.5 17 C 9 12 13 10 15 10 L 21 10 C 23 10 27 12 28.5 17 C 31 24 27 32 18 32 Z" stroke="{text_color}" stroke-width="2" /><rect x="15" y="7" width="6" height="3" stroke="{text_color}" stroke-width="1.5" /><rect x="13" y="3" width="10" height="4" rx="1" stroke="{text_color}" stroke-width="1.5" /><rect x="16" y="0" width="4" height="3" rx="1" fill="{logo_color}" stroke="{text_color}" stroke-width="1" /></svg><span style="font-size: 1.4rem; color: {text_color}; letter-spacing: 0.5px;"><span style="font-weight: 300;">Perfume</span><span style="font-weight: 600;">Trending</span></span></a>"""
    st.markdown(logo_html, unsafe_allow_html=True)

with btn_col1:
    if st.session_state['logged_in']:
        user_display = st.session_state['user_info'].get('nombre') or st.session_state['user_info'].get('email', 'Usuario')
        st.markdown('<div class="user-popover-container">', unsafe_allow_html=True)
        with st.popover(f"{user_display}", use_container_width=True):
            st.write(f"**Conectado como:**")
            st.write(st.session_state['user_info'].get('email', ''))
            st.markdown("<div style='margin-top: 8px;'></div>", unsafe_allow_html=True)
            
            # LINK DIRECTO A MI PERFIL Y ALERTAS
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

# 4. CHIPS DE NAVEGACIÓN RÁPIDA
col_chip_home, col_chip1, col_chip2, col_chip3, col_chip4 = st.columns([1.6, 1.5, 2.0, 1.7, 1.6], vertical_alignment="center")

with col_chip_home:
    st.page_link("app.py", label="Inicio / Catálogo", use_container_width=True)
with col_chip1:
    st.page_link("pages/trendhype.py", label="Trend Del Hype", use_container_width=True)
with col_chip2:
    st.page_link("pages/trustpage.py", label="Páginas de Confianza", use_container_width=True)
with col_chip3:
    st.page_link("pages/compararprecios.py", label="Comparar Precios", use_container_width=True)
with col_chip4:
    st.page_link("pages/remates.py", label="Remates & Flash", use_container_width=True)

st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)

# 5. TITULO PRINCIPAL DE LA SECCIÓN
col_title_text, col_title_back = st.columns([7, 3], vertical_alignment="center")
with col_title_text:
    st.markdown(f"""
    <div style='display: flex; align-items: center; gap: 10px;'>
        <span style='font-size: 1.6rem;'>⚡</span>
        <h1 style='color: {text_color}; font-size: 1.5rem; font-weight: 800; margin: 0; letter-spacing: 0.5px;'>REMATES DE ÚLTIMO MINUTO Y LIQUIDACIONES</h1>
    </div>
    <div style='color: {subtext_color}; font-size: 0.9rem; margin-top: 4px;'>
        Ofertas relámpago con stock limitado y descuentos excepcionales auditados en tiendas chilenas.
    </div>
    """, unsafe_allow_html=True)

with col_title_back:
    st.page_link("app.py", label="← Volver al Catálogo")

st.markdown("<div style='margin-top: 18px;'></div>", unsafe_allow_html=True)

# 6. FILTROS Y CONTROL BÚSQUEDA
col_search, col_order, col_tienda = st.columns([4, 3, 3], gap="small", vertical_alignment="center")

with col_search:
    search_remate = st.text_input("Buscar remates...", placeholder="Filtrar por perfume o tienda...", label_visibility="collapsed")

with col_order:
    orden_opt = st.selectbox("Ordenar por:", ["Mayor % Descuento", "Menor Precio", "Mayor Precio"], label_visibility="collapsed")

with col_tienda:
    tienda_opt = st.selectbox("Tienda:", ["Todas las tiendas", "Falabella", "Paris", "Silk Perfumes", "Elite Perfumes", "Alisha Perfumes"], label_visibility="collapsed")

st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)

# 7. DATOS SIMULADOS DE REMATES FLASH CON STOCK LIMITADO Y PRECIOS AUDITADOS
remates_data = [
    {
        "id": 1,
        "nombre": "Bleu de Chanel EDP 100ml",
        "marca": "Chanel",
        "tienda": "Falabella",
        "descuento": "-32% OFF",
        "precio_normal": 165990,
        "precio_remate": 112990,
        "timer": "01h 45m",
        "stock": "¡Últimas 2 unidades!",
        "img": get_image_src("APP/assets/perfumes/bleu_de_chanel.jpg"),
        "url": "https://www.falabella.com/falabella-cl/search?Ntt=Bleu+de+Chanel"
    },
    {
        "id": 2,
        "nombre": "YSL Libre Intense 90ml",
        "marca": "Yves Saint Laurent",
        "tienda": "Paris",
        "descuento": "-38% OFF",
        "precio_normal": 149990,
        "precio_remate": 92990,
        "timer": "00h 32m",
        "stock": "¡Queda 1 sola unidad!",
        "img": get_image_src("APP/assets/perfumes/ysl_libre.jpg"),
        "url": "https://www.paris.cl/search?q=YSL+Libre"
    },
    {
        "id": 5,
        "nombre": "Lattafa Khamrah 100ml",
        "marca": "Lattafa",
        "tienda": "Elite Perfumes",
        "descuento": "-42% OFF",
        "precio_normal": 49990,
        "precio_remate": 28990,
        "timer": "03h 15m",
        "stock": "¡Quedan 5 unidades!",
        "img": get_image_src("APP/assets/perfumes/lattafa_khamrah.jpg"),
        "url": "https://www.eliteperfumes.cl/search?q=Khamrah"
    },
    {
        "id": 4,
        "nombre": "Club de Nuit Intense 105ml",
        "marca": "Armaf",
        "tienda": "Alisha Perfumes",
        "descuento": "-40% OFF",
        "precio_normal": 54990,
        "precio_remate": 32990,
        "timer": "02h 10m",
        "stock": "¡Últimas 3 unidades!",
        "img": get_image_src("APP/assets/perfumes/club_de_nuit.jpg"),
        "url": "https://www.alisha.cl/search?q=Club+de+Nuit"
    },
    {
        "id": 3,
        "nombre": "Dior Sauvage Elixir 60ml",
        "marca": "Dior",
        "tienda": "Silk Perfumes",
        "descuento": "-28% OFF",
        "precio_normal": 179990,
        "precio_remate": 129990,
        "timer": "05h 40m",
        "stock": "¡Quedan 4 unidades!",
        "img": get_image_src("APP/assets/perfumes/dior_sauvage.jpg"),
        "url": "https://www.silkperfumes.cl/search?q=Dior+Sauvage"
    },
    {
        "id": 6,
        "nombre": "Baccarat Rouge 540 EDP 70ml",
        "marca": "Maison Francis Kurkdjian",
        "tienda": "Falabella",
        "descuento": "-25% OFF",
        "precio_normal": 385000,
        "precio_remate": 288990,
        "timer": "00h 18m",
        "stock": "¡Queda 1 unidad!",
        "img": get_image_src("APP/assets/perfumes/baccarat_rouge.jpg"),
        "url": "https://www.falabella.com/falabella-cl/search?Ntt=Baccarat+Rouge"
    }
]

# Filtrar resultados
items_filtrados = []
for item in remates_data:
    match_search = (search_remate.lower() in item['nombre'].lower() or search_remate.lower() in item['marca'].lower() or search_remate.lower() in item['tienda'].lower()) if search_remate else True
    match_tienda = (tienda_opt == "Todas las tiendas" or tienda_opt.lower() in item['tienda'].lower())
    if match_search and match_tienda:
        items_filtrados.append(item)

# Ordenar
if orden_opt == "Mayor % Descuento":
    items_filtrados.sort(key=lambda x: int(x['descuento'].replace('-', '').replace('% OFF', '')), reverse=True)
elif orden_opt == "Menor Precio":
    items_filtrados.sort(key=lambda x: x['precio_remate'])
elif orden_opt == "Mayor Precio":
    items_filtrados.sort(key=lambda x: x['precio_remate'], reverse=True)

# 8. RENDERIZADO EN GRID DE TARJETAS
if not items_filtrados:
    st.info("No hay ofertas de remate relámpago que coincidan con los filtros seleccionados.")
else:
    cols_per_row = 3
    for row in range(0, len(items_filtrados), cols_per_row):
        cols = st.columns(cols_per_row, gap="medium")
        for i in range(cols_per_row):
            idx = row + i
            if idx < len(items_filtrados):
                item = items_filtrados[idx]
                p_norm_str = f"${item['precio_normal']:,.0f}".replace(",", ".")
                p_rem_str = f"${item['precio_remate']:,.0f}".replace(",", ".")
                
                with cols[i]:
                    html_card = f"""
                    <div class="remate-card">
                        <div class="badge-discount">{item['descuento']}</div>
                        <div class="badge-timer">⏱️ {item['timer']}</div>
                        <div class="remate-img-box">
                            <img src="{item['img']}" alt="{item['nombre']}">
                        </div>
                        <div class="remate-title">{item['nombre']}</div>
                        <div class="remate-brand">{item['marca']}</div>
                        <div class="remate-store-row">
                            <span>Vendido por: <b>{item['tienda']}</b></span>
                            <span style="color: #4ade80; font-weight: 700;">Verificado ✓</span>
                        </div>
                        <div class="stock-badge">{item['stock']}</div>
                        <div class="price-box">
                            <span class="old-price-line">{p_norm_str} CLP</span>
                            <span class="deal-price">{p_rem_str} CLP</span>
                        </div>
                    </div>
                    """
                    st.markdown(clean_html(html_card), unsafe_allow_html=True)
                    
                    # Botón exclusivo para ir directo a la oferta del comercio
                    if st.button("Ir al Remate ↗", key=f"btn_remate_{idx}", use_container_width=True):
                        st.markdown(f'<script>window.open("{item["url"]}", "_blank");</script>', unsafe_allow_html=True)
