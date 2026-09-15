import streamlit as st
import streamlit.components.v1 as components
import pandas as pd

# 1. CONFIGURACIÓN DE LA PÁGINA Y ESTADO
st.set_page_config(page_title="PerfumeTrending", layout="wide", initial_sidebar_state="collapsed")

if 'current_page' not in st.session_state:
    st.session_state['current_page'] = 'home'
if 'theme' not in st.session_state:
    st.session_state['theme'] = 'dark'
if 'selected_perfume' not in st.session_state:
    st.session_state['selected_perfume'] = None

def toggle_theme():
    st.session_state['theme'] = 'dark' if st.session_state['theme'] == 'light' else 'light'

def navigate_to(page, perfume_data=None):
    st.session_state['current_page'] = page
    if perfume_data:
        st.session_state['selected_perfume'] = perfume_data

is_dark = st.session_state['theme'] == 'dark'

# Colores generales
app_bg_css = "background-color: #0c0e12 !important;" if is_dark else "background-color: #f9f9fb !important;"
text_color = "#f0f0f0" if is_dark else "#18181b"
subtext_color = "#888890" if is_dark else "#666670"

btn_bg = "#161920" if is_dark else "#ffffff"
btn_text = "#e0e0e0" if is_dark else "#18181b"
btn_border = "#2a2e39" if is_dark else "#e2e2e8"

input_bg = "#14171d" if is_dark else "#ffffff"
input_text = "#f0f0f0" if is_dark else "#18181b"
input_border = "#2a2e39" if is_dark else "#e2e2e8"

# Posicionamiento del Switch de Tema (Tamaño normal)
bottle_left_pos = "36px" if is_dark else "-2px"
static_icon_pos = "10px center" if is_dark else "calc(100% - 10px) center"

static_icon_svg = (
    "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23ffffff' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><circle cx='12' cy='12' r='4'/><line x1='12' y1='1' x2='12' y2='3'/><line x1='12' y1='21' x2='12' y2='23'/><line x1='4.22' y1='4.22' x2='5.64' y2='5.64'/><line x1='18.36' y1='18.36' x2='19.78' y2='19.78'/><line x1='1' y1='12' x2='3' y2='12'/><line x1='21' y1='12' x2='23' y2='12'/><line x1='4.22' y1='19.78' x2='5.64' y2='18.36'/><line x1='18.36' y1='5.64' x2='19.78' y2='4.22'/></svg>"
    if is_dark else
    "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%231a1a1a' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z'/></svg>"
)

bottle_svg = (
    "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 50 58'><rect x='18' y='2' width='14' height='7' rx='2' fill='%23ffffff' stroke='%23111111' stroke-width='2.5'/><rect x='21' y='9' width='8' height='5' fill='%23ffffff' stroke='%23111111' stroke-width='2.5'/><circle cx='25' cy='34' r='19' fill='%23ffffff' stroke='%23111111' stroke-width='2.5'/><path d='M21 28a8 8 0 0 0 9 10.5 8.5 8.5 0 0 1-9-10.5z' fill='none' stroke='%23111111' stroke-width='2.2' stroke-linecap='round' stroke-linejoin='round'/></svg>"
    if is_dark else
    "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 50 58'><rect x='18' y='2' width='14' height='7' rx='2' fill='%23ffffff' stroke='%23111111' stroke-width='2.5'/><rect x='21' y='9' width='8' height='5' fill='%23ffffff' stroke='%23111111' stroke-width='2.5'/><circle cx='25' cy='34' r='19' fill='%23ffffff' stroke='%23111111' stroke-width='2.5'/><circle cx='25' cy='34' r='5' fill='none' stroke='%23111111' stroke-width='2'/><line x1='25' y1='23' x2='25' y2='26' stroke='%23111111' stroke-width='2' stroke-linecap='round'/><line x1='25' y1='42' x2='25' y2='45' stroke='%23111111' stroke-width='2' stroke-linecap='round'/><line x1='14' y1='34' x2='17' y2='34' stroke='%23111111' stroke-width='2' stroke-linecap='round'/><line x1='33' y1='34' x2='36' y2='34' stroke='%23111111' stroke-width='2' stroke-linecap='round'/><line x1='17' y1='26' x2='19' y2='28' stroke='%23111111' stroke-width='2' stroke-linecap='round'/><line x1='31' y1='40' x2='33' y2='42' stroke='%23111111' stroke-width='2' stroke-linecap='round'/><line x1='17' y1='42' x2='19' y2='40' stroke='%23111111' stroke-width='2' stroke-linecap='round'/><line x1='31' y1='28' x2='33' y2='26' stroke='%23111111' stroke-width='2' stroke-linecap='round'/></svg>"
)

