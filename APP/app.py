import streamlit as st
import pandas as pd

# 1. CONFIGURACIÓN DE LA PÁGINA Y CSS CUSTOM 
st.set_page_config(page_title="PerfumeTrending", layout="wide", initial_sidebar_state="collapsed")

# 2. MANEJO DE ESTADO (Navegación y Tema)
if 'current_page' not in st.session_state:
    st.session_state['current_page'] = 'home'
if 'theme' not in st.session_state:
    st.session_state['theme'] = 'light'
if 'selected_perfume' not in st.session_state:
    st.session_state['selected_perfume'] = None

def toggle_theme():
    st.session_state['theme'] = 'dark' if st.session_state['theme'] == 'light' else 'light'

def navigate_to(page, perfume_data=None):
    st.session_state['current_page'] = page
    if perfume_data:
        st.session_state['selected_perfume'] = perfume_data

is_dark = st.session_state['theme'] == 'dark'

app_bg_css = "background-color: #f6efe9 !important;" if not is_dark else "background-color: #0e1117 !important;"
text_color = "#ffffff" if is_dark else "#1a1a1a"
subtext_color = "#a0a0a0" if is_dark else "#666666"

btn_bg = "#1f242d" if is_dark else "#ffffff"
btn_text = "#ffffff" if is_dark else "#2c2c2c"
btn_border = "#3a3f4d" if is_dark else "#d4cdc5"
btn_hover_bg = "#2d3340" if is_dark else "#fcfaf8"

input_bg = "#1f242d" if is_dark else "#252b36"
input_text = "#ffffff" if is_dark else "#ffffff"
input_border = "#3a3f4d" if is_dark else "#1a1a1a"

bottle_left_pos = "42px" if is_dark else "-2px"
static_icon_pos = "12px center" if is_dark else "calc(100% - 12px) center"

static_icon_svg = (
    "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23ffffff' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><circle cx='12' cy='12' r='4'/><line x1='12' y1='1' x2='12' y2='3'/><line x1='12' y1='21' x2='12' y2='23'/><line x1='4.22' y1='4.22' x2='5.64' y2='5.64'/><line x1='18.36' y1='18.36' x2='19.78' y2='19.78'/><line x1='1' y1='12' x2='3' y2='12'/><line x1='21' y1='12' x2='23' y2='12'/><line x1='4.22' y1='19.78' x2='5.64' y2='18.36'/><line x1='18.36' y1='5.64' x2='19.78' y2='4.22'/></svg>"
    if is_dark else
    "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23ffffff' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z'/></svg>"
)

bottle_svg = (
    "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 50 58'><rect x='18' y='2' width='14' height='7' rx='2' fill='%23ffffff' stroke='%23111111' stroke-width='2.5'/><rect x='21' y='9' width='8' height='5' fill='%23ffffff' stroke='%23111111' stroke-width='2.5'/><circle cx='25' cy='34' r='19' fill='%23ffffff' stroke='%23111111' stroke-width='2.5'/><path d='M21 28a8 8 0 0 0 9 10.5 8.5 8.5 0 0 1-9-10.5z' fill='none' stroke='%23111111' stroke-width='2.2' stroke-linecap='round' stroke-linejoin='round'/></svg>"
    if is_dark else
    "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 50 58'><rect x='18' y='2' width='14' height='7' rx='2' fill='%23ffffff' stroke='%23111111' stroke-width='2.5'/><rect x='21' y='9' width='8' height='5' fill='%23ffffff' stroke='%23111111' stroke-width='2.5'/><circle cx='25' cy='34' r='19' fill='%23ffffff' stroke='%23111111' stroke-width='2.5'/><circle cx='25' cy='34' r='5' fill='none' stroke='%23111111' stroke-width='2'/><line x1='25' y1='23' x2='25' y2='26' stroke='%23111111' stroke-width='2' stroke-linecap='round'/><line x1='25' y1='42' x2='25' y2='45' stroke='%23111111' stroke-width='2' stroke-linecap='round'/><line x1='14' y1='34' x2='17' y2='34' stroke='%23111111' stroke-width='2' stroke-linecap='round'/><line x1='33' y1='34' x2='36' y2='34' stroke='%23111111' stroke-width='2' stroke-linecap='round'/><line x1='17' y1='26' x2='19' y2='28' stroke='%23111111' stroke-width='2' stroke-linecap='round'/><line x1='31' y1='40' x2='33' y2='42' stroke='%23111111' stroke-width='2' stroke-linecap='round'/><line x1='17' y1='42' x2='19' y2='40' stroke='%23111111' stroke-width='2' stroke-linecap='round'/><line x1='31' y1='28' x2='33' y2='26' stroke='%23111111' stroke-width='2' stroke-linecap='round'/></svg>"
)

