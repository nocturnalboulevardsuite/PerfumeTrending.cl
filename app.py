import streamlit as st
import pandas as pd

# 1. CONFIGURACIÓN DE la PÁGINA Y CSS CUSTOM 
st.set_page_config(page_title="PerfumeTrending", layout="wide", initial_sidebar_state="collapsed")

# 2. MANEJO DE ESTADO (la Navegación y Tema)
if 'current_page' not in st.session_state:
    st.session_state['current_page'] = 'home'

if 'theme' not in st.session_state:
    st.session_state['theme'] = 'dark'

def toggle_theme():
    st.session_state['theme'] = 'light' if st.session_state['theme'] == 'dark' else 'dark'

def navigate_to(page):
    st.session_state['current_page'] = page

# Configuración dinámica de colores según el tema activo
is_dark = st.session_state['theme'] == 'dark'
bg_color = "#0e1117" if is_dark else "#ffffff"
text_color = "#ffffff" if is_dark else "#111111"
subtext_color = "#a0a0a0" if is_dark else "#555555"

# CSS principal y CSS avanzado para el Toggle de Perfume
st.markdown(f"""
    <style>
    .stApp {{
        background-color: {bg_color};
        color: {text_color};
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
    .product-title {{ font-size: 1.2rem; font-weight: bold; margin-bottom: 0; color: {text_color}; }}
    .product-brand {{ font-size: 0.9rem; color: {subtext_color}; margin-bottom: 10px; }}
    
    .header-nav {{
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 20px;
        font-weight: bold;
        font-size: 0.95rem;
    }}

    /* ----- TOGGLE PERSONALIZADO: BOTELLA DE PERFUME ----- */
    /* Ocultar texto por defecto del botón */
    button[title="switch_theme"] p {{
        display: none;
    }}
    
    /* El fondo del interruptor (Track) */
    button[title="switch_theme"] {{
        width: 76px !important;
        min-width: 76px !important;
        height: 36px !important;
        border-radius: 20px !important;
        background-color: {"#333333" if is_dark else "#e0e0e0"} !important;
        border: 2px solid {"#111111" if is_dark else "#aaaaaa"} !important;
        position: relative;
        overflow: visible !important;
        display: block;
        margin: 0 auto;
        cursor: pointer;
        transition: all 0.4s ease;
        box-shadow: inset 0 2px 4px rgba(0,0,0,0.3) !important;
    }}
    
    /* Icono de luna de fondo cuando está en modo oscuro */
    button[title="switch_theme"]::after {{
        content: '{"🌙" if is_dark else ""}'; 
        position: absolute;
        right: 12px;
        top: 50%;
        transform: translateY(-50%);
        font-size: 16px;
        opacity: {"1" if is_dark else "0"};
        transition: 0.3s;
    }}

    /* El interruptor movible (La botella de perfume blanca) */
    button[title="switch_theme"]::before {{
        content: '{"☀️" if is_dark else "🌙"}';
        position: absolute;
        top: -6px;
        left: {"-4px" if is_dark else "36px"};
        width: 38px;
        height: 44px;
        background-color: #f4f4f4;
        color: #111;
        border: 2px solid #111;
        border-radius: 45% 45% 15% 15%; /* Forma de frasco */
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 18px;
        z-index: 2;
        transition: left 0.4s cubic-bezier(0.25, 0.8, 0.25, 1);
        box-shadow: 2px 4px 6px rgba(0,0,0,0.3);
    }}
    </style>
""", unsafe_allow_html=True)

# 3. CABECERA GLOBAL (Los Header y el super Buscador)
col_logo, col_nav, col_actions = st.columns([3, 5, 2], vertical_alignment="center")

with col_logo:
    st.markdown("### 🏷️ PERFUME**TRENDING**")

with col_nav:
    st.markdown("<div class='header-nav'><span>HOMBRES</span> | <span>MUJERES</span> | <span>ÁRABES</span> | <span>DISEÑADOR</span> | <span>NICHO</span></div>", unsafe_allow_html=True)

