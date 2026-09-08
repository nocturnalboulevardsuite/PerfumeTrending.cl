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

# Configuración dinámica de colores según el tema activo
is_dark = st.session_state['theme'] == 'dark'

app_bg_css = "background-color: #0e1117 !important;" if is_dark else "background: linear-gradient(135deg, #fdfbf9 0%, #ede4dc 100%) !important;"
text_color = "#ffffff" if is_dark else "#1a1a1a"
subtext_color = "#a0a0a0" if is_dark else "#666666"

btn_bg = "#1f242d" if is_dark else "#ffffff"
btn_text = "#ffffff" if is_dark else "#2c2c2c"
btn_border = "#3a3f4d" if is_dark else "#d4cdc5"
btn_hover_bg = "#2d3340" if is_dark else "#f5ece4"

input_bg = "#1f242d" if is_dark else "#ffffff"
input_text = "#ffffff" if is_dark else "#2c2c2c"
input_border = "#3a3f4d" if is_dark else "#c9c0b5"

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

# Estilos CSS
st.markdown(f"""
    <style>
    header[data-testid="stHeader"] {{ display: none !important; }}
    .block-container {{ padding-top: 2rem !important; padding-bottom: 2rem !important; }}
    .stApp {{ {app_bg_css} color: {text_color} !important; }}

    .stApp p, .stApp span, .stApp label, .stMarkdown p, .stTextInput label p, .stMultiSelect label p {{
        color: {text_color} !important;
    }}

    /* IMÁGENES Y EFECTOS */
    div[data-testid="stImage"] img {{
        object-fit: cover !important;
        width: 100% !important;
        height: 280px !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08) !important;
        transition: transform 0.3s ease, box-shadow 0.3s ease !important;
    }}
    div[data-testid="stImage"] img:hover {{
        transform: translateY(-5px);
        box-shadow: 0 8px 20px rgba(0,0,0,0.15) !important;
    }}

    /* BOTONES GENERALES DE ACCIÓN */
    div[data-testid="stButton"] > button {{
        background-color: {btn_bg} !important;
        color: {btn_text} !important;
        border: 1px solid {btn_border} !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        transition: all 0.2s ease !important;
    }}
    
    div[data-testid="stButton"] > button p {{
        color: {btn_text} !important;
    }}

    div[data-testid="stButton"] > button:hover {{
        background-color: {btn_hover_bg} !important;
        border-color: {btn_hover_bg} !important;
    }}

    /* NAVEGACIÓN ESTILO LETRAS CLICKEABLES (TRANSPARENTE Y SIN CORTES) */
    div[data-testid="stButton"].st-key-n_hombres > button,
    div[data-testid="stButton"].st-key-n_mujeres > button,
    div[data-testid="stButton"].st-key-n_arabes > button,
    div[data-testid="stButton"].st-key-n_hype > button,
    div[data-testid="stButton"].st-key-n_disenador > button,
    div[data-testid="stButton"].st-key-n_nicho > button {{
        background: transparent !important;
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
        white-space: nowrap !important;
        overflow: visible !important;
    }}

    div[data-testid="stButton"].st-key-n_hombres > button:hover,
    div[data-testid="stButton"].st-key-n_mujeres > button:hover,
    div[data-testid="stButton"].st-key-n_arabes > button:hover,
    div[data-testid="stButton"].st-key-n_hype > button:hover,
    div[data-testid="stButton"].st-key-n_disenador > button:hover,
    div[data-testid="stButton"].st-key-n_nicho > button:hover {{
        background: transparent !important;
        background-color: transparent !important;
        border: none !important;
    }}
    
    div[data-testid="stButton"].st-key-n_hombres > button p,
    div[data-testid="stButton"].st-key-n_mujeres > button p,
    div[data-testid="stButton"].st-key-n_arabes > button p,
    div[data-testid="stButton"].st-key-n_hype > button p,
    div[data-testid="stButton"].st-key-n_disenador > button p,
    div[data-testid="stButton"].st-key-n_nicho > button p {{
        color: {text_color} !important;
        font-size: 0.95rem !important;
        font-weight: 800 !important;
        letter-spacing: 1px !important;
        text-transform: uppercase !important;
        white-space: nowrap !important;
        overflow: visible !important;
        margin: 0 !important;
        transition: color 0.2s ease !important;
    }}

    div[data-testid="stButton"].st-key-n_hombres > button:hover p,
    div[data-testid="stButton"].st-key-n_mujeres > button:hover p,
    div[data-testid="stButton"].st-key-n_arabes > button:hover p,
    div[data-testid="stButton"].st-key-n_hype > button:hover p,
    div[data-testid="stButton"].st-key-n_disenador > button:hover p,
    div[data-testid="stButton"].st-key-n_nicho > button:hover p {{
        color: #d4a373 !important;
        text-decoration: underline !important;
        text-underline-offset: 4px !important;
    }}

    /* FIX BOTÓN "PHOTO SEARCH" */
    .st-key-btn_photo_search button {{
        background-color: #1f242d !important;
        border: 1px solid #3a3f4d !important;
    }}
    .st-key-btn_photo_search button p,
    .st-key-btn_photo_search button span {{
        color: #ffffff !important;
    }}
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
    
    div[data-baseweb="input"] input::placeholder {{ 
        color: {subtext_color} !important; 
    }}

    /* ETIQUETAS DE MULTISELECT */
    span[data-baseweb="tag"] {{
        background-color: {btn_hover_bg} !important;
        border: 1px solid {btn_border} !important;
    }}

    /* BADGES DE NOTAS */
    .note-badge {{
        background-color: {'#2d3340' if is_dark else '#ebdcd0'};
        color: {text_color};
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.78rem;
        font-weight: 600;
        display: inline-block;
        margin-right: 4px;
        margin-bottom: 6px;
    }}

    .trust-badge-green {{
        background-color: #d4edda; color: #155724; padding: 4px 10px; 
        border-radius: 6px; border: 1px solid #c3e6cb; font-size: 12px; font-weight: bold;
    }}
    .trust-badge-red {{
        background-color: #f8d7da; color: #721c24; padding: 4px 10px; 
        border-radius: 6px; border: 1px solid #f5c6cb; font-size: 12px; font-weight: bold;
    }}
    .buy-btn {{
        background: linear-gradient(90deg, #4a86e8 0%, #366bc2 100%); 
        color: white !important; padding: 8px 16px; 
        text-decoration: none; border-radius: 6px; font-size: 12px; font-weight: bold;
        display: inline-block;
        box-shadow: 0 2px 5px rgba(74, 134, 232, 0.3);
        transition: transform 0.2s;
    }}
    .buy-btn:hover {{ transform: scale(1.05); }}
    
    .product-title {{ font-size: 1.15rem; font-weight: bold; margin-bottom: 0; color: {text_color} !important; margin-top: 12px; }}
    .product-brand {{ font-size: 0.85rem; color: {subtext_color} !important; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 1px; }}

    /* SWITCH TEMA */
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

# 3. CABECERA GLOBAL
col_logo, col_nav, col_actions = st.columns([2.5, 6, 2], vertical_alignment="center")

with col_logo:
    logo_color = "#333333" if is_dark else "#8c7b6d"
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

with col_nav:
    # Ajustamos proporciones para darle más espacio a las palabras largas (ej: DISEÑADOR)
    c1, c2, c3, c4, c5, c6 = st.columns([1, 1, 1, 1.2, 1.4, 1], vertical_alignment="center")
    with c1: st.button("HOMBRES", key="n_hombres", on_click=navigate_to, args=('home',))
    with c2: st.button("MUJERES", key="n_mujeres", on_click=navigate_to, args=('home',))
    with c3: st.button("ÁRABES", key="n_arabes", on_click=navigate_to, args=('home',))
    with c4: st.button("🚂 HYPE", key="n_hype", on_click=navigate_to, args=('hype',))
    with c5: st.button("DISEÑADOR", key="n_disenador", on_click=navigate_to, args=('home',))
    with c6: st.button("NICHO", key="n_nicho", on_click=navigate_to, args=('home',))

with col_actions:
    btn_col1, btn_col2 = st.columns([1.5, 1], vertical_alignment="center")
    with btn_col1:
        st.button("👤 Ingresar", key="login_btn", use_container_width=True)
    with btn_col2:
        st.button(" ", key="theme_toggle", on_click=toggle_theme)

st.write("")

# DATOS BASE DE PERFUMES
trending_perfumes = [
    {"brand": "CREED", "name": "AVENTUS", "price": "$140.00", "notes": ["Piña", "Cítricos", "Abedul", "Almizcle"], "img": "https://images.unsplash.com/photo-1594035910387-fea47794261f?w=500&q=80"},
    {"brand": "DIOR", "name": "SAUVAGE", "price": "$145.00", "notes": ["Bergamota", "Pimienta", "Ambroxan", "Cítricos"], "img": "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=500&q=80"},
    {"brand": "MAISON ALHAMBRA", "name": "MIDNIGHT OUD", "price": "$110.00", "notes": ["Oud", "Rosa", "Ámbar", "Cuero"], "img": "https://images.unsplash.com/photo-1588405748880-12d1d2a59f75?w=500&q=80"},
    {"brand": "TOM FORD", "name": "OMBRE LEATHER", "price": "$145.00", "notes": ["Cuero", "Cardamomo", "Jazmín", "Ámbar"], "img": "https://images.unsplash.com/photo-1541643600914-78b084683601?w=500&q=80"},
    {"brand": "JEAN PAUL GAULTIER", "name": "LE MALE ELIXIR", "price": "$125.00", "notes": ["Menta", "Vainilla", "Miel", "Habatonka"], "img": "https://images.unsplash.com/photo-1616949755610-8c9bbc08f138?w=500&q=80"},
    {"brand": "PARFUMS DE MARLY", "name": "DELINA", "price": "$210.00", "notes": ["Lichi", "Rosa", "Vainilla", "Ruibarbo"], "img": "https://images.unsplash.com/photo-1592945403244-b3fbafd7f539?w=500&q=80"},
    {"brand": "LATTAFA", "name": "KHAMRAH", "price": "$45.00", "notes": ["Canela", "Nuez Moscada", "Vainilla", "Praliné"], "img": "https://images.unsplash.com/photo-1523293182086-7651a899d37f?w=500&q=80"},
    {"brand": "GIORGIO ARMANI", "name": "ACQUA DI GIO", "price": "$115.00", "notes": ["Marinas", "Bergamota", "Cítricos", "Romero"], "img": "https://images.unsplash.com/photo-1594035910387-fea47794261f?w=500&q=80"},
    {"brand": "YVES SAINT LAURENT", "name": "Y EDP", "price": "$130.00", "notes": ["Manzana", "Jengibre", "Salvia", "Abedul"], "img": "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=500&q=80"},
    {"brand": "VERSACE", "name": "EROS", "price": "$95.00", "notes": ["Menta", "Manzana Verde", "Vainilla", "Habatonka"], "img": "https://images.unsplash.com/photo-1588405748880-12d1d2a59f75?w=500&q=80"}
]

# 4. BARRA DE BÚSQUEDA INTEGRADA Y FILTRO DE ESENCIAS
if st.session_state['current_page'] != 'hype':
    col_search, col_separator, col_photo = st.columns([8, 0.2, 2], vertical_alignment="center")

    with col_search:
        search_query = st.text_input("🔍 Buscar", placeholder="🔍 Buscar perfume, marca o esencias (Ej: Oud, Vainilla, Cítricos...)", label_visibility="collapsed")
    with col_separator:
        st.markdown(f"<div style='border-left: 2px solid {input_border}; height: 35px; margin: auto;'></div>", unsafe_allow_html=True)
    with col_photo:
        st.button("📷 PHOTO SEARCH", key="btn_photo_search", help="Buscar perfume por imagen", use_container_width=True)

    all_notes = sorted(list(set([note for p in trending_perfumes for note in p["notes"]])))
    selected_essences = st.multiselect("🌸 Filtrar por Esencias / Notas Olfativas:", options=all_notes, placeholder="Selecciona una o varias esencias...")

    st.divider()

    filtered_perfumes = []
    for p in trending_perfumes:
        matches_text = (
            search_query.lower() in p["name"].lower() or 
            search_query.lower() in p["brand"].lower() or
            any(search_query.lower() in n.lower() for n in p["notes"])
        )
        matches_essences = True
        if selected_essences:
            matches_essences = any(essence in p["notes"] for essence in selected_essences)
            
        if matches_text and matches_essences:
            filtered_perfumes.append(p)

# ==========================================
# VISTA 1: HOME / CATÁLOGO
# ==========================================
if st.session_state['current_page'] == 'home':
    st.markdown(f"<h3 style='text-align: center; margin-bottom: 25px; color: {text_color}; letter-spacing: 1px;'>🔥 CATÁLOGO Y TENDENCIAS</h3>", unsafe_allow_html=True)
    
    if not filtered_perfumes:
        st.warning("No se encontraron perfumes con los criterios seleccionados.")
    else:
        cols_per_row = 4
        for row_start in range(0, len(filtered_perfumes), cols_per_row):
            row_items = filtered_perfumes[row_start:row_start + cols_per_row]
            cols = st.columns(cols_per_row, gap="medium")
            for i, perfume in enumerate(row_items):
                idx = row_start + i
                with cols[i]:
                    st.image(perfume["img"], use_container_width=True)
                    st.markdown(f"<div class='product-title'>{perfume['name']}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='product-brand'>{perfume['brand']}</div>", unsafe_allow_html=True)
                    
                    notes_html = "".join([f"<span class='note-badge'>{note}</span>" for note in perfume["notes"][:3]])
                    st.markdown(f"<div>{notes_html}</div>", unsafe_allow_html=True)
                    
                    st.write(f"Desde **{perfume['price']}**")
                    st.button("✨ Ver Ofertas", key=f"btn_{idx}", on_click=navigate_to, args=('product', perfume), use_container_width=True)
            st.write("<br>", unsafe_allow_html=True)

# ==========================================
# VISTA 2: PERFIL Y COMPARADOR DEL PERFUME
# ==========================================
elif st.session_state['current_page'] == 'product':
    perfume = st.session_state.get('selected_perfume') or trending_perfumes[2]
    
    st.button("← Volver al catálogo", on_click=navigate_to, args=('home',))
    st.write("")
    
    col_izq, col_der = st.columns([1, 2], gap="large")
    
    with col_izq:
        st.image(perfume["img"], use_container_width=True)
        st.markdown(f"<h3 style='color: {text_color}; margin-top: 15px;'>{perfume['name']}<br><span style='font-size: 1rem; font-weight: normal; color: {subtext_color};'>{perfume['brand']}</span></h3>", unsafe_allow_html=True)
        st.write("**100ml / 3.4 oz**")
        
        st.markdown("**Notas Olfativas y Esencias:**")
        for note in perfume["notes"]:
            st.markdown(f"* 🧪 **{note}**")

    with col_der:
        st.markdown(f"<h4 style='color: {text_color}; border-bottom: 2px solid {input_border}; padding-bottom: 10px;'>📊 Comparación de Precios y Confianza</h4>", unsafe_allow_html=True)
        st.write("")
        
        table_bg = "#1f242d" if is_dark else "#ffffff"
        table_border = "#3a3f4d" if is_dark else "#d4cdc5"
        
        tabla_html = f"""
        <div style="border-radius: 10px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.05);">
            <table style="width:100%; text-align:center; border-collapse: collapse; color: {text_color}; background-color: {table_bg};">
                <tr style="border-bottom: 2px solid {table_border}; background-color: {'#2d3340' if is_dark else '#f5ece4'};">
                    <th style="padding: 15px;">#</th>
                    <th style="padding: 15px;">TIENDA</th>
                    <th style="padding: 15px;">PRECIO</th>
                    <th style="padding: 15px;">NIVEL DE CONFIANZA</th>
                    <th style="padding: 15px;">ACCIÓN</th>
                </tr>
                <tr style="border-bottom: 1px solid {table_border};">
                    <td style="padding: 18px;">1</td>
                    <td><strong>AURA SCENTS</strong></td>
                    <td style="color: #27ae60; font-size: 1.1rem;"><strong>{perfume['price']}</strong></td>
                    <td>
                        <span class="trust-badge-green">✔️ CONFIRMADO</span><br>
                        <small style="color: #27ae60;">Distribuidor Oficial</small>
                    </td>
                    <td><a href="#" class="buy-btn">COMPRAR AHORA</a></td>
                </tr>
                <tr style="border-bottom: 1px solid {table_border};">
                    <td style="padding: 18px;">2</td>
                    <td><strong>THE PERFUME BARN</strong></td>
                    <td style="font-size: 1.1rem;"><strong>$105.00</strong></td>
                    <td>
                        <span class="trust-badge-red">❌ RIESGO ALTO</span><br>
                        <small style="color: #c0392b;">Alerta de Falsificación</small>
                    </td>
                    <td><a href="#" class="buy-btn" style="background: #7f8c8d; box-shadow: none;">COMPRAR AHORA</a></td>
                </tr>
                <tr style="border-bottom: 1px solid {table_border};">
                    <td style="padding: 18px;">3</td>
                    <td><strong>ELEGANT FRAGRANCE</strong></td>
                    <td style="font-size: 1.1rem;"><strong>$112.50</strong></td>
                    <td>
                        <span class="trust-badge-green">✔️ CONFIRMADO</span><br>
                        <small style="color: #27ae60;">Seguro</small>
                    </td>
                    <td><a href="#" class="buy-btn">COMPRAR AHORA</a></td>
                </tr>
            </table>
        </div>
        """
        st.markdown(tabla_html, unsafe_allow_html=True)

# ==========================================
# VISTA 3: TREN DEL HYPE
# ==========================================
elif st.session_state['current_page'] == 'hype':
    st.button("← Volver al catálogo", on_click=navigate_to, args=('home',))
    st.markdown(f"<h2 style='text-align: center; color: {text_color}; margin-top: 10px;'>🚂 EL TREN DEL HYPE</h2>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; color: {subtext_color}; font-size: 1.05rem;'>Las fragancias más virales y comentadas en redes esta semana.</p>", unsafe_allow_html=True)
    st.write("<br>", unsafe_allow_html=True)

    hype_items = [
        {"rank": "#1 🔥", "brand": "LATTAFA", "name": "KHAMRAH", "hype_score": "98%", "reason": "Trending #1 en TikTok Fragrance Community"},
        {"rank": "#2 🚀", "brand": "JEAN PAUL GAULTIER", "name": "LE MALE ELIXIR", "hype_score": "95%", "reason": "Sube en menciones y búsquedas globales"},
        {"rank": "#3 💥", "brand": "CREED", "name": "AVENTUS", "hype_score": "91%", "reason": "Inmune al paso del tiempo, alta demanda"},
    ]

    for item in hype_items:
        st.markdown(f"""
        <div style="background-color: {'#1f242d' if is_dark else '#ffffff'}; border: 1px solid {'#3a3f4d' if is_dark else '#e2d8ce'}; border-radius: 12px; padding: 20px; margin-bottom: 15px; display: flex; align-items: center; justify-content: space-between;">
            <div>
                <span style="font-size: 1.4rem; font-weight: 800; color: #d4a373;">{item['rank']}</span>
                <span style="font-size: 1.2rem; font-weight: 700; color: {text_color}; margin-left: 15px;">{item['name']}</span>
                <span style="font-size: 0.9rem; color: {subtext_color}; margin-left: 8px;">by {item['brand']}</span>
                <p style="margin: 5px 0 0 0; color: {subtext_color}; font-size: 0.88rem;">{item['reason']}</p>
            </div>
            <div style="text-align: right;">
                <span style="background-color: #d4a373; color: #ffffff; font-weight: bold; padding: 6px 14px; border-radius: 20px; font-size: 0.9rem;">
                    HYPE SCORE: {item['hype_score']}
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)

# 5. PIE DE PÁGINA (FOOTER)
st.write("<br><br>", unsafe_allow_html=True)
st.divider()
st.markdown(
    f"""
    <div style='text-align: center; color: {subtext_color}; padding: 15px 0px; font-size: 0.85rem; letter-spacing: 0.5px;'>
        © 2026 Perfume Trending. Todos los derechos reservados.<br>
        <span style='font-size: 0.75rem;'>Diseñado para amantes de las fragancias.</span>
    </div>
    """,
    unsafe_allow_html=True
)
