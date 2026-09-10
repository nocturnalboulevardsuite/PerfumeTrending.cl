import streamlit as st

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Radar del Hype - PerfumeTrending", layout="wide")

# Heredamos el tema
is_dark = st.session_state.get('theme', 'light') == 'dark'

# Paleta de colores para las tarjetas
app_bg = "#0e1117" if is_dark else "#f6efe9"
card_bg = "#1f242d" if is_dark else "#ffffff"
text_color = "#ffffff" if is_dark else "#1a1a1a"
border_color = "#555555" if is_dark else "#1a1a1a"
badge_bg = "#2d3340" if is_dark else "#f0f0f0"

# 2. ESTILOS CSS REFINADOS (Tarjetas + Nuevos Filtros Dinámicos)
st.markdown(f"""
    <style>
    header[data-testid="stHeader"] {{ display: none !important; }}
    .stApp {{ background-color: {app_bg} !important; }}
    
    /* --- ESTILO PARA FILTROS DINÁMICOS (PILLS) --- */
    
    /* Forzar color negro en todos los textos de los filtros */
    .filter-label, div[role="radiogroup"] p {{
        color: #000000 !important;
    }}
    
    /* Contenedor principal de las opciones */
    div[role="radiogroup"] {{
        display: flex;
        flex-direction: row;
        gap: 12px;
        align-items: center;
    }}
    
    /* Estilo del botón inactivo */
    div[role="radiogroup"] > label {{
        background-color: #ffffff !important;
        border: 1px solid #cccccc !important;
        border-radius: 30px !important;
        padding: 8px 18px !important;
        cursor: pointer;
        transition: all 0.2s ease-in-out;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }}
    
    /* Efecto Hover al pasar el mouse */
    div[role="radiogroup"] > label:hover {{
        border-color: #000000 !important;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        transform: translateY(-2px);
    }}
    
    /* Estilo del botón ACTIVO (Seleccionado) */
    div[role="radiogroup"] > label[data-checked="true"] {{
        background-color: #f8f9fa !important;
        border: 2px solid #000000 !important;
        padding: 7px 17px !important; /* Ajuste por el borde más grueso */
    }}
    
    div[role="radiogroup"] > label[data-checked="true"] p {{
        font-weight: 800 !important;
    }}
    
    /* Ocultar el círculo nativo de Streamlit */
    div[role="radiogroup"] > label > div:first-child {{
        display: none !important;
    }}
    
    /* --- ESTILOS DE LAS TARJETAS (Intactos y seguros) --- */
    .hype-card {{
        background-color: {card_bg};
        border: 2px solid {border_color};
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
        background-color: {card_bg}; color: {text_color};
        font-size: 24px; font-weight: 900; padding: 5px 12px;
        border: 2px solid {border_color}; border-radius: 6px; box-shadow: 2px 2px 0px {border_color}; z-index: 2;
    }}
    .score-circle {{
        position: absolute; top: 15px; right: 15px; width: 70px; height: 70px; border-radius: 50%;
        border: 3px solid {border_color}; display: flex; flex-direction: column; justify-content: center;
        align-items: center; background-color: {card_bg}; padding: 2px;
        box-shadow: inset 0 0 0 2px {card_bg}, inset 0 0 0 3px {border_color};
    }}
    .score-title {{ font-size: 8px; font-weight: 800; line-height: 1.1; text-align: center; color: {text_color}; }}
    .score-value {{ font-size: 18px; font-weight: 900; color: {text_color}; }}
    .img-wrapper {{ text-align: center; margin-top: 15px; position: relative; }}
    .img-wrapper img {{ width: 130px; height: 130px; object-fit: contain; }}
    .year-badge {{
        position: absolute; bottom: 0; right: 10px; background: {card_bg}; border: 1px solid {border_color};
        border-radius: 4px; padding: 2px 8px; font-size: 12px; font-weight: bold;
    }}
    .perfume-title {{ text-align: center; font-size: 16px; font-weight: bold; margin-top: 10px; margin-bottom: 15px; }}
    .stats-row {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; font-size: 11px; }}
    .stats-text {{ width: 55%; color: {text_color}; line-height: 1.3; }}
    .chile-badge {{
        display: flex; align-items: center; gap: 5px; background-color: {badge_bg}; border: 1px solid {border_color};
        border-radius: 20px; padding: 4px 8px; font-weight: bold; font-size: 10px; text-align: left; line-height: 1.1;
    }}
    .ai-box {{
        display: flex; gap: 10px; align-items: center; border: 1px solid {border_color}; border-radius: 8px;
        padding: 10px; margin-bottom: 15px; font-size: 11px; line-height: 1.3; background-color: {badge_bg};
    }}
    .ai-icon {{
        min-width: 26px; height: 26px; border-radius: 50%; border: 1px solid {border_color}; display: flex;
        justify-content: center; align-items: center; font-weight: bold; font-size: 10px; background-color: {card_bg};
    }}
    .price-text {{ text-align: center; font-size: 12px; color: {text_color}; margin-bottom: 10px; }}
    </style>
""", unsafe_allow_html=True)

# 3. NAVEGACIÓN SUPERIOR
st.page_link("app.py", label="← Volver al Catálogo principal")

st.markdown(f"<h1 style='text-align: center; color: {text_color}; font-weight: 800; font-size: 2.5rem; margin-bottom: 30px;'>RADAR DEL HYPE - Viral Fragrances</h1>", unsafe_allow_html=True)

# 4. FILTROS DINÁMICOS
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

# 5. BASE DE DATOS
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

# 6. RENDERIZADO DE TARJETAS (Comprimido para evitar errores de Markdown)
cols = st.columns(3, gap="medium")

for i, data in enumerate(hype_data):
    with cols[i]:
        html_card = f"""<div class="hype-card"><div class="rank-badge">{data['rank']}</div><div class="score-circle"><div class="score-title">HYPE<br>SCORE:</div><div class="score-value">{data['score']}</div></div><div class="img-wrapper"><img src="{data['img']}"><div class="year-badge">{data['year']}</div></div><div class="perfume-title">{data['name']}</div><div class="stats-row"><div class="stats-text">{data['stats']}</div><div class="chile-badge"><span style="font-size:14px;">👤</span><div>Disponible<br>en Chile 🇨🇱</div></div></div><div class="ai-box"><div class="ai-icon">AI</div><div>"{data['ai_text']}"</div></div><div class="price-text">Average market price: <b>{data['price']}</b></div></div>"""
        
        st.markdown(html_card, unsafe_allow_html=True)
        st.button("Comparar Precios", key=f"btn_compare_{i}", use_container_width=True)
