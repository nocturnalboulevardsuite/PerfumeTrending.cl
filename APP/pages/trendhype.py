import streamlit as st

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Radar del Hype - PerfumeTrending", layout="wide")

# 2. SISTEMA DE TEMA (CLARO / OSCURO) INTEGRADO
if 'theme' not in st.session_state:
    st.session_state.theme = 'light'

def toggle_theme():
    if st.session_state.theme == 'light':
        st.session_state.theme = 'dark'
    else:
        st.session_state.theme = 'light'

is_dark = st.session_state.theme == 'dark'

# Paleta de colores exacta para emular el mockup
app_bg = "#121212" if is_dark else "#F5F2ED"
card_bg = "#1E1E1E" if is_dark else "#FFFFFF"
text_color = "#FFFFFF" if is_dark else "#1A1A1A"
border_color = "#444444" if is_dark else "#1A1A1A"
badge_bg = "#2A2A2A" if is_dark else "#F0F0F0"

# 3. CSS GLOBAL Y ESTILOS
st.markdown(f"""
    <style>
    /* Ocultar barra superior por defecto de Streamlit */
    header[data-testid="stHeader"] {{ display: none !important; }}
    
    /* Forzar fondo de la aplicación */
    .stApp {{
        background-color: {app_bg} !important;
    }}
    
    /* Textos globales de Streamlit */
    .stMarkdown, .stText, h1, h2, h3, h4, h5, h6, label {{
        color: {text_color} !important;
    }}
    
    /* Estilos específicos de las tarjetas (Sin saltos de línea en el HTML después para evitar errores de Markdown) */
    .hype-card {{
        background-color: {card_bg};
        border: 2px solid {border_color};
        border-radius: 12px;
        padding: 20px;
        position: relative;
        margin-top: 30px;
        margin-bottom: 10px;
        box-shadow: 4px 4px 0px {border_color};
        color: {text_color};
        font-family: sans-serif;
    }}
    .rank-badge {{
        position: absolute; top: -18px; left: -10px;
        background-color: {card_bg}; color: {text_color};
        font-size: 24px; font-weight: 900; padding: 4px 14px;
        border: 2px solid {border_color}; border-radius: 8px;
    }}
    .score-circle {{
        position: absolute; top: 15px; right: 15px;
        width: 65px; height: 65px; border-radius: 50%;
        border: 2px solid {border_color};
        display: flex; flex-direction: column; justify-content: center; align-items: center;
        background-color: {card_bg};
    }}
    .score-title {{ font-size: 8px; font-weight: 800; text-align: center; line-height: 1.1; color: {text_color}; }}
    .score-value {{ font-size: 18px; font-weight: 900; color: {text_color}; }}
    .img-wrapper {{ text-align: center; margin-top: 25px; position: relative; display: flex; justify-content: center; }}
    .img-wrapper img {{ width: 140px; height: 140px; object-fit: contain; }}
    .year-badge {{
        position: absolute; bottom: 0; right: 20px;
        background: {card_bg}; border: 1px solid {border_color}; border-radius: 4px;
        padding: 2px 8px; font-size: 12px; font-weight: bold; color: {text_color};
    }}
    .perfume-title {{ text-align: center; font-size: 18px; font-weight: 900; margin-top: 15px; margin-bottom: 15px; color: {text_color}; }}
    .stats-row {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; font-size: 11px; }}
    .stats-text {{ width: 55%; line-height: 1.3; color: {text_color}; }}
    .chile-badge {{
        display: flex; align-items: center; gap: 5px;
        background-color: {badge_bg}; border: 1px solid {border_color}; border-radius: 20px;
        padding: 4px 10px; font-weight: bold; font-size: 10px; line-height: 1.1; color: {text_color};
    }}
    .ai-box {{
        display: flex; gap: 10px; align-items: center;
        border: 1px solid {border_color}; border-radius: 8px; padding: 10px; margin-bottom: 15px;
        font-size: 11px; line-height: 1.3; background-color: {badge_bg}; color: {text_color};
    }}
    .ai-icon {{
        min-width: 26px; height: 26px; border-radius: 50%; border: 1px solid {border_color};
        display: flex; justify-content: center; align-items: center; font-weight: bold; font-size: 10px;
        background-color: {card_bg}; color: {text_color};
    }}
    .price-text {{ text-align: center; font-size: 12px; color: {text_color}; margin-bottom: 5px; }}
    </style>
""", unsafe_allow_html=True)

