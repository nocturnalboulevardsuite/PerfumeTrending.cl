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

import hashlib

from backend.database import (
    actualizar_perfil_usuario,
    actualizar_preferencias_notificacion,
    eliminar_favorito,
    obtener_catalogo,
    obtener_detalle_perfume,
    obtener_favoritos_usuario,
    obtener_perfil_usuario,
    obtener_precios_actuales,
    subir_avatar_usuario,
)
from ui import (
    DEFAULT_AVATAR_SVG,
    HOME_RED_SVG as home_red_svg,
    PERFUME_SVG_FAVICON,
    SHIELD_RED_SVG as shield_red_svg,
    TAG_RED_SVG as tag_red_svg,
    TREND_RED_SVG as trend_red_svg,
    cerrar_sesion_usuario,
    clean_html as _shared_clean_html,
    escape_html,
    get_image_src,
    get_theme_palette,
    init_common_session_state,
    is_valid_https_image_url,
    modal_autenticacion,
    toggle_theme,
)


def clean_html(html_str: str) -> str:
    """Limpia espacios iniciales y saltos de línea para evitar bloques de código accidentales."""
    return _shared_clean_html(html_str, join_char=" ")


@st.cache_data(ttl=120, show_spinner=False)
def get_cached_catalogo():
    return obtener_catalogo()


@st.cache_data(ttl=120, show_spinner=False)
def get_cached_precios(perfume_id):
    return obtener_precios_actuales(perfume_id)


# 1. CONFIGURACIÓN DE LA PÁGINA Y ESTADO SEGURO (SIN FAVORITOS HARDCODEADOS NI BYPASS)
st.set_page_config(
    page_title="Mi Perfil - PerfumeTrending",
    page_icon=PERFUME_SVG_FAVICON,
    layout="wide",
    initial_sidebar_state="collapsed",
)

init_common_session_state()

pal = get_theme_palette()
is_dark = pal.is_dark
app_bg = pal.app_bg
app_bg_css = pal.app_bg_css
text_color = pal.text_color
subtext_color = pal.subtext_color
btn_bg = pal.btn_bg
btn_text = pal.btn_text
btn_border = pal.btn_border
input_bg = pal.input_bg
input_text = pal.input_text
input_border = pal.input_border
bottle_left_pos = pal.bottle_left_pos
static_icon_pos = pal.static_icon_pos
static_icon_svg = pal.static_icon_svg
bottle_svg = pal.bottle_svg
user_icon_svg = pal.user_icon_svg

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
                cerrar_sesion_usuario()
                st.rerun()
    else:
        if st.button("Ingresar", key="login_btn", use_container_width=True):
            st.session_state['show_login_modal'] = True
            st.rerun()

with btn_col2:
    st.button(" ", key="theme_toggle", on_click=toggle_theme)

# MONITOREO Y RENDERIZADO PERSISTENTE DEL MODAL
if st.session_state.get('show_login_modal', False):
    st.session_state['show_login_modal'] = False
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

# Sincronizar el perfil real desde Supabase Auth / SQLite cuando existe sesión activa
u_info = st.session_state['user_info']
u_ident = u_info.get('id') or u_info.get('email')
if u_ident and not st.session_state.get('_perfil_cloud_synced'):
    perfil_remoto = obtener_perfil_usuario(u_ident)
    if perfil_remoto:
        st.session_state['user_info'].update(perfil_remoto)
        u_info = st.session_state['user_info']
    st.session_state['_perfil_cloud_synced'] = True

u_nombre = (u_info.get('nombre') or '').strip()
u_email = (u_info.get('email') or '').strip()
u_telefono = (u_info.get('telefono') or '').strip()
u_ubicacion = (u_info.get('ubicacion') or 'Santiago, Chile').strip()
u_bio = (u_info.get('bio') or '').strip()
u_foto = (u_info.get('foto_perfil') or '').strip()
u_alerta = bool(u_info.get('alerta_email', True))
u_umbral = int(u_info.get('umbral_descuento') or 10)
u_notif_stock = bool(u_info.get('notif_stock', True))
u_notif_resumen = bool(u_info.get('notif_resumen', False))

