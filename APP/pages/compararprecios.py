"""
PerfumeTrending.cl — Página de Comparador de Precios y Detalle de Fragancias
=============================================================================
Vista principal interactiva para comparar ofertas vigentes en tiempo real:
- Ficha técnica completa de la fragancia (marca, concentración, notas, familia olfativa).
- Comparativa en vivo de precios entre comercios chilenos auditados (Falabella, Paris, Ripley, Silk, Elite, etc.).
- Cálculo del precio por mililitro ($/ml) para comparar distintas presentaciones de volumen de manera justa.
- Visualización de la evolución histórica de precios mediante gráficos interactivos de series temporales.
- Gestión de favoritos y alertas de precio por usuario autenticado.
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

from backend.database import (
    agregar_favorito,
    eliminar_favorito,
    obtener_catalogo,
    obtener_detalle_perfume,
    obtener_favoritos_Ids_usuario,
    obtener_historico_precios,
    obtener_precios_actuales,
)
from backend.normalizador import es_precio_valido
from ui import (
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
    modal_autenticacion,
    resolver_url_oferta,
    sanitize_external_url,
    toggle_theme,
)


def clean_html(html_str: str) -> str:
    """Limpia espacios iniciales y saltos de línea para evitar bloques de código accidentales."""
    return _shared_clean_html(html_str, join_char=" ")


# =============================================================================
# BLOQUE 1: CACHÉ EN MEMORIA DE ALTO RENDIMIENTO (STREAMLIT CACHE DATA)
# =============================================================================
@st.cache_data(ttl=120, show_spinner=False)
def get_cached_catalogo():
    """Retorna el catálogo consolidado desde la capa de datos con caché de 2 minutos."""
    return obtener_catalogo()


@st.cache_data(ttl=120, show_spinner=False)
def get_cached_precios(perfume_id):
    """Consulta los precios vigentes en cada tienda para el perfume seleccionado."""
    return obtener_precios_actuales(perfume_id)


@st.cache_data(ttl=120, show_spinner=False)
def get_cached_historico(perfume_id, volumen_ml=None):
    """Consulta la serie de tiempo de precios históricos filtrada por presentación."""
    return obtener_historico_precios(perfume_id, volumen_ml=volumen_ml)


@st.cache_data(ttl=120, show_spinner=False)
def get_cached_detalle(perfume_id):
    """Retorna la ficha técnica completa del perfume (notas, género, concentración)."""
    return obtener_detalle_perfume(perfume_id)


# =============================================================================
# BLOQUE 2: CONFIGURACIÓN DE LA PÁGINA Y GESTIÓN DE SESIÓN
# =============================================================================
st.set_page_config(
    page_title="Comparador de Precios - PerfumeTrending",
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
settings_icon_svg = pal.settings_icon_svg
logout_icon_svg = pal.logout_icon_svg
logo_svg_data = pal.logo_svg_data

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

    /* BOTONES GENERALES DE ESTILO SOBRIO */
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

    /* 1. Trend Del Hype */
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

    /* 2. Páginas de Confianza */
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

    /* 3. Comparar Precios */
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

    /* 4. Inicio / Catálogo */
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

    /* TARJETA CABECERA DEL PERFUME */
    .perfume-header-card {{
        background-color: {btn_bg};
        border: 1px solid {btn_border};
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 24px;
        display: flex;
        gap: 24px;
        align-items: center;
    }}

    .perfume-header-img {{
        width: 130px;
        height: 130px;
        object-fit: contain;
        background: { "#14171d" if is_dark else "#ffffff" };
        border: 1px solid {btn_border};
        border-radius: 8px;
        padding: 8px;
    }}

    /* TARJETAS DE COMPARACIÓN DE PRECIOS */
    .price-card {{
        background-color: {btn_bg};
        border: 1px solid {btn_border};
        border-radius: 10px;
        padding: 16px 20px;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }}
    .price-card:hover {{
        transform: translateY(-2px);
        border-color: #d4c2a5;
    }}
    .best-deal {{
        border: 1px solid { "rgba(74, 222, 128, 0.45)" if is_dark else "rgba(46, 125, 50, 0.4)" } !important;
        background-color: { "rgba(34, 197, 94, 0.08)" if is_dark else "rgba(46, 125, 50, 0.06)" } !important;
        box-shadow: { "0 0 16px rgba(34, 197, 94, 0.08)" if is_dark else "0 2px 8px rgba(46, 125, 50, 0.06)" };
    }}
    .store-name {{
        font-size: 1.1rem;
        font-weight: 700;
        color: {text_color};
    }}
    .store-badge {{
        font-size: 0.75rem;
        padding: 2px 8px;
        border-radius: 4px;
        background-color: {btn_border};
        color: {text_color};
        margin-left: 8px;
    }}
    .price-value {{
        font-size: 1.25rem;
        font-weight: 800;
        color: {text_color};
    }}
    .old-price {{
        font-size: 0.85rem;
        text-decoration: line-through;
        color: {subtext_color};
        margin-right: 8px;
    }}
    .buy-btn {{
        background-color: #8c7b6d;
        color: #ffffff !important;
        padding: 8px 16px;
        border-radius: 6px;
        text-decoration: none;
        font-weight: 600;
        font-size: 0.85rem;
        display: inline-block;
        transition: background-color 0.2s ease;
    }}
    .buy-btn:hover {{
        background-color: #726255;
    }}

    /* TARJETAS DE OFERTAS AGOTADAS (EN EL FONDO/AL FINAL) */
    .price-card.out-of-stock {{
        opacity: 0.68;
        background-color: { "rgba(22, 24, 30, 0.55)" if is_dark else "rgba(244, 244, 246, 0.75)" } !important;
        border-color: { "rgba(255, 255, 255, 0.05)" if is_dark else "rgba(0, 0, 0, 0.06)" } !important;
        filter: grayscale(12%);
    }}
    .price-card.out-of-stock:hover {{
        opacity: 0.9;
        transform: translateY(-1px);
        filter: grayscale(0%);
        border-color: { "rgba(248, 113, 113, 0.35)" if is_dark else "rgba(220, 38, 38, 0.25)" } !important;
    }}

    /* SELECTOR DE PRESENTACIÓN ESTILO FALABELLA */
    div[data-testid="stPills"] {{
        gap: 8px !important;
        margin-top: 4px !important;
        margin-bottom: 16px !important;
    }}
    div[data-testid="stPills"] button {{
        border-radius: 8px !important;
        border: 1px solid {btn_border} !important;
        background-color: {btn_bg} !important;
        color: {text_color} !important;
        font-weight: 600 !important;
        font-size: 0.86rem !important;
        letter-spacing: 0.3px !important;
        padding: 6px 16px !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }}
    div[data-testid="stPills"] button:hover {{
        border-color: { "#d4c2a5" if is_dark else "#8c7b6d" } !important;
        transform: translateY(-1px) !important;
    }}
    div[data-testid="stPills"] button[aria-checked="true"],
    div[data-testid="stPills"] button[data-selected="true"] {{
        background-color: { "#282c37" if is_dark else "#ede6dc" } !important;
        border-color: { "#e2d5c4" if is_dark else "#8c7b6d" } !important;
        color: { "#ffffff" if is_dark else "#111827" } !important;
        box-shadow: 0 0 10px { "rgba(226, 213, 196, 0.25)" if is_dark else "rgba(140, 123, 109, 0.2)" } !important;
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
                cerrar_sesion_usuario()
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
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

# 5. SECCIÓN PRINCIPAL: COMPARADOR DE PRECIOS
# =============================================================================
# BLOQUE 4: SELECCIÓN DEL PERFUME Y FICHA TÉCNICA OLFATIVA
# -----------------------------------------------------------------------------
# ¿QUÉ HACE ESTE BLOQUE?
# 1. Carga el catálogo mediante la función cacheada `get_cached_catalogo()`.
# 2. Revisa si en `st.session_state['selected_perfume']` viene un perfume preseleccionado
#    desde la página principal o desde el banner de tendencias, marcándolo por defecto.
# 3. Presenta un desplegable `st.selectbox` con búsqueda difusa en vivo.
# 4. Muestra la cabecera del perfume con su imagen oficial, concentración (EDP/EDT),
#    género (Hombre/Mujer/Unisex), notas de salida/corazón/fondo y precio de referencia.
# =============================================================================
col_title_text, col_title_back = st.columns([7, 3], vertical_alignment="center")
with col_title_text:
    st.markdown(f"""<div style='color: {text_color}; letter-spacing: 1.5px; font-weight: 300; font-size: 1.1rem; text-transform: uppercase;'>COMPARADOR DE PRECIOS EN TIENDAS CHILENAS</div>""", unsafe_allow_html=True)
with col_title_back:
    st.page_link("app.py", label="← Volver al Catálogo")

# Cargar catálogo dinámico con caché en memoria
catalogo = get_cached_catalogo()

if not catalogo:
    st.warning("No hay perfumes disponibles en el catálogo en este momento.")
    st.stop()

# Diccionario de mapeo rápido sin colisiones entre concentraciones (EDT/EDP/Parfum) ni géneros (Hombre/Mujer)
opciones_perfumes = {}
for p in catalogo:
    tipo_lbl = (p.get("tipo") or "Eau de Parfum").strip()
    gen_lbl = (p.get("genero") or "Unisex").strip()
    base_lbl = f"{p['nombre']} — {p['marca']} ({tipo_lbl} · {gen_lbl})"
    lbl_final = base_lbl if base_lbl not in opciones_perfumes else f"{base_lbl} [#{p['id']}]"
    opciones_perfumes[lbl_final] = p

lista_nombres = list(opciones_perfumes.keys())

# Determinar perfume pre-seleccionado desde sesión (dict, id o nombre) o desde query param compartible (?id=)
default_index = 0
selected_session = st.session_state.get("selected_perfume")
qp_id = st.query_params.get("id")

target_id = None
if isinstance(selected_session, dict) and selected_session.get("id") is not None:
    target_id = str(selected_session.get("id"))
elif selected_session is not None and str(selected_session).isdigit():
    target_id = str(selected_session)
elif qp_id and str(qp_id).isdigit():
    target_id = str(qp_id)

if target_id is not None:
    for idx, (_, p) in enumerate(opciones_perfumes.items()):
        if str(p["id"]) == target_id:
            default_index = idx
            break
elif isinstance(selected_session, str) and selected_session.strip():
    term_sel = selected_session.strip().lower()
    for idx, (_, p) in enumerate(opciones_perfumes.items()):
        if term_sel in p["nombre"].lower():
            default_index = idx
            break

selected_label = st.selectbox("Selecciona un perfume para comparar ofertas en Chile:", lista_nombres, index=default_index)
perfume = opciones_perfumes[selected_label]
selected_id = perfume["id"]
st.session_state["selected_perfume"] = selected_id
try:
    if st.query_params.get("id") != str(selected_id):
        st.query_params["id"] = str(selected_id)
except Exception:
    pass

# Obtener detalle enriquecido desde caché
detalle = get_cached_detalle(selected_id) or perfume

# Mostrar ficha cabecera del perfume con packshot de alta resolución y sanitización XSS
img_src = get_image_src(detalle.get('imagen_url'))
nombre_safe = escape_html(detalle.get('nombre', ''))
marca_safe = escape_html(detalle.get('marca', ''))
notas_safe = escape_html(detalle.get('notas') or 'Notas olfativas exclusivas')
genero_safe = escape_html(detalle.get('genero') or 'Unisex')
tipo_safe = escape_html(detalle.get('tipo') or 'Eau de Parfum')

col_img, col_info = st.columns([1, 3], gap="medium")
with col_img:
    st.markdown(f"""
    <div style="background: #ffffff; border-radius: 12px; padding: 12px; display: flex; align-items: center; justify-content: center; border: 1px solid {btn_border};">
        <img src="{img_src}" alt="{nombre_safe}" style="max-height: 180px; max-width: 100%; object-fit: contain;">
    </div>
    """, unsafe_allow_html=True)

with col_info:
    ref_precio = detalle.get('precio_referencia')
    if not es_precio_valido(ref_precio):
        ref_precio = None
    ref_str = f"${ref_precio:,.0f} CLP".replace(",", ".") if ref_precio else "Consultar"

    st.markdown(f"""
    <div style="padding-top: 4px;">
        <h2 style="margin: 0 0 6px 0; color: {text_color}; font-size: 1.6rem; font-weight: 700;">{nombre_safe}</h2>
        <div style="color: {subtext_color}; font-size: 0.95rem; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 1px;">
            {marca_safe} &bull; {tipo_safe} &bull; {genero_safe}
        </div>
        <p style="margin: 0 0 8px 0; color: {text_color}; font-size: 0.9rem; line-height: 1.5;">
            <b>Notas olfativas:</b> {notas_safe}
        </p>
        <div style="margin-top: 10px; display: flex; gap: 16px; align-items: center; flex-wrap: wrap;">
            <span style="font-size: 0.85rem; color: {subtext_color};">Precio referencial de mercado: <b style="color: {text_color};">{ref_str}</b></span>
            <span style="background-color: #2e7d3222; color: #4caf50; font-size: 0.78rem; font-weight: 700; padding: 3px 8px; border-radius: 4px; border: 1px solid #4caf5044;">DISPONIBLE EN TIENDAS AUDITADAS</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Botón persistente de Favoritos y Monitoreo de Alertas conectado a Supabase Auth / SQLite
    favs_actuales = st.session_state.get('favoritos') or []
    if st.session_state.get('logged_in') and st.session_state.get('user_info') and not favs_actuales:
        u_key_fav = st.session_state['user_info'].get('id') or st.session_state['user_info'].get('email')
        if u_key_fav:
            favs_actuales = obtener_favoritos_Ids_usuario(u_key_fav, email=st.session_state['user_info'].get('email'))
            st.session_state['favoritos'] = favs_actuales

    ya_es_favorito = int(selected_id) in [int(x) for x in favs_actuales if str(x).isdigit()]
    col_fav_btn, _ = st.columns([1.8, 3.2])
    with col_fav_btn:
        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
        lbl_fav = "★ En tu Seguimiento (Quitar)" if ya_es_favorito else "☆ Guardar y Monitorear Baja de Precio"
        if st.button(lbl_fav, key=f"btn_toggle_fav_{selected_id}", use_container_width=True):
            if not st.session_state.get('logged_in') or not st.session_state.get('user_info'):
                st.session_state['show_login_modal'] = True
                st.rerun()
            else:
                u_ident = st.session_state['user_info'].get('id') or st.session_state['user_info'].get('email')
                if ya_es_favorito:
                    eliminar_favorito(u_ident, int(selected_id))
                    st.session_state['favoritos'] = [x for x in favs_actuales if int(x) != int(selected_id)]
                    st.toast("Fragancia retirada de tu seguimiento.", icon="🗑️")
                else:
                    agregar_favorito(u_ident, int(selected_id))
                    st.session_state['favoritos'] = list(set(favs_actuales + [int(selected_id)]))
                    st.toast("Fragancia guardada en tu seguimiento de precios.", icon="⭐")
                st.rerun()

