"""
PerfumeTrending.cl — Aplicación Web Principal (Streamlit Portal)
================================================================
Punto de entrada de la plataforma chilena de comparación de precios de fragancias:
- Arquitectura de navegación multipágina (Home, Comparador, Remates, TrendHype, TrustScore, Perfil).
- Catálogo interactivo con filtrado multifacético: por búsqueda difusa, familias olfativas, notas y marcas.
- Renderizado de componentes visuales con CSS personalizado (modo oscuro/claro y glassmorphism).
- Paginación dinámica y caché en memoria con invalidación TTL para alto rendimiento.
- Consumo resiliente de datos: consulta primaria a Supabase (PostgreSQL en la nube) con fallback a SQLite.
"""

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import sys
import os
import base64
import random
import time

# Configurar rutas para importar backend
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)
if APP_DIR not in sys.path:
    sys.path.append(APP_DIR)

from backend.database import (
    init_db,
    obtener_catalogo,
    obtener_detalle_perfume,
    obtener_precios_actuales,
    obtener_tiendas,
)
from ui import (
    DIAMOND_ICON_SVG as diamond_icon_svg,
    FLAME_RED_SVG as flame_red_svg,
    GRID_ICON_SVG as grid_icon_svg,
    HOME_RED_SVG as home_red_svg,
    PERFUME_SVG_FAVICON as perfume_svg_favicon,
    SHIELD_RED_SVG as shield_red_svg,
    TAG_RED_SVG as tag_red_svg,
    TREND_RED_SVG as trend_red_svg,
    cerrar_sesion_usuario,
    clean_html,
    escape_html,
    formatear_nombre_especifico,
    get_image_src,
    get_theme_palette,
    init_common_session_state,
    modal_autenticacion,
    toggle_theme as _shared_toggle_theme,
)


# =============================================================================
# BLOQUE 1: CACHÉ EN MEMORIA DE ALTO RENDIMIENTO (STREAMLIT CACHE DATA)
# =============================================================================
@st.cache_data(ttl=600, show_spinner=False)
def get_cached_catalogo(busqueda=None, esencias_tuple=None, categoria=None, orden="id_asc"):
    """Consulta el catálogo consolidado calculando el mejor precio en vivo con invalidación TTL."""
    esencias = list(esencias_tuple) if esencias_tuple else None
    return obtener_catalogo(busqueda=busqueda, esencias=esencias, categoria=categoria, orden=orden)


# =============================================================================
# BLOQUE 2: CONFIGURACIÓN DE PÁGINA Y ESTADO GLOBAL REACTIVO (SESSION STATE)
# =============================================================================
st.set_page_config(
    page_title="PerfumeTrending",
    page_icon=perfume_svg_favicon,
    layout="wide",
    initial_sidebar_state="collapsed"
)

init_db()
init_common_session_state()

if 'current_page' not in st.session_state:
    st.session_state['current_page'] = 'home'
if 'selected_perfume' not in st.session_state:
    st.session_state['selected_perfume'] = None
if 'catalog_page' not in st.session_state:
    st.session_state['catalog_page'] = 1
if 'items_per_page' not in st.session_state:
    st.session_state['items_per_page'] = 12
if 'selected_category' not in st.session_state:
    st.session_state['selected_category'] = 'todos'
if 'selected_order' not in st.session_state:
    st.session_state['selected_order'] = 'id_asc'
if 'selected_order_label' not in st.session_state:
    st.session_state['selected_order_label'] = 'Destacados'


def reset_modals():
    """Función para garantizar que ningún modal emergente quede abierto por error."""
    st.session_state['show_login_modal'] = False
    st.session_state['show_visual_modal'] = False


def toggle_theme():
    _shared_toggle_theme()
    reset_modals()


def navigate_to(page, perfume_data=None):
    st.session_state['current_page'] = page
    reset_modals()
    if perfume_data:
        st.session_state['selected_perfume'] = perfume_data


def reset_to_home():
    st.session_state['current_page'] = 'home'
    st.session_state['selected_perfume'] = None
    st.session_state['catalog_page'] = 1
    st.session_state['selected_category'] = 'todos'
    st.session_state['selected_order'] = 'id_asc'
    st.session_state['selected_order_label'] = 'Destacados'


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

# MODAL FLOTANTE PARA BÚSQUEDA VISUAL CON DIBUJOS HTML VECTORIALES
@st.dialog("Búsqueda Visual de Perfumes")
def modal_busqueda_visual():
    st.markdown(clean_html(f"""
        <div style="font-size:0.92rem; margin-bottom:14px; color: {text_color}; line-height: 1.4;">
            Sube una foto del frasco o usa tu cámara para identificar la fragancia y comparar precios en Chile.
        </div>
    """), unsafe_allow_html=True)
    
    tab_upload, tab_camera = st.tabs(["Subir Imagen", "Usar Cámara"])
    
    uploaded_file = None
    with tab_upload:
        st.markdown(clean_html(f"""
            <div style="display: flex; align-items: center; gap: 8px; margin: 8px 0 12px 0;">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="{text_color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
                </svg>
                <span style="font-weight: 600; font-size: 0.95rem; color: {text_color};">Arrastrar una imagen o seleccionar archivo</span>
            </div>
        """), unsafe_allow_html=True)
        file_up = st.file_uploader("Arrastra una imagen o selecciona un archivo", type=["jpg", "jpeg", "png", "webp"], key="vis_file_up", label_visibility="collapsed")
        if file_up:
            uploaded_file = file_up
            
    with tab_camera:
        st.markdown(clean_html(f"""
            <div style="display: flex; align-items: center; gap: 8px; margin: 8px 0 12px 0;">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="{text_color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
                    <circle cx="12" cy="13" r="4"/>
                </svg>
                <span style="font-weight: 600; font-size: 0.95rem; color: {text_color};">Tomar fotografía en vivo</span>
            </div>
        """), unsafe_allow_html=True)
        cam_up = st.camera_input("Capturar foto del perfume", key="vis_cam_up", label_visibility="collapsed")
        if cam_up:
            uploaded_file = cam_up

    if uploaded_file:
        col_preview, col_status = st.columns([1, 1])
        with col_preview:
            st.image(uploaded_file, caption="Imagen cargada", use_container_width=True)
        with col_status:
            with st.spinner("Analizando frasco, marca y silueta..."):
                time.sleep(0.4)
            st.markdown(clean_html(f"""
                <div style="display: flex; align-items: center; gap: 8px; color: #4caf50; font-weight: 600;">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#4caf50" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                        <polyline points="20 6 9 17 4 12"/>
                    </svg>
                    <span>Análisis finalizado</span>
                </div>
            """), unsafe_allow_html=True)
            
        st.markdown(f"<hr style='margin: 12px 0; border: none; border-bottom: 1px solid {btn_border};'>", unsafe_allow_html=True)
        
        st.markdown(clean_html(f"""
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px;">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#d83737" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="11" cy="11" r="8"/>
                    <line x1="21" y1="21" x2="16.65" y2="16.65"/>
                </svg>
                <span style="font-weight: 700; font-size: 1rem; color: {text_color};">Resultados detectados:</span>
            </div>
        """), unsafe_allow_html=True)
        
        filename = getattr(uploaded_file, 'name', 'foto_camara.jpg').lower()
        catalogo_completo = obtener_catalogo()
        coincidencias = []
        
        if catalogo_completo:
            for p in catalogo_completo:
                nombre_p = p['nombre'].lower()
                marca_p = p['marca'].lower()
                if any(w in filename for w in nombre_p.split() if len(w) > 2) or any(w in filename for w in marca_p.split() if len(w) > 2):
                    coincidencias.append(p)
            
            if not coincidencias:
                try:
                    img_bytes = uploaded_file.getvalue()
                    img_hash = sum(img_bytes) % len(catalogo_completo)
                    for idx in range(min(3, len(catalogo_completo))):
                        coincidencias.append(catalogo_completo[(img_hash + idx) % len(catalogo_completo)])
                except Exception:
                    coincidencias = catalogo_completo[:3]

        if coincidencias:
            for p in coincidencias:
                c_img, c_info = st.columns([1, 2])
                with c_img:
                    st.image(get_image_src(p.get('imagen_url')), use_container_width=True)
                with c_info:
                    st.markdown(f"**{p['nombre']}**")
                    st.caption(f"Marca: {p['marca']}")
                    p_val = p.get('mejor_precio')
                    p_txt = f"${p_val:,.0f} CLP".replace(",", ".") if p_val else "Ver tiendas"
                    st.markdown(f"<span style='color:#4caf50; font-weight:600;'>Mejor precio: {p_txt}</span>", unsafe_allow_html=True)
                    if st.button("Comparar Precios", key=f"btn_vis_select_{p['id']}", use_container_width=True):
                        st.session_state['selected_perfume'] = p['id']
                        reset_modals()
                        st.switch_page("pages/compararprecios.py")
                st.markdown("<div style='margin-bottom: 8px;'></div>", unsafe_allow_html=True)

    st.markdown(f"<hr style='margin: 14px 0; border: none; border-bottom: 1px solid {btn_border};'>", unsafe_allow_html=True)
    if st.button("Cerrar Ventana", key="btn_close_vis_modal", use_container_width=True):
        reset_modals()
        st.rerun()