# Icono de cámara genérico y limpio (estilo réflex/compacta)
camera_icon_svg = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23ffffff' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z'/><circle cx='12' cy='13' r='4'/></svg>"

st.markdown(f"""
    <style>
    header[data-testid="stHeader"] {{ display: none !important; }}
    .block-container {{ padding-top: 1.5rem !important; padding-bottom: 2rem !important; }}
    .stApp {{ {app_bg_css} color: {text_color} !important; }}

    .stApp p, .stApp span, .stApp label, .stMarkdown p, .stTextInput label p, .stMultiSelect label p {{
        color: {text_color} !important;
    }}

    /* NAVEGACIÓN PRINCIPAL SUPERIOR (ESTILO PESTAÑAS / TABS) */
    .st-key-n_perfumes button, 
    .st-key-n_arabes button, 
    .st-key-n_marcas button, 
    .st-key-n_remates button {{
        background-color: transparent !important;
        border: none !important;
        border-bottom: 2px solid transparent !important;
        border-radius: 0px !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
        padding: 0.4rem 0.2rem !important;
        box-shadow: none !important;
    }}

    .st-key-n_perfumes button p, 
    .st-key-n_arabes button p, 
    .st-key-n_marcas button p, 
    .st-key-n_remates button p {{
        color: {text_color} !important;
        white-space: nowrap !important;
    }}

    .st-key-n_perfumes button:hover, 
    .st-key-n_arabes button:hover, 
    .st-key-n_marcas button:hover, 
    .st-key-n_remates button:hover {{
        background-color: transparent !important;
        border-bottom: 2px solid #8c7b6d !important;
    }}

    .st-key-n_perfumes button:hover p, 
    .st-key-n_arabes button:hover p, 
    .st-key-n_marcas button:hover p, 
    .st-key-n_remates button:hover p {{
        color: #8c7b6d !important;
    }}

    /* HERRAMIENTAS RÁPIDAS (CHIPS DEBAJO DEL HERO SEARCH) */
    .st-key-btn_trend button, 
    .st-key-btn_trust button, 
    .st-key-btn_compare button {{
        background-color: transparent !important;
        border: 1px solid {btn_border} !important;
        border-radius: 16px !important;
        padding: 0.2rem 0.6rem !important;
        box-shadow: none !important;
    }}
    
    .st-key-btn_trend button p, 
    .st-key-btn_trust button p, 
    .st-key-btn_compare button p {{
        font-size: 0.8rem !important;
        font-weight: 500 !important;
        color: {subtext_color} !important;
    }}

    .st-key-btn_trend button:hover, 
    .st-key-btn_trust button:hover, 
    .st-key-btn_compare button:hover {{
        border-color: #8c7b6d !important;
        background-color: {btn_hover_bg} !important;
    }}
    
    .st-key-btn_trend button:hover p, 
    .st-key-btn_trust button:hover p, 
    .st-key-btn_compare button:hover p {{
        color: #8c7b6d !important;
    }}

    /* BOTÓN INGRESAR */
    .st-key-login_btn button {{
        background-color: {btn_bg} !important;
        color: {btn_text} !important;
        border: 1px solid {btn_border} !important;
        border-radius: 8px !important;
        font-weight: 500 !important;
    }}

    /* POPOVER ESENCIAS */
    div[data-testid="stPopover"] > button {{
        background-color: #1f242d !important;
        border: 1px solid #3a3f4d !important;
        border-radius: 8px !important;
        padding: 0.4rem 0.2rem !important;
    }}

    /* BOTÓN PHOTO SEARCH CON ÍCONO SVG GENÉRICO */
    .st-key-btn_photo_search button {{
        background-color: #1f242d !important;
        border: 1px solid #3a3f4d !important;
        border-radius: 8px !important;
        padding: 0.4rem 0.4rem 0.4rem 2.1rem !important;
        background-image: url("{camera_icon_svg}") !important;
        background-repeat: no-repeat !important;
        background-position: 10px center !important;
        background-size: 18px 18px !important;
    }}
    
    .stApp div[data-testid="stPopover"] button,
    .stApp div[data-testid="stPopover"] button p,
    .stApp div[data-testid="stPopover"] button span,
    .stApp div[data-testid="stPopover"] button div,
    .stApp .st-key-btn_photo_search button,
    .stApp .st-key-btn_photo_search button p,
    .stApp .st-key-btn_photo_search button span {{
        color: #ffffff !important;
        white-space: nowrap !important;
    }}

    div[data-testid="stPopover"] > button:hover,
    .st-key-btn_photo_search button:hover {{
        background-color: #2d3340 !important;
    }}

    /* INPUTS Y SELECTS */
    div[data-baseweb="input"], 
    div[data-baseweb="select"] > div {{
        background-color: {input_bg} !important;
        border: 1px solid {input_border} !important;
        border-radius: 8px !important;
    }}
    
    div[data-baseweb="input"] input, 
    div[data-baseweb="select"] span[data-baseweb="tag"] span,
    div[data-baseweb="select"] div {{
        color: {input_text} !important;
    }}
    
    div[data-baseweb="input"] input::placeholder {{ color: #9e9e9e !important; }}

    span[data-baseweb="tag"] {{
        background-color: #2d3340 !important;
        border: 1px solid #3a3f4d !important;
        color: white !important;
    }}

    /* SWITCH DE TEMA */
    .st-key-theme_toggle div[data-testid="stButton"] > button,
    .st-key-theme_toggle button {{
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
        margin: 0 auto !important;
        display: block !important;
    }}

    .st-key-theme_toggle button * {{ display: none !important; }}
    
    .st-key-theme_toggle button::before {{
        content: '' !important;
        position: absolute !important;
        top: 7px !important; left: 0 !important;
        width: 80px !important; height: 36px !important;
        background-color: #262626 !important;
        border: 2px solid #111111 !important;
        border-radius: 20px !important;
        box-shadow: inset 0 2px 5px rgba(0,0,0,0.6) !important;
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
        filter: drop-shadow(2px 3px 4px rgba(0,0,0,0.4)) !important;
        z-index: 2 !important;
    }}
    </style>
""", unsafe_allow_html=True)

