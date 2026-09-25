import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import sys
import os
import base64

# Configuración de rutas canónicas para importar backend
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)
if APP_DIR not in sys.path:
    sys.path.append(APP_DIR)

from backend.database import (
    obtener_catalogo,
    obtener_precios_actuales,
    obtener_historico_precios,
    obtener_detalle_perfume
)

def get_image_src(img_path_or_url):
    """Retorna URL remota o data URI en base64 para imágenes locales."""
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

# 1. CONFIGURACIÓN DE LA PÁGINA Y ESTADO
st.set_page_config(page_title="Comparador de Precios - PerfumeTrending", layout="wide", initial_sidebar_state="collapsed")

if 'theme' not in st.session_state:
    st.session_state['theme'] = 'dark'

def toggle_theme():
    st.session_state['theme'] = 'dark' if st.session_state['theme'] == 'light' else 'light'

is_dark = st.session_state['theme'] == 'dark'

# Colores dinámicos adaptables por tema
app_bg = "#0c0e12" if is_dark else "#f9f9fb"
app_bg_css = f"background-color: {app_bg} !important;"

text_color = "#f0f0f0" if is_dark else "#18181b"
subtext_color = "#888890" if is_dark else "#666670"

btn_bg = "#161920" if is_dark else "#ffffff"
btn_text = "#ffffff" if is_dark else "#18181b"
btn_border = "#2a2e39" if is_dark else "#d1d5db"

input_bg = "#14171d" if is_dark else "#ffffff"
input_text = "#f0f0f0" if is_dark else "#18181b"
input_border = "#2a2e39" if is_dark else "#d1d5db"

# SWITCH DE TEMA - POSICIONAMIENTO Y SVGS
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

user_icon_svg = f"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23{btn_text[1:]}' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2'/><circle cx='12' cy='7' r='4'/></svg>"

# ICONOS ILUSTRADOS EN ROJO (TREN, ESCUDO, ETIQUETA)
trend_red_svg = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23ff3838' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'><path d='M2 19h20M2 22h20M5 19v3M9 19v3M13 19v3M17 19v3M21 19v3' stroke='%23ff3838'/><path d='M4 11h9v7H4z' fill='%23ff3838'/><path d='M13 7h6v11h-6z' fill='%23ff3838'/><rect x='15' y='9' width='3' height='3' fill='%23ffffff'/><path d='M6 7h2v4H6z' fill='%23ff3838'/><path d='M19 14l3 4h-3z' fill='%23ff3838'/><circle cx='6.5' cy='18.5' r='1.5' fill='%23ff3838' stroke='%23ffffff' stroke-width='0.5'/><circle cx='10.5' cy='18.5' r='1.5' fill='%23ff3838' stroke='%23ffffff' stroke-width='0.5'/><circle cx='16' cy='18.5' r='1.5' fill='%23ff3838' stroke='%23ffffff' stroke-width='0.5'/></svg>"
shield_red_svg = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23ff3838' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z'/><path d='m9 12 2 2 4-4'/></svg>"
tag_red_svg = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23ff3838' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M12 2H2v10l11.29 11.29a1 1 0 0 0 1.41 0l7.58-7.58a1 1 0 0 0 0-1.41L12 2z'/><circle cx='7.5' cy='7.5' r='1.5' fill='%23ff3838'/></svg>"