camera_icon_svg = f"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23{text_color[1:]}' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z'/><circle cx='12' cy='13' r='4'/></svg>"

# 2. SCRIPT DE COLORES COMPACTO
js_color_script = f"""
<script>
(function() {{
    const doc = window.parent.document;
    const isDark = {str(is_dark).lower()};
    
    const colorRules = [
        {{ keywords: ['sangre', 'cereza', 'frambuesa', 'pimienta rosa', 'rosa', 'ruibarbo', 'lichi', 'ciruela', 'grosella', 'grosellas', 'peonía', 'geranio'], 
          bg: isDark ? '#3d1a1e' : '#f7eaec', border: isDark ? '#5c282e' : '#e2b3b7', text: isDark ? '#f0adb4' : '#5c1b22' }},
        {{ keywords: ['marina', 'marinas', 'agua', 'océano', 'mar', 'ozónica', 'ozónicas'], 
          bg: isDark ? '#152933' : '#eaf2f7', border: isDark ? '#224052' : '#a8c7da', text: isDark ? '#92ccdb' : '#173a4b' }},
        {{ keywords: ['albahaca', 'bergamota', 'cardamomo', 'higo', 'manzana', 'menta', 'pachulí', 'pera', 'romero', 'salvia', 'té verde', 'té blanco', 'vetiver', 'abedul', 'eucalipto', 'gálbano', 'hojas de violeta'], 
          bg: isDark ? '#162b1e' : '#ebf5ee', border: isDark ? '#234530' : '#a4cca2', text: isDark ? '#93d1a3' : '#193d25' }},
        {{ keywords: ['iris', 'lavanda', 'jazmín', 'nardos', 'neroli', 'violeta', 'fresia', 'heliotropo', 'mimosa', 'lila', 'magnolia', 'azahar', 'frangipani', 'gardenia', 'ylang'], 
          bg: isDark ? '#2b1d33' : '#f2ebf7', border: isDark ? '#432d52' : '#c3b1d4', text: isDark ? '#c7a9db' : '#391c47' }},
        {{ keywords: ['caramelo', 'miel', 'solares', 'vainilla', 'cacao', 'café', 'canela', 'tonka', 'nuez moscada', 'praliné', 'haba tonka', 'almendra', 'avellana', 'leche', 'malvavisco', 'chocolate', 'ron', 'cognac', 'whisky'], 
          bg: isDark ? '#332115' : '#f7ede6', border: isDark ? '#523522' : '#d8bca7', text: isDark ? '#dbb193' : '#452914' }},
        {{ keywords: ['ámbar gris', 'cedro', 'sándalo', 'tabaco', 'cuero', 'oud', 'incienso', 'ciprés', 'ébano', 'guayac', 'musgo', 'estoraque', 'ládano', 'benjuí'], 
          bg: isDark ? '#23272e' : '#edeef0', border: isDark ? '#373d47' : '#bdc1c9', text: isDark ? '#aeb5c2' : '#292e36' }},
        {{ keywords: ['azafrán', 'ámbar', 'mandarina', 'melocotón', 'durazno', 'mirra', 'naranjo', 'pomelo', 'cítrico', 'cítricos', 'limón', 'lima', 'clementina', 'yuzu', 'petit grain', 'piña', 'jengibre'], 
          bg: isDark ? '#382013' : '#f9ede6', border: isDark ? '#59331e' : '#debca8', text: isDark ? '#dfab8c' : '#4f2711' }},
        {{ keywords: ['almizcle', 'coco', 'civeta', 'castóreo', 'pimienta blanca', 'pimienta negra', 'iso e super', 'ambroxan', 'aldehídos', 'cachemira'], 
          bg: isDark ? '#1f2228' : '#f2f4f7', border: isDark ? '#333842' : '#cad0d9', text: isDark ? '#bcc2cc' : '#2b3038' }}
    ];

    function applyEssenceColors() {{
        const targets = doc.querySelectorAll('li[role="option"], div[role="option"], span[data-baseweb="tag"], div[data-baseweb="option"]');
        targets.forEach(el => {{
            if (el.dataset.colored === 'true') return;
            const text = (el.innerText || '').toLowerCase();
            if (!text) return;

            for (const rule of colorRules) {{
                if (rule.keywords.some(kw => text.includes(kw))) {{
                    el.style.backgroundColor = rule.bg;
                    el.style.border = '1px solid ' + rule.border;
                    el.style.color = rule.text; 
                    el.style.borderRadius = '3px';
                    el.style.padding = '2px 6px';
                    el.style.margin = '1px 0';
                    el.style.fontSize = '0.72rem';
                    el.dataset.colored = 'true';
                    el.querySelectorAll('*').forEach(child => {{ child.style.color = rule.text; }});
                    break;
                }}
            }}
        }});
    }}

    const observer = new MutationObserver(() => applyEssenceColors());
    observer.observe(doc.body, {{ childList: true, subtree: true }});
    applyEssenceColors();
}})();
</script>
"""

