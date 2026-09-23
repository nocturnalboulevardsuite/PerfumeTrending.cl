import streamlit as st
import streamlit.components.v1 as components

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(
    page_title="PerfumeTrending - Nivel de Confianza",
    page_icon="🧴",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2. GESTIÓN DEL TEMA Y ESTADO
if "theme" not in st.session_state:
    st.session_state.theme = "dark"

def toggle_theme():
    st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"

is_dark = st.session_state.theme == "dark"

# 3. PALETA DE COLORES Y SVGS DEL SWITCH (INCORPORADO DE SWITCH_2)
bg_color = "#0c0e12" if is_dark else "#f9f9fb"
card_bg = "#14171d" if is_dark else "#ffffff"
border_color = "#2a2e39" if is_dark else "#e4e4e7"
text_color = "#f0f0f0" if is_dark else "#18181b"
subtext_color = "#9a9a9a" if is_dark else "#71717a"
accent_color = "#d4c2a5" if is_dark else "#8c7b6d"

badge_green_bg = "#162b1e" if is_dark else "#ecfdf5"
badge_green_text = "#b8f5c8" if is_dark else "#047857"
badge_green_border = "#2a543b" if is_dark else "#a7f3d0"

# Configuración del Switch
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

# 4. ESTILOS CSS ADAPTADOS AL MOCKUP
st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"], .stApp {{
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
        background-color: {bg_color} !important;
        color: {text_color} !important;
    }}

    header[data-testid="stHeader"] {{ display: none !important; }}
    
    .block-container {{ 
        padding-top: 1rem !important; 
        padding-bottom: 2rem !important; 
        max-width: 1320px !important;
    }}

    /* HEADER Y NAVEGACIÓN ESTILO MOCKUP */
    .nav-link {{
        text-decoration: none;
        color: {subtext_color};
        font-weight: 700;
        font-size: 0.95rem;
        letter-spacing: 0.5px;
        transition: color 0.2s ease;
    }}
    .nav-link:hover, .nav-link.active {{
        color: {text_color};
    }}
    
    /* BÚSQUEDA Y USUARIO EN NAVBAR */
    .search-box {{
        background-color: {card_bg};
        border: 1px solid {border_color};
        border-radius: 8px;
        padding: 6px 14px;
        display: flex;
        align-items: center;
        gap: 8px;
        color: {subtext_color};
        font-size: 0.85rem;
    }}
    .search-box input {{
        background: transparent;
        border: none;
        outline: none;
        color: {text_color};
        width: 100%;
    }}

    /* SECCIÓN IZQUIERDA: PRODUCTO SPOTLIGHT */
    .product-card {{
        background-color: {card_bg};
        border: 1px solid {border_color};
        border-radius: 16px;
        padding: 24px;
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
        box-shadow: 0 4px 20px rgba(0,0,0,0.06);
    }}
    .bottle-wrapper {{
        width: 100%;
        max-width: 240px;
        margin-bottom: 16px;
    }}
    .product-title {{
        font-size: 1.25rem;
        font-weight: 800;
        letter-spacing: 0.5px;
        margin: 8px 0 2px 0;
        text-transform: uppercase;
        color: {text_color};
    }}
    .product-subtitle {{
        font-size: 0.88rem;
        color: {subtext_color};
        font-weight: 600;
        margin-bottom: 20px;
    }}

    /* NOTAS OLFATIVAS DETALLADAS */
    .notes-container {{
        width: 100%;
        text-align: left;
        margin-bottom: 20px;
    }}
    .note-item {{
        display: flex;
        align-items: flex-start;
        gap: 10px;
        margin-bottom: 10px;
    }}
    .note-icon {{
        font-size: 1.2rem;
        line-height: 1;
    }}
    .note-info strong {{
        display: block;
        font-size: 0.88rem;
        color: {text_color};
    }}
    .note-info span {{
        font-size: 0.78rem;
        color: {subtext_color};
    }}

    /* GRÁFICO VIRALITY DE MOCKUP */
    .virality-box {{
        width: 100%;
        border-top: 1px solid {border_color};
        padding-top: 16px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }}

    /* TABLA DE COMPARACIÓN (DERECHA MOCKUP) */
    .trust-table-container {{
        background-color: {card_bg};
        border: 1px solid {border_color};
        border-radius: 16px;
        padding: 12px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.06);
    }}
    table.trust-table {{
        width: 100%;
        border-collapse: separate;
        border-spacing: 0 8px;
    }}
    table.trust-table th {{
        padding: 12px 16px;
        font-size: 0.85rem;
        font-weight: 800;
        text-transform: uppercase;
        color: {text_color};
        letter-spacing: 0.5px;
        border-bottom: 2px solid {border_color};
        text-align: center;
    }}
    table.trust-table td {{
        padding: 16px;
        background-color: {bg_color};
        border-top: 1px solid {border_color};
        border-bottom: 1px solid {border_color};
        vertical-align: middle;
        text-align: center;
    }}
    table.trust-table tr td:first-child {{
        border-left: 1px solid {border_color};
        border-top-left-radius: 12px;
        border-bottom-left-radius: 12px;
        font-weight: 700;
        font-size: 1.1rem;
    }}
    table.trust-table tr td:last-child {{
        border-right: 1px solid {border_color};
        border-top-right-radius: 12px;
        border-bottom-right-radius: 12px;
    }}

    .store-cell {{
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 10px;
        font-weight: 800;
        font-size: 0.95rem;
        text-transform: uppercase;
        line-height: 1.2;
    }}

    .price-tag {{
        font-size: 1.25rem;
        font-weight: 800;
        color: {text_color};
    }}

    /* BADGES DE ESTADO MOCKUP */
    .status-badge-safe {{
        background-color: #22c55e20;
        border: 1.5 solid #22c55e;
        color: #22c55e;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 800;
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }}
    .status-badge-danger {{
        background-color: #ef444420;
        border: 1.5px solid #ef4444;
        color: #ef4444;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 800;
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }}
    .status-subtext-safe {{
        font-size: 0.75rem;
        color: #22c55e;
        font-weight: 700;
        margin-top: 4px;
    }}
    .status-subtext-danger {{
        font-size: 0.75rem;
        color: #ef4444;
        font-weight: 700;
        margin-top: 4px;
    }}

    /* BOTONES DE COMPRA */
    .btn-buy-now {{
        background: linear-gradient(180deg, #3b82f6 0%, #1d4ed8 100%);
        color: #ffffff !important;
        font-weight: 700;
        font-size: 0.78rem;
        padding: 8px 16px;
        border-radius: 8px;
        text-decoration: none !important;
        display: inline-block;
        box-shadow: 0 2px 6px rgba(29, 78, 216, 0.3);
        transition: transform 0.15s ease;
    }}
    .btn-buy-now:hover {{
        transform: scale(1.03);
    }}
    .btn-buy-disabled {{
        background: #27272a;
        color: #71717a !important;
        font-weight: 700;
        font-size: 0.78rem;
        padding: 8px 16px;
        border-radius: 8px;
        text-decoration: none !important;
        display: inline-block;
        cursor: not-allowed;
    }}

    /* SWITCH NEUTRO Y FLOTANTE (ESTILO SWITCH_2) */
    .st-key-theme_toggle,
    .st-key-theme_toggle div[data-testid="stButton"] {{
        background: transparent !important;
        background-color: transparent !important;
    }}

    .st-key-theme_toggle div[data-testid="stButton"] > button,
    .st-key-theme_toggle button,
    .st-key-theme_toggle button:hover,
    .st-key-theme_toggle button:focus,
    .st-key-theme_toggle button:active,
    .st-key-theme_toggle button:focus-visible,
    div[data-testid="stElementContainer"].st-key-theme_toggle button {{
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

    /* Botón de Sonido */
    .sound-btn {{
        background: {card_bg};
        border: 1px solid {border_color};
        border-radius: 50%;
        width: 38px;
        height: 38px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        font-size: 1.05rem;
        transition: all 0.2s ease;
    }}
    .sound-btn:hover {{
        border-color: {accent_color};
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# 5. HEADER COMPLETO (LOGO + NAVEGACIÓN + BÚSQUEDA + SWITCH)
col_head_logo, col_head_nav, col_head_actions = st.columns([2.5, 4, 3.5], vertical_alignment="center")

with col_head_logo:
    logo_color = "#8c7b6d"
    logo_html = f"""
    <div style="display: inline-flex; align-items: center; gap: 10px; cursor: pointer;" onclick="window.location.reload();">
        <svg width="34" height="34" viewBox="0 0 36 36" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path d="M 6.8 21 L 29.2 21 C 30 25 27 32 18 32 C 9 32 6 25 6.8 21 Z" fill="{logo_color}" />
            <line x1="6.8" y1="21" x2="29.2" y2="21" stroke="{text_color}" stroke-width="1.5" />
            <line x1="18" y1="10" x2="18" y2="30" stroke="{text_color}" stroke-width="1" />
            <path d="M 18 32 C 9 32 5 24 7.5 17 C 9 12 13 10 15 10 L 21 10 C 23 10 27 12 28.5 17 C 31 24 27 32 18 32 Z" stroke="{text_color}" stroke-width="2" />
            <rect x="15" y="7" width="6" height="3" stroke="{text_color}" stroke-width="1.5" />
            <rect x="13" y="3" width="10" height="4" rx="1" stroke="{text_color}" stroke-width="1.5" />
            <rect x="16" y="0" width="4" height="3" rx="1" fill="{logo_color}" stroke="{text_color}" stroke-width="1" />
        </svg>
        <span style="font-size: 1.3rem; color: {text_color}; letter-spacing: 0.2px;">
            <span style="font-weight: 300;">Perfume</span><span style="font-weight: 800;">Trending</span>
        </span>
    </div>
    """
    st.markdown(logo_html, unsafe_allow_html=True)

with col_head_nav:
    st.markdown(
        """
        <div style="display: flex; gap: 24px; justify-content: center; align-items: center;">
            <a href="#" class="nav-link active">HOME</a>
            <a href="#" class="nav-link">TRENDING</a>
            <a href="#" class="nav-link">BRANDS</a>
            <a href="#" class="nav-link">REVIEWS</a>
        </div>
        """,
        unsafe_allow_html=True
    )

with col_head_actions:
    c_search, c_user, c_sound, c_theme = st.columns([3, 1, 1, 1.5], vertical_alignment="center")
    with c_search:
        st.markdown(
            """
            <div class="search-box">
                🔍 <input type="text" placeholder="Search..." />
            </div>
            """,
            unsafe_allow_html=True
        )
    with c_user:
        st.markdown("<div style='font-size:1.3rem; text-align:center; cursor:pointer;'>👤</div>", unsafe_allow_html=True)
    with c_sound:
        st.markdown('<button id="sound-toggle-btn" class="sound-btn" onclick="window.parent.toggleSoundMute()" title="Activar/Desactivar Sonido">🔊</button>', unsafe_allow_html=True)
    with c_theme:
        st.button(" ", on_click=toggle_theme, key="theme_toggle")

st.markdown("<hr style='border-color: {}; margin: 16px 0 24px 0;' />".format(border_color), unsafe_allow_html=True)

# 6. ESTRUCTURA PRINCIPAL EN DOS COLUMNAS (AL IGUAL QUE EL MOCKUP)
left_col, right_col = st.columns([1, 1.35], gap="large")

# --- COLUMNA IZQUIERDA: DETALLES DEL PERFUME & VIRALIDAD ---
with left_col:
    # Ilustración SVG del Perfume Sketched (Midnight Oud)
    bottle_sketch_svg = f"""
    <svg viewBox="0 0 200 240" fill="none" xmlns="http://www.w3.org/2000/svg" style="width: 100%; height: auto; max-width: 200px;">
        <!-- Cap/Tapón octogonal -->
        <path d="M70 20 L130 20 L145 35 L145 55 L130 70 L70 70 L55 55 L55 35 Z" stroke="{text_color}" stroke-width="2.5" fill="{card_bg}"/>
        <rect x="75" y="70" width="50" height="15" stroke="{text_color}" stroke-width="2" fill="{card_bg}"/>
        <!-- Frasco principal -->
        <path d="M40 85 L160 85 L175 110 L175 210 L160 225 L40 225 L25 210 L25 110 Z" stroke="{text_color}" stroke-width="3" fill="{card_bg}"/>
        <!-- Etiqueta Central -->
        <rect x="55" y="115" width="90" height="65" stroke="{text_color}" stroke-width="1.8" fill="{bg_color}"/>
        <text x="100" y="132" font-size="7" font-weight="bold" fill="{subtext_color}" text-anchor="middle">SKETCHED SCENTS CO.</text>
        <text x="100" y="150" font-size="11" font-weight="900" fill="{text_color}" text-anchor="middle">MIDNIGHT</text>
        <text x="100" y="163" font-size="11" font-weight="900" fill="{text_color}" text-anchor="middle">OUD</text>
        <text x="100" y="174" font-size="6" fill="{subtext_color}" text-anchor="middle">50ml / 1.7 oz</text>
        <!-- Trazos artisticos -->
        <path d="M30 115 L30 205 M170 115 L170 205" stroke="{text_color}" stroke-width="1" stroke-dasharray="2 2"/>
    </svg>
    """

    # Gráfico SVG del Trend Score
    trend_graph_svg = f"""
    <svg viewBox="0 0 220 90" fill="none" xmlns="http://www.w3.org/2000/svg" style="width: 100%;">
        <!-- Ejes -->
        <line x1="25" y1="10" x2="25" y2="70" stroke="{subtext_color}" stroke-width="1.5"/>
        <line x1="25" y1="70" x2="190" y2="70" stroke="{subtext_color}" stroke-width="1.5"/>
        <!-- Etiqueta Y -->
        <text x="12" y="45" font-size="8" fill="{subtext_color}" font-weight="bold" transform="rotate(-90 12 45)">Virality</text>
        <!-- Línea del gráfico -->
        <path d="M35 60 L85 52 L175 15" stroke="{text_color}" stroke-width="2.5"/>
        <!-- Puntos -->
        <circle cx="35" cy="60" r="3.5" fill="{bg_color}" stroke="{text_color}" stroke-width="2"/>
        <circle cx="85" cy="52" r="3.5" fill="{bg_color}" stroke="{text_color}" stroke-width="2"/>
        <circle cx="175" cy="15" r="3.5" fill="{bg_color}" stroke="{text_color}" stroke-width="2"/>
        <!-- Sombra debajo de la curva -->
        <path d="M35 60 L85 52 L175 15 L175 70 L35 70 Z" fill="{text_color}" fill-opacity="0.06"/>
        <!-- Etiquetas X -->
        <text x="35" y="82" font-size="7" fill="{subtext_color}" text-anchor="middle">1 Week Ago</text>
        <text x="85" y="82" font-size="7" fill="{subtext_color}" text-anchor="middle">2 Weeks Ago</text>
        <text x="175" y="82" font-size="7" fill="{subtext_color}" text-anchor="middle">Today</text>
    </svg>
    """

    card_left_html = f"""
    <div class="product-card">
        <div class="bottle-wrapper">
            {bottle_sketch_svg}
        </div>
        <div class="product-title">MIDNIGHT OUD – EAU DE PARFUM</div>
        <div class="product-subtitle">50ml / 1.7 oz</div>
        
        <div class="notes-container">
            <div class="note-item">
                <span class="note-icon">🪵</span>
                <div class="note-info">
                    <strong>Oud Wood</strong>
                    <span>Oud Wood, with set Oud Wood</span>
                </div>
            </div>
            <div class="note-item">
                <span class="note-icon">🌹</span>
                <div class="note-info">
                    <strong>Bulgarian Rose</strong>
                    <span>Bulgarian Rose, Bulgarian Rose</span>
                </div>
            </div>
            <div class="note-item">
                <span class="note-icon">🪨</span>
                <div class="note-info">
                    <strong>Amber</strong>
                    <span>Amber with mariong hair</span>
                </div>
            </div>
        </div>

        <div style="width:100%; text-align:left; font-size:0.8rem; font-weight:800; color:{text_color}; margin-bottom:4px;">
            Trend Score
        </div>
        <div class="virality-box">
            <div style="flex-grow:1;">
                {trend_graph_svg}
            </div>
            <div style="display:flex; flex-direction:column; gap:6px; padding-left:10px;">
                <span style="background:{bg_color}; border:1px solid {border_color}; border-radius:50%; width:22px; height:22px; display:inline-flex; align-items:center; justify-content:center; font-size:10px;">🎵</span>
                <span style="background:{bg_color}; border:1px solid {border_color}; border-radius:50%; width:22px; height:22px; display:inline-flex; align-items:center; justify-content:center; font-size:10px;">📷</span>
                <span style="background:{bg_color}; border:1px solid {border_color}; border-radius:50%; width:22px; height:22px; display:inline-flex; align-items:center; justify-content:center; font-size:10px;">🔗</span>
            </div>
        </div>
    </div>
    """
    st.markdown(card_left_html, unsafe_allow_html=True)

# --- COLUMNA DERECHA: TABLA DE COMPARACIÓN Y CONFIANZA ---
with right_col:
    table_html = f"""
    <div class="trust-table-container">
        <table class="trust-table">
            <thead>
                <tr>
                    <th style="width: 8%;">#</th>
                    <th style="width: 28%;">STORE</th>
                    <th style="width: 18%;">PRICE</th>
                    <th style="width: 26%;">NIVEL DE CONFIANZA</th>
                    <th style="width: 20%;">COMPRA AHORA</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>1</td>
                    <td>
                        <div class="store-cell">
                            <span style="font-size:1.2rem;">🧪</span>
                            <div>AURA<br/><span style="font-size:0.65rem; color:{subtext_color};">SCENTS</span></div>
                        </div>
                    </td>
                    <td><span class="price-tag">$110.00</span></td>
                    <td>
                        <div class="status-badge-safe">✓ CONFIRMADO</div>
                        <div class="status-subtext-safe">✔ Muy Seguro</div>
                    </td>
                    <td>
                        <a href="#" class="btn-buy-now">COMPRA AHORA</a>
                    </td>
                </tr>
                <tr>
                    <td>2</td>
                    <td>
                        <div class="store-cell">
                            <div>THE<br/>PERFUME<br/>BARN</div>
                        </div>
                    </td>
                    <td><span class="price-tag">$105.00</span></td>
                    <td>
                        <div class="status-badge-danger">✖ RIESGO ALTO</div>
                        <div class="status-subtext-danger">✖ Alerta Estafa</div>
                    </td>
                    <td>
                        <a href="#" class="btn-buy-disabled">COMPRA AHORA</a>
                    </td>
                </tr>
                <tr>
                    <td>3</td>
                    <td>
                        <div class="store-cell">
                            <div>ELEGANT<br/>FRAGRANCE</div>
                        </div>
                    </td>
                    <td><span class="price-tag">$112.50</span></td>
                    <td>
                        <div class="status-badge-safe">✓ CONFIRMADO</div>
                        <div class="status-subtext-safe">✔ Muy Seguro</div>
                    </td>
                    <td>
                        <a href="#" class="btn-buy-now">COMPRA AHORA</a>
                    </td>
                </tr>
                <tr>
                    <td>4</td>
                    <td>
                        <div class="store-cell">
                            <div>FRAGRANCE<br/>DIRECT</div>
                        </div>
                    </td>
                    <td><span class="price-tag">$108.99</span></td>
                    <td>
                        <div class="status-badge-safe">✓ CONFIRMADO</div>
                        <div class="status-subtext-safe">✔ Muy Seguro</div>
                    </td>
                    <td>
                        <a href="#" class="btn-buy-now">COMPRA AHORA</a>
                    </td>
                </tr>
            </tbody>
        </table>
    </div>
    """
    st.markdown(table_html, unsafe_allow_html=True)

# 7. SCRIPT INTEGRADO DE SONIDO Y EFECTOS
js_color_script = f"""
<script>
(function() {{
    const doc = window.parent.document;
    
    window.parent.soundMuted = window.parent.soundMuted || false;
    
    window.parent.playBubbleSound = function() {{
        if (window.parent.soundMuted) return;
        try {{
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            if (!AudioContext) return;
            if (!window.parent.audioCtx) {{
                window.parent.audioCtx = new AudioContext();
            }}
            const ctx = window.parent.audioCtx;
            if (ctx.state === 'suspended') {{
                ctx.resume();
            }}
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();

            osc.type = 'sine';
            const now = ctx.currentTime;

            osc.frequency.setValueAtTime(220, now);
            osc.frequency.exponentialRampToValueAtTime(750, now + 0.07);

            gain.gain.setValueAtTime(0.25, now);
            gain.gain.exponentialRampToValueAtTime(0.001, now + 0.07);

            osc.connect(gain);
            gain.connect(ctx.destination);

            osc.start(now);
            osc.stop(now + 0.07);
        }} catch(e) {{ console.error(e); }}
    }};

    window.parent.toggleSoundMute = function() {{
        window.parent.soundMuted = !window.parent.soundMuted;
        const btn = doc.getElementById('sound-toggle-btn');
        if (btn) {{
            btn.innerHTML = window.parent.soundMuted ? '🔇' : '🔊';
            btn.style.opacity = window.parent.soundMuted ? '0.55' : '1';
        }}
    }};
}})();
</script>
"""

components.html(js_color_script, height=0, width=0)