# Cierre total de LFI: jamás se permite leer rutas locales del servidor desde avatares (`allow_local=False`)
avatar_src = get_image_src(u_foto, allow_local=False, default_src=DEFAULT_AVATAR_SVG)

# Sanitización XSS estricta en todos los campos editables por el usuario
u_nombre_safe = escape_html(u_nombre) if u_nombre else "Usuario Registrado"
u_email_display = escape_html(u_email) if u_email else "<i style='opacity:0.6;'>Sin correo registrado</i>"
u_telefono_display = escape_html(u_telefono) if u_telefono else "<i style='opacity:0.6;'>Sin teléfono registrado</i>"
u_ubicacion_safe = escape_html(u_ubicacion)
u_bio_display = (
    escape_html(u_bio)
    if u_bio
    else "<i style='opacity:0.7;'>Aún no has agregado una biografía. Completa tus datos personales en la pestaña 'Editar Datos Personales'.</i>"
)

if u_email and u_alerta:
    badge_alerta = f"<span style='background: {'rgba(34, 197, 94, 0.15)' if is_dark else '#e8f5e9'}; color: {'#4ade80' if is_dark else '#2e7d32'}; border: 1px solid {'rgba(74, 222, 128, 0.35)' if is_dark else 'rgba(46, 125, 50, 0.3)'}; font-size: 0.78rem; font-weight: 700; padding: 5px 12px; border-radius: 6px;'>{svg_bell_active} ALERTAS ACTIVADAS ({u_umbral}%)</span>"
elif u_email and not u_alerta:
    badge_alerta = f"<span style='background: {btn_border}; color: {subtext_color}; font-size: 0.78rem; font-weight: 600; padding: 5px 12px; border-radius: 6px;'>{svg_bell_off} ALERTAS DESACTIVADAS</span>"
else:
    badge_alerta = f"<span style='background: {btn_border}; color: {subtext_color}; font-size: 0.78rem; font-weight: 600; padding: 5px 12px; border-radius: 6px;'>{svg_bell_off} AGREGA UN CORREO PARA ALERTAS</span>"


# =============================================================================
# BLOQUE 4: TARJETA DE PERFIL Y SUBIDA SEGURA DE AVATAR EN LA NUBE
# =============================================================================
st.markdown('<div class="profile-card-container">', unsafe_allow_html=True)
col_av, col_details = st.columns([1.5, 8.5], vertical_alignment="center")

with col_av:
    st.markdown(clean_html(f'''
    <div class="avatar-click-zone" title="Haz clic aquí para seleccionar y cambiar tu foto de perfil o GIF desde tu PC">
        <img src="{avatar_src}" class="profile-avatar-img" alt="{u_nombre_safe}">
        <div class="avatar-overlay-badge">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg>
            <span style="font-size: 0.7rem; font-weight: 700; margin-top: 2px;">Cambiar</span>
        </div>
    </div>
    '''), unsafe_allow_html=True)

    quick_file = st.file_uploader(
        "Subir Foto",
        type=["png", "jpg", "jpeg", "gif", "webp"],
        key="avatar_quick_uploader",
        label_visibility="collapsed",
    )

    if quick_file is not None:
        bytes_data = quick_file.getvalue()
        file_digest = hashlib.sha256(bytes_data).hexdigest()
        if st.session_state.get("_last_quick_avatar_digest") != file_digest:
            st.session_state["_last_quick_avatar_digest"] = file_digest
            ok_up, url_or_err = subir_avatar_usuario(u_ident, bytes_data, quick_file.type or "")
            if ok_up:
                ok_db, msg_db = actualizar_perfil_usuario(
                    u_ident,
                    nombre=u_nombre or "Usuario",
                    email=u_email,
                    telefono=u_telefono,
                    bio=u_bio,
                    foto_perfil=url_or_err,
                    ubicacion=u_ubicacion,
                )
                if ok_db:
                    st.session_state['user_info']['foto_perfil'] = url_or_err
                    st.toast("¡Foto de perfil guardada de forma persistente!", icon="✅")
                    st.rerun()
                else:
                    st.error(msg_db)
            else:
                st.error(url_or_err)

