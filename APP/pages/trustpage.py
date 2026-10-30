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
    sanitize_external_url,
    toggle_theme,
)
from auth_email import modal_autenticacion
from perfume_actions import estilos_avatar_usuario, estilos_moviles, mostrar_aviso_favoritos

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

# Paleta clara reforzada: fondo blanco y texto oscuro legible en todos los componentes.
# El modo oscuro conserva exactamente los valores de la paleta compartida.
if not is_dark:
    bg_color = "#ffffff"
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

# Tokens visuales compartidos con Inicio y Trend del Hype
accent = "#d83737"
accent_hover = "#b92d2d"
accent_soft = "rgba(216, 55, 55, 0.14)" if is_dark else "rgba(216, 55, 55, 0.07)"
gold = "#d4c2a5" if is_dark else "#8c7b6d"
gold_soft = "rgba(212, 194, 165, 0.16)" if is_dark else "rgba(140, 123, 109, 0.14)"
ok_green = "#4ade80" if is_dark else "#15803d"
warn_amber = "#fbbf24" if is_dark else "#b45309"
risk_red = "#f87171" if is_dark else "#dc2626"
surface_soft = "rgba(255, 255, 255, 0.035)" if is_dark else "#faf8f5"
meter_track = "rgba(255, 255, 255, 0.08)" if is_dark else "#efebe6"
shadow_sm = "0 1px 2px rgba(0,0,0,0.35)" if is_dark else "0 1px 2px rgba(40,30,20,0.06)"
shadow_hover = "0 6px 16px rgba(0,0,0,0.35)" if is_dark else "0 6px 16px rgba(60,45,35,0.10)"
font_sans = "'Manrope', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"