# 2. CSS ADAPTABLE Y ESTILOS PRINCIPALES
st.markdown(f"""
    <style>
    html, body, .stApp {{
        -webkit-font-smoothing: antialiased !important;
        -moz-osx-font-smoothing: grayscale !important;
        text-rendering: optimizeLegibility !important;
    }}

    header[data-testid="stHeader"] {{ display: none !important; }}
    
    .block-container {{ 
        padding-top: 1.2rem !important; 
        padding-bottom: 2rem !important; 
        max-width: 1200px !important;
    }}
    
    .stApp {{ {app_bg_css} color: {text_color} !important; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }}

    .stApp p, .stApp span, .stApp label, .stMarkdown p {{
        color: {text_color} !important;
        text-shadow: none !important;
    }}

    /* EFECTO DE BOTONES Y ENLACES PAGE_LINK */
    div.stButton > button,
    a[data-testid="stPageLink-NavLink"] {{
        transition: transform 0.22s cubic-bezier(0.34, 1.56, 0.64, 1), background-color 0.15s ease, border-color 0.15s ease, color 0.15s ease !important;
        text-shadow: none !important;
        box-shadow: none !important;
        outline: none !important;
    }}

    div.stButton > button:hover,
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

    .st-key-login_btn button {{
        background-color: {btn_bg} !important;
        color: {btn_text} !important;
        border: 1px solid {btn_border} !important;
        border-radius: 8px !important;
        height: 44px !important;
        padding: 0 1rem 0 2.5rem !important;
        background-image: url("{user_icon_svg}") !important;
        background-repeat: no-repeat !important;
        background-position: 14px center !important;
        background-size: 18px 18px !important;
        font-size: 0.95rem !important;
    }}
    .st-key-login_btn button p {{
        color: {btn_text} !important;
        font-weight: 600 !important;
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

    /* DIBUJOS ILUSTRADOS EN ROJO PARA LOS BOTONES */
    a[data-testid="stPageLink-NavLink"][href*="trendhype"],
    a[data-testid="stPageLink-NavLink"][href*="trustpage"],
    a[data-testid="stPageLink-NavLink"][href*="compararprecios"] {{
        position: relative !important;
        padding-left: 2.8rem !important;
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
        width: 20px !important;
        height: 20px !important;
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
        width: 19px !important;
        height: 19px !important;
        background-image: url("{shield_red_svg}") !important;
        background-repeat: no-repeat !important;
        background-size: contain !important;
        background-position: center !important;
    }}

    /* 3. Comparar Precios */
    a[data-testid="stPageLink-NavLink"][href*="compararprecios"]::before {{
        content: '' !important;
        position: absolute !important;
        left: 14px !important;
        top: 50% !important;
        transform: translateY(-50%) !important;
        width: 19px !important;
        height: 19px !important;
        background-image: url("{tag_red_svg}") !important;
        background-repeat: no-repeat !important;
        background-size: contain !important;
        background-position: center !important;
    }}

    /* TARJETA CABECERA DEL PERFUME */
    .perfume-header-card {{
        background-color: {btn_bg};
        border: 1px solid {btn_border};
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 24px;
        display: flex;
        gap: 24px;
        align-items: center;
    }}

    .perfume-header-img {{
        width: 130px;
        height: 130px;
        object-fit: contain;
        background: #ffffff;
        border-radius: 8px;
        padding: 8px;
    }}

    /* TARJETAS DE COMPARACIÓN DE PRECIOS */
    .price-card {{
        background-color: {btn_bg};
        border: 1px solid {btn_border};
        border-radius: 10px;
        padding: 16px 20px;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }}
    .price-card:hover {{
        transform: translateY(-2px);
        border-color: #d4c2a5;
    }}
    .best-deal {{
        border: 2px solid #2e7d32 !important;
        background-color: { "#122415" if is_dark else "#eef7f0" } !important;
    }}
    .store-name {{
        font-size: 1.1rem;
        font-weight: 700;
        color: {text_color};
    }}
    .store-badge {{
        font-size: 0.75rem;
        padding: 2px 8px;
        border-radius: 4px;
        background-color: {btn_border};
        color: {text_color};
        margin-left: 8px;
    }}
    .price-value {{
        font-size: 1.25rem;
        font-weight: 800;
        color: {text_color};
    }}
    .old-price {{
        font-size: 0.85rem;
        text-decoration: line-through;
        color: {subtext_color};
        margin-right: 8px;
    }}
    .buy-btn {{
        background-color: #8c7b6d;
        color: #ffffff !important;
        padding: 8px 16px;
        border-radius: 6px;
        text-decoration: none;
        font-weight: 600;
        font-size: 0.85rem;
        display: inline-block;
        transition: background-color 0.2s ease;
    }}
    .buy-btn:hover {{
        background-color: #726255;
    }}
    </style>
""", unsafe_allow_html=True)

# 3. CABECERA CON LOGO Y SWITCH ALINEADO
col_logo, col_espacio, col_actions = st.columns([5, 1.8, 2.4], vertical_alignment="center")

