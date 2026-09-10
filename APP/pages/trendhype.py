import streamlit as st

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Radar del Hype - PerfumeTrending", layout="wide")

# 2. MANEJO DE ESTADO
if 'current_page' not in st.session_state:
    st.session_state['current_page'] = 'home'
if 'theme' not in st.session_state:
    st.session_state['theme'] = 'light'
if 'selected_month' not in st.session_state:
    st.session_state['selected_month'] = "Este Mes"

def toggle_theme():
    st.session_state['theme'] = 'dark' if st.session_state['theme'] == 'light' else 'light'

is_dark = st.session_state['theme'] == 'dark'

app_bg_css = "background-color: #f6efe9 !important;" if not is_dark else "background-color: #0e1117 !important;"
text_color = "#ffffff" if is_dark else "#1a1a1a"
subtext_color = "#a0a0a0" if is_dark else "#8c7b6d"

btn_bg = "#1f242d" if is_dark else "#ffffff"
btn_border = "#3a3f4d" if is_dark else "#d4cdc5"
btn_hover_bg = "#2d3340" if is_dark else "#fcfaf8"

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

# 3. ESTILOS CSS CORREGIDOS (AISLADOS)
st.markdown(f"""
    <style>
    header[data-testid="stHeader"] {{ display: none !important; }}
    div[data-testid="stAppViewContainer"] {{ padding-top: 0px !important; }}
    
    .stApp {{ {app_bg_css} }}
    
    .main .block-container,
    div.block-container,
    [data-testid="stMainBlockContainer"],
    [data-testid="stAppViewBlockContainer"] {{
        padding-top: 1.2rem !important;
        margin-top: 0rem !important;
        padding-bottom: 2rem !important;
        max-width: 1200px !important;
    }}

    /* SWITCH DE TEMA SIN ARTEFACTOS */
    .st-key-theme_toggle div[data-testid="stButton"] > button,
    .st-key-theme_toggle button {{
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        outline: none !important;
        padding: 0 !important;
        width: 82px !important;
        height: 48px !important;
        position: relative !important;
        cursor: pointer !important;
        margin-left: auto !important;
        display: block !important;
    }}

    .st-key-theme_toggle button * {{ display: none !important; }}
    
    .st-key-theme_toggle button::before {{
        content: '' !important;
        position: absolute !important;
        top: 7px !important; left: 0 !important;
        width: 80px !important; height: 36px !important;
        background-color: #2b2c34 !important;
        border: 2px solid #1a1b20 !important;
        border-radius: 20px !important;
        box-shadow: inset 0 2px 5px rgba(0,0,0,0.4) !important;
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
        filter: drop-shadow(2px 3px 4px rgba(0,0,0,0.3)) !important;
        z-index: 2 !important;
    }}

    /* TÍTULO Y TOOLTIP */
    .radar-title-container {{
        display: inline-flex;
        align-items: center;
        gap: 8px;
    }}

    .radar-title-text {{
        color: #d83737 !important;
        font-weight: 900 !important;
        font-size: 2rem !important;
        letter-spacing: 1px !important;
        margin: 0;
    }}

    .info-icon-container {{
        position: relative;
        display: inline-block;
    }}

    .info-btn-badge {{
        width: 18px;
        height: 18px;
        background: linear-gradient(135deg, #d83737 0%, #a81722 100%);
        color: #ffffff;
        border-radius: 50%;
        font-size: 11px;
        font-weight: 900;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
    }}

    .info-tooltip-box {{
        visibility: hidden;
        opacity: 0;
        width: 300px;
        background-color: {"#181a20" if is_dark else "#ffffff"};
        color: {text_color};
        border: 1px solid {"#343846" if is_dark else "#e2dacd"};
        border-radius: 10px;
        padding: 12px;
        position: absolute;
        top: 25px;
        left: -130px;
        z-index: 999;
        box-shadow: 0 10px 25px rgba(0,0,0,0.2);
        font-size: 0.85rem;
        transition: opacity 0.2s ease, visibility 0.2s ease;
    }}

    .info-icon-container:hover .info-tooltip-box {{
        visibility: visible;
        opacity: 1;
    }}

    .filter-label-text {{
        color: {text_color} !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
        margin: 0 !important;
        white-space: nowrap !important;
    }}

    /* FILTROS POPOVER */
    div[data-testid="stPopover"] > button {{
        background-color: {btn_bg} !important;
        border: 1px solid {btn_border} !important;
        border-radius: 8px !important;
        height: 36px !important;
        color: {text_color} !important;
        font-weight: 700 !important;
        font-size: 12px !important;
    }}

    /* SECCIÓN DE RED SOCIAL */
    .social-select-box {{
        display: flex !important;
        align-items: center !important;
        gap: 8px !important;
        color: {text_color};
        font-size: 13px;
        height: 36px !important;
    }}

    .social-label {{
        color: {subtext_color};
        font-weight: 600;
        white-space: nowrap;
    }}

    .yt-chip-btn {{
        display: inline-flex !important;
        align-items: center !important;
        gap: 6px;
        background-color: {btn_bg};
        border: 1px solid {btn_border};
        border-radius: 8px;
        padding: 0 10px;
        height: 32px !important;
        color: {text_color};
        font-weight: 700;
        font-size: 12px;
    }}

    .social-desc {{
        font-size: 11px;
        color: {subtext_color};
        font-style: italic;
    }}

    .nav-back-link {{
        text-align: right;
        display: block;
        color: {subtext_color} !important;
        text-decoration: none !important;
        font-size: 0.88rem;
        font-weight: 600;
    }}

    /* TARJETAS DE PERFUME INDEPENDIENTES */
    .hype-card {{
        background-color: {btn_bg};
        border: 2px solid {btn_border};
        border-radius: 12px;
        padding: 14px;
        position: relative;
        margin-top: 15px;
        margin-bottom: 12px;
        box-shadow: 2px 4px 10px rgba(0,0,0,0.08);
        color: {text_color};
        font-family: 'Inter', sans-serif;
        transition: transform 0.25s ease, border-color 0.25s ease;
    }}
    
    .hype-card:hover {{
        transform: translateY(-5px);
        border-color: #d83737;
    }}

    .rank-badge {{
        position: absolute; top: -12px; left: -8px;
        background-color: {btn_bg}; color: {text_color};
        font-size: 15px; font-weight: 900; padding: 2px 8px;
        border: 2px solid {btn_border}; border-radius: 6px;
        display: flex; align-items: center; gap: 4px; z-index: 2;
    }}

    .score-circle {{
        position: absolute; top: 10px; right: 10px; width: 52px; height: 52px; border-radius: 50%;
        border: 2px solid {btn_border}; display: flex; flex-direction: column; justify-content: center;
        align-items: center; background-color: {btn_bg};
    }}

    .score-title {{ font-size: 7px; font-weight: 800; text-align: center; color: {text_color}; }}
    .score-value {{ font-size: 14px; font-weight: 900; color: {text_color}; }}
    
    .img-wrapper {{ text-align: center; margin-top: 12px; position: relative; }}
    .img-wrapper img {{ 
        width: 100px; 
        height: 100px; 
        object-fit: contain; 
    }}

    .year-badge {{
        position: absolute; bottom: 0; right: 5px; background: {btn_bg}; border: 1px solid {btn_border};
        border-radius: 4px; padding: 1px 5px; font-size: 10px; font-weight: bold;
    }}
    .perfume-title {{ text-align: center; font-size: 14px; font-weight: bold; margin-top: 8px; margin-bottom: 8px; }}
    .stats-row {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; font-size: 10px; }}
    .stats-text {{ width: 55%; color: {text_color}; line-height: 1.2; }}
    .chile-badge {{
        display: flex; align-items: center; gap: 4px; background-color: {btn_hover_bg}; border: 1px solid {btn_border};
        border-radius: 12px; padding: 3px 6px; font-weight: bold; font-size: 9px;
    }}
    .ai-box {{
        display: flex; gap: 6px; align-items: center; border: 1px solid {btn_border}; border-radius: 8px;
        padding: 6px; margin-bottom: 8px; font-size: 10px; background-color: {btn_hover_bg};
    }}
    .ai-icon {{
        min-width: 20px; height: 20px; border-radius: 50%; border: 1px solid {btn_border}; display: flex;
        justify-content: center; align-items: center; font-weight: bold; font-size: 9px; background-color: {btn_bg};
    }}
    .price-text {{ text-align: center; font-size: 11px; color: {text_color}; margin-bottom: 6px; }}

    div[data-testid="stElementContainer"] > div.stButton > button:not([aria-label=" "]) {{
        background-color: #d83737 !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
        font-size: 12px !important;
        padding: 8px !important;
        width: 100% !important;
    }}
    </style>
""", unsafe_allow_html=True)

