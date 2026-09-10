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
subtext_color = "#a0a0a0" if is_dark else "#8c7b6d"

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

# 3. ESTILOS CSS REFINADOS
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

    /* SWITCH DE TEMA LIMPIO SIN BORDES ROJOS */
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
        margin-left: auto !important;
        margin-right: 0 !important;
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

    /* TÍTULO ANCHO, ROJIZO PERLADO Y CON HOVER OSCURO */
    .radar-title-text {{
        color: #d9787f !important;
        font-weight: 900 !important;
        font-size: 2.1rem !important;
        letter-spacing: 2.5px !important;
        margin: 0;
        display: inline-block;
        transition: color 0.3s ease, transform 0.3s ease !important;
        cursor: pointer;
    }}

    .radar-title-text:hover {{
        color: #7a1c24 !important;
    }}

    /* INFORMACIÓN DEL RADAR DESPLEGABLE ANIMADO */
    details.radar-dropdown {{
        background-color: {btn_bg};
        border: 1px solid {btn_border};
        border-radius: 12px;
        margin-top: 12px;
        margin-bottom: 20px;
        overflow: hidden;
        transition: all 0.3s ease;
        box-shadow: 0 4px 12px rgba(0,0,0,0.04);
    }}

    details.radar-dropdown summary {{
        padding: 12px 18px;
        font-size: 0.95rem;
        font-weight: 700;
        color: {text_color};
        cursor: pointer;
        list-style: none;
        display: flex;
        justify-content: space-between;
        align-items: center;
        user-select: none;
        transition: background-color 0.2s ease;
    }}

    details.radar-dropdown summary::-webkit-details-marker {{
        display: none;
    }}

    details.radar-dropdown summary:hover {{
        background-color: {btn_hover_bg};
    }}

    details.radar-dropdown[open] summary {{
        border-bottom: 1px solid {btn_border};
    }}

    .radar-dropdown-content {{
        padding: 14px 18px;
        color: {subtext_color};
        font-size: 0.88rem;
        line-height: 1.5;
        animation: fadeInSubtle 0.35s ease-in-out;
    }}

    @keyframes fadeInSubtle {{
        from {{ opacity: 0; transform: translateY(-6px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}

    /* FILTROS DESPLEGABLES Y CONTENEDOR DE RED SOCIAL TRANSPARENTE */
    .filter-title {{
        color: {text_color} !important;
        font-weight: 800 !important;
        font-size: 0.95rem;
        margin: 0;
    }}
    
    div[data-baseweb="select"] > div {{
        background-color: #282933 !important;
        border: 1px solid #383946 !important;
        border-radius: 10px !important;
        color: #ffffff !important;
        font-weight: 600 !important;
        height: 38px !important;
    }}
    
    div[data-baseweb="select"] span, 
    div[data-baseweb="select"] div {{
        color: #ffffff !important;
        font-size: 13px !important;
    }}

    div[data-baseweb="select"] svg {{
        fill: #ffffff !important;
    }}
    
    div[data-testid="stSelectbox"] label {{
        display: none !important;
    }}

    .social-select-box {{
        display: flex;
        align-items: center;
        gap: 10px;
        background-color: transparent;
        border: 1px solid transparent;
        border-radius: 10px;
        padding: 0;
        height: 38px;
        color: {text_color};
        font-weight: 600;
        font-size: 13px;
        width: 100%;
        box-sizing: border-box;
        box-shadow: none;
    }}

    .yt-chip {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background-color: transparent;
        border: 1px solid transparent;
        border-radius: 6px;
        padding: 2px 8px;
        color: {text_color};
        font-weight: 700;
    }}

    /* ENLACE DE NAVEGACIÓN A LA DERECHA */
    .nav-back-link {{
        text-align: right;
        display: block;
        color: {subtext_color} !important;
        text-decoration: none !important;
        font-size: 0.88rem;
        font-weight: 600;
        transition: color 0.2s ease;
        white-space: nowrap;
    }}
    .nav-back-link:hover {{
        color: {text_color} !important;
    }}

    /* TARJETAS CON ZOOM Y ELEVACIÓN DINÁMICA PROFESIONAL */
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
        transition: transform 0.32s cubic-bezier(0.25, 0.8, 0.25, 1), box-shadow 0.32s cubic-bezier(0.25, 0.8, 0.25, 1), border-color 0.32s ease;
        will-change: transform, box-shadow;
    }}
    
    .hype-card:hover {{
        transform: translateY(-8px) scale(1.025);
        box-shadow: 0 16px 30px rgba(0,0,0,0.16);
        border-color: #7a1c24;
    }}

    .rank-badge {{
        position: absolute; top: -12px; left: -8px;
        background-color: {btn_bg}; color: {text_color};
        font-size: 18px; font-weight: 900; padding: 3px 10px;
        border: 2px solid {btn_border}; border-radius: 6px; box-shadow: 2px 2px 0px {btn_border}; z-index: 2;
        transition: border-color 0.3s ease;
    }}
    .hype-card:hover .rank-badge {{
        border-color: #7a1c24;
    }}

    .score-circle {{
        position: absolute; top: 10px; right: 10px; width: 56px; height: 56px; border-radius: 50%;
        border: 2px solid {btn_border}; display: flex; flex-direction: column; justify-content: center;
        align-items: center; background-color: {btn_bg}; padding: 2px;
        box-shadow: inset 0 0 0 2px {btn_bg}, inset 0 0 0 2px {btn_border};
        transition: border-color 0.3s ease;
    }}
    .hype-card:hover .score-circle {{
        border-color: #7a1c24;
    }}

    .score-title {{ font-size: 7px; font-weight: 800; line-height: 1.0; text-align: center; color: {text_color}; }}
    .score-value {{ font-size: 15px; font-weight: 900; color: {text_color}; }}
    
    .img-wrapper {{ text-align: center; margin-top: 10px; position: relative; overflow: hidden; border-radius: 8px; }}
    .img-wrapper img {{ 
        width: 105px; 
        height: 105px; 
        object-fit: contain; 
        transition: transform 0.4s cubic-bezier(0.25, 0.8, 0.25, 1);
    }}
    
    .hype-card:hover .img-wrapper img {{
        transform: scale(1.12);
    }}

    .year-badge {{
        position: absolute; bottom: 0; right: 5px; background: {btn_bg}; border: 1px solid {btn_border};
        border-radius: 4px; padding: 1px 6px; font-size: 11px; font-weight: bold;
    }}
    .perfume-title {{ text-align: center; font-size: 14px; font-weight: bold; margin-top: 8px; margin-bottom: 10px; }}
    .stats-row {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; font-size: 10px; }}
    .stats-text {{ width: 55%; color: {text_color}; line-height: 1.25; }}
    .chile-badge {{
        display: flex; align-items: center; gap: 4px; background-color: {btn_hover_bg}; border: 1px solid {btn_border};
        border-radius: 16px; padding: 3px 6px; font-weight: bold; font-size: 9px; text-align: left; line-height: 1.1;
    }}
    .ai-box {{
        display: flex; gap: 8px; align-items: center; border: 1px solid {btn_border}; border-radius: 8px;
        padding: 8px; margin-bottom: 10px; font-size: 10px; line-height: 1.25; background-color: {btn_hover_bg};
    }}
    .ai-icon {{
        min-width: 22px; height: 22px; border-radius: 50%; border: 1px solid {btn_border}; display: flex;
        justify-content: center; align-items: center; font-weight: bold; font-size: 9px; background-color: {btn_bg};
    }}
    .price-text {{ text-align: center; font-size: 11px; color: {text_color}; margin-bottom: 6px; }}

    /* BOTONES COMPARAR PRECIOS EN ROJO VINO MATE */
    div[data-testid="stElementContainer"] > div.stButton > button:not([aria-label=" "]) {{
        background-color: #7a1c24 !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 700 !important;
        font-size: 13px !important;
        padding: 10px 16px !important;
        box-shadow: 0 3px 10px rgba(122, 28, 36, 0.25) !important;
        transition: transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1), background-color 0.2s ease, box-shadow 0.25s ease !important;
        width: 100% !important;
    }}

    div[data-testid="stElementContainer"] > div.stButton > button:not([aria-label=" "]):hover {{
        background-color: #5c131a !important;
        transform: scale(1.04) translateY(-2px) !important;
        box-shadow: 0 6px 16px rgba(122, 28, 36, 0.4) !important;
        color: #ffffff !important;
    }}

    div[data-testid="stElementContainer"] > div.stButton > button:not([aria-label=" "]):active {{
        transform: scale(0.98) translateY(0px) !important;
    }}
    </style>
