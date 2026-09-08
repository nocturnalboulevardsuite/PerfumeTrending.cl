import streamlit as st

# 1. Heredar el tema del session_state (para que no desentone con la app principal)
is_dark = st.session_state.get('theme', 'light') == 'dark'

bg_color = "#1f242d" if is_dark else "#ffffff"
text_color = "#ffffff" if is_dark else "#2c2c2c"
border_color = "#3a3f4d" if is_dark else "#d4cdc5"
ai_bg = "#2d3340" if is_dark else "#f8f9fa"

# 2. CSS personalizado para las tarjetas tipo "Radar"
st.markdown(f"""
    <style>
    header[data-testid="stHeader"] {{ display: none !important; }}
    .hype-card {{
        background-color: {bg_color};
        border: 2px solid {border_color};
        border-radius: 15px;
        padding: 20px;
        position: relative;
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
        color: {text_color};
    }}
    .rank-badge {{
        position: absolute;
        top: -15px;
        left: -15px;
        background: {text_color};
        color: {bg_color};
        font-size: 24px;
        font-weight: 900;
        padding: 10px 15px;
        border-radius: 8px;
        clip-path: polygon(0% 0%, 100% 0%, 100% 80%, 50% 100%, 0% 80%);
    }}
    .score-circle {{
        position: absolute;
        top: 10px;
        right: 10px;
        width: 70px;
        height: 70px;
        border-radius: 50%;
        border: 4px solid #e74c3c;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        font-weight: bold;
        line-height: 1.1;
    }}
    .score-circle span {{ font-size: 10px; color: #888; }}
    .score-circle div {{ font-size: 20px; }}
    .year-badge {{
        background-color: {border_color};
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: bold;
        float: right;
    }}
    .ai-box {{
        background-color: {ai_bg};
        border-left: 4px solid #3498db;
        padding: 12px;
        border-radius: 6px;
        font-size: 0.85rem;
        font-style: italic;
        margin: 15px 0;
        display: flex;
        gap: 10px;
        align-items: start;
    }}
    .ai-icon {{
        background: #3498db; color: white; border-radius: 50%; width: 24px; height: 24px;
        display: flex; justify-content: center; align-items: center; font-size: 10px; font-weight: bold;
    }}
    .stats-text {{ font-size: 0.85rem; color: #888; margin-bottom: 5px; }}
    .chile-badge {{
        display: inline-flex; align-items: center; gap: 5px;
        background: #ecf0f1; color: #2c3e50; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: bold;
    }}
    </style>
""", unsafe_allow_html=True)

# 3. Botón para volver al inicio
st.page_link("app.py", label="← Volver al Catálogo principal")

st.markdown(f"<h1 style='text-align: center; color: {text_color};'>RADAR DEL HYPE - Viral Fragrances</h1>", unsafe_allow_html=True)
st.write("")

# 4. Filtros superiores
col_filtro1, col_filtro2 = st.columns(2)
with col_filtro1:
    st.radio("Time Frame", ["Esta Semana", "Este Mes", "Este Año", "Año Pasado"], horizontal=True, index=1)
with col_filtro2:
    st.radio("Social Platform", ["TikTok", "Instagram", "Youtube"], horizontal=True, index=2)

st.divider()

# 5. Base de datos del Hype
hype_data = [
    {
        "rank": "#1", "name": "Bleu de Chanel", "score": "95%", "year": "2010", "price": "$180,000 CLP",
        "img": "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=500&q=80",
        "stats": "75 videos and 1.5 Million views in 1 month",
        "ai_text": "Trending due to fresh versatility and 'quiet luxury' aesthetic endorsement by major TikTok influencers."
    },
    {
        "rank": "#2", "name": "YSL Libre", "score": "90%", "year": "2019", "price": "$150,000 CLP",
        "img": "https://images.unsplash.com/photo-1592945403244-b3fbafd7f539?w=500&q=80",
        "stats": "60 videos and 1 Million views in 1 month",
        "ai_text": "Exploding in popularity for its bold floral lavender profile, often featured in 'best feminine scents' lists."
    },
    {
        "rank": "#3", "name": "Dior Sauvage", "score": "88%", "year": "2015", "price": "$165,000 CLP",
        "img": "https://images.unsplash.com/photo-1588405748880-12d1d2a59f75?w=500&q=80",
        "stats": "55 videos and 900k views in 1 month",
        "ai_text": "Continues viral dominance, praised for mass appeal and strong performance, sparking debate and reviews."
    }
]

# 6. Renderizar Tarjetas en 3 Columnas
cols = st.columns(3, gap="large")

for i, data in enumerate(hype_data):
    with cols[i]:
        html_card = f"""
        <div class="hype-card">
            <div class="rank-badge">{data['rank']}</div>
            <div class="score-circle">
                <span>HYPE</span>
                <div>{data['score']}</div>
            </div>
            
            <div style="text-align: center; margin-top: 30px; margin-bottom: 10px;">
                <img src="{data['img']}" style="width: 120px; height: 120px; object-fit: cover; border-radius: 10px;">
            </div>
            
            <div class="year-badge">{data['year']}</div>
            <h3 style="margin: 0; padding: 0;">{data['name']}</h3>
            
            <div style="display: flex; justify-content: space-between; align-items: end; margin-top: 10px;">
                <div class="stats-text" style="width: 60%;">{data['stats']}</div>
                <div class="chile-badge">✔️ Disponible 🇨🇱</div>
            </div>
            
            <div class="ai-box">
                <div class="ai-icon">AI</div>
                <div>"{data['ai_text']}"</div>
            </div>
            
            <p style="text-align: center; font-size: 0.9rem; margin-bottom: 15px;">
                Average market price: <strong>{data['price']}</strong>
            </p>
        </div>
        """
        st.markdown(html_card, unsafe_allow_html=True)
        # El botón de Streamlit va por fuera del HTML para que sea interactivo
        st.button("Comparar Precios", key=f"btn_compare_{i}", use_container_width=True)