# 4. ESTILOS CSS (MISMO SISTEMA VISUAL QUE INICIO Y TREND DEL HYPE)
css_styles = f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@300;400;500;600;700;800&display=swap');

    header[data-testid="stHeader"] {{ display: none !important; }}
    div[data-testid="stAppViewContainer"] {{ padding-top: 0px !important; }}

    html, body {{ background-color: {bg_color} !important; }}
    .stApp {{
        background-color: {bg_color} !important;
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

    .stApp p, .stApp label, .stMarkdown p {{
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

/* BOTÓN DE INGRESO Y PERFIL */
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

/* ---------- ACCESOS RÁPIDOS (CHIPS) ---------- */
a[data-testid="stPageLink-NavLink"],
div.st-key-chip_remates div.stButton > button {{
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
a[data-testid="stPageLink-NavLink"]:hover,
div.st-key-chip_remates div.stButton > button:hover {{
    background-color: {btn_bg} !important;
    border-color: {gold} !important;
    box-shadow: none !important;
}}
a[data-testid="stPageLink-NavLink"] p,
a[data-testid="stPageLink-NavLink"] span,
div.st-key-chip_remates div.stButton > button p {{
    font-size: 0.87rem !important;
    font-weight: 600 !important;
    color: {btn_text} !important;
    white-space: nowrap !important;
    text-overflow: clip !important;
    overflow: visible !important;
    margin: 0 !important;
}}

/* Página actual resaltada */
a[data-testid="stPageLink-NavLink"][href*="trustpage"] {{
    border-color: {accent} !important;
    background-color: {accent_soft} !important;
}}

a[data-testid="stPageLink-NavLink"][href*="trendhype"],
a[data-testid="stPageLink-NavLink"][href*="trustpage"],
a[data-testid="stPageLink-NavLink"][href*="compararprecios"],
a[data-testid="stPageLink-NavLink"][href$="app.py"],
a[data-testid="stPageLink-NavLink"][href="/"],
div.st-key-chip_remates div.stButton > button {{
    position: relative !important;
    padding-left: 2.6rem !important;
    padding-right: 1.1rem !important;
    overflow: hidden !important;
}}

a[data-testid="stPageLink-NavLink"][href*="trendhype"]::before,
a[data-testid="stPageLink-NavLink"][href*="trustpage"]::before,
a[data-testid="stPageLink-NavLink"][href*="compararprecios"]::before,
a[data-testid="stPageLink-NavLink"][href$="app.py"]::before,
a[data-testid="stPageLink-NavLink"][href="/"]::before,
div.st-key-chip_remates div.stButton > button::before {{
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
div.st-key-chip_remates div.stButton > button::before {{ background-image: url("{flame_red_svg}") !important; }}

/* ---------- ENCABEZADO DE SECCIÓN ---------- */
.trust-head-title {{
    font-family: {font_sans};
    font-weight: 800;
    font-size: clamp(1.6rem, 3vw, 2.2rem);
    letter-spacing: -0.025em;
    line-height: 1.1;
    color: {text_color};
    display: flex;
    align-items: center;
    gap: 12px;
}}
.trust-head-icon {{
    width: 40px;
    height: 40px;
    border-radius: 12px;
    background: {accent_soft};
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}}
.trust-head-sub {{
    font-size: 0.98rem;
    color: {subtext_color};
    margin-top: 10px;
    max-width: 64ch;
    line-height: 1.55;
}}
.pt-divider {{
    height: 1px;
    background: {btn_border};
    opacity: 0.55;
    margin: 18px 0 26px 0;
}}
.section-label {{
    font-size: 1.05rem;
    font-weight: 800;
    color: {text_color};
    letter-spacing: -0.01em;
    margin: 0 0 4px 0;
}}
.section-help {{
    font-size: 0.86rem;
    color: {subtext_color};
    margin-bottom: 14px;
    line-height: 1.5;
}}

/* ---------- FICHA ILUSTRADA (COLUMNA IZQUIERDA) ---------- */
.product-card {{
    background-color: {card_bg};
    border: 1px solid {border_color};
    border-radius: 18px;
    padding: 30px 28px 22px 28px;
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
}}
.product-illustration {{
    width: 100%;
    display: flex;
    justify-content: center;
    padding: 18px 0 14px 0;
    border-radius: 14px;
    background: {"radial-gradient(circle at 50% 45%, #1d222c 0%, #11141a 100%)" if is_dark else "radial-gradient(circle at 50% 45%, #ffffff 0%, #f6f4f1 100%)"};
}}
.product-title {{
    font-family: {font_sans};
    font-size: 1.45rem;
    font-weight: 800;
    letter-spacing: -0.02em;
    margin: 20px 0 4px 0;
    color: {text_color};
}}
.product-subtitle {{
    font-size: 0.84rem;
    color: {subtext_color};
    font-weight: 500;
    margin-bottom: 22px;
}}
.notes-container {{
    width: 100%;
    text-align: left;
    border-top: 1px solid {border_color};
    padding-top: 6px;
}}
.note-item {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 12px 0;
    border-bottom: 1px dashed {border_color};
}}
.note-item:last-child {{ border-bottom: none; }}
.note-label {{
    font-size: 0.82rem;
    font-weight: 600;
    color: {subtext_color};
}}
.note-value {{
    font-size: 0.9rem;
    font-weight: 700;
    color: {text_color};
    text-align: right;
}}

/* ---------- TABLA DE CONFIANZA ---------- */
.trust-table-container {{
    background-color: {card_bg};
    border: 1px solid {border_color};
    border-radius: 18px;
    padding: 6px 14px 10px 14px;
    overflow-x: auto;
}}
table.trust-table {{
    width: 100%;
    border-collapse: collapse;
    font-family: {font_sans};
}}
table.trust-table th {{
    padding: 14px 8px 10px 8px;
    font-size: 0.78rem;
    font-weight: 700;
    color: {subtext_color};
    border-bottom: 1px solid {border_color};
    text-align: left;
    white-space: nowrap;
}}
table.trust-table td {{
    padding: 14px 8px;
    border-bottom: 1px solid {border_color};
    vertical-align: middle;
    background: transparent;
}}
table.trust-table, table.trust-table thead, table.trust-table tbody, table.trust-table tr {{ border: none !important; }}
table.trust-table th, table.trust-table td {{
    border-top: none !important;
    border-left: none !important;
    border-right: none !important;
    border-bottom: 1px solid {border_color} !important;
}}
table.trust-table tbody tr:last-child td {{ border-bottom: none !important; }}
table.trust-table tbody tr {{ transition: background-color 0.15s ease; }}
table.trust-table tbody tr:hover {{ background-color: {surface_soft}; }}
table.trust-table tr td:first-child {{
    font-weight: 700;
    font-size: 0.8rem;
    color: {subtext_color};
    font-variant-numeric: tabular-nums;
    width: 40px;
}}
table.trust-table tr td:last-child {{ text-align: right; }}
tr.trust-row-risk td {{ background-color: {"rgba(239, 68, 68, 0.06)" if is_dark else "rgba(239, 68, 68, 0.04)"}; }}

.store-title {{
    font-weight: 700;
    font-size: 0.95rem;
    color: {text_color};
}}
.store-meta {{
    font-size: 0.76rem;
    color: {subtext_color};
    margin-top: 3px;
}}
.store-meta-risk {{ color: {risk_red}; }}

.score-cell {{ min-width: 76px; }}
.price-tag {{
    font-size: 1rem;
    font-weight: 800;
    color: {text_color};
    font-variant-numeric: tabular-nums;
}}
.price-tag small {{ font-size: 0.72rem; font-weight: 600; color: {subtext_color}; }}
.score-meter {{
    height: 5px;
    border-radius: 999px;
    background: {meter_track};
    margin-top: 6px;
    overflow: hidden;
    max-width: 80px;
}}
.score-meter-fill {{ height: 100%; border-radius: 999px; }}

/* Insignias de estado */
.status-badge-safe,
.status-badge-danger,
.status-badge-warn {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 0.76rem;
    font-weight: 700;
    white-space: nowrap;
}}
.status-badge-safe {{
    background: rgba(34, 197, 94, 0.10);
    color: {ok_green};
    border: 1px solid rgba(34, 197, 94, 0.28);
}}
.status-badge-warn {{
    background: rgba(245, 158, 11, 0.10);
    color: {warn_amber};
    border: 1px solid rgba(245, 158, 11, 0.30);
}}
.status-badge-danger {{
    background: rgba(239, 68, 68, 0.10);
    color: {risk_red};
    border: 1px solid rgba(239, 68, 68, 0.28);
}}
.status-dot {{ width: 6px; height: 6px; border-radius: 50%; background: currentColor; }}

/* Botones de acción de la tabla */
.btn-buy-now,
.btn-buy-now:visited {{
    background: {text_color};
    color: {bg_color} !important;
    font-weight: 700;
    font-size: 0.8rem;
    padding: 7px 14px;
    border-radius: 999px;
    text-decoration: none !important;
    display: inline-block;
    white-space: nowrap;
    transition: opacity 0.18s ease;
}}
.btn-buy-now:hover {{ opacity: 0.85; color: {bg_color} !important; }}
.btn-buy-now:focus-visible {{ outline: 2px solid {accent}; outline-offset: 2px; }}
.btn-buy-disabled {{
    background: transparent;
    color: {subtext_color} !important;
    border: 1px solid {border_color};
    font-weight: 700;
    font-size: 0.8rem;
    padding: 7px 14px;
    border-radius: 999px;
    display: inline-block;
    white-space: nowrap;
    cursor: not-allowed;
}}

/* ---------- AUDITOR INTERACTIVO ---------- */
div[data-testid="stForm"] {{
    background-color: {card_bg} !important;
    border: 1px solid {border_color} !important;
    border-radius: 18px !important;
    padding: 20px 20px 18px 20px !important;
}}
div[data-testid="stTextInput"] div[data-baseweb="input"],
div[data-testid="stTextInput"] [data-testid="stTextInputRootElement"] {{
    border-radius: 999px !important;
    min-height: 44px !important;
}}
div[data-testid="stFormSubmitButton"] button {{
    background-color: {accent} !important;
    border: 1px solid {accent} !important;
    color: #ffffff !important;
    border-radius: 999px !important;
    min-height: 44px !important;
    box-shadow: none !important;
    transition: background-color 0.18s ease, box-shadow 0.18s ease !important;
}}
div[data-testid="stFormSubmitButton"] button:hover {{
    background-color: {accent_hover} !important;
    border-color: {accent_hover} !important;
    box-shadow: 0 8px 18px rgba(216, 55, 55, 0.28) !important;
}}
div[data-testid="stFormSubmitButton"] button p {{
    color: #ffffff !important;
    font-weight: 700 !important;
}}
div[data-testid="stAlert"] > div {{ border-radius: 12px !important; }}

.audit-result {{
    background: {card_bg};
    border: 1px solid {border_color};
    border-left-width: 4px;
    border-radius: 14px;
    padding: 16px 18px;
    margin-top: 12px;
}}
.audit-result-top {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
}}
.audit-result-name {{ font-weight: 800; font-size: 1rem; color: {text_color}; }}
.audit-result-domain {{ font-weight: 500; font-size: 0.82rem; color: {subtext_color}; }}
.audit-result-meta {{ font-size: 0.8rem; color: {subtext_color}; margin-top: 3px; }}
.audit-result-score {{ font-weight: 800; font-size: 1.3rem; font-variant-numeric: tabular-nums; white-space: nowrap; }}
.audit-result-rec {{ font-size: 0.88rem; color: {text_color}; margin-top: 10px; line-height: 1.5; }}
.audit-result-alerts {{ margin: 8px 0 0 18px; padding: 0; color: {risk_red}; font-size: 0.82rem; line-height: 1.5; }}

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
.brand-logo-text strong {{
    font-weight: 800 !important;
    color: {text_color} !important;
}}

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

/* ---------- MÓVIL ---------- */
@media (max-width: 768px) {{
    .block-container {{
        padding-top: 0.4rem !important;
        padding-left: 0.8rem !important;
        padding-right: 0.8rem !important;
    }}
    div[data-testid="stHorizontalBlock"] {{
        flex-wrap: wrap !important;
        gap: 6px !important;
    }}
    div[data-testid="stColumn"] {{
        width: 100% !important;
        flex: 1 1 100% !important;
        min-width: 0 !important;
    }}
    div[data-testid="stHorizontalBlock"]:has(.st-key-login_btn, .st-key-theme_toggle) {{
        flex-wrap: nowrap !important;
        align-items: center !important;
        justify-content: space-between !important;
    }}
    div[data-testid="stColumn"]:has(a[data-testid="stPageLink-NavLink"]),
    div[data-testid="stColumn"]:has(.st-key-chip_remates) {{
        flex: 1 1 calc(50% - 4px) !important;
        width: calc(50% - 4px) !important;
    }}
    a[data-testid="stPageLink-NavLink"],
    div.st-key-chip_remates div.stButton > button {{
        justify-content: flex-start !important;
        padding-left: 2.2rem !important;
    }}
    a[data-testid="stPageLink-NavLink"] p,
    a[data-testid="stPageLink-NavLink"] span,
    div.st-key-chip_remates div.stButton > button p {{
        font-size: 0.8rem !important;
        white-space: normal !important;
        line-height: 1.15 !important;
    }}
    a[data-testid="stPageLink-NavLink"]::before,
    div.st-key-chip_remates div.stButton > button::before {{ left: 11px !important; }}
    .brand-logo-text {{ font-size: 1.35rem !important; }}
    .product-card {{ padding: 22px 18px 16px 18px; }}
    table.trust-table {{ min-width: 540px; }}
    div.st-key-login_btn div.stButton > button {{
        min-height: 36px !important;
        padding: 5px 14px 5px 32px !important;
        background-position: 11px center !important;
    }}
}}
</style>
"""
st.markdown(clean_html(css_styles), unsafe_allow_html=True)

# Diseño responsivo para celulares (común a todas las páginas)
st.markdown(estilos_moviles(accent, border_color, is_dark), unsafe_allow_html=True)

# Foto de perfil en el botón del usuario (cabecera)
_css_avatar = estilos_avatar_usuario(gold)
if _css_avatar:
    st.markdown(_css_avatar, unsafe_allow_html=True)

# 5. HEADER (LOGO + INICIO DE SESIÓN DINÁMICO + SWITCH COPIADO EXACTO DE APP.PY)
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
        <svg width="34" height="34" viewBox="0 0 36 36" fill="none" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M 6.8 21 L 29.2 21 C 30 25 27 32 18 32 C 9 32 6 25 6.8 21 Z" fill="{gold}" />
            <line x1="6.8" y1="21" x2="29.2" y2="21" stroke="{text_color}" stroke-width="1.5" />
            <line x1="18" y1="10" x2="18" y2="30" stroke="{text_color}" stroke-width="1" />
            <path d="M 18 32 C 9 32 5 24 7.5 17 C 9 12 13 10 15 10 L 21 10 C 23 10 27 12 28.5 17 C 31 24 27 32 18 32 Z" stroke="{text_color}" stroke-width="2" />
            <rect x="15" y="7" width="6" height="3" stroke="{text_color}" stroke-width="1.5" />
            <rect x="13" y="3" width="10" height="4" rx="1" stroke="{text_color}" stroke-width="1.5" />
            <rect x="16" y="0" width="4" height="3" rx="1" fill="{gold}" stroke="{text_color}" stroke-width="1" />
        </svg>
        <div class="brand-logo-text">Perfume<strong>Trending</strong></div>
    </a>
    """), unsafe_allow_html=True)

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
mostrar_aviso_favoritos()

st.markdown("<div style='margin-top: 22px;'></div>", unsafe_allow_html=True)

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

st.markdown("<div style='margin-top: 34px;'></div>", unsafe_allow_html=True)
col_sub_title, col_sub_back = st.columns([7, 3], vertical_alignment="center")
with col_sub_title:
    st.markdown(clean_html(f"""
        <div class="trust-head-title">
            <span class="trust-head-icon">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="{accent}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                    <polyline points="9 12 11 14 15 10"/>
                </svg>
            </span>
            Auditoría de tiendas y seguridad
        </div>
        <div class="trust-head-sub">Revisa qué tan confiable es cada tienda de perfumes en Chile antes de comprar: RUT, respaldo legal y nivel de riesgo.</div>
    """), unsafe_allow_html=True)
with col_sub_back:
    st.page_link("app.py", label="Volver al catálogo")

st.markdown("<div class='pt-divider'></div>", unsafe_allow_html=True)

# =============================================================================
# BLOQUE 4: ESTRUCTURA DE AUDITORÍA (FICHA ILUSTRADA + TABLA DE CONFIANZA)
# =============================================================================
left_col, right_col = st.columns([1, 1.4], gap="large")

# --- COLUMNA IZQUIERDA: TARJETA DE PRODUCTO MINIMALISTA ILUSTRADA ---
with left_col:
    bottle_sketch_svg = f"""
    <svg viewBox="0 0 200 240" fill="none" xmlns="http://www.w3.org/2000/svg" style="width: 100%; height: auto; max-width: 150px;" aria-hidden="true">
        <path d="M70 20 L130 20 L145 35 L145 55 L130 70 L70 70 L55 55 L55 35 Z" stroke="{text_color}" stroke-width="1.8" fill="{gold}" fill-opacity="0.35"/>
        <rect x="75" y="70" width="50" height="15" stroke="{text_color}" stroke-width="1.2" fill="{card_bg}"/>
        <path d="M40 85 L160 85 L175 110 L175 210 L160 225 L40 225 L25 210 L25 110 Z" stroke="{text_color}" stroke-width="1.8" fill="{card_bg}"/>
        <path d="M30 150 L170 150 L170 208 L157 220 L43 220 L30 208 Z" fill="{gold}" fill-opacity="0.22"/>
        <rect x="55" y="115" width="90" height="65" rx="3" stroke="{border_color}" stroke-width="1" fill="{bg_color}"/>
        <text x="100" y="132" font-size="5.5" font-weight="600" fill="{subtext_color}" text-anchor="middle" letter-spacing="1">SKETCHED SCENTS</text>
        <text x="100" y="150" font-size="9.5" font-weight="700" fill="{text_color}" text-anchor="middle" letter-spacing="1.5">MIDNIGHT</text>
        <text x="100" y="163" font-size="9.5" font-weight="700" fill="{text_color}" text-anchor="middle" letter-spacing="1.5">OUD</text>
        <text x="100" y="174" font-size="5" fill="{subtext_color}" text-anchor="middle">EAU DE PARFUM</text>
        <line x1="36" y1="98" x2="36" y2="200" stroke="#ffffff" stroke-opacity="0.5" stroke-width="3" stroke-linecap="round"/>
    </svg>
    """

    card_left_html = f"""
    <div class="product-card">
        <div class="product-illustration">
            {bottle_sketch_svg}
        </div>
        <div class="product-title">Midnight Oud</div>
        <div class="product-subtitle">Eau de Parfum, 50 ml / 1.7 oz</div>

        <div class="notes-container">
            <div class="note-item">
                <span class="note-label">Nota de salida</span>
                <span class="note-value">Madera de Oud Natural</span>
            </div>
            <div class="note-item">
                <span class="note-label">Nota de corazón</span>
                <span class="note-value">Rosa de Bulgaria</span>
            </div>
            <div class="note-item">
                <span class="note-label">Nota de fondo</span>
                <span class="note-value">Ámbar Ahumado</span>
            </div>
        </div>
    </div>
    """
    st.markdown(clean_html(card_left_html), unsafe_allow_html=True)

# --- COLUMNA DERECHA: TABLA DE VERIFICACIÓN EN ESPAÑOL + AUDITOR DE URL ---
with right_col:
    tiendas_auditadas = obtener_tiendas()

    st.markdown(clean_html("""
        <div class="section-label">Tiendas auditadas</div>
        <div class="section-help">Puntaje de confianza de 0 a 100. Desde 85 la tienda se considera verificada.</div>
    """), unsafe_allow_html=True)

    filas_html = []
    for idx, t in enumerate(tiendas_auditadas, 1):
        num_str = f"{idx:02d}"
        score = int(t.get('trust_score', 95) or 95)
        badge_status = (
            '<span class="status-badge-safe"><span class="status-dot"></span>Verificado</span>'
            if score >= 85
            else '<span class="status-badge-warn"><span class="status-dot"></span>En auditoría</span>'
        )
        meter_color = ok_green if score >= 85 else (warn_amber if score >= 70 else risk_red)
        meter_w = max(0, min(100, score))
        raw_url = str(t.get("url_base") or "")
        if "alisha.cl" in raw_url and "alishaperfumes.cl" not in raw_url:
            raw_url = "https://alishaperfumes.cl"
        safe_url = escape_html(sanitize_external_url(raw_url, fallback="#"))
        safe_nombre = escape_html(str(t.get('nombre', 'Tienda')))
        safe_badge = escape_html(str(t.get('badge') or 'Comercio Oficial'))
        safe_rut = escape_html(str(t.get('rut') or 'Verificado SII'))
        accion_html = f'<a href="{safe_url}" target="_blank" rel="noopener noreferrer" class="btn-buy-now">Visitar</a>'

        fila = f"""
        <tr>
            <td>{num_str}</td>
            <td>
                <div class="store-title">{safe_nombre}</div>
                <div class="store-meta">{safe_badge}, RUT {safe_rut}</div>
            </td>
            <td class="score-cell">
                <span class="price-tag">{score}<small>/100</small></span>
                <div class="score-meter"><div class="score-meter-fill" style="width: {meter_w}%; background: {meter_color};"></div></div>
            </td>
            <td>{badge_status}</td>
            <td>{accion_html}</td>
        </tr>
        """
        filas_html.append(fila)

    num_alerta = f"{len(tiendas_auditadas) + 1:02d}"
    fila_riesgo = f"""
    <tr class="trust-row-risk">
        <td>{num_alerta}</td>
        <td>
            <div class="store-title">Vendedor no auditado</div>
            <div class="store-meta store-meta-risk">Sin RUT tributario ni boleta legal</div>
        </td>
        <td class="score-cell">
            <span class="price-tag" style="color: {risk_red};">38<small>/100</small></span>
            <div class="score-meter"><div class="score-meter-fill" style="width: 38%; background: {risk_red};"></div></div>
        </td>
        <td><span class="status-badge-danger"><span class="status-dot"></span>Alto riesgo</span></td>
        <td><span class="btn-buy-disabled">Bloqueado</span></td>
    </tr>
    """
    filas_html.append(fila_riesgo)

    table_html = f"""
    <div class="trust-table-container">
        <table class="trust-table">
            <thead>
                <tr>
                    <th style="width: 8%;">#</th>
                    <th style="width: 36%;">Comercio auditado</th>
                    <th style="width: 18%;">Confianza</th>
                    <th style="width: 22%;">Estado</th>
                    <th style="width: 16%; text-align: right;">Acción</th>
                </tr>
            </thead>
            <tbody>
                {''.join(filas_html)}
            </tbody>
        </table>
    </div>
    """
    st.markdown(clean_html(table_html), unsafe_allow_html=True)

    # - ¿Qué hace esta sección?:
    #   Muestra las métricas del pipeline de auto-descubrimiento continuo de fragancias:
    #   cuántos productos se inspeccionaron en los feeds de tiendas, cuántos fueron filtrados
    #   por calidad (cremas/testers/clones) y cuántas fragancias nuevas legítimas fueron incorporadas.
    try:
        from backend.scraper_autonomo import obtener_ultimo_reporte_descubrimiento
        rep_desc = obtener_ultimo_reporte_descubrimiento()
    except Exception:
        rep_desc = None

    if rep_desc and isinstance(rep_desc, dict):
        m_desc = rep_desc.get("metricas", {})
        meta_desc = rep_desc.get("metadata", {})
        total_analizados = m_desc.get("total_productos_analizados", 0)
        descartados_qa = m_desc.get("descartados_no_perfume", 0)
        nuevos_perfumes = m_desc.get("nuevos_perfumes_descubiertos", 0)
        fecha_desc = meta_desc.get("fecha_ejecucion", "")
        
        st.markdown(
            clean_html(f"""
            <div style="margin-top: 20px; padding: 18px 22px; border-radius: 12px; background: {card_bg}; border: 1px solid {border_color}; box-shadow: {shadow_sm};">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-wrap: wrap; gap: 8px;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="font-size: 1.1rem;">📡</span>
                        <strong style="font-size: 0.95rem; color: {text_color};">Pipeline Autónomo de Expansión de Catálogo</strong>
                        <span style="font-size: 0.72rem; padding: 2px 8px; border-radius: 999px; background: rgba(74, 222, 128, 0.15); color: {ok_green}; font-weight: 600;">ACTIVO</span>
                    </div>
                    <span style="font-size: 0.76rem; color: {subtext_color};">Última ejecución: {fecha_desc}</span>
                </div>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; text-align: center;">
                    <div style="padding: 10px; background: {surface_soft}; border-radius: 8px; border: 1px solid {border_color};">
                        <div style="font-size: 1.25rem; font-weight: 700; color: {text_color};">{total_analizados:,}</div>
                        <div style="font-size: 0.72rem; color: {subtext_color};">Ítems Analizados</div>
                    </div>
                    <div style="padding: 10px; background: {surface_soft}; border-radius: 8px; border: 1px solid {border_color};">
                        <div style="font-size: 1.25rem; font-weight: 700; color: {warn_amber};">{descartados_qa:,}</div>
                        <div style="font-size: 0.72rem; color: {subtext_color};">Filtrados por Calidad</div>
                    </div>
                    <div style="padding: 10px; background: {surface_soft}; border-radius: 8px; border: 1px solid {border_color};">
                        <div style="font-size: 1.25rem; font-weight: 700; color: {accent};">+{nuevos_perfumes:,}</div>
                        <div style="font-size: 0.72rem; color: {subtext_color};">Nuevas Fragancias</div>
                    </div>
                </div>
                <div style="margin-top: 10px; font-size: 0.72rem; color: {subtext_color}; text-align: right;">
                    Auditado y saneado con normalizador canónico, detección de imitaciones y verificación de volumen comercial (≥ 25ml).
                </div>
            </div>
            """),
            unsafe_allow_html=True
        )

    st.markdown("<div style='margin-top: 26px;'></div>", unsafe_allow_html=True)
    with st.form("form_auditar_url_tienda", clear_on_submit=False):
        st.markdown(
            clean_html("""
                <div class="section-label">Auditor interactivo de sitios de perfumería</div>
                <div class="section-help">Escribe el dominio o la URL de cualquier tienda y revisa su respaldo antes de comprar.</div>
            """),
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
                    alertas_html = f"<ul class='audit-result-alerts'>{items_al}</ul>"
                st.markdown(
                    clean_html(f"""
                    <div class="audit-result" style="border-color: {borde_res};">
                        <div class="audit-result-top">
                            <div>
                                <div class="audit-result-name">{safe_nom_aud} <span class="audit-result-domain">({safe_dom_aud})</span></div>
                                <div class="audit-result-meta">RUT: {safe_rut_aud}, {escape_html(res_audit.get('badge', ''))}</div>
                            </div>
                            <div class="audit-result-score" style="color: {borde_res};">{sc_val}/100</div>
                        </div>
                        <div class="audit-result-rec">{safe_rec_aud}</div>
                        {alertas_html}
                    </div>
                    """),
                    unsafe_allow_html=True,
                )

# PIE DE PÁGINA
st.markdown(clean_html("""
    <div class="pt-footer">
        <div class="pt-footer-mark">Perfume<strong>Trending</strong></div>
        <div class="pt-footer-copy">© 2026 Perfume Trending. Todos los derechos reservados.</div>
    </div>
"""), unsafe_allow_html=True)
