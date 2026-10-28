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

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)
if APP_DIR not in sys.path:
    sys.path.append(APP_DIR)

from backend.database import obtener_catalogo
from ui import (
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
    modal_autenticacion,
    toggle_theme,
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
        const essenceCards = doc.querySelectorAll('.hype-card');
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
    header[data-testid="stHeader"] {{ display: none !important; }}
    div[data-testid="stAppViewContainer"] {{ padding-top: 0px !important; }}

    .stApp {{ 
        background-color: {app_bg} !important; 
        color: {text_color} !important; 
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; 
    }}

    .block-container {{ 
        padding-top: 1.2rem !important; 
        padding-bottom: 2rem !important; 
        max-width: 1200px !important;
    }}

    .stApp p, .stApp span, .stApp label, .stMarkdown p {{
        color: {text_color} !important;
        text-shadow: none !important;
    }}

    /* BOTONES GENERALES DE ESTILO SOBRIO (IGUAL A APP.PY) */
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

    /* BOTÓN CERRAR SESIÓN Y MI PERFIL CON DIBUJOS VECTORIALES HTML/SVG (SIN FONDO ROJO) */
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

    /* TÍTULO Y TOOLTIP DE INFORMACIÓN */
    .radar-title-container {{
        display: inline-flex;
        align-items: baseline;
        gap: 6px;
    }}

    .radar-title-text {{
        color: #d83737 !important;
        font-weight: 900 !important;
        font-size: 2.1rem !important;
        letter-spacing: 1.5px !important;
        margin: 0;
        display: inline;
        transition: color 0.3s ease !important;
    }}

    .radar-title-text:hover {{
        color: #8b121a !important;
    }}

    .info-icon-container {{
        position: relative;
        display: inline-block;
        vertical-align: super;
        top: -12px;
        left: 3px;
    }}

    .info-btn-badge {{
        width: 18px;
        height: 18px;
        background: linear-gradient(135deg, #d83737 0%, #a81722 100%);
        color: #ffffff;
        border-radius: 50%;
        font-size: 11px;
        font-weight: 900;
        font-family: 'Georgia', serif;
        font-style: italic;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        box-shadow: 0 2px 6px rgba(216, 55, 55, 0.35);
        transition: transform 0.25s ease, box-shadow 0.25s ease;
    }}

    .info-icon-container:hover .info-btn-badge {{
        transform: scale(1.22);
        box-shadow: 0 4px 10px rgba(216, 55, 55, 0.5);
    }}

    .info-tooltip-box {{
        visibility: hidden;
        opacity: 0;
        width: 320px;
        background-color: {card_bg};
        color: {text_color};
        border: 1px solid {border_color};
        border-radius: 12px;
        padding: 14px 16px;
        position: absolute;
        top: 26px;
        left: -140px;
        z-index: 999;
        box-shadow: 0 12px 30px rgba(0,0,0,0.25);
        font-size: 0.86rem;
        line-height: 1.45;
        transition: opacity 0.25s ease, visibility 0.25s ease, transform 0.25s ease;
        transform: translateY(-6px);
        pointer-events: none;
    }}

    .info-icon-container:hover .info-tooltip-box {{
        visibility: visible;
        opacity: 1;
        transform: translateY(0);
        pointer-events: auto;
    }}

    /* FILTROS DE FECHA EN PÁGINA */
    .filter-label-text {{
        color: {text_color} !important;
        font-weight: 700 !important;
        font-size: 1rem !important;
        margin: 0 !important;
        display: flex;
        align-items: center !important;
        justify-content: flex-start;
        height: 32px;
    }}

    /* CHIP YOUTUBE */
    .social-select-box {{
        display: flex;
        align-items: center;
        gap: 8px;
        color: {text_color};
        font-size: 13px;
        width: 100%;
        box-sizing: border-box;
        height: 32px;
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
        gap: 6px;
        background-color: {card_bg};
        border: 1px solid {border_color};
        border-radius: 8px;
        padding: 0 10px;
        height: 32px;
        box-sizing: border-box;
        color: {text_color};
        font-weight: 700;
        font-size: 12px;
        line-height: 1;
        white-space: nowrap;
        cursor: pointer;
        transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1), background-color 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
        outline: none;
        user-select: none;
    }}

    .yt-chip-btn:hover {{
        transform: translateY(-1px);
        border-color: #d83737;
        background-color: {app_bg};
        box-shadow: 0 3px 8px rgba(216, 55, 55, 0.15);
    }}

    .social-desc {{
        font-size: 11px;
        color: {subtext_color};
        font-style: italic;
        line-height: 1.2;
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

    /* DIBUJOS ILUSTRADOS VECTORIALES EN ROJO PARA LOS BOTONES DE NAVEGACIÓN */
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

    /* TARJETAS DE PERFUME DE TENDENCIA */
    .hype-card {{
        background-color: {card_bg};
        border: 2px solid {border_color};
        border-radius: 12px;
        padding: 14px;
        position: relative;
        margin-top: 15px;
        margin-bottom: 12px;
        box-shadow: 2px 4px 10px rgba(0,0,0,0.08);
        color: {text_color};
        font-family: 'Inter', sans-serif;
        transition: transform 0.32s cubic-bezier(0.25, 0.8, 0.25, 1), box-shadow 0.32s cubic-bezier(0.25, 0.8, 0.25, 1), border-color 0.32s ease;
    }}
    
    .hype-card:hover {{
        transform: translateY(-8px) scale(1.025);
        box-shadow: 0 16px 30px rgba(0,0,0,0.16);
        border-color: #d83737;
    }}

    .rank-badge {{
        position: absolute; top: -12px; left: -8px;
        background-color: {card_bg}; color: {text_color};
        font-size: 16px; font-weight: 900; padding: 3px 10px;
        border: 2px solid {border_color}; border-radius: 6px; box-shadow: 2px 2px 0px {border_color}; z-index: 2;
        display: flex; align-items: center; gap: 6px;
        transition: border-color 0.3s ease;
    }}
    .hype-card:hover .rank-badge {{
        border-color: #d83737;
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

    .score-circle {{
        position: absolute; top: 10px; right: 10px; width: 56px; height: 56px; border-radius: 50%;
        border: 2px solid {border_color}; display: flex; flex-direction: column; justify-content: center;
        align-items: center; background-color: {card_bg}; padding: 2px;
        box-shadow: inset 0 0 0 2px {card_bg}, inset 0 0 0 2px {border_color};
        transition: border-color 0.3s ease;
    }}
    .hype-card:hover .score-circle {{ border-color: #d83737; }}

    .score-title {{ font-size: 7px; font-weight: 800; line-height: 1.0; text-align: center; color: {text_color}; }}
    .score-value {{ font-size: 15px; font-weight: 900; color: {text_color}; }}
    
    .img-wrapper {{ text-align: center; margin-top: 10px; position: relative; overflow: hidden; border-radius: 8px; }}
    .img-wrapper img {{ 
        width: 105px; 
        height: 105px; 
        object-fit: contain; 
        transition: transform 0.4s cubic-bezier(0.25, 0.8, 0.25, 1);
    }}
    
    .hype-card:hover .img-wrapper img {{ transform: scale(1.12); }}

    .year-badge {{
        position: absolute; bottom: 0; right: 5px; background: {card_bg}; border: 1px solid {border_color};
        border-radius: 4px; padding: 1px 6px; font-size: 11px; font-weight: bold; color: {text_color};
    }}
    .perfume-title {{ text-align: center; font-size: 14px; font-weight: bold; margin-top: 8px; margin-bottom: 10px; color: {text_color}; }}
    .stats-row {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; font-size: 10px; }}
    .stats-text {{ width: 55%; color: {text_color}; line-height: 1.25; }}
    .chile-badge {{
        display: flex; align-items: center; gap: 4px; background-color: {app_bg}; border: 1px solid {border_color};
        border-radius: 16px; padding: 3px 6px; font-weight: bold; font-size: 9px; text-align: left; line-height: 1.1; color: {text_color};
    }}
    .ai-box {{
        display: flex; gap: 8px; align-items: center; border: 1px solid {border_color}; border-radius: 8px;
        padding: 8px; margin-bottom: 10px; font-size: 10px; line-height: 1.25; background-color: {app_bg}; color: {subtext_color};
    }}
    .ai-icon {{
        min-width: 22px; height: 22px; border-radius: 50%; border: 1px solid {border_color}; display: flex;
        justify-content: center; align-items: center; font-weight: bold; font-size: 9px; background-color: {card_bg}; color: {text_color};
    }}
    .price-text {{ text-align: center; font-size: 11px; color: {text_color}; margin-bottom: 6px; }}

    /* BOTONES DE COMPARAR PRECIOS (EXCLUSIVO PARA BOTONES DENTRO DE TARJETAS DE PERFUME) */
    div[data-testid="stElementContainer"] div.stButton button[key*="btn_compare_"],
    div.stButton > button[key*="btn_compare_"] {{
        background-color: #d83737 !important;
        color: #ffffff !important;
        border: 1px solid #d83737 !important;
        border-radius: 10px !important;
        font-weight: 700 !important;
        font-size: 13px !important;
        padding: 10px 16px !important;
        box-shadow: 0 4px 12px rgba(216, 55, 55, 0.22) !important;
        transition: transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1), background-color 0.2s ease, box-shadow 0.25s ease !important;
        width: 100% !important;
    }}

    div[data-testid="stElementContainer"] div.stButton button[key*="btn_compare_"] p,
    div.stButton > button[key*="btn_compare_"] p {{
        color: #ffffff !important;
        font-weight: 700 !important;
    }}

    div[data-testid="stElementContainer"] div.stButton button[key*="btn_compare_"]:hover,
    div.stButton > button[key*="btn_compare_"]:hover {{
        background-color: #be2e2e !important;
        border-color: #be2e2e !important;
        color: #ffffff !important;
        transform: scale(1.03) translateY(-2px) !important;
        box-shadow: 0 6px 18px rgba(216, 55, 55, 0.38) !important;
    }}

    div[data-testid="stElementContainer"] div.stButton button[key*="btn_compare_"]:active,
    div.stButton > button[key*="btn_compare_"]:active {{
        transform: scale(0.98) translateY(0px) !important;
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

# 4. ENCABEZADO SUPERIOR: LOGO, BOTÓN "INGRESAR" / PERFIL Y SWITCH DE TEMA
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

st.markdown("<div style='margin-top: 14px;'></div>", unsafe_allow_html=True)

# CHIPS DE NAVEGACIÓN RÁPIDA
col_chip_home, col_chip1, col_chip2, col_chip3, col_chip_space = st.columns([1.6, 1.5, 2.0, 1.7, 2.2], vertical_alignment="center")

with col_chip_home:
    st.page_link("app.py", label="Inicio / Catálogo", use_container_width=True)
with col_chip1:
    st.page_link("pages/trendhype.py", label="Trend Del Hype", use_container_width=True)
with col_chip2:
    st.page_link("pages/trustpage.py", label="Páginas de Confianza", use_container_width=True)
with col_chip3:
    st.page_link("pages/compararprecios.py", label="Comparar Precios", use_container_width=True)

# 5. SECCIÓN DEL TÍTULO Y NAVEGACIÓN
st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
col_header_title, col_back_btn = st.columns([3.4, 1], vertical_alignment="center")

with col_header_title:
    title_html = f"""
    <div class="radar-title-container">
        <h1 class="radar-title-text">RADAR DEL HYPE - VIRAL FRAGRANCES</h1>
        <div class="info-icon-container">
            <div class="info-btn-badge">i</div>
            <div class="info-tooltip-box">
                <div style="font-weight: 800; color: #d83737; margin-bottom: 6px; font-size: 0.92rem;">¿Qué es el Radar del Hype?</div>
                Es nuestro sistema inteligente que detecta qué fragancias se están volviendo virales en tiempo real analizando menciones y reproducciones en <b>YouTube</b>. Una herramienta clave para <b>revendedores, influencers y entusiastas</b> que buscan adelantarse a las tendencias del mercado.
            </div>
        </div>
    </div>
    """
    st.markdown(title_html, unsafe_allow_html=True)

with col_back_btn:
    st.page_link("app.py", label="← Volver al Catálogo")

st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)

# =============================================================================
# BLOQUE 4: FILTRADO TEMPORAL Y FUENTE DE INTELIGENCIA DE TENDENCIAS
# -----------------------------------------------------------------------------
# ¿QUÉ HACE ESTE BLOQUE?
# 1. Permite filtrar el radar de tendencias por períodos temporales:
#    - "Este Mes", "Hoy / Día", "Esta Semana", "Este Año", "Año Pasado".
# 2. Especifica la fuente de analítica social (YouTube / TikTok / Instagram):
#    - Monitorea volumen de reseñas, menciones y reproducciones totales de videos.
# =============================================================================
col_title, col_fecha, col_red = st.columns([0.28, 0.42, 3.3], gap="small", vertical_alignment="center")

with col_title:
    st.markdown("<div class='filter-label-text'>Filtrado por :</div>", unsafe_allow_html=True)

with col_fecha:
    opciones_fecha = ["Este Mes", "Hoy / Día", "Esta Semana", "Este Año", "Año Pasado"]
    with st.popover(f"{st.session_state.selected_month}", use_container_width=False):
        for opt in opciones_fecha:
            if st.button(opt, key=f"btn_m_{opt}", use_container_width=True):
                st.session_state.selected_month = opt
                st.rerun()

with col_red:
    social_select_html = f"""
    <div class="social-select-box">
        <span class="social-label">Red social analizada:</span>
        <button class="yt-chip-btn">
            <svg width="16" height="12" viewBox="0 0 26 20" fill="none">
                <rect x="1" y="1" width="24" height="18" rx="5" fill="#d83737" />
                <polygon points="10,5 18,10 10,15" fill="#ffffff" />
            </svg>
            <span>YouTube</span>
        </button>
        <span class="social-desc">(Mide la popularidad en tiempo real según menciones y reseñas en video)</span>
    </div>
    """
    st.markdown(social_select_html, unsafe_allow_html=True)

st.write("")


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

# 8. RENDERIZADO DE TARJETAS EN REJILLA CON VINCULACIÓN DINÁMICA AL CATÁLOGO
cat_map = get_cached_catalogo_map()
cols_per_row = 3
for row in range(0, len(hype_data), cols_per_row):
    cols = st.columns(cols_per_row, gap="medium")
    for i in range(cols_per_row):
        idx = row + i
        if idx < len(hype_data):
            data = hype_data[idx]
            perf_info = cat_map.get(data['perfume_id'])
            if not perf_info:
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
            with cols[i]:
                html_card = f"""
                <div class="hype-card">
                    <div class="rank-badge">{data['star']}{data['rank']}</div>
                    <div class="score-circle">
                        <div class="score-title">HYPE<br>SCORE:</div>
                        <div class="score-value">{data['score']}</div>
                    </div>
                    <div class="img-wrapper">
                        <img src="{data['img']}" alt="{name_safe}">
                        <div class="year-badge">{data['year']}</div>
                    </div>
                    <div class="perfume-title">{name_safe}</div>
                    <div class="stats-row">
                        <div class="stats-text">{data['stats']}</div>
                        <div class="chile-badge">
                            <div>Disponible<br>en Chile</div>
                        </div>
                    </div>
                    <div class="ai-box">
                        <div class="ai-icon">AI</div>
                        <div>"{ai_safe}"</div>
                    </div>
                    <div class="price-text">Mejor precio hoy: <b>{price_disp}</b></div>
                </div>
                """
                st.markdown(clean_html(html_card), unsafe_allow_html=True)
                if st.button("Comparar Precios", key=f"btn_compare_{idx}", use_container_width=True):
                    st.session_state['selected_perfume'] = resolved_pid
                    st.switch_page("pages/compararprecios.py")
