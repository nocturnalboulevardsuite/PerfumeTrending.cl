"""
PerfumeTrending.cl — Directorio de Confianza y Auditoría de Comercios (Trust Score)
===================================================================================
Módulo de transparencia y evaluación de legitimidad para tiendas de perfumería en Chile:
- Cálculo del Trust Score (0 - 100) basado en RUT verificado, antigüedad, certificados SSL y reclamos SERNAC.
- Distinción entre grandes retailers (Falabella, Paris, Ripley) y perfumerías boutique especializadas.
- Desglose de políticas de devolución, sellos de la Cámara de Comercio de Santiago (CCS) y despacho.
- Guía al consumidor para evitar falsificaciones y compras en sitios no oficiales o fraudulentos.
"""

import streamlit as st
import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)
if APP_DIR not in sys.path:
    sys.path.append(APP_DIR)

from backend.database import auditar_tienda_por_url, obtener_tiendas
from ui import (
    FLAME_RED_SVG as flame_red_svg,
    HOME_RED_SVG as home_red_svg,
    PERFUME_SVG_FAVICON,
    SHIELD_RED_SVG as shield_red_svg,
    TAG_RED_SVG as tag_red_svg,
    TREND_RED_SVG as trend_red_svg,
    cerrar_sesion_usuario,
    clean_html,
    escape_html,
    get_theme_palette,
    init_common_session_state,
    modal_autenticacion,
    sanitize_external_url,
    toggle_theme,
)

# 1. CONFIGURACIÓN DE PÁGINA Y ESTADO COMPARTIDO
st.set_page_config(
    page_title="PerfumeTrending — Verificación de Confianza",
    page_icon=PERFUME_SVG_FAVICON,
    layout="wide",
    initial_sidebar_state="collapsed",
)

init_common_session_state()

pal = get_theme_palette()
is_dark = pal.is_dark
bg_color = pal.app_bg
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
logo_svg_data = pal.logo_svg_data

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
            st.write("**Conectado como:**")
            st.write(st.session_state['user_info'].get('email', ''))
            st.markdown("<div style='margin-top: 8px;'></div>", unsafe_allow_html=True)

            if st.button("Mi Perfil y Alertas", key="btn_go_profile", use_container_width=True):
                st.switch_page("pages/perfil.py")

            if st.button("Cerrar Sesión", key="btn_logout", use_container_width=True):
                cerrar_sesion_usuario()
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        if st.button("Ingresar", key="login_btn", use_container_width=True):
            st.session_state['show_login_modal'] = True

with btn_col2:
    st.button(" ", key="theme_toggle", on_click=toggle_theme)

# MONITOREO Y RENDERIZADO DEL MODAL
if st.session_state.get('show_login_modal', False):
    st.session_state['show_login_modal'] = False
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
        st.switch_page("pages/remates.py")

st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
col_sub_title, col_sub_back = st.columns([7, 3], vertical_alignment="center")
with col_sub_title:
    st.markdown(f"<div style='color: {subtext_color}; font-size: 0.85rem; font-weight: 600; text-transform: uppercase; letter-spacing: 1px;'>AUDITORÍA DE TIENDAS Y SEGURIDAD</div>", unsafe_allow_html=True)
with col_sub_back:
    st.page_link("app.py", label="← Volver al Catálogo")

st.markdown(f"<hr style='border: none; border-top: 1px solid {border_color}; margin: 16px 0 24px 0;' />", unsafe_allow_html=True)

# =============================================================================
# BLOQUE 4: ESTRUCTURA DE AUDITORÍA (FICHA ILUSTRADA + TABLA DE CONFIANZA)
# =============================================================================
left_col, right_col = st.columns([1, 1.4], gap="large")

# --- COLUMNA IZQUIERDA: TARJETA DE PRODUCTO MINIMALISTA ILUSTRADA ---
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

