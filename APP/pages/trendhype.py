import streamlit as st

# 1. Configuración de la página e integración con el tema global
st.set_page_config(page_title="Radar del Hype - PerfumeTrending", layout="wide")

is_dark = st.session_state.get('theme', 'light') == 'dark'

# Paleta de colores adaptable al tema (Claro / Oscuro)
app_bg = "#0e1117" if is_dark else "#f6efe9"
card_bg = "#1f242d" if is_dark else "#ffffff"
text_color = "#ffffff" if is_dark else "#1a1a1a"
subtext_color = "#a0a0a0" if is_dark else "#666666"
border_color = "#3a3f4d" if is_dark else "#d4cdc5"
ai_bg = "#2d3340" if is_dark else "#f8f9fa"
badge_bg = "#2d3340" if is_dark else "#e8e2dc"

# 2. CSS Personalizado para emular el Mockup de la imagen
st.markdown(f"""
    <style>
    header[data-testid="stHeader"] {{ display: none !important; }}
    .stApp {{
        background-color: {app_bg} !important;
        color: {text_color} !important;
    }}
    
    /* Estilos del encabezado de filtros */
    .filter-header-title {{
        font-weight: bold;
        font-size: 1.1rem;
        color: {text_color};
    }}
    
    /* Estilos de la tarjeta principal */
    .hype-card {{
        background-color: {card_bg};
        border: 2px solid {border_color};
        border-radius: 18px;
        padding: 24px 18px 18px 18px;
        position: relative;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        color: {text_color};
        margin-top: 15px;
    }}
    
    /* Banderola de Ranking superior izquierda (#1, #2, #3) */
    .rank-badge {{
        position: absolute;
        top: -14px;
        left: 15px;
        background: {text_color};
        color: {card_bg};
        font-size: 22px;
        font-weight: 900;
        padding: 4px 14px;
        border-radius: 8px;
        border: 2px solid {border_color};
    }}
    
    /* Círculo de Hype Score superior derecho */
    .score-circle {{
        position: absolute;
        top: 15px;
        right: 15px;
        width: 70px;
        height: 70px;
        border-radius: 50%;
        border: 3px solid {text_color};
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        text-align: center;
        line-height: 1.1;
    }}
    
    .score-circle span {{
        font-size: 8px;
        font-weight: 800;
        color: {subtext_color};
        letter-spacing: 0.5px;
    }}
    
    .score-circle div {{
        font-size: 18px;
        font-weight: 900;
        color: {text_color};
    }}
    
    /* Insignia del año del perfume */
    .year-badge {{
        background-color: {badge_bg};
        color: {text_color};
        padding: 2px 8px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 700;
        border: 1px solid {border_color};
        display: inline-block;
    }}
    
    /* Bloque de Resumen IA */
    .ai-box {{
        background-color: {ai_bg};
        border: 1px solid {border_color};
        border-left: 4px solid #8c7b6d;
        padding: 10px 12px;
        border-radius: 10px;
        font-size: 0.8rem;
        margin: 12px 0;
        display: flex;
        gap: 8px;
        align-items: flex-start;
        line-height: 1.35;
    }}
    
    .ai-icon {{
        background: #8c7b6d;
        color: white;
        border-radius: 50%;
        min-width: 22px;
        height: 22px;
        display: flex;
        justify-content: center;
        align-items: center;
        font-size: 10px;
        font-weight: bold;
    }}
    
    /* Insignia de disponibilidad en Chile */
    .chile-badge {{
        display: inline-flex;
        align-items: center;
        gap: 4px;
        background: {badge_bg};
        color: {text_color};
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 0.72rem;
        font-weight: 600;
        border: 1px solid {border_color};
        white-space: nowrap;
    }}
    
    .stats-text {{
        font-size: 0.8rem;
        color: {subtext_color};
        font-weight: 600;
        line-height: 1.2;
    }}
    </style>
""", unsafe_allow_html=True)

# 3. Navegación superior
st.page_link("app.py", label="← Volver al Catálogo principal")

