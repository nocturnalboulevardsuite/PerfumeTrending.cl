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

# Importación de librería estándar o dependencia externa (streamlit)
import streamlit as st
# Importación de librería estándar o dependencia externa (streamlit.components.v1)
import streamlit.components.v1 as components
# Importación de librería estándar o dependencia externa (pandas)
import pandas as pd
# Importación de librería estándar o dependencia externa (sys)
import sys
# Importación de librería estándar o dependencia externa (os)
import os
# Importación de librería estándar o dependencia externa (base64)
import base64
# Importación de librería estándar o dependencia externa (urllib.parse)
import urllib.parse
# Importación de librería estándar o dependencia externa (random)
import random
# Bloque try/except para manejo seguro de errores y resiliencia operativa
try:
    # Importación de librería estándar o dependencia externa (plotly.graph_objects)
    import plotly.graph_objects as go
    # Asignamos 'HAS_PLOTLY' con True
    HAS_PLOTLY = True
except ImportError:
    # Asignamos 'HAS_PLOTLY' con False
    HAS_PLOTLY = False

# Configuración de rutas canónicas para importar backend
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Asignamos 'BASE_DIR' con os.path.dirname(APP_DIR)
BASE_DIR = os.path.dirname(APP_DIR)
# Recorremos iterativamente cada '_p' en (APP_DIR, BASE_DIR)
for _p in (APP_DIR, BASE_DIR):
    # Evaluamos la condición lógica (_p not in sys.path) para controlar el flujo
    if _p not in sys.path:
        # Ejecutamos instrucción: sys.path.insert(0, _p)
        sys.path.insert(0, _p)
    # Evaluamos la condición lógica (sys.path[0] != _p) para controlar el flujo
    elif sys.path[0] != _p:
        # Bloque try/except para manejo seguro de errores y resiliencia operativa
        try:
            # Ejecutamos instrucción: sys.path.remove(_p)
            sys.path.remove(_p)
        except ValueError:
            # Ejecutamos instrucción: pass
            pass
        # Ejecutamos instrucción: sys.path.insert(0, _p)
        sys.path.insert(0, _p)

# Bloque try/except para manejo seguro de errores y resiliencia operativa
try:
    # Importación de componentes (agregar_favorito, eliminar_favorito, es_minimo_historico, obtener_catalogo, ...) desde el módulo 'backend.database'
    from backend.database import (
        agregar_favorito,
        eliminar_favorito,
        es_minimo_historico,
        obtener_catalogo,
        obtener_detalle_perfume,
        obtener_favoritos_Ids_usuario,
        obtener_historico_precios,
        obtener_minimo_historico,
        obtener_precios_actuales,
    )
except (ImportError, ModuleNotFoundError):
    # Importación de componentes (agregar_favorito, eliminar_favorito, es_minimo_historico, obtener_catalogo, ...) desde el módulo 'APP.backend.database'
    from APP.backend.database import (
        agregar_favorito,
        eliminar_favorito,
        es_minimo_historico,
        obtener_catalogo,
        obtener_detalle_perfume,
        obtener_favoritos_Ids_usuario,
        obtener_historico_precios,
        obtener_minimo_historico,
        obtener_precios_actuales,
    )
# Importación de componentes (es_precio_valido) desde el módulo 'backend.normalizador'
from backend.normalizador import es_precio_valido
# Importación de componentes (DEFAULT_PERFUME_IMAGE, HOME_RED_SVG, PERFUME_SVG_FAVICON, SHIELD_RED_SVG, ...) desde el módulo 'ui'
from ui import (
    DEFAULT_PERFUME_IMAGE,
    HOME_RED_SVG as home_red_svg,
    PERFUME_SVG_FAVICON,
    SHIELD_RED_SVG as shield_red_svg,
    TAG_RED_SVG as tag_red_svg,
    TREND_RED_SVG as trend_red_svg,
    cerrar_sesion_usuario,
    clean_html as _shared_clean_html,
    escape_html,
    formatear_nombre_especifico,
    get_image_src,
    get_theme_palette,
    init_common_session_state,
    resolver_url_oferta,
    sanitize_external_url,
    toggle_theme,
)
# Importación de componentes (modal_autenticacion) desde el módulo 'auth_email'
from auth_email import modal_autenticacion
# Importación de componentes (sincronizar_id_en_url, boton_abrir_perfume, boton_corazon, estilos_moviles, ...) desde el módulo 'perfume_actions'
from perfume_actions import (
    sincronizar_id_en_url,
    boton_abrir_perfume,
    boton_corazon,
    estilos_moviles,
    estilos_tarjetas_cliqueables,
    mostrar_aviso_favoritos,
)


# Definición de función 'clean_html' (parámetros: html_str)
def clean_html(html_str: str) -> str:
    """Limpia espacios iniciales y saltos de línea para evitar bloques de código accidentales."""
    # Retornamos el resultado procesado (_shared_clean_html(html_str, join_char=' '))
    return _shared_clean_html(html_str, join_char=" ")


# =============================================================================
# BLOQUE 1: CACHÉ EN MEMORIA DE ALTO RENDIMIENTO (STREAMLIT CACHE DATA)
# =============================================================================
@st.cache_data(ttl=600, show_spinner=False)
def get_cached_catalogo():
    """Retorna el catálogo consolidado desde la capa de datos con caché de 10 minutos."""
    # Retornamos el resultado procesado (obtener_catalogo())
    return obtener_catalogo()


# - ¿Qué hace esta función?:
#   Obtiene las ofertas en stock y precios vigentes en cada comercio para el perfume seleccionado (en caché de 120s).
@st.cache_data(ttl=120, show_spinner=False)
def get_cached_precios(perfume_id):
    """Consulta los precios vigentes en cada tienda para el perfume seleccionado."""
    # Retornamos el resultado procesado (obtener_precios_actuales(perfume_id))
    return obtener_precios_actuales(perfume_id)


# - ¿Qué hace esta función?:
#   Extrae la serie histórica temporal de observaciones de precios en la base de datos para graficar la evolución.
@st.cache_data(ttl=120, show_spinner=False)
def get_cached_historico(perfume_id, volumen_ml=None):
    """Consulta la serie de tiempo de precios históricos filtrada por presentación."""
    # Retornamos el resultado procesado (obtener_historico_precios(perfume_id, volumen_m...)
    return obtener_historico_precios(perfume_id, volumen_ml=volumen_ml)


# Definición de función 'get_cached_minimo_historico' (parámetros: perfume_id, volumen_ml)
@st.cache_data(ttl=120, show_spinner=False)
def get_cached_minimo_historico(perfume_id, volumen_ml=None):
    """Retorna el menor precio histórico registrado para este perfume y volumen."""
    # Retornamos el resultado procesado (obtener_minimo_historico(perfume_id, volumen_ml...)
    return obtener_minimo_historico(perfume_id, volumen_ml=volumen_ml)


# - ¿Qué hace esta función?:
#   Recupera la ficha técnica oficial del perfume: marca, concentración (EDP/EDT), notas olfativas e imagen.
@st.cache_data(ttl=120, show_spinner=False)
def get_cached_detalle(perfume_id):
    """Retorna la ficha técnica completa del perfume (notas, género, concentración)."""
    # Retornamos el resultado procesado (obtener_detalle_perfume(perfume_id))
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

# Ejecutamos instrucción: init_common_session_state()
init_common_session_state()

# Asignamos 'pal' con get_theme_palette()
pal = get_theme_palette()
# Asignamos 'is_dark' con pal.is_dark
is_dark = pal.is_dark
# Asignamos 'app_bg' con pal.app_bg
app_bg = pal.app_bg
# Asignamos 'app_bg_css' con pal.app_bg_css
app_bg_css = pal.app_bg_css
# Asignamos 'text_color' con pal.text_color
text_color = pal.text_color
# Asignamos 'subtext_color' con pal.subtext_color
subtext_color = pal.subtext_color
# Asignamos 'btn_bg' con pal.btn_bg
btn_bg = pal.btn_bg
# Asignamos 'btn_text' con pal.btn_text
btn_text = pal.btn_text
# Asignamos 'btn_border' con pal.btn_border
btn_border = pal.btn_border
# Asignamos 'input_bg' con pal.input_bg
input_bg = pal.input_bg
# Asignamos 'input_text' con pal.input_text
input_text = pal.input_text
# Asignamos 'input_border' con pal.input_border
input_border = pal.input_border
# Asignamos 'bottle_left_pos' con pal.bottle_left_pos
bottle_left_pos = pal.bottle_left_pos
# Asignamos 'static_icon_pos' con pal.static_icon_pos
static_icon_pos = pal.static_icon_pos
# Asignamos 'static_icon_svg' con pal.static_icon_svg
static_icon_svg = pal.static_icon_svg
# Asignamos 'bottle_svg' con pal.bottle_svg
bottle_svg = pal.bottle_svg
# Asignamos 'user_icon_svg' con pal.user_icon_svg
user_icon_svg = pal.user_icon_svg
# Asignamos 'settings_icon_svg' con pal.settings_icon_svg
settings_icon_svg = pal.settings_icon_svg
# Asignamos 'logout_icon_svg' con pal.logout_icon_svg
logout_icon_svg = pal.logout_icon_svg
# Asignamos 'logo_svg_data' con pal.logo_svg_data
logo_svg_data = pal.logo_svg_data


# Paleta clara reforzada: fondo blanco y texto oscuro legible en todos los componentes.
# El modo oscuro conserva exactamente los valores de la paleta compartida.
if not is_dark:
    # Asignamos 'app_bg' con '#ffffff'
    app_bg = "#ffffff"
    # Asignamos 'app_bg_css' con 'background: #ffffff !important; backgroun...
    app_bg_css = "background: #ffffff !important; background-color: #ffffff !important;"
    # Asignamos 'text_color' con '#1c1917'
    text_color = "#1c1917"
    # Asignamos 'subtext_color' con '#6b6159'
    subtext_color = "#6b6159"
    # Asignamos 'btn_bg' con '#ffffff'
    btn_bg = "#ffffff"
    # Asignamos 'btn_text' con '#1c1917'
    btn_text = "#1c1917"
    # Asignamos 'btn_border' con '#d6cec5'
    btn_border = "#d6cec5"
    # Asignamos 'input_bg' con '#ffffff'
    input_bg = "#ffffff"
    # Asignamos 'input_text' con '#1c1917'
    input_text = "#1c1917"
    # Asignamos 'input_border' con '#d6cec5'
    input_border = "#d6cec5"

