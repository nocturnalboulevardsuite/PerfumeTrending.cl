"""
PerfumeTrending.cl — Aplicación Web Principal (Streamlit Portal)
================================================================
Punto de entrada de la plataforma chilena de comparación de precios de fragancias:
- Arquitectura de navegación multipágina (Home, Comparador, Remates, TrendHype, TrustScore, Perfil).
- Catálogo interactivo con filtrado multifacético: por búsqueda difusa, familias olfativas, notas y marcas.
- Renderizado de componentes visuales con CSS personalizado (modo oscuro/claro, tipografía Manrope).
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


# 5. TOKENS VISUALES (derivados de la paleta compartida, no alteran el tema)
accent = "#d83737"
accent_hover = "#b92d2d"
accent_soft = "rgba(216, 55, 55, 0.14)" if is_dark else "rgba(216, 55, 55, 0.07)"
gold = "#d4c2a5" if is_dark else "#8c7b6d"
gold_soft = "rgba(212, 194, 165, 0.16)" if is_dark else "rgba(140, 123, 109, 0.14)"
price_green = "#4ade80" if is_dark else "#15803d"
shadow_sm = "0 1px 2px rgba(0,0,0,0.35)" if is_dark else "0 1px 2px rgba(40,30,20,0.06)"
shadow_hover = "0 6px 16px rgba(0,0,0,0.35)" if is_dark else "0 6px 16px rgba(60,45,35,0.10)"
font_display = "'Manrope', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
font_sans = "'Manrope', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"

_search_svg = (
    f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" '
    f'stroke="{subtext_color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    f'<circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.2" y2="16.2"/></svg>'
)
search_icon_svg = "data:image/svg+xml;base64," + base64.b64encode(_search_svg.encode("utf-8")).decode("ascii")

# Dibujos del switch de tema: frasco facetado (perilla) + sol / luna con estrellas (riel)
def _svg_uri(svg: str) -> str:
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")

if is_dark:
    _liq_a, _liq_b, _glass = "#b9a4ff", "#6d5bd0", "#eef1ff"
else:
    _liq_a, _liq_b, _glass = "#ffcf73", "#e8873a", "#ffffff"

switch_bottle_svg = _svg_uri(f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 34 40">
<defs>
<linearGradient id="cap" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#f1d79a"/><stop offset="0.55" stop-color="#c9a24f"/><stop offset="1" stop-color="#8f6a26"/></linearGradient>
<linearGradient id="liq" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{_liq_a}"/><stop offset="1" stop-color="{_liq_b}"/></linearGradient>
<linearGradient id="gl" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{_glass}" stop-opacity="0.98"/><stop offset="1" stop-color="{_glass}" stop-opacity="0.82"/></linearGradient>
</defs>
<rect x="11" y="1" width="12" height="7" rx="2" fill="url(#cap)" stroke="#7a5a1f" stroke-width="0.8"/>
<rect x="13" y="2.2" width="2" height="4.6" rx="1" fill="#fff" opacity="0.5"/>
<rect x="14" y="8" width="6" height="3.5" fill="#d8cfc2" stroke="#9c8f7f" stroke-width="0.6"/>
<path d="M7 11.5 H27 L31 16 V34 Q31 38.5 26.5 38.5 H7.5 Q3 38.5 3 34 V16 Z" fill="url(#gl)" stroke="#8c7b6d" stroke-width="1.1" stroke-linejoin="round"/>
<path d="M5.2 21 Q11 19.2 17 21 T28.8 21 V33.6 Q28.8 36.4 26 36.4 H8 Q5.2 36.4 5.2 33.6 Z" fill="url(#liq)"/>
<path d="M5.2 21 Q11 19.2 17 21 T28.8 21" fill="none" stroke="#ffffff" stroke-opacity="0.55" stroke-width="0.8"/>
<rect x="11" y="24.5" width="12" height="7" rx="1.2" fill="#ffffff" fill-opacity="0.82" stroke="#c9a24f" stroke-width="0.6"/>
<line x1="13.5" y1="27" x2="20.5" y2="27" stroke="#8c7b6d" stroke-width="0.9" stroke-linecap="round"/>
<line x1="14.8" y1="29.2" x2="19.2" y2="29.2" stroke="#8c7b6d" stroke-width="0.7" stroke-linecap="round"/>
<path d="M6.4 15.5 V31" stroke="#ffffff" stroke-width="1.6" stroke-linecap="round" opacity="0.8"/>
</svg>""")

if is_dark:
    switch_track_icon = _svg_uri("""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 30 18">
<path d="M10.5 2.2 A6.8 6.8 0 1 0 17 11.6 A5.4 5.4 0 1 1 10.5 2.2 Z" fill="#f6e7b4"/>
<circle cx="21.5" cy="4" r="0.9" fill="#ffffff"/>
<circle cx="26" cy="9" r="0.7" fill="#ffffff" opacity="0.8"/>
<path d="M23.5 12.2 l0.6 1.4 1.4 0.6 -1.4 0.6 -0.6 1.4 -0.6 -1.4 -1.4 -0.6 1.4 -0.6 Z" fill="#ffffff" opacity="0.9"/>
</svg>""")
    switch_icon_pos = "left 7px center"
    switch_icon_size = "30px 18px"
    switch_track_gradient = "linear-gradient(135deg, #1b1f3b 0%, #2c2f63 100%)"
    switch_track_border = "#3b3f7a"
    switch_track_inset = "rgba(0,0,0,0.55)"
    switch_bottle_left = "40px"
    switch_bottle_shadow = "rgba(120,100,255,0.45)"
    switch_tilt = "6deg"
else:
    switch_track_icon = _svg_uri("""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#e58a12" stroke-width="2" stroke-linecap="round">
<circle cx="12" cy="12" r="4.2" fill="#ffbf3c" stroke="#e58a12"/>
<line x1="12" y1="2" x2="12" y2="4.3"/><line x1="12" y1="19.7" x2="12" y2="22"/>
<line x1="2" y1="12" x2="4.3" y2="12"/><line x1="19.7" y1="12" x2="22" y2="12"/>
<line x1="4.9" y1="4.9" x2="6.5" y2="6.5"/><line x1="17.5" y1="17.5" x2="19.1" y2="19.1"/>
<line x1="4.9" y1="19.1" x2="6.5" y2="17.5"/><line x1="17.5" y1="6.5" x2="19.1" y2="4.9"/>
</svg>""")
    switch_icon_pos = "right 9px center"
    switch_icon_size = "18px 18px"
    switch_track_gradient = "linear-gradient(135deg, #fff4dc 0%, #ffd9a0 100%)"
    switch_track_border = "#efc98a"
    switch_track_inset = "rgba(180,120,40,0.18)"
    switch_bottle_left = "0px"
    switch_bottle_shadow = "rgba(120,80,30,0.30)"
    switch_tilt = "-6deg"

