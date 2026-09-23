import streamlit as st
import streamlit.components.v1 as components

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(
    page_title="PerfumeTrending — Trust Verification",
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

# 3. PALETA DE COLORES Y ESTILOS
bg_color = "#090a0f" if is_dark else "#f8f9fa"
card_bg = "#111319" if is_dark else "#ffffff"
border_color = "rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.08)"
text_color = "#f4f4f5" if is_dark else "#09090b"
subtext_color = "#71717a" if is_dark else "#71717a"
accent_color = "#2563eb" if is_dark else "#1d4ed8"

# Switch SVG
bottle_left_pos = "42px" if is_dark else "-2px"
static_icon_pos = "12px center" if is_dark else "calc(100% - 12px) center"

static_icon_svg = (
    "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23ffffff' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><circle cx='12' cy='12' r='4'/><line x1='12' y1='1' x2='12' y2='3'/><line x1='12' y1='21' x2='12' y2='23'/><line x1='4.22' y1='4.22' x2='5.64' y2='5.64'/><line x1='18.36' y1='18.36' x2='19.78' y2='19.78'/><line x1='1' y1='12' x2='3' y2='12'/><line x1='21' y1='12' x2='23' y2='12'/><line x1='4.22' y1='19.78' x2='5.64' y2='18.36'/><line x1='18.36' y1='5.64' x2='19.78' y2='4.22'/></svg>"
    if is_dark else
    "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23111111' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z'/></svg>"
)

bottle_svg = (
    "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 50 58'><rect x='18' y='2' width='14' height='7' rx='2' fill='%23ffffff' stroke='%23111111' stroke-width='2.5'/><rect x='21' y='9' width='8' height='5' fill='%23ffffff' stroke='%23111111' stroke-width='2.5'/><circle cx='25' cy='34' r='19' fill='%23ffffff' stroke='%23111111' stroke-width='2.5'/></svg>"
    if is_dark else
    "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 50 58'><rect x='18' y='2' width='14' height='7' rx='2' fill='%23111111' stroke='%23ffffff' stroke-width='2.5'/><rect x='21' y='9' width='8' height='5' fill='%23111111' stroke='%23ffffff' stroke-width='2.5'/><circle cx='25' cy='34' r='19' fill='%23111111' stroke='%23ffffff' stroke-width='2.5'/></svg>"
)

# 4. ESTILOS CSS MINIMALISTAS
st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"], .stApp {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        background-color: {bg_color} !important;
        color: {text_color} !important;
    }}

    header[data-testid="stHeader"] {{ display: none !important; }}
    
    .block-container {{ 
        padding-top: 1.5rem !important; 
        padding-bottom: 2rem !important; 
        max-width: 1280px !important;
    }}

    /* HEADER Y LOGO */
    .brand-logo {{
        display: flex;
        align-items: center;
        gap: 12px;
        letter-spacing: 2.5px;
        font-size: 0.95rem;
        font-weight: 700;
        text-transform: uppercase;
        color: {text_color};
    }}

    /* CARDS Y CONTENEDORES */
    .product-card {{
        background-color: {card_bg};
        border: 1px solid {border_color};
        border-radius: 12px;
        padding: 28px;
        display: flex;
        flex-direction: column;
        align-items: center;
    }}

    .product-title {{
        font-family: 'Space Grotesk', sans-serif;
        font-size: 1.15rem;
        font-weight: 700;
        letter-spacing: 1.5px;
        margin: 16px 0 4px 0;
        text-transform: uppercase;
        color: {text_color};
        text-align: center;
    }}

    .product-subtitle {{
        font-size: 0.75rem;
        color: {subtext_color};
        font-weight: 500;
        letter-spacing: 1px;
        text-transform: uppercase;
        margin-bottom: 24px;
    }}

    /* NOTAS OLFATIVAS MINIMALISTAS */
    .notes-container {{
        width: 100%;
        margin-bottom: 24px;
        border-top: 1px solid {border_color};
        padding-top: 16px;
    }}
    .note-item {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 8px 0;
        border-bottom: 1px dashed {border_color};
    }}
    .note-label {{
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 1px;
        color: {subtext_color};
        text-transform: uppercase;
    }}
    .note-value {{
        font-size: 0.82rem;
        font-weight: 500;
        color: {text_color};
    }}

    /* TABLA DE TRUST */
    .trust-table-container {{
        background-color: {card_bg};
        border: 1px solid {border_color};
        border-radius: 12px;
        padding: 8px;
    }}
    table.trust-table {{
        width: 100%;
        border-collapse: separate;
        border-spacing: 0 6px;
    }}
    table.trust-table th {{
        padding: 14px 16px;
        font-size: 0.7rem;
        font-weight: 700;
        text-transform: uppercase;
        color: {subtext_color};
        letter-spacing: 1.2px;
        border-bottom: 1px solid {border_color};
        text-align: left;
    }}
    table.trust-table td {{
        padding: 14px 16px;
        background-color: {bg_color};
        border-top: 1px solid {border_color};
        border-bottom: 1px solid {border_color};
        vertical-align: middle;
        font-size: 0.85rem;
    }}
    table.trust-table tr td:first-child {{
        border-left: 1px solid {border_color};
        border-top-left-radius: 8px;
        border-bottom-left-radius: 8px;
        color: {subtext_color};
        font-weight: 600;
        font-size: 0.75rem;
    }}
    table.trust-table tr td:last-child {{
        border-right: 1px solid {border_color};
        border-top-right-radius: 8px;
        border-bottom-right-radius: 8px;
        text-align: right;
    }}

    .store-title {{
        font-weight: 700;
        font-size: 0.88rem;
        letter-spacing: 0.8px;
        text-transform: uppercase;
        color: {text_color};
    }}

    .price-tag {{
        font-family: 'Space Grotesk', sans-serif;
        font-size: 1.05rem;
        font-weight: 700;
        color: {text_color};
    }}

    /* BADGES MINIMALISTAS */
    .badge-safe {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 10px;
        border-radius: 4px;
        font-size: 0.68rem;
        font-weight: 700;
        letter-spacing: 0.8px;
        text-transform: uppercase;
        background: rgba(34, 197, 94, 0.1);
        color: #22c55e;
        border: 1px solid rgba(34, 197, 94, 0.25);
    }}
    .badge-danger {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 10px;
        border-radius: 4px;
        font-size: 0.68rem;
        font-weight: 700;
        letter-spacing: 0.8px;
        text-transform: uppercase;
        background: rgba(239, 68, 68, 0.1);
        color: #ef4444;
        border: 1px solid rgba(239, 68, 68, 0.25);
    }}

    /* BOTONES MINIMALISTAS */
    .btn-buy {{
        background-color: {text_color};
        color: {bg_color} !important;
        font-weight: 600;
        font-size: 0.72rem;
        letter-spacing: 1px;
        padding: 8px 16px;
        border-radius: 6px;
        text-decoration: none !important;
        display: inline-block;
        text-transform: uppercase;
        transition: opacity 0.2s ease;
    }}
    .btn-buy:hover {{
        opacity: 0.85;
    }}
    .btn-disabled {{
        background-color: transparent;
        color: {subtext_color} !important;
        border: 1px solid {border_color};
        font-weight: 600;
        font-size: 0.72rem;
        letter-spacing: 1px;
        padding: 8px 16px;
        border-radius: 6px;
        display: inline-block;
        text-transform: uppercase;
        cursor: not-allowed;
    }}

    /* SWITCH CUSTOMIZADO */
    .st-key-theme_toggle button {{
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
        width: 82px !important;
        height: 38px !important;
        position: relative !important;
        cursor: pointer !important;
        margin-left: auto !important;
        display: block !important;
    }}
    .st-key-theme_toggle button * {{ display: none !important; }}
    .st-key-theme_toggle button::before {{
        content: '' !important;
        position: absolute !important;
        top: 2px !important; left: 0 !important;
        width: 80px !important; height: 34px !important;
        background-color: {card_bg} !important;
        border: 1px solid {border_color} !important;
        border-radius: 20px !important;
        box-image: none !important;
        background-image: url("{static_icon_svg}") !important;
        background-repeat: no-repeat !important;
        background-position: {static_icon_pos} !important;
        background-size: 16px 16px !important;
        transition: all 0.3s ease !important;
    }}
    .st-key-theme_toggle button::after {{
        content: '' !important;
        position: absolute !important;
        top: -3px !important;
        left: {bottle_left_pos} !important;
        width: 38px !important; height: 42px !important;
        background-image: url("{bottle_svg}") !important;
        background-repeat: no-repeat !important;
        background-size: contain !important;
        transition: left 0.3s cubic-bezier(0.16, 1, 0.3, 1) !important;
        z-index: 2 !important;
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# 5. HEADER MINIMALISTA (SOLO LOGO Y TEMA)
col_head_logo, col_head_actions = st.columns([8, 2], vertical_alignment="center")

with col_head_logo:
    logo_html = f"""
    <div class="brand-logo">
        <svg width="22" height="22" viewBox="0 0 36 36" fill="none">
            <rect x="13" y="2" width="10" height="4" rx="1" fill="{text_color}"/>
            <rect x="15" y="6" width="6" height="4" fill="{text_color}"/>
            <path d="M8 12 C8 10 10 10 18 10 C26 10 28 10 28 12 L30 30 C30 33 27 34 18 34 C9 34 6 33 6 30 Z" fill="none" stroke="{text_color}" stroke-width="2"/>
        </svg>
        <span>PERFUME<span style="opacity: 0.5; font-weight: 400;">TRENDING</span></span>
    </div>
    """
    st.markdown(logo_html, unsafe_allow_html=True)

with col_head_actions:
    st.button(" ", on_click=toggle_theme, key="theme_toggle")

st.markdown(f"<hr style='border: none; border-top: 1px solid {border_color}; margin: 20px 0 28px 0;' />", unsafe_allow_html=True)

# 6. ESTRUCTURA DE DOS COLUMNAS
left_col, right_col = st.columns([1, 1.4], gap="large")

# --- COLUMNA IZQUIERDA: PRODUCTO ---
with left_col:
    bottle_sketch_svg = f"""
    <svg viewBox="0 0 200 240" fill="none" xmlns="http://www.w3.org/2000/svg" style="width: 100%; height: auto; max-width: 180px;">
        <path d="M70 20 L130 20 L145 35 L145 55 L130 70 L70 70 L55 55 L55 35 Z" stroke="{text_color}" stroke-width="1.5" fill="{card_bg}"/>
        <rect x="75" y="70" width="50" height="15" stroke="{text_color}" stroke-width="1.2" fill="{card_bg}"/>
        <path d="M40 85 L160 85 L175 110 L175 210 L160 225 L40 225 L25 210 L25 110 Z" stroke="{text_color}" stroke-width="1.8" fill="{card_bg}"/>
        <rect x="55" y="115" width="90" height="65" stroke="{border_color}" stroke-width="1" fill="{bg_color}"/>
        <text x="100" y="132" font-size="6" font-weight="600" fill="{subtext_color}" text-anchor="middle" letter-spacing="1">SKETCHED SCENTS</text>
        <text x="100" y="150" font-size="10" font-weight="700" fill="{text_color}" text-anchor="middle" letter-spacing="1.5">MIDNIGHT</text>
        <text x="100" y="163" font-size="10" font-weight="700" fill="{text_color}" text-anchor="middle" letter-spacing="1.5">OUD</text>
        <text x="100" y="174" font-size="5.5" fill="{subtext_color}" text-anchor="middle" letter-spacing="0.5">EAU DE PARFUM</text>
    </svg>
    """

    trend_graph_svg = f"""
    <svg viewBox="0 0 220 70" fill="none" style="width: 100%;">
        <path d="M10 55 L75 45 L140 25 L210 10" stroke="{text_color}" stroke-width="1.5"/>
        <path d="M10 55 L75 45 L140 25 L210 10 L210 65 L10 65 Z" fill="{text_color}" fill-opacity="0.03"/>
        <circle cx="210" cy="10" r="3" fill="{text_color}"/>
    </svg>
    """

    card_left_html = f"""
    <div class="product-card">
        <div style="width: 100%; display: flex; justify-content: center;">
            {bottle_sketch_svg}
        </div>
        <div class="product-title">MIDNIGHT OUD</div>
        <div class="product-subtitle">EAU DE PARFUM — 50ML / 1.7 OZ</div>
        
        <div class="notes-container">
            <div class="note-item">
                <span class="note-label">TOP NOTE</span>
                <span class="note-value">Natural Oud Wood</span>
            </div>
            <div class="note-item">
                <span class="note-label">HEART NOTE</span>
                <span class="note-value">Bulgarian Rose</span>
            </div>
            <div class="note-item">
                <span class="note-label">BASE NOTE</span>
                <span class="note-value">Smokey Amber</span>
            </div>
        </div>

        <div style="width:100%; display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <span style="font-size: 0.68rem; font-weight: 700; letter-spacing: 1.2px; color: {subtext_color}; text-transform: uppercase;">VIRALITY METRICS</span>
            <span style="font-size: 0.68rem; font-weight: 700; color: {text_color};">98.4 / 100</span>
        </div>
        {trend_graph_svg}
    </div>
    """
    st.markdown(card_left_html, unsafe_allow_html=True)

# --- COLUMNA DERECHA: TABLA DE VERIFICACIÓN ---
with right_col:
    table_html = f"""
    <div class="trust-table-container">
        <table class="trust-table">
            <thead>
                <tr>
                    <th style="width: 6%;">#</th>
                    <th style="width: 30%;">RETAILER</th>
                    <th style="width: 20%;">PRICE</th>
                    <th style="width: 24%;">VERIFICATION</th>
                    <th style="width: 20%; text-align: right;">ACTION</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>01</td>
                    <td>
                        <div class="store-title">AURA SCENTS</div>
                    </td>
                    <td><span class="price-tag">$110.00</span></td>
                    <td>
                        <span class="badge-safe">VERIFIED</span>
                    </td>
                    <td>
                        <a href="#" class="btn-buy">PURCHASE</a>
                    </td>
                </tr>
                <tr>
                    <td>02</td>
                    <td>
                        <div class="store-title">THE PERFUME BARN</div>
                    </td>
                    <td><span class="price-tag">$105.00</span></td>
                    <td>
                        <span class="badge-danger">HIGH RISK</span>
                    </td>
                    <td>
                        <span class="btn-disabled">BLOCKED</span>
                    </td>
                </tr>
                <tr>
                    <td>03</td>
                    <td>
                        <div class="store-title">ELEGANT FRAGRANCE</div>
                    </td>
                    <td><span class="price-tag">$112.50</span></td>
                    <td>
                        <span class="badge-safe">VERIFIED</span>
                    </td>
                    <td>
                        <a href="#" class="btn-buy">PURCHASE</a>
                    </td>
                </tr>
                <tr>
                    <td>04</td>
                    <td>
                        <div class="store-title">FRAGRANCE DIRECT</div>
                    </td>
                    <td><span class="price-tag">$108.99</span></td>
                    <td>
                        <span class="badge-safe">VERIFIED</span>
                    </td>
                    <td>
                        <a href="#" class="btn-buy">PURCHASE</a>
                    </td>
                </tr>
            </tbody>
        </table>
    </div>
    """
    st.markdown(table_html, unsafe_allow_html=True)