components.html(js_color_script, height=0, width=0)

# 3. CSS ULTRA MINIMALISTA CON ZOOM GLOBAL (+10%)
st.markdown(f"""
    <style>
    /* ZOOM GLOBAL DEL 10% A TODA LA PÁGINA */
    html, body, .stApp {{
        zoom: 1.1;
    }}

    header[data-testid="stHeader"] {{ display: none !important; }}
    
    /* Reducción de márgenes globales de la página */
    .block-container {{ 
        padding-top: 0.8rem !important; 
        padding-bottom: 1.5rem !important; 
        max-width: 1100px !important;
    }}
    
    .stApp {{ {app_bg_css} color: {text_color} !important; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }}

    .stApp p, .stApp span, .stApp label, .stMarkdown p {{
        color: {text_color} !important;
        font-size: 0.82rem !important;
    }}

    /* EFECTO MINI-ZOOM SUTIL Y SOBERANO PARA BOTONES */
    div.stButton > button,
    div.stDownloadButton > button,
    div[data-testid="stPopover"] > button,
    button[data-testid="stPopoverButton"],
    .st-key-btn_photo_search button,
    .st-key-login_btn button,
    .st-key-theme_toggle button {{
        transition: transform 0.15s ease, background-color 0.15s ease, border-color 0.15s ease !important;
        will-change: transform;
        min-height: 0px !important;
        height: auto !important;
    }}

    div.stButton > button:hover,
    div[data-testid="stPopover"] > button:hover,
    button[data-testid="stPopoverButton"]:hover,
    .st-key-btn_photo_search button:hover,
    .st-key-login_btn button:hover {{
        transform: translateY(-1px) !important;
        cursor: pointer !important;
    }}

    /* NAVEGACIÓN PRINCIPAL (MINIMALISTA) */
    .st-key-n_perfumes button, 
    .st-key-n_remates button,
    .st-key-n_disenador button,
    .st-key-n_nicho button,
    .st-key-n_arabes button, 
    .st-key-n_esencias button {{
        background-color: transparent !important;
        border: none !important;
        border-bottom: 1px solid transparent !important;
        border-radius: 0px !important;
        font-weight: 500 !important;
        font-size: 0.72rem !important;
        padding: 0.15rem 0rem !important;
        box-shadow: none !important;
        letter-spacing: 0.8px !important;
    }}

    .st-key-n_perfumes button p, 
    .st-key-n_remates button p,
    .st-key-n_disenador button p,
    .st-key-n_nicho button p,
    .st-key-n_arabes button p, 
    .st-key-n_esencias button p {{
        color: {subtext_color} !important;
        white-space: nowrap !important;
        font-size: 0.72rem !important;
    }}

    .st-key-n_perfumes button:hover p, 
    .st-key-n_remates button:hover p,
    .st-key-n_disenador button:hover p,
    .st-key-n_nicho button:hover p,
    .st-key-n_arabes button:hover p, 
    .st-key-n_esencias button:hover p {{
        color: {text_color} !important;
    }}

    /* CHIPS Y HERRAMIENTAS RÁPIDAS COMPACTAS */
    .st-key-btn_trend button, 
    .st-key-btn_trust button, 
    .st-key-btn_compare button {{
        background-color: transparent !important;
        border: 1px solid {btn_border} !important;
        border-radius: 14px !important;
        padding: 0.1rem 0.5rem !important;
        box-shadow: none !important;
    }}
    
    .st-key-btn_trend button p, 
    .st-key-btn_trust button p, 
    .st-key-btn_compare button p {{
        font-size: 0.68rem !important;
        font-weight: 400 !important;
        color: {subtext_color} !important;
        letter-spacing: 0.2px;
    }}

    /* BOTÓN INGRESAR COMPACTO */
    .st-key-login_btn button {{
        background-color: {btn_bg} !important;
        color: {btn_text} !important;
        border: 1px solid {btn_border} !important;
        border-radius: 4px !important;
        padding: 0.2rem 0.6rem !important;
        font-size: 0.72rem !important;
    }}
    .st-key-login_btn button p {{
        font-size: 0.72rem !important;
    }}

    /* INPUTS Y SELECTS COMPACTOS */
    div[data-baseweb="input"],
    div[data-baseweb="base-input"],
    div[data-baseweb="select"] > div,
    div[data-testid="stPopover"] > button,
    button[data-testid="stPopoverButton"],
    button[data-testid="stBaseButton-secondary"] {{
        background-color: {input_bg} !important;
        border: 1px solid {input_border} !important;
        border-radius: 4px !important;
        box-shadow: none !important;
        padding-top: 2px !important;
        padding-bottom: 2px !important;
        min-height: 32px !important;
    }}

    div[data-baseweb="input"] input,
    div[data-baseweb="base-input"] input {{
        font-size: 0.78rem !important;
        padding: 4px 8px !important;
    }}

    div[data-baseweb="input"] input::placeholder {{
        color: {subtext_color} !important;
        font-size: 0.75rem !important;
    }}

    .st-key-btn_photo_search button {{
        background-color: {input_bg} !important;
        border: 1px solid {input_border} !important;
        border-radius: 4px !important;
        padding: 0.25rem 0.5rem 0.25rem 1.8rem !important;
        background-image: url("{camera_icon_svg}") !important;
        background-repeat: no-repeat !important;
        background-position: 8px center !important;
        background-size: 13px 13px !important;
        font-size: 0.75rem !important;
    }}
    
    .stApp .st-key-btn_photo_search button p {{
        font-size: 0.75rem !important;
        color: {text_color} !important;
    }}

    /* SWITCH DE TEMA REFINADO (TAMAÑO NORMAL) */
    .st-key-theme_toggle button {{
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
        width: 72px !important;
        height: 36px !important;
        position: relative !important;
        cursor: pointer !important;
        margin: 0 auto !important;
        display: block !important;
    }}

    .st-key-theme_toggle button * {{ display: none !important; }}
    
    .st-key-theme_toggle button::before {{
        content: '' !important;
        position: absolute !important;
        top: 3px !important; left: 0 !important;
        width: 68px !important; height: 30px !important;
        background-color: {"#1c1f26" if is_dark else "#eae8e6"} !important;
        border: 1px solid {btn_border} !important;
        border-radius: 15px !important;
        background-image: url("{static_icon_svg}") !important;
        background-repeat: no-repeat !important;
        background-position: {static_icon_pos} !important;
        background-size: 14px 14px !important;
    }}
    
    .st-key-theme_toggle button::after {{
        content: '' !important;
        position: absolute !important;
        top: -1px !important;
        left: {bottle_left_pos} !important;
        width: 34px !important; height: 38px !important;
        background-image: url("{bottle_svg}") !important;
        background-repeat: no-repeat !important;
        background-size: contain !important;
        transition: left 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
        z-index: 2 !important;
    }}

    /* TARJETAS DE CATÁLOGO COMPACTAS */
    .catalog-card {{
        background-color: transparent;
        border: 1px solid {btn_border};
        border-radius: 4px;
        overflow: hidden;
        position: relative;
        margin-bottom: 16px;
        transition: border-color 0.2s ease;
    }}
    .catalog-card:hover {{
        border-color: #7a6a5d;
    }}
    .square-img-box {{
        position: relative;
        width: 100%;
        aspect-ratio: 1 / 1;
        background-color: #ffffff;
        display: flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
        padding: 12px;
        box-sizing: border-box;
    }}
    .square-img-box img {{
        max-width: 100%;
        max-height: 100%;
        object-fit: contain;
    }}
    .card-hover-overlay {{
        position: absolute;
        top: 0; left: 0; right: 0; bottom: 0;
        background: rgba(12, 14, 18, 0.94);
        color: #ffffff;
        padding: 12px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        opacity: 0;
        transition: opacity 0.2s ease;
        text-align: left;
    }}
    .catalog-card:hover .card-hover-overlay {{ opacity: 1; }}
    .overlay-title {{
        font-size: 0.82rem;
        font-weight: 600;
        color: #d4c2a5;
        margin-bottom: 6px;
        border-bottom: 1px solid rgba(255,255,255,0.1);
        padding-bottom: 4px;
    }}
    .overlay-info {{ font-size: 0.7rem; font-weight: 300; line-height: 1.4; color: #b8b8b8; margin-bottom: 4px; }}
    .card-footer-info {{ padding: 8px 10px; text-align: center; background-color: {btn_bg}; }}
    .card-perfume-name {{ font-size: 0.78rem; font-weight: 500; color: {text_color}; margin-bottom: 2px; }}
    .card-perfume-brand {{ font-size: 0.65rem; font-weight: 300; color: {subtext_color}; text-transform: uppercase; letter-spacing: 0.5px; }}

    /* DICCIONARIO DE ESENCIAS COMPACTO */
    .essence-card {{ border-radius: 4px; padding: 10px 12px; margin-bottom: 8px; border-width: 1px; border-style: solid; }}
    .essence-title {{ font-size: 0.78rem; font-weight: 600; margin-bottom: 3px; letter-spacing: 0.3px; }}
    .essence-desc {{ font-size: 0.72rem; font-weight: 400; line-height: 1.35; opacity: 0.88; }}
    </style>
""", unsafe_allow_html=True)

