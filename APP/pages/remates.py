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

# Paleta clara reforzada: fondo blanco y texto oscuro legible en todos los componentes.
# El modo oscuro conserva exactamente los valores de la paleta compartida.
if not is_dark:
    app_bg = "#ffffff"
    app_bg_css = "background: #ffffff !important; background-color: #ffffff !important;"
    card_bg = "#ffffff"
    border_color = "#e6e1db"
    text_color = "#1c1917"
    subtext_color = "#6b6159"
    btn_bg = "#ffffff"
    btn_text = "#1c1917"
    btn_border = "#d6cec5"
    input_bg = "#ffffff"
    input_text = "#1c1917"
    input_border = "#d6cec5"

# Tokens visuales compartidos con el resto del sitio
accent = "#d83737"
accent_hover = "#b92d2d"
accent_soft = "rgba(216, 55, 55, 0.14)" if is_dark else "rgba(216, 55, 55, 0.07)"
gold = "#d4c2a5" if is_dark else "#8c7b6d"
gold_soft = "rgba(212, 194, 165, 0.16)" if is_dark else "rgba(140, 123, 109, 0.14)"
ok_green = "#4ade80" if is_dark else "#15803d"
risk_red = "#f87171" if is_dark else "#dc2626"
surface_soft = "rgba(255, 255, 255, 0.035)" if is_dark else "#faf8f5"
img_stage_bg = "radial-gradient(circle at 50% 45%, #1d222c 0%, #11141a 100%)" if is_dark else "radial-gradient(circle at 50% 45%, #ffffff 0%, #f6f4f1 100%)"
shadow_sm = "0 1px 2px rgba(0,0,0,0.35)" if is_dark else "0 1px 2px rgba(40,30,20,0.06)"
shadow_hover = "0 6px 16px rgba(0,0,0,0.35)" if is_dark else "0 6px 16px rgba(60,45,35,0.10)"
font_sans = "'Manrope', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"

_search_svg = (
    f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" '
    f'stroke="{subtext_color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    f'<circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.2" y2="16.2"/></svg>'
)
search_icon_svg = "data:image/svg+xml;base64," + base64.b64encode(_search_svg.encode("utf-8")).decode("ascii")