# 1. LA CABECERA (LOGO + USER / THEME)
col_logo, col_espacio, col_actions = st.columns([4, 3, 2.5], vertical_alignment="center")

with col_logo:
    logo_color = "#8c7b6d"
    logo_html = f"""
    <div style="display: flex; align-items: center; gap: 10px; cursor: pointer;" onclick="window.location.reload();">
        <svg width="42" height="42" viewBox="0 0 36 36" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path d="M 6.8 21 L 29.2 21 C 30 25 27 32 18 32 C 9 32 6 25 6.8 21 Z" fill="{logo_color}" />
            <line x1="6.8" y1="21" x2="29.2" y2="21" stroke="{text_color}" stroke-width="2" />
            <line x1="18" y1="10" x2="18" y2="30" stroke="{text_color}" stroke-width="1.5" />
            <path d="M 18 32 C 9 32 5 24 7.5 17 C 9 12 13 10 15 10 L 21 10 C 23 10 27 12 28.5 17 C 31 24 27 32 18 32 Z" stroke="{text_color}" stroke-width="2.5" />
            <rect x="15" y="7" width="6" height="3" stroke="{text_color}" stroke-width="2.5" />
            <rect x="13" y="3" width="10" height="4" rx="1" stroke="{text_color}" stroke-width="2.5" />
            <rect x="16" y="0" width="4" height="3" rx="1" fill="{logo_color}" stroke="{text_color}" stroke-width="1.5" />
            <path d="M 23 5 L 26 4" stroke="{text_color}" stroke-width="2.5" />
            <ellipse cx="29" cy="3" rx="3.5" ry="2.5" transform="rotate(-25 29 3)" fill="{logo_color}" stroke="{text_color}" stroke-width="1.5" />
        </svg>
        <span style="font-family: 'Inter', sans-serif; font-size: 1.55rem; color: {text_color}; letter-spacing: -0.5px;">
            <span style="font-weight: 800;">Perfume</span><span style="font-weight: 400;">Trending</span>
        </span>
    </div>
    """
    st.markdown(logo_html, unsafe_allow_html=True)

with col_actions:
    btn_col1, btn_col2 = st.columns([1.5, 1], vertical_alignment="center")
    with btn_col1:
        st.button("👤 Ingresar", key="login_btn", use_container_width=True)
    with btn_col2:
        st.button(" ", key="theme_toggle", on_click=toggle_theme)

# 2. NAVEGACIÓN PRINCIPAL (UBICADA INMEDIATAMENTE DEBAJO DE LA CABECERA)
st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
col_nav1, col_nav2, col_nav3, col_nav4, col_nav_space = st.columns([1.2, 1.6, 1.2, 1.4, 4.6], vertical_alignment="center")

with col_nav1: 
    st.button("PERFUMES", key="n_perfumes", on_click=navigate_to, args=('home',), use_container_width=True)
with col_nav2: 
    st.button("PERFUMES ÁRABES", key="n_arabes", on_click=navigate_to, args=('home',), use_container_width=True)