st.markdown(f"<h1 style='text-align: center; color: {text_color}; margin-bottom: 25px;'>RADAR DEL HYPE - Viral Fragrances</h1>", unsafe_allow_html=True)

# 4. Sección de Filtros traducida (Marco Temporal y Plataforma Social exclusivamente con YouTube)
col_lbl, col_tf, col_sp = st.columns([1.2, 4.5, 2.5], vertical_alignment="center")

with col_lbl:
    st.markdown(f"<div class='filter-header-title' style='text-align: right;'>Filtrar por :</div>", unsafe_allow_html=True)

with col_tf:
    st.caption("**Marco Temporal**")
    st.radio(
        "Marco Temporal", 
        ["Esta Semana", "Este Mes", "Este Año", "Año Pasado"], 
        horizontal=True, 
        index=1, 
        label_visibility="collapsed",
        key="time_frame"
    )

with col_sp:
    st.caption("**Plataforma Social**")
    st.radio(
        "Plataforma Social", 
        ["▶️ YouTube"], 
        horizontal=True, 
        index=0, 
        label_visibility="collapsed",
        key="social_platform"
    )

st.divider()

# 5. Datos estructurados de los Perfumes en Tendencia
hype_data = [
    {
        "rank": "#1", 
        "name": "Bleu de Chanel", 
        "score": "95%", 
        "year": "2010", 
        "price": "$180,000 CLP",
        "img": "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=500&q=80",
        "stats": "75 videos y 1.5 Millones de vistas en 1 mes",
        "ai_text": "En tendencia por su versatilidad fresca y estilo 'quiet luxury', ampliamente recomendado por creadores en YouTube."
    },
    {
        "rank": "#2", 
        "name": "YSL Libre", 
        "score": "90%", 
        "year": "2019", 
        "price": "$150,000 CLP",
        "img": "https://images.unsplash.com/photo-1592945403244-b3fbafd7f539?w=500&q=80",
        "stats": "60 videos y 1 Millón de vistas en 1 mes",
        "ai_text": "Popularidad en ascenso por su marcado perfil floral de lavanda, frecuente en tops de 'mejores perfumes femeninos'."
    },
    {
        "rank": "#3", 
        "name": "Dior Sauvage", 
        "score": "88%", 
        "year": "2015", 
        "price": "$165,000 CLP",
        "img": "https://images.unsplash.com/photo-1588405748880-12d1d2a59f75?w=500&q=80",
        "stats": "55 videos y 900k vistas en 1 mes",
        "ai_text": "Dominio viral continuo, elogiado por su gran atractivo masivo y excelente rendimiento en reseñas de YouTube."
    }
]

# 6. Renderizado en 3 Columnas estilo Mockup
cols = st.columns(3, gap="medium")

for i, data in enumerate(hype_data):
    with cols[i]:
        html_card = f"""
        <div class="hype-card">
            <div class="rank-badge">{data['rank']}</div>
            <div class="score-circle">
                <span>HYPE SCORE</span>
                <div>{data['score']}</div>
            </div>
            
            <div style="text-align: center; margin-top: 25px; margin-bottom: 10px;">
                <img src="{data['img']}" style="width: 120px; height: 120px; object-fit: cover; border-radius: 12px;">
            </div>
            
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <h3 style="margin: 0; font-size: 1.2rem; color: {text_color};">{data['name']}</h3>
                <div class="year-badge">{data['year']}</div>
            </div>
            
            <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 8px; gap: 5px;">
                <div class="stats-text" style="flex: 1;">{data['stats']}</div>
                <div class="chile-badge">👤 Disponible en Chile 🇨🇱</div>
            </div>
            
            <div class="ai-box">
                <div class="ai-icon">AI</div>
                <div>"{data['ai_text']}"</div>
            </div>
            
            <p style="text-align: center; font-size: 0.88rem; margin-bottom: 10px; color: {subtext_color};">
                Precio promedio de mercado: <strong style="color: {text_color};">{data['price']}</strong>
            </p>
        </div>
        """
        st.markdown(html_card, unsafe_allow_html=True)
        st.button("Comparar Precios", key=f"btn_compare_{i}", use_container_width=True)
