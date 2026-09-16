"""
PerfumeTrending.cl — Trust Score & Verificación Antifraude
----------------------------------------------------------
Directorio oficial y auditor en vivo de legitimidad de comercios
electrónicos de perfumería en Chile (Ley del Consumidor, SERNAC y NIC Chile).
"""

import streamlit as st
import os
import sys

# Asegurar que la raíz del proyecto esté en sys.path para importar backend
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

try:
    from backend.database import (
        obtener_tiendas_trust,
        auditar_tienda_por_url,
        init_db
    )
except ImportError:
    from database import (
        obtener_tiendas_trust,
        auditar_tienda_por_url,
        init_db
    )

@st.cache_data(ttl=60, show_spinner=False)
def cached_obtener_tiendas_trust(filtro_tipo=None, score_minimo=0, busqueda=""):
    return obtener_tiendas_trust(filtro_tipo=filtro_tipo, score_minimo=score_minimo, busqueda=busqueda)

# -----------------------------------------------------------------------------
# 1. CONFIGURACIÓN DE PÁGINA Y TEMA
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Trust Score Antifraude — PerfumeTrending",
    page_icon="🛡️",
    layout="wide"
)

if "theme" not in st.session_state:
    st.session_state.theme = "dark"

def toggle_theme():
    st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"

is_dark = st.session_state.theme == "dark"

bg_color = "#0B0E14" if is_dark else "#F8FAFC"
card_bg = "#151B28" if is_dark else "#FFFFFF"
border_color = "#232D42" if is_dark else "#E2E8F0"
text_color = "#F8FAFC" if is_dark else "#0F172A"
subtext_color = "#94A3B8" if is_dark else "#475569"
accent_color = "#38BDF8"
success_color = "#10B981"
warning_color = "#F59E0B"
danger_color = "#EF4444"

st.markdown(f"""
<style>
    .stApp {{
        background-color: {bg_color};
        color: {text_color};
    }}
    .trust-header {{
        background: linear-gradient(135deg, {"#1E293B, #0F172A" if is_dark else "#EFF6FF, #DBEAFE"});
        padding: 24px;
        border-radius: 16px;
        border: 1px solid {border_color};
        margin-bottom: 24px;
    }}
    .metric-card {{
        background: {card_bg};
        border: 1px solid {border_color};
        padding: 16px;
        border-radius: 12px;
        text-align: center;
    }}
    .metric-val {{
        font-size: 2rem;
        font-weight: 800;
        color: {accent_color};
    }}
    .metric-lbl {{
        font-size: 0.85rem;
        color: {subtext_color};
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }}
    .store-card {{
        background: {card_bg};
        border: 1px solid {border_color};
        border-radius: 14px;
        padding: 20px;
        margin-bottom: 18px;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }}
    .store-card:hover {{
        border-color: {accent_color};
        box-shadow: 0 8px 24px rgba(0,0,0,0.15);
    }}
    .score-badge {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: {"rgba(16, 185, 129, 0.15)" if is_dark else "#ECFDF5"};
        color: {success_color};
        padding: 6px 12px;
        border-radius: 9999px;
        font-weight: 700;
        font-size: 1.1rem;
        border: 1px solid {success_color};
    }}
    .audit-result {{
        background: {card_bg};
        border: 2px solid {accent_color};
        border-radius: 16px;
        padding: 24px;
        margin-top: 16px;
        margin-bottom: 24px;
    }}
    .badge-pill {{
        background: {"#1E293B" if is_dark else "#F1F5F9"};
        color: {subtext_color};
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
    }}
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. ENCABEZADO Y CONTROLES SUPERIORES
# -----------------------------------------------------------------------------
col_h1, col_h2 = st.columns([0.82, 0.18])

with col_h1:
    st.markdown("""
    <div class="trust-header">
        <h1 style="margin: 0; font-size: 2.2rem;">🛡️ Trust Score — Verificación Antifraude de Perfumerías</h1>
        <p style="margin: 8px 0 0 0; font-size: 1.05rem; opacity: 0.9;">
            Índice técnico de legitimidad y transparencia comercial para compras seguras de perfumería en Chile.
            Evaluación basada en <strong>NIC Chile, SERNAC, Cifrado SSL y Cámara de Comercio de Santiago</strong>.
        </p>
    </div>
    """, unsafe_allow_html=True)

with col_h2:
    st.write("")
    st.write("")
    btn_theme_lbl = "☀️ Modo Claro" if is_dark else "🌙 Modo Oscuro"
    st.button(btn_theme_lbl, on_click=toggle_theme, use_container_width=True)

# -----------------------------------------------------------------------------
# 3. KPIs DEL MERCADO CHILENO
# -----------------------------------------------------------------------------
tiendas_totales = cached_obtener_tiendas_trust()
total_comercios = len(tiendas_totales)
avg_trust = round(sum(t["trust_score"] for t in tiendas_totales) / max(total_comercios, 1), 1)
ccs_conteo = sum(1 for t in tiendas_totales if t["sello_ccs"])
pct_ccs = int((ccs_conteo / max(total_comercios, 1)) * 100)

kpi1, kpi2, kpi3, kpi4 = st.columns(4)

with kpi1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-val">{total_comercios}</div>
        <div class="metric-lbl">Comercios Auditados 🇨🇱</div>
    </div>
    """, unsafe_allow_html=True)