# 2. CSS ADAPTABLE Y ESTILOS DE LA PÁGINA (MISMO SISTEMA VISUAL QUE EL RESTO DEL SITIO)
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
    div[role="dialog"] {{
        background-color: {card_bg} !important;
        color: {text_color} !important;
        border: 1px solid {border_color} !important;
        border-radius: 16px !important;
    }}
    div[role="dialog"] h2, div[role="dialog"] h2 *, div[role="dialog"] p, div[role="dialog"] label {{
        color: {text_color} !important;
    }}
    div[role="dialog"] button[aria-label="Close"] svg {{ color: {text_color} !important; fill: {text_color} !important; }}

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

    /* ---------- BOTÓN INGRESAR Y CABECERA ---------- */
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

    /* El switch conserva exactamente el comportamiento visual que tenía en esta página */
    div.st-key-theme_toggle div.stButton > button {{
        background-color: {btn_bg} !important;
        border: 1px solid {btn_border} !important;
        border-radius: 8px !important;
        box-shadow: none !important;
        outline: none !important;
        transform: none !important;
    }}
    div.st-key-theme_toggle div.stButton > button:hover,
    div.st-key-theme_toggle div.stButton > button:focus,
    div.st-key-theme_toggle div.stButton > button:focus-visible {{
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        outline: none !important;
        transform: none !important;
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

    a[data-testid="stPageLink-NavLink"][href*="remates"] {{
        border-color: {accent} !important;
        background-color: {accent_soft} !important;
    }}
    a[data-testid="stPageLink-NavLink"][href*="remates"] {{
        position: relative !important;
        padding-left: 2.6rem !important;
        padding-right: 1.1rem !important;
        overflow: hidden !important;
    }}
    a[data-testid="stPageLink-NavLink"][href*="remates"]::before {{
        content: '' !important;
        position: absolute !important;
        left: 15px !important;
        top: 50% !important;
        transform: translateY(-50%) !important;
        width: 16px !important;
        height: 16px !important;
        background-image: url("{flame_red_svg}") !important;
        background-repeat: no-repeat !important;
        background-size: contain !important;
        background-position: center !important;
        z-index: 1 !important;
    }}

    /* ---------- ENCABEZADO DE SECCIÓN ---------- */
    .pt-title {{
        display: flex;
        align-items: center;
        gap: 12px;
        font-family: {font_sans};
        font-weight: 800;
        font-size: clamp(1.6rem, 3vw, 2.2rem);
        letter-spacing: -0.025em;
        line-height: 1.1;
        color: {text_color};
    }}
    .pt-title-icon {{
        width: 40px;
        height: 40px;
        border-radius: 12px;
        background: {accent_soft};
        display: inline-flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
    }}
    .pt-lede {{
        font-size: 0.98rem;
        color: {subtext_color};
        margin-top: 10px;
        max-width: 62ch;
        line-height: 1.55;
    }}
    .pt-meta {{
        font-size: 0.9rem;
        color: {subtext_color};
        margin-bottom: 16px;
    }}
    .pt-meta b {{ color: {text_color}; font-weight: 700; }}

    /* ---------- FILTROS ---------- */
    div[data-baseweb="select"] > div,
    [data-testid="stSelectbox"] div[role="group"] {{
        background-color: {input_bg} !important;
        border: 1px solid {input_border} !important;
        border-radius: 999px !important;
        min-height: 46px !important;
        box-shadow: none !important;
        color: {input_text} !important;
        padding-left: 6px !important;
    }}
    div[data-baseweb="select"] > div:focus-within,
    [data-testid="stSelectbox"] div[role="group"]:focus-within {{
        border-color: {gold} !important;
        box-shadow: 0 0 0 3px {gold_soft} !important;
    }}
    div[data-baseweb="select"] div,
    div[data-baseweb="select"] input,
    [data-testid="stSelectbox"] input {{
        color: {input_text} !important;
        background-color: transparent !important;
    }}
    div[data-baseweb="select"] svg,
    [data-testid="stSelectbox"] button svg {{ color: {subtext_color} !important; fill: {subtext_color} !important; }}
    div[data-baseweb="popover"] ul,
    [role="listbox"] {{
        background-color: {input_bg} !important;
        border: 1px solid {border_color} !important;
        border-radius: 10px !important;
    }}
    div[data-baseweb="popover"] li, div[data-baseweb="popover"] li *,
    [role="listbox"] [role="option"], [role="listbox"] [role="option"] * {{ color: {input_text} !important; }}
    div[data-baseweb="popover"] li:hover,
    div[data-baseweb="popover"] li[aria-selected="true"],
    [role="listbox"] [role="option"]:hover,
    [role="listbox"] [role="option"][aria-selected="true"] {{ background-color: {gold_soft} !important; }}
    div[data-testid="stTextInput"]:has(input[placeholder*="Filtrar"]) div[data-baseweb="input"],
    div[data-testid="stTextInput"]:has(input[placeholder*="Filtrar"]) [data-testid="stTextInputRootElement"] {{
        border-radius: 999px !important;
        min-height: 46px !important;
        padding-left: 30px !important;
        background-image: url("{search_icon_svg}") !important;
        background-repeat: no-repeat !important;
        background-position: 16px center !important;
        background-size: 17px 17px !important;
    }}
    div[data-testid="stAlert"] > div {{ border-radius: 12px !important; }}

    /* ---------- TARJETAS DE REMATE ---------- */
    .remate-card {{
        background-color: {card_bg};
        border: 1px solid {border_color};
        border-bottom: none;
        border-radius: 16px 16px 0 0;
        padding: 14px 14px 18px 14px;
        position: relative;
        margin-bottom: 0;
        transition: border-color 0.2s ease;
    }}
    div[data-testid="stColumn"]:has(.remate-card) {{ margin-bottom: 18px; }}
    div[data-testid="stColumn"]:has(.remate-card):hover .remate-card {{ border-color: {gold}; }}

    .remate-img-box {{
        position: relative;
        width: 100%;
        height: 170px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 12px;
        background: {img_stage_bg};
        margin-bottom: 14px;
        overflow: hidden;
    }}
    .remate-img-box img {{
        max-height: 140px;
        max-width: 72%;
        object-fit: contain;
        transition: transform 0.35s ease;
        filter: {"drop-shadow(0 10px 18px rgba(0,0,0,0.45))" if is_dark else "drop-shadow(0 8px 14px rgba(60,45,35,0.12))"};
    }}
    div[data-testid="stColumn"]:has(.remate-card):hover .remate-img-box img {{ transform: scale(1.05); }}

    .badge-discount {{
        position: absolute;
        top: 10px;
        left: 10px;
        background: {accent};
        color: #ffffff;
        font-weight: 800;
        font-size: 0.85rem;
        padding: 4px 11px;
        border-radius: 999px;
        font-variant-numeric: tabular-nums;
        z-index: 2;
    }}
    .badge-timer {{
        position: absolute;
        top: 10px;
        right: 10px;
        background-color: {card_bg};
        border: 1px solid {border_color};
        color: {text_color};
        font-weight: 700;
        font-size: 0.74rem;
        padding: 3px 10px;
        border-radius: 999px;
        z-index: 2;
    }}

    .remate-title {{
        font-size: 1.05rem;
        font-weight: 800;
        color: {text_color};
        line-height: 1.3;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}
    .remate-brand {{
        font-size: 0.84rem;
        color: {subtext_color};
        margin: 2px 0 12px 0;
    }}
    .remate-store-row {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 8px;
        background-color: {surface_soft};
        padding: 8px 12px;
        border-radius: 10px;
        border: 1px solid {border_color};
        margin-bottom: 12px;
        font-size: 0.82rem;
        color: {subtext_color};
    }}
    .remate-store-row b {{ color: {text_color}; }}
    .remate-stock {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        color: {ok_green};
        font-weight: 700;
        white-space: nowrap;
    }}
    .remate-stock-dot {{ width: 7px; height: 7px; border-radius: 50%; background: {ok_green}; }}

    .price-box {{
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        gap: 8px;
        padding-top: 10px;
        border-top: 1px dashed {border_color};
    }}
    .old-price-line {{
        text-decoration: line-through;
        color: {subtext_color};
        font-size: 0.86rem;
        font-variant-numeric: tabular-nums;
    }}
    .deal-price {{
        font-size: 1.3rem;
        font-weight: 800;
        color: {ok_green};
        font-variant-numeric: tabular-nums;
        letter-spacing: -0.01em;
    }}
    .stock-badge {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-size: 0.8rem;
        color: {accent};
        font-weight: 700;
        margin-bottom: 10px;
        font-variant-numeric: tabular-nums;
    }}
    a.remate-buy-btn,
    a.remate-buy-btn:visited {{
        display: block;
        margin-top: 14px;
        text-align: center;
        background: {accent};
        color: #ffffff !important;
        font-weight: 700;
        font-size: 0.9rem;
        padding: 11px 14px;
        border-radius: 999px;
        text-decoration: none !important;
        transition: background-color 0.18s ease;
    }}
    a.remate-buy-btn:hover {{ background: {accent_hover}; color: #ffffff !important; }}
    a.remate-buy-btn:focus-visible {{ outline: 2px solid {accent}; outline-offset: 2px; }}

    /* Botón "Comparar en todas las tiendas" unido a la base de la tarjeta */
    div[class*="st-key-btn_remate_comp_"] {{ margin-top: -1rem !important; }}
    div[class*="st-key-btn_remate_comp_"] div.stButton > button {{
        background-color: {surface_soft} !important;
        border: 1px solid {border_color} !important;
        border-radius: 0 0 16px 16px !important;
        min-height: 44px !important;
        box-shadow: none !important;
    }}
    div[class*="st-key-btn_remate_comp_"] div.stButton > button p {{
        color: {text_color} !important;
        font-weight: 700 !important;
        font-size: 0.88rem !important;
    }}
    div[class*="st-key-btn_remate_comp_"] div.stButton > button:hover {{
        border-color: {gold} !important;
        background-color: {gold_soft} !important;
    }}
    div[data-testid="stColumn"]:has(.remate-card):hover div[class*="st-key-btn_remate_comp_"] div.stButton > button {{
        border-color: {gold} !important;
    }}

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
        div.st-key-login_btn div.stButton > button {{
            min-height: 36px !important;
            padding: 5px 14px 5px 32px !important;
            background-position: 11px center !important;
        }}
    }}
    </style>