st.markdown("<div style='margin-top: 24px;'></div>", unsafe_allow_html=True)
st.markdown(f"<h3 style='font-size: 1.15rem; color: {text_color}; font-weight: 600; margin-bottom: 16px;'>Ofertas en tiendas chilenas verificadas</h3>", unsafe_allow_html=True)


# =============================================================================
# BLOQUE 5: COMPARATIVA EN VIVO, CÁLCULO $/ML Y BADGE "MEJOR PRECIO"
# -----------------------------------------------------------------------------
# ¿QUÉ HACE ESTE BLOQUE?
# 1. Consulta las ofertas en stock en comercios chilenos (Falabella, Paris, Ripley, Silk, etc.).
# 2. Algoritmo de detección del mejor precio:
#    - Filtra los precios válidos mayores a 0.
#    - Encuentra el valor mínimo (`min_precio`).
#    - A la tienda ganadora le asigna la clase CSS `.best-deal` con borde verde brillante
#      y el distintivo "MEJOR PRECIO".
# 3. Métricas de valor real:
#    - Calcula el precio por mililitro: `precio_por_ml = precio_actual / volumen_ml`.
#      Esto permite que el usuario compare ofertas de 50ml vs 100ml de forma transparente.
# 4. Enlace de compra verificado con `resolver_url_oferta()`.
# =============================================================================
tiendas_db = get_cached_precios(selected_id)
if tiendas_db:
    tiendas_db = [t for t in tiendas_db if es_precio_valido(t.get('precio_actual'))]