# --- COLUMNA DERECHA: TABLA DE VERIFICACIÓN EN ESPAÑOL + AUDITOR DE URL ---
with right_col:
    tiendas_auditadas = obtener_tiendas()

    filas_html = []
    for idx, t in enumerate(tiendas_auditadas, 1):
        num_str = f"{idx:02d}"
        score = int(t.get('trust_score', 95) or 95)
        badge_status = (
            '<span class="status-badge-safe">VERIFICADO</span>'
            if score >= 85
            else '<span class="status-badge-danger">AUDITORÍA</span>'
        )
        raw_url = str(t.get("url_base") or "")
        if "alisha.cl" in raw_url and "alishaperfumes.cl" not in raw_url:
            raw_url = "https://alishaperfumes.cl"
        safe_url = escape_html(sanitize_external_url(raw_url, fallback="#"))
        safe_nombre = escape_html(str(t.get('nombre', 'Tienda')).upper())
        safe_badge = escape_html(str(t.get('badge') or 'Comercio Oficial'))
        safe_rut = escape_html(str(t.get('rut') or 'Verificado SII'))
        accion_html = f'<a href="{safe_url}" target="_blank" rel="noopener noreferrer" class="btn-buy-now">VISITAR</a>'

        fila = f"""
        <tr>
            <td>{num_str}</td>
            <td>
                <div class="store-title">{safe_nombre}</div>
                <div style="font-size: 0.65rem; color: {subtext_color};">{safe_badge} &bull; RUT: {safe_rut}</div>
            </td>
            <td><span class="price-tag">{score}/100</span></td>
            <td>{badge_status}</td>
            <td>{accion_html}</td>
        </tr>
        """
        filas_html.append(fila)

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

    st.markdown("<div style='margin-top: 22px;'></div>", unsafe_allow_html=True)
    with st.form("form_auditar_url_tienda", clear_on_submit=False):
        st.markdown(
            f"<div style='font-size: 0.82rem; font-weight: 700; color: {text_color}; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.6px;'>Auditor Interactivo de Sitios de Perfumería</div>",
            unsafe_allow_html=True,
        )
        col_u1, col_u2 = st.columns([3.2, 1.3], vertical_alignment="bottom")
        with col_u1:
            url_check = st.text_input(
                "Ingresa el dominio o URL de una tienda para verificar su respaldo",
                placeholder="Ej: silkperfumes.cl, eliteperfumes.cl o tienda-sospechosa.com",
                label_visibility="collapsed",
            )
        with col_u2:
            btn_audit = st.form_submit_button("Auditar Sitio", use_container_width=True)

        if btn_audit:
            res_audit = auditar_tienda_por_url(url_check)
            if not res_audit:
                st.warning("Ingresa un dominio o URL válido para analizar.")
            else:
                sc_val = int(res_audit.get("score", 0))
                es_ok = bool(res_audit.get("es_conocida")) and sc_val >= 85
                borde_res = "#10b981" if es_ok else ("#f59e0b" if sc_val >= 70 else "#ef4444")
                safe_nom_aud = escape_html(res_audit.get("nombre", ""))
                safe_dom_aud = escape_html(res_audit.get("dominio", ""))
                safe_rec_aud = escape_html(res_audit.get("recomendacion", ""))
                safe_rut_aud = escape_html(res_audit.get("rut", ""))
                alertas = res_audit.get("senales_alerta") or []
                alertas_html = ""
                if alertas:
                    items_al = "".join(f"<li>{escape_html(a)}</li>" for a in alertas)
                    alertas_html = f"<ul style='margin: 8px 0 0 18px; color: #ef4444; font-size: 0.78rem;'>{items_al}</ul>"
                st.markdown(
                    clean_html(f"""
                    <div style="background: {card_bg}; border: 1px solid {borde_res}; border-left: 4px solid {borde_res}; border-radius: 10px; padding: 14px 16px; margin-top: 10px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; gap: 10px;">
                            <div>
                                <div style="font-weight: 700; font-size: 0.95rem; color: {text_color};">{safe_nom_aud} <span style="font-weight: 400; font-size: 0.78rem; color: {subtext_color};">({safe_dom_aud})</span></div>
                                <div style="font-size: 0.76rem; color: {subtext_color}; margin-top: 2px;">RUT: {safe_rut_aud} &bull; {escape_html(res_audit.get('badge', ''))}</div>
                            </div>
                            <div style="font-weight: 800; font-size: 1.15rem; color: {borde_res};">{sc_val}/100</div>
                        </div>
                        <div style="font-size: 0.8rem; color: {text_color}; margin-top: 8px;">{safe_rec_aud}</div>
                        {alertas_html}
                    </div>
                    """),
                    unsafe_allow_html=True,
                )
