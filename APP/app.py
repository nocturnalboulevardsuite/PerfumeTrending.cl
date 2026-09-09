import streamlit as st
import pandas as pd
import sys
import os

# Asegurar que la raíz del proyecto esté en sys.path para importar backend
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from backend.database import (
    obtener_catalogo,
    obtener_detalle_perfume,
    obtener_precios_actuales,
    obtener_historico_precios,
    obtener_tiendas,
    init_db
)
from backend.scraper_periodico import ejecutar_ciclo_scraping_y_descubrimiento

import base64

def get_image_src(img_path_or_url):
    """
    Retorna la URL remota o el data URI en base64 si es un archivo local del proyecto,
    garantizando que se renderice con máxima fidelidad en navegador y en Streamlit Cloud.
    """
    if not img_path_or_url:
        return "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=500&q=80"
    
    if img_path_or_url.startswith("http://") or img_path_or_url.startswith("https://") or img_path_or_url.startswith("data:"):
        return img_path_or_url

    local_path = img_path_or_url
    if not os.path.isabs(local_path):
        cand1 = os.path.join(BASE_DIR, local_path)
        cand2 = os.path.join(BASE_DIR, "APP", local_path)
        if os.path.exists(cand1):
            local_path = cand1
        elif os.path.exists(cand2):
            local_path = cand2

    if os.path.exists(local_path):
        ext = os.path.splitext(local_path)[1].lower().replace(".", "")
        mime = "image/png" if ext == "png" else "image/jpeg"
        try:
            with open(local_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
                return f"data:{mime};base64,{b64}"
        except Exception:
            pass

    return img_path_or_url

# 1. CONFIGURACIÓN DE LA PÁGINA Y CSS CUSTOM 
st.set_page_config(page_title="PerfumeTrending — Comparador & Radar", layout="wide", initial_sidebar_state="collapsed")

# Inicializar base de datos con tablas y datos semilla si no existen
init_db()


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
    st.button("PERFUMES", key="n_perfumes", on_click=navigate_to, args=('home', None), use_container_width=True)
with col_nav2: 
    st.button("PERFUMES ÁRABES", key="n_arabes", on_click=navigate_to, args=('arabes', None), use_container_width=True)
with col_nav3: 
    st.button("MARCAS", key="n_marcas", on_click=navigate_to, args=('marcas', None), use_container_width=True)
with col_nav4: 
    st.button("REMATES", key="n_remates", on_click=navigate_to, args=('remates', None), use_container_width=True)

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
    with st.popover("📷 PHOTO SEARCH", use_container_width=True):
        st.write("##### 📷 Búsqueda Visual de Perfumes")
        st.caption("Sube una foto del frasco o caja para reconocer el perfume automáticamente:")
        uploaded_file = st.file_uploader("Subir imagen", type=["jpg", "png", "jpeg"], label_visibility="collapsed")
        if uploaded_file:
            st.image(uploaded_file, caption="Imagen cargada", use_column_width=True)
            st.success("✨ Perfume reconocido: Dior Sauvage Eau de Toilette")
            if st.button("Ver Comparador de este perfume", key="btn_photo_match"):
                navigate_to('detalle', 3)
                st.rerun()

# 4. HERRAMIENTAS RÁPIDAS (CHIPS DEBAJO DEL BUSCADOR)
st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
col_chip1, col_chip2, col_chip3, col_chip_space = st.columns([1.5, 1.8, 1.6, 5.1], vertical_alignment="center")

with col_chip1:
    if st.button("Trend Del Hype", key="btn_trend", use_container_width=True):
        st.switch_page("pages/trendhype.py")
with col_chip2:
    st.button("Páginas de Confianza", key="btn_trust", on_click=navigate_to, args=('trust_page', None), use_container_width=True)
with col_chip3:
    st.button("Comparar Precios", key="btn_compare", on_click=navigate_to, args=('home', None), use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)

# -------------------------------------------------------------------------------------------------
# VISTA: FICHA DETALLADA DEL PERFUME (COMPARADOR + ANÁLISIS PERIÓDICO DE PRECIOS)
# -------------------------------------------------------------------------------------------------
if st.session_state['current_page'] == 'detalle' and st.session_state['selected_perfume']:
    perfume_id = st.session_state['selected_perfume']
    perfume = obtener_detalle_perfume(perfume_id)

    if not perfume:
        st.error("No se encontró el perfume seleccionado.")
        if st.button("← Volver al Catálogo"):
            navigate_to('home', None)
            st.rerun()
    else:
        col_back, col_actions_top = st.columns([6, 3])
        with col_back:
            if st.button("← Volver al Catálogo", key="btn_back_catalog"):
                navigate_to('home', None)
                st.rerun()
        with col_actions_top:
            if st.button("🔄 Ejecutar Análisis Periódico (Scraper)", key="btn_scrape_single", use_container_width=True):
                with st.spinner("Ejecutando scraper y registrando nuevos snapshots..."):
                    res = ejecutar_ciclo_scraping_y_descubrimiento()
                    st.toast(f"¡Precios analizados! {res['actualizaciones']} registros actualizados.", icon="✅")
                    st.rerun()

        st.markdown("<hr style='margin: 10px 0 20px 0; border: none; border-bottom: 1px solid #3a3f4d;'>", unsafe_allow_html=True)

        precios_tiendas = obtener_precios_actuales(perfume_id)
        historico = obtener_historico_precios(perfume_id)

        # Filtrar tiendas que tienen stock y precio > 0 para calcular el mejor precio disponible
        tiendas_en_stock = [p for p in precios_tiendas if p.get("en_stock") == 1 and p.get("precio_actual", 0) > 0]
        if tiendas_en_stock:
            mejor_tienda_obj = min(tiendas_en_stock, key=lambda x: x["precio_actual"])
            mejor_precio = mejor_tienda_obj["precio_actual"]
            mejor_tienda = mejor_tienda_obj["tienda_nombre"]
            mejor_url = mejor_tienda_obj["url_producto"]
        else:
            mejor_precio = perfume["precio_referencia"]
            mejor_tienda = "Retail Oficial"
            mejor_url = f"https://www.google.com/search?q={perfume['nombre']}+perfume+chile"

        ultima_captura = precios_tiendas[0]["fecha_registro"] if precios_tiendas else "Hoy"

        # Cabecera de la Ficha
        col_img, col_info = st.columns([3.5, 6.5], gap="large")

        with col_img:
            img_src = get_image_src(perfume.get('imagen_url'))
            st.markdown(f"""
            <div style="background-color: {btn_bg}; padding: 25px; border-radius: 20px; border: 1px solid {btn_border}; text-align: center; box-shadow: 0 10px 30px rgba(0,0,0,0.12); position: relative; overflow: hidden;">
                <img src="{img_src}" style="max-width: 100%; height: 350px; object-fit: contain; border-radius: 12px; margin-bottom: 15px; filter: drop-shadow(0 12px 24px rgba(0,0,0,0.28)); transition: transform 0.4s ease;" onmouseover="this.style.transform='scale(1.04)'" onmouseout="this.style.transform='scale(1)'">
                <div style="font-size: 0.88rem; color: {text_color}; font-weight: 600; letter-spacing: 0.5px;">
                    {perfume['genero']} • {perfume['tipo']}
                </div>
            </div>
            """, unsafe_allow_html=True)


        with col_info:
            tag_arabe = "<span style='background-color: #8c7b6d; color: white; padding: 3px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: bold;'>🇨🇱 Perfume Árabe</span>" if perfume["es_arabe"] else ""
            tag_tendencia = "<span style='background-color: #e74c3c; color: white; padding: 3px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: bold;'>🔥 Viral / Hype</span>" if perfume["en_tendencia"] else ""

            st.markdown(f"""
            <div>
                {tag_arabe} {tag_tendencia}
                <h1 style='color: {text_color}; margin: 8px 0 0 0;'>{perfume['nombre']}</h1>
                <h4 style='color: {subtext_color}; margin-top: 0;'>{perfume['marca']}</h4>
            </div>
            """, unsafe_allow_html=True)

            # BANNER DEL MEJOR PRECIO: CLIC EN EL BANNER O EN EL PRECIO REDIRIGE DIRECTO A LA TIENDA
            st.markdown(f"""
            <a href="{mejor_url}" target="_blank" style="text-decoration: none; color: inherit;">
                <div style="background-color: {btn_bg}; border: 2px solid #27ae60; border-radius: 12px; padding: 15px; margin: 15px 0; cursor: pointer; transition: transform 0.2s;" onmouseover="this.style.transform='scale(1.01)'" onmouseout="this.style.transform='scale(1)'">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 0.85rem; color: #27ae60; font-weight: bold;">⚡ MEJOR PRECIO DISPONIBLE EN CHILE (CLIC PARA IR A LA TIENDA ↗)</span>
                        <span style="background-color: #27ae60; color: white; padding: 4px 12px; border-radius: 8px; font-size: 0.8rem; font-weight: bold;">Ver en {mejor_tienda} ↗</span>
                    </div>
                    <div style="font-size: 2.3rem; font-weight: 800; color: #27ae60; margin: 6px 0;">${mejor_precio:,.0f} CLP <span style="font-size: 1.05rem; color: {text_color}; font-weight: 600;">en {mejor_tienda}</span></div>
                    <div style="font-size: 0.8rem; color: {subtext_color};">🕒 Último análisis del scraper: <strong>{ultima_captura}</strong> • <span style="color: #27ae60; text-decoration: underline; font-weight: bold;">Haz clic en el precio para comprar directamente</span></div>
                </div>
            </a>
            """, unsafe_allow_html=True)

            st.markdown(f"**Notas Olfativas:**")
            notas_lista = [n.strip() for n in perfume['notas'].split(",")]
            badges_html = " ".join([f"<span style='display:inline-block; background-color:{btn_hover_bg}; border:1px solid {btn_border}; padding: 3px 10px; border-radius: 14px; font-size: 0.8rem; margin: 2px; color:{text_color};'>{nota}</span>" for nota in notas_lista])
            st.markdown(badges_html, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # PESTAÑAS: COMPARADOR DE TIENDAS Y ANÁLISIS HISTÓRICO
        tab_comparador, tab_historico = st.tabs(["🛒 Comparativa de Precios por Tienda", "📈 Análisis Periódico y Evolución de Precios"])

        with tab_comparador:
            st.write("##### Precios recopilados por el scraper en tiendas chilenas (Haz clic en el precio para abrir la tienda):")
            if precios_tiendas:
                for pt in precios_tiendas:
                    tiene_stock = (pt["en_stock"] == 1 and pt["precio_actual"] > 0)
                    es_mejor = (tiene_stock and pt["precio_actual"] == mejor_precio)
                    ahorro = pt["precio_normal"] - pt["precio_actual"] if tiene_stock else 0
                    ahorro_pct = int(round((ahorro / pt["precio_normal"]) * 100)) if (tiene_stock and pt["precio_normal"] > pt["precio_actual"]) else 0

                    col_t1, col_t2, col_t3, col_t4 = st.columns([3, 2.5, 2.5, 2], vertical_alignment="center")

                    with col_t1:
                        st.markdown(f"""
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <span style="font-size: 1.6rem;">{pt['logo_emoji']}</span>
                            <div>
                                <strong style="font-size: 1.05rem; color: {text_color};">{pt['tienda_nombre']}</strong><br>
                                <span style="font-size: 0.75rem; color: #27ae60; font-weight: bold;">Trust Score: {pt['trust_score']}%</span> • <span style="font-size: 0.75rem; color: {subtext_color};">{pt['badge']}</span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

                    with col_t2:
                        # CLIC EN EL PRECIO REDIRIGE DIRECTO A LA PÁGINA O BÚSQUEDA EN LA TIENDA
                        if tiene_stock:
                            st.markdown(f"""
                            <div>
                                <a href="{pt['url_producto']}" target="_blank" style="text-decoration: none; color: inherit;" title="Clic aquí para abrir la oferta en {pt['tienda_nombre']}">
                                    <span style="font-size: 1.35rem; font-weight: 800; color: #27ae60; border-bottom: 2px dashed #27ae60; cursor: pointer;">
                                        ${pt['precio_actual']:,} CLP ↗
                                    </span>
                                </a><br>
                                <span style="font-size: 0.8rem; color: {subtext_color}; text-decoration: line-through;">${pt['precio_normal']:,} CLP</span>
                                {f"<span style='color: #e74c3c; font-size: 0.8rem; font-weight: bold;'> (-{ahorro_pct}%)</span>" if ahorro_pct > 0 else ""}
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.markdown(f"""
                            <div>
                                <a href="{pt['url_producto']}" target="_blank" style="text-decoration: none; color: inherit;" title="Verificar catálogo de {pt['tienda_nombre']}">
                                    <span style="font-size: 0.95rem; font-weight: 600; color: #888; border-bottom: 1px dashed #888; cursor: pointer;">
                                        Sin stock verificado ↗
                                    </span>
                                </a>
                            </div>
                            """, unsafe_allow_html=True)

                    with col_t3:
                        stock_badge = "🟢 En Stock Verificado" if tiene_stock else "🔴 No comercializado / Agotado"
                        st.markdown(f"""
                        <div style="font-size: 0.85rem; color: {subtext_color};">
                            {stock_badge}<br>
                            <span style="font-size: 0.75rem;">Captura: {pt['fecha_registro']}</span>
                        </div>
                        """, unsafe_allow_html=True)

                    with col_t4:
                        btn_label = "Ir a la tienda ↗" if tiene_stock else "Buscar en tienda ↗"
                        st.link_button(btn_label, pt["url_producto"], use_container_width=True)

                    st.markdown(f"<hr style='margin: 8px 0; border: none; border-bottom: 1px dashed {btn_border};'>", unsafe_allow_html=True)
            else:
                st.info("No se han registrado tiendas para este perfume aún.")


        with tab_historico:
            st.write("##### Evolución periódica de precios capturada por el scraper:")
            st.caption("Cada punto del gráfico representa un snapshot periódico recopilado por el scraper en cada tienda chilena.")

            if historico and len(historico) > 0:
                df_hist = pd.DataFrame(historico)
                df_hist["fecha_registro"] = pd.to_datetime(df_hist["fecha_registro"])
                df_pivot = df_hist.pivot_table(index="fecha_registro", columns="tienda", values="precio_actual", aggfunc="last").ffill().bfill()

                st.line_chart(df_pivot)

                col_m1, col_m2, col_m3 = st.columns(3)
                with col_m1:
                    min_hist = int(df_hist["precio_actual"].min())
                    st.metric("Precio Mínimo Histórico", f"${min_hist:,} CLP")
                with col_m2:
                    max_hist = int(df_hist["precio_actual"].max())
                    st.metric("Precio Máximo Histórico", f"${max_hist:,} CLP")
                with col_m3:
                    tiendas_rastreadas = df_hist["tienda"].nunique()
                    st.metric("Tiendas Rastreadas", f"{tiendas_rastreadas} tiendas")
            else:
                st.info("Aún no hay suficientes registros históricos para este perfume.")

# -------------------------------------------------------------------------------------------------
# VISTA: PÁGINAS DE CONFIANZA (TRUST SCORE DIRECTORY)
# -------------------------------------------------------------------------------------------------
elif st.session_state['current_page'] == 'trust_page':
    st.markdown(f"<h2 style='text-align: center; color: {text_color};'>Directorio de Comercios y Trust Score 🇨🇱</h2>", unsafe_allow_html=True)
    st.write("<p style='text-align: center; color: #888;'>Índice de transparencia y legitimidad de comercios electrónicos de perfumería en Chile.</p>", unsafe_allow_html=True)
    
    tiendas = obtener_tiendas()
    for t in tiendas:
        col_t1, col_t2, col_t3 = st.columns([3, 4, 3], vertical_alignment="center")
        with col_t1:
            st.markdown(f"### {t['logo_emoji']} {t['nombre']}")
            st.caption(f"Portal: {t['url_base']}")
        with col_t2:
            st.write(f"**Distintivo:** {t['badge']}")
            st.write("Verificación: Boleta/Factura legal, presencia verificada y certificado SSL.")
        with col_t3:
            st.metric("Trust Score Antifraude", f"{t['trust_score']} / 100")
        st.divider()

    if st.button("← Volver al Catálogo"):
        navigate_to('home', None)
        st.rerun()

# -------------------------------------------------------------------------------------------------
# VISTA: CATÁLOGO PRINCIPAL (HOME / ÁRABES / REMATES / MARCAS)
# -------------------------------------------------------------------------------------------------
else:
    cat = st.session_state['current_page']
    categoria_filtro = "arabes" if cat == "arabes" else ("remates" if cat == "remates" else None)

    col_titulo, col_btn_scrape = st.columns([7, 3], vertical_alignment="center")
    with col_titulo:
        titulo_cat = "CATÁLOGO DE PERFUMES ÁRABES" if cat == "arabes" else ("REMATES Y OFERTAS" if cat == "remates" else "CATÁLOGO Y TENDENCIAS")
        st.markdown(f"<h3 style='color: {text_color}; letter-spacing: 0.5px; margin: 0;'>{titulo_cat}</h3>", unsafe_allow_html=True)
    
    with col_btn_scrape:
        if st.button("🤖 Descubrir Perfumes Automáticamente", key="btn_auto_discover", use_container_width=True, help="Ejecuta el scraper para buscar nuevos perfumes e insertarlos automáticamente"):
            with st.spinner("Scraper explorando tiendas e insertando perfumes automáticamente..."):
                res = ejecutar_ciclo_scraping_y_descubrimiento()
                st.toast(f"¡Listo! Se agregaron {res['nuevos']} nuevos perfumes y {res['actualizaciones']} precios actualizados.", icon="✨")
                st.rerun()

    perfumes = obtener_catalogo(busqueda=search_query, esencias=selected_essences, categoria=categoria_filtro)

    if selected_essences:
        st.caption(f"Filtrando por notas: **{', '.join(selected_essences)}** ({len(perfumes)} resultados encontrados)")
    else:
        st.caption(f"{len(perfumes)} perfumes monitorizados periódicamente en el mercado chileno")

    st.markdown("<br>", unsafe_allow_html=True)

    if not perfumes:
        st.info("No se encontraron perfumes con los filtros seleccionados.")
    else:
        cols_grid = st.columns(3, gap="medium")

        for idx, p in enumerate(perfumes):
            col_target = cols_grid[idx % 3]

            with col_target:
                p_img_src = get_image_src(p.get("imagen_url"))
                precio_display = f"${p['mejor_precio']:,} CLP" if p.get('mejor_precio') else f"${p['precio_referencia']:,} CLP"
                badge_tag = ""
                if p.get("es_arabe"):
                    badge_tag = "<span style='background-color: #8c7b6d; color: white; padding: 2px 6px; border-radius: 8px; font-size: 0.7rem; font-weight: bold;'>🇨🇱 Árabe</span>"
                elif p.get("en_tendencia"):
                    badge_tag = "<span style='background-color: #e74c3c; color: white; padding: 2px 6px; border-radius: 8px; font-size: 0.7rem; font-weight: bold;'>🔥 Viral</span>"

                card_html = f"""
                <div style="background-color: {btn_bg}; border: 1px solid {btn_border}; border-radius: 14px; padding: 15px; margin-bottom: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.06); min-height: 430px; display: flex; flex-direction: column; justify-content: space-between;">
                    <div>
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                            <span style="font-size: 0.8rem; color: {subtext_color}; text-transform: uppercase; font-weight: bold;">{p['marca']}</span>
                            {badge_tag}
                        </div>
                        <div style="text-align: center; margin: 8px 0; background: {btn_hover_bg}; border-radius: 10px; padding: 12px;">
                            <img src="{p_img_src}" style="width: 100%; height: 175px; object-fit: contain; filter: drop-shadow(0 6px 12px rgba(0,0,0,0.2)); transition: transform 0.3s ease;">
                        </div>
                        <h4 style="margin: 6px 0 2px 0; color: {text_color}; font-size: 1.1rem;">{p['nombre']}</h4>
                        <div style="font-size: 0.78rem; color: {subtext_color}; line-height: 1.3; height: 35px; overflow: hidden; margin-bottom: 8px;">
                            {p['notas']}
                        </div>
                    </div>
                    <div>
                        <div style="border-top: 1px solid {btn_border}; padding-top: 10px; margin-top: 5px;">
                            <span style="font-size: 0.75rem; color: {subtext_color};">Desde</span><br>
                            <span style="font-size: 1.3rem; font-weight: 800; color: #27ae60;">{precio_display}</span>
                        </div>
                    </div>
                </div>
                """
                st.markdown(card_html, unsafe_allow_html=True)

                if st.button("📊 Comparar Precios & Historial", key=f"btn_p_{p['id']}", use_container_width=True):
                    navigate_to('detalle', p['id'])
                    st.rerun()

