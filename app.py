import streamlit as st
import pandas as pd

# 1. CONFIGURACIÓN DE la PÁGINA Y CSS CUSTOM 
st.set_page_config(page_title="PerfumeTrending", layout="wide", initial_sidebar_state="collapsed")

# CSS para replicar los botones y etiquetas (badges) como se mostraban en los mockups
st.markdown("""
    <style>
    .trust-badge-green {
        background-color: #d4edda; color: #155724; padding: 4px 10px; 
        border-radius: 4px; border: 1px solid #c3e6cb; font-size: 12px; font-weight: bold;
    }
    .trust-badge-red {
        background-color: #f8d7da; color: #721c24; padding: 4px 10px; 
        border-radius: 4px; border: 1px solid #f5c6cb; font-size: 12px; font-weight: bold;
    }
    .buy-btn {
        background-color: #4a86e8; color: white !important; padding: 6px 12px; 
        text-decoration: none; border-radius: 4px; font-size: 12px; font-weight: bold;
    }
    .product-title { font-size: 1.2rem; font-weight: bold; margin-bottom: 0; }
    .product-brand { font-size: 0.9rem; color: gray; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

# 2. MANEJO DE ESTADO (la Navegación)
if 'current_page' not in st.session_state:
    st.session_state['current_page'] = 'home'

def navigate_to(page):
    st.session_state['current_page'] = page

# 3. CABECERA GLOBAL (Los Header y el super Buscador)
col_logo, col_nav, col_mode = st.columns([2, 5, 1])
with col_logo:
    st.markdown("### 🏷️ PERFUME**TRENDING**")
with col_nav:
    st.markdown("**MEN** &nbsp;&nbsp;|&nbsp;&nbsp; **WOMEN** &nbsp;&nbsp;|&nbsp;&nbsp; **ARABIC** &nbsp;&nbsp;|&nbsp;&nbsp; **DESIGNER** &nbsp;&nbsp;|&nbsp;&nbsp; **NICHE**")
with col_mode:
    st.markdown("👤 Login | 🌗 Theme")

st.text_input("🔍 Search for perfume, brand, notes...", placeholder="Ej: Midnight Oud...")

st.divider()

# ==========================================
# VISTA 1: HOME o LOBBY (TRENDING en SOCIAL MEDIA)
# ==========================================
if st.session_state['current_page'] == 'home':
    st.markdown("<h3 style='text-align: center;'>TRENDING ON SOCIAL MEDIA</h3>", unsafe_allow_html=True)
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
            st.image(perfume["img"], use_column_width=True)
            st.markdown(f"<div class='product-title'>{perfume['name']}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='product-brand'>{perfume['brand']}</div>", unsafe_allow_html=True)
            st.write(f"Compare prices from **{perfume['price']}**")
            
            # El botón de Midnight Oud lleva a la vista de los detalles
            if perfume["name"] == "MIDNIGHT OUD":
                st.button("View Deals", key=f"btn_{i}", on_click=navigate_to, args=('product',), use_container_width=True)
            else:
                st.button("View Deals", key=f"btn_{i}", use_container_width=True)

# ==========================================
# VISTA 2: DETALLE DE PRODUCTO (COMPARADOR)
# ==========================================
elif st.session_state['current_page'] == 'product':
    st.button("← Volver al inicio", on_click=navigate_to, args=('home',))
    st.write("")
    
    col_izq, col_der = st.columns([1, 2])
    
    with col_izq:
        st.image("https://via.placeholder.com/300?text=Midnight+Oud+Bottle", use_column_width=True)
        st.markdown("### MIDNIGHT OUD - EAU DE PARFUM")
        st.write("**50ml / 1.7 oz**")
        st.markdown("""
        * 🪵 **Oud Wood:** Oud Wood with an Oud floral
        * 🌹 **Bulgarian Rose:** Bulgarian Rose, Bulgarian Rose
        * 🍯 **Amber:** Amber with morning hair
        """)
        # Placeholder para el gráfico del Hype Score (Diego y Alonso pls revisar)
        st.image("https://via.placeholder.com/300x100?text=Tendency+Graph+(Hype+Score)", use_column_width=True)

    with col_der:
        st.markdown("#### Comparación de Precios y Confianza")
        
        # Tabla HTML personalizada para replicar exactamente los badges del mockup
        tabla_html = """
        <table style="width:100%; text-align:center; border-collapse: collapse;">
            <tr style="border-bottom: 2px solid #ddd; background-color: #f9f9f9;">
                <th style="padding: 10px;">#</th>
                <th style="padding: 10px;">STORE</th>
                <th style="padding: 10px;">PRICE</th>
                <th style="padding: 10px;">NIVEL DE CONFIANZA</th>
                <th style="padding: 10px;">COMPRA AHORA</th>
            </tr>
            <tr style="border-bottom: 1px solid #eee;">
                <td style="padding: 15px;">1</td>
                <td><strong>AURA SCENTS</strong></td>
                <td><strong>$110.00</strong></td>
                <td>
                    <span class="trust-badge-green">✔️ CONFIRMADO</span><br>
                    <small style="color: green;">Muy Seguro</small>
                </td>
                <td><a href="#" class="buy-btn">COMPRA AHORA</a></td>
            </tr>
            <tr style="border-bottom: 1px solid #eee;">
                <td style="padding: 15px;">2</td>
                <td><strong>THE PERFUME BARN</strong></td>
                <td><strong>$105.00</strong></td>
                <td>
                    <span class="trust-badge-red">❌ RIESGO ALTO</span><br>
                    <small style="color: red;">Alerta Estafa</small>
                </td>
                <td><a href="#" class="buy-btn" style="background-color: #555;">COMPRA AHORA</a></td>
            </tr>
            <tr style="border-bottom: 1px solid #eee;">
                <td style="padding: 15px;">3</td>
                <td><strong>ELEGANT FRAGRANCE</strong></td>
                <td><strong>$112.50</strong></td>
                <td>
                    <span class="trust-badge-green">✔️ CONFIRMADO</span><br>
                    <small style="color: green;">Muy Seguro</small>
                </td>
                <td><a href="#" class="buy-btn">COMPRA AHORA</a></td>
            </tr>
            <tr>
                <td style="padding: 15px;">4</td>
                <td><strong>FRAGRANCE DIRECT</strong></td>
                <td><strong>$108.99</strong></td>
                <td>
                    <span class="trust-badge-green">✔️ CONFIRMADO</span><br>
                    <small style="color: green;">Muy Seguro</small>
                </td>
                <td><a href="#" class="buy-btn">COMPRA AHORA</a></td>
            </tr>
        </table>
        """
        st.markdown(tabla_html, unsafe_allow_html=True)
