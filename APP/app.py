import streamlit as st
import pandas as pd

# 1. CONFIGURACIÓN DE LA PÁGINA Y CSS CUSTOM 
st.set_page_config(page_title="PerfumeTrending", layout="wide", initial_sidebar_state="collapsed")

# 2. MANEJO DE ESTADO (Navegación)
if 'current_page' not in st.session_state:
    st.session_state['current_page'] = 'home'

if 'theme' not in st.session_state:
    st.session_state['theme'] = 'light'

def toggle_theme():
    st.session_state['theme'] = 'dark' if st.session_state['theme'] == 'light' else 'light'

def navigate_to(page):
    st.session_state['current_page'] = page

# Configuración dinámica de colores según el tema activo
is_dark = st.session_state['theme'] == 'dark'
bg_color = "#0e1117" if is_dark else "#ffffff"
text_color = "#ffffff" if is_dark else "#111111"
subtext_color = "#a0a0a0" if is_dark else "#555555"

# Colores para botones e inputs
btn_bg = "#1f242d" if is_dark else "#111111"
btn_text = "#ffffff"
btn_border = "#3a3f4d" if is_dark else "#111111"
btn_hover_bg = "#2d3340" if is_dark else "#333333"

input_bg = "#1f242d" if is_dark else "#f4f5f7"
input_text = "#ffffff" if is_dark else "#111111"
input_border = "#3a3f4d" if is_dark else "#d1d5db"