with col_logo:
    logo_color = "#8c7b6d"
    logo_html = f"""<div style="display: inline-flex; align-items: center; gap: 12px; cursor: pointer; width: fit-content;" onclick="window.location.href='/';"><svg width="34" height="34" viewBox="0 0 36 36" fill="none" stroke-linecap="round" stroke-linejoin="round"><path d="M 6.8 21 L 29.2 21 C 30 25 27 32 18 32 C 9 32 6 25 6.8 21 Z" fill="{logo_color}" /><line x1="6.8" y1="21" x2="29.2" y2="21" stroke="{text_color}" stroke-width="1.5" /><line x1="18" y1="10" x2="18" y2="30" stroke="{text_color}" stroke-width="1" /><path d="M 18 32 C 9 32 5 24 7.5 17 C 9 12 13 10 15 10 L 21 10 C 23 10 27 12 28.5 17 C 31 24 27 32 18 32 Z" stroke="{text_color}" stroke-width="2" /><rect x="15" y="7" width="6" height="3" stroke="{text_color}" stroke-width="1.5" /><rect x="13" y="3" width="10" height="4" rx="1" stroke="{text_color}" stroke-width="1.5" /><rect x="16" y="0" width="4" height="3" rx="1" fill="{logo_color}" stroke="{text_color}" stroke-width="1" /></svg><span style="font-size: 1.4rem; color: {text_color}; letter-spacing: 0.5px;"><span style="font-weight: 300;">Perfume</span><span style="font-weight: 600;">Trending</span></span></div>"""
    st.markdown(logo_html, unsafe_allow_html=True)

with col_actions:
    btn_col1, btn_col2 = st.columns([1.4, 1], vertical_alignment="center")
    with btn_col1:
        st.button("Ingresar", key="login_btn", use_container_width=True)
    with btn_col2:
        st.button(" ", key="theme_toggle", on_click=toggle_theme)

st.markdown("<div style='margin-top: 14px;'></div>", unsafe_allow_html=True)

# 4. CHIPS DE NAVEGACIÓN RÁPIDA
col_chip1, col_chip2, col_chip3, col_chip_space = st.columns([1.5, 2.0, 1.7, 3.8], vertical_alignment="center")

with col_chip1:
    st.page_link("pages/trendhype.py", label="Trend Del Hype", use_container_width=True)
with col_chip2:
    st.page_link("pages/trustpage.py", label="Páginas de Confianza", use_container_width=True)
with col_chip3:
    st.page_link("pages/compararprecios.py", label="Comparar Precios", use_container_width=True)

st.markdown("<div style='margin-top: 24px;'></div>", unsafe_allow_html=True)

# 5. SECCIÓN PRINCIPAL: COMPARADOR DE PRECIOS
st.markdown(f"""<div style='text-align: center; margin-bottom: 24px; color: {text_color}; letter-spacing: 1.5px; font-weight: 300; font-size: 1.1rem; text-transform: uppercase;'>COMPARADOR DE PRECIOS EN TIENDAS CHILENAS</div>""", unsafe_allow_html=True)

# Cargar catálogo dinámico desde SQLite
catalogo = obtener_catalogo()

if not catalogo:
    st.warning("No hay perfumes disponibles en el catálogo en este momento.")
    st.stop()

# Diccionario de selección: Nombre Completo -> Objeto Perfume
opciones_perfumes = {f"{p['nombre']} — {p['marca']}": p for p in catalogo}
lista_nombres = list(opciones_perfumes.keys())

# Determinar perfume pre-seleccionado
default_index = 0
selected_session = st.session_state.get('selected_perfume')
if selected_session is not None:
    for idx, (lbl, p) in enumerate(opciones_perfumes.items()):
        if str(selected_session) == str(p['id']) or (isinstance(selected_session, str) and selected_session.lower() in p['nombre'].lower()):
            default_index = idx
            break

selected_label = st.selectbox("Selecciona un perfume para comparar ofertas en Chile:", lista_nombres, index=default_index)
perfume = opciones_perfumes[selected_label]
selected_id = perfume['id']

# Obtener detalle enriquecido
detalle = obtener_detalle_perfume(selected_id) or perfume

# Mostrar ficha cabecera del perfume con packshot de alta resolución
img_src = get_image_src(detalle.get('imagen_url'))
notas_txt = detalle.get('notas', 'Notas olfativas exclusivas')
genero_txt = detalle.get('genero', 'Unisex')
tipo_txt = detalle.get('tipo', 'Eau de Parfum')

col_img, col_info = st.columns([1, 3], gap="medium")
with col_img:
    st.markdown(f"""
    <div style="background: #ffffff; border-radius: 12px; padding: 12px; display: flex; align-items: center; justify-content: center; border: 1px solid {btn_border};">
        <img src="{img_src}" alt="{detalle['nombre']}" style="max-height: 180px; max-width: 100%; object-fit: contain;">
    </div>
    """, unsafe_allow_html=True)