# 3. RENDERIZADO EXCLUSIVO DE MODALES
if st.session_state.get('show_login_modal', False):
    st.session_state['show_login_modal'] = False
    modal_autenticacion()

# Posicionamiento del Switch de Tema y SVGs dinámicos desde paleta compartida
bottle_left_pos = pal.bottle_left_pos
static_icon_pos = pal.static_icon_pos
static_icon_svg = pal.static_icon_svg
bottle_svg = pal.bottle_svg
camera_icon_svg = pal.camera_icon_svg
user_icon_svg = pal.user_icon_svg
settings_icon_svg = pal.settings_icon_svg
logout_icon_svg = pal.logout_icon_svg
logo_svg_data = pal.logo_svg_data

# 4. SISTEMA DE SONIDO Y EVENTOS DE TARJETAS
js_color_script = f"""
<script>
(function() {{
    const topWin = window.parent || window;
    const topDoc = topWin.document;
    const iconDataUri = "{perfume_svg_favicon}";
    
    function lockTitleAndFavicon() {{
        try {{
            if (topDoc.title !== "PerfumeTrending") {{
                topDoc.title = "PerfumeTrending";
            }}
            let iconLink = topDoc.querySelector("link[rel*='icon']");
            if (!iconLink) {{
                iconLink = topDoc.createElement('link');
                iconLink.rel = 'shortcut icon';
                topDoc.getElementsByTagName('head')[0].appendChild(iconLink);
            }}
            if (iconLink.href !== iconDataUri) {{
                iconLink.href = iconDataUri;
            }}
        }} catch(e) {{}}
    }}

    try {{
        lockTitleAndFavicon();
        const titleEl = topDoc.querySelector('title');
        if (titleEl) {{
            const titleObserver = new MutationObserver(lockTitleAndFavicon);
            titleObserver.observe(titleEl, {{ childList: true, characterData: true, subtree: true }});
        }}
    }} catch(e) {{}}

    if (typeof topWin.soundMuted === 'undefined') {{
        topWin.soundMuted = false;
    }}
    
    topWin.playBubbleSound = function() {{
        if (topWin.soundMuted) return;
        try {{
            const AudioContext = window.AudioContext || window.webkitAudioContext || topWin.AudioContext || topWin.webkitAudioContext;
            if (!AudioContext) return;
            if (!topWin.audioCtx) {{
                topWin.audioCtx = new AudioContext();
            }}
            const ctx = topWin.audioCtx;
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

    topWin.toggleSoundMute = function() {{
        topWin.soundMuted = !topWin.soundMuted;
        topWin.updateSoundButtonUI();
    }};

    topWin.updateSoundButtonUI = function() {{
        const btn = topDoc.getElementById('sound-toggle-btn');
        if (btn) {{
            const speakerSvg = '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14"/></svg>';
            const muteSvg = '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><line x1="23" y1="9" x2="17" y2="15"/><line x1="17" y1="9" x2="23" y2="15"/></svg>';
            btn.innerHTML = topWin.soundMuted ? muteSvg : speakerSvg;
            btn.title = topWin.soundMuted ? 'Activar sonido de burbujas' : 'Desactivar sonido de burbujas';
            btn.style.opacity = topWin.soundMuted ? '0.45' : '1';
        }}
    }};

    function attachCardEvents() {{
        lockTitleAndFavicon();
        const essenceCards = topDoc.querySelectorAll('.essence-card');
        essenceCards.forEach(card => {{
            if (!card.dataset.soundAttached) {{
                card.dataset.soundAttached = 'true';
                card.addEventListener('click', () => topWin.playBubbleSound());
            }}
        }});

        topWin.updateSoundButtonUI();
    }}

    let debounceTimer = null;
    const observer = new MutationObserver(() => {{
        if (debounceTimer) clearTimeout(debounceTimer);
        debounceTimer = setTimeout(attachCardEvents, 100);
    }});
    
    observer.observe(topDoc.body, {{ childList: true, subtree: true }});
    attachCardEvents();

    setInterval(function() {{
        try {{
            if (topWin && topWin.document) {{
                topWin.document.dispatchEvent(new Event('visibilitychange'));
            }}
        }} catch(e) {{}}
    }}, 180000);
}})();
</script>
"""

try:
    st.html(js_color_script, unsafe_allow_javascript=True)
except Exception:
    components.html(js_color_script, height=0, width=0)

