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
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_DIR = os.path.dirname(APP_DIR)
for _p in (APP_DIR, BASE_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)
    elif sys.path[0] != _p:
        try:
            sys.path.remove(_p)
        except ValueError:
            pass
        sys.path.insert(0, _p)

import hashlib

try:
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
except (ImportError, ModuleNotFoundError):
    from APP.backend.database import (
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
    toggle_theme,
)
from auth_email import modal_autenticacion
from perfume_actions import (
    boton_abrir_perfume,
    boton_corazon,
    estilos_moviles,
    estilos_tarjetas_cliqueables,
    mostrar_aviso_favoritos,
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
settings_icon_svg = pal.settings_icon_svg
logout_icon_svg = pal.logout_icon_svg

# Paleta clara reforzada: fondo blanco y texto oscuro legible en todos los componentes.
# El modo oscuro conserva exactamente los valores de la paleta compartida.
if not is_dark:
    app_bg = "#ffffff"
    app_bg_css = "background: #ffffff !important; background-color: #ffffff !important;"
    text_color = "#1c1917"
    subtext_color = "#6b6159"
    btn_bg = "#ffffff"
    btn_text = "#1c1917"
    btn_border = "#d6cec5"
    input_bg = "#ffffff"
    input_text = "#1c1917"
    input_border = "#d6cec5"

# Tokens visuales compartidos con Inicio, Trend del Hype y Páginas de Confianza
card_bg = btn_bg
border_color = "rgba(255, 255, 255, 0.10)" if is_dark else "#e6e1db"
accent = "#d83737"
accent_hover = "#b92d2d"
accent_soft = "rgba(216, 55, 55, 0.14)" if is_dark else "rgba(216, 55, 55, 0.07)"
gold = "#d4c2a5" if is_dark else "#8c7b6d"
gold_soft = "rgba(212, 194, 165, 0.16)" if is_dark else "rgba(140, 123, 109, 0.14)"
ok_green = "#4ade80" if is_dark else "#15803d"
warn_amber = "#fbbf24" if is_dark else "#b45309"
risk_red = "#f87171" if is_dark else "#dc2626"
info_blue = "#60a5fa" if is_dark else "#1d4ed8"
surface_soft = "rgba(255, 255, 255, 0.035)" if is_dark else "#faf8f5"
img_stage_bg = "radial-gradient(circle at 50% 45%, #1d222c 0%, #11141a 100%)" if is_dark else "radial-gradient(circle at 50% 45%, #ffffff 0%, #f6f4f1 100%)"
shadow_sm = "0 1px 2px rgba(0,0,0,0.35)" if is_dark else "0 1px 2px rgba(40,30,20,0.06)"
shadow_hover = "0 6px 16px rgba(0,0,0,0.35)" if is_dark else "0 6px 16px rgba(60,45,35,0.10)"
font_sans = "'Manrope', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"


# COMPONENTES VECTORIALES INLINE SVG PARA REEMPLAZO DE EMOJIS
svg_mail = f'<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="{subtext_color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: -2px; margin-right: 4px;"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>'
svg_phone = f'<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="{subtext_color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: -2px; margin-right: 4px;"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/></svg>'
svg_bell_active = f'<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: -2px; margin-right: 5px;"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>'
svg_bell_off = f'<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: -2px; margin-right: 5px;"><path d="M13.73 21a2 2 0 0 1-3.46 0"/><line x1="1" y1="1" x2="23" y2="23"/></svg>'
svg_trend_down = f'<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: -2px; margin-right: 5px;"><polyline points="23 18 13.5 8.5 8.5 13.5 1 6"/><polyline points="17 18 23 18 23 12"/></svg>'
svg_pin = f'<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="{subtext_color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: -2px; margin-right: 4px;"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>'

# 2. CSS ADAPTABLE Y ESTILOS PRINCIPALES (MISMO SISTEMA VISUAL QUE EL RESTO DEL SITIO)
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@300;400;500;600;700;800&display=swap');

    header[data-testid="stHeader"] {{ display: none !important; }}
    div[data-testid="stAppViewContainer"] {{ padding-top: 0px !important; }}

    html, body {{ background-color: {app_bg} !important; }}
    .stApp {{
        {app_bg_css}
        color: {text_color} !important;
        font-family: {font_sans};
        color-scheme: {"dark" if is_dark else "light"};
    }}
    [data-testid="stMain"],
    [data-testid="stMainBlockContainer"],
    [data-testid="stBottom"] > div {{
        background: transparent !important;
        background-color: transparent !important;
    }}

    .block-container {{
        padding-top: 1.4rem !important;
        padding-bottom: 2rem !important;
        max-width: 1180px !important;
        zoom: 0.92;
    }}

    .stApp p, .stApp label, .stApp li, .stApp input, .stApp textarea, .stApp button,
    div[data-testid="stPopoverBody"] p {{
        font-family: {font_sans} !important;
    }}

    .stApp p, .stApp span:not([class*="pt-"]), .stApp label, .stMarkdown p {{
        color: {text_color} !important;
        text-shadow: none !important;
    }}

    /* Textos nativos y modales (login) */
    .stApp h1, .stApp h2, .stApp h3, .stApp strong, .stApp b,
    [data-testid="stWidgetLabel"] p,
    button[data-baseweb="tab"] p {{
        color: {text_color} !important;
    }}
    [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {{ color: {subtext_color} !important; }}
    button[data-baseweb="tab"] {{ background: transparent !important; }}
    div[data-baseweb="tab-highlight"] {{ background-color: {accent} !important; }}
    [role="dialog"] {{
        background-color: {card_bg} !important;
        color: {text_color} !important;
        border: 1px solid {border_color} !important;
        border-radius: 16px !important;
    }}
    [role="dialog"] h2, [role="dialog"] h2 *, [role="dialog"] p, [role="dialog"] label {{
        color: {text_color} !important;
    }}
    [role="dialog"] button[aria-label="Close"] svg {{ color: {text_color} !important; fill: {text_color} !important; }}

    /* Campos de texto (modal de ingreso), versiones antiguas y nuevas de Streamlit */
    div[data-baseweb="input"],
    [data-testid="stTextInputRootElement"] {{
        background-color: {input_bg} !important;
        border: 1px solid {input_border} !important;
        border-radius: 10px !important;
        box-shadow: none !important;
    }}
    div[data-baseweb="base-input"] {{ background-color: transparent !important; border: none !important; }}
    div[data-baseweb="input"] input,
    [data-testid="stTextInputRootElement"] input {{
        background-color: transparent !important;
        color: {input_text} !important;
    }}
    div[data-baseweb="input"]:focus-within,
    [data-testid="stTextInputRootElement"]:focus-within {{
        border-color: {gold} !important;
        box-shadow: 0 0 0 3px {gold_soft} !important;
    }}
    input::placeholder {{ color: {subtext_color} !important; opacity: 1 !important; }}

    /* ---------- BOTONES BASE ---------- */
    div.stButton > button {{
        background-color: {btn_bg} !important;
        border: 1px solid {btn_border} !important;
        color: {btn_text} !important;
        border-radius: 10px !important;
        min-height: 42px;
        box-shadow: {shadow_sm} !important;
        transition: background-color 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease !important;
        outline: none !important;
    }}

    div.stButton > button p {{
        color: {btn_text} !important;
        font-weight: 600 !important;
        font-size: 0.92rem !important;
    }}

    div.stButton > button:hover {{
        border-color: {gold} !important;
        box-shadow: {shadow_hover} !important;
    }}

    div.stButton > button:focus-visible,
    a[data-testid="stPageLink-NavLink"]:focus-visible {{
        outline: 2px solid {accent} !important;
        outline-offset: 2px !important;
    }}

    /* ---------- POPOVERS (perfil y filtro de período) ---------- */
    button[data-testid="stPopoverButton"],
    div[data-testid="stPopover"] > button {{
        background-color: {btn_bg} !important;
        color: {btn_text} !important;
        border: 1px solid {btn_border} !important;
        border-radius: 999px !important;
        min-height: 38px !important;
        box-shadow: {shadow_sm} !important;
        transition: border-color 0.18s ease, box-shadow 0.18s ease !important;
    }}
    button[data-testid="stPopoverButton"]:hover,
    div[data-testid="stPopover"] > button:hover {{
        border-color: {gold} !important;
        box-shadow: {shadow_hover} !important;
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
        border-radius: 14px !important;
        color: {text_color} !important;
        box-shadow: {shadow_hover} !important;
    }}

    /* Popover de usuario con icono */
    div[data-testid="stColumn"]:has(.user-popover-container) button[data-testid="stPopoverButton"] {{
        padding-left: 2.4rem !important;
        background-image: url("{user_icon_svg}") !important;
        background-repeat: no-repeat !important;
        background-position: 14px center !important;
        background-size: 17px 17px !important;
    }}

    /* Mi Perfil / Cerrar sesión */
    div.st-key-btn_go_profile div.stButton > button,
    div.st-key-btn_logout div.stButton > button {{
        justify-content: flex-start !important;
        padding-left: 2.6rem !important;
        background-repeat: no-repeat !important;
        background-position: 14px center !important;
        background-size: 17px 17px !important;
        box-shadow: none !important;
    }}
    div.st-key-btn_go_profile div.stButton > button {{ background-image: url("{settings_icon_svg}") !important; }}
    div.st-key-btn_logout div.stButton > button {{ background-image: url("{logout_icon_svg}") !important; }}

    /* ---------- BOTÓN INGRESAR ---------- */
    .st-key-login_btn, .st-key-theme_toggle {{
        display: flex !important;
        align-items: center !important;
        height: 100% !important;
    }}

    .st-key-login_btn,
    .st-key-login_btn div[data-testid="stButton"] {{
        justify-content: flex-end !important;
        width: 100% !important;
        display: flex !important;
    }}

    div.st-key-login_btn div.stButton > button {{
        background-color: {btn_bg} !important;
        color: {btn_text} !important;
        border: 1px solid {btn_border} !important;
        border-radius: 999px !important;
        width: auto !important;
        min-width: max-content !important;
        height: auto !important;
        min-height: 38px !important;
        padding: 6px 18px 6px 38px !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        overflow: visible !important;
        background-image: url("{user_icon_svg}") !important;
        background-repeat: no-repeat !important;
        background-position: 14px center !important;
        background-size: 16px 16px !important;
        box-shadow: {shadow_sm} !important;
        margin: 0 !important;
        white-space: nowrap !important;
    }}
    div.st-key-login_btn div.stButton > button > div,
    div.st-key-login_btn div.stButton > button div[data-testid="stMarkdownContainer"] {{
        overflow: visible !important;
        width: auto !important;
        margin: 0 !important;
        padding: 0 !important;
        display: block !important;
    }}
    div.st-key-login_btn div.stButton > button p {{
        font-size: 0.92rem !important;
        line-height: 1.35 !important;
        margin: 0 !important;
        padding: 0 !important;
        color: {btn_text} !important;
        font-weight: 700 !important;
        letter-spacing: 0.2px !important;
        white-space: nowrap !important;
        overflow: visible !important;
        text-overflow: clip !important;
    }}
    div[data-testid="stColumn"]:has(.user-popover-container) button[data-testid="stPopoverButton"] {{
        min-height: 38px !important;
        height: auto !important;
    }}

    /* El switch conserva exactamente su aspecto original (sin fondo ni borde) */
    div.st-key-theme_toggle div.stButton > button,
    div.st-key-theme_toggle div.stButton > button:hover,
    div.st-key-theme_toggle div.stButton > button:focus,
    div.st-key-theme_toggle div.stButton > button:focus-visible {{
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        outline: none !important;
        transform: none !important;
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

    /* ---------- ACCESOS RÁPIDOS (CHIPS) ---------- */
    a[data-testid="stPageLink-NavLink"] {{
        background-color: transparent !important;
        border: 1px solid {btn_border} !important;
        border-radius: 999px !important;
        padding: 0.45rem 1.1rem !important;
        box-shadow: none !important;
        width: 100% !important;
        min-height: 40px !important;
        height: auto !important;
        filter: none !important;
        text-decoration: none !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        box-sizing: border-box !important;
        transition: background-color 0.18s ease, border-color 0.18s ease !important;
    }}
    a[data-testid="stPageLink-NavLink"]:hover {{
        background-color: {btn_bg} !important;
        border-color: {gold} !important;
    }}
    a[data-testid="stPageLink-NavLink"] p,
    a[data-testid="stPageLink-NavLink"] span {{
        font-size: 0.87rem !important;
        font-weight: 600 !important;
        color: {btn_text} !important;
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
        padding-left: 2.6rem !important;
        padding-right: 1.1rem !important;
        overflow: hidden !important;
    }}
    a[data-testid="stPageLink-NavLink"][href*="trendhype"]::before,
    a[data-testid="stPageLink-NavLink"][href*="trustpage"]::before,
    a[data-testid="stPageLink-NavLink"][href*="compararprecios"]::before,
    a[data-testid="stPageLink-NavLink"][href$="app.py"]::before,
    a[data-testid="stPageLink-NavLink"][href="/"]::before {{
        content: '' !important;
        position: absolute !important;
        left: 15px !important;
        top: 50% !important;
        transform: translateY(-50%) !important;
        width: 16px !important;
        height: 16px !important;
        background-repeat: no-repeat !important;
        background-size: contain !important;
        background-position: center !important;
        z-index: 1 !important;
    }}
    a[data-testid="stPageLink-NavLink"][href*="trendhype"]::before {{ background-image: url("{trend_red_svg}") !important; }}
    a[data-testid="stPageLink-NavLink"][href*="trustpage"]::before {{ background-image: url("{shield_red_svg}") !important; }}
    a[data-testid="stPageLink-NavLink"][href*="compararprecios"]::before {{ background-image: url("{tag_red_svg}") !important; }}
    a[data-testid="stPageLink-NavLink"][href$="app.py"]::before,
    a[data-testid="stPageLink-NavLink"][href="/"]::before {{ background-image: url("{home_red_svg}") !important; }}

    /* ---------- LOGO ---------- */
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
        border: none !important;
        box-shadow: none !important;
        outline: none !important;
        padding: 0 !important;
        margin: 0 !important;
        cursor: pointer !important;
        user-select: none !important;
    }}
    .brand-logo-text {{
        font-family: {font_sans} !important;
        font-size: 1.6rem !important;
        color: {text_color} !important;
        letter-spacing: -0.02em !important;
        font-weight: 300 !important;
        line-height: 1 !important;
        display: inline-block !important;
    }}
    .brand-logo-text strong {{ font-weight: 800 !important; color: {text_color} !important; }}

    /* ---------- PIE DE PÁGINA ---------- */
    .pt-footer {{
        display: flex;
        flex-wrap: wrap;
        align-items: baseline;
        justify-content: space-between;
        gap: 10px;
        padding: 22px 0 26px 0;
        margin-top: 40px;
        border-top: 1px solid {btn_border};
    }}
    .pt-footer-mark {{ font-size: 1.1rem; font-weight: 300; color: {text_color}; }}
    .pt-footer-mark strong {{ font-weight: 800; color: {text_color}; }}
    .pt-footer-copy {{ font-size: 0.85rem; color: {subtext_color}; }}


    /* ---------- ENCABEZADO DE SECCIÓN ---------- */
    .pt-title {{
        font-family: {font_sans};
        font-weight: 800;
        font-size: clamp(1.6rem, 3vw, 2.2rem);
        letter-spacing: -0.025em;
        line-height: 1.1;
        color: {text_color};
    }}
    .pt-lede {{
        font-size: 0.98rem;
        color: {subtext_color};
        margin-top: 8px;
        max-width: 62ch;
        line-height: 1.55;
    }}
    .pt-section-title {{
        display: flex;
        align-items: center;
        font-size: 1.15rem;
        font-weight: 800;
        letter-spacing: -0.01em;
        color: {text_color};
        margin: 6px 0 4px 0;
    }}
    .pt-section-help {{
        font-size: 0.88rem;
        color: {subtext_color};
        line-height: 1.55;
        margin-bottom: 16px;
        max-width: 72ch;
    }}

    /* ---------- TARJETA DE PERFIL ---------- */
    .st-key-profile_card {{
        background-color: {card_bg} !important;
        border: 1px solid {border_color} !important;
        border-radius: 20px !important;
        padding: 26px 28px !important;
        margin-bottom: 26px !important;
    }}

    /* Foto de perfil: toda la zona (foto + "Cambiar foto") abre el selector de archivos del PC */
    .st-key-avatar_box {{
        position: relative !important;
        width: 136px !important;
        margin: 0 auto !important;
        gap: 0 !important;
    }}
    .avatar-click-zone {{
        position: relative;
        width: 120px;
        height: 120px;
        border-radius: 50%;
        margin: 0 auto;
        cursor: pointer;
    }}
    .avatar-click-zone .profile-avatar-img {{
        width: 120px;
        height: 120px;
        border-radius: 50%;
        object-fit: cover;
        border: 3px solid {gold};
        background-color: {input_bg};
        padding: 3px;
        display: block;
        box-sizing: border-box;
    }}
    .avatar-click-zone .avatar-overlay-badge {{
        position: absolute;
        inset: 0;
        border-radius: 50%;
        background: rgba(0, 0, 0, 0.55);
        color: #ffffff;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 2px;
        opacity: 0;
        transition: opacity 0.2s ease;
        pointer-events: none;
        font-size: 0.74rem;
        font-weight: 700;
    }}
    .avatar-camera-dot {{
        position: absolute;
        right: 4px;
        bottom: 4px;
        width: 32px;
        height: 32px;
        border-radius: 50%;
        background: {accent};
        border: 3px solid {card_bg};
        display: flex;
        align-items: center;
        justify-content: center;
        box-sizing: border-box;
    }}
    .avatar-change-pill {{
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 6px;
        margin: 12px auto 0 auto;
        width: max-content;
        padding: 6px 14px;
        border-radius: 999px;
        border: 1px solid {btn_border};
        background: {btn_bg};
        color: {text_color};
        font-size: 0.82rem;
        font-weight: 700;
        transition: border-color 0.18s ease, background-color 0.18s ease;
    }}
    .st-key-avatar_box:hover .avatar-overlay-badge {{ opacity: 1; }}
    .st-key-avatar_box:hover .avatar-change-pill {{ border-color: {gold}; background: {gold_soft}; }}
    .st-key-avatar_box:focus-within .avatar-change-pill {{ outline: 2px solid {accent}; outline-offset: 2px; }}
    .avatar-help {{
        text-align: center;
        font-size: 0.74rem;
        color: {subtext_color};
        margin-top: 8px;
        line-height: 1.4;
    }}

    /* Selector de archivos invisible que cubre toda la zona de la foto */
    .st-key-avatar_quick_uploader {{
        position: absolute !important;
        inset: 0 !important;
        width: 100% !important;
        height: 100% !important;
        margin: 0 !important;
        padding: 0 !important;
        opacity: 0 !important;
        z-index: 25 !important;
        overflow: hidden !important;
        cursor: pointer !important;
    }}
    .st-key-avatar_quick_uploader * {{ cursor: pointer !important; }}
    .st-key-avatar_quick_uploader > div,
    .st-key-avatar_quick_uploader [data-testid="stFileUploader"],
    .st-key-avatar_quick_uploader [data-testid="stFileUploader"] > div,
    .st-key-avatar_quick_uploader section,
    .st-key-avatar_quick_uploader [data-testid="stFileUploaderDropzone"] {{
        width: 100% !important;
        height: 100% !important;
        min-height: 100% !important;
        margin: 0 !important;
        padding: 0 !important;
    }}
    .st-key-avatar_quick_uploader button {{
        position: absolute !important;
        inset: 0 !important;
        width: 100% !important;
        height: 100% !important;
        margin: 0 !important;
    }}

    /* Datos del usuario */
    .profile-name {{
        margin: 0 0 6px 0;
        color: {text_color};
        font-size: 1.7rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        line-height: 1.15;
    }}
    .profile-contact {{
        color: {subtext_color};
        font-size: 0.9rem;
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 6px 16px;
        margin-bottom: 12px;
    }}
    .profile-contact-item {{ display: inline-flex; align-items: center; }}
    .profile-bio {{
        margin: 4px 0 0 0;
        color: {text_color};
        font-size: 0.94rem;
        line-height: 1.6;
        max-width: 70ch;
    }}
    .profile-top {{
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        flex-wrap: wrap;
        gap: 12px;
    }}
    span.pt-alert-on,
    span.pt-alert-off {{
        display: inline-flex;
        align-items: center;
        font-size: 0.8rem;
        font-weight: 700;
        padding: 6px 13px;
        border-radius: 999px;
        white-space: nowrap;
    }}
    span.pt-alert-on {{
        background: rgba(34, 197, 94, 0.10);
        color: {ok_green} !important;
        border: 1px solid rgba(34, 197, 94, 0.30);
    }}
    span.pt-alert-off {{
        background: {surface_soft};
        color: {subtext_color} !important;
        border: 1px solid {border_color};
    }}

    /* ---------- PESTAÑAS ---------- */
    div[data-baseweb="tab-list"],
    div[role="tablist"] {{
        gap: 6px !important;
        border-bottom: 1px solid {btn_border} !important;
    }}
    button[data-baseweb="tab"],
    div[role="tablist"] button[role="tab"],
    [data-testid="stTabs"] [role="tab"] {{
        background: transparent !important;
        padding: 10px 4px !important;
        margin-right: 18px !important;
    }}
    button[data-baseweb="tab"] p,
    div[role="tablist"] button[role="tab"] p,
    [data-testid="stTabs"] [role="tab"] p {{
        font-size: 0.95rem !important;
        font-weight: 700 !important;
        color: {subtext_color} !important;
    }}
    button[data-baseweb="tab"][aria-selected="true"] p,
    div[role="tablist"] button[role="tab"][aria-selected="true"] p,
    [data-testid="stTabs"] [role="tab"][aria-selected="true"] p {{
        color: {text_color} !important;
    }}
    div[data-baseweb="tab-border"] {{ display: none !important; }}
    div[data-baseweb="tab-panel"],
    div[role="tabpanel"] {{ padding-top: 18px !important; }}

    /* ---------- FAVORITOS ---------- */
    div[class*="st-key-fav_row_"] {{
        background-color: {card_bg} !important;
        border: 1px solid {border_color} !important;
        border-radius: 14px !important;
        padding: 14px 16px !important;
        margin-bottom: 10px !important;
        transition: border-color 0.18s ease !important;
    }}
    div[class*="st-key-fav_row_"]:hover {{ border-color: {gold} !important; }}
    .fav-name {{ font-weight: 800; font-size: 1rem; color: {text_color}; line-height: 1.3; }}
    .fav-brand {{ font-size: 0.84rem; color: {subtext_color}; margin-top: 2px; }}
    span.pt-price-drop {{
        display: inline-flex;
        align-items: center;
        color: {ok_green} !important;
        font-weight: 800;
        font-size: 0.95rem;
        font-variant-numeric: tabular-nums;
    }}
    span.pt-price-now {{
        color: {text_color} !important;
        font-weight: 700;
        font-size: 0.95rem;
        font-variant-numeric: tabular-nums;
    }}
    span.pt-price-sub {{
        display: block;
        font-size: 0.78rem;
        color: {subtext_color} !important;
        margin-top: 2px;
        font-variant-numeric: tabular-nums;
    }}
    span.pt-price-out {{ color: {subtext_color} !important; font-weight: 600; font-size: 0.9rem; }}
    div[class*="st-key-btn_comp_fav_"] div.stButton > button {{
        background-color: {accent} !important;
        border: 1px solid {accent} !important;
        box-shadow: none !important;
        border-radius: 999px !important;
    }}
    div[class*="st-key-btn_comp_fav_"] div.stButton > button p {{ color: #ffffff !important; font-weight: 700 !important; }}
    div[class*="st-key-btn_comp_fav_"] div.stButton > button:hover {{
        background-color: {accent_hover} !important;
        border-color: {accent_hover} !important;
    }}
    div[class*="st-key-btn_rem_fav_"] div.stButton > button {{
        background-color: transparent !important;
        box-shadow: none !important;
        border-radius: 999px !important;
    }}
    div[class*="st-key-btn_rem_fav_"] div.stButton > button:hover {{
        border-color: {risk_red} !important;
    }}
    div[class*="st-key-btn_rem_fav_"] div.stButton > button:hover p {{ color: {risk_red} !important; }}
    div.st-key-btn_go_catalog div.stButton > button,
    div.st-key-btn_must_login div.stButton > button {{
        background-color: {accent} !important;
        border: 1px solid {accent} !important;
        border-radius: 999px !important;
        padding: 0 22px !important;
        box-shadow: none !important;
    }}
    div.st-key-btn_go_catalog div.stButton > button p,
    div.st-key-btn_must_login div.stButton > button p {{ color: #ffffff !important; font-weight: 700 !important; }}

    /* ---------- FORMULARIOS ---------- */
    div[data-testid="stForm"] {{
        background-color: {card_bg} !important;
        border: 1px solid {border_color} !important;
        border-radius: 18px !important;
        padding: 22px 22px 18px 22px !important;
    }}
    div[data-baseweb="textarea"],
    [data-testid="stTextArea"] textarea {{
        background-color: {input_bg} !important;
        border-color: {input_border} !important;
        border-radius: 10px !important;
        color: {input_text} !important;
    }}
    [data-testid="stTextArea"] textarea {{ border: 1px solid {input_border} !important; }}
    [data-testid="stTextArea"] textarea:focus {{
        border-color: {gold} !important;
        box-shadow: 0 0 0 3px {gold_soft} !important;
    }}
    [data-testid="stFileUploader"] section,
    [data-testid="stFileUploaderDropzone"] {{
        background-color: {surface_soft} !important;
        border: 1px dashed {input_border} !important;
        border-radius: 12px !important;
    }}
    [data-testid="stFileUploader"] section *,
    [data-testid="stFileUploaderDropzone"] * {{ color: {text_color} !important; }}
    [data-testid="stFileUploader"] small {{ color: {subtext_color} !important; }}
    div[data-testid="stFormSubmitButton"] button {{
        background-color: {accent} !important;
        border: 1px solid {accent} !important;
        color: #ffffff !important;
        border-radius: 999px !important;
        min-height: 46px !important;
        box-shadow: none !important;
        transition: background-color 0.18s ease !important;
    }}
    div[data-testid="stFormSubmitButton"] button:hover {{
        background-color: {accent_hover} !important;
        border-color: {accent_hover} !important;
    }}
    div[data-testid="stFormSubmitButton"] button p {{ color: #ffffff !important; font-weight: 700 !important; }}
    div[data-testid="stSlider"] div[role="slider"] {{
        background-color: {accent} !important;
        border-color: {accent} !important;
        box-shadow: 0 0 0 4px {accent_soft} !important;
    }}
    div[data-testid="stCheckbox"] label p {{ font-size: 0.93rem !important; }}
    div[data-testid="stAlert"] > div {{ border-radius: 12px !important; }}

    /* ---------- MÓVIL ---------- */
    @media (max-width: 768px) {{
        .block-container {{
            padding-top: 0.4rem !important;
            padding-left: 0.8rem !important;
            padding-right: 0.8rem !important;
        }}
        div[data-testid="stHorizontalBlock"] {{ flex-wrap: wrap !important; gap: 6px !important; }}
        div[data-testid="stColumn"] {{ width: 100% !important; flex: 1 1 100% !important; min-width: 0 !important; }}
        div[data-testid="stHorizontalBlock"]:has(.st-key-login_btn, .st-key-theme_toggle) {{
            flex-wrap: nowrap !important;
            align-items: center !important;
            justify-content: space-between !important;
        }}
        div[data-testid="stColumn"]:has(a[data-testid="stPageLink-NavLink"]) {{
            flex: 1 1 calc(50% - 4px) !important;
            width: calc(50% - 4px) !important;
        }}
        a[data-testid="stPageLink-NavLink"] {{ justify-content: flex-start !important; padding-left: 2.2rem !important; }}
        a[data-testid="stPageLink-NavLink"] p,
        a[data-testid="stPageLink-NavLink"] span {{ font-size: 0.8rem !important; white-space: normal !important; line-height: 1.15 !important; }}
        a[data-testid="stPageLink-NavLink"]::before {{ left: 11px !important; }}
        .brand-logo-text {{ font-size: 1.35rem !important; }}
        .st-key-profile_card {{ padding: 20px 16px !important; }}
        .profile-top {{ justify-content: center; text-align: center; }}
        .profile-contact {{ justify-content: center; }}
        .profile-name {{ font-size: 1.45rem; }}
        div.st-key-login_btn div.stButton > button {{
            min-height: 36px !important;
            padding: 5px 14px 5px 32px !important;
            background-position: 11px center !important;
        }}
    }}
    </style>
""", unsafe_allow_html=True)

# Perfumes cliqueables y corazón de favoritos (compartido con todas las páginas)
st.markdown(estilos_tarjetas_cliqueables(accent, card_bg, border_color, subtext_color, is_dark), unsafe_allow_html=True)
# Diseño responsivo para celulares (común a todas las páginas)
st.markdown(estilos_moviles(accent, border_color, is_dark), unsafe_allow_html=True)
st.markdown(f"""
    <style>
    div[class*="st-key-pcard_favrow_"] {{ cursor: pointer; }}
    div[class*="st-key-pcard_favrow_"]:hover .fav-name {{ color: {accent}; text-decoration: underline; text-underline-offset: 3px; }}
    </style>
""", unsafe_allow_html=True)

# 3. ENCABEZADO SUPERIOR: LOGO, BOTÓN "INGRESAR" / PERFIL Y SWITCH DE TEMA
if st.session_state['logged_in']:
    # Mismo tamaño del botón de usuario en todas las páginas: ni muy chico ni muy grande
    col_logo, col_espacio, col_actions = st.columns([5.2, 0.6, 3.2], vertical_alignment="center")
    btn_col1, btn_col2 = col_actions.columns([2.4, 0.8], vertical_alignment="center", gap="small")
else:
    col_logo, col_espacio, col_actions = st.columns([5.6, 1.2, 2.4], vertical_alignment="center")
    btn_col1, btn_col2 = col_actions.columns([2.0, 0.8], vertical_alignment="center", gap="small")

with col_logo:
    st.markdown(clean_html(f"""
    <a href="/" target="_self" class="brand-logo-clean" title="PerfumeTrending">
        <svg width="34" height="34" viewBox="0 0 36 36" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path d="M 6.8 21 L 29.2 21 C 30 25 27 32 18 32 C 9 32 6 25 6.8 21 Z" fill="{gold}" />
            <line x1="6.8" y1="21" x2="29.2" y2="21" stroke="{text_color}" stroke-width="1.5" />
            <line x1="18" y1="10" x2="18" y2="30" stroke="{text_color}" stroke-width="1" />
            <path d="M 18 32 C 9 32 5 24 7.5 17 C 9 12 13 10 15 10 L 21 10 C 23 10 27 12 28.5 17 C 31 24 27 32 18 32 Z" stroke="{text_color}" stroke-width="2" />
            <rect x="15" y="7" width="6" height="3" stroke="{text_color}" stroke-width="1.5" />
            <rect x="13" y="3" width="10" height="4" rx="1" stroke="{text_color}" stroke-width="1.5" />
            <rect x="16" y="0" width="4" height="3" rx="1" fill="{gold}" stroke="{text_color}" stroke-width="1" />
        </svg>
        <span class="brand-logo-text">Perfume<strong>Trending</strong></span>
    </a>
    """), unsafe_allow_html=True)

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
mostrar_aviso_favoritos()

st.markdown("<div style='margin-top: 22px;'></div>", unsafe_allow_html=True)

# 4. CHIPS DE NAVEGACIÓN RÁPIDA
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
    st.page_link("pages/remates.py", label="Remates & Flash", use_container_width=True)

st.markdown("<div style='margin-top: 34px;'></div>", unsafe_allow_html=True)

# 5. SECCIÓN PRINCIPAL: PERFIL DE USUARIO Y PREFERENCIAS
col_title_text, col_title_back = st.columns([7, 3], vertical_alignment="center")
with col_title_text:
    st.markdown(clean_html("""
        <div class="pt-title">Mi perfil</div>
        <div class="pt-lede">Tus datos, tus fragancias monitoreadas y cómo quieres recibir las alertas de precio.</div>
    """), unsafe_allow_html=True)
with col_title_back:
    st.page_link("app.py", label="Volver al catálogo")

st.markdown("<div style='margin-top: 22px;'></div>", unsafe_allow_html=True)

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
    badge_alerta = f"<span class='pt-alert-on'>{svg_bell_active} Alertas activadas ({u_umbral}%)</span>"
elif u_email and not u_alerta:
    badge_alerta = f"<span class='pt-alert-off'>{svg_bell_off} Alertas desactivadas</span>"
else:
    badge_alerta = f"<span class='pt-alert-off'>{svg_bell_off} Agrega un correo para recibir alertas</span>"


# =============================================================================
# BLOQUE 4: TARJETA DE PERFIL Y SUBIDA SEGURA DE AVATAR EN LA NUBE
# =============================================================================
profile_card = st.container(key="profile_card")
with profile_card:
    col_av, col_details = st.columns([1.7, 8.3], vertical_alignment="center", gap="large")

with col_av:
    # Zona de foto: al hacer clic (o arrastrar una imagen encima) se abre el selector de archivos del PC
    # y la nueva foto se sube y guarda automáticamente, sin pasos adicionales.
    with st.container(key="avatar_box"):
        st.markdown(clean_html(f'''
        <div class="avatar-click-zone" title="Haz clic para elegir una nueva foto de perfil o GIF desde tu PC">
            <img src="{avatar_src}" class="profile-avatar-img" alt="{u_nombre_safe}">
            <div class="avatar-overlay-badge">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg>
                <div>Cambiar foto</div>
            </div>
            <div class="avatar-camera-dot">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg>
            </div>
        </div>
        <div class="avatar-change-pill">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="{text_color}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M17 3a2.85 2.85 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/></svg>
            Cambiar foto
        </div>
        '''), unsafe_allow_html=True)

        quick_file = st.file_uploader(
            "Cambiar foto de perfil",
            type=["png", "jpg", "jpeg", "gif", "webp"],
            key="avatar_quick_uploader",
            label_visibility="collapsed",
        )
    st.markdown("<div class='avatar-help'>PNG, JPG, GIF o WEBP desde tu PC.<br>Se guarda al instante.</div>", unsafe_allow_html=True)

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
    <div class="profile-top">
        <div>
            <div class="profile-name">{u_nombre_safe}</div>
            <div class="profile-contact">
                <div class="profile-contact-item">{svg_mail} {u_email_display}</div>
                <div class="profile-contact-item">{svg_phone} {u_telefono_display}</div>
                <div class="profile-contact-item">{svg_pin} {u_ubicacion_safe}</div>
            </div>
        </div>
        <div>{badge_alerta}</div>
    </div>
    <div class="profile-bio">{u_bio_display}</div>
    '''), unsafe_allow_html=True)


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
    st.markdown(f"<div class='pt-section-title'>{svg_heart_header} Mis fragancias favoritas</div>", unsafe_allow_html=True)
    st.markdown("<div class='pt-section-help'>Tus fragancias guardadas se sincronizan con tu cuenta y comparan el mejor precio vigente en Chile frente al valor que tenían cuando iniciaste el seguimiento.</div>", unsafe_allow_html=True)

    fav_items = obtener_favoritos_usuario(u_ident) if u_ident else []
    st.session_state['favoritos'] = [int(it['id']) for it in fav_items if it.get('id')]
    st.session_state['_favoritos_cargados_para'] = str(u_ident)  # esta lista manda: corazones llenos en tus favoritos

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
                        f"<span class='pt-price-drop'>{svg_trend_down} ¡Bajó {pct_desc:.0f}%! ${p_min:,.0f} CLP</span>"
                        f"<span class='pt-price-sub'>Guardado en ${p_guardado:,.0f} CLP</span>"
                    ).replace(",", ".")
                else:
                    sub_guardado = (
                        f"<span class='pt-price-sub'>Base monitoreada: ${p_guardado:,.0f} CLP</span>".replace(",", ".")
                        if p_guardado > 0 else ""
                    )
                    badge_precio = f"<span class='pt-price-now'>Mejor precio: ${p_min:,.0f} CLP</span>".replace(",", ".") + sub_guardado
            else:
                badge_precio = "<span class='pt-price-out'>Temporalmente agotado en tiendas</span>"

            with st.container(key=f"fav_row_{p_id}"):
                col_f0, col_f1, col_f2, col_f3, col_f4 = st.columns([0.55, 3, 2.5, 2, 1.5], vertical_alignment="center")
            with col_f0:
                boton_corazon(p_id, "perfil", item.get('nombre', ''), en_linea=True)
            with col_f1:
                # El nombre del perfume abre su comparativa
                with st.container(key=f"pcard_favrow_{p_id}"):
                    st.markdown(f"<div class='fav-name'>{p_nombre_safe}</div><div class='fav-brand'>{p_marca_safe}</div>", unsafe_allow_html=True)
                    boton_abrir_perfume(p_id, "perfil")
            with col_f2:
                st.markdown(f"<div>{badge_precio}</div>", unsafe_allow_html=True)
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
    st.markdown(f"<div class='pt-section-title'>{svg_edit_header} Completar y modificar datos personales</div>", unsafe_allow_html=True)
    st.markdown("<div class='pt-section-help'>Puedes cambiar tu foto aquí o directamente haciendo clic sobre ella en la tarjeta de arriba.</div>", unsafe_allow_html=True)

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
    st.markdown(f"<div class='pt-section-title'>{svg_notif_header} Alertas inteligentes por correo electrónico</div>", unsafe_allow_html=True)
    st.markdown("<div class='pt-section-help'>Configura cuándo deseas recibir avisos automáticos cuando tus fragancias monitoreadas bajen de precio o recuperen stock en tiendas chilenas auditadas.</div>", unsafe_allow_html=True)

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
st.markdown(clean_html("""
    <div class="pt-footer">
        <div class="pt-footer-mark">Perfume<strong>Trending</strong></div>
        <div class="pt-footer-copy">© 2026 Perfume Trending. Todos los derechos reservados.</div>
    </div>
"""), unsafe_allow_html=True)
