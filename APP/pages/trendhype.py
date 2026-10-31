"""
PerfumeTrending.cl — Radar de Tendencias Virales y Hype Score (TikTok/Instagram)
================================================================================
Panel de analítica y descubrimiento de fragancias virales en redes sociales y mercado:
- Cálculo del Hype Score (0 - 100) ponderando menciones semanales, tasa de crecimiento y volumen de búsqueda.
- Segmentación por perfumería oriental/árabe de alta demanda (Lattafa, Armaf, Afnan) vs diseñador occidental.
- Identificación de dupes (clones accesibles de fragancias de nicho de alto costo).
- Gráficas de aceleración de tendencias y recomendaciones personalizadas por afinidad.
"""

import streamlit as st
import streamlit.components.v1 as components
import sys
import os
import base64
import random
from datetime import timedelta, timezone

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

try:
    from backend.database import obtener_catalogo
except (ImportError, ModuleNotFoundError):
    from APP.backend.database import obtener_catalogo
from ui import (
    DEFAULT_PERFUME_IMAGE,
    HOME_RED_SVG as home_red_svg,
    PERFUME_SVG_FAVICON,
    SHIELD_RED_SVG as shield_red_svg,
    TAG_RED_SVG as tag_red_svg,
    TREND_RED_SVG as trend_red_svg,
    cerrar_sesion_usuario,
    clean_html,
    escape_html,
    get_image_src,
    get_theme_palette,
    init_common_session_state,
    toggle_theme,
)
from auth_email import modal_autenticacion
from hype_youtube import PERIODOS, formatear_numero, obtener_ranking_hype
from perfume_actions import (
    boton_abrir_perfume,
    boton_corazon,
    estilos_moviles,
    estilos_tarjetas_cliqueables,
    mostrar_aviso_favoritos,
)


@st.cache_data(ttl=180, show_spinner=False)
def get_cached_catalogo_map():
    cat = obtener_catalogo()
    return {p['id']: p for p in cat}


# 1. CONFIGURACIÓN DE PÁGINA Y ESTADO COMPARTIDO
st.set_page_config(
    page_title="Radar del Hype - PerfumeTrending",
    page_icon=PERFUME_SVG_FAVICON,
    layout="wide",
    initial_sidebar_state="collapsed",
)

init_common_session_state()
if 'current_page' not in st.session_state:
    st.session_state['current_page'] = 'home'
if 'selected_perfume' not in st.session_state:
    st.session_state['selected_perfume'] = None
if 'selected_month' not in st.session_state:
    st.session_state['selected_month'] = 'Este Mes'


def navigate_to(page, perfume_data=None):
    st.session_state['current_page'] = page
    if perfume_data:
        st.session_state['selected_perfume'] = perfume_data


pal = get_theme_palette()
is_dark = pal.is_dark
app_bg = pal.app_bg
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
    app_bg = "#ffffff"
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

# Tokens visuales compartidos con la página de Inicio
accent = "#d83737"
accent_hover = "#b92d2d"
accent_soft = "rgba(216, 55, 55, 0.14)" if is_dark else "rgba(216, 55, 55, 0.07)"
gold = "#d4c2a5" if is_dark else "#8c7b6d"
gold_soft = "rgba(212, 194, 165, 0.16)" if is_dark else "rgba(140, 123, 109, 0.14)"
price_green = "#4ade80" if is_dark else "#15803d"
surface_soft = "rgba(255, 255, 255, 0.035)" if is_dark else "#faf8f5"
shadow_sm = "0 1px 2px rgba(0,0,0,0.35)" if is_dark else "0 1px 2px rgba(40,30,20,0.06)"
shadow_hover = "0 6px 16px rgba(0,0,0,0.35)" if is_dark else "0 6px 16px rgba(60,45,35,0.10)"
font_sans = "'Manrope', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"


# 2. SISTEMA DE SONIDO Y EVENTOS DE TARJETAS
js_color_script = f"""
<script>
(function() {{
    const doc = window.parent.document;
    const isDark = {str(is_dark).lower()};
    
    window.parent.soundMuted = window.parent.soundMuted || false;
    
    window.parent.playBubbleSound = function() {{
        if (window.parent.soundMuted) return;
        try {{
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            if (!AudioContext) return;
            if (!window.parent.audioCtx) {{
                window.parent.audioCtx = new AudioContext();
            }}
            const ctx = window.parent.audioCtx;
            if (ctx.state === 'suspended') {{
                ctx.resume();
            }}
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();

            osc.type = 'sine';
            const now = ctx.currentTime;

            osc.frequency.setValueAtTime(220, now);
            osc.frequency.exponentialRampToValueAtTime(750, now + 0.07);

            gain.gain.setValueAtTime(0.25, now);
            gain.gain.exponentialRampToValueAtTime(0.001, now + 0.07);

            osc.connect(gain);
            gain.connect(ctx.destination);

            osc.start(now);
            osc.stop(now + 0.07);
        }} catch(e) {{ console.error(e); }}
    }};

    function attachCardEvents() {{
        const essenceCards = doc.querySelectorAll('.hype-card, [class*="st-key-pcard_hype_"]');
        essenceCards.forEach(card => {{
            if (!card.dataset.soundAttached) {{
                card.dataset.soundAttached = 'true';
                card.addEventListener('click', () => window.parent.playBubbleSound());
            }}
        }});
    }}

    let debounceTimer = null;
    const observer = new MutationObserver(() => {{
        if (debounceTimer) clearTimeout(debounceTimer);
        debounceTimer = setTimeout(attachCardEvents, 100);
    }});
    
    observer.observe(doc.body, {{ childList: true, subtree: true }});
    attachCardEvents();
}})();
</script>
"""

