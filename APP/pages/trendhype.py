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

is_dark = st.session_state['theme'] == 'dark'

app_bg_css = "background-color: #f6efe9 !important;" if not is_dark else "background-color: #0e1117 !important;"
text_color = "#ffffff" if is_dark else "#1a1a1a"
subtext_color = "#a0a0a0" if is_dark else "#c4b8ab"

btn_bg = "#1f242d" if is_dark else "#ffffff"
btn_border = "#3a3f4d" if is_dark else "#d4cdc5"
btn_hover_bg = "#2d3340" if is_dark else "#fcfaf8"

# VARIABLES Y SVGS PARA EL SWITCH DE TEMA (FRASCO DE PERFUME)
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

# 3. ESTILOS CSS REFINADOS (ELIMINACIÓN TOTAL DE MARGEN SUPERIOR)
st.markdown(f"""
    <style>
    /* Ocultar encabezados predeterminados y colapsar espacio superior */
    header[data-testid="stHeader"] {{ display: none !important; }}
    div[data-testid="stAppViewContainer"] {{ padding-top: 0px !important; }}
    
    .stApp {{ {app_bg_css} }}
    
    .main .block-container,
    div.block-container,
    [data-testid="stMainBlockContainer"],
    [data-testid="stAppViewBlockContainer"] {{
        padding-top: 0.5rem !important;
        margin-top: -3.5rem !important;
        padding-bottom: 2rem !important;
        max-width: 1200px !important;
    }}

    /* --- SWITCH DE TEMA ANIMADO EN FORMA DE BOTELLA --- */
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

    /* --- ESTILO DE FILTROS DESPLEGABLES --- */
    .filter-title {{
        color: {text_color} !important;
        font-weight: 800 !important;
        font-size: 1.1rem;
        margin: 0;
    }}
    
    div[data-baseweb="select"] > div {{
        background-color: #282933 !important;
        border: 1px solid #383946 !important;
        border-radius: 10px !important;
        color: #ffffff !important;
        font-weight: 600 !important;
        height: 42px !important;
    }}
    
    div[data-baseweb="select"] span, 
    div[data-baseweb="select"] div {{
        color: #ffffff !important;
        font-size: 14px !important;
    }}

    div[data-baseweb="select"] svg {{
        fill: #ffffff !important;
    }}
    
    div[data-testid="stSelectbox"] label {{
        display: none !important;
    }}

    /* Estilo del enlace superior central idéntico al original */
    .nav-back-link {{
        text-align: center;
        display: block;
        color: {subtext_color} !important;
        text-decoration: none !important;
        font-size: 0.95rem;
        font-weight: 500;
        transition: color 0.2s ease;
    }}
    .nav-back-link:hover {{
        color: {text_color} !important;
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

# 4. CABECERA SUPERIOR
col_logo, col_back, col_theme = st.columns([3, 4, 1], vertical_alignment="center")

with col_logo:
    logo_color = "#8c7b6d"
    logo_html = f"""
    <div style="display: flex; align-items: center; gap: 10px; cursor: pointer;" onclick="window.location.reload();">
        <svg width="38" height="38" viewBox="0 0 36 36" fill="none" stroke-linecap="round" stroke-linejoin="round">
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

with col_back:
    st.markdown('<a href="app.py" target="_self" class="nav-back-link">← Volver al Catálogo principal</a>', unsafe_allow_html=True)

with col_theme:
    st.button(" ", key="theme_toggle", on_click=toggle_theme)

# 5. TÍTULO Y FILTROS CENTRALIZADOS
st.markdown(f"<h1 style='text-align: center; color: {text_color}; font-weight: 800; font-size: 2.3rem; margin-top: 35px; margin-bottom: 35px;'>RADAR DEL HYPE - Viral Fragrances</h1>", unsafe_allow_html=True)

col_title, col_fecha, col_red, col_empty = st.columns([1.2, 2.2, 2.2, 3.5], vertical_alignment="center")

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
cols = st.columns(3, gap="medium")

for i, data in enumerate(hype_data):
    with cols[i]:
        html_card = f"""<div class="hype-card"><div class="rank-badge">{data['rank']}</div><div class="score-circle"><div class="score-title">HYPE<br>SCORE:</div><div class="score-value">{data['score']}</div></div><div class="img-wrapper"><img src="{data['img']}"><div class="year-badge">{data['year']}</div></div><div class="perfume-title">{data['name']}</div><div class="stats-row"><div class="stats-text">{data['stats']}</div><div class="chile-badge"><span style="font-size:14px;">👤</span><div>Disponible<br>en Chile 🇨🇱</div></div></div><div class="ai-box"><div class="ai-icon">AI</div><div>"{data['ai_text']}"</div></div><div class="price-text">Average market price: <b>{data['price']}</b></div></div>"""
        
        st.markdown(html_card, unsafe_allow_html=True)
        st.button("Comparar Precios", key=f"btn_compare_{i}", use_container_width=True)
