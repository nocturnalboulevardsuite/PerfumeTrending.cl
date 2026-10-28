"""
PerfumeTrending.cl — Página de Remates, Liquidaciones y Descuentos Reales
========================================================================
Módulo de visualización y filtrado de ofertas con rebajas genuinas en el mercado:
- Algoritmo de detección de gangas: compara el precio_actual contra el precio_normal confirmado.
- Filtro estricto contra falsos descuentos: solo muestra ofertas con rebaja porcentual real demostrable.
- Indicadores visuales de porcentaje de ahorro y diferencia en pesos chilenos ($ CLP).
- Ordenamiento dinámico por mayor porcentaje de descuento o menor precio absoluto.
- Tarjetas de producto interactivas con acceso directo a la compra en el comercio respectivo.
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
    obtener_catalogo,
    obtener_remates_reales,
    obtener_tiendas,
)
from ui import (
    FLAME_RED_SVG as flame_red_svg,
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
    """Limpia espacios iniciales y elimina saltos de línea para evitar bloques de código accidentales."""
    return _shared_clean_html(html_str, join_char=" ")


@st.cache_data(ttl=120, show_spinner=False)
def get_cached_remates():
    return obtener_remates_reales(limite=60, descuento_min_pct=12)


# 1. CONFIGURACIÓN DE LA PÁGINA Y ESTADO COMPARTIDO
st.set_page_config(
    page_title="Remates y Liquidaciones Reales - PerfumeTrending",
    page_icon=PERFUME_SVG_FAVICON,
    layout="wide",
    initial_sidebar_state="collapsed",
)

init_common_session_state()
if 'selected_perfume' not in st.session_state:
    st.session_state['selected_perfume'] = None

pal = get_theme_palette()
is_dark = pal.is_dark
app_bg = pal.app_bg
app_bg_css = pal.app_bg_css
card_bg = pal.card_bg
border_color = pal.border_color
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

# 3. ENCABEZADO SUPERIOR: LOGO, PERFIL Y SWITCH DE TEMA
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
            
            # LINK DIRECTO A MI PERFIL Y ALERTAS
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
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#d83737" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
        </svg>
        <h1 style='color: {text_color}; font-size: 1.5rem; font-weight: 800; margin: 0; letter-spacing: 0.5px;'>REMATES DE ÚLTIMO MINUTO Y LIQUIDACIONES</h1>
    </div>
    <div style='color: {subtext_color}; font-size: 0.9rem; margin-top: 4px;'>
        Ofertas relámpago con stock limitado y descuentos excepcionales auditados en tiendas chilenas.
    </div>
    """, unsafe_allow_html=True)

with col_title_back:
    st.page_link("app.py", label="← Volver al Catálogo")

st.markdown("<div style='margin-top: 18px;'></div>", unsafe_allow_html=True)

# =============================================================================
# BLOQUE 3: FILTRADO MULTI-VARIABLE Y CONTROLES DE BÚSQUEDA
# -----------------------------------------------------------------------------
# ¿QUÉ HACE ESTE BLOQUE?
# Provee los controles superiores para refinar las ofertas de remate:
# 1. Campo de búsqueda de texto libre (coincidencia en perfume, diseñador o tienda).
# 2. Selector de ordenamiento:
#    - "Mayor % Descuento": Calcula la rebaja porcentual real y prioriza las mejores oportunidades.
#    - "Menor Precio": Ordena por el desembolso mínimo absoluto en pesos chilenos.
#    - "Mayor Precio": Perfumes de nicho o lujo con descuento.
# 3. Selector de comercio: Permite auditar ofertas por tienda específica (Falabella, Paris, Silk, etc.).
# =============================================================================
remates_data = get_cached_remates() or []

tiendas_unicas = sorted({str(r.get("tienda") or "").strip() for r in remates_data if r.get("tienda")})
if not tiendas_unicas:
    tiendas_unicas = [t["nombre"] for t in (obtener_tiendas() or []) if t.get("nombre")]

col_search, col_order, col_tienda = st.columns([4, 3, 3], gap="small", vertical_alignment="center")

with col_search:
    search_remate = st.text_input("Buscar remates...", placeholder="Filtrar por perfume, marca o tienda...", label_visibility="collapsed")

with col_order:
    orden_opt = st.selectbox("Ordenar por:", ["Mayor % Descuento", "Mayor Ahorro ($ CLP)", "Menor Precio", "Mayor Precio"], label_visibility="collapsed")

with col_tienda:
    tienda_opt = st.selectbox("Tienda:", ["Todas las tiendas"] + tiendas_unicas, label_visibility="collapsed")

st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)