try:
    st.html(js_color_script, unsafe_allow_javascript=True)
except Exception:
    components.html(js_color_script, height=0, width=0)

# 3. CSS ADAPTABLE, BOTONES Y SWITCH DE TEMA (SIN AFECTAR LOS BOTONES DE POPOVER)
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@300;400;500;600;700;800&display=swap');

    header[data-testid="stHeader"] {{ display: none !important; }}
    div[data-testid="stAppViewContainer"] {{ padding-top: 0px !important; }}

    html, body {{ background-color: {app_bg} !important; }}
    .stApp {{
        background-color: {app_bg} !important;
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

    .stApp p, .stApp span, .stApp label, .stMarkdown p {{
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

    /* Opciones del filtro de período */
    div[class*="st-key-btn_m_"] div.stButton > button {{
        border: 1px solid transparent !important;
        background-color: transparent !important;
        box-shadow: none !important;
        justify-content: flex-start !important;
        min-height: 36px !important;
        border-radius: 8px !important;
    }}
    div[class*="st-key-btn_m_"] div.stButton > button:hover {{
        background-color: {gold_soft} !important;
        border-color: transparent !important;
        box-shadow: none !important;
    }}

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

    /* SWITCH PERSONALIZADO DE TEMA DE BOTELLA */
    .st-key-theme_toggle,
    .st-key-theme_toggle div[data-testid="stButton"] {{
        background: transparent !important;
        background-color: transparent !important;
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

    /* ---------- TÍTULO Y TOOLTIP DE INFORMACIÓN ---------- */
    .radar-head {{
        margin: 2px 0 4px 0;
    }}
    .radar-title-container {{
        display: inline-flex;
        align-items: center;
        gap: 10px;
    }}

    .radar-title-text {{
        font-family: {font_sans} !important;
        color: {text_color} !important;
        font-weight: 800 !important;
        font-size: clamp(1.6rem, 3vw, 2.2rem) !important;
        letter-spacing: -0.025em !important;
        line-height: 1.1 !important;
        margin: 0 !important;
        padding: 0 !important;
        display: inline;
    }}
    .radar-title-text .radar-title-mark {{
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background: {accent};
        margin-left: 4px;
        box-shadow: 0 0 0 4px {accent_soft};
        vertical-align: middle;
        animation: radarPulse 2.4s ease-in-out infinite;
    }}
    @keyframes radarPulse {{
        0%, 100% {{ box-shadow: 0 0 0 3px {accent_soft}; }}
        50% {{ box-shadow: 0 0 0 7px rgba(216, 55, 55, 0); }}
    }}
    .radar-subtitle {{
        font-size: 0.98rem;
        color: {subtext_color};
        margin-top: 8px;
        max-width: 62ch;
        line-height: 1.55;
    }}

    .info-icon-container {{
        position: relative;
        display: inline-block;
    }}

    .info-btn-badge {{
        width: 20px;
        height: 20px;
        background: transparent;
        color: {subtext_color};
        border: 1.5px solid {btn_border};
        border-radius: 50%;
        font-size: 11px;
        font-weight: 800;
        font-family: {font_sans};
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: help;
        transition: border-color 0.2s ease, color 0.2s ease;
    }}

    .info-icon-container:hover .info-btn-badge {{
        border-color: {accent};
        color: {accent};
    }}

    .info-tooltip-box {{
        visibility: hidden;
        opacity: 0;
        width: 320px;
        background-color: {card_bg};
        color: {text_color};
        border: 1px solid {border_color};
        border-radius: 14px;
        padding: 14px 16px;
        position: absolute;
        top: 30px;
        left: -150px;
        z-index: 999;
        box-shadow: {shadow_hover};
        font-size: 0.86rem;
        line-height: 1.55;
        transition: opacity 0.2s ease, visibility 0.2s ease, transform 0.2s ease;
        transform: translateY(-4px);
        pointer-events: none;
    }}

    .info-icon-container:hover .info-tooltip-box {{
        visibility: visible;
        opacity: 1;
        transform: translateY(0);
        pointer-events: auto;
    }}
    .info-tooltip-title {{
        font-weight: 800;
        color: {accent};
        margin-bottom: 6px;
        font-size: 0.92rem;
    }}

    /* ---------- BARRA DE FILTROS ---------- */
    .filter-label-text {{
        color: {subtext_color} !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
        margin: 0 !important;
        display: flex;
        align-items: center !important;
        justify-content: flex-start;
        height: 38px;
        white-space: nowrap;
    }}

    .social-select-box {{
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 10px;
        color: {text_color};
        font-size: 0.88rem;
        width: 100%;
        box-sizing: border-box;
        min-height: 38px;
    }}

    .social-label {{
        color: {subtext_color};
        font-weight: 600;
        white-space: nowrap;
    }}

    .yt-chip-btn {{
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 7px;
        background-color: {btn_bg};
        border: 1px solid {btn_border};
        border-radius: 999px;
        padding: 0 14px;
        height: 34px;
        box-sizing: border-box;
        color: {text_color};
        font-family: {font_sans};
        font-weight: 700;
        font-size: 0.84rem;
        line-height: 1;
        white-space: nowrap;
        cursor: default;
        outline: none;
        user-select: none;
    }}
    .yt-chip-btn span {{ color: {text_color} !important; }}

    .social-desc {{
        font-size: 0.82rem;
        color: {subtext_color};
        line-height: 1.4;
    }}

    .pt-divider {{
        height: 1px;
        background: {btn_border};
        opacity: 0.55;
        margin: 6px 0 8px 0;
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

    /* Página actual resaltada */
    a[data-testid="stPageLink-NavLink"][href*="trendhype"] {{
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

    /* ---------- TARJETAS DE PERFUME DE TENDENCIA ---------- */
    .hype-card {{
        background-color: {card_bg};
        border: 1px solid {border_color};
        border-bottom: none;
        border-radius: 16px 16px 0 0;
        padding: 16px 16px 20px 16px;
        position: relative;
        margin-top: 14px;
        margin-bottom: 0;
        color: {text_color};
        font-family: {font_sans};
        cursor: pointer;
        transition: border-color 0.2s ease;
    }}
    div[data-testid="stColumn"]:has(.hype-card) {{
        margin-bottom: 18px;
    }}
    div[data-testid="stColumn"]:has(.hype-card):hover .hype-card {{
        border-color: {gold};
    }}

    .hype-top {{
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
    }}

    .rank-badge {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-size: 0.95rem;
        font-weight: 800;
        color: {text_color};
        background-color: {surface_soft};
        border: 1px solid {border_color};
        border-radius: 999px;
        padding: 4px 12px 4px 9px;
        font-variant-numeric: tabular-nums;
    }}

    @keyframes minimalStarGlow {{
        0%, 100% {{ transform: scale(1); filter: drop-shadow(0 0 2px rgba(216, 55, 55, 0.3)); opacity: 0.92; }}
        50% {{ transform: scale(1.15); filter: drop-shadow(0 0 7px rgba(216, 55, 55, 0.75)); opacity: 1; }}
    }}

    @keyframes goldStarGlow {{
        0%, 100% {{ transform: scale(1); filter: drop-shadow(0 0 2px rgba(212, 175, 55, 0.3)); opacity: 0.92; }}
        50% {{ transform: scale(1.15); filter: drop-shadow(0 0 7px rgba(241, 196, 15, 0.75)); opacity: 1; }}
    }}

    @keyframes silverStarGlow {{
        0%, 100% {{ transform: scale(1); filter: drop-shadow(0 0 2px rgba(148, 163, 184, 0.3)); opacity: 0.92; }}
        50% {{ transform: scale(1.15); filter: drop-shadow(0 0 7px rgba(226, 232, 240, 0.75)); opacity: 1; }}
    }}

    .star-minimal-ruby {{ animation: minimalStarGlow 3s ease-in-out infinite; display: inline-flex; vertical-align: middle; }}
    .star-minimal-gold {{ animation: goldStarGlow 3.2s ease-in-out infinite; display: inline-flex; vertical-align: middle; }}
    .star-minimal-silver {{ animation: silverStarGlow 3.5s ease-in-out infinite; display: inline-flex; vertical-align: middle; }}

    /* Anillo del Hype Score: se llena según el porcentaje */
    .score-circle {{
        width: 58px;
        height: 58px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
    }}
    .score-inner {{
        width: 48px;
        height: 48px;
        border-radius: 50%;
        background-color: {card_bg};
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
    }}
    .score-value {{
        font-size: 0.95rem;
        font-weight: 800;
        color: {text_color};
        line-height: 1;
        font-variant-numeric: tabular-nums;
    }}
    .score-title {{
        font-size: 0.6rem;
        font-weight: 700;
        color: {subtext_color};
        line-height: 1;
        margin-top: 3px;
        letter-spacing: 0.2px;
    }}

    .img-wrapper {{
        position: relative;
        margin: 10px 0 0 0;
        height: 150px;
        border-radius: 12px;
        background: {"radial-gradient(circle at 50% 45%, #1d222c 0%, #11141a 100%)" if is_dark else "radial-gradient(circle at 50% 45%, #ffffff 0%, #f6f4f1 100%)"};
        display: flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
    }}
    .img-wrapper img {{
        max-width: 70%;
        max-height: 128px;
        object-fit: contain;
        transition: transform 0.35s ease;
        filter: {"drop-shadow(0 10px 18px rgba(0,0,0,0.45))" if is_dark else "drop-shadow(0 8px 14px rgba(60,45,35,0.12))"};
    }}
    div[data-testid="stColumn"]:has(.hype-card):hover .img-wrapper img {{ transform: scale(1.05); }}

    .year-badge {{
        position: absolute;
        bottom: 8px;
        right: 8px;
        background: {card_bg};
        border: 1px solid {border_color};
        border-radius: 999px;
        padding: 2px 9px;
        font-size: 0.72rem;
        font-weight: 700;
        color: {subtext_color};
        font-variant-numeric: tabular-nums;
    }}
    .perfume-title {{
        font-size: 1.05rem;
        font-weight: 700;
        margin: 14px 0 10px 0;
        color: {text_color};
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}
    .stats-row {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 10px;
        margin-bottom: 12px;
    }}
    .stats-text {{
        color: {subtext_color};
        font-size: 0.82rem;
        line-height: 1.4;
    }}
    .chile-badge {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        flex-shrink: 0;
        background-color: {surface_soft};
        border: 1px solid {border_color};
        border-radius: 999px;
        padding: 4px 10px 4px 8px;
        font-weight: 700;
        font-size: 0.72rem;
        line-height: 1.15;
        color: {text_color};
    }}
    .chile-dot {{
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background: {price_green};
        flex-shrink: 0;
    }}
    .ai-box {{
        display: flex;
        gap: 10px;
        align-items: flex-start;
        border-radius: 12px;
        padding: 10px 12px;
        margin-bottom: 12px;
        font-size: 0.82rem;
        line-height: 1.5;
        background-color: {gold_soft};
        color: {text_color};
    }}
    .ai-icon {{
        min-width: 24px;
        height: 24px;
        border-radius: 7px;
        display: flex;
        justify-content: center;
        align-items: center;
        font-weight: 800;
        font-size: 0.66rem;
        background-color: {gold};
        color: {"#1c1917" if is_dark else "#ffffff"};
        letter-spacing: 0.3px;
    }}
    .price-text {{
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        gap: 8px;
        padding-top: 10px;
        border-top: 1px dashed {border_color};
        font-size: 0.8rem;
        color: {subtext_color};
    }}
    .price-text b {{
        font-size: 1.1rem;
        font-weight: 800;
        color: {price_green} !important;
        font-variant-numeric: tabular-nums;
        letter-spacing: -0.01em;
    }}

    /* ---------- BOTÓN COMPARAR PRECIOS (unido a la tarjeta) ---------- */
    div[class*="st-key-btn_compare_"] {{
        margin-top: -1rem !important;
    }}
    div[class*="st-key-btn_compare_"] div.stButton > button {{
        background-color: {accent} !important;
        color: #ffffff !important;
        border: 1px solid {accent} !important;
        border-radius: 0 0 16px 16px !important;
        min-height: 46px !important;
        box-shadow: none !important;
        width: 100% !important;
    }}
    div[class*="st-key-btn_compare_"] div.stButton > button p {{
        color: #ffffff !important;
        font-weight: 700 !important;
    }}
    div[class*="st-key-btn_compare_"] div.stButton > button:hover {{
        background-color: {accent_hover} !important;
        border-color: {accent_hover} !important;
        box-shadow: 0 8px 18px rgba(216, 55, 55, 0.28) !important;
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

    @media (prefers-reduced-motion: reduce) {{
        .star-minimal-ruby, .star-minimal-gold, .star-minimal-silver,
        .radar-title-text .radar-title-mark {{ animation: none !important; }}
    }}

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
        div[data-testid="stColumn"]:has(a[data-testid="stPageLink-NavLink"]) {{
            flex: 1 1 calc(50% - 4px) !important;
            width: calc(50% - 4px) !important;
        }}
        a[data-testid="stPageLink-NavLink"] {{
            justify-content: flex-start !important;
            padding-left: 2.2rem !important;
        }}
        a[data-testid="stPageLink-NavLink"] p,
        a[data-testid="stPageLink-NavLink"] span {{
            font-size: 0.8rem !important;
            white-space: normal !important;
            line-height: 1.15 !important;
        }}
        a[data-testid="stPageLink-NavLink"]::before {{ left: 11px !important; }}
        .brand-logo-text {{ font-size: 1.35rem !important; }}
        .info-tooltip-box {{ left: -230px; width: 280px; }}
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
st.markdown(f"""
    <style>
    div[class*="st-key-pcard_hype_"] {{ --heart-top: 106px; --heart-right: 26px; }}
    div[class*="st-key-pcard_hype_"]:hover .hype-card {{ border-color: {gold}; }}
    </style>
""", unsafe_allow_html=True)

st.markdown(f"""
    <style>
    .hype-meta {{
        font-size: 0.86rem;
        color: {subtext_color};
        margin: 2px 0 6px 0;
    }}
    .hype-meta b {{ color: {text_color}; }}
    .hype-meta-warn {{
        background: {gold_soft};
        border: 1px solid {border_color};
        border-radius: 12px;
        padding: 10px 14px;
        color: {text_color};
    }}
    .img-wrapper img.hype-thumb {{
        width: 100%;
        height: 100%;
        max-width: 100%;
        max-height: 100%;
        object-fit: cover;
        filter: none;
    }}
    .chile-badge-new .chile-dot {{ background: {accent}; }}
    .price-text b.hype-noprice {{
        color: {subtext_color} !important;
        font-size: 0.86rem !important;
        font-weight: 700 !important;
        white-space: nowrap;
    }}
    a.hype-card-link, a.hype-card-link:hover, a.hype-card-link:visited {{
        text-decoration: none !important;
        color: inherit !important;
        display: block;
    }}
    a.hype-card-link:hover .hype-card {{ border-color: {gold}; }}
    div[class*="st-key-ytbtn_"] {{ margin-top: -1rem !important; }}
    div[class*="st-key-ytbtn_"] a {{
        background-color: {accent} !important;
        border: 1px solid {accent} !important;
        color: #ffffff !important;
        border-radius: 0 0 16px 16px !important;
        min-height: 46px !important;
        box-shadow: none !important;
    }}
    div[class*="st-key-ytbtn_"] a p, div[class*="st-key-ytbtn_"] a span {{ color: #ffffff !important; font-weight: 700 !important; }}
    div[class*="st-key-ytbtn_"] a:hover {{ background-color: {accent_hover} !important; border-color: {accent_hover} !important; }}
    </style>
""", unsafe_allow_html=True)

# 4. ENCABEZADO SUPERIOR: LOGO, BOTÓN "INGRESAR" / PERFIL Y SWITCH DE TEMA
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
            st.write(f"**Conectado como:**")
            st.write(st.session_state['user_info'].get('email', ''))
            st.markdown("<div style='margin-top: 8px;'></div>", unsafe_allow_html=True)
            
            # ACOPLE DIRECTO A LA PÁGINA DE PERFIL CON DIBUJO VECTORIAL SVG Y ESTILO LIMPIO (SIN ROJO)
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
    st.page_link("pages/remates.py", label="Remates & Flash", use_container_width=True)

# 5. SECCIÓN DEL TÍTULO Y NAVEGACIÓN
st.markdown("<div style='margin-top: 34px;'></div>", unsafe_allow_html=True)
col_header_title, col_back_btn = st.columns([3.4, 1], vertical_alignment="center")

with col_header_title:
    title_html = """
    <div class="radar-head">
        <div class="radar-title-container">
            <div class="radar-title-text">Radar del Hype<span class="radar-title-mark"></span></div>
            <div class="info-icon-container">
                <div class="info-btn-badge">i</div>
                <div class="info-tooltip-box">
                    <div class="info-tooltip-title">¿Qué es el Radar del Hype?</div>
                    Es nuestro sistema inteligente que detecta qué fragancias se están volviendo virales en tiempo real analizando menciones y reproducciones en <b>YouTube</b>. Una herramienta clave para <b>revendedores, influencers y entusiastas</b> que buscan adelantarse a las tendencias del mercado.
                </div>
            </div>
        </div>
        <div class="radar-subtitle">Las fragancias más virales del momento, ordenadas por su Hype Score.</div>
    </div>
    """
    st.markdown(clean_html(title_html), unsafe_allow_html=True)

with col_back_btn:
    st.page_link("app.py", label="Volver al catálogo")

st.markdown("<div style='margin-top: 14px;'></div>", unsafe_allow_html=True)

# =============================================================================
# BLOQUE 4: FILTRADO TEMPORAL Y FUENTE DE INTELIGENCIA DE TENDENCIAS
# -----------------------------------------------------------------------------
# ¿QUÉ HACE ESTE BLOQUE?
# 1. Permite filtrar el radar de tendencias por períodos temporales:
#    - "Este Mes", "Hoy / Día", "Esta Semana", "Este Año", "Año Pasado".
# 2. Especifica la fuente de analítica social (YouTube / TikTok / Instagram):
#    - Monitorea volumen de reseñas, menciones y reproducciones totales de videos.
# =============================================================================
col_title, col_fecha, col_red = st.columns([0.7, 1.2, 6.1], gap="small", vertical_alignment="center")

with col_title:
    st.markdown("<div class='filter-label-text'>Período:</div>", unsafe_allow_html=True)

with col_fecha:
    opciones_fecha = ["Este Mes", "Hoy / Día", "Esta Semana", "Este Año", "Año Pasado"]
    with st.popover(f"{st.session_state.selected_month}", use_container_width=False):
        for opt in opciones_fecha:
            etiqueta_opt = f"✓  {opt}" if opt == st.session_state.selected_month else opt
            if st.button(etiqueta_opt, key=f"btn_m_{opt}", use_container_width=True):
                st.session_state.selected_month = opt
                st.rerun()

with col_red:
    social_select_html = """
    <div class="social-select-box">
        <span class="social-label">Red social analizada:</span>
        <button class="yt-chip-btn">
            <svg width="16" height="12" viewBox="0 0 26 20" fill="none" aria-hidden="true">
                <rect x="1" y="1" width="24" height="18" rx="5" fill="#d83737" />
                <polygon points="10,5 18,10 10,15" fill="#ffffff" />
            </svg>
            <span>YouTube</span>
        </button>
        <span class="social-desc">Videos en español de Latinoamérica: visitas, videos nuevos, canales y velocidad de crecimiento.</span>
    </div>
    """
    st.markdown(clean_html(social_select_html), unsafe_allow_html=True)

st.markdown("<div class='pt-divider'></div>", unsafe_allow_html=True)


# =============================================================================
# BLOQUE 5: INSIGNIAS VISUALES DE RANKING (ANIMACIONES SVG RUBÍ, ORO Y PLATA)
# -----------------------------------------------------------------------------
# ¿QUÉ HACE ESTE BLOQUE?
# Genera estrellas vectoriales con animaciones sutiles de resplandor (CSS Keyframes):
# - Estrella Rubí (#1): Para el perfume líder absoluto de la temporada (Bleu de Chanel).
# - Estrella Dorada (#2): Segundo lugar de alto impacto (YSL Libre).
# - Estrella Plateada (#3): Tercer lugar destacado (Dior Sauvage).
# =============================================================================
star_ruby_svg = """
<div class="star-minimal-ruby">
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
        <defs>
            <linearGradient id="minRuby" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#ff4d5a"/>
                <stop offset="100%" stop-color="#a81722"/>
            </linearGradient>
        </defs>
        <path d="M12 2L14.4 9.6L22 12L14.4 14.4L12 22L9.6 14.4L2 12L9.6 9.6L12 2Z" fill="url(#minRuby)" stroke="#ff8591" stroke-width="0.8"/>
        <circle cx="12" cy="12" r="1.5" fill="#ffffff" opacity="0.9"/>
    </svg>
</div>
"""

star_gold_svg = """
<div class="star-minimal-gold">
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
        <defs>
            <linearGradient id="minGold" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#f3e5ab"/>
                <stop offset="50%" stop-color="#d4af37"/>
                <stop offset="100%" stop-color="#aa7c11"/>
            </linearGradient>
        </defs>
        <path d="M12 2L14.4 9.6L22 12L14.4 14.4L12 22L9.6 14.4L2 12L9.6 9.6L12 2Z" fill="url(#minGold)" stroke="#fff3a8" stroke-width="0.8"/>
        <circle cx="12" cy="12" r="1.5" fill="#ffffff" opacity="0.9"/>
    </svg>
</div>
"""

star_silver_svg = """
<div class="star-minimal-silver">
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
        <defs>
            <linearGradient id="minSilver" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#ffffff"/>
                <stop offset="100%" stop-color="#8a99ad"/>
            </linearGradient>
        </defs>
        <path d="M12 2L14.4 9.6L22 12L14.4 14.4L12 22L9.6 14.4L2 12L9.6 9.6L12 2Z" fill="url(#minSilver)" stroke="#e2e8f0" stroke-width="0.8"/>
        <circle cx="12" cy="12" r="1.5" fill="#ffffff" opacity="0.9"/>
    </svg>
</div>
"""


# =============================================================================
# BLOQUE 6: MODELO DE DATOS DE HYPE Y RESÚMENES SEMÁNTICOS CON IA
# -----------------------------------------------------------------------------
# ¿CÓMO SE CALCULA EL HYPE SCORE?
# Pondera:
# 1. Volumen de contenido (videos y reseñas creadas en el mes).
# 2. Impresiones e interacciones totales (vistas estimadas).
# 3. Interés de búsqueda en Chile y tasa de conversación en redes.
# Incluye un extracto analítico generado mediante procesamiento de lenguaje natural
# (`ai_text`) que explica al usuario por qué la fragancia es viral (ej. aroma versátil,
# dupe accesible de nicho, o tendencia gourmand de temporada).
# =============================================================================
hype_data = [
    {
        "perfume_id": 1, "rank": "#1", "star": star_ruby_svg, "name": "Bleu de Chanel", "score": "95%", "year": "2010", "price": "$145.990 CLP",
        "img": get_image_src("APP/assets/perfumes/bleu_de_chanel.jpg"),
        "stats": "↗ 75 videos y 1.5M<br>visitas este mes",
        "ai_text": "Tendencia por su versatilidad fresca y estética de 'lujo silencioso' en YouTube."
    },
    {
        "perfume_id": 2, "rank": "#2", "star": star_gold_svg, "name": "YSL Libre EDP", "score": "90%", "year": "2019", "price": "$129.990 CLP",
        "img": get_image_src("APP/assets/perfumes/ysl_libre.jpg"),
        "stats": "↗ 60 videos y 1.0M<br>visitas este mes",
        "ai_text": "Gran popularidad por su elegante nota de lavanda floral para uso diario o de noche."
    },
    {
        "perfume_id": 3, "rank": "#3", "star": star_silver_svg, "name": "Dior Sauvage", "score": "88%", "year": "2015", "price": "$149.990 CLP",
        "img": get_image_src("APP/assets/perfumes/dior_sauvage.jpg"),
        "stats": "↗ 55 videos y 900k<br>visitas este mes",
        "ai_text": "Dominio constante en redes por su proyección masiva y versatilidad inigualable."
    },
    {
        "perfume_id": 6, "rank": "#4", "star": "", "name": "Baccarat Rouge 540", "score": "86%", "year": "2015", "price": "$310.000 CLP",
        "img": get_image_src("APP/assets/perfumes/baccarat_rouge.jpg"),
        "stats": "↗ 48 videos y 820k<br>visitas este mes",
        "ai_text": "El aroma nicho dulzón y ambarado más clonado e influyente de YouTube."
    },
    {
        "perfume_id": 4, "rank": "#5", "star": "", "name": "Club de Nuit Intense", "score": "84%", "year": "2015", "price": "$39.990 CLP",
        "img": get_image_src("APP/assets/perfumes/club_de_nuit.jpg"),
        "stats": "↗ 42 videos y 750k<br>visitas este mes",
        "ai_text": "Rey indiscutido de las fragancias árabes relación precio-calidad."
    },
    {
        "perfume_id": 5, "rank": "#6", "star": "", "name": "Khamrah Lattafa", "score": "82%", "year": "2022", "price": "$34.990 CLP",
        "img": get_image_src("APP/assets/perfumes/lattafa_khamrah.jpg"),
        "stats": "↗ 38 videos y 680k<br>visitas este mes",
        "ai_text": "Tendencia invernal gourmand con notas de licor de canela y praliné."
    }
]

# 8. RANKING REAL DESDE YOUTUBE (con respaldo de ejemplo si no hay clave o falla la conexión)
cat_map = get_cached_catalogo_map()
periodo_actual = st.session_state.selected_month
periodo_txt = PERIODOS.get(periodo_actual, PERIODOS["Este Mes"])["texto"]
with st.spinner("Analizando los videos de perfumes en YouTube..."):
    ranking = obtener_ranking_hype(periodo_actual, list(cat_map.values()), limite=12)

estrellas = [star_ruby_svg, star_gold_svg, star_silver_svg]
if ranking["ok"]:
    hype_items = []
    for pos, f in enumerate(ranking["items"]):
        p_cat = cat_map.get(f["perfume_id"]) if f["perfume_id"] else None
        if p_cat and (p_cat.get("mejor_precio") or p_cat.get("precio_referencia")):
            p_disp = p_cat.get("mejor_precio") or p_cat.get("precio_referencia")
            price_txt = f"${int(p_disp):,.0f} CLP".replace(",", ".")
        else:
            price_txt = "Sin ofertas"
        img_cat = get_image_src(p_cat.get("imagen_url")) if (p_cat and p_cat.get("imagen_url")) else ""
        hype_items.append({
            "perfume_id": f["perfume_id"],
            "en_catalogo": f["en_catalogo"],
            "rank": f"#{pos + 1}",
            "star": estrellas[pos] if pos < 3 else "",
            "name": f["nombre"],
            "score": f"{f['score']}%",
            "year": f"{f['videos']} videos",
            "price": price_txt,
            "img": img_cat or f["miniatura"],
            "es_miniatura": not img_cat,
            "stats": f"↗ {f['videos']} videos y {formatear_numero(f['visitas'])}<br>visitas {periodo_txt}",
            "ai_text": f["insight"],
            "url": f["top_url"],
        })
    hora_txt = ranking["actualizado"].astimezone(timezone(timedelta(hours=-3))).strftime("%d/%m %H:%M") if ranking.get("actualizado") else ""
    st.markdown(
        f"<div class='hype-meta'>Basado en <b>{ranking['videos_analizados']}</b> videos de perfumes en español publicados {periodo_txt}. "
        f"Actualizado el {hora_txt} (hora de Chile).</div>",
        unsafe_allow_html=True,
    )
    if ranking.get("mensaje"):
        st.caption(ranking["mensaje"])
else:
    # Respaldo: datos de ejemplo (la página nunca queda vacía)
    hype_items = [dict(d, en_catalogo=True, es_miniatura=False, url="") for d in hype_data]
    if ranking.get("mensaje"):
        st.markdown(f"<div class='hype-meta hype-meta-warn'>{escape_html(ranking['mensaje'])}</div>", unsafe_allow_html=True)

# 9. RENDERIZADO DE TARJETAS EN REJILLA CON VINCULACIÓN DINÁMICA AL CATÁLOGO
score_track = "rgba(255, 255, 255, 0.08)" if is_dark else "#efebe6"
cols_per_row = 3
for row in range(0, len(hype_items), cols_per_row):
    cols = st.columns(cols_per_row, gap="medium")
    for i in range(cols_per_row):
        idx = row + i
        if idx < len(hype_items):
            data = hype_items[idx]
            en_catalogo = bool(data.get("en_catalogo")) and data.get("perfume_id") is not None
            perf_info = cat_map.get(data['perfume_id']) if en_catalogo else None
            if en_catalogo and not perf_info:
                target_words = [w.lower() for w in data['name'].split() if len(w) > 3]
                for cand in cat_map.values():
                    c_full = f"{cand.get('marca', '')} {cand.get('nombre', '')}".lower()
                    if target_words and all(w in c_full for w in target_words[:2]):
                        perf_info = cand
                        break

            resolved_pid = perf_info['id'] if perf_info else data['perfume_id']
            if perf_info and (perf_info.get('mejor_precio') or perf_info.get('precio_referencia')):
                p_disp = perf_info.get('mejor_precio') or perf_info.get('precio_referencia')
                price_disp = f"${int(p_disp):,.0f} CLP".replace(",", ".")
            else:
                price_disp = escape_html(data['price'])

            name_safe = escape_html(data['name'])
            ai_safe = escape_html(data['ai_text'])
            img_safe = escape_html(data['img'])
            img_class = "hype-thumb" if data.get("es_miniatura") else ""

            # Porcentaje del anillo del Hype Score (solo visual)
            try:
                score_pct = max(0, min(100, int(str(data['score']).strip().rstrip('%'))))
            except ValueError:
                score_pct = 0
            score_deg = round(score_pct * 3.6, 1)

            if en_catalogo:
                badge_html = """
                        <div class="chile-badge">
                            <span class="chile-dot"></span>
                            <div>Disponible<br>en Chile</div>
                        </div>"""
                precio_label = "Mejor precio hoy"
            else:
                badge_html = """
                        <div class="chile-badge chile-badge-new">
                            <span class="chile-dot"></span>
                            <div>Nuevo en<br>tendencia</div>
                        </div>"""
                precio_label = "Aún no en tiendas auditadas"

            with cols[i]:
                html_card = f"""
                <div class="hype-card">
                    <div class="hype-top">
                        <div class="rank-badge">{data['star']}{data['rank']}</div>
                        <div class="score-circle" style="background: conic-gradient({accent} {score_deg}deg, {score_track} 0deg);" title="Hype Score">
                            <div class="score-inner">
                                <div class="score-value">{data['score']}</div>
                                <div class="score-title">HYPE</div>
                            </div>
                        </div>
                    </div>
                    <div class="img-wrapper">
                        <img src="{img_safe}" alt="{name_safe}" class="{img_class}" loading="lazy" onerror="this.onerror=null;this.src='{DEFAULT_PERFUME_IMAGE}';">
                        <div class="year-badge">{data['year']}</div>
                    </div>
                    <div class="perfume-title" title="{name_safe}">{name_safe}</div>
                    <div class="stats-row">
                        <div class="stats-text">{data['stats']}</div>{badge_html}
                    </div>
                    <div class="ai-box">
                        <div class="ai-icon">AI</div>
                        <div>{ai_safe}</div>
                    </div>
                    <div class="price-text"><div>{precio_label}</div><b class="{'' if en_catalogo else 'hype-noprice'}">{price_disp}</b></div>
                </div>
                """
                if en_catalogo:
                    # Toda la tarjeta abre el perfume; el corazón lo guarda en favoritos
                    with st.container(key=f"pcard_hype_{idx}_{resolved_pid}"):
                        st.markdown(clean_html(html_card), unsafe_allow_html=True)
                        boton_abrir_perfume(resolved_pid, f"hype{idx}")
                        boton_corazon(resolved_pid, f"hype{idx}", data['name'])
                    if st.button("Comparar Precios", key=f"btn_compare_{idx}", use_container_width=True):
                        st.session_state['selected_perfume'] = resolved_pid
                        st.switch_page("pages/compararprecios.py")
                else:
                    # Perfume viral que aún no está en el catálogo: la tarjeta abre su video más visto
                    url_safe = escape_html(data.get("url") or "#")
                    st.markdown(
                        clean_html(f'<div class="hype-link-wrap"><a class="hype-card-link" href="{url_safe}" target="_blank" rel="noopener noreferrer">{html_card}</a></div>'),
                        unsafe_allow_html=True,
                    )
                    with st.container(key=f"ytbtn_{idx}"):
                        st.link_button("Ver el video más visto ↗", data.get("url") or "https://www.youtube.com", use_container_width=True)

# PIE DE PÁGINA
st.markdown(clean_html("""
    <div class="pt-footer">
        <div class="pt-footer-mark">Perfume<strong>Trending</strong></div>
        <div class="pt-footer-copy">© 2026 Perfume Trending. Todos los derechos reservados.</div>
    </div>
"""), unsafe_allow_html=True)