# 4. LOGO Y TEMAS
col_logo, col_theme = st.columns([6, 1], vertical_alignment="center")

with col_logo:
    logo_color = "#8c7b6d"
    logo_html = f"""
    <a href="app.py" target="_self" style="text-decoration: none; display: flex; align-items: center; gap: 10px;">
        <svg width="34" height="34" viewBox="0 0 36 36" fill="none">
            <path d="M 6.8 21 L 29.2 21 C 30 25 27 32 18 32 C 9 32 6 25 6.8 21 Z" fill="{logo_color}" />
            <line x1="6.8" y1="21" x2="29.2" y2="21" stroke="{text_color}" stroke-width="2" />
            <rect x="13" y="3" width="10" height="4" rx="1" stroke="{text_color}" stroke-width="2.5" />
        </svg>
        <span style="font-family: 'Inter', sans-serif; font-size: 1.4rem; color: {text_color};">
            <span style="font-weight: 800;">Perfume</span><span style="font-weight: 400;">Trending</span>
        </span>
    </a>
    """
    st.markdown(logo_html, unsafe_allow_html=True)

with col_theme:
    st.button(" ", key="theme_toggle", on_click=toggle_theme)

# SECCIÓN DE TÍTULO
col_header_title, col_back_btn = st.columns([3.4, 1], vertical_alignment="center")