with col_details:
    st.markdown(clean_html(f'''
    <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 10px;">
        <div>
            <h2 style="margin: 0 0 4px 0; color: {text_color}; font-size: 1.5rem; font-weight: 700;">{u_nombre_safe}</h2>
            <div style="color: {subtext_color}; font-size: 0.9rem; margin-bottom: 8px; display: flex; align-items: center; flex-wrap: wrap;">
                {svg_mail} <span>{u_email_display}</span> &nbsp;&bull;&nbsp; {svg_phone} <span>{u_telefono_display}</span>
                &nbsp;&bull;&nbsp; <span style="margin-left: 4px;">📍 {u_ubicacion_safe}</span>
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
# BLOQUE 5: GESTIÓN PERSISTENTE DE FAVORITOS, PERFIL Y ALERTAS EN LA NUBE
# =============================================================================
tab_favs, tab_edit, tab_notif = st.tabs([
    "Fragancias Monitoreadas",
    "Editar Datos Personales",
    "Configuración de Alertas",
])

# --- TAB 1: FRAGANCIAS FAVORITAS PERSISTENTES ---
with tab_favs:
    svg_heart_header = f'<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#d83737" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: -3px; margin-right: 8px;"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>'
    st.markdown(f"<h3 style='display: flex; align-items: center;'>{svg_heart_header} Mis Fragancias Favoritas</h3>", unsafe_allow_html=True)
    st.caption("Tus fragancias guardadas se sincronizan con tu cuenta y comparan el mejor precio vigente en Chile frente al valor que tenían cuando iniciaste el seguimiento.")

    fav_items = obtener_favoritos_usuario(u_ident) if u_ident else []
    st.session_state['favoritos'] = [int(it['id']) for it in fav_items if it.get('id')]

    if not fav_items:
        st.info("Aún no tienes fragancias guardadas en tu seguimiento. Explora el catálogo o el comparador y pulsa 'Guardar y Monitorear Baja de Precio'.")
        if st.button("Ir al Catálogo de Perfumes", key="btn_go_catalog"):
            st.switch_page("app.py")
    else:
        for item in fav_items:
            p_id = int(item['id'])
            p_nombre_safe = escape_html(item.get('nombre', 'Perfume'))
            p_marca_safe = escape_html(item.get('marca', 'Marca'))
            p_min = item.get('mejor_precio_actual') or item.get('mejor_precio')
            p_guardado = int(item.get('precio_guardado') or 0)
            baja_detectada = bool(item.get('baja_detectada'))
            pct_desc = float(item.get('porcentaje_descuento') or 0.0)

            if p_min and p_min > 0:
                if baja_detectada and pct_desc > 0:
                    badge_precio = (
                        f"<span style='color: {'#4ade80' if is_dark else '#2e7d32'}; font-weight: 700;'>"
                        f"{svg_trend_down} ¡Bajó {pct_desc:.0f}%! ${p_min:,.0f} CLP</span>"
                        f"<br><span style='font-size:0.78rem; color:{subtext_color};'>Guardado en ${p_guardado:,.0f} CLP</span>"
                    ).replace(",", ".")
                else:
                    sub_guardado = (
                        f"<br><span style='font-size:0.78rem; color:{subtext_color};'>Base monitoreada: ${p_guardado:,.0f} CLP</span>".replace(",", ".")
                        if p_guardado > 0 else ""
                    )
                    badge_precio = f"<span style='color: {text_color}; font-weight: 600;'>Mejor precio: ${p_min:,.0f} CLP</span>".replace(",", ".") + sub_guardado
            else:
                badge_precio = f"<span style='color: {subtext_color}; font-weight: 600;'>Temporalmente agotado en tiendas</span>"

            col_f1, col_f2, col_f3, col_f4 = st.columns([3, 2.5, 2, 1.5], vertical_alignment="center")
            with col_f1:
                st.markdown(f"**{p_nombre_safe}**  \n<span style='color:{subtext_color}; font-size:0.85rem;'>{p_marca_safe}</span>", unsafe_allow_html=True)
            with col_f2:
                st.markdown(badge_precio, unsafe_allow_html=True)
            with col_f3:
                if st.button("Comparar Precios", key=f"btn_comp_fav_{p_id}", use_container_width=True):
                    st.session_state['selected_perfume'] = p_id
                    st.switch_page("pages/compararprecios.py")
            with col_f4:
                if st.button("Quitar", key=f"btn_rem_fav_{p_id}", use_container_width=True):
                    eliminar_favorito(u_ident, p_id)
                    st.session_state['favoritos'] = [fid for fid in st.session_state.get('favoritos', []) if fid != p_id]
                    st.toast("Fragancia retirada de tus favoritos.", icon="🗑️")
                    st.rerun()

# --- TAB 2: EDITAR PERFIL Y SUBIR FOTO/GIF ---
with tab_edit:
    svg_edit_header = f'<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="{text_color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: -3px; margin-right: 8px;"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>'
    st.markdown(f"<h3 style='display: flex; align-items: center;'>{svg_edit_header} Completar y Modificar Datos Personales</h3>", unsafe_allow_html=True)

    with st.form("form_edit_user_profile"):
        col_e1, col_e2 = st.columns(2, gap="medium")

        with col_e1:
            e_nombre = st.text_input("Nombre completo / Nickname", value=u_nombre, placeholder="Ej: Carlos Mendoza", max_chars=80)
            e_email = st.text_input("Correo Electrónico", value=u_email, placeholder="ejemplo@correo.cl", max_chars=120)
            e_telefono = st.text_input("Número de Teléfono", value=u_telefono, placeholder="+56 9 1234 5678", max_chars=30)
            e_ubicacion = st.text_input("Ciudad / Región", value=u_ubicacion, placeholder="Santiago, Chile", max_chars=80)

        with col_e2:
            uploaded_file = st.file_uploader(
                "Seleccionar foto o GIF desde PC (máx. 2 MB)",
                type=["png", "jpg", "jpeg", "gif", "webp"],
                help="Se valida y almacena de forma segura en la nube",
            )
            e_foto_url = st.text_input(
                "O ingresar URL pública HTTPS de imagen/GIF",
                value=u_foto if u_foto.startswith("https://") else "",
                placeholder="https://sitio.com/mi-foto.jpg",
                help="Por seguridad solo se aceptan enlaces externos con HTTPS",
            )
            e_bio = st.text_area(
                "Biografía / Notas Olfativas Preferidas",
                value=u_bio,
                placeholder="Escribe un breve resumen sobre ti o tus familias olfativas favoritas...",
                max_chars=280,
                height=100,
            )

        btn_save = st.form_submit_button("Guardar Cambios de Perfil", use_container_width=True)

        if btn_save:
            nueva_foto = u_foto
            error_validacion = None

            if uploaded_file is not None:
                ok_up, res_up = subir_avatar_usuario(u_ident, uploaded_file.getvalue(), uploaded_file.type or "")
                if ok_up:
                    nueva_foto = res_up
                else:
                    error_validacion = res_up
            elif e_foto_url.strip():
                if is_valid_https_image_url(e_foto_url.strip()):
                    nueva_foto = e_foto_url.strip()
                else:
                    error_validacion = "La URL de imagen debe comenzar estrictamente con https:// y ser válida."
            elif u_foto.startswith("https://") and not e_foto_url.strip():
                nueva_foto = ""

            if error_validacion:
                st.error(error_validacion)
            else:
                exito_upd, msg_upd = actualizar_perfil_usuario(
                    u_ident,
                    nombre=e_nombre,
                    email=e_email,
                    telefono=e_telefono,
                    bio=e_bio,
                    foto_perfil=nueva_foto,
                    ubicacion=e_ubicacion,
                )
                if exito_upd:
                    st.session_state['user_info'].update({
                        'nombre': e_nombre.strip(),
                        'email': e_email.strip().lower(),
                        'telefono': e_telefono.strip(),
                        'ubicacion': e_ubicacion.strip() or 'Santiago, Chile',
                        'bio': e_bio.strip(),
                        'foto_perfil': nueva_foto,
                    })
                    st.success(msg_upd)
                    st.rerun()
                else:
                    st.error(msg_upd)

# --- TAB 3: CONFIGURACIÓN DE NOTIFICACIONES Y ALERTAS ---
with tab_notif:
    svg_notif_header = f'<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="{text_color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: -3px; margin-right: 8px;"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>'
    st.markdown(f"<h3 style='display: flex; align-items: center;'>{svg_notif_header} Alertas Inteligentes por Correo Electrónico</h3>", unsafe_allow_html=True)
    st.write("Configura cuándo deseas recibir avisos automáticos cuando tus fragancias monitoreadas bajen de precio o recuperen stock en tiendas chilenas auditadas.")

    if not u_email:
        st.warning("Para activar notificaciones por correo electrónico, primero registra un correo válido en la pestaña 'Editar Datos Personales'.")

    with st.form("form_notif_settings"):
        alerta_check = st.checkbox(
            "Recibir alertas por correo electrónico cuando un perfume favorito baje de precio.",
            value=u_alerta,
            disabled=not bool(u_email),
        )

        umbral_val = st.slider(
            "Avisarme únicamente si la baja de precio es igual o mayor a:",
            min_value=5,
            max_value=50,
            value=max(5, min(50, int(u_umbral))),
            step=5,
            format="%d%%",
        )

        notif_stock_check = st.checkbox(
            "Notificarme cuando una fragancia agotada vuelva a tener stock verificado.",
            value=u_notif_stock,
            disabled=not bool(u_email),
        )

        notif_resumen_check = st.checkbox(
            "Recibir resumen semanal con las mayores liquidaciones verificadas en Chile.",
            value=u_notif_resumen,
            disabled=not bool(u_email),
        )

        btn_save_notif = st.form_submit_button("Guardar Preferencias de Alertas", use_container_width=True)

        if btn_save_notif:
            ok_pref, msg_pref = actualizar_preferencias_notificacion(
                u_ident,
                alerta_email=alerta_check,
                umbral_descuento=umbral_val,
                notif_stock=notif_stock_check,
                notif_resumen=notif_resumen_check,
            )
            if ok_pref:
                st.session_state['user_info'].update({
                    'alerta_email': alerta_check,
                    'umbral_descuento': umbral_val,
                    'notif_stock': notif_stock_check,
                    'notif_resumen': notif_resumen_check,
                })
                st.success(msg_pref)
                st.rerun()
            else:
                st.error(msg_pref)

# 6. PIE DE PÁGINA
st.markdown(f"<hr style='margin: 40px 0 20px 0; border: none; border-bottom: 1px solid {btn_border}; opacity: 0.3;'>", unsafe_allow_html=True)
st.markdown(f"""
    <div style="text-align: center; padding: 10px 0 20px 0; color: {subtext_color}; font-size: 0.85rem;">
        © 2026 Perfume Trending. Todos los derechos reservados.
    </div>
""", unsafe_allow_html=True)
