import streamlit as st

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

is_dark = st.session_state['theme'] == 'dark'

app_bg_css = "background-color: #f6efe9 !important;" if not is_dark else "background-color: #0e1117 !important;"
text_color = "#ffffff" if is_dark else "#1a1a1a"
subtext_color = "#a0a0a0" if is_dark else "#666666"

btn_bg = "#1f242d" if is_dark else "#ffffff"
btn_text = "#ffffff" if is_dark else "#2c2c2c"
btn_border = "#3a3f4d" if is_dark else "#d4cdc5"
btn_hover_bg = "#2d3340" if is_dark else "#fcfaf8"

input_bg = "#1f242d" if is_dark else "#252b36"
input_text = "#ffffff" if is_dark else "#ffffff"
input_border = "#3a3f4d" if is_dark else "#1a1a1a"

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
# 3. ESTILOS CSS REFINADOS
st.markdown(f"""
    <style>
    header[data-testid="stHeader"] {{ display: none !important; }}
    .stApp {{ {app_bg_css} }}
    
    /* --- ESTILO PARA FILTROS DINÁMICOS (PILLS) --- */
    .filter-label, div[role="radiogroup"] p {{
        color: #000000 !important;
    }}
    div[role="radiogroup"] {{ display: flex; flex-direction: row; gap: 12px; align-items: center; }}
    div[role="radiogroup"] > label {{
        background-color: #ffffff !important;
        border: 1px solid #cccccc !important;
        border-radius: 30px !important;
        padding: 8px 18px !important;
        cursor: pointer;
        transition: all 0.2s ease-in-out;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }}
    div[role="radiogroup"] > label:hover {{
        border-color: #000000 !important;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        transform: translateY(-2px);
    }}
    div[role="radiogroup"] > label[data-checked="true"] {{
        background-color: #f8f9fa !important;
        border: 2px solid #000000 !important;
        padding: 7px 17px !important; 
    }}
    div[role="radiogroup"] > label[data-checked="true"] p {{ font-weight: 800 !important; }}
    div[role="radiogroup"] > label > div:first-child {{ display: none !important; }}
    
    /* --- ESTILOS DE LAS TARJETAS INTEGRADOS CON NUEVO TEMA --- */
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

# 4. NAVEGACIÓN SUPERIOR
# Si deseas que el botón use la función nativa de tu nuevo estado, descomenta la de abajo y borra el page_link.
st.page_link("app.py", label="← Volver al Catálogo principal")
# st.button("← Volver al Catálogo principal", on_click=lambda: navigate_to('home'))

st.markdown(f"<h1 style='text-align: center; color: {text_color}; font-weight: 800; font-size: 2.5rem; margin-bottom: 30px;'>RADAR DEL HYPE - Viral Fragrances</h1>", unsafe_allow_html=True)

# 5. FILTROS DINÁMICOS
col_filtro1, col_filtro2, col_filtro3 = st.columns([1.2, 4, 2], vertical_alignment="center")

with col_filtro1:
    st.markdown(f"<h4 style='margin: 0; color: #000000; font-weight: 900;'>Filtrar por :</h4>", unsafe_allow_html=True)

with col_filtro2:
    st.markdown("<div class='filter-label' style='font-size: 12px; font-weight: bold; margin-bottom: 5px;'>Marco Temporal</div>", unsafe_allow_html=True)
    st.radio("Marco Temporal", ["Esta Semana", "Este Mes", "Este Año", "Año Pasado"], horizontal=True, index=1, label_visibility="collapsed")

with col_filtro3:
    st.markdown("<div class='filter-label' style='font-size: 12px; font-weight: bold; margin-bottom: 5px;'>Plataforma Social</div>", unsafe_allow_html=True)
    st.radio("Plataforma Social", ["▶️ YouTube"], horizontal=True, index=0, label_visibility="collapsed")

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