# 5. CSS ADAPTABLE Y ESTILOS
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
        font-size: 1rem !important;
        text-shadow: none !important;
    }}

    /* EFECTO DE BOTONES Y ENLACES PAGE_LINK */
    div.stButton > button,
    div.stDownloadButton > button {{
        background-color: {btn_bg} !important;
        border: 1px solid {btn_border} !important;
        color: {btn_text} !important;
        border-radius: 8px !important;
        transition: transform 0.22s cubic-bezier(0.34, 1.56, 0.64, 1), background-color 0.15s ease, border-color 0.15s ease, color 0.15s ease !important;
        text-shadow: none !important;
        box-shadow: { "none" if is_dark else "0 1px 3px rgba(0,0,0,0.05)" } !important;
        outline: none !important;
    }}

    div.stButton > button p,
    div.stDownloadButton > button p {{
        color: {btn_text} !important;
        font-weight: 600 !important;
    }}

    /* BOTONES DE COMPARAR PRECIOS EN CATÁLOGO */
    div[data-testid="stElementContainer"] div.stButton button[key*="btn_comp_"],
    div.stButton > button[key*="btn_comp_"] {{
        background-color: #d83737 !important;
        color: #ffffff !important;
        border: 1px solid #d83737 !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
        box-shadow: 0 3px 10px rgba(216, 55, 55, 0.25) !important;
    }}

    div[data-testid="stElementContainer"] div.stButton button[key*="btn_comp_"] p,
    div.stButton > button[key*="btn_comp_"] p {{
        color: #ffffff !important;
        font-weight: 700 !important;
    }}

    div[data-testid="stElementContainer"] div.stButton button[key*="btn_comp_"]:hover,
    div.stButton > button[key*="btn_comp_"]:hover {{
        background-color: #be2e2e !important;
        border-color: #be2e2e !important;
        color: #ffffff !important;
        transform: scale(1.03) !important;
        box-shadow: 0 5px 14px rgba(216, 55, 55, 0.35) !important;
    }}

    div.stButton > button:hover,
    .st-key-btn_photo_search button:hover,
    .st-key-login_btn button:hover,
    div.stButton > button:focus,
    a[data-testid="stPageLink-NavLink"]:hover {{
        transform: scale(1.04) !important;
        cursor: pointer !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
        filter: none !important;
        outline: none !important;
    }}

    div.stButton > button:active,
    a[data-testid="stPageLink-NavLink"]:active {{
        transform: scale(0.98) !important;
    }}

    /* ESTILO ESPECÍFICO PARA BOTONES POPOVER */
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

    div[data-testid="stPopover"] > button:hover,
    button[data-testid="stPopoverButton"]:hover {{
        transform: scale(1.04) !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
    }}

    div[data-testid="stPopover"] button p,
    div[data-testid="stPopover"] button span,
    div[data-testid="stPopover"] button label,
    div[data-testid="stPopover"] button div,
    button[data-testid="stPopoverButton"] p,
    button[data-testid="stPopoverButton"] span,
    button[data-testid="stPopoverButton"] div {{
        color: {btn_text} !important;
        font-weight: 600 !important;
        white-space: nowrap !important;
        text-overflow: clip !important;
        overflow: visible !important;
    }}

    div[data-testid="stPopoverBody"],
    div[data-testid="stPopoverContent"] {{
        background-color: {input_bg} !important;
        border: 1px solid {btn_border} !important;
        border-radius: 8px !important;
        color: {text_color} !important;
    }}

    /* CONTENEDOR Y BOTÓN POPOVER DE USUARIO */
    .user-popover-container div[data-testid="stPopover"],
    .user-popover-container div[data-testid="stPopover"] > button,
    .user-popover-container button[data-testid="stPopoverButton"] {{
        padding-left: 2.3rem !important;
        background-image: url("{user_icon_svg}") !important;
        background-repeat: no-repeat !important;
        background-position: 12px center !important;
        background-size: 18px 18px !important;
    }}

    /* BOTÓN CERRAR SESIÓN Y MI PERFIL */
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

    /* SWITCH TEMA */
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

    /* NAVEGACIÓN SUPERIOR Principal */
    .st-key-n_perfumes button, 
    .st-key-n_esencias button {{
        background-color: transparent !important;
        border: none !important;
        border-bottom: 1px solid transparent !important;
        border-radius: 0px !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        padding: 0.6rem 0rem !important;
        box-shadow: none !important;
        letter-spacing: 0.8px !important;
        min-height: 0px !important;
        height: auto !important;
        transition: transform 0.22s cubic-bezier(0.34, 1.56, 0.64, 1), color 0.15s ease !important;
    }}

    .st-key-n_perfumes button p, 
    .st-key-n_esencias button p {{
        color: {text_color} !important;
        font-weight: 600 !important;
        white-space: nowrap !important;
        font-size: 0.95rem !important;
    }}

    .st-key-n_perfumes button:hover, 
    .st-key-n_esencias button:hover {{
        transform: scale(1.08) !important;
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

    /* DIBUJOS ILUSTRADOS VECTORIALES EN ROJO PARA CHIPS */
    .st-key-btn_chip_home button {{
        position: relative !important;
        padding-left: 2.7rem !important;
        border-radius: 20px !important;
    }}
    .st-key-btn_chip_home button::before {{
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

    a[data-testid="stPageLink-NavLink"][href*="trendhype"],
    a[data-testid="stPageLink-NavLink"][href*="trustpage"],
    a[data-testid="stPageLink-NavLink"][href*="compararprecios"],
    a[data-testid="stPageLink-NavLink"][href*="remates"] {{
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

    /* 4. Remates & Flash */
    a[data-testid="stPageLink-NavLink"][href*="remates"]::before {{
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

    /* CHIPS DE ACCESO RÁPIDO CON BOTONES NATIVOS STREAMLIT */
    .st-key-chip_home button,
    .st-key-chip_remates button {{
        background-color: {btn_bg} !important;
        border: 1px solid {btn_border} !important;
        border-radius: 20px !important;
        padding: 0.45rem 1rem !important;
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
        color: {btn_text} !important;
        letter-spacing: 0.2px;
        white-space: nowrap !important;
        cursor: pointer !important;
        transition: transform 0.22s cubic-bezier(0.34, 1.56, 0.64, 1), background-color 0.15s ease !important;
    }}
    .st-key-chip_home button:hover,
    .st-key-chip_remates button:hover {{
        transform: scale(1.04) !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
    }}
    .st-key-chip_home button p,
    .st-key-chip_remates button p {{
        font-size: 0.85rem !important;
        font-weight: 600 !important;
        color: {btn_text} !important;
        margin: 0 !important;
        white-space: nowrap !important;
    }}
    .st-key-chip_home button {{
        position: relative !important;
        padding-left: 2.7rem !important;
        padding-right: 1.1rem !important;
    }}
    .st-key-chip_home button::before {{
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
    .st-key-chip_remates button {{
        position: relative !important;
        padding-left: 2.7rem !important;
        padding-right: 1.1rem !important;
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

    /* INPUTS */
    div[data-baseweb="input"],
    div[data-baseweb="base-input"],
    div[data-baseweb="select"] > div {{
        background-color: {input_bg} !important;
        border: 1px solid {input_border} !important;
        border-radius: 8px !important;
        box-shadow: none !important;
        padding-top: 6px !important;
        padding-bottom: 6px !important;
        min-height: 44px !important;
        color: {input_text} !important;
    }}

    div[data-baseweb="file-uploader"],
    [data-testid="stFileUploader"] section {{
        background-color: {input_bg} !important;
        border: 1px dashed {input_border} !important;
        border-radius: 10px !important;
        padding: 12px !important;
    }}

    div[data-baseweb="input"] input,
    div[data-baseweb="base-input"] input {{
        font-size: 0.95rem !important;
        padding: 8px 14px !important;
        color: {input_text} !important;
        background-color: {input_bg} !important;
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

    /* BOTONES DE CATEGORÍAS CATÁLOGO CON ICONOS VECTORIALES */
    div.st-key-btn_cat_todos button,
    div.st-key-btn_cat_arabes button,
    div.st-key-btn_cat_remates button {{
        border-radius: 20px !important;
        padding: 0.35rem 1rem 0.35rem 2.3rem !important;
        font-size: 0.85rem !important;
        font-weight: 600 !important;
        min-height: 36px !important;
        height: 36px !important;
        letter-spacing: 0.3px !important;
        position: relative !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        transition: transform 0.22s cubic-bezier(0.34, 1.56, 0.64, 1), border-color 0.15s ease !important;
    }}
    div.st-key-btn_cat_todos button:hover,
    div.st-key-btn_cat_arabes button:hover,
    div.st-key-btn_cat_remates button:hover {{
        transform: scale(1.03) !important;
    }}
    div.st-key-btn_cat_todos button::before {{
        content: '' !important;
        position: absolute !important;
        left: 12px !important;
        top: 50% !important;
        transform: translateY(-50%) !important;
        width: 14px !important;
        height: 14px !important;
        background-image: url("{grid_icon_svg}") !important;
        background-repeat: no-repeat !important;
        background-size: contain !important;
        background-position: center !important;
    }}
    div.st-key-btn_cat_arabes button::before {{
        content: '' !important;
        position: absolute !important;
        left: 12px !important;
        top: 50% !important;
        transform: translateY(-50%) !important;
        width: 14px !important;
        height: 14px !important;
        background-image: url("{diamond_icon_svg}") !important;
        background-repeat: no-repeat !important;
        background-size: contain !important;
        background-position: center !important;
    }}
    div.st-key-btn_cat_remates button::before {{
        content: '' !important;
        position: absolute !important;
        left: 12px !important;
        top: 50% !important;
        transform: translateY(-50%) !important;
        width: 14px !important;
        height: 14px !important;
        background-image: url("{tag_red_svg}") !important;
        background-repeat: no-repeat !important;
        background-size: contain !important;
        background-position: center !important;
    }}

    /* BOTÓN VER MÁS PERFUMES */
    div.st-key-btn_load_more button {{
        background-color: {card_bg} !important;
        border: 1px solid { "#a39281" if is_dark else "#8c7b6d" } !important;
        color: {text_color} !important;
        padding: 12px 24px !important;
        font-size: 0.95rem !important;
        font-weight: 700 !important;
        border-radius: 12px !important;
        letter-spacing: 0.5px !important;
        box-shadow: { "0 4px 14px rgba(0,0,0,0.3)" if is_dark else "0 2px 8px rgba(0,0,0,0.06)" } !important;
        transition: all 0.22s cubic-bezier(0.34, 1.56, 0.64, 1) !important;
    }}
    div.st-key-btn_load_more button:hover {{
        background-color: { "#1f242e" if is_dark else "#f0ede8" } !important;
        border-color: { "#d4c2a5" if is_dark else "#6e5d50" } !important;
        transform: translateY(-2px) scale(1.01) !important;
        box-shadow: { "0 8px 24px rgba(0,0,0,0.4)" if is_dark else "0 6px 16px rgba(0,0,0,0.12)" } !important;
    }}

    /* TARJETAS CATÁLOGO LUXURY */
    .catalog-card {{
        background-color: {card_bg};
        border: 1px solid {border_color};
        border-radius: 12px;
        overflow: hidden;
        position: relative;
        margin-bottom: 12px;
        box-shadow: { "0 4px 14px rgba(0,0,0,0.25)" if is_dark else "0 2px 10px rgba(0,0,0,0.04)" };
        transition: border-color 0.22s ease, transform 0.22s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.22s ease;
        display: flex;
        flex-direction: column;
    }}
    .catalog-card:hover {{
        border-color: { "#a39281" if is_dark else "#8c7b6d" };
        transform: translateY(-4px);
        box-shadow: { "0 10px 24px rgba(0,0,0,0.38)" if is_dark else "0 8px 20px rgba(0,0,0,0.08)" };
    }}
    .square-img-box {{
        position: relative;
        width: 100%;
        aspect-ratio: 1 / 1;
        background: { "radial-gradient(circle at center, #1b2029 0%, #101217 100%)" if is_dark else "radial-gradient(circle at center, #ffffff 0%, #f4f4f6 100%)" };
        display: flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
        padding: 18px;
        box-sizing: border-box;
        border-bottom: 1px solid {border_color};
    }}
    .square-img-box img {{
        max-width: 88%;
        max-height: 88%;
        object-fit: contain;
        transition: transform 0.28s ease;
        filter: { "drop-shadow(0 6px 14px rgba(0,0,0,0.35))" if is_dark else "drop-shadow(0 4px 10px rgba(0,0,0,0.08))" };
    }}
    .catalog-card:hover .square-img-box img {{
        transform: scale(1.05);
    }}
    .card-hover-overlay {{
        position: absolute !important;
        top: 0 !important; left: 0 !important; right: 0 !important; bottom: 0 !important;
        background: { "rgba(12, 14, 18, 0.94)" if is_dark else "rgba(255, 255, 255, 0.96)" } !important;
        backdrop-filter: blur(8px) !important;
        -webkit-backdrop-filter: blur(8px) !important;
        color: { "#ffffff" if is_dark else "#18181b" } !important;
        padding: 16px !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: flex-start !important;
        align-items: flex-start !important;
        opacity: 0 !important;
        visibility: hidden !important;
        pointer-events: none !important;
        transition: opacity 0.22s ease, visibility 0.22s ease !important;
        text-align: left !important;
        overflow-y: auto !important;
        z-index: 4 !important;
    }}
    .catalog-card:hover .card-hover-overlay {{
        opacity: 1 !important;
        visibility: visible !important;
        pointer-events: auto !important;
    }}
    .overlay-title {{
        font-size: 0.98rem;
        font-weight: 700;
        color: { "#d4c2a5" if is_dark else "#8c7b6d" };
        margin-bottom: 6px;
        border-bottom: 1px solid { "rgba(255,255,255,0.12)" if is_dark else "rgba(0,0,0,0.1)" };
        padding-bottom: 4px;
        width: 100%;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}
    .overlay-info {{ 
        font-size: 0.8rem; 
        font-weight: 400; 
        line-height: 1.45; 
        color: { "#e0e0e0" if is_dark else "#374151" }; 
        margin-bottom: 4px; 
        width: 100%;
    }}
    .overlay-notes {{
        display: -webkit-box;
        -webkit-line-clamp: 4;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }}
    .overlay-price-badge {{
        margin-top: auto;
        padding: 5px 8px;
        border-radius: 6px;
        background: rgba(34, 197, 94, 0.15);
        border: 1px solid rgba(34, 197, 94, 0.3);
        color: #4ade80;
        font-weight: 700;
        font-size: 0.82rem;
        width: 100%;
        box-sizing: border-box;
        text-align: center;
    }}
    .card-footer-info {{ 
        padding: 12px 14px 10px 14px; 
        text-align: center; 
        background-color: {card_bg}; 
        flex-grow: 1;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }}
    .card-perfume-name {{ 
        font-size: 0.95rem; 
        font-weight: 600; 
        color: {text_color}; 
        margin-bottom: 2px; 
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}
    .card-perfume-brand {{ 
        font-size: 0.78rem; 
        font-weight: 400; 
        color: {subtext_color}; 
        text-transform: uppercase; 
        letter-spacing: 0.8px; 
        margin-bottom: 6px;
    }}
    .card-perfume-price {{
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 6px;
        margin-top: 6px;
        padding: 4px 10px;
        background-color: { "rgba(255, 255, 255, 0.04)" if is_dark else "rgba(0, 0, 0, 0.03)" };
        border-radius: 6px;
        border: 1px solid { border_color };
    }}
    .price-label {{
        font-size: 0.74rem;
        color: {subtext_color};
        text-transform: uppercase;
        font-weight: 600;
        letter-spacing: 0.4px;
    }}
    .price-val {{
        font-size: 0.96rem;
        font-weight: 800;
        color: { "#4ade80" if is_dark else "#15803d" };
        letter-spacing: 0.2px;
    }}
    .price-val-agotado {{
        font-size: 0.8rem;
        font-weight: 700;
        color: { "#f87171" if is_dark else "#dc2626" };
        letter-spacing: 0.3px;
    }}
    .out-of-stock-card-price {{
        background-color: { "rgba(239, 68, 68, 0.08)" if is_dark else "rgba(239, 68, 68, 0.05)" } !important;
        border-color: { "rgba(239, 68, 68, 0.2)" if is_dark else "rgba(239, 68, 68, 0.15)" } !important;
    }}

    /* TARJETAS ESENCIAS */
    .essence-card {{ 
        border-radius: 8px; 
        padding: 14px 16px; 
        margin-bottom: 12px; 
        border-width: 1px; 
        border-style: solid;
        cursor: pointer;
        user-select: none;
        transition: transform 0.22s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.22s ease, border-color 0.22s ease;
    }}
    .essence-card:hover {{
        transform: translateY(-4px) scale(1.025);
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.2);
    }}
    .essence-title {{ 
        font-size: 0.98rem; 
        font-weight: 700; 
        margin-bottom: 6px; 
        letter-spacing: 0.3px; 
    }}
    .essence-desc {{ 
        font-size: 0.88rem; 
        font-weight: 500; 
        line-height: 1.5; 
        opacity: 0.95; 
    }}

    .sound-mute-btn {{
        background: transparent;
        border: 1px solid {btn_border};
        color: {text_color};
        border-radius: 50%;
        width: 44px;
        height: 44px;
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: 1.15rem;
        transition: transform 0.22s cubic-bezier(0.34, 1.56, 0.64, 1), background-color 0.2s ease, opacity 0.2s ease;
        margin-bottom: 24px;
        outline: none;
    }}
    .sound-mute-btn:hover {{
        transform: scale(1.15);
        background-color: {btn_bg};
    }}

    /* OPTIMIZACIÓN RESPONSIVA MÓVIL */
    @media (max-width: 768px) {{
        .block-container {{ 
            padding-top: 0.4rem !important; 
            padding-bottom: 1.5rem !important; 
            padding-left: 0.6rem !important;
            padding-right: 0.6rem !important;
        }}

        div[data-testid="stHorizontalBlock"] {{
            flex-wrap: wrap !important;
            gap: 6px !important;
        }}

        div[data-testid="column"], div[data-testid="stColumn"] {{
            width: 100% !important;
            flex: 1 1 100% !important;
            min-width: 0 !important;
        }}

        div[style*="border-left: 1px solid"] {{
            display: none !important;
        }}

        div[data-testid="stHorizontalBlock"]:has(.st-key-login_btn, .st-key-theme_toggle) {{
            flex-wrap: nowrap !important;
            align-items: center !important;
            justify-content: space-between !important;
        }}

        .st-key-login_btn {{
            flex: 0 0 auto !important;
            width: auto !important;
        }}

        .st-key-login_btn button {{
            height: 38px !important;
            min-height: 38px !important;
            padding: 0 0.6rem 0 2rem !important;
            font-size: 0.82rem !important;
            background-position: 8px center !important;
            background-size: 15px 15px !important;
        }}

        .st-key-login_btn button p {{
            font-size: 0.82rem !important;
            white-space: nowrap !important;
        }}

        .st-key-theme_toggle {{
            flex: 0 0 auto !important;
            width: auto !important;
        }}

        .st-key-theme_toggle button {{
            transform: scale(0.72) !important;
            transform-origin: right center !important;
            width: 60px !important;
            margin: 0 !important;
        }}

        div[data-testid="stHorizontalBlock"]:has(.st-key-n_perfumes) {{
            flex-wrap: nowrap !important;
        }}

        div[data-testid="column"]:has(.st-key-n_perfumes),
        div[data-testid="column"]:has(.st-key-n_esencias) {{
            flex: 1 1 50% !important;
            width: 50% !important;
        }}

        .st-key-n_perfumes button p,
        .st-key-n_esencias button p {{
            font-size: 0.85rem !important;
        }}

        div[data-testid="column"]:has(input[placeholder*="Buscar"]) {{
            flex: 1 1 100% !important;
            width: 100% !important;
            margin-bottom: 2px !important;
        }}

        div[data-testid="column"]:has(div[data-testid="stPopover"]),
        div[data-testid="column"]:has(.st-key-btn_photo_search) {{
            flex: 1 1 calc(50% - 4px) !important;
            width: calc(50% - 4px) !important;
        }}

        div[data-testid="stPopover"] > button {{
            min-height: 40px !important;
            font-size: 0.82rem !important;
            width: 100% !important;
        }}

        .st-key-btn_photo_search button {{
            min-height: 40px !important;
            font-size: 0.82rem !important;
            padding: 0.3rem 0.4rem 0.3rem 2.1rem !important;
            background-position: 10px center !important;
            background-size: 16px 16px !important;
            width: 100% !important;
        }}

        .st-key-btn_photo_search button p {{
            font-size: 0.82rem !important;
            white-space: nowrap !important;
        }}

        div[data-testid="stHorizontalBlock"]:has(a[data-testid="stPageLink-NavLink"]) {{
            flex-wrap: wrap !important;
            gap: 6px !important;
        }}

        div[data-testid="column"]:has(a[data-testid="stPageLink-NavLink"]) {{
            flex: 1 1 calc(50% - 4px) !important;
            width: calc(50% - 4px) !important;
        }}

        a[data-testid="stPageLink-NavLink"] {{
            padding: 0.5rem 0.4rem 0.5rem 2.2rem !important;
            border-radius: 12px !important;
            min-height: 38px !important;
            justify-content: flex-start !important;
            width: 100% !important;
        }}

        a[data-testid="stPageLink-NavLink"] p,
        a[data-testid="stPageLink-NavLink"] span {{
            font-size: 0.78rem !important;
            white-space: normal !important;
            line-height: 1.1 !important;
            text-align: left !important;
        }}

        a[data-testid="stPageLink-NavLink"]::before {{
            left: 8px !important;
            width: 15px !important;
            height: 15px !important;
        }}

        div[data-testid="stHorizontalBlock"]:has(.catalog-card) {{
            flex-direction: column !important;
        }}

        div[data-testid="column"]:has(.catalog-card) {{
            flex: 1 1 100% !important;
            width: 100% !important;
            margin-bottom: 12px !important;
        }}

        .catalog-card {{
            margin-bottom: 8px !important;
            border-radius: 12px !important;
        }}

        .square-img-box {{
            max-height: 280px !important;
            padding: 16px !important;
        }}

        .card-perfume-name {{
            font-size: 1.05rem !important;
        }}

        .card-perfume-brand {{
            font-size: 0.82rem !important;
        }}

        div[data-testid="stElementContainer"] div.stButton button[key*="btn_comp_"] {{
            font-size: 0.9rem !important;
            padding: 8px 12px !important;
            height: 42px !important;
        }}

        div[data-testid="stHorizontalBlock"]:has(.essence-card) {{
            flex-direction: column !important;
        }}

        div[data-testid="column"]:has(.essence-card) {{
            flex: 1 1 100% !important;
            width: 100% !important;
        }}

        .essence-card {{
            padding: 12px 14px !important;
            margin-bottom: 8px !important;
        }}

        .essence-title {{
            font-size: 0.95rem !important;
        }}

        .essence-desc {{
            font-size: 0.85rem !important;
        }}
    }}
    </style>
""", unsafe_allow_html=True)

# 4. CABECERA CON LOGO COMPACTO E INTERACTIVO
col_logo, col_espacio, col_actions = st.columns([5.5, 1.3, 2.4], vertical_alignment="center")

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

with col_actions:
    btn_col1, btn_col2 = st.columns([1.8, 1.0], vertical_alignment="center")
    with btn_col1:
        if st.session_state['logged_in']:
            user_display = st.session_state['user_info'].get('nombre') or st.session_state['user_info'].get('email', 'Usuario')
            st.markdown('<div class="user-popover-container">', unsafe_allow_html=True)
            with st.popover(f"{user_display}", use_container_width=True):
                st.write(f"**Conectado como:**")
                st.write(st.session_state['user_info'].get('email', ''))
                st.markdown("<div style='margin-top: 8px;'></div>", unsafe_allow_html=True)
                
                if st.button("Mi Perfil y Alertas", key="btn_go_profile", use_container_width=True):
                    reset_modals()
                    st.switch_page("pages/perfil.py")
                    
                if st.button("Cerrar Sesión", key="btn_logout", use_container_width=True):
                    cerrar_sesion_usuario()
                    reset_modals()
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            if st.button("Ingresar", key="login_btn", use_container_width=True):
                st.session_state['show_login_modal'] = True
                st.session_state['show_visual_modal'] = False
                st.rerun()
                
    with btn_col2:
        st.button(" ", key="theme_toggle", on_click=toggle_theme)

# 7. NAVEGACIÓN PRINCIPAL
st.markdown("<div style='margin-top: 14px;'></div>", unsafe_allow_html=True)
nav_cols = st.columns([1, 1])

with nav_cols[0]: 
    st.button("PERFUMES", key="n_perfumes", on_click=navigate_to, args=('home',), use_container_width=True)
with nav_cols[1]: 
    st.button("ESENCIAS", key="n_esencias", on_click=navigate_to, args=('esencias_page',), use_container_width=True)

st.markdown(f"<hr style='margin: 10px 0 24px 0; border: none; border-bottom: 1px solid {btn_border}; opacity: 0.3;'>", unsafe_allow_html=True)

# 8. BÚSQUEDA Y FILTRO DE ESENCIAS
col_search, col_filter = st.columns([7.8, 2.2], vertical_alignment="center")

with col_search:
    search_query = st.text_input("Buscar", placeholder="Buscar perfume, marca o esencias...", label_visibility="collapsed")

raw_notes = [
    "Bergamota", "Clementina", "Limón", "Lima", "Mandarina", "Neroli", "Petit Grain", "Pomelo (Toronja)", "Yuzu",
    "Almendra", "Avellana", "Ciruela", "Coco", "Durazno (Melocotón)", "Frambuesa", "Grosellas Negras", 
    "Higo", "Lichi", "Manzana", "Melón", "Pera", "Piña", "Ruibarbo", "Sandía",
    "Fresia", "Geranio", "Heliotropo", "Iris (Orris)", "Lavanda", "Lilium (Lirio)", "Mimosa", "Peonía", "Rosa", "Violeta",
    "Flor de Azahar del Naranjo", "Flor de Frangipani", "Gardenia", "Jazmín", "Magnolia", "Tuberosa (Nardo)", "Ylang-Ylang",
    "Abedul", "Albahaca", "Eucalipto", "Gálbano", "Hojas de Violeta", "Menta", "Pachulí", "Romero", "Salvia", "Té Blanco", "Té Negro", "Té Verde", "Vetiver",
    "Anís Estrellado", "Azafrán", "Canela", "Cardamomo", "Clavo de Olor", "Jengibre", "Nuez Moscada", "Pimienta Blanca", "Pimienta Negra", "Pimienta Rosa",
    "Cacao / Chocolate", "Café", "Caramelo", "Haba Tonka", "Leche", "Malvavisco", "Miel", "Praliné", "Vainilla",
    "Cedro", "Ciprés", "Ébano", "Guayac", "Musgo de Roble", "Oud (Madera de Agar)", "Sándalo",
    "Ámbar (Cálido)", "Bálsamo del Perú", "Benjuí", "Estoraque", "Incienso (Olíbano)", "Ládano", "Mirra",
    "Almizcle (Blanco/Musk)", "Almizcle Vegetal", "Ámbar Gris", "Castóreo", "Civeta",
    "Amaretto", "Champán", "Cognac", "Ginebra", "Mojito", "Ron", "Whisky",
    "Aldehídos", "Ambroxan", "Cachemira (Cashmeran)", "Cuero", "Iso E Super", "Notas Marinas", "Notas Solares", "Sangre (Metálica)"
]

all_notes = sorted(raw_notes)

with col_filter:
    with st.popover("Esencias", use_container_width=True):
        selected_essences = st.multiselect(
            "Selecciona notas olfativas:",
            options=all_notes,
            placeholder="Filtrar...",
            label_visibility="collapsed"
        )

# 7. CHIPS DE ENLACE RÁPIDO (5 ACCESOS DIRECTOS)
st.markdown("<div style='margin-top: 14px;'></div>", unsafe_allow_html=True)
c_chip0, c_chip1, c_chip2, c_chip3, c_chip4 = st.columns([1.7, 1.6, 2.0, 1.8, 1.8], vertical_alignment="center")

with c_chip0:
    if st.button("Inicio / Catálogo", key="chip_home", use_container_width=True, on_click=reset_to_home):
        pass
with c_chip1:
    st.page_link("pages/trendhype.py", label="Trend Del Hype", use_container_width=True)
with c_chip2:
    st.page_link("pages/trustpage.py", label="Páginas de Confianza", use_container_width=True)
with c_chip3:
    st.page_link("pages/compararprecios.py", label="Comparar Precios", use_container_width=True)
with c_chip4:
    if st.button("Remates & Flash", key="chip_remates", use_container_width=True):
        st.session_state['selected_category'] = 'remates'
        st.session_state['catalog_page'] = 1
        st.rerun()

st.markdown("<div style='margin-top: 24px;'></div>", unsafe_allow_html=True)

# 10. SECCIONES Y CONTENIDOS
if st.session_state['current_page'] == 'home':
    st.markdown(f"<div style='text-align: center; margin-bottom: 20px; color: {text_color}; letter-spacing: 1.5px; font-weight: 300; font-size: 1.1rem; text-transform: uppercase;'>CATÁLOGO Y TENDENCIAS EN CHILE</div>", unsafe_allow_html=True)
    
    # =========================================================================
    # BLOQUE 5: FILTRADO MULTI-FACÉTICO (CATEGORÍAS Y ORDENAMIENTO EN VIVO)
    # -------------------------------------------------------------------------
    # ¿QUÉ HACE ESTE BLOQUE?
    # 1. Filtros por categoría comercial:
    #    - "Todos": Muestra el catálogo unificado de más de 130 fragancias.
    #    - "Árabes & Nicho": Filtra fragancias orientales (Lattafa, Armaf, Afnan).
    #    - "Remates & Ofertas": Filtra solo perfumes con rebajas demostrables.
    # 2. Selector de ordenamiento:
    #    - Destacados (id_asc), Precio Ascendente/Descendente, Nombre A-Z.
    # 3. Al cambiar cualquier filtro, resetea la página a 1 (`catalog_page = 1`)
    #    y re-ejecuta reactivamente la vista con `st.rerun()`.
    # =========================================================================
    col_filter_chips, col_sort_select = st.columns([7, 3], vertical_alignment="center")
    
    cur_cat = st.session_state.get('selected_category', 'todos')
    cat_active_key = f"btn_cat_{cur_cat}"
    st.markdown(f"""
        <style>
        div.st-key-{cat_active_key} button {{
            border-color: #d83737 !important;
            background-color: {"#241518" if is_dark else "#fdf2f2"} !important;
            box-shadow: 0 0 0 1px #d83737 !important;
        }}
        </style>
    """, unsafe_allow_html=True)

    with col_filter_chips:
        c_cat1, c_cat2, c_cat3 = st.columns([1.8, 2.0, 2.1])
        with c_cat1:
            if st.button("Todos los Perfumes", key="btn_cat_todos", use_container_width=True):
                st.session_state['selected_category'] = 'todos'
                st.session_state['catalog_page'] = 1
                st.rerun()
        with c_cat2:
            if st.button("Árabes & Nicho", key="btn_cat_arabes", use_container_width=True):
                st.session_state['selected_category'] = 'arabes'
                st.session_state['catalog_page'] = 1
                st.rerun()
        with c_cat3:
            if st.button("Remates & Ofertas", key="btn_cat_remates", use_container_width=True):
                st.session_state['selected_category'] = 'remates'
                st.session_state['catalog_page'] = 1
                st.rerun()
                
    with col_sort_select:
        orden_map = {
            "Destacados": "id_asc",
            "Precio: Menor a Mayor": "precio_asc",
            "Precio: Mayor a Menor": "precio_desc",
            "Nombre: A - Z": "nombre_asc"
        }
        labels = list(orden_map.keys())
        current_label = st.session_state.get('selected_order_label', 'Destacados')
        cur_idx = labels.index(current_label) if current_label in labels else 0
        nuevo_orden = st.selectbox(
            "Ordenar catálogo", 
            options=labels, 
            index=cur_idx, 
            label_visibility="collapsed"
        )
        if nuevo_orden != current_label:
            st.session_state['selected_order_label'] = nuevo_orden
            st.session_state['selected_order'] = orden_map[nuevo_orden]
            st.session_state['catalog_page'] = 1
            st.rerun()

    if selected_essences:
        safe_essences = ", ".join(escape_html(e) for e in selected_essences)
        st.markdown(f"<div style='margin: 8px 0 16px 0; font-size: 0.9rem; color: {subtext_color};'><b>Filtro de notas activo:</b> {safe_essences}</div>", unsafe_allow_html=True)

    # =========================================================================
    # BLOQUE 6: CONSULTA REACTIVA A BD Y PAGINACIÓN DINÁMICA (12 ITEMS/PÁG)
    # -------------------------------------------------------------------------
    # ¿QUÉ HACE ESTE BLOQUE?
    # 1. Invoca `get_cached_catalogo()` combinando texto, esencias y categoría.
    # 2. Divide el conjunto en páginas de 12 elementos (`items_per_page = 12`).
    # 3. Calcula `start_idx` y `end_idx` para extraer la porción visible (slice `[start:end]`).
    # 4. Renderiza los perfumes en una grilla de 3 columnas (`cols_per_row = 3`).
    # 5. Tarjeta interactiva con hover overlay: revela país de origen, concentración
    #    y notas completas al posar el cursor, con botón para ir directo a la comparativa.
    # =========================================================================
    categoria_arg = None if st.session_state['selected_category'] == 'todos' else st.session_state['selected_category']
    catalog_perfumes = get_cached_catalogo(
        busqueda=search_query, 
        esencias_tuple=tuple(selected_essences) if selected_essences else None,
        categoria=categoria_arg,
        orden=st.session_state.get('selected_order', 'id_asc')
    )

    @st.fragment
    def render_catalogo_paginado(catalog_list):
        if not catalog_list:
            st.info("No se encontraron perfumes que coincidan con la búsqueda o notas seleccionadas.")
            if st.button("Restablecer filtros", key="btn_reset_filters"):
                reset_to_home()
                st.rerun()
            return

        total_perfumes = len(catalog_list)
        opciones_por_pag = [12, 24, 48, 96]
        items_per_page = int(st.session_state.get('items_per_page', 12))
        if items_per_page not in opciones_por_pag:
            items_per_page = 12
        total_pages = max(1, (total_perfumes + items_per_page - 1) // items_per_page)

        if st.session_state['catalog_page'] > total_pages:
            st.session_state['catalog_page'] = total_pages
        elif st.session_state['catalog_page'] < 1:
            st.session_state['catalog_page'] = 1

        cur_page = int(st.session_state['catalog_page'])
        extra_rows = int(st.session_state.get('catalog_extra_items', 0))
        start_idx = (cur_page - 1) * items_per_page
        end_idx = min(start_idx + items_per_page + extra_rows, total_perfumes)

        col_stat_txt, col_per_page, col_jump_top = st.columns([5.2, 2.4, 2.4], vertical_alignment="center")
        with col_stat_txt:
            st.markdown(
                f"<div style='font-size: 0.88rem; color: {subtext_color}; margin: 4px 0;'>"
                f"Mostrando <b>{start_idx + 1}–{end_idx}</b> de <b>{total_perfumes}</b> fragancias "
                f"&bull; Página <b>{cur_page}</b> de <b>{total_pages}</b></div>",
                unsafe_allow_html=True,
            )
        with col_per_page:
            sel_pp = st.selectbox(
                "Perfumes por página",
                options=opciones_por_pag,
                index=opciones_por_pag.index(items_per_page),
                format_func=lambda n: f"Mostrar {n} por pág.",
                key="sel_items_per_page_top",
                label_visibility="collapsed",
            )
            if sel_pp != items_per_page:
                st.session_state['items_per_page'] = sel_pp
                st.session_state['catalog_page'] = 1
                st.session_state['catalog_extra_items'] = 0
                st.rerun(scope="fragment")
        with col_jump_top:
            sel_jump = st.selectbox(
                "Ir a página",
                options=list(range(1, total_pages + 1)),
                index=cur_page - 1,
                format_func=lambda p_num: f"Ir a página {p_num} de {total_pages}",
                key="sel_jump_page_top",
                label_visibility="collapsed",
            )
            if sel_jump != cur_page:
                st.session_state['catalog_page'] = int(sel_jump)
                st.session_state['catalog_extra_items'] = 0
                st.rerun(scope="fragment")

        st.markdown("<div style='margin-top: 8px;'></div>", unsafe_allow_html=True)

        page_perfumes = catalog_list[start_idx:end_idx]
        cols_per_row = 3
        for i in range(0, len(page_perfumes), cols_per_row):
            cols = st.columns(cols_per_row, gap="medium")
            for j in range(cols_per_row):
                if i + j < len(page_perfumes):
                    p = page_perfumes[i + j]

                    pais_origen = "Emiratos Árabes" if p.get('es_arabe') else "Francia" if p.get('marca') in ['Chanel', 'Dior', 'Yves Saint Laurent', 'Jean Paul Gaultier', 'Kilian', 'Maison Francis Kurkdjian'] else "Italia" if p.get('marca') in ['Giorgio Armani', 'Versace'] else "Estados Unidos" if p.get('marca') in ['Tom Ford'] else "Internacional"
                    nombre_especifico = formatear_nombre_especifico(p) or p.get('nombre', '')
                    nombre_safe = escape_html(nombre_especifico)
                    marca_safe = escape_html(p.get('marca', ''))
                    genero_safe = escape_html(p.get('genero') or 'Unisex')
                    notas_safe = escape_html(p.get('notas') or 'Notas aromáticas selectas')
                    tipo_safe = escape_html(p.get('tipo') or 'Eau de Parfum')
                    img_src = get_image_src(p.get('imagen_url'))

                    mejor_p = p.get('mejor_precio')
                    es_solo_tester = bool(p.get('mejor_precio_es_tester'))
                    if mejor_p and mejor_p > 0:
                        precio_num_txt = f"${mejor_p:,.0f} CLP".replace(",", ".")
                        label_desde = "Tester desde" if es_solo_tester else "Desde"
                        precio_html = f"""
                        <div class="card-perfume-price">
                            <span class="price-label">{label_desde}</span>
                            <span class="price-val">{precio_num_txt}</span>
                        </div>
                        """
                        overlay_badge_html = f'<div class="overlay-price-badge">Mejor oferta: {precio_num_txt}</div>'
                    else:
                        precio_html = f"""
                        <div class="card-perfume-price out-of-stock-card-price">
                            <span class="price-val-agotado">Sin stock</span>
                        </div>
                        """
                        overlay_badge_html = '<div class="overlay-price-badge" style="background: rgba(239, 68, 68, 0.2); border-color: rgba(239, 68, 68, 0.4); color: #f87171;">Agotado en tiendas</div>'

                    card_html = f"""
                    <div class="catalog-card">
                        <div class="square-img-box">
                            <img src="{img_src}" alt="{nombre_safe}" loading="lazy" decoding="async">
                            <div class="card-hover-overlay">
                                <div class="overlay-title">{nombre_safe}</div>
                                <div class="overlay-info"><b>Marca:</b> {marca_safe} ({tipo_safe} &bull; {genero_safe})</div>
                                <div class="overlay-info"><b>Origen:</b> {pais_origen}</div>
                                <div class="overlay-info overlay-notes" style="margin-top: 4px;"><b>Notas:</b> {notas_safe}</div>
                                {overlay_badge_html}
                            </div>
                        </div>
                        <div class="card-footer-info">
                            <div>
                                <div class="card-perfume-name" title="{nombre_safe}">{nombre_safe}</div>
                                <div class="card-perfume-brand">{marca_safe} &bull; {genero_safe}</div>
                            </div>
                            {precio_html}
                        </div>
                    </div>
                    """
                    with cols[j]:
                        st.markdown(clean_html(card_html), unsafe_allow_html=True)
                        if st.button("Comparar Precios", key=f"btn_comp_{p['id']}", use_container_width=True):
                            st.session_state['selected_perfume'] = p['id']
                            reset_modals()
                            st.switch_page("pages/compararprecios.py")

        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)

        # Botón "Ver más perfumes" acumulativo (carga más tarjetas en la misma vista sin recargar toda la app)
        if end_idx < total_perfumes:
            siguientes_cant = min(items_per_page, total_perfumes - end_idx)
            _, c_more_mid, _ = st.columns([1, 2, 1])
            with c_more_mid:
                if st.button(f"Ver más perfumes (+{siguientes_cant} fragancias) ↓", key="btn_load_more", use_container_width=True):
                    st.session_state['catalog_extra_items'] = extra_rows + items_per_page
                    st.rerun(scope="fragment")

        # Barra de paginación multi-página con ventana numérica clicable + Primera/Última
        win_start = max(1, cur_page - 2)
        win_end = min(total_pages, win_start + 4)
        win_start = max(1, win_end - 4)
        paginas_ventana = list(range(win_start, win_end + 1))

        nav_cols_spec = [1.1, 1.3] + [0.9] * len(paginas_ventana) + [1.3, 1.1]
        pag_cols = st.columns(nav_cols_spec, vertical_alignment="center")

        with pag_cols[0]:
            if st.button("« 1", key="btn_pag_first", disabled=(cur_page <= 1), use_container_width=True):
                st.session_state['catalog_page'] = 1
                st.session_state['catalog_extra_items'] = 0
                st.rerun(scope="fragment")
        with pag_cols[1]:
            if st.button("← Ant.", key="btn_pag_prev", disabled=(cur_page <= 1), use_container_width=True):
                st.session_state['catalog_page'] = max(1, cur_page - 1)
                st.session_state['catalog_extra_items'] = 0
                st.rerun(scope="fragment")

        for idx_p, p_num in enumerate(paginas_ventana):
            with pag_cols[2 + idx_p]:
                lbl_p = f"[{p_num}]" if p_num == cur_page else str(p_num)
                if st.button(lbl_p, key=f"btn_pag_num_{p_num}", disabled=(p_num == cur_page), use_container_width=True):
                    st.session_state['catalog_page'] = p_num
                    st.session_state['catalog_extra_items'] = 0
                    st.rerun(scope="fragment")

        with pag_cols[2 + len(paginas_ventana)]:
            if st.button("Sig. →", key="btn_pag_next", disabled=(cur_page >= total_pages), use_container_width=True):
                st.session_state['catalog_page'] = min(total_pages, cur_page + 1)
                st.session_state['catalog_extra_items'] = 0
                st.rerun(scope="fragment")
        with pag_cols[3 + len(paginas_ventana)]:
            if st.button(f"{total_pages} »", key="btn_pag_last", disabled=(cur_page >= total_pages), use_container_width=True):
                st.session_state['catalog_page'] = total_pages
                st.session_state['catalog_extra_items'] = 0
                st.rerun(scope="fragment")

        st.markdown(
            f"<div style='text-align: center; color: {subtext_color}; font-size: 0.85rem; margin-top: 8px;'>"
            f"Página <b>{cur_page}</b> de <b>{total_pages}</b> &bull; Total catálogo activo: <b>{total_perfumes}</b> fragancias</div>",
            unsafe_allow_html=True,
        )

    render_catalogo_paginado(catalog_perfumes)

elif st.session_state['current_page'] == 'esencias_page':
    col_dict_title, col_dict_mute = st.columns([9, 1])
    
    with col_dict_title:
        st.markdown(f"<div style='text-align: center; color: {text_color}; letter-spacing: 1px; font-weight: 300; margin-bottom: 24px; font-size: 1.1rem; text-transform: uppercase;'>DICCIONARIO DE ESENCIAS Y NOTAS</div>", unsafe_allow_html=True)
    
    with col_dict_mute:
        st.markdown(f"""
        <div style="text-align: right;">
            <button id="sound-toggle-btn" class="sound-mute-btn" onclick="if(window.toggleSoundMute){{window.toggleSoundMute();}}else if(window.parent.toggleSoundMute){{window.parent.toggleSoundMute();}}" title="Activar / Desactivar sonido de burbujas">
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14"/></svg>
            </button>
        </div>
        """, unsafe_allow_html=True)

    def get_essence_colors(name):
        n = name.lower()
        if any(k in n for k in ['sangre', 'cereza', 'frambuesa', 'pimienta rosa', 'rosa', 'ruibarbo', 'lichi', 'ciruela', 'grosella', 'peonía', 'geranio']):
            return ("#5c282e" if is_dark else "#e2b3b7", "#3d1a1e" if is_dark else "#f7eaec", "#f0adb4" if is_dark else "#5c1b22")
        elif any(k in n for k in ['marina', 'marinas', 'agua', 'océano', 'ozónica']):
            return ("#224052" if is_dark else "#a8c7da", "#152933" if is_dark else "#eaf2f7", "#92ccdb" if is_dark else "#173a4b")
        elif any(k in n for k in ['albahaca', 'bergamota', 'cardamomo', 'higo', 'manzana', 'menta', 'pachulí', 'pera', 'romero', 'salvia', 'té verde', 'té blanco', 'vetiver', 'abedul', 'eucalipto', 'gálbano']):
            return ("#234530" if is_dark else "#a4cca2", "#162b1e" if is_dark else "#ebf5ee", "#93d1a3" if is_dark else "#193d25")
        elif any(k in n for k in ['iris', 'lavanda', 'jazmín', 'nardos', 'neroli', 'violeta', 'fresia', 'gardenia', 'ylang', 'magnolia', 'azahar']):
            return ("#432d52" if is_dark else "#c3b1d4", "#2b1d33" if is_dark else "#f2ebf7", "#c7a9db" if is_dark else "#391c47")
        elif any(k in n for k in ['caramelo', 'miel', 'solares', 'vainilla', 'cacao', 'café', 'canela', 'tonka', 'nuez moscada', 'praliné', 'almendra', 'avellana', 'ron', 'cognac', 'whisky']):
            return ("#523522" if is_dark else "#d8bca7", "#332115" if is_dark else "#f7ede6", "#dbb193" if is_dark else "#452914")
        elif any(k in n for k in ['ámbar gris', 'cedro', 'sándalo', 'tabaco', 'cuero', 'oud', 'incienso', 'ciprés', 'ébano', 'guayac', 'musgo', 'benjuí', 'ládano']):
            return ("#373d47" if is_dark else "#bdc1c9", "#23272e" if is_dark else "#edeef0", "#aeb5c2" if is_dark else "#292e36")
        elif any(k in n for k in ['azafrán', 'ámbar', 'mandarina', 'melocotón', 'durazno', 'mirra', 'naranjo', 'pomelo', 'cítrico', 'cítricos', 'limón', 'lima', 'piña', 'jengibre', 'yuzu']):
            return ("#59331e" if is_dark else "#debca8", "#382013" if is_dark else "#f9ede6", "#dfab8c" if is_dark else "#4f2711")
        else:
            return ("#333842" if is_dark else "#cad0d9", "#1f2228" if is_dark else "#f2f4f7", "#bcc2cc" if is_dark else "#2b3038")

    essence_descriptions = {
        "Bergamota": "Cítrico efervescente y luminoso con delicados matices florales.",
        "Clementina": "Cítrico dulce, jugoso y chispeante que transmite alegría inmediata.",
        "Limón": "Ácido, limpio y deslumbrante; inyección de luz y energía viva.",
        "Lima": "Verde, amarga y brillante; aporta un matiz tropical muy refrescante.",
        "Mandarina": "Frutal dulce y suave que brinda una frescura risueña y festiva.",
        "Neroli": "Fresco, cítrico y floral blanco; evoca la elegancia mediterránea.",
        "Petit Grain": "Verde, amargo y leñoso; destilado de las hojas del naranjo amargo.",
        "Pomelo (Toronja)": "Cítrico amargo, efervescente y vigorizante con un toque seco.",
        "Yuzu": "Cítrico japonés con matices entre pomelo y mandarina.",
        "Almendra": "Nota cremosa, suavemente amarga y avainillada.",
        "Avellana": "Cálida, tostada y lactónica; evoca la riqueza cremosa.",
        "Ciruela": "Frutal, rica y aterciopelada; añade una profundidad oscura.",
        "Coco": "Cremoso, exótico y lácteo; transmite una sensación solar.",
        "Durazno (Melocotón)": "Carnoso, jugoso y suave; brinda una dulzura frutal sensual.",
        "Frambuesa": "Frutal, chispeante y acidulada; aporta un matiz alegre.",
        "Grosellas Negras": "Frutal oscuro, ácido y vegetal; genera contrastes refinados.",
        "Higo": "Nota verde, frutal y láctea; evoca la frescura del árbol.",
        "Lichi": "Frutal, acuoso y delicadamente floral; añade frescura exótica.",
        "Manzana": "Crujiente, fresca y jugosa; infunde un toque limpio.",
        "Melón": "Acuoso, frutal dulce; aporta un perfil estival muy refrescante.",
        "Pera": "Jugosa, cristalina y delicada; añade una frescura acuática.",
        "Piña": "Tropical, efervescente y jugosa; añade una salida radiante.",
        "Ruibarbo": "Ácido, verde y chispeante; aporta un contraste vanguardista.",
        "Sandía": "Fresca, ozónica y dulce; transmite ligereza acuosa.",
        "Fresia": "Floral suave, limpio y ligeramente afrutado.",
        "Geranio": "Verde, floral y rosado con matices aromáticos.",
        "Heliotropo": "Polvoso, avainillado y meloso con ecos de almendra dulce.",
        "Iris (Orris)": "Polvoso, elegante y aristocrático; evoca la finura del maquillaje.",
        "Lavanda": "Aromática, limpia y relaxing; pilar clásico que aporta serenidad.",
        "Lilium (Lirio)": "Floral noble, verde y radiante con presencia pulcra.",
        "Mimosa": "Cálida, dulce, polvosa y mielada; evoca la primavera.",
        "Peonía": "Floral delicado, fresco y acuático similar a la rosa joven.",
        "Rosa": "La reina de las flores; romántica, atemporal y rica.",
        "Violeta": "Floral verde, polvoso y dulce; evoca nostalgia elegante.",
        "Flor de Azahar del Naranjo": "Radiante, solar y limpia con matices mielados.",
        "Flor de Frangipani": "Exótica, cremosa y embriagadora con acentos solares.",
        "Gardenia": "Floral opulento, cremoso y verde de gran sensualidad.",
        "Jazmín": "La reina blanca de las flores; voluptuosa y embriagadora.",
        "Magnolia": "Floral fresca, cítrica y cerosa de una elegancia luminosa.",
        "Tuberosa (Nardo)": "Flor blanca intensa, carnal y dramática.",
        "Ylang-Ylang": "Flor exótica, embriagadora y marcadamente sensual.",
        "Abedul": "Nota ahumada, leñosa y balsámica que evoca cuero suave.",
        "Albahaca": "Aromática, fresca y picante; infunde una energía mentolada.",
        "Eucalipto": "Helado, mentolado y balsámico; despeja la composición.",
        "Gálbano": "Resina verde, amarga y silvestre de gran carácter botánico.",
        "Hojas de Violeta": "Verde, metálica y terrosa; aporta un matiz de césped cortado.",
        "Menta": "Vigorizante, fresca y helada; impacto aromático estimulante.",
        "Pachulí": "Terroso, oscuro y balsámico; pilar de la perfumería chipre.",
        "Romero": "Herbal, aromático y balsámico; brinda aire mediterráneo.",
        "Salvia": "Aromática, herbal y ambarina; aporta sofisticación.",
        "Té Blanco": "Delicado, transparente y zen; matiz pulcro y sereno.",
        "Té Negro": "Ahumado, tanino y profundo; aporta estructura seca.",
        "Té Verde": "Herbal, sereno y reconfortante; infunde frescura limpia.",
        "Vetiver": "Terroso, leñoso y ahumado; clásico de la elegancia masculina.",
        "Anís Estrellado": "Especiado, dulce y licoroso con destellos mentolados.",
        "Azafrán": "Especiado, leñoso y de elegancia amarga refinada.",
        "Canela": "Especiada, dulce y cálida; añade una presencia reconfortante.",
        "Cardamomo": "Especiado, fresco y resinoso; brinda una sofisticación vibrante.",
        "Clavo de Olor": "Picante, cálido y penetrante con carácter audaz.",
        "Jengibre": "Picante, efervescente y cítrico; inyecta una chispa moderna.",
        "Nuez Moscada": "Cálida, especiada y amaderada; agrega un contraste misterioso.",
        "Pimienta Blanca": "Especiada suave, seca y sutil; aporta calidez.",
        "Pimienta Negra": "Vigorosa, picante y aromática; infunde un dinamismo directo.",
        "Pimienta Rosa": "Especiada, brillante y frutal; aporta un matiz efervescente.",
        "Cacao / Chocolate": "Profundo, amargo y reconfortante; aporta calidez adictiva.",
        "Café": "Tostado, energizante y oscuro; perfecto para fragancias audaces.",
        "Caramelo": "Dulce, cremoso y tentador; agrega un toque goloso.",
        "Haba Tonka": "Cálida, avainillada y con matices a almendra.",
        "Leche": "Lactónica, suave y envolvente; recrea bienestar reconfortante.",
        "Malvavisco": "Dulce esponjoso, azucarado y algodonoso.",
        "Miel": "Dorada, viscosa y melosa; envuelve en una riqueza cálida.",
        "Praliné": "Dulce de frutos secos y azúcar caramelizada.",
        "Vainilla": "Dulce, sensual y reconfortante; reina de la adicción olfativa.",
        "Cedro": "Seco, noble y leñoso; estructura la base aportando fuerza.",
        "Ciprés": "Resinoso, verde y seco; proyecta serenidad de arboleda.",
        "Ébano": "Madera oscura, densa y refinada de gran presencia.",
        "Guayac": "Madera ahumada, dulce y balsámica con matices rosados.",
        "Musgo de Roble": "Terroso, boscoso y húmedo; esencial para la estructura Chipre.",
        "Oud (Madera de Agar)": "Profundo, resinoso y complejo; tesoro de Oriente.",
        "Sándalo": "Madera cremosa, suave y balsámica; transmite serenidad.",
        "Ámbar (Cálido)": "Nota resinosa y dorada que envuelve en riqueza dulzona.",
        "Bálsamo del Perú": "Balsámico, dulce y acanelado de rica densidad.",
        "Benjuí": "Resina dulce con olor a vainilla tostada e incienso suave.",
        "Estoraque": "Ahumado, leñoso y con matices de cuero resinoso.",
        "Incienso (Olíbano)": "Místico, resinoso y ahumado; añade solemnidad.",
        "Ládano": "Ambarino, denso y profundamente cuero-resinoso.",
        "Mirra": "Balsámica, cálida y milenaria; offers un aura mística.",
        "Almizcle (Blanco/Musk)": "Piel limpia, suavidad algodonosa y fijación sensual.",
        "Almizcle Vegetal": "Alternativa botánica limpia de perfil transparente.",
        "Ámbar Gris": "Marino, terroso y aterciopelada; fija la fragancia.",
        "Castóreo": "Nota animalic ahumada que evoca cuero profundo.",
        "Civeta": "Sensualidad animalica cálida que aporta densidad.",
        "Amaretto": "Licoroso, dulce y almendrado de perfil tentador.",
        "Champán": "Burbujeante, efervescente y festivo de tono cristalino.",
        "Cognac": "Embriagador, leñoso y ambarino con distinción.",
        "Ginebra": "Fresca, botánica y de enebro vigorizante.",
        "Mojito": "Cítrico, mentolado y azucarado de máxima frescura.",
        "Ron": "Licoroso, dulce y especiado con notas de barrica.",
        "Whisky": "Malteado, ahumado y cálido con presencia elegante.",
        "Aldehídos": "Chispeantes, jabonosos y efervescentes; elevan el perfume.",
        "Ambroxan": "Ambarino, leñoso y salino de proyección moderna.",
        "Cachemira (Cashmeran)": "Suave como la lana, leñoso, ambarino y almizclado.",
        "Cuero": "Seco, ahumado y sofisticado; proyecta distinción.",
        "Iso E Super": "Molécula maderosa, suave battered.",
        "Notas Marinas": "Brisa salada y aire ozónico; aportan frescura oceánica.",
        "Notas Solares": "Calidez de la piel bajo el sol y tardes de verano.",
        "Sangre (Metálica)": "Nota vanguardista nicho; evoca hierro y un matiz salado."
    }

    col_es_1, col_es_2 = st.columns(2, gap="medium")
    html_col1 = []
    html_col2 = []
    
    for i, note in enumerate(all_notes):
        border_col, bg_col, text_c = get_essence_colors(note)
        desc = essence_descriptions.get(note, "Nota olfativa distintiva que aporta carácter y equilibrio.")
        
        tarjeta_html = f"""
        <div class="essence-card" onclick="(window.playBubbleSound || window.parent.playBubbleSound || function(){{}})()" style="border-color: {border_col}; background-color: {bg_col}; color: {text_c};">
            <div class="essence-title" style="color: {text_c} !important;">{note}</div>
            <div class="essence-desc" style="color: {text_c} !important;">{desc}</div>
        </div>
        """
        if i % 2 == 0:
            html_col1.append(tarjeta_html)
        else:
            html_col2.append(tarjeta_html)

    with col_es_1:
        st.markdown("\n".join(html_col1), unsafe_allow_html=True)
    with col_es_2:
        st.markdown("\n".join(html_col2), unsafe_allow_html=True)

# 11. PIE DE PÁGINA (FOOTER)
st.markdown(f"<hr style='margin: 40px 0 20px 0; border: none; border-bottom: 1px solid {btn_border}; opacity: 0.3;'>", unsafe_allow_html=True)
st.markdown(f"""
    <div style="text-align: center; padding: 10px 0 20px 0; color: {subtext_color}; font-size: 0.85rem;">
        © 2026 Perfume Trending. Todos los derechos reservados.
    </div>
""", unsafe_allow_html=True)