# 4. CABECERA
col_logo, col_espacio, col_actions = st.columns([5, 2, 2.2], vertical_alignment="center")

with col_logo:
    logo_color = "#8c7b6d"
    logo_html = f"""
    <div style="display: flex; align-items: center; gap: 8px; cursor: pointer;" onclick="window.location.reload();">
        <svg width="24" height="24" viewBox="0 0 36 36" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path d="M 6.8 21 L 29.2 21 C 30 25 27 32 18 32 C 9 32 6 25 6.8 21 Z" fill="{logo_color}" />
            <line x1="6.8" y1="21" x2="29.2" y2="21" stroke="{text_color}" stroke-width="1.5" />
            <line x1="18" y1="10" x2="18" y2="30" stroke="{text_color}" stroke-width="1" />
            <path d="M 18 32 C 9 32 5 24 7.5 17 C 9 12 13 10 15 10 L 21 10 C 23 10 27 12 28.5 17 C 31 24 27 32 18 32 Z" stroke="{text_color}" stroke-width="2" />
            <rect x="15" y="7" width="6" height="3" stroke="{text_color}" stroke-width="1.5" />
            <rect x="13" y="3" width="10" height="4" rx="1" stroke="{text_color}" stroke-width="1.5" />
            <rect x="16" y="0" width="4" height="3" rx="1" fill="{logo_color}" stroke="{text_color}" stroke-width="1" />
        </svg>
        <span style="font-size: 1.05rem; color: {text_color}; letter-spacing: 0.5px;">
            <span style="font-weight: 300;">Perfume</span><span style="font-weight: 600;">Trending</span>
        </span>
    </div>
    """
    st.markdown(logo_html, unsafe_allow_html=True)