""", unsafe_allow_html=True)


# 3. ENCABEZADO SUPERIOR: LOGO, PERFIL Y SWITCH DE TEMA
if st.session_state['logged_in']:
    col_logo, col_espacio, col_actions = st.columns([4.0, 0.5, 4.5], vertical_alignment="center")
    btn_col1, btn_col2 = col_actions.columns([3.5, 1.0], vertical_alignment="center")
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

st.markdown("<div style='margin-top: 22px;'></div>", unsafe_allow_html=True)

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

st.markdown("<div style='margin-top: 34px;'></div>", unsafe_allow_html=True)

# 5. TITULO PRINCIPAL DE LA SECCIÓN
col_title_text, col_title_back = st.columns([7, 3], vertical_alignment="center")
with col_title_text:
    st.markdown(clean_html(f"""
    <div class="pt-title">
        <span class="pt-title-icon">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="{accent}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
            </svg>
        </span>
        Remates y liquidaciones
    </div>
    <div class="pt-lede">Ofertas relámpago con stock limitado y descuentos excepcionales auditados en tiendas chilenas.</div>
    """), unsafe_allow_html=True)

with col_title_back:
    st.page_link("app.py", label="Volver al catálogo")

st.markdown("<div style='margin-top: 22px;'></div>", unsafe_allow_html=True)

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
        f"<div class='pt-meta'>"
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
                        <div class="remate-img-box">
                            <div class="badge-discount">-{pct_val}%</div>
                            <div class="badge-timer">{vol_ml} ml</div>
                            <img src="{img_safe}" alt="{nombre_safe}" loading="lazy">
                        </div>
                        <div class="remate-title" title="{nombre_safe}">{nombre_safe}</div>
                        <div class="remate-brand">{marca_safe}</div>
                        <div class="remate-store-row">
                            <div>Vendido por <b>{tienda_safe}</b></div>
                            <div class="remate-stock"><div class="remate-stock-dot"></div>En stock</div>
                        </div>
                        <div class="stock-badge">Ahorras {ahorro_str} CLP</div>
                        <div class="price-box">
                            <div class="old-price-line">{p_norm_str} CLP</div>
                            <div class="deal-price">{p_rem_str} CLP</div>
                        </div>
                        <a href="{safe_url}" target="_blank" rel="noopener noreferrer" class="remate-buy-btn">Ir a la oferta en {tienda_safe} ↗</a>
                    </div>
                    """
                    st.markdown(clean_html(html_card), unsafe_allow_html=True)
                    if st.button("Comparar en todas las tiendas", key=f"btn_remate_comp_{item['perfume_id']}_{idx}", use_container_width=True):
                        st.session_state['selected_perfume'] = item['perfume_id']
                        st.switch_page("pages/compararprecios.py")

# PIE DE PÁGINA
st.markdown(clean_html("""
    <div class="pt-footer">
        <div class="pt-footer-mark">Perfume<strong>Trending</strong></div>
        <div class="pt-footer-copy">© 2026 Perfume Trending. Todos los derechos reservados.</div>
    </div>
"""), unsafe_allow_html=True)