with kpi2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-val">{avg_trust} / 100</div>
        <div class="metric-lbl">Índice Promedio de Confianza</div>
    </div>
    """, unsafe_allow_html=True)

with kpi3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-val">{pct_ccs}%</div>
        <div class="metric-lbl">Con Sello Oficial CCS</div>
    </div>
    """, unsafe_allow_html=True)

with kpi4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-val">100%</div>
        <div class="metric-lbl">Garantía Legal / Retracto</div>
    </div>
    """, unsafe_allow_html=True)

st.write("")
st.divider()

# -----------------------------------------------------------------------------
# 4. AUDITOR ANTIFRAUDE EN VIVO
# -----------------------------------------------------------------------------
st.subheader("🔍 Auditor Antifraude en Vivo")
st.caption("Pega la URL de cualquier tienda o publicación para auditar su nivel de riesgo antes de comprar:")

col_input, col_btn = st.columns([0.8, 0.2])
with col_input:
    url_auditoria = st.text_input(
        "Ingresa la dirección web (URL):",
        placeholder="Ej: https://www.silkperfumes.cl o https://tienda-ejemplo.cl",
        label_visibility="collapsed"
    )
with col_btn:
    btn_auditar = st.button("🚀 Auditar Comercio", use_container_width=True, type="primary")

if btn_auditar and url_auditoria:
    res = auditar_tienda_por_url(url_auditoria)
    if res:
        score_val = res["score"]
        score_color = success_color if score_val >= 85 else (warning_color if score_val >= 70 else danger_color)
        
        st.markdown(f"""
        <div class="audit-result">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
                <div>
                    <h3 style="margin:0;">{res['nombre']} <span class="badge-pill">{res['tipo']}</span></h3>
                    <p style="margin:4px 0 0 0; color:{subtext_color};">Dominio auditado: <strong>{res['dominio']}</strong></p>
                </div>
                <div style="text-align:right;">
                    <div style="font-size:1.8rem; font-weight:800; color:{score_color};">
                        {score_val} <span style="font-size:1rem; color:{subtext_color};">/ 100</span>
                    </div>
                    <span style="font-size:0.85rem; font-weight:600; color:{score_color};">{res['badge']}</span>
                </div>
            </div>
            
            <hr style="border-color:{border_color}; margin:16px 0;">
            
            <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap:12px; margin-bottom:16px;">
                <div><strong>RUT Empresa:</strong> {res['rut']}</div>
                <div><strong>Certificado SSL:</strong> {"✅ Activo (HTTPS)" if res['ssl'] else "❌ Inseguro (HTTP)"}</div>
                <div><strong>Sello Cámara de Comercio:</strong> {"✅ Adherido" if res['sello_ccs'] else "ℹ️ No registrado"}</div>
                <div><strong>Historial SERNAC:</strong> {res['sernac']}</div>
            </div>
            
            <div style="background:{'rgba(56, 189, 248, 0.1)' if is_dark else '#F0F9FF'}; padding:12px; border-radius:8px; border-left:4px solid {accent_color};">
                <strong>💡 Recomendación del Sistema:</strong> {res['recomendacion']}
            </div>
        </div>
        """, unsafe_allow_html=True)

st.write("")
st.divider()

# -----------------------------------------------------------------------------
# 5. DIRECTORIO DE COMERCIOS AUDITADOS EN CHILE
# -----------------------------------------------------------------------------
st.subheader("🏬 Directorio Oficial de Perfumerías Verificadas en Chile")

col_f1, col_f2, col_f3 = st.columns([0.45, 0.35, 0.20])

with col_f1:
    busqueda_txt = st.text_input("🔍 Buscar por tienda, RUT o dominio:", placeholder="Ej: Silk, Falabella, 77.261...")

with col_f2:
    tipo_filtro = st.selectbox(
        "Tipo de Comercio:",
        ["Todas", "Gran Retail Oficial", "Importador Especializado", "Cadena Especializada", "Perfumería Independiente"]
    )

with col_f3:
    min_score = st.slider("Confianza mínima:", 0, 100, 85)

tiendas_filtradas = cached_obtener_tiendas_trust(
    filtro_tipo=tipo_filtro,
    score_minimo=min_score,
    busqueda=busqueda_txt
)

st.caption(f"Mostrando **{len(tiendas_filtradas)}** comercios que cumplen con los criterios de auditoría:")

if tiendas_filtradas:
    for t in tiendas_filtradas:
        with st.container():
            col_info, col_score = st.columns([0.72, 0.28])
            
            with col_info:
                st.markdown(f"""
                <div style="display:flex; align-items:center; gap:10px; margin-bottom:6px;">
                    <span style="font-size:1.8rem;">{t['logo_emoji']}</span>
                    <h3 style="margin:0; display:inline;">{t['nombre']}</h3>
                    <span class="badge-pill">{t['tipo_tienda']}</span>
                    <span style="font-size:0.85rem; color:{accent_color}; font-weight:600;">{t['badge']}</span>
                </div>
                <div style="font-size:0.9rem; color:{subtext_color}; line-height:1.6;">
                    📍 <strong>RUT:</strong> {t['rut']} &nbsp;|&nbsp; 
                    🏢 <strong>Casa Matriz:</strong> {t['direccion_fiscal']} &nbsp;|&nbsp;
                    📅 <strong>Antigüedad:</strong> {t['anios_antiguedad']} años en Chile<br>
                    🛡️ <strong>Garantía:</strong> {t['politica_devolucion']} &nbsp;|&nbsp;
                    🏛️ <strong>Sello CCS:</strong> {"✅ Adherido" if t['sello_ccs'] else "No requerido"} &nbsp;|&nbsp;
                    ⚖️ <strong>SERNAC:</strong> Reclamos {t['reclamos_sernac']}
                </div>
                """, unsafe_allow_html=True)
            
            with col_score:
                st.markdown(f"""
                <div style="text-align:right;">
                    <div class="score-badge">
                        🛡️ {t['trust_score']} / 100
                    </div>
                    <div style="color:#F59E0B; font-size:1rem; margin-top:4px;">
                        {"⭐" * int(t['estrellas'])} <span style="font-size:0.8rem; color:{subtext_color};">({t['estrellas']})</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                col_btn_visit, col_btn_cat = st.columns(2)
                with col_btn_visit:
                    st.link_button("🌐 Sitio Web", t["url_base"], use_container_width=True)
                with col_btn_cat:
                    if st.button("🛍️ Catálogo", key=f"cat_{t['id']}", use_container_width=True):
                        st.session_state["filtro_tienda_catalogo"] = t["nombre"]
                        st.switch_page("app.py")

            with st.expander(f"📊 Ver Desglose de Puntaje Técnico — {t['nombre']}"):
                p1, p2, p3, p4 = st.columns(4)
                with p1:
                    st.metric("🔒 Seguridad Web", f"{t['puntos_seguridad']} / 25 pts", "SSL/TLS 1.3")
                with p2:
                    st.metric("🏢 Legalidad & RUT", f"{t['puntos_legalidad']} / 25 pts", "SII Verificado")
                with p3:
                    st.metric("📦 Devolución & Retracto", f"{t['puntos_garantia']} / 25 pts", "Ley 19.496")
                with p4:
                    st.metric("🏅 Reputación & Sellos", f"{t['puntos_reputacion']} / 25 pts", f"Reclamos {t['reclamos_sernac']}")
            
            st.divider()