with col_header_title:
    title_html = f"""
    <div class="radar-title-container">
        <h1 class="radar-title-text">RADAR DEL HYPE - VIRAL FRAGRANCES</h1>
        <div class="info-icon-container">
            <div class="info-btn-badge">i</div>
            <div class="info-tooltip-box">
                <div style="font-weight: 800; color: #d83737; margin-bottom: 4px;">📡 ¿Qué es el Radar del Hype?</div>
                Mide las fragancias más virales en tiempo real según menciones y reproducciones en <b>YouTube</b>.
            </div>
        </div>
    </div>
    """
    st.markdown(title_html, unsafe_allow_html=True)

with col_back_btn:
    st.markdown('<a href="app.py" target="_self" class="nav-back-link">← Volver al Catálogo principal</a>', unsafe_allow_html=True)

st.write("")

# 5. FILTROS EN LÍNEA
col_title, col_fecha, col_red = st.columns([0.15, 0.20, 0.65], gap="small", vertical_alignment="center")

with col_title:
    st.markdown("<div class='filter-label-text'>Filtrado por :</div>", unsafe_allow_html=True)

with col_fecha:
    opciones_fecha = ["Este Mes", "Hoy / Día", "Esta Semana", "Este Año", "Año Pasado"]
    with st.popover(f"📅 {st.session_state['selected_month']}", use_container_width=True):
        for opt in opciones_fecha:
            if st.button(opt, key=f"btn_m_{opt}", use_container_width=True):
                st.session_state['selected_month'] = opt
                st.rerun()

with col_red:
    social_select_html = f"""
    <div class="social-select-box">
        <span class="social-label">Red social analizada:</span>
        <div class="yt-chip-btn">
            <svg width="14" height="10" viewBox="0 0 26 20" fill="none">
                <rect x="1" y="1" width="24" height="18" rx="5" fill="#d83737" />
                <polygon points="10,5 18,10 10,15" fill="#ffffff" />
            </svg>
            <span>YouTube</span>
        </div>
        <span class="social-desc">(Mide popularidad en tiempo real según reseñas en video)</span>
    </div>
    """
    st.markdown(social_select_html, unsafe_allow_html=True)