""", unsafe_allow_html=True)

# 4. CABECERA CON LOGO REDIRIGIENDO AL HOME
col_logo, col_theme = st.columns([6, 1], vertical_alignment="center")

with col_logo:
    logo_color = "#8c7b6d"
    logo_html = f"""
    <a href="app.py" target="_self" style="text-decoration: none; display: flex; align-items: center; gap: 10px; cursor: pointer;">
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
    </a>
    """
    st.markdown(logo_html, unsafe_allow_html=True)

with col_theme:
    st.button(" ", key="theme_toggle", on_click=toggle_theme)

# SECCIÓN DEL TÍTULO CON TEXTO ROJIZO PERLADO Y BOTÓN VOLVER
st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
col_header_title, col_back_btn = st.columns([3.2, 1], vertical_alignment="center")

with col_header_title:
    st.markdown("<h1 class='radar-title-text'>RADAR DEL HYPE - VIRAL FRAGRANCES</h1>", unsafe_allow_html=True)

with col_back_btn:
    st.markdown('<a href="app.py" target="_self" class="nav-back-link">← Volver al Catálogo principal</a>', unsafe_allow_html=True)

# BANNER INFORMATIVO DESPLEGABLE Y SUAVE (RADAR DEL HYPE)
st.markdown(f"""
    <details class="radar-dropdown">
        <summary>
            <span>📡 ¿Qué es el Radar del Hype?</span>
            <span style="font-size: 0.8rem; opacity: 0.7;">▼ ver detalle</span>
        </summary>
        <div class="radar-dropdown-content">
            Es nuestro sistema inteligente que detecta qué fragancias se están volviendo virales en tiempo real a través de <b>YouTube</b>. Una herramienta clave para <b>revendedores, influencers y entusiastas</b> que buscan adelantarse al mercado y adquirir un perfume antes de que se agote o suba de precio.
        </div>
    </details>