with col_info:
    ref_precio = detalle.get('precio_referencia')
    ref_str = f"${ref_precio:,.0f} CLP".replace(",", ".") if ref_precio else "Consultar"
    
    st.markdown(f"""
    <div style="padding-top: 4px;">
        <h2 style="margin: 0 0 6px 0; color: {text_color}; font-size: 1.6rem; font-weight: 700;">{detalle['nombre']}</h2>
        <div style="color: {subtext_color}; font-size: 0.95rem; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 1px;">
            {detalle['marca']} &bull; {tipo_txt} &bull; {genero_txt}
        </div>
        <p style="margin: 0 0 8px 0; color: {text_color}; font-size: 0.9rem; line-height: 1.5;">
            <b>Notas olfativas:</b> {notas_txt}
        </p>
        <div style="margin-top: 10px; display: flex; gap: 16px; align-items: center;">
            <span style="font-size: 0.85rem; color: {subtext_color};">Precio referencial de mercado: <b style="color: {text_color};">{ref_str}</b></span>
            <span style="background-color: #2e7d3222; color: #4caf50; font-size: 0.78rem; font-weight: 700; padding: 3px 8px; border-radius: 4px; border: 1px solid #4caf5044;">DISPONIBLE EN TIENDAS AUDITADAS</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='margin-top: 24px;'></div>", unsafe_allow_html=True)
st.markdown(f"<h3 style='font-size: 1.15rem; color: {text_color}; font-weight: 600; margin-bottom: 16px;'>Ofertas en tiendas chilenas verificadas</h3>", unsafe_allow_html=True)

# Obtener ofertas y precios actuales desde la base de datos
tiendas_db = obtener_precios_actuales(selected_id)

if not tiendas_db:
    st.info("Actualmente estamos sincronizando los precios en tiempo real para esta fragancia.")
else:
    # Identificar el mejor precio (mínimo precio_actual > 0)
    precios_validos = [t['precio_actual'] for t in tiendas_db if t.get('precio_actual', 0) > 0]
    min_precio = min(precios_validos) if precios_validos else 0

    for item in tiendas_db:
        p_act = item.get('precio_actual', 0)
        p_norm = item.get('precio_normal', 0)
        is_best_deal = (p_act == min_precio and p_act > 0)
        
        card_class = "price-card best-deal" if is_best_deal else "price-card"
        best_badge = "<span style='color: #2e7d32; font-weight: 700; margin-left: 8px; font-size: 0.8rem;'>🏆 MEJOR PRECIO</span>" if is_best_deal else ""
        
        precio_actual_str = f"${p_act:,.0f}".replace(",", ".")
        precio_ant_str = f"${p_norm:,.0f}".replace(",", ".") if p_norm and p_norm > p_act else ""
        old_price_html = f"<span class='old-price'>{precio_ant_str}</span>" if precio_ant_str else ""
        
        # Enlace 100% directo a la ficha del producto en la tienda
        url_directa = item.get('url_producto') or item.get('url_base') or "#"
        badge_tienda = item.get('badge', 'Tienda Verificada')
        
        html_card = f"""
        <div class="{card_class}">
            <div>
                <span class="store-name">{item['tienda_nombre']}</span>
                <span class="store-badge">{badge_tienda}</span>
                {best_badge}
            </div>
            <div style="display: flex; align-items: center; gap: 16px;">
                <div>
                    {old_price_html}
                    <span class="price-value">{precio_actual_str} CLP</span>
                </div>
                <a href="{url_directa}" class="buy-btn" target="_blank" rel="noopener noreferrer">Ir a la oferta ↗</a>
            </div>
        </div>
        """
        st.markdown(html_card, unsafe_allow_html=True)

# 6. HISTORIAL Y EVOLUCIÓN DE PRECIOS
st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
with st.expander("📈 Ver Evolución Histórica de Precios en Tiendas Chilenas"):
    historico = obtener_historico_precios(selected_id)
    if historico:
        df_hist = pd.DataFrame(historico)
        if 'fecha' in df_hist.columns and 'precio' in df_hist.columns and 'tienda' in df_hist.columns:
            df_hist['fecha'] = pd.to_datetime(df_hist['fecha'])
            df_pivot = df_hist.pivot_table(index='fecha', columns='tienda', values='precio', aggfunc='min')
            st.line_chart(df_pivot)
        else:
            st.write(df_hist)
    else:
        st.write("Recopilando datos históricos de variaciones de precio en comercios auditados.")