if not tiendas_db:
    st.info("Actualmente estamos sincronizando los precios en tiempo real para esta fragancia.")
else:
    def extraer_volumen(item):
        try:
            val = item.get('volumen_ml')
            if val is not None and float(val) > 0:
                return int(round(float(val)))
        except Exception:
            pass
        return 100

    def esta_en_stock(item):
        val = item.get('en_stock')
        if val is None:
            return True
        if isinstance(val, str):
            return val.lower() not in ('false', '0', 'agotado', 'f', 'no')
        return bool(val)

    # 1. Obtener todas las presentaciones de volumen (ml) disponibles para la fragancia
    vols_disponibles = sorted(list({extraer_volumen(t) for t in tiendas_db}))
    key_filtro = f"filtro_vol_{selected_id}"

    # 2. Selector de presentación estilo Falabella ("Elige una opción:")
    if vols_disponibles:
        opciones_vol = ["Todos"] + [f"{v} ML" for v in vols_disponibles]
        
        sel_guardada = st.session_state.get(key_filtro, "Todos")
        default_val = sel_guardada if sel_guardada in opciones_vol else "Todos"

        # Pre-filtrar temporalmente para obtener métricas de stock antes de renderizar el selector
        if sel_guardada and sel_guardada != "Todos":
            try:
                v_num_pre = int(sel_guardada.upper().replace("ML", "").strip())
                pre_filtradas = [t for t in tiendas_db if extraer_volumen(t) == v_num_pre]
            except Exception:
                pre_filtradas = list(tiendas_db)
        else:
            pre_filtradas = list(tiendas_db)

        if not pre_filtradas:
            pre_filtradas = list(tiendas_db)

        hay_stock_pre = any(esta_en_stock(t) for t in pre_filtradas)
        if hay_stock_pre:
            indicador_stock = f"<span style='color: {'#4ade80' if is_dark else '#2e7d32'}; font-size: 0.8rem; font-weight: 600; display: inline-flex; align-items: center; gap: 5px;'><span style='width: 7px; height: 7px; border-radius: 50%; background-color: {'#4ade80' if is_dark else '#2e7d32'};'></span> En stock</span>"
        else:
            indicador_stock = f"<span style='color: {'#f87171' if is_dark else '#dc2626'}; font-size: 0.8rem; font-weight: 600; display: inline-flex; align-items: center; gap: 5px;'><span style='width: 7px; height: 7px; border-radius: 50%; background-color: {'#f87171' if is_dark else '#dc2626'};'></span> Agotado en tiendas</span>"

        st.markdown(
            f"""
            <div style="margin: 0 0 6px 0; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="font-size: 0.95rem; font-weight: 700; color: {text_color}; letter-spacing: 0.3px;">
                        Elige una opción:
                    </span>
                    {indicador_stock}
                </div>
                <span style="font-size: 0.78rem; color: {subtext_color};">
                    Mostrando {len(pre_filtradas)} oferta{'s' if len(pre_filtradas) != 1 else ''} &bull; Ordenadas por precio (disponibles primero)
                </span>
            </div>
            """,
            unsafe_allow_html=True
        )

        seleccion_vol = st.pills(
            "Elige una opción (ml):",
            options=opciones_vol,
            default=default_val,
            key=key_filtro,
            label_visibility="collapsed"
        )
        if not seleccion_vol:
            seleccion_vol = "Todos"

        if seleccion_vol != "Todos":
            try:
                vol_num = int(seleccion_vol.upper().replace("ML", "").strip())
                tiendas_filtradas = [t for t in tiendas_db if extraer_volumen(t) == vol_num]
            except Exception:
                tiendas_filtradas = list(tiendas_db)
        else:
            tiendas_filtradas = list(tiendas_db)
    else:
        seleccion_vol = "Todos"
        tiendas_filtradas = list(tiendas_db)

    if not tiendas_filtradas:
        tiendas_filtradas = list(tiendas_db)

    # 3. Ordenamiento inteligente estricto:
    #    - Primero: ofertas con stock disponible (en_stock == True), priorizando formato regular a igual precio.
    #    - Al final: ofertas agotadas (en_stock == False), ordenadas de menor a mayor precio.
    def es_tester_item(it):
        return str(it.get('formato') or '').lower() == 'tester' or 'tester' in str(it.get('url_producto') or '').lower()

    tiendas_ordenadas = sorted(
        tiendas_filtradas,
        key=lambda x: (
            0 if esta_en_stock(x) else 1,
            x.get('precio_actual', 0) if x.get('precio_actual', 0) > 0 else 999999999,
            1 if es_tester_item(x) else 0,
        )
    )

    # 4. Identificar el mejor precio priorizando botellas selladas ('regular') cuando existe stock regular
    precios_regular_stock = [
        t['precio_actual']
        for t in tiendas_filtradas
        if t.get('precio_actual', 0) > 0 and esta_en_stock(t) and not es_tester_item(t)
    ]
    precios_validos = [
        t['precio_actual']
        for t in tiendas_filtradas
        if t.get('precio_actual', 0) > 0 and esta_en_stock(t)
    ]
    hay_regular_en_stock = len(precios_regular_stock) > 0
    min_precio = min(precios_regular_stock) if hay_regular_en_stock else (min(precios_validos) if precios_validos else 0)

    total_agotados = len([t for t in tiendas_ordenadas if not esta_en_stock(t)])
    total_disponibles = len(tiendas_ordenadas) - total_agotados

    if not precios_validos:
        st.markdown(
            f"""
            <div style="background-color: {'rgba(239, 68, 68, 0.1)' if is_dark else '#fef2f2'}; border: 1px solid {'rgba(239, 68, 68, 0.25)' if is_dark else '#fecaca'}; border-radius: 8px; padding: 10px 14px; margin: 4px 0 16px 0; display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 1.05rem;">🔴</span>
                <span style="font-size: 0.85rem; color: {'#f87171' if is_dark else '#dc2626'}; font-weight: 600;">
                    Presentación sin stock disponible en este momento. Mostrando últimos precios de referencia abajo.
                </span>
            </div>
            """,
            unsafe_allow_html=True
        )

    # 5. Renderizado de tarjetas con separador antes de los agotados y distintivo TESTER transparente
    separador_mostrado = False

    for item in tiendas_ordenadas:
        p_act = item.get('precio_actual', 0)
        p_norm = item.get('precio_normal', 0)
        vol_ml = extraer_volumen(item)
        en_stock = esta_en_stock(item)
        es_tester = es_tester_item(item)
        is_best_deal = (
            p_act == min_precio
            and p_act > 0
            and en_stock
            and (not es_tester if hay_regular_en_stock else True)
        )

        # Si pasamos a las ofertas agotadas y habían ofertas en stock, mostrar separador al final
        if not en_stock and not separador_mostrado and total_disponibles > 0:
            separador_mostrado = True
            st.markdown(
                f"""
                <div style="margin: 24px 0 14px 0; display: flex; align-items: center; gap: 12px;">
                    <span style="font-size: 0.78rem; font-weight: 700; color: {subtext_color}; text-transform: uppercase; letter-spacing: 0.8px;">
                        Tiendas sin stock ({total_agotados})
                    </span>
                    <div style="flex: 1; height: 1px; background-color: {btn_border};"></div>
                </div>
                """,
                unsafe_allow_html=True
            )

        card_class = "price-card best-deal" if is_best_deal else ("price-card" if en_stock else "price-card out-of-stock")

        if is_best_deal:
            lbl_best = "MEJOR PRECIO TESTER" if es_tester else "MEJOR PRECIO"
            status_badge = f"<span style='background: {'rgba(34, 197, 94, 0.15)' if is_dark else '#e8f5e9'}; color: {'#4ade80' if is_dark else '#2e7d32'}; border: 1px solid {'rgba(74, 222, 128, 0.35)' if is_dark else 'rgba(46, 125, 50, 0.3)'}; font-weight: 700; margin-left: 8px; font-size: 0.72rem; padding: 2px 8px; border-radius: 4px; letter-spacing: 0.5px;'>{lbl_best}</span>"
        elif not en_stock:
            status_badge = f"<span style='background: {'rgba(239, 68, 68, 0.15)' if is_dark else '#fee2e2'}; color: {'#f87171' if is_dark else '#dc2626'}; border: 1px solid {'rgba(248, 113, 113, 0.35)' if is_dark else 'rgba(220, 38, 38, 0.3)'}; font-weight: 700; margin-left: 8px; font-size: 0.72rem; padding: 2px 8px; border-radius: 4px; letter-spacing: 0.5px;'>AGOTADO</span>"
        else:
            status_badge = ""

        badge_tester = (
            f"<span title='Unidad Tester de demostración comercial (puede venir en caja neutra o sin celofán)' "
            f"style='background: {'rgba(245, 158, 11, 0.16)' if is_dark else '#fef3c7'}; "
            f"color: {'#fbbf24' if is_dark else '#b45309'}; "
            f"border: 1px solid {'rgba(251, 191, 36, 0.4)' if is_dark else 'rgba(180, 83, 9, 0.3)'}; "
            f"font-weight: 700; margin-left: 8px; font-size: 0.72rem; padding: 2px 8px; border-radius: 4px; letter-spacing: 0.5px;'>TESTER</span>"
            if es_tester else ""
        )

        precio_actual_str = f"${p_act:,.0f}".replace(",", ".")
        precio_ant_str = f"${p_norm:,.0f}".replace(",", ".") if p_norm and p_norm > p_act else ""
        old_price_html = f"<span class='old-price'>{precio_ant_str}</span>" if (precio_ant_str and en_stock) else ""

        ml_txt = ""
        if p_act > 0 and vol_ml > 0 and en_stock:
            p_ml = int(round(p_act / vol_ml))
            ml_txt = f"<span style='font-size: 0.78rem; color: {subtext_color}; display: block; text-align: right;'>${p_ml:,.0f}/ml ({vol_ml}ml)</span>".replace(",", ".")

        url_directa = sanitize_external_url(
            resolver_url_oferta(
                tienda_nombre=item.get('tienda_nombre', ''),
                perfume_nombre=detalle.get('nombre', ''),
                url_prod=item.get('url_producto', ''),
                url_base=item.get('url_base', ''),
                marca=detalle.get('marca', '')
            )
        )
        tienda_safe = escape_html(item.get('tienda_nombre', 'Tienda'))
        badge_tienda_safe = escape_html(item.get('badge', 'Tienda Verificada'))
        badge_vol = f"<span class='store-badge' style='background: {btn_bg}; border: 1px solid {btn_border}; font-weight: 600;'>{vol_ml}ml</span>" if vol_ml else ""

        if not en_stock:
            price_display_html = f"""
            <div style="text-align: right;">
                <span style="font-size: 1.12rem; font-weight: 700; color: {'#ef4444' if is_dark else '#dc2626'}; letter-spacing: 0.5px;">AGOTADO</span>
                <span style="display: block; font-size: 0.8rem; color: {subtext_color}; text-decoration: line-through;">{precio_actual_str} CLP</span>
            </div>
            """
            btn_label = "Ver en tienda (Agotado) ↗"
            btn_extra_style = "opacity: 0.65; filter: grayscale(30%);"
        else:
            price_display_html = f"""
            <div style="text-align: right;">
                {old_price_html}
                <span class="price-value">{precio_actual_str} CLP</span>
                {ml_txt}
            </div>
            """
            btn_label = "Ir a la oferta ↗"
            btn_extra_style = ""

        html_card = f"""
        <div class="{card_class}">
            <div>
                <span class="store-name">{tienda_safe}</span>
                <span class="store-badge">{badge_tienda_safe}</span>
                {badge_vol}
                {badge_tester}
                {status_badge}
            </div>
            <div style="display: flex; align-items: center; gap: 16px;">
                {price_display_html}
                <a href="{url_directa}" class="buy-btn" style="{btn_extra_style}" target="_blank" rel="noopener noreferrer">{btn_label}</a>
            </div>
        </div>
        """
        st.markdown(clean_html(html_card), unsafe_allow_html=True)