with col_nav3: 
    st.button("MARCAS", key="n_marcas", on_click=navigate_to, args=('home',), use_container_width=True)
with col_nav4: 
    st.button("REMATES", key="n_remates", on_click=navigate_to, args=('hype',), use_container_width=True)

st.markdown(f"<hr style='margin: 8px 0 25px 0; border: none; border-bottom: 1px solid {btn_border}; opacity: 0.5;'>", unsafe_allow_html=True)

# 3. EL "HERO" DE BÚSQUEDA (CENTRO DE ATENCIÓN UNIFICADO)
col_search, col_filter, col_separator, col_photo = st.columns([5.5, 1.8, 0.2, 2], vertical_alignment="center")

with col_search:
    search_query = st.text_input("🔍 Buscar", placeholder="🔍 Buscar perfume, marca o esencias...", label_visibility="collapsed")

with col_filter:
    with st.popover("Esencias", use_container_width=True):
        all_notes = sorted([
            "Abedul", "Albahaca", "Almizcle (Musk)", "Ámbar", "Ámbar Gris", "Azafrán", "Bergamota",
            "Cacao", "Café", "Canela", "Caramelo", "Cardamomo", "Cedro", "Cereza", "Ciruela", 
            "Cítricos", "Civeta", "Coco", "Cuero", "Frambuesa", "Grosellas Negras", "Haba Tonka", 
            "Higo", "Incienso", "Iris", "Jazmín", "Jengibre", "Lavanda", "Lichi", "Limón", 
            "Mandarina", "Manzana", "Melocotón", "Menta", "Miel", "Mirra", "Naranjo", "Nardos", 
            "Neroli", "Notas Marinas", "Notas Solares", "Nuez Moscada", "Oud", "Pachulí", "Pera", 
            "Pimienta Blanca", "Pimienta Negra", "Pimienta Rosa", "Piña", "Pomelo", "Praliné", 
            "Romero", "Rosa", "Ruibarbo", "Salvia", "Sándalo", "Sangre", "Tabaco", "Té Verde", 
            "Vainilla", "Vetiver", "Ylang-Ylang"
        ])
        selected_essences = st.multiselect(
            "Selecciona notas olfativas:",
            options=all_notes,
            placeholder="Elige esencias...",
            label_visibility="collapsed"
        )

with col_separator:
    st.markdown(f"<div style='border-left: 2px solid #ccc; height: 35px; margin: auto;'></div>", unsafe_allow_html=True)

with col_photo:
    st.button("PHOTO SEARCH", key="btn_photo_search", help="Buscar perfume por imagen", use_container_width=True)

# 4. HERRAMIENTAS RÁPIDAS (FILTROS DE CONFIANZA TIPO CHIPS DEBAJO DEL BUSCADOR)
st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
col_chip1, col_chip2, col_chip3, col_chip_space = st.columns([1.5, 1.8, 1.6, 5.1], vertical_alignment="center")

with col_chip1:
    st.button("Trend Del Hype", key="btn_trend", on_click=navigate_to, args=('trend_page',), use_container_width=True)
with col_chip2:
    st.button("Páginas de Confianza", key="btn_trust", on_click=navigate_to, args=('trust_page',), use_container_width=True)
with col_chip3:
    st.button("Comparar Precios", key="btn_compare", on_click=navigate_to, args=('compare_page',), use_container_width=True)

st.markdown("<br><br>", unsafe_allow_html=True)

# VISTAS DE PÁGINA Y CATÁLOGO
if st.session_state['current_page'] == 'home':
    st.markdown(f"<h3 style='text-align: center; margin-bottom: 25px; color: {text_color}; letter-spacing: 1px;'>CATÁLOGO Y TENDENCIAS</h3>", unsafe_allow_html=True)
    
    if selected_essences:
        st.write(f"**Filtrando por:** {', '.join(selected_essences)}")
    else:
        st.info("Catálogo en desarrollo...")
elif st.session_state['current_page'] == 'trend_page':
    st.markdown(f"<h3 style='text-align: center; color: {text_color};'>Trend Del Hype (Próximamente)</h3>", unsafe_allow_html=True)
elif st.session_state['current_page'] == 'trust_page':
    st.markdown(f"<h3 style='text-align: center; color: {text_color};'>Páginas de Confianza (Próximamente)</h3>", unsafe_allow_html=True)
elif st.session_state['current_page'] == 'compare_page':
    st.markdown(f"<h3 style='text-align: center; color: {text_color};'>Comparador de Precios (Próximamente)</h3>", unsafe_allow_html=True)