with col_actions:
    btn_col1, btn_col2 = st.columns([1.3, 1], vertical_alignment="center")
    with btn_col1:
        st.button("Ingresar", key="login_btn", use_container_width=True)
    with btn_col2:
        st.button(" ", key="theme_toggle", on_click=toggle_theme)

# 5. NAVEGACIÓN
st.markdown("<div style='margin-top: 8px;'></div>", unsafe_allow_html=True)
nav_cols = st.columns([1, 1, 1, 1, 1, 1], vertical_alignment="center")

with nav_cols[0]: st.button("PERFUMES", key="n_perfumes", on_click=navigate_to, args=('home',), use_container_width=True)
with nav_cols[1]: st.button("REMATES", key="n_remates", on_click=navigate_to, args=('hype',), use_container_width=True)
with nav_cols[2]: st.button("DISEÑADOR", key="n_disenador", on_click=navigate_to, args=('home',), use_container_width=True)
with nav_cols[3]: st.button("NICHO", key="n_nicho", on_click=navigate_to, args=('home',), use_container_width=True)
with nav_cols[4]: st.button("ÁRABES", key="n_arabes", on_click=navigate_to, args=('home',), use_container_width=True)
with nav_cols[5]: st.button("ESENCIAS", key="n_esencias", on_click=navigate_to, args=('esencias_page',), use_container_width=True)