items_filtrados = []
q_lower = (search_remate or "").strip().lower()
for item in remates_data:
    match_search = (
        not q_lower
        or q_lower in str(item.get("nombre") or "").lower()
        or q_lower in str(item.get("marca") or "").lower()
        or q_lower in str(item.get("tienda") or "").lower()
    )
    match_tienda = (tienda_opt == "Todas las tiendas" or tienda_opt.lower() == str(item.get("tienda") or "").lower())
    if match_search and match_tienda:
        items_filtrados.append(item)

if orden_opt == "Mayor % Descuento":
    items_filtrados.sort(key=lambda x: (-int(x.get("descuento_pct") or 0), -int(x.get("ahorro_clp") or 0)))
elif orden_opt == "Mayor Ahorro ($ CLP)":
    items_filtrados.sort(key=lambda x: (-int(x.get("ahorro_clp") or 0), -int(x.get("descuento_pct") or 0)))
elif orden_opt == "Menor Precio":
    items_filtrados.sort(key=lambda x: int(x.get("precio_remate") or 999999999))
elif orden_opt == "Mayor Precio":
    items_filtrados.sort(key=lambda x: -int(x.get("precio_remate") or 0))

if not items_filtrados:
    st.info("No se encontraron ofertas con descuento real verificado para los filtros actuales.")
else:
    st.markdown(
        f"<div style='font-size: 0.88rem; color: {subtext_color}; margin-bottom: 14px;'>"
        f"Mostrando <b>{len(items_filtrados)}</b> liquidaciones reales en stock verificadas sobre botellas selladas (&ge; 25 ml)</div>",
        unsafe_allow_html=True,
    )
    cols_per_row = 3
    for row in range(0, len(items_filtrados), cols_per_row):
        cols = st.columns(cols_per_row, gap="medium")
        for i in range(cols_per_row):
            idx = row + i
            if idx < len(items_filtrados):
                item = items_filtrados[idx]
                p_norm_str = f"${int(item['precio_normal']):,.0f}".replace(",", ".")
                p_rem_str = f"${int(item['precio_remate']):,.0f}".replace(",", ".")
                ahorro_str = f"${int(item.get('ahorro_clp') or 0):,.0f}".replace(",", ".")
                pct_val = int(item.get("descuento_pct") or 0)
                vol_ml = int(item.get("volumen_ml") or 100)

                nombre_safe = escape_html(item.get("nombre", ""))
                marca_safe = escape_html(item.get("marca", ""))
                tienda_safe = escape_html(item.get("tienda", "Tienda Oficial"))
                img_safe = get_image_src(item.get("imagen_url"))
                safe_url = sanitize_external_url(
                    resolver_url_oferta(
                        tienda_nombre=str(item.get("tienda") or ""),
                        perfume_nombre=str(item.get("nombre") or ""),
                        url_prod=str(item.get("url") or ""),
                        url_base=str(item.get("url_base") or ""),
                        marca=str(item.get("marca") or ""),
                    )
                )

                with cols[i]:
                    html_card = f"""
                    <div class="remate-card">
                        <div class="badge-discount">-{pct_val}% OFF</div>
                        <div class="badge-timer">{vol_ml} ML</div>
                        <div class="remate-img-box">
                            <img src="{img_safe}" alt="{nombre_safe}" loading="lazy">
                        </div>
                        <div class="remate-title" title="{nombre_safe}">{nombre_safe}</div>
                        <div class="remate-brand">{marca_safe}</div>
                        <div class="remate-store-row">
                            <span>Vendido por: <b>{tienda_safe}</b></span>
                            <span style="color: #4ade80; font-weight: 700;">Stock Activo</span>
                        </div>
                        <div class="stock-badge">Ahorro real verificado: {ahorro_str} CLP</div>
                        <div class="price-box">
                            <span class="old-price-line">{p_norm_str} CLP</span>
                            <span class="deal-price">{p_rem_str} CLP</span>
                        </div>
                        <a href="{safe_url}" target="_blank" rel="noopener noreferrer"
                           style="display:block; margin-top:10px; text-align:center; background:#d83737; color:#ffffff !important; font-weight:700; font-size:0.9rem; padding:10px 14px; border-radius:8px; text-decoration:none;">
                           Ir a la Oferta en {tienda_safe} ↗
                        </a>
                    </div>
                    """
                    st.markdown(clean_html(html_card), unsafe_allow_html=True)
                    if st.button("Comparar en todas las tiendas", key=f"btn_remate_comp_{item['perfume_id']}_{idx}", use_container_width=True):
                        st.session_state['selected_perfume'] = item['perfume_id']
                        st.switch_page("pages/compararprecios.py")