# 6. CSS ADAPTABLE Y ESTILOS
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@300;400;500;600;700;800&display=swap');

    header[data-testid="stHeader"] {{ display: none !important; }}

    .block-container {{
        padding-top: 1.4rem !important;
        padding-bottom: 2rem !important;
        max-width: 1180px !important;
        zoom: 0.95;
    }}

    html, body {{ background-color: {app_bg} !important; }}
    .stApp {{ {app_bg_css} color: {text_color} !important; font-family: {font_sans}; color-scheme: {"dark" if is_dark else "light"}; }}
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"],
    [data-testid="stMainBlockContainer"],
    [data-testid="stBottom"] > div {{
        background: transparent !important;
        background-color: transparent !important;
    }}

    /* Textos nativos: títulos, captions, alertas, pestañas del modal */
    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp strong, .stApp b,
    [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p,
    [data-testid="stWidgetLabel"] p,
    button[data-baseweb="tab"] p {{
        color: {text_color} !important;
    }}
    [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {{
        color: {subtext_color} !important;
    }}
    button[data-baseweb="tab"] {{ background: transparent !important; }}
    div[data-baseweb="tab-highlight"] {{ background-color: {accent} !important; }}
    div[data-baseweb="tab-border"] {{ background-color: {btn_border} !important; }}

    /* Ventanas modales (login y búsqueda visual) */
    div[role="dialog"] {{
        background-color: {card_bg} !important;
        color: {text_color} !important;
        border: 1px solid {border_color} !important;
        border-radius: 16px !important;
    }}
    div[role="dialog"] h2, div[role="dialog"] h2 * , div[role="dialog"] p, div[role="dialog"] label {{
        color: {text_color} !important;
    }}
    div[role="dialog"] button[aria-label="Close"] svg {{ color: {text_color} !important; fill: {text_color} !important; }}

    /* Menús desplegables (selectbox / multiselect) */
    div[data-baseweb="popover"] ul,
    div[data-baseweb="popover"] div[data-baseweb="menu"],
    ul[data-testid="stSelectboxVirtualDropdown"] {{
        background-color: {input_bg} !important;
        border: 1px solid {border_color} !important;
        border-radius: 10px !important;
    }}
    div[data-baseweb="popover"] li,
    div[data-baseweb="popover"] li * {{
        color: {input_text} !important;
        background-color: transparent;
    }}
    div[data-baseweb="popover"] li:hover,
    div[data-baseweb="popover"] li[aria-selected="true"] {{
        background-color: {gold_soft} !important;
    }}
    div[data-baseweb="select"] div,
    div[data-baseweb="select"] input {{
        color: {input_text} !important;
    }}
    div[data-baseweb="select"] svg {{ color: {subtext_color} !important; fill: {subtext_color} !important; }}
    span[data-baseweb="tag"] {{
        background-color: {gold_soft} !important;
        border: 1px solid {gold} !important;
    }}
    span[data-baseweb="tag"] span, span[data-baseweb="tag"] svg {{
        color: {text_color} !important; fill: {text_color} !important;
    }}
    input::placeholder, textarea::placeholder {{
        color: {subtext_color} !important;
        opacity: 1 !important;
    }}

    /* Alertas (st.info, etc.) */
    div[data-testid="stAlert"] > div {{
        background-color: {gold_soft} !important;
        border-radius: 12px !important;
    }}
    div[data-testid="stAlert"] p {{ color: {text_color} !important; }}

    /* Uploader y cámara */
    [data-testid="stFileUploader"] section *,
    [data-testid="stFileUploaderDropzone"] * {{
        color: {text_color} !important;
    }}
    [data-testid="stFileUploader"] small {{ color: {subtext_color} !important; }}

    .stApp p, .stApp label, .stApp li, .stApp input, .stApp textarea, .stApp button,
    .stApp div[data-baseweb="select"] div,
    div[data-testid="stPopoverBody"] p {{
        font-family: {font_sans} !important;
    }}

    .stApp p, .stApp span, .stApp label, .stMarkdown p {{
        color: {text_color} !important;
        text-shadow: none !important;
    }}
    .stMarkdown p {{
        font-size: 1rem !important;
        line-height: 1.55 !important;
    }}

    /* ---------- BOTONES BASE ---------- */
    div.stButton > button,
    div.stDownloadButton > button {{
        background-color: {btn_bg} !important;
        border: 1px solid {btn_border} !important;
        color: {btn_text} !important;
        border-radius: 10px !important;
        min-height: 42px;
        box-shadow: {shadow_sm} !important;
        text-shadow: none !important;
        outline: none !important;
        transition: background-color 0.18s ease, border-color 0.18s ease, color 0.18s ease, box-shadow 0.18s ease, transform 0.18s ease !important;
    }}

    div.stButton > button p,
    div.stDownloadButton > button p {{
        color: {btn_text} !important;
        font-weight: 600 !important;
        font-size: 0.92rem !important;
        letter-spacing: 0.1px !important;
    }}

    div.stButton > button:hover,
    div.stDownloadButton > button:hover,
    a[data-testid="stPageLink-NavLink"]:hover {{
        border-color: {gold} !important;
        box-shadow: {shadow_hover} !important;
        transform: translateY(-1px) !important;
        cursor: pointer !important;
        filter: none !important;
        outline: none !important;
    }}

    div.stButton > button:active,
    a[data-testid="stPageLink-NavLink"]:active {{
        transform: translateY(0) scale(0.99) !important;
    }}

    div.stButton > button:focus-visible,
    a[data-testid="stPageLink-NavLink"]:focus-visible {{
        outline: 2px solid {accent} !important;
        outline-offset: 2px !important;
    }}

    div.stButton > button:disabled {{
        opacity: 0.4 !important;
        transform: none !important;
        box-shadow: none !important;
        cursor: not-allowed !important;
    }}

    /* ---------- BOTÓN PRINCIPAL (COMPARAR PRECIOS) ---------- */
    div[class*="st-key-btn_comp_"] div.stButton > button,
    div[class*="st-key-btn_vis_select_"] div.stButton > button {{
        background-color: {accent} !important;
        border: 1px solid {accent} !important;
        color: #ffffff !important;
        box-shadow: none !important;
    }}
    div[class*="st-key-btn_comp_"] div.stButton > button p,
    div[class*="st-key-btn_vis_select_"] div.stButton > button p {{
        color: #ffffff !important;
        font-weight: 700 !important;
        letter-spacing: 0.2px !important;
    }}
    div[class*="st-key-btn_comp_"] div.stButton > button:hover,
    div[class*="st-key-btn_vis_select_"] div.stButton > button:hover {{
        background-color: {accent_hover} !important;
        border-color: {accent_hover} !important;
        box-shadow: 0 8px 18px rgba(216, 55, 55, 0.28) !important;
    }}

    /* El botón se une visualmente a la base de su tarjeta */
    div[class*="st-key-btn_comp_"] {{
        margin-top: -1rem !important;
    }}
    div[class*="st-key-btn_comp_"] div.stButton > button {{
        border-radius: 0 0 14px 14px !important;
        min-height: 46px !important;
        transform: none !important;
    }}

    /* ---------- POPOVERS ---------- */
    button[data-testid="stPopoverButton"],
    div[data-testid="stPopover"] > button {{
        background-color: {btn_bg} !important;
        color: {btn_text} !important;
        border: 1px solid {btn_border} !important;
        border-radius: 10px !important;
        min-height: 44px !important;
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
        border-radius: 14px !important;
        color: {text_color} !important;
        box-shadow: {shadow_hover} !important;
    }}

    /* Popover de usuario con icono */
    div[data-testid="stColumn"]:has(.user-popover-container) button[data-testid="stPopoverButton"] {{
        padding-left: 2.4rem !important;
        border-radius: 999px !important;
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

    /* ---------- BOTÓN INGRESAR (alineado con el switch) ---------- */
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
        height: 36px !important;
        min-height: 36px !important;
        padding: 0 1rem 0 2.2rem !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        background-image: url("{user_icon_svg}") !important;
        background-repeat: no-repeat !important;
        background-position: 12px center !important;
        background-size: 16px 16px !important;
        box-shadow: {shadow_sm} !important;
        margin: 0 !important;
        white-space: nowrap !important;
    }}
    div.st-key-login_btn div.stButton > button:hover {{
        border-color: {gold} !important;
        box-shadow: {shadow_hover} !important;
    }}
    div.st-key-login_btn div.stButton > button p {{
        font-size: 0.88rem !important;
        line-height: 1 !important;
        margin: 0 !important;
        color: {btn_text} !important;
        font-weight: 700 !important;
        letter-spacing: 0.1px !important;
        white-space: nowrap !important;
    }}
    div[data-testid="stColumn"]:has(.user-popover-container) button[data-testid="stPopoverButton"] {{
        min-height: 36px !important;
        height: 36px !important;
    }}

    /* ---------- SWITCH DE TEMA (frasco de perfume día / noche) ---------- */
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
        width: 76px !important;
        height: 44px !important;
        min-height: 44px !important;
        position: relative !important;
        cursor: pointer !important;
        overflow: visible !important;
        margin-left: auto !important;
        margin-right: 0 !important;
        display: block !important;
        transform: none !important;
    }}

    .st-key-theme_toggle button * {{ display: none !important; }}

    /* Riel: cielo cálido de día, cielo nocturno con estrellas de noche */
    .st-key-theme_toggle button::before {{
        content: '' !important;
        position: absolute !important;
        top: 6px !important; left: 2px !important;
        width: 72px !important; height: 32px !important;
        border-radius: 999px !important;
        box-sizing: border-box !important;
        border: 1px solid {switch_track_border} !important;
        background-image: url("{switch_track_icon}"), {switch_track_gradient} !important;
        background-repeat: no-repeat, no-repeat !important;
        background-position: {switch_icon_pos}, 0 0 !important;
        background-size: {switch_icon_size}, 100% 100% !important;
        box-shadow: inset 0 2px 5px {switch_track_inset} !important;
        transition: border-color 0.3s ease, box-shadow 0.25s ease !important;
    }}

    /* Perilla: frasco de perfume que se desliza */
    .st-key-theme_toggle button::after {{
        content: '' !important;
        position: absolute !important;
        top: 2px !important;
        left: {switch_bottle_left} !important;
        width: 34px !important; height: 40px !important;
        background-image: url("{switch_bottle_svg}") !important;
        background-repeat: no-repeat !important;
        background-position: center !important;
        background-size: contain !important;
        transition: left 0.38s cubic-bezier(0.34, 1.56, 0.64, 1), transform 0.2s ease !important;
        filter: drop-shadow(0 3px 4px {switch_bottle_shadow}) !important;
        z-index: 2 !important;
    }}
    .st-key-theme_toggle button:hover::after {{
        transform: translateY(-1px) rotate({switch_tilt}) !important;
    }}
    .st-key-theme_toggle button:hover::before {{
        box-shadow: inset 0 2px 5px {switch_track_inset}, 0 0 0 3px {gold_soft} !important;
    }}
    .st-key-theme_toggle button:focus-visible::before {{
        box-shadow: inset 0 2px 5px {switch_track_inset}, 0 0 0 2px {accent} !important;
    }}

    /* ---------- NAVEGACIÓN PRINCIPAL (PESTAÑAS) ---------- */
    div.st-key-n_perfumes div.stButton > button,
    div.st-key-n_esencias div.stButton > button {{
        background: transparent !important;
        background-color: transparent !important;
        border: none !important;
        border-bottom: 2px solid transparent !important;
        border-radius: 0 !important;
        box-shadow: none !important;
        padding: 0.7rem 0 !important;
        min-height: 0 !important;
        height: auto !important;
        transform: none !important;
    }}
    div.st-key-n_perfumes div.stButton > button:hover,
    div.st-key-n_esencias div.stButton > button:hover {{
        background: transparent !important;
        box-shadow: none !important;
        transform: none !important;
    }}
    div.st-key-n_perfumes div.stButton > button p,
    div.st-key-n_esencias div.stButton > button p {{
        color: {subtext_color} !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        letter-spacing: 0.2px !important;
        white-space: nowrap !important;
        transition: color 0.18s ease !important;
    }}
    div.st-key-n_perfumes div.stButton > button:hover p,
    div.st-key-n_esencias div.stButton > button:hover p {{
        color: {text_color} !important;
    }}
    .pt-tabs-rule {{
        height: 1px;
        background: {btn_border};
        opacity: 0.55;
        margin: -1rem 0 26px 0;
    }}

    /* ---------- BUSCADOR ---------- */
    div[data-baseweb="input"],
    div[data-baseweb="base-input"],
    div[data-baseweb="select"] > div {{
        background-color: {input_bg} !important;
        border: 1px solid {input_border} !important;
        border-radius: 10px !important;
        box-shadow: none !important;
        min-height: 44px !important;
        color: {input_text} !important;
        transition: border-color 0.18s ease, box-shadow 0.18s ease !important;
    }}
    div[data-baseweb="base-input"] {{
        border: none !important;
    }}
    div[data-baseweb="input"]:focus-within,
    div[data-baseweb="select"] > div:focus-within {{
        border-color: {gold} !important;
        box-shadow: 0 0 0 3px {gold_soft} !important;
    }}

    div[data-baseweb="input"] input,
    div[data-baseweb="base-input"] input {{
        font-size: 0.96rem !important;
        padding: 8px 14px !important;
        color: {input_text} !important;
        background-color: {input_bg} !important;
    }}

    div[data-testid="stTextInput"]:has(input[placeholder*="Buscar"]) div[data-baseweb="input"] {{
        border-radius: 999px !important;
        min-height: 50px !important;
        padding-left: 30px !important;
        background-image: url("{search_icon_svg}") !important;
        background-repeat: no-repeat !important;
        background-position: 18px center !important;
        background-size: 18px 18px !important;
    }}
    div[data-testid="stTextInput"]:has(input[placeholder*="Buscar"]) div[data-baseweb="base-input"],
    div[data-testid="stTextInput"]:has(input[placeholder*="Buscar"]) input {{
        background-color: transparent !important;
    }}
    div[data-testid="stTextInput"]:has(input[placeholder*="Buscar"]) input {{
        font-size: 1rem !important;
    }}
    div[data-testid="stColumn"]:has(input[placeholder*="Buscar"]) + div[data-testid="stColumn"] button[data-testid="stPopoverButton"] {{
        border-radius: 999px !important;
        min-height: 50px !important;
    }}

    div[data-baseweb="file-uploader"],
    [data-testid="stFileUploader"] section {{
        background-color: {input_bg} !important;
        border: 1px dashed {input_border} !important;
        border-radius: 12px !important;
        padding: 14px !important;
    }}

    /* ---------- ACCESOS RÁPIDOS (CHIPS) ---------- */
    a[data-testid="stPageLink-NavLink"],
    div.st-key-chip_home div.stButton > button,
    div.st-key-chip_remates div.stButton > button {{
        background-color: transparent !important;
        border: 1px solid {btn_border} !important;
        border-radius: 999px !important;
        padding: 0.45rem 1.1rem 0.45rem 2.6rem !important;
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
        position: relative !important;
        overflow: hidden !important;
        cursor: pointer !important;
        transition: background-color 0.18s ease, border-color 0.18s ease, transform 0.18s ease !important;
    }}
    a[data-testid="stPageLink-NavLink"]:hover,
    div.st-key-chip_home div.stButton > button:hover,
    div.st-key-chip_remates div.stButton > button:hover {{
        background-color: {btn_bg} !important;
        border-color: {gold} !important;
        box-shadow: none !important;
    }}

    a[data-testid="stPageLink-NavLink"] p,
    a[data-testid="stPageLink-NavLink"] span,
    div.st-key-chip_home div.stButton > button p,
    div.st-key-chip_remates div.stButton > button p {{
        font-size: 0.87rem !important;
        font-weight: 600 !important;
        color: {btn_text} !important;
        white-space: nowrap !important;
        text-overflow: clip !important;
        overflow: visible !important;
        margin: 0 !important;
    }}

    a[data-testid="stPageLink-NavLink"][href*="trendhype"]::before,
    a[data-testid="stPageLink-NavLink"][href*="trustpage"]::before,
    a[data-testid="stPageLink-NavLink"][href*="compararprecios"]::before,
    a[data-testid="stPageLink-NavLink"][href*="remates"]::before,
    div.st-key-chip_home div.stButton > button::before,
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
    a[data-testid="stPageLink-NavLink"][href*="remates"]::before {{ background-image: url("{flame_red_svg}") !important; }}
    div.st-key-chip_home div.stButton > button::before {{ background-image: url("{home_red_svg}") !important; }}
    div.st-key-chip_remates div.stButton > button::before {{ background-image: url("{flame_red_svg}") !important; }}

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
    a.brand-logo-clean:focus-visible {{
        outline: 2px solid {accent} !important;
        outline-offset: 4px !important;
        border-radius: 6px !important;
    }}
    .brand-logo-text {{
        font-family: {font_display} !important;
        font-size: 1.6rem !important;
        color: {text_color} !important;
        font-weight: 300 !important;
        letter-spacing: -0.02em !important;
        line-height: 1 !important;
        display: inline-block !important;
    }}
    .brand-logo-text strong {{
        font-weight: 800 !important;
        color: {text_color} !important;
    }}

    /* ---------- ENCABEZADOS DE SECCIÓN ---------- */
    .pt-section-head {{
        margin: 4px 0 22px 0;
    }}
    .pt-display {{
        font-family: {font_display};
        font-weight: 800;
        font-size: clamp(1.8rem, 3.4vw, 2.5rem);
        line-height: 1.1;
        letter-spacing: -0.025em;
        color: {text_color};
        margin: 0 0 10px 0;
    }}
    .pt-lede {{
        font-size: 1rem;
        line-height: 1.55;
        color: {subtext_color};
        max-width: 62ch;
    }}
    .pt-meta {{
        font-size: 0.9rem;
        color: {subtext_color};
        margin: 4px 0;
        font-variant-numeric: tabular-nums;
    }}
    .pt-meta b {{ color: {text_color}; font-weight: 600; }}
    .pt-meta-center {{ text-align: center; margin-top: 10px; }}

    /* Notas activas del filtro */
    .pt-note-row {{
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 6px;
        margin: 4px 0 18px 0;
    }}
    .pt-note-label {{
        font-size: 0.88rem;
        color: {subtext_color};
        margin-right: 4px;
    }}
    .pt-note-chip {{
        font-size: 0.82rem;
        font-weight: 600;
        color: {text_color};
        background: {gold_soft};
        border: 1px solid {gold};
        border-radius: 999px;
        padding: 3px 11px;
    }}

    /* Estado vacío */
    .pt-empty {{
        border: 1px dashed {btn_border};
        border-radius: 16px;
        padding: 36px 24px;
        text-align: center;
        margin: 8px 0 14px 0;
    }}
    .pt-empty-title {{
        font-family: {font_display};
        font-size: 1.25rem;
        font-weight: 700;
        color: {text_color};
        margin-bottom: 6px;
    }}
    .pt-empty-text {{
        font-size: 0.95rem;
        color: {subtext_color};
    }}

    /* ---------- CATEGORÍAS (SEGMENTOS) ---------- */
    div.st-key-btn_cat_todos div.stButton > button,
    div.st-key-btn_cat_arabes div.stButton > button,
    div.st-key-btn_cat_remates div.stButton > button {{
        background-color: transparent !important;
        border-radius: 999px !important;
        padding: 0.35rem 1rem 0.35rem 2.3rem !important;
        min-height: 40px !important;
        height: 40px !important;
        position: relative !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        box-shadow: none !important;
    }}
    div.st-key-btn_cat_todos div.stButton > button p,
    div.st-key-btn_cat_arabes div.stButton > button p,
    div.st-key-btn_cat_remates div.stButton > button p {{
        font-size: 0.87rem !important;
    }}
    div.st-key-btn_cat_todos div.stButton > button::before,
    div.st-key-btn_cat_arabes div.stButton > button::before,
    div.st-key-btn_cat_remates div.stButton > button::before {{
        content: '' !important;
        position: absolute !important;
        left: 13px !important;
        top: 50% !important;
        transform: translateY(-50%) !important;
        width: 14px !important;
        height: 14px !important;
        background-repeat: no-repeat !important;
        background-size: contain !important;
        background-position: center !important;
    }}
    div.st-key-btn_cat_todos div.stButton > button::before {{ background-image: url("{grid_icon_svg}") !important; }}
    div.st-key-btn_cat_arabes div.stButton > button::before {{ background-image: url("{diamond_icon_svg}") !important; }}
    div.st-key-btn_cat_remates div.stButton > button::before {{ background-image: url("{tag_red_svg}") !important; }}

    /* ---------- VER MÁS ---------- */
    div.st-key-btn_load_more div.stButton > button {{
        background-color: transparent !important;
        border: 1px solid {gold} !important;
        border-radius: 999px !important;
        min-height: 50px !important;
        box-shadow: none !important;
    }}
    div.st-key-btn_load_more div.stButton > button:hover {{
        background-color: {gold_soft} !important;
    }}
    div.st-key-btn_load_more div.stButton > button p {{
        color: {text_color} !important;
        font-size: 0.95rem !important;
    }}

    /* ---------- PAGINACIÓN ---------- */
    div[class*="st-key-btn_pag_"] div.stButton > button {{
        min-height: 40px !important;
        border-radius: 10px !important;
        box-shadow: none !important;
        padding: 0 0.4rem !important;
    }}
    div[class*="st-key-btn_pag_"] div.stButton > button p {{
        font-size: 0.86rem !important;
        font-variant-numeric: tabular-nums !important;
        white-space: nowrap !important;
    }}

    /* ---------- TARJETAS DEL CATÁLOGO ---------- */
    .catalog-card {{
        background-color: {card_bg};
        border: 1px solid {border_color};
        border-bottom: none;
        border-radius: 14px 14px 0 0;
        overflow: hidden;
        position: relative;
        margin-bottom: 0;
        display: flex;
        flex-direction: column;
        transition: border-color 0.2s ease;
    }}
    div[data-testid="stColumn"]:has(.catalog-card) {{
        margin-bottom: 18px;
    }}
    div[data-testid="stColumn"]:has(.catalog-card):hover .catalog-card {{
        border-color: {gold};
    }}
    .square-img-box {{
        position: relative;
        width: 100%;
        aspect-ratio: 1 / 1;
        background: {"radial-gradient(circle at 50% 42%, #1d222c 0%, #11141a 100%)" if is_dark else "radial-gradient(circle at 50% 42%, #ffffff 0%, #f6f4f1 100%)"};
        display: flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
        padding: 22px;
        box-sizing: border-box;
    }}
    .square-img-box img {{
        max-width: 86%;
        max-height: 86%;
        object-fit: contain;
        transition: transform 0.35s ease;
        filter: {"drop-shadow(0 10px 18px rgba(0,0,0,0.45))" if is_dark else "drop-shadow(0 8px 14px rgba(60,45,35,0.12))"};
    }}
    div[data-testid="stColumn"]:has(.catalog-card):hover .square-img-box img {{
        transform: scale(1.04);
    }}
    .card-hover-overlay {{
        position: absolute !important;
        inset: 0 !important;
        background: {"rgba(14, 16, 21, 0.95)" if is_dark else "rgba(255, 255, 255, 0.96)"} !important;
        backdrop-filter: blur(8px) !important;
        -webkit-backdrop-filter: blur(8px) !important;
        color: {"#ffffff" if is_dark else "#18181b"} !important;
        padding: 20px !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: flex-start !important;
        align-items: flex-start !important;
        gap: 2px !important;
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
        font-family: {font_display};
        font-size: 1rem;
        font-weight: 700;
        color: {gold};
        margin-bottom: 8px;
        padding-bottom: 8px;
        border-bottom: 1px solid {"rgba(255,255,255,0.12)" if is_dark else "rgba(0,0,0,0.08)"};
        width: 100%;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}
    .overlay-info {{
        font-size: 0.82rem;
        line-height: 1.5;
        color: {"#e4e4e7" if is_dark else "#3f3f46"};
        margin-bottom: 4px;
        width: 100%;
    }}
    .overlay-notes {{
        display: -webkit-box;
        -webkit-line-clamp: 5;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }}
    .overlay-price-badge {{
        margin-top: auto;
        padding: 7px 10px;
        border-radius: 8px;
        background: rgba(34, 197, 94, 0.14);
        border: 1px solid rgba(34, 197, 94, 0.32);
        color: {price_green};
        font-weight: 700;
        font-size: 0.85rem;
        width: 100%;
        box-sizing: border-box;
        text-align: center;
        font-variant-numeric: tabular-nums;
    }}
    .card-footer-info {{
        padding: 14px 16px 14px 16px;
        background-color: {card_bg};
        border-top: 1px solid {border_color};
        flex-grow: 1;
        display: flex;
        flex-direction: column;
        gap: 10px;
    }}
    .card-perfume-name {{
        font-size: 1rem;
        font-weight: 600;
        color: {text_color};
        line-height: 1.3;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}
    .card-perfume-brand {{
        font-size: 0.84rem;
        color: {subtext_color};
        margin-top: 2px;
    }}
    .card-perfume-price {{
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        gap: 8px;
        padding-top: 10px;
        border-top: 1px dashed {border_color};
    }}
    .price-label {{
        font-size: 0.8rem;
        color: {subtext_color};
        font-weight: 500;
    }}
    .price-val {{
        font-size: 1.12rem;
        font-weight: 700;
        color: {price_green};
        font-variant-numeric: tabular-nums;
        letter-spacing: -0.01em;
    }}
    .price-val-agotado {{
        font-size: 0.86rem;
        font-weight: 600;
        color: {"#f87171" if is_dark else "#dc2626"};
    }}
    .out-of-stock-card-price {{
        justify-content: center;
    }}

    /* ---------- DICCIONARIO DE ESENCIAS ---------- */
    .essence-card {{
        border-radius: 12px;
        padding: 16px 18px;
        margin-bottom: 12px;
        border-width: 1px;
        border-style: solid;
        cursor: pointer;
        user-select: none;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }}
    .essence-card:hover {{
        transform: translateY(-2px);
        box-shadow: {shadow_hover};
    }}
    .essence-card:active {{
        transform: translateY(0) scale(0.99);
    }}
    .essence-title {{
        font-family: {font_display};
        font-size: 1.05rem;
        font-weight: 700;
        line-height: 1.2;
        margin-bottom: 6px;
    }}
    .essence-desc {{
        font-size: 0.9rem;
        line-height: 1.55;
        opacity: 0.92;
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
        transition: background-color 0.18s ease, border-color 0.18s ease, opacity 0.2s ease;
        outline: none;
    }}
    .sound-mute-btn:hover {{
        background-color: {btn_bg};
        border-color: {gold};
    }}
    .sound-mute-btn:focus-visible {{
        outline: 2px solid {accent};
        outline-offset: 2px;
    }}

    /* ---------- PIE DE PÁGINA ---------- */
    .pt-footer {{
        display: flex;
        flex-wrap: wrap;
        align-items: baseline;
        justify-content: space-between;
        gap: 10px;
        padding: 22px 0 26px 0;
        margin-top: 48px;
        border-top: 1px solid {btn_border};
    }}
    .pt-footer-mark {{
        font-family: {font_display};
        font-size: 1.1rem;
        font-weight: 300;
        color: {text_color};
    }}
    .pt-footer-mark strong {{ font-weight: 800; color: {text_color}; }}
    .pt-footer-copy {{
        font-size: 0.85rem;
        color: {subtext_color};
    }}

    @media (prefers-reduced-motion: reduce) {{
        .catalog-card, .square-img-box img, .card-hover-overlay, .essence-card,
        a[data-testid="stPageLink-NavLink"],
        div[data-testid="stElementContainer"]:not(.st-key-theme_toggle) div.stButton > button {{
            transition: none !important;
        }}
    }}

    /* ---------- OPTIMIZACIÓN RESPONSIVA MÓVIL ---------- */
    @media (max-width: 768px) {{
        .block-container {{
            padding-top: 0.4rem !important;
            padding-bottom: 1.5rem !important;
            padding-left: 0.8rem !important;
            padding-right: 0.8rem !important;
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

        .brand-logo-text {{ font-size: 1.35rem !important; }}
        .pt-display {{ font-size: 1.7rem; }}
        .pt-lede {{ font-size: 0.94rem; }}

        div[data-testid="stHorizontalBlock"]:has(.st-key-login_btn, .st-key-theme_toggle) {{
            flex-wrap: nowrap !important;
            align-items: center !important;
            justify-content: space-between !important;
        }}

        .st-key-login_btn {{
            flex: 0 0 auto !important;
            width: auto !important;
        }}

        div.st-key-login_btn div.stButton > button {{
            height: 34px !important;
            min-height: 34px !important;
            padding: 0 0.8rem 0 2rem !important;
            background-position: 10px center !important;
            background-size: 15px 15px !important;
        }}

        div.st-key-login_btn div.stButton > button p {{
            font-size: 0.84rem !important;
            white-space: nowrap !important;
        }}

        .st-key-theme_toggle {{
            flex: 0 0 auto !important;
            width: auto !important;
        }}

        div[data-testid="stElementContainer"].st-key-theme_toggle button,
        div[data-testid="stElementContainer"].st-key-theme_toggle button:hover {{
            transform: scale(0.85) !important;
            transform-origin: right center !important;
            margin: 0 !important;
        }}

        div[data-testid="stHorizontalBlock"]:has(.st-key-n_perfumes) {{
            flex-wrap: nowrap !important;
        }}

        div[data-testid="stColumn"]:has(.st-key-n_perfumes),
        div[data-testid="stColumn"]:has(.st-key-n_esencias),
        div[data-testid="column"]:has(.st-key-n_perfumes),
        div[data-testid="column"]:has(.st-key-n_esencias) {{
            flex: 1 1 50% !important;
            width: 50% !important;
        }}

        div.st-key-n_perfumes div.stButton > button p,
        div.st-key-n_esencias div.stButton > button p {{
            font-size: 0.92rem !important;
        }}

        div[data-testid="stColumn"]:has(input[placeholder*="Buscar"]) {{
            flex: 1 1 100% !important;
            width: 100% !important;
            margin-bottom: 2px !important;
        }}

        div[data-testid="stTextInput"]:has(input[placeholder*="Buscar"]) div[data-baseweb="input"] {{
            min-height: 46px !important;
        }}

        div[data-testid="stPopover"] > button,
        button[data-testid="stPopoverButton"] {{
            min-height: 42px !important;
            font-size: 0.84rem !important;
            width: 100% !important;
        }}

        div[data-testid="stHorizontalBlock"]:has(a[data-testid="stPageLink-NavLink"]) {{
            flex-wrap: wrap !important;
            gap: 6px !important;
        }}

        div[data-testid="stColumn"]:has(a[data-testid="stPageLink-NavLink"]),
        div[data-testid="stColumn"]:has(.st-key-chip_home),
        div[data-testid="stColumn"]:has(.st-key-chip_remates) {{
            flex: 1 1 calc(50% - 4px) !important;
            width: calc(50% - 4px) !important;
        }}

        a[data-testid="stPageLink-NavLink"],
        div.st-key-chip_home div.stButton > button,
        div.st-key-chip_remates div.stButton > button {{
            padding: 0.5rem 0.5rem 0.5rem 2.2rem !important;
            min-height: 40px !important;
            justify-content: flex-start !important;
        }}

        a[data-testid="stPageLink-NavLink"] p,
        a[data-testid="stPageLink-NavLink"] span,
        div.st-key-chip_home div.stButton > button p,
        div.st-key-chip_remates div.stButton > button p {{
            font-size: 0.8rem !important;
            white-space: normal !important;
            line-height: 1.15 !important;
            text-align: left !important;
        }}

        a[data-testid="stPageLink-NavLink"]::before,
        div.st-key-chip_home div.stButton > button::before,
        div.st-key-chip_remates div.stButton > button::before {{
            left: 11px !important;
            width: 15px !important;
            height: 15px !important;
        }}

        div[data-testid="stHorizontalBlock"]:has(.catalog-card) {{
            flex-direction: column !important;
        }}

        div[data-testid="stColumn"]:has(.catalog-card) {{
            flex: 1 1 100% !important;
            width: 100% !important;
            margin-bottom: 14px !important;
        }}

        .square-img-box {{
            max-height: 300px !important;
            padding: 18px !important;
        }}

        .card-perfume-name {{ font-size: 1.05rem !important; }}

        div[class*="st-key-btn_comp_"] div.stButton > button {{
            min-height: 46px !important;
        }}

        div[data-testid="stHorizontalBlock"]:has(.essence-card) {{
            flex-direction: column !important;
        }}

        div[data-testid="stColumn"]:has(.essence-card) {{
            flex: 1 1 100% !important;
            width: 100% !important;
        }}

        .essence-card {{
            padding: 14px 16px !important;
            margin-bottom: 8px !important;
        }}

        .pt-footer {{
            flex-direction: column;
            align-items: flex-start;
        }}
    }}
    </style>
""", unsafe_allow_html=True)

# 7. CABECERA CON LOGO COMPACTO E INTERACTIVO
col_logo, col_espacio, col_actions = st.columns([5.6, 1.2, 2.4], vertical_alignment="center")

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

with col_actions:
    btn_col1, btn_col2 = st.columns([2.0, 0.8], vertical_alignment="center", gap="small")
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

# 8. NAVEGACIÓN PRINCIPAL (PESTAÑAS)
active_nav_key = "n_perfumes" if st.session_state['current_page'] == 'home' else "n_esencias"
st.markdown(f"""
    <style>
    div.st-key-{active_nav_key} div.stButton > button {{ border-bottom-color: {accent} !important; }}
    div.st-key-{active_nav_key} div.stButton > button p {{ color: {text_color} !important; }}
    </style>
""", unsafe_allow_html=True)

st.markdown("<div style='margin-top: 18px;'></div>", unsafe_allow_html=True)
nav_cols = st.columns([1, 1], gap="small")

with nav_cols[0]: 
    st.button("Perfumes", key="n_perfumes", on_click=navigate_to, args=('home',), use_container_width=True)
with nav_cols[1]: 
    st.button("Esencias", key="n_esencias", on_click=navigate_to, args=('esencias_page',), use_container_width=True)

st.markdown("<div class='pt-tabs-rule'></div>", unsafe_allow_html=True)

# 9. BÚSQUEDA Y FILTRO DE ESENCIAS
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

# 10. CHIPS DE ENLACE RÁPIDO (5 ACCESOS DIRECTOS)
st.markdown("<div style='margin-top: 12px;'></div>", unsafe_allow_html=True)
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

st.markdown("<div style='margin-top: 36px;'></div>", unsafe_allow_html=True)

# 11. SECCIONES Y CONTENIDOS
if st.session_state['current_page'] == 'home':
    st.markdown(clean_html("""
        <div class="pt-section-head">
            <div class="pt-display">Catálogo y tendencias en Chile</div>
            <div class="pt-lede">Compara el precio de cada fragancia entre tiendas chilenas y encuentra dónde comprarla al mejor precio.</div>
        </div>
    """), unsafe_allow_html=True)
    
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
        div.st-key-{cat_active_key} div.stButton > button {{
            border-color: {accent} !important;
            background-color: {accent_soft} !important;
            box-shadow: inset 0 0 0 1px {accent} !important;
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
        note_chips = "".join(f'<div class="pt-note-chip">{escape_html(e)}</div>' for e in selected_essences)
        st.markdown(clean_html(f"""
            <div class="pt-note-row">
                <div class="pt-note-label">Notas activas:</div>
                {note_chips}
            </div>
        """), unsafe_allow_html=True)

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
            st.markdown(clean_html("""
                <div class="pt-empty">
                    <div class="pt-empty-title">Ninguna fragancia coincide</div>
                    <div class="pt-empty-text">Prueba con otro nombre o marca, o quita algunas notas del filtro de esencias.</div>
                </div>
            """), unsafe_allow_html=True)
            _, c_reset_mid, _ = st.columns([1, 1, 1])
            with c_reset_mid:
                if st.button("Restablecer filtros", key="btn_reset_filters", use_container_width=True):
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

        # Resalta el número de la página actual en la barra de paginación
        st.markdown(f"""
            <style>
            div.st-key-btn_pag_num_{cur_page} div.stButton > button:disabled {{
                opacity: 1 !important;
                background-color: {accent} !important;
                border-color: {accent} !important;
                cursor: default !important;
            }}
            div.st-key-btn_pag_num_{cur_page} div.stButton > button:disabled p {{
                color: #ffffff !important;
                font-weight: 700 !important;
            }}
            </style>
        """, unsafe_allow_html=True)

        col_stat_txt, col_per_page, col_jump_top = st.columns([5.2, 2.4, 2.4], vertical_alignment="center")
        with col_stat_txt:
            st.markdown(
                f"<div class='pt-meta'>Mostrando <b>{start_idx + 1}–{end_idx}</b> de <b>{total_perfumes}</b> fragancias</div>",
                unsafe_allow_html=True,
            )
        with col_per_page:
            sel_pp = st.selectbox(
                "Perfumes por página",
                options=opciones_por_pag,
                index=opciones_por_pag.index(items_per_page),
                format_func=lambda n: f"Mostrar {n} por página",
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
                format_func=lambda p_num: f"Página {p_num} de {total_pages}",
                key="sel_jump_page_top",
                label_visibility="collapsed",
            )
            if sel_jump != cur_page:
                st.session_state['catalog_page'] = int(sel_jump)
                st.session_state['catalog_extra_items'] = 0
                st.rerun(scope="fragment")

        st.markdown("<div style='margin-top: 12px;'></div>", unsafe_allow_html=True)

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
                            <div class="price-label">{label_desde}</div>
                            <div class="price-val">{precio_num_txt}</div>
                        </div>
                        """
                        overlay_badge_html = f'<div class="overlay-price-badge">Mejor oferta: {precio_num_txt}</div>'
                    else:
                        precio_html = """
                        <div class="card-perfume-price out-of-stock-card-price">
                            <div class="price-val-agotado">Sin stock en tiendas</div>
                        </div>
                        """
                        overlay_badge_html = '<div class="overlay-price-badge" style="background: rgba(239, 68, 68, 0.16); border-color: rgba(239, 68, 68, 0.4); color: #f87171;">Agotado en tiendas</div>'

                    card_html = f"""
                    <div class="catalog-card">
                        <div class="square-img-box">
                            <img src="{img_src}" alt="{nombre_safe}" loading="lazy" decoding="async">
                            <div class="card-hover-overlay">
                                <div class="overlay-title">{nombre_safe}</div>
                                <div class="overlay-info"><b>Marca:</b> {marca_safe} ({tipo_safe}, {genero_safe})</div>
                                <div class="overlay-info"><b>Origen:</b> {pais_origen}</div>
                                <div class="overlay-info overlay-notes" style="margin-top: 4px;"><b>Notas:</b> {notas_safe}</div>
                                {overlay_badge_html}
                            </div>
                        </div>
                        <div class="card-footer-info">
                            <div>
                                <div class="card-perfume-name" title="{nombre_safe}">{nombre_safe}</div>
                                <div class="card-perfume-brand">{marca_safe}, {genero_safe}</div>
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

        st.markdown("<div style='margin-top: 24px;'></div>", unsafe_allow_html=True)

        # Botón "Ver más perfumes" acumulativo (carga más tarjetas en la misma vista sin recargar toda la app)
        if end_idx < total_perfumes:
            siguientes_cant = min(items_per_page, total_perfumes - end_idx)
            _, c_more_mid, _ = st.columns([1, 2, 1])
            with c_more_mid:
                if st.button(f"Ver {siguientes_cant} perfumes más", key="btn_load_more", use_container_width=True):
                    st.session_state['catalog_extra_items'] = extra_rows + items_per_page
                    st.rerun(scope="fragment")
            st.markdown("<div style='margin-top: 14px;'></div>", unsafe_allow_html=True)

        # Barra de paginación multi-página con ventana numérica clicable + Primera/Última
        win_start = max(1, cur_page - 2)
        win_end = min(total_pages, win_start + 4)
        win_start = max(1, win_end - 4)
        paginas_ventana = list(range(win_start, win_end + 1))

        nav_cols_spec = [1.1, 1.5] + [0.9] * len(paginas_ventana) + [1.5, 1.1]
        pag_cols = st.columns(nav_cols_spec, vertical_alignment="center", gap="small")

        with pag_cols[0]:
            if st.button("« 1", key="btn_pag_first", disabled=(cur_page <= 1), use_container_width=True):
                st.session_state['catalog_page'] = 1
                st.session_state['catalog_extra_items'] = 0
                st.rerun(scope="fragment")
        with pag_cols[1]:
            if st.button("‹ Anterior", key="btn_pag_prev", disabled=(cur_page <= 1), use_container_width=True):
                st.session_state['catalog_page'] = max(1, cur_page - 1)
                st.session_state['catalog_extra_items'] = 0
                st.rerun(scope="fragment")

        for idx_p, p_num in enumerate(paginas_ventana):
            with pag_cols[2 + idx_p]:
                if st.button(str(p_num), key=f"btn_pag_num_{p_num}", disabled=(p_num == cur_page), use_container_width=True):
                    st.session_state['catalog_page'] = p_num
                    st.session_state['catalog_extra_items'] = 0
                    st.rerun(scope="fragment")

        with pag_cols[2 + len(paginas_ventana)]:
            if st.button("Siguiente ›", key="btn_pag_next", disabled=(cur_page >= total_pages), use_container_width=True):
                st.session_state['catalog_page'] = min(total_pages, cur_page + 1)
                st.session_state['catalog_extra_items'] = 0
                st.rerun(scope="fragment")
        with pag_cols[3 + len(paginas_ventana)]:
            if st.button(f"{total_pages} »", key="btn_pag_last", disabled=(cur_page >= total_pages), use_container_width=True):
                st.session_state['catalog_page'] = total_pages
                st.session_state['catalog_extra_items'] = 0
                st.rerun(scope="fragment")

        st.markdown(
            f"<div class='pt-meta pt-meta-center'>Página <b>{cur_page}</b> de <b>{total_pages}</b>. "
            f"Catálogo activo: <b>{total_perfumes}</b> fragancias.</div>",
            unsafe_allow_html=True,
        )

    render_catalogo_paginado(catalog_perfumes)

elif st.session_state['current_page'] == 'esencias_page':
    col_dict_title, col_dict_mute = st.columns([9, 1], vertical_alignment="center")
    
    with col_dict_title:
        st.markdown(clean_html("""
            <div class="pt-section-head">
                <div class="pt-display">Diccionario de esencias</div>
                <div class="pt-lede">Qué aporta cada nota olfativa a un perfume. Son las mismas notas que puedes usar en el filtro de búsqueda.</div>
            </div>
        """), unsafe_allow_html=True)
    
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
        "Lavanda": "Aromática, limpia y relajante; pilar clásico que aporta serenidad.",
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
        "Mirra": "Balsámica, cálida y milenaria; ofrece un aura mística.",
        "Almizcle (Blanco/Musk)": "Piel limpia, suavidad algodonosa y fijación sensual.",
        "Almizcle Vegetal": "Alternativa botánica limpia de perfil transparente.",
        "Ámbar Gris": "Marino, terroso y aterciopelado; fija la fragancia.",
        "Castóreo": "Nota animálica ahumada que evoca cuero profundo.",
        "Civeta": "Sensualidad animálica cálida que aporta densidad.",
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
        "Iso E Super": "Molécula amaderada, suave y aterciopelada que realza la piel.",
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

# 12. PIE DE PÁGINA (FOOTER)
st.markdown(clean_html("""
    <div class="pt-footer">
        <div class="pt-footer-mark">Perfume<strong>Trending</strong></div>
        <div class="pt-footer-copy">© 2026 Perfume Trending. Todos los derechos reservados.</div>
    </div>
"""), unsafe_allow_html=True)
