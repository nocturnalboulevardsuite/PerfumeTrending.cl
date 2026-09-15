import streamlit as st

# -----------------------------------------------------------------------------
# 1. GESTIÓN DEL TEMA (CLARO / OSCURO)
# -----------------------------------------------------------------------------
if "theme" not in st.session_state:
    st.session_state.theme = "light"

def toggle_theme():
    st.session_state.theme = "dark" if st.session_state.theme == "light" else "light"

# Aplicar CSS dinámico según el estado del tema
is_dark = st.session_state.theme == "dark"

bg_color = "#0E1117" if is_dark else "#FFFFFF"
text_color = "#FAFAFA" if is_dark else "#111827"
card_bg = "#1E222D" if is_dark else "#F9FAFB"
border_color = "#30363D" if is_dark else "#E5E7EB"
subtext_color = "#9CA3AF" if is_dark else "#4B5563"

st.markdown(
    f"""
    <style>
    .stApp {{
        background-color: {bg_color};
        color: {text_color};
    }}
    .trust-card {{
        background-color: {card_bg};
        border: 1px solid {border_color};
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 12px;
    }}
    .trust-card h4 {{
        margin: 0 0 6px 0;
        color: {text_color};
    }}
    .trust-card p {{
        margin: 0;
        color: {subtext_color};
        font-size: 0.9rem;
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# -----------------------------------------------------------------------------
# 2. ENCABEZADO Y CONTROLES
# -----------------------------------------------------------------------------
col_title, col_toggle = st.columns([0.8, 0.2])

with col_title:
    st.title("🛡️ Páginas de Confianza")
    st.caption("Directorio de sitios web verificados y seguros.")

with col_toggle:
    icon = "☀️ Modo Claro" if is_dark else "🌙 Modo Oscuro"
    st.button(icon, on_click=toggle_theme, use_container_width=True)

st.divider()

# -----------------------------------------------------------------------------
# 3. FILTROS Y BÚSQUEDA
# -----------------------------------------------------------------------------
search_query = st.text_input("🔍 Buscar por nombre o dominio...", "")

cat_col, trust_col = st.columns(2)
with cat_col:
    category = st.selectbox("Categoría", ["Todas", "Finanzas", "Educación", "Tecnología", "Gobierno"])
with trust_col:
    min_rating = st.slider("Nivel de confianza mínimo", 1, 5, 4)

# -----------------------------------------------------------------------------
# 4. DATOS DE EJEMPLO Y RENDERIZADO
# -----------------------------------------------------------------------------
trusted_sites = [
    {
        "name": "Banco Nacional",
        "domain": "https://banconacional.example.com",
        "category": "Finanzas",
        "rating": 5,
        "description": "Entidad bancaria con cifrado SSL extremo y certificación oficial."
    },
    {
        "name": "Portal Educativo Abierto",
        "domain": "https://educacion.example.org",
        "category": "Educación",
        "rating": 4,
        "description": "Recursos académicos abiertos respaldados por universidades asociadas."
    },
    {
        "name": "Servicios Ciudadanos",
        "domain": "https://gobierno.example.gob",
        "category": "Gobierno",
        "rating": 5,
        "description": "Plataforma oficial de tramitación gubernamental con autenticación segura."
    },
]

# Filtrar resultados
filtered_sites = [
    site for site in trusted_sites
    if (search_query.lower() in site["name"].lower() or search_query.lower() in site["domain"].lower())
    and (category == "Todas" or site["category"] == category)
    and site["rating"] >= min_rating
]

# Mostrar los datos
if filtered_sites:
    for site in filtered_sites:
        stars = "⭐" * site["rating"]
        st.markdown(
            f"""
            <div class="trust-card">
                <h4>{site['name']} <span style="font-size:0.8rem; font-weight:normal;">({site['category']})</span></h4>
                <p><strong>URL:</strong> <a href="{site['domain']}" target="_blank" style="color:#3B82F6;">{site['domain']}</a></p>
                <p><strong>Confianza:</strong> {stars} ({site['rating']}/5)</p>
                <p style="margin-top:6px;">{site['description']}</p>
            </div>
            """,
            unsafe_allow_html=True
        )
else:
    st.info("No se encontraron páginas de confianza que coincidan con los filtros seleccionados.")
