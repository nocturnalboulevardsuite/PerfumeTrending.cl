import streamlit as st

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Radar del Hype - PerfumeTrending", layout="wide")

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

# 3. ESTILOS CSS REFINADOS (Desplegables Minimalistas)
st.markdown(f"""
    <style>
    header[data-testid="stHeader"] {{ display: none !important; }}
    .stApp {{ {app_bg_css} }}
    
    /* --- ESTILO MINIMALISTA PARA DESPLEGABLES (SELECTBOX) --- */
    
    /* Etiqueta y texto negro forzado en filtros */
    .filter-title {{
        color: #000000 !important;
        font-weight: 900 !important;
        font-size: 1.1rem;
        margin: 0;
    }}
    
    /* Contenedor del desplegable */
    div[data-baseweb="select"] > div {{
        background-color: #ffffff !important;
        border: 1.5px solid #000000 !important;
        border-radius: 25px !important;
        color: #000000 !important;
        font-weight: 600 !important;
        padding-left: 10px !important;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        transition: all 0.2s ease-in-out;
    }}
    
    div[data-baseweb="select"]:hover > div {{
        box-shadow: 0 4px 8px rgba(0,0,0,0.12);
        transform: translateY(-1px);
    }}
    
    /* Forzar texto dentro de los selectbox a negro */
    div[data-baseweb="select"] span, 
    div[data-baseweb="select"] div,
    div[data-baseweb="popover"] div {{
        color: #000000 !important;
        font-size: 13px !important;
    }}
    
    /* Ocultar etiquetas por defecto de Streamlit arriba de los inputs */
    div[data-testid="stSelectbox"] label {{
        display: none !important;
    }}

    /* --- ESTILOS DE LAS TARJETAS --- */
    .hype-card {{
        background-color: {btn_bg};
        border: 2px solid {btn_border};
        border-radius: 12px;
        padding: 20px;
        position: relative;
        margin-top: 25px;
        margin-bottom: 15px;
        box-shadow: 2px 4px 10px rgba(0,0,0,0.1);
        color: {text_color};
        font-family: 'Inter', sans-serif;
    }}
    .rank-badge {{
        position: absolute; top: -15px; left: -10px;
        background-color: {btn_bg}; color: {text_color};
        font-size: 24px; font-weight: 900; padding: 5px 12px;
        border: 2px solid {btn_border}; border-radius: 6px; box-shadow: 2px 2px 0px {btn_border}; z-index: 2;
    }}
    .score-circle {{
        position: absolute; top: 15px; right: 15px; width: 70px; height: 70px; border-radius: 50%;
        border: 3px solid {btn_border}; display: flex; flex-direction: column; justify-content: center;
        align-items: center; background-color: {btn_bg}; padding: 2px;
        box-shadow: inset 0 0 0 2px {btn_bg}, inset 0 0 0 3px {btn_border};
    }}
    .score-title {{ font-size: 8px; font-weight: 800; line-height: 1.1; text-align: center; color: {text_color}; }}
    .score-value {{ font-size: 18px; font-weight: 900; color: {text_color}; }}
    .img-wrapper {{ text-align: center; margin-top: 15px; position: relative; }}
    .img-wrapper img {{ width: 130px; height: 130px; object-fit: contain; }}
    .year-badge {{
        position: absolute; bottom: 0; right: 10px; background: {btn_bg}; border: 1px solid {btn_border};
        border-radius: 4px; padding: 2px 8px; font-size: 12px; font-weight: bold;
    }}
    .perfume-title {{ text-align: center; font-size: 16px; font-weight: bold; margin-top: 10px; margin-bottom: 15px; }}
    .stats-row {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; font-size: 11px; }}
    .stats-text {{ width: 55%; color: {text_color}; line-height: 1.3; }}
    .chile-badge {{
        display: flex; align-items: center; gap: 5px; background-color: {btn_hover_bg}; border: 1px solid {btn_border};
        border-radius: 20px; padding: 4px 8px; font-weight: bold; font-size: 10px; text-align: left; line-height: 1.1;
    }}
    .ai-box {{
        display: flex; gap: 10px; align-items: center; border: 1px solid {btn_border}; border-radius: 8px;
        padding: 10px; margin-bottom: 15px; font-size: 11px; line-height: 1.3; background-color: {btn_hover_bg};
    }}
    .ai-icon {{
        min-width: 26px; height: 26px; border-radius: 50%; border: 1px solid {btn_border}; display: flex;
        justify-content: center; align-items: center; font-weight: bold; font-size: 10px; background-color: {btn_bg};
    }}
    .price-text {{ text-align: center; font-size: 12px; color: {text_color}; margin-bottom: 10px; }}
    </style>
""", unsafe_allow_html=True)

# 4. NAVEGACIÓN SUPERIOR Y TÍTULO
st.page_link("app.py", label="← Volver al Catálogo principal")

st.markdown(f"<h1 style='text-align: center; color: {text_color}; font-weight: 800; font-size: 2.5rem; margin-bottom: 30px;'>RADAR DEL HYPE - Viral Fragrances</h1>", unsafe_allow_html=True)

# 5. FILTROS MINIMALISTAS (CLICK Y DESPLEGABLE)
col_title, col_fecha, col_red, col_espacio = st.columns([1.2, 2, 2, 3], vertical_alignment="center")

with col_title:
    st.markdown("<p class='filter-title'>Filtrar por :</p>", unsafe_allow_html=True)

with col_fecha:
    opcion_fecha = st.selectbox(
        "Filtrar por Fecha",
        ["📅 Fecha: Este Mes", "📅 Fecha: Esta Semana", "📅 Fecha: Este Año", "📅 Fecha: Año Pasado"],
        index=0
    )

with col_red:
    opcion_red = st.selectbox(
        "Plataforma Social",
        ["▶️ YouTube", "🎵 TikTok", "📸 Instagram"],
        index=0
    )

st.divider()

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
cols = st.columns(3, gap="medium")

for i, data in enumerate(hype_data):
    with cols[i]:
        html_card = f"""<div class="hype-card"><div class="rank-badge">{data['rank']}</div><div class="score-circle"><div class="score-title">HYPE<br>SCORE:</div><div class="score-value">{data['score']}</div></div><div class="img-wrapper"><img src="{data['img']}"><div class="year-badge">{data['year']}</div></div><div class="perfume-title">{data['name']}</div><div class="stats-row"><div class="stats-text">{data['stats']}</div><div class="chile-badge"><span style="font-size:14px;">👤</span><div>Disponible<br>en Chile 🇨🇱</div></div></div><div class="ai-box"><div class="ai-icon">AI</div><div>"{data['ai_text']}"</div></div><div class="price-text">Average market price: <b>{data['price']}</b></div></div>"""
        
        st.markdown(html_card, unsafe_allow_html=True)
        st.button("Comparar Precios", key=f"btn_compare_{i}", use_container_width=True)