# =============================================================================
# BLOQUE 6: GRÁFICO INTERACTIVO DE EVOLUCIÓN HISTÓRICA DE PRECIOS POR VOLUMEN
# =============================================================================
st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
vol_filtro_hist = None
if 'seleccion_vol' in locals() and seleccion_vol != "Todos":
    try:
        vol_filtro_hist = int(seleccion_vol.upper().replace("ML", "").strip())
    except Exception:
        vol_filtro_hist = None

titulo_hist = (
    f"Ver Evolución Histórica de Precios ({vol_filtro_hist} ML)"
    if vol_filtro_hist
    else "Ver Evolución Histórica de Precios en Tiendas Chilenas"
)
with st.expander(titulo_hist):
    historico = get_cached_historico(selected_id, volumen_ml=vol_filtro_hist)
    if historico:
        df_hist = pd.DataFrame(historico)
        if 'fecha_registro' in df_hist.columns and 'fecha' not in df_hist.columns:
            df_hist = df_hist.rename(columns={'fecha_registro': 'fecha'})
        if 'precio_actual' in df_hist.columns and 'precio' not in df_hist.columns:
            df_hist = df_hist.rename(columns={'precio_actual': 'precio'})

        if 'fecha' in df_hist.columns and 'precio' in df_hist.columns and 'tienda' in df_hist.columns:
            df_hist['fecha'] = pd.to_datetime(df_hist['fecha'], errors='coerce')
            df_hist = df_hist.dropna(subset=['fecha', 'precio'])
            if not df_hist.empty:
                df_pivot = df_hist.pivot_table(index='fecha', columns='tienda', values='precio', aggfunc='min')
                st.line_chart(df_pivot)
            else:
                st.caption("Aún no existen suficientes puntos temporales verificados para graficar esta presentación.")
        else:
            st.dataframe(df_hist, use_container_width=True)
    else:
        st.caption("Recopilando observaciones históricas verificadas en comercios chilenos para esta presentación.")