st.write("")

# 6. DATOS DE TARJETAS (Imágenes estables SVG / Wikimedia para evitar errores de carga)
hype_data = [
    {
        "rank": "#1", "star": "✨", "name": "Bleu de Chanel", "score": "95%", "year": "2010", "price": "$180,000 CLP",
        "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/14/No5_Chanel.jpg/320px-No5_Chanel.jpg",
        "stats": "↗ 75 videos y 1.5M visitas este mes",
        "ai_text": "Tendencia por su versatilidad fresca y estética de 'lujo silencioso'."
    },
    {
        "rank": "#2", "star": "✨", "name": "YSL Libre EDP", "score": "90%", "year": "2019", "price": "$150,000 CLP",
        "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/14/No5_Chanel.jpg/320px-No5_Chanel.jpg",
        "stats": "↗ 60 videos y 1.0M visitas este mes",
        "ai_text": "Gran popularidad por su elegante nota de lavanda floral."
    },
    {
        "rank": "#3", "star": "✨", "name": "Dior Sauvage", "score": "88%", "year": "2015", "price": "$165,000 CLP",
        "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/14/No5_Chanel.jpg/320px-No5_Chanel.jpg",
        "stats": "↗ 55 videos y 900k visitas este mes",
        "ai_text": "Dominio constante en redes por su proyección masiva."
    },
    {
        "rank": "#4", "star": "", "name": "Baccarat Rouge 540", "score": "86%", "year": "2015", "price": "$310,000 CLP",
        "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/14/No5_Chanel.jpg/320px-No5_Chanel.jpg",
        "stats": "↗ 48 videos y 820k visitas este mes",
        "ai_text": "El aroma nicho dulzón y ambarado más influyente."
    },
    {
        "rank": "#5", "star": "", "name": "Club de Nuit Intense", "score": "84%", "year": "2015", "price": "$45,000 CLP",
        "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/14/No5_Chanel.jpg/320px-No5_Chanel.jpg",
        "stats": "↗ 42 videos y 750k visitas este mes",
        "ai_text": "Rey indiscutido en relación precio-calidad."
    },
    {
        "rank": "#6", "star": "", "name": "Angels' Share", "score": "82%", "year": "2020", "price": "$240,000 CLP",
        "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/14/No5_Chanel.jpg/320px-No5_Chanel.jpg",
        "stats": "↗ 38 videos y 680k visitas este mes",
        "ai_text": "Tendencia invernal gourmand con notas de licor."
    }
]

# 7. RENDERIZADO DE REJILLA LIMPISIMO
cols_per_row = 3
for row in range(0, len(hype_data), cols_per_row):
    cols = st.columns(cols_per_row, gap="medium")
    for i in range(cols_per_row):
        idx = row + i
        if idx < len(hype_data):
            data = hype_data[idx]
            with cols[i]:
                html_card = f"""
                <div class="hype-card">
                    <div class="rank-badge">{data['star']} {data['rank']}</div>
                    <div class="score-circle">
                        <div class="score-title">HYPE<br>SCORE</div>
                        <div class="score-value">{data['score']}</div>
                    </div>
                    <div class="img-wrapper">
                        <img src="{data['img']}" alt="{data['name']}">
                        <div class="year-badge">{data['year']}</div>
                    </div>
                    <div class="perfume-title">{data['name']}</div>
                    <div class="stats-row">
                        <div class="stats-text">{data['stats']}</div>
                        <div class="chile-badge">🇨🇱 Disponible</div>
                    </div>
                    <div class="ai-box">
                        <div class="ai-icon">AI</div>
                        <div>"{data['ai_text']}"</div>
                    </div>
                    <div class="price-text">Precio prom. mercado: <b>{data['price']}</b></div>
                </div>
                """
                st.markdown(html_card, unsafe_allow_html=True)
                st.button("Comparar Precios", key=f"btn_compare_{idx}", use_container_width=True)