# Parámetros del interruptor personalizado
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
    /* Ocultar barra superior predeterminada de Streamlit */
    header[data-testid="stHeader"] {{
        display: none !important;
    }}
    
    /* Espaciado superior e inferior limpio */
    .block-container {{
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
    }}
    
    .stApp {{
        background-color: {bg_color} !important;
        color: {text_color} !important;
    }}

    /* REGLA DE SIMETRÍA Y TAMAÑO IDENTICO PARA TODAS LAS IMÁGENES */
    div[data-testid="stImage"] img {{
        object-fit: cover !important;
        width: 100% !important;
        height: 280px !important;
        border-radius: 8px !important;
    }}

    /* ESTILO GENERAL DE BOTONES STREAMLIT */
    div[data-testid="stButton"] > button {{
        background-color: {btn_bg} !important;
        color: {btn_text} !important;
        border: 1px solid {btn_border} !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
        transition: all 0.2s ease !important;
    }}
    div[data-testid="stButton"] > button:hover {{
        background-color: {btn_hover_bg} !important;
        color: {btn_text} !important;
        border-color: {btn_hover_bg} !important;
    }}

    /* ESTILO GENERAL DE CAMPOS DE TEXTO E INPUTS */
    div[data-baseweb="input"] {{
        background-color: {input_bg} !important;
        border: 1px solid {input_border} !important;
        border-radius: 8px !important;
    }}
    div[data-baseweb="input"] input {{
        color: {input_text} !important;
    }}
    div[data-baseweb="input"] input::placeholder {{
        color: {subtext_color} !important;
    }}

    .trust-badge-green {{
        background-color: #d4edda; color: #155724; padding: 4px 10px; 
        border-radius: 4px; border: 1px solid #c3e6cb; font-size: 12px; font-weight: bold;
    }}
    .trust-badge-red {{
        background-color: #f8d7da; color: #721c24; padding: 4px 10px; 
        border-radius: 4px; border: 1px solid #f5c6cb; font-size: 12px; font-weight: bold;
    }}
    .buy-btn {{
        background-color: #4a86e8; color: white !important; padding: 6px 12px; 
        text-decoration: none; border-radius: 4px; font-size: 12px; font-weight: bold;
        display: inline-block;
    }}
    .product-title {{ font-size: 1.1rem; font-weight: bold; margin-bottom: 0; color: {text_color}; margin-top: 10px; }}
    .product-brand {{ font-size: 0.85rem; color: {subtext_color}; margin-bottom: 10px; }}
    
    .header-nav {{
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 20px;
        font-weight: bold;
        font-size: 0.95rem;
        color: {text_color};
    }}

    /* INTERRUPTOR PERSONALIZADO EN FORMA DE BOTELLA DE PERFUME */
    .st-key-theme_toggle button {{
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
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

    .st-key-theme_toggle button * {{
        display: none !important;
    }}

    /* Cápsula de fondo (Track) */
    .st-key-theme_toggle button::before {{
        content: '' !important;
        position: absolute !important;
        top: 7px !important;
        left: 0 !important;
        width: 80px !important;
        height: 36px !important;
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

    /* Botella de Perfume deslizante (Thumb) */
    .st-key-theme_toggle button::after {{
        content: '' !important;
        position: absolute !important;
        top: -1px !important;
        left: {bottle_left_pos} !important;
        width: 40px !important;
        height: 46px !important;
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
col_logo, col_nav, col_actions = st.columns([3, 5, 2], vertical_alignment="center")

with col_logo:
    logo_color = "#333333" if is_dark else "#a0a0a0"
    
    logo_html = f"""
    <div style="display: flex; align-items: center; gap: 10px; overflow: visible;">
        <svg width="42" height="42" viewBox="0 0 36 36" fill="none" stroke-linecap="round" stroke-linejoin="round" style="overflow: visible;">
            <!-- Liquid Fill -->
            <path d="M 6.8 21 L 29.2 21 C 30 25 27 32 18 32 C 9 32 6 25 6.8 21 Z" fill="{logo_color}" />
            <!-- Liquid Level Line -->
            <line x1="6.8" y1="21" x2="29.2" y2="21" stroke="{text_color}" stroke-width="2" />
            <!-- Straw -->
            <line x1="18" y1="10" x2="18" y2="30" stroke="{text_color}" stroke-width="1.5" />
            <!-- Bottle Outline -->
            <path d="M 18 32 C 9 32 5 24 7.5 17 C 9 12 13 10 15 10 L 21 10 C 23 10 27 12 28.5 17 C 31 24 27 32 18 32 Z" stroke="{text_color}" stroke-width="2.5" />
            <!-- Neck -->
            <rect x="15" y="7" width="6" height="3" stroke="{text_color}" stroke-width="2.5" />
            <!-- Pump Base -->
            <rect x="13" y="3" width="10" height="4" rx="1" stroke="{text_color}" stroke-width="2.5" />
            <!-- Pump Top -->
            <rect x="16" y="0" width="4" height="3" rx="1" fill="{logo_color}" stroke="{text_color}" stroke-width="1.5" />
            <!-- Atomizer Stem -->
            <path d="M 23 5 L 26 4" stroke="{text_color}" stroke-width="2.5" />
            <!-- Atomizer Bulb -->
            <ellipse cx="29" cy="3" rx="3.5" ry="2.5" transform="rotate(-25 29 3)" fill="{logo_color}" stroke="{text_color}" stroke-width="1.5" />
        </svg>
        <span style="font-family: 'Inter', 'Helvetica Neue', Helvetica, sans-serif; font-size: 1.65rem; color: {text_color}; letter-spacing: -0.5px; white-space: nowrap;">
            <span style="font-weight: 800;">Perfume</span><span style="font-weight: 400;">Trending</span>
        </span>
    </div>
    """
    st.markdown(logo_html, unsafe_allow_html=True)

with col_nav:
    st.markdown("<div class='header-nav'><span>HOMBRES</span> | <span>MUJERES</span> | <span>ÁRABES</span> | <span>DISEÑADOR</span> | <span>NICHO</span></div>", unsafe_allow_html=True)

with col_actions:
    btn_col1, btn_col2 = st.columns([1, 1], vertical_alignment="center")
    with btn_col1:
        st.button("👤 Ingresar", key="login_btn", use_container_width=True)
    with btn_col2:
        st.button(" ", key="theme_toggle", on_click=toggle_theme)

st.text_input("🔍 Buscar perfume, marca, notas...", placeholder="Ej: Midnight Oud...")

st.divider()

# ==========================================
# VISTA 1: HOME o LOBBY (TRENDING en SOCIAL MEDIA)
# ==========================================
if st.session_state['current_page'] == 'home':
    st.markdown(f"<h3 style='text-align: center; margin-bottom: 20px; color: {text_color};'>TENDENCIAS EN REDES SOCIALES</h3>", unsafe_allow_html=True)
    
    trending_perfumes = [
        {"brand": "CREED", "name": "AVENTUS", "price": "$140.00", "img": "https://images.unsplash.com/photo-1594035910387-fea47794261f?w=500&q=80"},
        {"brand": "DIOR", "name": "SAUVAGE", "price": "$145.00", "img": "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=500&q=80"},
        {"brand": "MAISON ALHAMBRA", "name": "MIDNIGHT OUD", "price": "$110.00", "img": "https://images.unsplash.com/photo-1588405748880-12d1d2a59f75?w=500&q=80"},
        {"brand": "TOM FORD", "name": "OMBRE LEATHER", "price": "$145.00", "img": "https://images.unsplash.com/photo-1541643600914-78b084683601?w=500&q=80"},
        {"brand": "JEAN PAUL GAULTIER", "name": "LE MALE ELIXIR", "price": "$125.00", "img": "https://images.unsplash.com/photo-1616949755610-8c9bbc08f138?w=500&q=80"},
        {"brand": "PARFUMS DE MARLY", "name": "DELINA", "price": "$210.00", "img": "https://images.unsplash.com/photo-1592945403244-b3fbafd7f539?w=500&q=80"},
        {"brand": "LATTAFA", "name": "KHAMRAH", "price": "$45.00", "img": "https://images.unsplash.com/photo-1523293182086-7651a899d37f?w=500&q=80"},
        {"brand": "GIORGIO ARMANI", "name": "ACQUA DI GIO", "price": "$115.00", "img": "https://images.unsplash.com/photo-1594035910387-fea47794261f?w=500&q=80"},
        {"brand": "YVES SAINT LAURENT", "name": "Y EDP", "price": "$130.00", "img": "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=500&q=80"},
        {"brand": "VERSACE", "name": "EROS", "price": "$95.00", "img": "https://images.unsplash.com/photo-1588405748880-12d1d2a59f75?w=500&q=80"}
    ]

    # Despliegue en filas de 4 columnas
    cols_per_row = 4
    for row_start in range(0, len(trending_perfumes), cols_per_row):
        row_items = trending_perfumes[row_start:row_start + cols_per_row]
        cols = st.columns(cols_per_row)
        for i, perfume in enumerate(row_items):
            idx = row_start + i
            with cols[i]:
                st.image(perfume["img"], use_container_width=True)
                st.markdown(f"<div class='product-title'>{perfume['name']}</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='product-brand'>{perfume['brand']}</div>", unsafe_allow_html=True)
                st.write(f"Compara precios desde **{perfume['price']}**")
                
                if perfume["name"] == "MIDNIGHT OUD":
                    st.button("Ver Ofertas", key=f"btn_{idx}", on_click=navigate_to, args=('product',), use_container_width=True)
                else:
                    st.button("Ver Ofertas", key=f"btn_{idx}", use_container_width=True)
        st.write("")

# ==========================================
# VISTA 2: DETALLE DE PRODUCTO (COMPARADOR)
# ==========================================
elif st.session_state['current_page'] == 'product':
    st.button("← Volver al inicio", on_click=navigate_to, args=('home',))
    st.write("")
    
    col_izq, col_der = st.columns([1, 2])
    
    with col_izq:
        st.image("https://images.unsplash.com/photo-1588405748880-12d1d2a59f75?w=500&q=80", use_container_width=True)
        st.markdown(f"<h3 style='color: {text_color}; margin-top: 15px;'>MIDNIGHT OUD - EAU DE PARFUM</h3>", unsafe_allow_html=True)
        st.write("**50ml / 1.7 oz**")
        st.markdown("""
        * 🪵 **Madera de Oud:** Oud floral amaderado
        * 🌹 **Rosa Búlgara:** Rosa Búlgara fresca
        * 🍯 **Ámbar:** Ámbar cálido y resinoso
        """)

    with col_der:
        st.markdown(f"<h4 style='color: {text_color};'>Comparación de Precios y Confianza</h4>", unsafe_allow_html=True)
        
        table_bg = "#1f242d" if is_dark else "#f8f9fa"
        table_border = "#3a3f4d" if is_dark else "#e5e7eb"
        
        tabla_html = f"""
        <table style="width:100%; text-align:center; border-collapse: collapse; color: {text_color}; border: 1px solid {table_border};">
            <tr style="border-bottom: 2px solid {table_border}; background-color: {table_bg};">
                <th style="padding: 10px;">#</th>
                <th style="padding: 10px;">TIENDA</th>
                <th style="padding: 10px;">PRECIO</th>
                <th style="padding: 10px;">NIVEL DE CONFIANZA</th>
                <th style="padding: 10px;">COMPRA AHORA</th>
            </tr>
            <tr style="border-bottom: 1px solid {table_border};">
                <td style="padding: 15px;">1</td>
                <td><strong>AURA SCENTS</strong></td>
                <td><strong>$110.00</strong></td>
                <td>
                    <span class="trust-badge-green">✔️ CONFIRMADO</span><br>
                    <small style="color: green;">Muy Seguro</small>
                </td>
                <td><a href="#" class="buy-btn">COMPRAR AHORA</a></td>
            </tr>
            <tr style="border-bottom: 1px solid {table_border};">
                <td style="padding: 15px;">2</td>
                <td><strong>THE PERFUME BARN</strong></td>
                <td><strong>$105.00</strong></td>
                <td>
                    <span class="trust-badge-red">❌ RIESGO ALTO</span><br>
                    <small style="color: red;">Alerta Estafa</small>
                </td>
                <td><a href="#" class="buy-btn" style="background-color: #555;">COMPRAR AHORA</a></td>
            </tr>
            <tr style="border-bottom: 1px solid {table_border};">
                <td style="padding: 15px;">3</td>
                <td><strong>ELEGANT FRAGRANCE</strong></td>
                <td><strong>$112.50</strong></td>
                <td>
                    <span class="trust-badge-green">✔️ CONFIRMADO</span><br>
                    <small style="color: green;">Muy Seguro</small>
                </td>
                <td><a href="#" class="buy-btn">COMPRAR AHORA</a></td>
            </tr>
            <tr>
                <td style="padding: 15px;">4</td>
                <td><strong>FRAGRANCE DIRECT</strong></td>
                <td><strong>$108.99</strong></td>
                <td>
                    <span class="trust-badge-green">✔️ CONFIRMADO</span><br>
                    <small style="color: green;">Muy Seguro</small>
                </td>
                <td><a href="#" class="buy-btn">COMPRAR AHORA</a></td>
            </tr>
        </table>
        """
        st.markdown(tabla_html, unsafe_allow_html=True)

# 4. PIE DE PÁGINA (FOOTER)
st.divider()
st.markdown(
    f"""
    <div style='text-align: center; color: {subtext_color}; padding: 15px 0px; font-size: 0.85rem;'>
        © 2026 Perfume Trending. Todos los derechos reservados.
    </div>
    """,
    unsafe_allow_html=True
)