st.markdown(f"<hr style='margin: 4px 0 16px 0; border: none; border-bottom: 1px solid {btn_border}; opacity: 0.3;'>", unsafe_allow_html=True)

# 6. BÚSQUEDA Y SELECCIÓN DE ESENCIAS
col_search, col_filter, col_separator, col_photo = st.columns([5.5, 1.8, 0.1, 2.0], vertical_alignment="center")

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

with col_separator:
    st.markdown(f"<div style='border-left: 1px solid {btn_border}; height: 24px; margin: auto;'></div>", unsafe_allow_html=True)

with col_photo:
    st.button("Búsqueda visual", key="btn_photo_search", help="Buscar por imagen", use_container_width=True)

# 7. CHIPS DE NAVEGACIÓN RÁPIDA
st.markdown("<div style='margin-top: 8px;'></div>", unsafe_allow_html=True)
col_chip1, col_chip2, col_chip3, col_chip_space = st.columns([1.2, 1.4, 1.3, 5.5], vertical_alignment="center")

with col_chip1:
    if st.button("Trend Del Hype", key="btn_trend", use_container_width=True):
        st.switch_page("pages/trendhype.py")
with col_chip2:
    st.button("Páginas de Confianza", key="btn_trust", on_click=navigate_to, args=('trust_page',), use_container_width=True)
with col_chip3:
    st.button("Comparar Precios", key="btn_compare", on_click=navigate_to, args=('compare_page',), use_container_width=True)

st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

# 8. VISTAS DE PÁGINA
if st.session_state['current_page'] == 'home':
    st.markdown(f"<div style='text-align: center; margin-bottom: 20px; color: {text_color}; letter-spacing: 1.5px; font-weight: 300; font-size: 0.95rem; text-transform: uppercase;'>CATÁLOGO Y TENDENCIAS</div>", unsafe_allow_html=True)
    
    if selected_essences:
        st.write(f"**Filtro activo:** {', '.join(selected_essences)}")

    catalog_perfumes = [
        {
            "name": "Bleu de Chanel",
            "brand": "Chanel",
            "country": "Francia 🇫🇷",
            "perfumer": "Jacques Polge",
            "notes": "Toronja, Limón, Menta, Jengibre, Incienso, Cedro, Sándalo",
            "img": "https://m.media-amazon.com/images/I/71R2e1U3JYL._SL1500_.jpg"
        },
        {
            "name": "Sauvage Elixir",
            "brand": "Dior",
            "country": "Francia 🇫🇷",
            "perfumer": "François Demachy",
            "notes": "Canela, Nuez Moscada, Lavanda, Regaliz, Sándalo, Ámbar",
            "img": "https://m.media-amazon.com/images/I/71xSg5Wf0-L._SL1500_.jpg"
        },
        {
            "name": "Baccarat Rouge 540",
            "brand": "Maison Francis Kurkdjian",
            "country": "Francia 🇫🇷",
            "perfumer": "Francis Kurkdjian",
            "notes": "Azafrán, Jazmín, Ámbar Gris, Madera de Cedro, Resina de Abeto",
            "img": "https://m.media-amazon.com/images/I/61yD-8sK6yL._SL1500_.jpg"
        },
        {
            "name": "Club de Nuit Intense",
            "brand": "Armaf",
            "country": "Emiratos Árabes 🇦🇪",
            "perfumer": "Christian Provenzano",
            "notes": "Limón, Piña, Grosellas Negras, Abedul, Jazmín, Almizcle",
            "img": "https://m.media-amazon.com/images/I/61Yg40gX3mL._SL1500_.jpg"
        },
        {
            "name": "Angels' Share",
            "brand": "Kilian",
            "country": "Francia 🇫🇷",
            "perfumer": "Benoist Lapouza",
            "notes": "Cognac, Canela, Haba Tonka, Roble, Vainilla, Sándalo, Praliné",
            "img": "https://m.media-amazon.com/images/I/61sN52z4wEL._SL1500_.jpg"
        },
        {
            "name": "YSL Libre EDP",
            "brand": "Yves Saint Laurent",
            "country": "Francia 🇫🇷",
            "perfumer": "Anne Flipo & Carlos Benaïm",
            "notes": "Lavanda, Mandarina, Grosellas Negras, Flor de Azahar, Vainilla",
            "img": "https://m.media-amazon.com/images/I/61A+-0V2VFL._SL1500_.jpg"
        }
    ]

    cols_per_row = 3
    for i in range(0, len(catalog_perfumes), cols_per_row):
        cols = st.columns(cols_per_row, gap="medium")
        for j in range(cols_per_row):
            if i + j < len(catalog_perfumes):
                p = catalog_perfumes[i + j]
                card_html = f"""
                <div class="catalog-card">
                    <div class="square-img-box">
                        <img src="{p['img']}" alt="{p['name']}" referrerpolicy="no-referrer">
                        <div class="card-hover-overlay">
                            <div class="overlay-title">{p['name']}</div>
                            <div class="overlay-info"><b>Orígenes:</b> {p['country']}</div>
                            <div class="overlay-info"><b>Perfumista:</b> {p['perfumer']}</div>
                            <div class="overlay-info" style="margin-top: 4px;"><b>Notas:</b> {p['notes']}</div>
                        </div>
                    </div>
                    <div class="card-footer-info">
                        <div class="card-perfume-name">{p['name']}</div>
                        <div class="card-perfume-brand">{p['brand']}</div>
                    </div>
                </div>
                """
                with cols[j]:
                    st.markdown(card_html, unsafe_allow_html=True)