else:
    st.warning("No se encontraron comercios que coincidan con los filtros y el puntaje mínimo seleccionado.")

# -----------------------------------------------------------------------------
# 6. METODOLOGÍA Y CRITERIOS NORMATIVOS
# -----------------------------------------------------------------------------
st.write("")
with st.expander("ℹ️ ¿Cómo se calcula el Trust Score en PerfumeTrending? (Metodología Oficial)"):
    st.markdown("""
    El **Trust Score** es un algoritmo multifactorial diseñado específicamente para el mercado chileno de perfumería,
    orientado a prevenir estafas por perfumes falsificados (*testers*, réplicas no declaradas o tiendas clonadas en redes sociales):
    
    1. **Seguridad Web (25%):**
       - Certificado digital SSL/TLS vigente emitido por una entidad certificadora autorizada.
       - Implementación de pasarelas de pago auditadas por la CMF (Webpay Plus, Transbank, Mercado Pago).
    
    2. **Transparencia Legal y Tributaria (25%):**
       - Identificación tributaria verificable (RUT de persona jurídica en el Servicio de Impuestos Internos).
       - Dirección física y domicilio legal informado en la República de Chile.
    
    3. **Garantías y Derechos del Consumidor (25%):**
       - Respeto a la garantía legal de 6 meses (Ley del Consumidor Nº 19.496).
       - Política explícita de derecho a retracto en compras electrónicas (10 a 30 días).
    
    4. **Acreditación y Reputación Digital (25%):**
       - Registro de dominio oficial `.cl` gestionado por NIC Chile (Universidad de Chile).
       - Adhesión a sellos éticos de comercio (Cámara de Comercio de Santiago - CCS / Buenas Prácticas).
       - Tasa de resolución de reclamos en el SERNAC y plataformas de opinión ciudadana.
    """)