# Tokens visuales compartidos con Inicio, Trend del Hype y Páginas de Confianza
card_bg = btn_bg
# Asignamos 'border_color' con 'rgba(255, 255, 255, 0.10)' if is_dark els...
border_color = "rgba(255, 255, 255, 0.10)" if is_dark else "#e6e1db"
# Asignamos 'accent' con '#d83737'
accent = "#d83737"
# Asignamos 'accent_hover' con '#b92d2d'
accent_hover = "#b92d2d"
# Asignamos 'accent_soft' con 'rgba(216, 55, 55, 0.14)' if is_dark else ...
accent_soft = "rgba(216, 55, 55, 0.14)" if is_dark else "rgba(216, 55, 55, 0.07)"
# Asignamos 'gold' con '#d4c2a5' if is_dark else '#8c7b6d'
gold = "#d4c2a5" if is_dark else "#8c7b6d"
# Asignamos 'gold_soft' con 'rgba(212, 194, 165, 0.16)' if is_dark els...
gold_soft = "rgba(212, 194, 165, 0.16)" if is_dark else "rgba(140, 123, 109, 0.14)"
# Asignamos 'ok_green' con '#4ade80' if is_dark else '#15803d'
ok_green = "#4ade80" if is_dark else "#15803d"
# Asignamos 'warn_amber' con '#fbbf24' if is_dark else '#b45309'
warn_amber = "#fbbf24" if is_dark else "#b45309"
# Asignamos 'risk_red' con '#f87171' if is_dark else '#dc2626'
risk_red = "#f87171" if is_dark else "#dc2626"
# Asignamos 'info_blue' con '#60a5fa' if is_dark else '#1d4ed8'
info_blue = "#60a5fa" if is_dark else "#1d4ed8"
# Asignamos 'surface_soft' con 'rgba(255, 255, 255, 0.035)' if is_dark el...
surface_soft = "rgba(255, 255, 255, 0.035)" if is_dark else "#faf8f5"
# Asignamos 'img_stage_bg' con 'radial-gradient(circle at 50% 45%, #1d222...
img_stage_bg = "radial-gradient(circle at 50% 45%, #1d222c 0%, #11141a 100%)" if is_dark else "radial-gradient(circle at 50% 45%, #ffffff 0%, #f6f4f1 100%)"
# Asignamos 'shadow_sm' con '0 1px 2px rgba(0,0,0,0.35)' if is_dark el...
shadow_sm = "0 1px 2px rgba(0,0,0,0.35)" if is_dark else "0 1px 2px rgba(40,30,20,0.06)"
# Asignamos 'shadow_hover' con '0 6px 16px rgba(0,0,0,0.35)' if is_dark e...
shadow_hover = "0 6px 16px rgba(0,0,0,0.35)" if is_dark else "0 6px 16px rgba(60,45,35,0.10)"
# Asignamos 'font_sans' con "'Manrope', -apple-system, BlinkMacSystemF...
font_sans = "'Manrope', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"

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

    /* Botón de compartir WhatsApp nativo en HTML (0 dependencias JS para evitar errores de módulos dinámicos) */
    a.pt-wa-share-btn {{
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        width: 100% !important;
        height: 38px !important;
        padding: 0.25rem 0.75rem !important;
        background: transparent !important;
        color: {text_color} !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 8px !important;
        font-family: {font_sans} !important;
        font-size: 14px !important;
        font-weight: 500 !important;
        text-decoration: none !important;
        box-sizing: border-box !important;
        transition: all 0.2s ease !important;
    }}
    a.pt-wa-share-btn:hover {{
        border-color: #25d366 !important;
        color: #25d366 !important;
        background: rgba(37, 211, 102, 0.08) !important;
    }}

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

    /* Switch de tema: sin bordes, sin fondo y sin sombra en ningún estado (igual que app.py) */
    div.st-key-theme_toggle,
    div.st-key-theme_toggle div[data-testid="stButton"],
    div.st-key-theme_toggle div.stButton {{
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        outline: none !important;
    }}
    div.st-key-theme_toggle div.stButton > button,
    div.st-key-theme_toggle div.stButton > button:hover,
    div.st-key-theme_toggle div.stButton > button:active,
    div.st-key-theme_toggle div.stButton > button:focus,
    div.st-key-theme_toggle div.stButton > button:focus-visible {{
        background: transparent !important;
        background-color: transparent !important;
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
    a[data-testid="stPageLink-NavLink"][href*="compararprecios"] {{
        border-color: {accent} !important;
        background-color: {accent_soft} !important;
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

    /* ---------- SELECTORES Y FILTROS ---------- */
    div[data-baseweb="select"] > div,
    [data-testid="stSelectbox"] div[role="group"] {{
        background-color: {input_bg} !important;
        border: 1px solid {input_border} !important;
        border-radius: 10px !important;
        min-height: 44px !important;
        box-shadow: none !important;
        color: {input_text} !important;
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
    [role="listbox"] [role="option"], [role="listbox"] [role="option"] * {{
        color: {input_text} !important;
    }}
    div[data-baseweb="popover"] li:hover,
    div[data-baseweb="popover"] li[aria-selected="true"],
    [role="listbox"] [role="option"]:hover,
    [role="listbox"] [role="option"][aria-selected="true"] {{
        background-color: {gold_soft} !important;
    }}
    [data-testid="stWidgetLabel"] p {{
        font-size: 0.86rem !important;
        font-weight: 600 !important;
        color: {subtext_color} !important;
    }}

    /* Pastillas (género y presentación en ml) */
    div[data-testid="stPills"],
    div[data-testid="stButtonGroup"] {{
        gap: 8px !important;
    }}
    div[data-testid="stPills"] button,
    div[data-testid="stButtonGroup"] button,
    button[data-testid="stBaseButton-pills"],
    button[data-testid="stBaseButton-pillsActive"] {{
        border-radius: 999px !important;
        border: 1px solid {btn_border} !important;
        background-color: transparent !important;
        color: {text_color} !important;
        font-weight: 600 !important;
        font-size: 0.86rem !important;
        padding: 6px 16px !important;
        min-height: 36px !important;
        box-shadow: none !important;
        transition: background-color 0.18s ease, border-color 0.18s ease !important;
    }}
    div[data-testid="stPills"] button p,
    div[data-testid="stButtonGroup"] button p,
    button[data-testid="stBaseButton-pills"] p,
    button[data-testid="stBaseButton-pillsActive"] p {{
        color: {text_color} !important;
        font-weight: 600 !important;
    }}
    div[data-testid="stPills"] button:hover,
    div[data-testid="stButtonGroup"] button:hover,
    button[data-testid="stBaseButton-pills"]:hover {{
        border-color: {gold} !important;
        background-color: {btn_bg} !important;
    }}
    div[data-testid="stPills"] button[aria-checked="true"],
    div[data-testid="stPills"] button[data-selected="true"],
    div[data-testid="stButtonGroup"] button[aria-checked="true"],
    button[data-testid="stBaseButton-pillsActive"] {{
        background-color: {accent_soft} !important;
        border-color: {accent} !important;
        box-shadow: inset 0 0 0 1px {accent} !important;
    }}

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
        font-size: 1.15rem;
        font-weight: 800;
        letter-spacing: -0.01em;
        color: {text_color};
        margin: 0;
    }}
    .pt-section-row {{
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 8px;
        margin-bottom: 14px;
    }}
    .pt-section-meta {{ font-size: 0.82rem; color: {subtext_color}; }}

    /* ---------- FICHA DEL PERFUME ---------- */
    .perfume-header-stage {{
        background: {img_stage_bg};
        border: 1px solid {border_color};
        border-radius: 16px;
        padding: 16px;
        display: flex;
        align-items: center;
        justify-content: center;
        min-height: 200px;
    }}
    .perfume-header-stage img {{
        max-height: 190px;
        max-width: 100%;
        object-fit: contain;
        filter: {"drop-shadow(0 10px 18px rgba(0,0,0,0.45))" if is_dark else "drop-shadow(0 8px 14px rgba(60,45,35,0.12))"};
    }}
    .perfume-name {{
        margin: 0 0 6px 0;
        color: {text_color};
        font-size: 1.75rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        line-height: 1.15;
    }}
    .perfume-meta {{
        color: {subtext_color};
        font-size: 0.95rem;
        margin-bottom: 14px;
    }}
    .perfume-notes {{
        color: {text_color};
        font-size: 0.92rem;
        line-height: 1.55;
        margin-bottom: 12px;
    }}
    .perfume-notes-label {{ font-weight: 700; }}
    .perfume-ref-row {{
        display: flex;
        gap: 12px;
        align-items: center;
        flex-wrap: wrap;
    }}
    .perfume-ref {{ font-size: 0.88rem; color: {subtext_color}; }}
    .perfume-ref-val {{ color: {text_color}; font-weight: 800; font-variant-numeric: tabular-nums; }}
    span.pt-pill-ok {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(34, 197, 94, 0.10);
        color: {ok_green} !important;
        border: 1px solid rgba(34, 197, 94, 0.28);
        font-size: 0.78rem;
        font-weight: 700;
        padding: 4px 11px;
        border-radius: 999px;
    }}
    span.pt-dot {{ width: 6px; height: 6px; border-radius: 50%; background: currentColor; display: inline-block; }}

    /* Botones de seguimiento y compartir */
    div[class*="st-key-btn_toggle_fav_"] div.stButton > button {{
        border-color: {gold} !important;
        background-color: {gold_soft} !important;
    }}
    div[class*="st-key-btn_toggle_fav_"] div.stButton > button:hover {{
        border-color: {gold} !important;
    }}
    div[data-testid="stLinkButton"] a {{
        background-color: {btn_bg} !important;
        border: 1px solid {btn_border} !important;
        color: {btn_text} !important;
        border-radius: 10px !important;
        min-height: 42px !important;
        box-shadow: {shadow_sm} !important;
        text-decoration: none !important;
        transition: border-color 0.18s ease, box-shadow 0.18s ease !important;
    }}
    div[data-testid="stLinkButton"] a:hover {{
        border-color: {gold} !important;
        box-shadow: {shadow_hover} !important;
    }}
    div[data-testid="stLinkButton"] a p,
    div[data-testid="stLinkButton"] a span {{
        color: {btn_text} !important;
        font-weight: 600 !important;
        font-size: 0.92rem !important;
    }}

    /* ---------- OFERTAS ---------- */
    .offer-toolbar {{
        margin: 0 0 8px 0;
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 8px;
    }}
    .offer-toolbar-left {{ display: flex; align-items: center; gap: 10px; }}
    .offer-toolbar-label {{ font-size: 0.95rem; font-weight: 700; color: {text_color}; }}
    .offer-toolbar-meta {{ font-size: 0.8rem; color: {subtext_color}; }}
    span.pt-stock {{
        font-size: 0.8rem;
        font-weight: 700;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }}
    span.pt-stock-ok {{ color: {ok_green} !important; }}
    span.pt-stock-out {{ color: {risk_red} !important; }}

    .price-card {{
        background-color: {card_bg};
        border: 1px solid {border_color};
        border-radius: 14px;
        padding: 16px 18px;
        margin-bottom: 10px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 16px;
        transition: border-color 0.18s ease;
    }}
    .price-card:hover {{ border-color: {gold}; }}
    .best-deal {{
        border: 1px solid {"rgba(74, 222, 128, 0.45)" if is_dark else "rgba(21, 128, 61, 0.40)"} !important;
        background-color: {"rgba(34, 197, 94, 0.07)" if is_dark else "rgba(21, 128, 61, 0.04)"} !important;
        box-shadow: inset 4px 0 0 {ok_green};
    }}
    .price-card-left {{
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 8px;
        min-width: 0;
    }}
    .store-name {{
        font-size: 1.05rem;
        font-weight: 800;
        color: {text_color};
        margin-right: 4px;
    }}
    span.pt-tag {{
        font-size: 0.74rem;
        font-weight: 600;
        padding: 3px 9px;
        border-radius: 999px;
        background-color: {surface_soft};
        border: 1px solid {border_color};
        color: {subtext_color} !important;
        white-space: nowrap;
    }}
    span.pt-tag-strong {{ color: {text_color} !important; font-weight: 700; }}
    span.pt-tag-best {{ background: rgba(34, 197, 94, 0.12); border-color: rgba(34, 197, 94, 0.35); color: {ok_green} !important; font-weight: 700; }}
    span.pt-tag-out {{ background: rgba(239, 68, 68, 0.10); border-color: rgba(239, 68, 68, 0.30); color: {risk_red} !important; font-weight: 700; }}
    span.pt-tag-ml {{ background: rgba(59, 130, 246, 0.12); border-color: rgba(96, 165, 250, 0.35); color: {info_blue} !important; font-weight: 700; }}
    span.pt-tag-tester {{ background: rgba(245, 158, 11, 0.12); border-color: rgba(251, 191, 36, 0.35); color: {warn_amber} !important; font-weight: 700; }}
    span.pt-tag-alltime {{ background: rgba(220, 38, 38, 0.15); border-color: rgba(220, 38, 38, 0.40); color: #ef4444 !important; font-weight: 800; }}
    span.pt-tag-age {{ opacity: 0.85; font-size: 0.71rem; }}
    span.pt-tag-stale {{ background: rgba(245, 158, 11, 0.14); border-color: rgba(251, 191, 36, 0.45); color: {warn_amber} !important; font-weight: 700; }}

    .price-card-right {{
        display: flex;
        align-items: center;
        gap: 16px;
        flex-shrink: 0;
    }}
    .price-block {{ text-align: right; }}
    span.pt-old-price {{
        font-size: 0.85rem;
        text-decoration: line-through;
        color: {subtext_color} !important;
        margin-right: 8px;
    }}
    span.pt-price-value {{
        font-size: 1.3rem;
        font-weight: 800;
        color: {text_color} !important;
        font-variant-numeric: tabular-nums;
        letter-spacing: -0.01em;
    }}
    .best-deal span.pt-price-value {{ color: {ok_green} !important; }}
    span.pt-price-ml {{
        font-size: 0.78rem;
        color: {subtext_color} !important;
        display: block;
        text-align: right;
        font-variant-numeric: tabular-nums;
    }}
    span.pt-price-out {{
        font-size: 1rem;
        font-weight: 800;
        color: {risk_red} !important;
    }}
    span.pt-price-out-old {{
        display: block;
        font-size: 0.8rem;
        color: {subtext_color} !important;
        text-decoration: line-through;
    }}
    a.buy-btn, a.buy-btn:visited {{
        background-color: {text_color};
        color: {app_bg} !important;
        padding: 9px 16px;
        border-radius: 999px;
        text-decoration: none !important;
        font-weight: 700;
        font-size: 0.85rem;
        display: inline-block;
        white-space: nowrap;
        transition: opacity 0.18s ease, background-color 0.18s ease;
    }}
    a.buy-btn:hover {{ opacity: 0.85; color: {app_bg} !important; }}
    .best-deal a.buy-btn {{ background-color: {accent}; color: #ffffff !important; }}
    .best-deal a.buy-btn:hover {{ background-color: {accent_hover}; opacity: 1; }}
    a.buy-btn:focus-visible {{ outline: 2px solid {accent}; outline-offset: 2px; }}

    .price-card.out-of-stock {{
        opacity: 0.7;
        background-color: {surface_soft} !important;
        border-style: dashed !important;
    }}
    .price-card.out-of-stock:hover {{ opacity: 0.95; }}
    .price-card.out-of-stock a.buy-btn {{
        background: transparent;
        color: {subtext_color} !important;
        border: 1px solid {border_color};
    }}

    .offer-separator {{
        margin: 22px 0 12px 0;
        display: flex;
        align-items: center;
        gap: 12px;
    }}
    .offer-separator-label {{ font-size: 0.85rem; font-weight: 700; color: {subtext_color}; white-space: nowrap; }}
    .offer-separator-line {{ flex: 1; height: 1px; background-color: {btn_border}; }}

    .offer-alert {{
        background-color: {"rgba(239, 68, 68, 0.08)" if is_dark else "#fef2f2"};
        border: 1px solid {"rgba(239, 68, 68, 0.25)" if is_dark else "#fecaca"};
        border-radius: 12px;
        padding: 12px 16px;
        margin: 4px 0 16px 0;
        display: flex;
        align-items: center;
        gap: 10px;
        font-size: 0.88rem;
        font-weight: 600;
        color: {risk_red};
    }}

    /* ---------- HISTÓRICO (EXPANDER) ---------- */
    div[data-testid="stExpander"] details {{
        background-color: {card_bg} !important;
        border: 1px solid {border_color} !important;
        border-radius: 14px !important;
    }}
    div[data-testid="stExpander"] summary,
    div[data-testid="stExpander"] summary:hover,
    div[data-testid="stExpander"] details[open] > summary {{
        background: transparent !important;
        background-color: transparent !important;
        color: {text_color} !important;
    }}
    div[data-testid="stExpander"] summary p {{
        font-weight: 700 !important;
        color: {text_color} !important;
    }}
    div[data-testid="stExpander"] summary svg {{ color: {subtext_color} !important; fill: {subtext_color} !important; }}

    /* ---------- RECOMENDADAS ---------- */
    .rel-card {{
        background: {card_bg};
        border: 1px solid {border_color};
        border-bottom: none;
        border-radius: 14px 14px 0 0;
        padding: 12px 12px 20px 12px;
        display: flex;
        flex-direction: column;
        text-align: left;
        transition: border-color 0.18s ease;
    }}
    div[data-testid="stColumn"]:has(.rel-card):hover .rel-card {{ border-color: {gold}; }}
    .rel-stage {{
        background: {img_stage_bg};
        border-radius: 10px;
        height: 120px;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-bottom: 10px;
    }}
    .rel-stage img {{ max-height: 100px; max-width: 80%; object-fit: contain; }}
    .rel-brand {{ font-size: 0.76rem; color: {subtext_color}; }}
    .rel-name {{
        font-weight: 700;
        font-size: 0.9rem;
        color: {text_color};
        margin: 3px 0 8px 0;
        line-height: 1.3;
        min-height: 2.6em;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }}
    .rel-price {{ font-size: 0.92rem; font-weight: 800; color: {ok_green}; font-variant-numeric: tabular-nums; }}
    div[class*="st-key-btn_ir_rel_"] {{ margin-top: -1rem !important; }}
    div[class*="st-key-btn_ir_rel_"] div.stButton > button {{
        background-color: {accent} !important;
        border: 1px solid {accent} !important;
        border-radius: 0 0 14px 14px !important;
        min-height: 42px !important;
        box-shadow: none !important;
    }}
    div[class*="st-key-btn_ir_rel_"] div.stButton > button p {{ color: #ffffff !important; font-weight: 700 !important; }}
    div[class*="st-key-btn_ir_rel_"] div.stButton > button:hover {{
        background-color: {accent_hover} !important;
        border-color: {accent_hover} !important;
    }}

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
        div[data-testid="stColumn"]:has(a[data-testid="stPageLink-NavLink"]),
        div[data-testid="stColumn"]:has(.rel-card) {{
            flex: 1 1 calc(50% - 4px) !important;
            width: calc(50% - 4px) !important;
        }}
        a[data-testid="stPageLink-NavLink"] {{ justify-content: flex-start !important; padding-left: 2.2rem !important; }}
        a[data-testid="stPageLink-NavLink"] p,
        a[data-testid="stPageLink-NavLink"] span {{ font-size: 0.8rem !important; white-space: normal !important; line-height: 1.15 !important; }}
        a[data-testid="stPageLink-NavLink"]::before {{ left: 11px !important; }}
        .brand-logo-text {{ font-size: 1.35rem !important; }}
        .price-card {{ flex-direction: column; align-items: stretch; }}
        .price-card-right {{ justify-content: space-between; }}
        .perfume-name {{ font-size: 1.45rem; }}
        div.st-key-login_btn div.stButton > button {{
            min-height: 36px !important;
            padding: 5px 14px 5px 32px !important;
            background-position: 11px center !important;
        }}
    }}
    </style>
""", unsafe_allow_html=True)

# Tarjetas de perfume cliqueables y corazón de favoritos (compartido con todas las páginas)
st.markdown(estilos_tarjetas_cliqueables(accent, card_bg, border_color, subtext_color, is_dark), unsafe_allow_html=True)
# Diseño responsivo para celulares (común a todas las páginas)
st.markdown(estilos_moviles(accent, border_color, is_dark), unsafe_allow_html=True)
# Renderizado de componente visual o control interactivo en la interfaz Streamlit
st.markdown(f"""
    <style>
    div[class*="st-key-pcard_rel_"] {{ --heart-top: 20px; --heart-right: 20px; }}
    div[class*="st-key-pcard_rel_"]:hover .rel-card {{ border-color: {gold}; }}
    div[class*="st-key-pcard_main_"] {{ --heart-top: 12px; --heart-right: 12px; }}
    </style>
""", unsafe_allow_html=True)

# 3. ENCABEZADO SUPERIOR: LOGO, BOTÓN "INGRESAR" / PERFIL Y SWITCH DE TEMA
if st.session_state['logged_in']:
    # Mismo tamaño del botón de usuario en todas las páginas: ni muy chico ni muy grande
    col_logo, col_espacio, col_actions = st.columns([5.2, 0.6, 3.2], vertical_alignment="center")
    # Asignamos '(btn_col1, btn_col2)' con col_actions.columns([2.4, 0.8], vertical_a...
    btn_col1, btn_col2 = col_actions.columns([2.4, 0.8], vertical_alignment="center", gap="small")
else:
    # Renderizado de componente visual o control interactivo en la interfaz Streamlit
    col_logo, col_espacio, col_actions = st.columns([5.6, 1.2, 2.4], vertical_alignment="center")
    # Asignamos '(btn_col1, btn_col2)' con col_actions.columns([2.0, 0.8], vertical_a...
    btn_col1, btn_col2 = col_actions.columns([2.0, 0.8], vertical_alignment="center", gap="small")

# Gestión automática de contexto y recursos para: col_logo
with col_logo:
    # Renderizado de componente visual o control interactivo en la interfaz Streamlit
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

# Gestión automática de contexto y recursos para: btn_col1
with btn_col1:
    # Evaluamos la condición lógica (st.session_state['logged_in']) para controlar el flujo
    if st.session_state['logged_in']:
        # Asignamos 'user_display' con st.session_state['user_info'].get('nombre'...
        user_display = st.session_state['user_info'].get('nombre') or st.session_state['user_info'].get('email', 'Usuario')
        # Renderizado de componente visual o control interactivo en la interfaz Streamlit
        st.markdown('<div class="user-popover-container">', unsafe_allow_html=True)
        # Gestión automática de contexto y recursos para: st.popover(f'{user_display}', use_container_wid...
        with st.popover(f"{user_display}", use_container_width=True):
            # Renderizado de componente visual o control interactivo en la interfaz Streamlit
            st.write(f"**Conectado como:**")
            # Renderizado de componente visual o control interactivo en la interfaz Streamlit
            st.write(st.session_state['user_info'].get('email', ''))
            # Renderizado de componente visual o control interactivo en la interfaz Streamlit
            st.markdown("<div style='margin-top: 8px;'></div>", unsafe_allow_html=True)
            
            # ACOPLE DIRECTO A LA PÁGINA DE PERFIL CON DIBUJO VECTORIAL SVG
            if st.button("Mi Perfil y Alertas", key="btn_go_profile", use_container_width=True):
                # Ejecutamos instrucción: st.switch_page('pages/perfil.py')
                st.switch_page("pages/perfil.py")
                
            # Evaluamos la condición lógica (st.button('Cerrar Sesión', key='btn_logout', use_con...) para controlar el flujo
            if st.button("Cerrar Sesión", key="btn_logout", use_container_width=True):
                # Ejecutamos instrucción: cerrar_sesion_usuario()
                cerrar_sesion_usuario()
                # Ejecutamos instrucción: st.rerun()
                st.rerun()
        # Renderizado de componente visual o control interactivo en la interfaz Streamlit
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        # Evaluamos la condición lógica (st.button('Ingresar', key='login_btn', use_container...) para controlar el flujo
        if st.button("Ingresar", key="login_btn", use_container_width=True):
            # Asignamos 'st.session_state['show_login_mod...' con True
            st.session_state['show_login_modal'] = True
            # Ejecutamos instrucción: st.rerun()
            st.rerun()

# Gestión automática de contexto y recursos para: btn_col2
with btn_col2:
    # Renderizado de componente visual o control interactivo en la interfaz Streamlit
    st.button(" ", key="theme_toggle", on_click=toggle_theme)

# MONITOREO Y RENDERIZADO PERSISTENTE DEL MODAL
if st.session_state.get('show_login_modal', False):
    # Asignamos 'st.session_state['show_login_mod...' con False
    st.session_state['show_login_modal'] = False
    # Ejecutamos instrucción: modal_autenticacion()
    modal_autenticacion()
# Ejecutamos instrucción: mostrar_aviso_favoritos()
mostrar_aviso_favoritos()

# Renderizado de componente visual o control interactivo en la interfaz Streamlit
st.markdown("<div style='margin-top: 22px;'></div>", unsafe_allow_html=True)

# 4. CHIPS DE NAVEGACIÓN RÁPIDA
col_chip_home, col_chip1, col_chip2, col_chip3, col_chip_remates = st.columns([1.6, 1.5, 2.0, 1.7, 1.8], vertical_alignment="center")

# Gestión automática de contexto y recursos para: col_chip_home
with col_chip_home:
    # Ejecutamos instrucción: st.page_link('app.py', label='Inicio / Catálogo', us...
    st.page_link("app.py", label="Inicio / Catálogo", use_container_width=True)
# Gestión automática de contexto y recursos para: col_chip1
with col_chip1:
    # Ejecutamos instrucción: st.page_link('pages/trendhype.py', label='Trend Del ...
    st.page_link("pages/trendhype.py", label="Trend Del Hype", use_container_width=True)
# Gestión automática de contexto y recursos para: col_chip2
with col_chip2:
    # Ejecutamos instrucción: st.page_link('pages/trustpage.py', label='Páginas de...
    st.page_link("pages/trustpage.py", label="Páginas de Confianza", use_container_width=True)
# Gestión automática de contexto y recursos para: col_chip3
with col_chip3:
    # Ejecutamos instrucción: st.page_link('pages/compararprecios.py', label='Comp...
    st.page_link("pages/compararprecios.py", label="Comparar Precios", use_container_width=True)
# Gestión automática de contexto y recursos para: col_chip_remates
with col_chip_remates:
    # Ejecutamos instrucción: st.page_link('pages/remates.py', label='Remates & Fl...
    st.page_link("pages/remates.py", label="Remates & Flash", use_container_width=True)

# Renderizado de componente visual o control interactivo en la interfaz Streamlit
st.markdown("<div style='margin-top: 34px;'></div>", unsafe_allow_html=True)

# 5. SECCIÓN PRINCIPAL: COMPARADOR DE PRECIOS
# =============================================================================
# - ¿Qué hace este bloque (Ficha Técnica y Búsqueda de Perfume)?:
#   Permite buscar cualquier perfume con autocompletado en tiempo real (selectbox)
#   y despliega el banner visual con su frasco oficial, notas de salida/corazón/fondo y botón de favoritos.
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
# Gestión automática de contexto y recursos para: col_title_text
with col_title_text:
    # Renderizado de componente visual o control interactivo en la interfaz Streamlit
    st.markdown(clean_html("""
        <div class="pt-title">Comparador de precios</div>
        <div class="pt-lede">Elige una fragancia y compara sus ofertas en tiendas chilenas verificadas, con el precio por mililitro de cada presentación.</div>
    """), unsafe_allow_html=True)
# Gestión automática de contexto y recursos para: col_title_back
with col_title_back:
    # Ejecutamos instrucción: st.page_link('app.py', label='Volver al catálogo')
    st.page_link("app.py", label="Volver al catálogo")

# Renderizado de componente visual o control interactivo en la interfaz Streamlit
st.markdown("<div style='margin-top: 18px;'></div>", unsafe_allow_html=True)

# Cargar catálogo dinámico con caché en memoria
catalogo = get_cached_catalogo()

# Evaluamos la condición lógica (not catalogo) para controlar el flujo
if not catalogo:
    # Ejecutamos instrucción: st.warning('No hay perfumes disponibles en el catálo...
    st.warning("No hay perfumes disponibles en el catálogo en este momento.")
    # Ejecutamos instrucción: st.stop()
    st.stop()

# Determinar perfume pre-seleccionado desde sesión (dict, id o nombre) o desde query param compartible (?id=)
qp_id = st.query_params.get("id")
# Si la dirección cambió por fuera (botones Atrás/Adelante del navegador), se muestra ese perfume
_id_url_anterior = st.session_state.get("_cp_id_en_url")
# Evaluamos la condición lógica (qp_id and str(qp_id).isdigit() and (_id_url_anterior...) para controlar el flujo
if qp_id and str(qp_id).isdigit() and _id_url_anterior is not None and str(qp_id) != str(_id_url_anterior):
    # Asignamos 'st.session_state['selected_perfu...' con int(qp_id)
    st.session_state["selected_perfume"] = int(qp_id)
# Asignamos 'selected_session' con st.session_state.get('selected_perfume')
selected_session = st.session_state.get("selected_perfume")

# Asignamos 'target_id' con None
target_id = None
# Evaluamos la condición lógica (isinstance(selected_session, dict) and selected_sess...) para controlar el flujo
if isinstance(selected_session, dict) and selected_session.get("id") is not None:
    # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
    target_id = str(selected_session.get("id"))
# Evaluamos la condición lógica (selected_session is not None and str(selected_sessio...) para controlar el flujo
elif selected_session is not None and str(selected_session).isdigit():
    # Asignamos 'target_id' con str(selected_session)
    target_id = str(selected_session)
# Evaluamos la condición lógica (qp_id and str(qp_id).isdigit()) para controlar el flujo
elif qp_id and str(qp_id).isdigit():
    # Asignamos 'target_id' con str(qp_id)
    target_id = str(qp_id)

# Asignamos 'p_target' con next((p for p in catalogo if str(p['id']) ...
p_target = next((p for p in catalogo if str(p["id"]) == target_id), None) if target_id else None

# Filtros rápidos opcionales por Marca y Género para acotar el catálogo instantáneamente
marcas_disponibles = sorted(list({(p.get("marca") or "").strip() for p in catalogo if p.get("marca")}))
# Asignamos 'opciones_marcas' con ['Todas las marcas'] + marcas_disponibles
opciones_marcas = ["Todas las marcas"] + marcas_disponibles
# Asignamos 'opciones_generos' con ['Todos', 'Hombre', 'Mujer', 'Unisex']
opciones_generos = ["Todos", "Hombre", "Mujer", "Unisex"]

# Si se solicitó un perfume específico por id o sesión, verificar que los filtros no lo oculten
if p_target:
    # Asignamos 'guardada_marca' con st.session_state.get('filtro_marca_comp')
    guardada_marca = st.session_state.get("filtro_marca_comp")
    # Evaluamos la condición lógica (guardada_marca and guardada_marca != 'Todas las marc...) para controlar el flujo
    if guardada_marca and guardada_marca != "Todas las marcas" and guardada_marca != p_target.get("marca"):
        # Asignamos 'st.session_state['filtro_marca_c...' con 'Todas las marcas'
        st.session_state["filtro_marca_comp"] = "Todas las marcas"
    # Asignamos 'guardado_gen' con st.session_state.get('filtro_gen_comp')
    guardado_gen = st.session_state.get("filtro_gen_comp")
    # Evaluamos la condición lógica (guardado_gen and guardado_gen != 'Todos' and (guarda...) para controlar el flujo
    if guardado_gen and guardado_gen != "Todos" and guardado_gen.lower() != str(p_target.get("genero") or "").lower():
        # Asignamos 'st.session_state['filtro_gen_comp']' con 'Todos'
        st.session_state["filtro_gen_comp"] = "Todos"

# Renderizado de componente visual o control interactivo en la interfaz Streamlit
col_f_marca, col_f_genero = st.columns([1.5, 1], vertical_alignment="bottom")
# Gestión automática de contexto y recursos para: col_f_marca
with col_f_marca:
    # Renderizado de componente visual o control interactivo en la interfaz Streamlit
    marca_filtro = st.selectbox(
        "Filtrar por Marca:",
        opciones_marcas,
        index=0,
        key="filtro_marca_comp"
    )
# Gestión automática de contexto y recursos para: col_f_genero
with col_f_genero:
    # Asignamos 'genero_filtro' con st.pills('Género:', opciones_generos, defa...
    genero_filtro = st.pills(
        "Género:",
        opciones_generos,
        default="Todos",
        key="filtro_gen_comp"
    )

# Asignamos 'catalogo_filtrado' con catalogo
catalogo_filtrado = catalogo
# Evaluamos la condición lógica (marca_filtro != 'Todas las marcas') para controlar el flujo
if marca_filtro != "Todas las marcas":
    # Asignamos 'catalogo_filtrado' con [p for p in catalogo_filtrado if (p.get('m...
    catalogo_filtrado = [p for p in catalogo_filtrado if (p.get("marca") or "").strip() == marca_filtro]
# Evaluamos la condición lógica (genero_filtro and genero_filtro != 'Todos') para controlar el flujo
if genero_filtro and genero_filtro != "Todos":
    # Asignamos 'catalogo_filtrado' con [p for p in catalogo_filtrado if (p.get('g...
    catalogo_filtrado = [p for p in catalogo_filtrado if (p.get("genero") or "").strip().lower() == genero_filtro.lower()]

# Si el perfume objetivo quedó fuera del filtro por alguna razón, restaurar catálogo completo
if p_target and p_target not in catalogo_filtrado:
    # Asignamos 'catalogo_filtrado' con catalogo
    catalogo_filtrado = catalogo

# Diccionario de mapeo rápido con nombre específico sin colisiones entre concentraciones ni géneros
opciones_perfumes = {}
# Recorremos iterativamente cada 'p' en catalogo_filtrado
for p in catalogo_filtrado:
    # Asignamos 'tipo_lbl' con (p.get('tipo') or 'Eau de Parfum').strip()
    tipo_lbl = (p.get("tipo") or "Eau de Parfum").strip()
    # Asignamos 'gen_lbl' con (p.get('genero') or 'Unisex').strip()
    gen_lbl = (p.get("genero") or "Unisex").strip()
    # Asignamos 'nom_esp' con formatear_nombre_especifico(p) or p['nombre']
    nom_esp = formatear_nombre_especifico(p) or p["nombre"]
    # Asignamos 'base_lbl' con f"{nom_esp} — {p['marca']} ({tipo_lbl} · {...
    base_lbl = f"{nom_esp} — {p['marca']} ({tipo_lbl} · {gen_lbl})"
    # Asignamos 'lbl_final' con base_lbl if base_lbl not in opciones_perfu...
    lbl_final = base_lbl if base_lbl not in opciones_perfumes else f"{base_lbl} [#{p['id']}]"
    # Asignamos 'opciones_perfumes[lbl_final]' con p
    opciones_perfumes[lbl_final] = p

# Asignamos 'lista_nombres' con list(opciones_perfumes.keys())
lista_nombres = list(opciones_perfumes.keys())
# Asignamos 'default_index' con 0
default_index = 0

# Evaluamos la condición lógica (target_id is not None) para controlar el flujo
if target_id is not None:
    # Recorremos iterativamente cada '(idx, (_, p))' en enumerate(opciones_perfumes.items())
    for idx, (_, p) in enumerate(opciones_perfumes.items()):
        # Evaluamos la condición lógica (str(p['id']) == target_id) para controlar el flujo
        if str(p["id"]) == target_id:
            # Asignamos 'default_index' con idx
            default_index = idx
            # Interrumpimos el ciclo actual al cumplirse la condición de salida
            break
# Evaluamos la condición lógica (isinstance(selected_session, str) and selected_sessi...) para controlar el flujo
elif isinstance(selected_session, str) and selected_session.strip():
    # Asignamos 'term_sel' con selected_session.strip().lower()
    term_sel = selected_session.strip().lower()
    # Recorremos iterativamente cada '(idx, (_, p))' en enumerate(opciones_perfumes.items())
    for idx, (_, p) in enumerate(opciones_perfumes.items()):
        # Evaluamos la condición lógica (term_sel in p['nombre'].lower()) para controlar el flujo
        if term_sel in p["nombre"].lower():
            # Asignamos 'default_index' con idx
            default_index = idx
            # Interrumpimos el ciclo actual al cumplirse la condición de salida
            break

# Renderizado de componente visual o control interactivo en la interfaz Streamlit
selected_label = st.selectbox("Selecciona un perfume para comparar ofertas en Chile:", lista_nombres, index=default_index)
# Asignamos 'perfume' con opciones_perfumes[selected_label]
perfume = opciones_perfumes[selected_label]
# Asignamos 'selected_id' con perfume['id']
selected_id = perfume["id"]
# Asignamos 'st.session_state['selected_perfu...' con selected_id
st.session_state["selected_perfume"] = selected_id
# El id del perfume se refleja en la dirección (enlace compartible) reemplazando la entrada actual
# del historial en vez de crear una nueva; así el botón "Atrás" del navegador vuelve a la página anterior.
sincronizar_id_en_url(selected_id)

# Obtener detalle enriquecido desde caché
detalle = get_cached_detalle(selected_id) or perfume

# Mostrar ficha cabecera del perfume con packshot de alta resolución y nombre específico inequívoco
img_src = get_image_src(detalle.get('imagen_url'))
# Asignamos 'nombre_especifico_det' con formatear_nombre_especifico(detalle) or de...
nombre_especifico_det = formatear_nombre_especifico(detalle) or detalle.get('nombre', '')
# Asignamos 'nombre_safe' con escape_html(nombre_especifico_det)
nombre_safe = escape_html(nombre_especifico_det)
# Asignamos 'marca_safe' con escape_html(detalle.get('marca', ''))
marca_safe = escape_html(detalle.get('marca', ''))
# Asignamos 'notas_safe' con escape_html(detalle.get('notas') or 'Notas...
notas_safe = escape_html(detalle.get('notas') or 'Notas olfativas exclusivas')
# Asignamos 'genero_safe' con escape_html(detalle.get('genero') or 'Unis...
genero_safe = escape_html(detalle.get('genero') or 'Unisex')
# Asignamos 'tipo_safe' con escape_html(detalle.get('tipo') or 'Eau de...
tipo_safe = escape_html(detalle.get('tipo') or 'Eau de Parfum')

# Renderizado de componente visual o control interactivo en la interfaz Streamlit
col_img, col_info = st.columns([1, 3], gap="medium")
# Gestión automática de contexto y recursos para: col_img
with col_img:
    # Gestión automática de contexto y recursos para: st.container(key=f'pcard_main_{selected_id}')
    with st.container(key=f"pcard_main_{selected_id}"):
        # Renderizado de componente visual o control interactivo en la interfaz Streamlit
        st.markdown(clean_html(f"""
        <div class="perfume-header-stage">
            <img src="{img_src}" alt="{nombre_safe}" onerror="this.onerror=null;this.src='{DEFAULT_PERFUME_IMAGE}';">
        </div>
        """), unsafe_allow_html=True)
        # Ejecutamos instrucción: boton_corazon(selected_id, 'main', nombre_especifico...
        boton_corazon(selected_id, "main", nombre_especifico_det)

# Gestión automática de contexto y recursos para: col_info
with col_info:
    # Asignamos 'ref_precio' con detalle.get('precio_referencia')
    ref_precio = detalle.get('precio_referencia')
    # Evaluamos la condición lógica (not es_precio_valido(ref_precio)) para controlar el flujo
    if not es_precio_valido(ref_precio):
        # Asignamos 'ref_precio' con None
        ref_precio = None
    # Asignamos 'ref_str' con f'${ref_precio:,.0f} CLP'.replace(',', '.'...
    ref_str = f"${ref_precio:,.0f} CLP".replace(",", ".") if ref_precio else "Consultar"

    # Renderizado de componente visual o control interactivo en la interfaz Streamlit
    st.markdown(clean_html(f"""
    <div style="padding-top: 4px;">
        <div class="perfume-name">{nombre_safe}</div>
        <div class="perfume-meta">{marca_safe}, {tipo_safe}, {genero_safe}</div>
        <div class="perfume-notes"><span class="perfume-notes-label">Notas olfativas:</span> {notas_safe}</div>
        <div class="perfume-ref-row">
            <div class="perfume-ref">Precio referencial de mercado: <b class="perfume-ref-val">{ref_str}</b></div>
            <span class="pt-pill-ok"><span class="pt-dot"></span>Disponible en tiendas auditadas</span>
        </div>
    </div>
    """), unsafe_allow_html=True)

    # Botón persistente de Favoritos y Monitoreo de Alertas conectado a Supabase Auth / SQLite
    favs_actuales = st.session_state.get('favoritos') or []
    # Evaluamos la condición lógica (st.session_state.get('logged_in') and st.session_sta...) para controlar el flujo
    if st.session_state.get('logged_in') and st.session_state.get('user_info') and not favs_actuales:
        # Asignamos 'u_key_fav' con st.session_state['user_info'].get('id') or...
        u_key_fav = st.session_state['user_info'].get('id') or st.session_state['user_info'].get('email')
        # Evaluamos la condición lógica (u_key_fav) para controlar el flujo
        if u_key_fav:
            # Asignamos 'favs_actuales' con obtener_favoritos_Ids_usuario(u_key_fav, e...
            favs_actuales = obtener_favoritos_Ids_usuario(u_key_fav, email=st.session_state['user_info'].get('email'))
            # Asignamos 'st.session_state['favoritos']' con favs_actuales
            st.session_state['favoritos'] = favs_actuales

    # Asignamos 'ya_es_favorito' con int(selected_id) in [int(x) for x in favs_...
    ya_es_favorito = int(selected_id) in [int(x) for x in favs_actuales if str(x).isdigit()]
    
    # Asignamos 'url_directa' con f'https://perfumetrending-cl.streamlit.app...
    url_directa = f"https://perfumetrending-cl.streamlit.app/compararprecios?id={selected_id}"
    # Asignamos 'texto_wa' con f'¡Mira esta comparativa de {nombre_safe} ...
    texto_wa = f"¡Mira esta comparativa de {nombre_safe} ({marca_safe}) en PerfumeTrending.cl! Revisa tiendas y precios aquí: {url_directa}"
    # Asignamos 'wa_href' con f'https://api.whatsapp.com/send?text={urll...
    wa_href = f"https://api.whatsapp.com/send?text={urllib.parse.quote(texto_wa)}"

    # Renderizado de componente visual o control interactivo en la interfaz Streamlit
    col_fav_btn, col_wa_btn, col_share_btn = st.columns([1.8, 1.2, 1.2], gap="small")
    # Gestión automática de contexto y recursos para: col_fav_btn
    with col_fav_btn:
        # Renderizado de componente visual o control interactivo en la interfaz Streamlit
        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
        # Asignamos 'lbl_fav' con '★ En Seguimiento' if ya_es_favorito else ...
        lbl_fav = "★ En Seguimiento" if ya_es_favorito else "☆ Monitorear Precio"
        # Evaluamos la condición lógica (st.button(lbl_fav, key=f'btn_toggle_fav_{selected_id...) para controlar el flujo
        if st.button(lbl_fav, key=f"btn_toggle_fav_{selected_id}", use_container_width=True):
            # Evaluamos la condición lógica (not st.session_state.get('logged_in') or not st.sess...) para controlar el flujo
            if not st.session_state.get('logged_in') or not st.session_state.get('user_info'):
                # Asignamos 'st.session_state['show_login_mod...' con True
                st.session_state['show_login_modal'] = True
                # Ejecutamos instrucción: st.rerun()
                st.rerun()
            else:
                # Asignamos 'u_ident' con st.session_state['user_info'].get('id') or...
                u_ident = st.session_state['user_info'].get('id') or st.session_state['user_info'].get('email')
                # Evaluamos la condición lógica (ya_es_favorito) para controlar el flujo
                if ya_es_favorito:
                    # Ejecutamos instrucción: eliminar_favorito(u_ident, int(selected_id))
                    eliminar_favorito(u_ident, int(selected_id))
                    # Asignamos 'st.session_state['favoritos']' con [x for x in favs_actuales if int(x) != int...
                    st.session_state['favoritos'] = [x for x in favs_actuales if int(x) != int(selected_id)]
                    # Ejecutamos instrucción: st.toast('Fragancia retirada de tu seguimiento.', ic...
                    st.toast("Fragancia retirada de tu seguimiento.", icon="🗑️")
                else:
                    # Ejecutamos instrucción: agregar_favorito(u_ident, int(selected_id))
                    agregar_favorito(u_ident, int(selected_id))
                    # Asignamos 'st.session_state['favoritos']' con list(set(favs_actuales + [int(selected_id)]))
                    st.session_state['favoritos'] = list(set(favs_actuales + [int(selected_id)]))
                    # Ejecutamos instrucción: st.toast('Fragancia guardada en tu seguimiento de pr...
                    st.toast("Fragancia guardada en tu seguimiento de precios.", icon="⭐")
                # Ejecutamos instrucción: st.rerun()
                st.rerun()

    # Gestión automática de contexto y recursos para: col_wa_btn
    with col_wa_btn:
        # Renderizado de componente visual o control interactivo en la interfaz Streamlit
        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
        # Renderizado de componente visual o control interactivo en la interfaz Streamlit
        st.markdown(
            f'''<a href="{wa_href}" target="_blank" rel="noopener noreferrer" class="pt-wa-share-btn">💬 WhatsApp</a>''',
            unsafe_allow_html=True,
        )

    # Gestión automática de contexto y recursos para: col_share_btn
    with col_share_btn:
        # Renderizado de componente visual o control interactivo en la interfaz Streamlit
        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
        # Evaluamos la condición lógica (st.button('🔗 Enlace', key=f'btn_copy_link_{selected_...) para controlar el flujo
        if st.button("🔗 Enlace", key=f"btn_copy_link_{selected_id}", use_container_width=True):
            # Ejecutamos instrucción: st.toast(f'Enlace listo para compartir: {url_directa...
            st.toast(f"Enlace listo para compartir: {url_directa}", icon="📋")

# Renderizado de componente visual o control interactivo en la interfaz Streamlit
st.markdown("<div style='margin-top: 32px;'></div>", unsafe_allow_html=True)
# Renderizado de componente visual o control interactivo en la interfaz Streamlit
st.markdown("<div class='pt-section-row'><div class='pt-section-title'>Ofertas en tiendas chilenas verificadas</div></div>", unsafe_allow_html=True)


# =============================================================================
# - ¿Qué hace este bloque (Comparativa Multitienda en Vivo)?:
#   1. Agrupa y filtra las ofertas activas por tamaño de botella (ej. 50ml, 100ml, 200ml).
#   2. Ordena las tiendas de menor a mayor precio, colocando siempre primero las ofertas con stock.
#   3. Identifica la mejor oferta, calcula el costo por mililitro ($/ml) y destaca los Mínimos Históricos.
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
# Evaluamos la condición lógica (tiendas_db) para controlar el flujo
if tiendas_db:
    # Asignamos 'tiendas_db' con [t for t in tiendas_db if es_precio_valido...
    tiendas_db = [t for t in tiendas_db if es_precio_valido(t.get('precio_actual'))]

# Evaluamos la condición lógica (not tiendas_db) para controlar el flujo
if not tiendas_db:
    # Ejecutamos instrucción: st.info('Actualmente estamos sincronizando los preci...
    st.info("Actualmente estamos sincronizando los precios en tiempo real para esta fragancia.")
else:
    # Definición de función 'extraer_volumen' (parámetros: item)
    def extraer_volumen(item):
        # Bloque try/except para manejo seguro de errores y resiliencia operativa
        try:
            # Asignamos 'val' con item.get('volumen_ml')
            val = item.get('volumen_ml')
            # Evaluamos la condición lógica (val is not None and float(val) > 0) para controlar el flujo
            if val is not None and float(val) > 0:
                # Retornamos el resultado procesado (int(round(float(val))))
                return int(round(float(val)))
        except Exception:
            # Ejecutamos instrucción: pass
            pass
        # Retornamos el resultado procesado (100)
        return 100

    # Definición de función 'esta_en_stock' (parámetros: item)
    def esta_en_stock(item):
        # Asignamos 'val' con item.get('en_stock')
        val = item.get('en_stock')
        # Evaluamos la condición lógica (val is None) para controlar el flujo
        if val is None:
            # Retornamos el resultado procesado (True)
            return True
        # Evaluamos la condición lógica (isinstance(val, str)) para controlar el flujo
        if isinstance(val, str):
            # Retornamos el resultado procesado (val.lower() not in ('false', '0', 'agotado', 'f...)
            return val.lower() not in ('false', '0', 'agotado', 'f', 'no')
        # Retornamos el resultado procesado (bool(val))
        return bool(val)

    # 1. Obtener todas las presentaciones de volumen (ml) disponibles para la fragancia
    vols_disponibles = sorted(list({extraer_volumen(t) for t in tiendas_db}))
    # Asignamos 'key_filtro' con f'filtro_vol_{selected_id}'
    key_filtro = f"filtro_vol_{selected_id}"

    # 2. Selector de presentación estilo Falabella ("Elige una opción:")
    if vols_disponibles:
        # Asignamos 'opciones_vol' con ['Todos'] + [f'{v} ML' for v in vols_dispo...
        opciones_vol = ["Todos"] + [f"{v} ML" for v in vols_disponibles]
        
        # Evaluamos la condición lógica (key_filtro not in st.session_state) para controlar el flujo
        if key_filtro not in st.session_state:
            # Asignamos 'sel_guardada' con 'Todos'
            sel_guardada = "Todos"
        else:
            # Asignamos 'sel_guardada' con st.session_state.get(key_filtro, 'Todos')
            sel_guardada = st.session_state.get(key_filtro, "Todos")
            
        # Asignamos 'default_val' con sel_guardada if sel_guardada in opciones_v...
        default_val = sel_guardada if sel_guardada in opciones_vol else "Todos"

        # Pre-filtrar temporalmente para obtener métricas de stock antes de renderizar el selector
        if sel_guardada and sel_guardada != "Todos":
            # Bloque try/except para manejo seguro de errores y resiliencia operativa
            try:
                # Asignamos 'v_num_pre' con int(sel_guardada.upper().replace('ML', '')...
                v_num_pre = int(sel_guardada.upper().replace("ML", "").strip())
                # Asignamos 'pre_filtradas' con [t for t in tiendas_db if extraer_volumen(...
                pre_filtradas = [t for t in tiendas_db if extraer_volumen(t) == v_num_pre]
            except Exception:
                # Asignamos 'pre_filtradas' con list(tiendas_db)
                pre_filtradas = list(tiendas_db)
        else:
            # Asignamos 'pre_filtradas' con list(tiendas_db)
            pre_filtradas = list(tiendas_db)

        # Evaluamos la condición lógica (not pre_filtradas) para controlar el flujo
        if not pre_filtradas:
            # Asignamos 'pre_filtradas' con list(tiendas_db)
            pre_filtradas = list(tiendas_db)

        # Asignamos 'hay_stock_pre' con any((esta_en_stock(t) for t in pre_filtrad...
        hay_stock_pre = any(esta_en_stock(t) for t in pre_filtradas)
        # Evaluamos la condición lógica (hay_stock_pre) para controlar el flujo
        if hay_stock_pre:
            # Asignamos 'indicador_stock' con "<span class='pt-stock pt-stock-ok'><span ...
            indicador_stock = "<span class='pt-stock pt-stock-ok'><span class='pt-dot'></span>En stock</span>"
        else:
            # Asignamos 'indicador_stock' con "<span class='pt-stock pt-stock-out'><span...
            indicador_stock = "<span class='pt-stock pt-stock-out'><span class='pt-dot'></span>Agotado en tiendas</span>"

        # Renderizado de componente visual o control interactivo en la interfaz Streamlit
        st.markdown(
            clean_html(f"""
            <div class="offer-toolbar">
                <div class="offer-toolbar-left">
                    <div class="offer-toolbar-label">Elige una presentación:</div>
                    {indicador_stock}
                </div>
                <div class="offer-toolbar-meta">
                    Mostrando {len(pre_filtradas)} oferta{'s' if len(pre_filtradas) != 1 else ''}, ordenadas por precio (disponibles primero)
                </div>
            </div>
            """),
            unsafe_allow_html=True
        )

        # Asignamos 'seleccion_vol' con st.pills('Elige una opción (ml):', options...
        seleccion_vol = st.pills(
            "Elige una opción (ml):",
            options=opciones_vol,
            default=default_val,
            key=key_filtro,
            label_visibility="collapsed"
        )
        # Evaluamos la condición lógica (not seleccion_vol) para controlar el flujo
        if not seleccion_vol:
            # Asignamos 'seleccion_vol' con 'Todos'
            seleccion_vol = "Todos"

        # Evaluamos la condición lógica (seleccion_vol != 'Todos') para controlar el flujo
        if seleccion_vol != "Todos":
            # Bloque try/except para manejo seguro de errores y resiliencia operativa
            try:
                # Asignamos 'vol_num' con int(seleccion_vol.upper().replace('ML', ''...
                vol_num = int(seleccion_vol.upper().replace("ML", "").strip())
                # Asignamos 'tiendas_filtradas' con [t for t in tiendas_db if extraer_volumen(...
                tiendas_filtradas = [t for t in tiendas_db if extraer_volumen(t) == vol_num]
            except Exception:
                # Asignamos 'tiendas_filtradas' con list(tiendas_db)
                tiendas_filtradas = list(tiendas_db)
        else:
            # Asignamos 'tiendas_filtradas' con list(tiendas_db)
            tiendas_filtradas = list(tiendas_db)
    else:
        # Asignamos 'seleccion_vol' con 'Todos'
        seleccion_vol = "Todos"
        # Asignamos 'tiendas_filtradas' con list(tiendas_db)
        tiendas_filtradas = list(tiendas_db)

    # Evaluamos la condición lógica (not tiendas_filtradas) para controlar el flujo
    if not tiendas_filtradas:
        # Asignamos 'tiendas_filtradas' con list(tiendas_db)
        tiendas_filtradas = list(tiendas_db)

    # 3. Ordenamiento inteligente estricto:
    #    - Primero: ofertas con stock disponible (en_stock == True), priorizando formato regular a igual precio.
    #    - Al final: ofertas agotadas (en_stock == False), ordenadas de menor a mayor precio.
    def es_tester_item(it):
        # Retornamos el resultado procesado (str(it.get('formato') or '').lower() == 'tester...)
        return str(it.get('formato') or '').lower() == 'tester' or 'tester' in str(it.get('url_producto') or '').lower()

    # Asignamos 'tiendas_ordenadas' con sorted(tiendas_filtradas, key=lambda x: (0...
    tiendas_ordenadas = sorted(
        tiendas_filtradas,
        key=lambda x: (
            0 if esta_en_stock(x) else 1,
            x.get('precio_actual', 0) if x.get('precio_actual', 0) > 0 else 999999999,
            1 if es_tester_item(x) else 0,
        )
    )

    # 4. Identificar el mejor precio y el mejor valor por ml priorizando botellas selladas ('regular').
    def es_oferta_fresca_elegible(it):
        # Evaluamos la condición lógica (it.get('excluida_mejor_precio')) para controlar el flujo
        if it.get('excluida_mejor_precio'):
            # Retornamos el resultado procesado (False)
            return False
        # Retornamos el resultado procesado (True)
        return True

    # Asignamos 'precios_regular_stock' con [t['precio_actual'] for t in tiendas_filtr...
    precios_regular_stock = [
        t['precio_actual']
        for t in tiendas_filtradas
        if t.get('precio_actual', 0) > 0 and esta_en_stock(t) and not es_tester_item(t) and es_oferta_fresca_elegible(t)
    ]
    # Asignamos 'precios_validos' con [t['precio_actual'] for t in tiendas_filtr...
    precios_validos = [
        t['precio_actual']
        for t in tiendas_filtradas
        if t.get('precio_actual', 0) > 0 and esta_en_stock(t) and es_oferta_fresca_elegible(t)
    ]
    # Asignamos 'hay_alguna_en_stock' con any((t.get('precio_actual', 0) > 0 and est...
    hay_alguna_en_stock = any(t.get('precio_actual', 0) > 0 and esta_en_stock(t) for t in tiendas_filtradas)
    # Asignamos 'hay_regular_en_stock' con len(precios_regular_stock) > 0
    hay_regular_en_stock = len(precios_regular_stock) > 0
    # Asignamos 'min_precio' con min(precios_regular_stock) if hay_regular_...
    min_precio = min(precios_regular_stock) if hay_regular_en_stock else (min(precios_validos) if precios_validos else 0)

    # Calcular mejor costo por mililitro ($/ml) cuando se comparan múltiples volúmenes ('Todos')
    min_precio_ml = 0.0
    # Evaluamos la condición lógica (len({extraer_volumen(t) for t in tiendas_filtradas i...) para controlar el flujo
    if len({extraer_volumen(t) for t in tiendas_filtradas if esta_en_stock(t) and es_oferta_fresca_elegible(t)}) > 1:
        # Asignamos 'candidatos_ml' con [t['precio_actual'] / max(1, extraer_volum...
        candidatos_ml = [
            t['precio_actual'] / max(1, extraer_volumen(t))
            for t in tiendas_filtradas
            if t.get('precio_actual', 0) > 0 and esta_en_stock(t) and es_oferta_fresca_elegible(t) and (not es_tester_item(t) if hay_regular_en_stock else True)
        ]
        # Evaluamos la condición lógica (candidatos_ml) para controlar el flujo
        if candidatos_ml:
            # Asignamos 'min_precio_ml' con min(candidatos_ml)
            min_precio_ml = min(candidatos_ml)

    # Asignamos 'total_agotados' con len([t for t in tiendas_ordenadas if not e...
    total_agotados = len([t for t in tiendas_ordenadas if not esta_en_stock(t)])
    # Asignamos 'total_disponibles' con len(tiendas_ordenadas) - total_agotados
    total_disponibles = len(tiendas_ordenadas) - total_agotados

    # Evaluamos la condición lógica (not hay_alguna_en_stock) para controlar el flujo
    if not hay_alguna_en_stock:
        # Renderizado de componente visual o control interactivo en la interfaz Streamlit
        st.markdown(
            clean_html("""
            <div class="offer-alert">
                <span class="pt-dot" style="width: 8px; height: 8px;"></span>
                <div>Presentación sin stock disponible en este momento. Mostrando últimos precios de referencia abajo.</div>
            </div>
            """),
            unsafe_allow_html=True
        )

    # 5. Renderizado de tarjetas con separador antes de los agotados y distintivo TESTER transparente
    separador_mostrado = False

    # Recorremos iterativamente cada 'item' en tiendas_ordenadas
    for item in tiendas_ordenadas:
        # Asignamos 'p_act' con item.get('precio_actual', 0)
        p_act = item.get('precio_actual', 0)
        # Asignamos 'p_norm' con item.get('precio_normal', 0)
        p_norm = item.get('precio_normal', 0)
        # Asignamos 'vol_ml' con extraer_volumen(item)
        vol_ml = extraer_volumen(item)
        # Asignamos 'en_stock' con esta_en_stock(item)
        en_stock = esta_en_stock(item)
        # Asignamos 'es_tester' con es_tester_item(item)
        es_tester = es_tester_item(item)
        # - ¿Qué hace esta lógica (Detección de la Mejor Oferta + Frescura)?:
        #   Determina si esta tienda tiene el precio más bajo del mercado en stock y verificado (<=7 días),
        #   priorizando frascos sellados estándar sobre unidades tester para no engañar al usuario.
        es_elegible_frescura = es_oferta_fresca_elegible(item)
        # Asignamos 'dias_sv_raw' con item.get('dias_sin_verificar')
        dias_sv_raw = item.get('dias_sin_verificar')
        # Asignamos 'dias_sv_num' con float(dias_sv_raw) if dias_sv_raw is not N...
        dias_sv_num = float(dias_sv_raw) if dias_sv_raw is not None else 0.0
        # Asignamos 'dias_sv_int' con max(1, int(round(dias_sv_num))) if dias_sv...
        dias_sv_int = max(1, int(round(dias_sv_num))) if dias_sv_raw is not None else 0

        # Asignamos 'is_best_deal' con p_act == min_precio and p_act > 0 and en_s...
        is_best_deal = (
            p_act == min_precio
            and p_act > 0
            and en_stock
            and es_elegible_frescura
            and (not es_tester if hay_regular_en_stock else True)
        )

        # Si pasamos a las ofertas agotadas y habían ofertas en stock, mostrar separador al final
        if not en_stock and not separador_mostrado and total_disponibles > 0:
            # Asignamos 'separador_mostrado' con True
            separador_mostrado = True
            # Renderizado de componente visual o control interactivo en la interfaz Streamlit
            st.markdown(
                clean_html(f"""
                <div class="offer-separator">
                    <div class="offer-separator-label">Tiendas sin stock ({total_agotados})</div>
                    <div class="offer-separator-line"></div>
                </div>
                """),
                unsafe_allow_html=True
            )

        # Asignamos 'card_class' con 'price-card best-deal' if is_best_deal els...
        card_class = "price-card best-deal" if is_best_deal else ("price-card" if en_stock else "price-card out-of-stock")

        # Evaluamos la condición lógica (is_best_deal) para controlar el flujo
        if is_best_deal:
            # Asignamos 'lbl_best' con 'Mejor precio tester' if es_tester else 'M...
            lbl_best = "Mejor precio tester" if es_tester else "Mejor precio"
            # Asignamos 'status_badge' con f"<span class='pt-tag pt-tag-best'>{lbl_be...
            status_badge = f"<span class='pt-tag pt-tag-best'>{lbl_best}</span>"
        # Evaluamos la condición lógica (not en_stock) para controlar el flujo
        elif not en_stock:
            # Asignamos 'status_badge' con "<span class='pt-tag pt-tag-out'>Agotado</...
            status_badge = "<span class='pt-tag pt-tag-out'>Agotado</span>"
        else:
            # Asignamos 'is_best_ml' con min_precio_ml > 0 and en_stock and es_eleg...
            is_best_ml = (
                min_precio_ml > 0
                and en_stock
                and es_elegible_frescura
                and (not es_tester if hay_regular_en_stock else True)
                and abs((p_act / max(1, vol_ml)) - min_precio_ml) < 0.5
            )
            # Evaluamos la condición lógica (is_best_ml) para controlar el flujo
            if is_best_ml:
                # Asignamos 'status_badge' con "<span class='pt-tag pt-tag-ml'>Mejor valo...
                status_badge = "<span class='pt-tag pt-tag-ml'>Mejor valor por ml</span>"
            else:
                # Asignamos 'status_badge' con ''
                status_badge = ""

        # Asignamos 'badge_tester' con "<span class='pt-tag pt-tag-tester' title=...
        badge_tester = (
            "<span class='pt-tag pt-tag-tester' title='Unidad Tester de demostración comercial (puede venir en caja neutra o sin celofán)'>Tester</span>"
            if es_tester else ""
        )

        # - ¿Qué hace esta lógica (Insignia de Mínimo Histórico)?:
        #   Compara el precio en vivo contra el mínimo histórico registrado en Supabase/SQLite para esa presentación.
        #   Si es igual o menor, activa el badge visual '🔥 Mínimo Histórico' para avisar que es el mejor momento para comprar.
        min_historico_vol = get_cached_minimo_historico(selected_id, vol_ml)
        # Asignamos 'es_min_hist' con en_stock and es_elegible_frescura and (p_a...
        es_min_hist = (
            en_stock
            and es_elegible_frescura
            and p_act > 0
            and min_historico_vol is not None
            and p_act <= min_historico_vol
        )
        # Asignamos 'badge_minimo_hist' con "<span class='pt-tag pt-tag-alltime' title...
        badge_minimo_hist = (
            "<span class='pt-tag pt-tag-alltime' title='Precio más bajo jamás registrado para este perfume'>🔥 Mínimo Histórico</span>"
            if es_min_hist else ""
        )
        # Asignamos 'badge_frescura' con ''
        badge_frescura = ""

        # Asignamos 'precio_actual_str' con f'${p_act:,.0f}'.replace(',', '.')
        precio_actual_str = f"${p_act:,.0f}".replace(",", ".")
        # Asignamos 'precio_ant_str' con f'${p_norm:,.0f}'.replace(',', '.') if p_n...
        precio_ant_str = f"${p_norm:,.0f}".replace(",", ".") if p_norm and p_norm > p_act else ""
        # Asignamos 'old_price_html' con f"<span class='pt-old-price'>{precio_ant_s...
        old_price_html = f"<span class='pt-old-price'>{precio_ant_str}</span>" if (precio_ant_str and en_stock) else ""

        # Asignamos 'ml_txt' con ''
        ml_txt = ""
        # Evaluamos la condición lógica (p_act > 0 and vol_ml > 0 and en_stock) para controlar el flujo
        if p_act > 0 and vol_ml > 0 and en_stock:
            # Asignamos 'p_ml' con int(round(p_act / vol_ml))
            p_ml = int(round(p_act / vol_ml))
            # Asignamos 'ml_txt' con f"<span class='pt-price-ml'>${p_ml:,.0f}/m...
            ml_txt = f"<span class='pt-price-ml'>${p_ml:,.0f}/ml ({vol_ml} ml)</span>".replace(",", ".")

        # Asignamos 'url_directa' con sanitize_external_url(resolver_url_oferta(...
        url_directa = sanitize_external_url(
            resolver_url_oferta(
                tienda_nombre=item.get('tienda_nombre', ''),
                perfume_nombre=detalle.get('nombre', ''),
                url_prod=item.get('url_producto', ''),
                url_base=item.get('url_base', ''),
                marca=detalle.get('marca', '')
            )
        )
        # Asignamos 'tienda_safe' con escape_html(item.get('tienda_nombre', 'Tie...
        tienda_safe = escape_html(item.get('tienda_nombre', 'Tienda'))
        # Asignamos 'badge_tienda_safe' con escape_html(item.get('badge', 'Tienda Veri...
        badge_tienda_safe = escape_html(item.get('badge', 'Tienda Verificada'))
        # Asignamos 'badge_vol' con f"<span class='pt-tag pt-tag-strong'>{vol_...
        badge_vol = f"<span class='pt-tag pt-tag-strong'>{vol_ml} ml</span>" if vol_ml else ""

        # Evaluamos la condición lógica (not en_stock) para controlar el flujo
        if not en_stock:
            # Asignamos 'price_display_html' con f'\n <div class="price-block">\n <span cla...
            price_display_html = f"""
            <div class="price-block">
                <span class="pt-price-out">Agotado</span>
                <span class="pt-price-out-old">{precio_actual_str} CLP</span>
            </div>
            """
            # Asignamos 'btn_label' con 'Ver en tienda (Agotado) ↗'
            btn_label = "Ver en tienda (Agotado) ↗"
            # Asignamos 'btn_extra_style' con ''
            btn_extra_style = ""
        else:
            # Asignamos 'price_display_html' con f'\n <div class="price-block">\n {old_pric...
            price_display_html = f"""
            <div class="price-block">
                {old_price_html}
                <span class="pt-price-value">{precio_actual_str} CLP</span>
                {ml_txt}
            </div>
            """
            # Asignamos 'btn_label' con 'Ir a la oferta ↗'
            btn_label = "Ir a la oferta ↗"
            # Asignamos 'btn_extra_style' con ''
            btn_extra_style = ""

        # Asignamos 'html_card' con f'\n <div class="{card_class}">\n <div cla...
        html_card = f"""
        <div class="{card_class}">
            <div class="price-card-left">
                <span class="store-name">{tienda_safe}</span>
                <span class="pt-tag">{badge_tienda_safe}</span>
                {badge_vol}
                {badge_tester}
                {status_badge}
                {badge_minimo_hist}
                {badge_frescura}
            </div>
            <div class="price-card-right">
                {price_display_html}
                <a href="{url_directa}" class="buy-btn" style="{btn_extra_style}" target="_blank" rel="noopener noreferrer">{btn_label}</a>
            </div>
        </div>
        """
        # Renderizado de componente visual o control interactivo en la interfaz Streamlit
        st.markdown(clean_html(html_card), unsafe_allow_html=True)


# =============================================================================
# - ¿Qué hace este bloque (Gráfico Histórico de Precios)?:
#   Transforma las observaciones históricas en una tabla pivotada (fecha vs tienda)
#   y dibuja la curva temporal de precios para comprobar si la fragancia ha subido o bajado.
# BLOQUE 6: GRÁFICO INTERACTIVO DE EVOLUCIÓN HISTÓRICA DE PRECIOS POR VOLUMEN
# =============================================================================
st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
# Asignamos 'vol_filtro_hist' con None
vol_filtro_hist = None
# Evaluamos la condición lógica ('seleccion_vol' in locals() and seleccion_vol != 'To...) para controlar el flujo
if 'seleccion_vol' in locals() and seleccion_vol != "Todos":
    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Asignamos 'vol_filtro_hist' con int(seleccion_vol.upper().replace('ML', ''...
        vol_filtro_hist = int(seleccion_vol.upper().replace("ML", "").strip())
    except Exception:
        # Asignamos 'vol_filtro_hist' con None
        vol_filtro_hist = None

# Asignamos 'titulo_hist' con f'Ver Evolución Histórica de Precios ({vol...
titulo_hist = (
    f"Ver Evolución Histórica de Precios ({vol_filtro_hist} ML)"
    if vol_filtro_hist
    else "Ver Evolución Histórica de Precios en Tiendas Chilenas"
)
# Gestión automática de contexto y recursos para: st.expander(titulo_hist)
with st.expander(titulo_hist):
    # Asignamos 'historico' con get_cached_historico(selected_id, volumen_...
    historico = get_cached_historico(selected_id, volumen_ml=vol_filtro_hist)
    # Evaluamos la condición lógica (historico) para controlar el flujo
    if historico:
        # Asignamos 'df_hist' con pd.DataFrame(historico)
        df_hist = pd.DataFrame(historico)
        # Evaluamos la condición lógica ('fecha_registro' in df_hist.columns and 'fecha' not ...) para controlar el flujo
        if 'fecha_registro' in df_hist.columns and 'fecha' not in df_hist.columns:
            # Asignamos 'df_hist' con df_hist.rename(columns={'fecha_registro': ...
            df_hist = df_hist.rename(columns={'fecha_registro': 'fecha'})
        # Evaluamos la condición lógica ('precio_actual' in df_hist.columns and 'precio' not ...) para controlar el flujo
        if 'precio_actual' in df_hist.columns and 'precio' not in df_hist.columns:
            # Asignamos 'df_hist' con df_hist.rename(columns={'precio_actual': '...
            df_hist = df_hist.rename(columns={'precio_actual': 'precio'})

        # Evaluamos la condición lógica ('fecha' in df_hist.columns and 'precio' in df_hist.c...) para controlar el flujo
        if 'fecha' in df_hist.columns and 'precio' in df_hist.columns and 'tienda' in df_hist.columns:
            # Asignamos 'df_hist['fecha']' con pd.to_datetime(df_hist['fecha'], errors='c...
            df_hist['fecha'] = pd.to_datetime(df_hist['fecha'], errors='coerce')
            # Asignamos 'df_hist' con df_hist.dropna(subset=['fecha', 'precio'])
            df_hist = df_hist.dropna(subset=['fecha', 'precio'])
            # Evaluamos la condición lógica (not df_hist.empty) para controlar el flujo
            if not df_hist.empty:
                # Evaluamos la condición lógica (HAS_PLOTLY) para controlar el flujo
                if HAS_PLOTLY:
                    # Asignamos 'fig' con go.Figure()
                    fig = go.Figure()
                    # Asignamos 'tiendas_series' con list(df_hist['tienda'].unique())
                    tiendas_series = list(df_hist['tienda'].unique())
                    # Asignamos 'palette_colors' con ['#e11d48', '#2563eb', '#16a34a', '#d97706...
                    palette_colors = [
                        "#e11d48", "#2563eb", "#16a34a", "#d97706",
                        "#8b5cf6", "#06b6d4", "#ec4899", "#10b981",
                        "#f97316", "#6366f1"
                    ]

                    # Recorremos iterativamente cada '(idx_t, t_nom)' en enumerate(tiendas_series)
                    for idx_t, t_nom in enumerate(tiendas_series):
                        # Asignamos 'df_t' con df_hist[df_hist['tienda'] == t_nom].sort_v...
                        df_t = df_hist[df_hist['tienda'] == t_nom].sort_values('fecha')
                        # Asignamos 'color_line' con palette_colors[idx_t % len(palette_colors)]
                        color_line = palette_colors[idx_t % len(palette_colors)]
                        # Ejecutamos instrucción: fig.add_trace(go.Scatter(x=df_t['fecha'], y=df_t['pr...
                        fig.add_trace(go.Scatter(
                            x=df_t['fecha'],
                            y=df_t['precio'],
                            mode='lines+markers',
                            name=t_nom,
                            line=dict(width=2.5, color=color_line),
                            marker=dict(size=7, color=color_line),
                            hovertemplate=f"<b>{t_nom}</b><br>Fecha: %{{x|%d %b %Y}}<br>Precio: $%{{y:,.0f}} CLP<extra></extra>",
                        ))

                    # Línea horizontal del Mínimo Histórico
                    min_record = get_cached_minimo_historico(selected_id, volumen_ml=vol_filtro_hist)
                    # Evaluamos la condición lógica (min_record and min_record > 0) para controlar el flujo
                    if min_record and min_record > 0:
                        # Ejecutamos instrucción: fig.add_hline(y=min_record, line_dash='dot', line_co...
                        fig.add_hline(
                            y=min_record,
                            line_dash="dot",
                            line_color="#f59e0b",
                            line_width=2,
                            annotation_text=f"🔥 Récord Mínimo: ${min_record:,.0f} CLP",
                            annotation_position="bottom right",
                            annotation_font_color="#f59e0b",
                            annotation_font_size=11,
                        )

                    # Asignamos 'text_color_plotly' con '#f1f5f9' if is_dark else '#1e293b'
                    text_color_plotly = "#f1f5f9" if is_dark else "#1e293b"
                    # Asignamos 'grid_color_plotly' con 'rgba(255, 255, 255, 0.08)' if is_dark els...
                    grid_color_plotly = "rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.06)"

                    # Ejecutamos instrucción: fig.update_layout(margin=dict(l=20, r=20, t=35, b=25...
                    fig.update_layout(
                        margin=dict(l=20, r=20, t=35, b=25),
                        height=380,
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(family="system-ui, sans-serif", color=text_color_plotly, size=12),
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=1.03,
                            xanchor="right",
                            x=1,
                            font=dict(size=11),
                        ),
                        xaxis=dict(
                            showgrid=True,
                            gridcolor=grid_color_plotly,
                            tickformat="%d %b %Y",
                            color=text_color_plotly,
                        ),
                        yaxis=dict(
                            showgrid=True,
                            gridcolor=grid_color_plotly,
                            tickprefix="$",
                            tickformat=",.0f",
                            color=text_color_plotly,
                        ),
                        hovermode="closest",
                    )
                    # Ejecutamos instrucción: st.plotly_chart(fig, use_container_width=True, confi...
                    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
                else:
                    # Asignamos 'df_pivot' con df_hist.pivot_table(index='fecha', columns...
                    df_pivot = df_hist.pivot_table(index='fecha', columns='tienda', values='precio', aggfunc='min')
                    # Ejecutamos instrucción: st.line_chart(df_pivot)
                    st.line_chart(df_pivot)
            else:
                # Ejecutamos instrucción: st.caption('Aún no existen suficientes puntos tempor...
                st.caption("Aún no existen suficientes puntos temporales verificados para graficar esta presentación.")
        else:
            # Ejecutamos instrucción: st.dataframe(df_hist, use_container_width=True)
            st.dataframe(df_hist, use_container_width=True)
    else:
        # Ejecutamos instrucción: st.caption('Recopilando observaciones históricas ver...
        st.caption("Recopilando observaciones históricas verificadas en comercios chilenos para esta presentación.")

# =============================================================================
# BLOQUE 7: FRAGANCIAS RELACIONADAS DE LA MISMA MARCA O FAMILIA
# =============================================================================
p_marca_actual = str(detalle.get("marca") or "").strip().lower()
# Asignamos 'p_gen_actual' con str(detalle.get('genero') or '').strip().l...
p_gen_actual = str(detalle.get("genero") or "").strip().lower()

# Asignamos 'relacionados' con [p for p in catalogo if p['id'] != selecte...
relacionados = [
    p for p in catalogo
    if p["id"] != selected_id
    and (p.get("marca") or "").strip().lower() == p_marca_actual
]

# Priorizar fragancias del mismo género
mismo_gen = [p for p in relacionados if str(p.get("genero") or "").strip().lower() == p_gen_actual]
# Asignamos 'otros_gen' con [p for p in relacionados if str(p.get('gen...
otros_gen = [p for p in relacionados if str(p.get("genero") or "").strip().lower() != p_gen_actual]
# Asignamos 'rel_final' con (mismo_gen + otros_gen)[:4]
rel_final = (mismo_gen + otros_gen)[:4]

# Si la marca tiene pocas opciones, completar con perfumes en tendencia del mismo género
if len(rel_final) < 4:
    # Asignamos 'tendencias' con [p for p in catalogo if p['id'] != selecte...
    tendencias = [
        p for p in catalogo
        if p["id"] != selected_id
        and p["id"] not in [r["id"] for r in rel_final]
        and str(p.get("genero") or "").strip().lower() == p_gen_actual
        and p.get("en_tendencia")
    ]
    # Asignamos 'rel_final' con (rel_final + tendencias)[:4]
    rel_final = (rel_final + tendencias)[:4]

# Evaluamos la condición lógica (rel_final) para controlar el flujo
if rel_final:
    # Renderizado de componente visual o control interactivo en la interfaz Streamlit
    st.markdown("<div style='margin-top: 40px;'></div>", unsafe_allow_html=True)
    # Renderizado de componente visual o control interactivo en la interfaz Streamlit
    st.markdown(
        clean_html(f"""
        <div class="pt-section-row">
            <div class="pt-section-title">Fragancias recomendadas de {marca_safe}</div>
            <div class="pt-section-meta">Misma marca, {genero_safe}</div>
        </div>
        """),
        unsafe_allow_html=True,
    )

    # Renderizado de componente visual o control interactivo en la interfaz Streamlit
    cols_rel = st.columns(len(rel_final), gap="medium")
    # Recorremos iterativamente cada '(idx_rel, p_rel)' en enumerate(rel_final)
    for idx_rel, p_rel in enumerate(rel_final):
        # Gestión automática de contexto y recursos para: cols_rel[idx_rel]
        with cols_rel[idx_rel]:
            # Asignamos 'img_rel' con get_image_src(p_rel.get('imagen_url'))
            img_rel = get_image_src(p_rel.get("imagen_url"))
            # Asignamos 'nom_rel' con formatear_nombre_especifico(p_rel) or p_re...
            nom_rel = formatear_nombre_especifico(p_rel) or p_rel.get("nombre", "")
            # Asignamos 'nom_rel_safe' con escape_html(nom_rel)
            nom_rel_safe = escape_html(nom_rel)
            # Asignamos 'marca_rel_safe' con escape_html(p_rel.get('marca', ''))
            marca_rel_safe = escape_html(p_rel.get("marca", ""))
            # Asignamos 'tipo_rel_safe' con escape_html(p_rel.get('tipo', 'EDP'))
            tipo_rel_safe = escape_html(p_rel.get("tipo", "EDP"))
            # Asignamos 'ref_val' con p_rel.get('precio_referencia')
            ref_val = p_rel.get("precio_referencia")
            # Asignamos 'ref_txt' con f'${ref_val:,.0f} CLP'.replace(',', '.') i...
            ref_txt = f"${ref_val:,.0f} CLP".replace(",", ".") if es_precio_valido(ref_val) else "Ver ofertas"

            # Toda la tarjeta abre el perfume; el corazón lo guarda en favoritos
            with st.container(key=f"pcard_rel_{p_rel['id']}"):
                # Renderizado de componente visual o control interactivo en la interfaz Streamlit
                st.markdown(
                    clean_html(f"""
                    <div class="rel-card">
                        <div class="rel-stage">
                            <img src="{img_rel}" alt="{nom_rel_safe}" onerror="this.onerror=null;this.src='{DEFAULT_PERFUME_IMAGE}';">
                        </div>
                        <div class="rel-brand">{marca_rel_safe}, {tipo_rel_safe}</div>
                        <div class="rel-name" title="{nom_rel_safe}">{nom_rel_safe}</div>
                        <div class="rel-price">{ref_txt}</div>
                    </div>
                    """),
                    unsafe_allow_html=True,
                )
                # Ejecutamos instrucción: boton_abrir_perfume(p_rel['id'], 'rel', misma_pagina...
                boton_abrir_perfume(p_rel['id'], "rel", misma_pagina=True)
                # Ejecutamos instrucción: boton_corazon(p_rel['id'], 'rel', nom_rel)
                boton_corazon(p_rel['id'], "rel", nom_rel)
            # Evaluamos la condición lógica (st.button('Comparar', key=f"btn_ir_rel_{p_rel['id']}...) para controlar el flujo
            if st.button("Comparar", key=f"btn_ir_rel_{p_rel['id']}", use_container_width=True):
                # Asignamos 'st.session_state['selected_perfu...' con p_rel['id']
                st.session_state["selected_perfume"] = p_rel["id"]
                # Ejecutamos instrucción: st.rerun()
                st.rerun()

# PIE DE PÁGINA
st.markdown(clean_html("""
    <div class="pt-footer">
        <div class="pt-footer-mark">Perfume<strong>Trending</strong></div>
        <div class="pt-footer-copy">© 2026 Perfume Trending. Todos los derechos reservados.</div>
    </div>
"""), unsafe_allow_html=True)