elif st.session_state['current_page'] == 'esencias_page':
    st.markdown(f"<div style='text-align: center; color: {text_color}; letter-spacing: 1px; font-weight: 300; margin-bottom: 20px; font-size: 0.95rem; text-transform: uppercase;'>DICCIONARIO DE ESENCIAS Y NOTAS</div>", unsafe_allow_html=True)
    
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
        "Melón": "Acuoso, frutal y dulce; aporta un perfil estival muy refrescante.",
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
        "Iso E Super": "Molécula maderosa, suave y aterciopelada.",
        "Notas Marinas": "Brisa salada y aire ozónico; aportan frescura oceánica.",
        "Notas Solares": "Calidez de la piel bajo el sol y tardes de verano.",
        "Sangre (Metálica)": "Nota vanguardista nicho; evoca hierro y un matiz salado."
    }

    esencias_dict = []
    for note in all_notes:
        border_col, bg_col, text_c = get_essence_colors(note)
        desc = essence_descriptions.get(note, "Nota olfativa distintiva que aporta carácter y equilibrio.")
        esencias_dict.append({
            "title": note,
            "color_border": border_col,
            "color_bg": bg_col,
            "color_text": text_c,
            "desc": desc
        })

    col_es_1, col_es_2 = st.columns(2, gap="medium")
    
    for i, item in enumerate(esencias_dict):
        tarjeta_html = f"""
        <div class="essence-card" style="border-color: {item['color_border']}; background-color: {item['color_bg']}; color: {item['color_text']};">
            <div class="essence-title" style="color: {item['color_text']} !important;">{item['title']}</div>
            <div class="essence-desc" style="color: {item['color_text']} !important;">{item['desc']}</div>
        </div>
        """
        if i % 2 == 0:
            with col_es_1:
                st.markdown(tarjeta_html, unsafe_allow_html=True)
        else:
            with col_es_2:
                st.markdown(tarjeta_html, unsafe_allow_html=True)

elif st.session_state['current_page'] == 'trust_page':
    st.markdown(f"<div style='text-align: center; color: {text_color}; font-weight: 300; font-size: 0.9rem;'>Páginas de Confianza (Próximamente)</div>", unsafe_allow_html=True)
elif st.session_state['current_page'] == 'compare_page':
    st.markdown(f"<div style='text-align: center; color: {text_color}; font-weight: 300; font-size: 0.9rem;'>Comparador de Precios (Próximamente)</div>", unsafe_allow_html=True)