""", unsafe_allow_html=True)

# 5. FILTROS CENTRALIZADOS BIEN DISTRIBUIDOS
col_title, col_fecha, col_red = st.columns([1.1, 2.8, 3.8], vertical_alignment="center")

with col_title:
    st.markdown("<p class='filter-title'>Filtrar por :</p>", unsafe_allow_html=True)

with col_fecha:
    opcion_fecha = st.selectbox(
        "Filtrar por Fecha",
        ["📅 Fecha: Este Mes", "📅 Fecha: Esta Semana", "📅 Fecha: Este Año", "📅 Fecha: Año Pasado"],
        index=0
    )

with col_red:
    social_select_html = f"""
    <div class="social-select-box">
        <span style="color: {subtext_color}; font-size: 13px;">Red social seleccionada:</span>
        <div class="yt-chip">
            <svg width="18" height="14" viewBox="0 0 26 20" fill="none">
                <rect x="1" y="1" width="24" height="18" rx="5" fill="#7a1c24" />
                <polygon points="10,5 18,10 10,15" fill="#ffffff" />
            </svg>
            <span>YouTube</span>
        </div>
    </div>
    """
    st.markdown(social_select_html, unsafe_allow_html=True)

st.write("")

# 6. BASE DE DATOS DE 6 PERFUMES
hype_data = [
    {
        "rank": "#1", "name": "Bleu de Chanel", "score": "95%", "year": "2010", "price": "$180,000 CLP",
        "img": "https://fimgs.net/mdig/rx_perfume/58/28/6005828.jpg",
        "stats": "↗ 75 videos y 1.5M<br>visitas este mes",
        "ai_text": "Tendencia por su versatilidad fresca y estética de 'lujo silencioso' en YouTube."
    },
    {
        "rank": "#2", "name": "YSL Libre EDP", "score": "90%", "year": "2019", "price": "$150,000 CLP",
        "img": "https://fimgs.net/mdig/rx_perfume/56/55/5605655.jpg",
        "stats": "↗ 60 videos y 1.0M<br>visitas este mes",
        "ai_text": "Gran popularidad por su elegante nota de lavanda floral para uso diario o de noche."
    },
    {
        "rank": "#3", "name": "Dior Sauvage", "score": "88%", "year": "2015", "price": "$165,000 CLP",
        "img": "https://fimgs.net/mdig/rx_perfume/31/86/31861.jpg",
        "stats": "↗ 55 videos y 900k<br>visitas este mes",
        "ai_text": "Dominio constante en redes por su proyección masiva y versatilidad inigualable."
    },
    {
        "rank": "#4", "name": "Baccarat Rouge 540", "score": "86%", "year": "2015", "price": "$310,000 CLP",
        "img": "https://fimgs.net/mdig/rx_perfume/30/88/30886.jpg",
        "stats": "↗ 48 videos y 820k<br>visitas este mes",
        "ai_text": "El aroma nicho dulzón y ambarado más clonado e influyente de YouTube."
    },
    {
        "rank": "#5", "name": "Club de Nuit Intense", "score": "84%", "year": "2015", "price": "$45,000 CLP",
        "img": "https://fimgs.net/mdig/rx_perfume/27/65/27656.jpg",
        "stats": "↗ 42 videos y 750k<br>visitas este mes",
        "ai_text": "Rey indiscutido de las fragancias árabes relación precio-calidad."
    },
    {
        "rank": "#6", "name": "Angels' Share", "score": "82%", "year": "2020", "price": "$240,000 CLP",
        "img": "https://fimgs.net/mdig/rx_perfume/62/61/62615.jpg",
        "stats": "↗ 38 videos y 680k<br>visitas este mes",
        "ai_text": "Tendencia invernal gourmand con notas de licor de canela y praliné."
    }
]

# 7. RENDERIZADO DE 6 TARJETAS EN REJILLA (2 FILAS DE 3 COLUMNAS)
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
                    <div class="rank-badge">{data['rank']}</div>
                    <div class="score-circle">
                        <div class="score-title">HYPE<br>SCORE:</div>
                        <div class="score-value">{data['score']}</div>
                    </div>
                    <div class="img-wrapper">
                        <img src="{data['img']}">
                        <div class="year-badge">{data['year']}</div>
                    </div>
                    <div class="perfume-title">{data['name']}</div>
                    <div class="stats-row">
                        <div class="stats-text">{data['stats']}</div>
                        <div class="chile-badge">
                            <span style="font-size:12px;">👤</span>
                            <div>Disponible<br>en Chile 🇨🇱</div>
                        </div>
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