with col_actions:
    btn_col1, btn_col2 = st.columns([1, 1])
    with btn_col1:
        st.button("👤 Ingresar", key="login_btn", use_container_width=True)
    with btn_col2:
        # El parámetro help="switch_theme" aplica el diseño de la botella de perfume mediante CSS
        st.button(" ", key="theme_toggle", on_click=toggle_theme, help="switch_theme")

st.text_input("🔍 Buscar perfume, marca, notas...", placeholder="Ej: Midnight Oud...")

st.divider()

# ==========================================
# VISTA 1: HOME o LOBBY (TRENDING en SOCIAL MEDIA)
# ==========================================
if st.session_state['current_page'] == 'home':
    st.markdown("<h3 style='text-align: center;'>TENDENCIAS EN REDES SOCIALES</h3>", unsafe_allow_html=True)
    st.write("")
    
    # Datos simulados de fragancias virales (dummy)
    trending_perfumes = [
        {"brand": "CREED", "name": "AVENTUS", "price": "$140.00", "img": "https://via.placeholder.com/150?text=Creed+Aventus"},
        {"brand": "DIOR", "name": "SAUVAGE", "price": "$145.00", "img": "https://via.placeholder.com/150?text=Dior+Sauvage"},
        {"brand": "MAISON ALHAMBRA", "name": "MIDNIGHT OUD", "price": "$110.00", "img": "https://via.placeholder.com/150?text=Midnight+Oud"},
        {"brand": "TOM FORD", "name": "OMBRE LEATHER", "price": "$145.00", "img": "https://via.placeholder.com/150?text=Ombre+Leather"}
    ]

    # Creador de 4 columnas
    cols = st.columns(4)
    for i, perfume in enumerate(trending_perfumes):
        with cols[i]:
            st.image(perfume["img"], use_container_width=True)
            st.markdown(f"<div class='product-title'>{perfume['name']}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='product-brand'>{perfume['brand']}</div>", unsafe_allow_html=True)
            st.write(f"Compara precios desde **{perfume['price']}**")
            
            # El botón de Midnight Oud lleva a la vista de los detalles
            if perfume["name"] == "MIDNIGHT OUD":
                st.button("Ver Ofertas", key=f"btn_{i}", on_click=navigate_to, args=('product',), use_container_width=True)
            else:
                st.button("Ver Ofertas", key=f"btn_{i}", use_container_width=True)

# ==========================================
# VISTA 2: DETALLE DE PRODUCTO (COMPARADOR)
# ==========================================
elif st.session_state['current_page'] == 'product':
    st.button("← Volver al inicio", on_click=navigate_to, args=('home',))
    st.write("")
    
    col_izq, col_der = st.columns([1, 2])
    
    with col_izq:
        st.image("https://via.placeholder.com/300?text=Midnight+Oud+Bottle", use_container_width=True)
        st.markdown("### MIDNIGHT OUD - EAU DE PARFUM")
        st.write("**50ml / 1.7 oz**")
        st.markdown("""
        * 🪵 **Madera de Oud:** Oud floral amaderado
        * 🌹 **Rosa Búlgara:** Rosa Búlgara fresca
        * 🍯 **Ámbar:** Ámbar cálido y resinoso
        """)
        # Placeholder para el gráfico del Hype Score (Diego y Alonso pls revisar)
        st.image("https://via.placeholder.com/300x100?text=Grafico+de+Tendencia+(Hype+Score)", use_container_width=True)

    with col_der:
        st.markdown("#### Comparación de Precios y Confianza")
        
        table_bg = "#1a1d24" if is_dark else "#f9f9f9"
        table_border = "#333333" if is_dark else "#dddddd"
        
        # Tabla HTML personalizada para replicar exactamente los badges del mockup
        tabla_html = f"""
        <table style="width:100%; text-align:center; border-collapse: collapse; color: {text_color};">
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