# 4. NAVEGACIÓN Y BOTÓN DE TEMA
col_nav, col_space, col_theme = st.columns([2, 6, 1.5], vertical_alignment="center")
with col_nav:
    st.page_link("app.py", label="← Volver al Catálogo principal")
with col_theme:
    # Botón Toggle nativo de Streamlit
    st.toggle("☀️ / 🌙", value=is_dark, on_change=toggle_theme, key="theme_toggle")

st.markdown("<h1 style='text-align: center; font-weight: 900; font-size: 2.8rem; margin-bottom: 30px;'>RADAR DEL HYPE - Viral Fragrances</h1>", unsafe_allow_html=True)

# 5. FILTROS (Español, Solo YouTube)
col_filtro1, col_filtro2, col_filtro3 = st.columns([1.5, 4, 2], vertical_alignment="center")

with col_filtro1:
    st.markdown("<h4 style='margin: 0; font-weight: bold;'>Filtrar por :</h4>", unsafe_allow_html=True)

with col_filtro2:
    st.caption("Marco Temporal")
    st.radio("Marco Temporal", ["Esta Semana", "Este Mes", "Este Año", "Año Pasado"], horizontal=True, index=1, label_visibility="collapsed")

with col_filtro3:
    st.caption("Plataforma Social")
    st.radio("Plataforma Social", ["▶️ YouTube"], horizontal=True, index=0, label_visibility="collapsed")

st.write("")
st.write("")

# 6. BASE DE DATOS
hype_data = [
    {
        "rank": "#1", "name": "Bleu de Chanel", "score": "95%", "year": "2010", "price": "$180,000 CLP",
        "img": "https://fimgs.net/mdig/rx_perfume/58/28/6005828.jpg",
        "stats": "↗ 75 videos and 1.5 Million<br>views in 1 month",
        "ai_text": "Trending due to fresh versatility and 'quiet luxury' aesthetic endorsement by major YouTube influencers."
    },
    {
        "rank": "#2", "name": "YSL Libre", "score": "90%", "year": "2019", "price": "$150,000 CLP",
        "img": "https://fimgs.net/mdig/rx_perfume/56/55/5605655.jpg",
        "stats": "↗ 60 videos and 1 Million<br>views in 1 month",
        "ai_text": "Exploding in popularity for its bold floral lavender profile, often featured in 'best feminine scents' lists."
    },
    {
        "rank": "#3", "name": "Dior Sauvage", "score": "88%", "year": "2015", "price": "$165,000 CLP",
        "img": "https://fimgs.net/mdig/rx_perfume/31/86/31861.jpg",
        "stats": "↗ 55 videos and 900k<br>views in 1 month",
        "ai_text": "Continues viral dominance, praised for mass appeal and strong performance, sparking debate and reviews."
    }
]

# 7. RENDERIZADO DE TARJETAS
cols = st.columns(3, gap="large")

# NOTA IMPORTANTE: El bloque HTML está comprimido sin líneas en blanco.
# Esto es CRUCIAL para que Streamlit no lo convierta en un bloque de código negro.
for i, data in enumerate(hype_data):
    with cols[i]:
        html_card = f"""<div class="hype-card"><div class="rank-badge">{data['rank']}</div><div class="score-circle"><div class="score-title">HYPE<br>SCORE:</div><div class="score-value">{data['score']}</div></div><div class="img-wrapper"><img src="{data['img']}"><div class="year-badge">{data['year']}</div></div><div class="perfume-title">{data['name']}</div><div class="stats-row"><div class="stats-text">{data['stats']}</div><div class="chile-badge"><span style="font-size:14px;">👤</span><div>Disponible<br>en Chile 🇨🇱</div></div></div><div class="ai-box"><div class="ai-icon">AI</div><div>"{data['ai_text']}"</div></div><div class="price-text">Average market price: <b>{data['price']}</b></div></div>"""
        
        st.markdown(html_card, unsafe_allow_html=True)
        st.button("Comparar Precios", key=f"btn_compare_{i}", use_container_width=True)
