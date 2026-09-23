import streamlit as st

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(
    page_title="PerfumeTrending — Verificación de Confianza",
    page_icon="🧴",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# HELPER: Limpia espacios/indentaciones iniciales para evitar que Streamlit Markdown convierta HTML en código
def clean_html(html_str: str) -> str:
    return "\n".join(line.strip() for line in html_str.splitlines())

# 2. GESTIÓN DEL TEMA Y ESTADO
if "theme" not in st.session_state:
    st.session_state.theme = "dark"

def toggle_theme():
    st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"

is_dark = st.session_state.theme == "dark"

# 3. PALETA DE COLORES Y SVGS
bg_color = "#0c0e12" if is_dark else "#f8f9fa"
card_bg = "#14171d" if is_dark else "#ffffff"
border_color = "#232730" if is_dark else "#e2e8f0"
text_color = "#f3f4f6" if is_dark else "#0f172a"
subtext_color = "#8e95a5" if is_dark else "#64748b"

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

# 4. ESTILOS CSS CON TIPOGRAFÍA ELEGANTE Y EDITORIAL
css_styles = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,500;0,600;0,700;1,400&family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"], .stApp {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    background-color: {bg_color} !important;
    color: {text_color} !important;
}}

header[data-testid="stHeader"] {{ display: none !important; }}

.block-container {{ 
    padding-top: 2rem !important; 
    padding-bottom: 2rem !important; 
    max-width: 1200px !important;
}}

/* TARJETA DE PRODUCTO MINIMALISTA */
.product-card {{
    background-color: {card_bg};
    border: 1px solid {border_color};
    border-radius: 16px;
    padding: 36px 32px 28px 32px;
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
}}

.product-title {{
    font-family: 'Cormorant Garamond', serif;
    font-size: 1.8rem;
    font-weight: 600;
    letter-spacing: 2px;
    margin: 20px 0 2px 0;
    text-transform: uppercase;
    color: {text_color};
}}

.product-subtitle {{
    font-size: 0.72rem;
    color: {subtext_color};
    font-weight: 500;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    margin-bottom: 28px;
}}

/* NOTAS OLFATIVAS */
.notes-container {{
    width: 100%;
    text-align: left;
    border-top: 1px solid {border_color};
    padding-top: 20px;
}}

.note-item {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 0;
    border-bottom: 1px dashed {border_color};
}}

.note-item:last-child {{
    border-bottom: none;
}}

.note-label {{
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 1.2px;
    color: {subtext_color};
    text-transform: uppercase;
}}

.note-value {{
    font-size: 0.85rem;
    font-weight: 500;
    color: {text_color};
}}

/* TABLA DE COMPARACIÓN */
.trust-table-container {{
    background-color: {card_bg};
    border: 1px solid {border_color};
    border-radius: 16px;
    padding: 12px;
}}

table.trust-table {{
    width: 100%;
    border-collapse: separate;
    border-spacing: 0 8px;
}}

table.trust-table th {{
    padding: 12px 18px;
    font-size: 0.68rem;
    font-weight: 700;
    text-transform: uppercase;
    color: {subtext_color};
    letter-spacing: 1.5px;
    border-bottom: 1px solid {border_color};
    text-align: left;
}}

table.trust-table td {{
    padding: 16px 18px;
    background-color: {bg_color};
    border-top: 1px solid {border_color};
    border-bottom: 1px solid {border_color};
    vertical-align: middle;
}}

table.trust-table tr td:first-child {{
    border-left: 1px solid {border_color};
    border-top-left-radius: 10px;
    border-bottom-left-radius: 10px;
    font-weight: 500;
    font-size: 0.75rem;
    color: {subtext_color};
}}

table.trust-table tr td:last-child {{
    border-right: 1px solid {border_color};
    border-top-right-radius: 10px;
    border-bottom-right-radius: 10px;
    text-align: right;
}}

.store-title {{
    font-weight: 600;
    font-size: 0.85rem;
    letter-spacing: 0.8px;
    text-transform: uppercase;
    color: {text_color};
}}

.price-tag {{
    font-family: 'Inter', sans-serif;
    font-size: 1rem;
    font-weight: 600;
    color: {text_color};
}}

/* BADGES DE ESTADO */
.status-badge-safe {{
    display: inline-flex;
    align-items: center;
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
    background: rgba(34, 197, 94, 0.08);
    color: #22c55e;
    border: 1px solid rgba(34, 197, 94, 0.2);
}}

.status-badge-danger {{
    display: inline-flex;
    align-items: center;
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
    background: rgba(239, 68, 68, 0.08);
    color: #ef4444;
    border: 1px solid rgba(239, 68, 68, 0.2);
}}

/* BOTONES ACCIÓN MINIMALISTAS */
.btn-buy-now {{
    background: {text_color};
    color: {bg_color} !important;
    font-weight: 600;
    font-size: 0.7rem;
    letter-spacing: 1px;
    padding: 9px 18px;
    border-radius: 8px;
    text-decoration: none !important;
    display: inline-block;
    text-transform: uppercase;
    transition: opacity 0.2s ease;
}}

.btn-buy-now:hover {{
    opacity: 0.85;
}}

.btn-buy-disabled {{
    background: transparent;
    color: {subtext_color} !important;
    border: 1px solid {border_color};
    font-weight: 600;
    font-size: 0.7rem;
    letter-spacing: 1px;
    padding: 9px 18px;
    border-radius: 8px;
    text-decoration: none !important;
    display: inline-block;
    text-transform: uppercase;
    cursor: not-allowed;
    opacity: 0.6;
}}

/* SWITCH FLOTANTE */
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
</style>
"""
st.markdown(clean_html(css_styles), unsafe_allow_html=True)

# 5. HEADER (LOGO + SWITCH)
col_head_logo, col_head_switch = st.columns([8, 2], vertical_alignment="center")

with col_head_logo:
    logo_color = "#c5a880" if is_dark else "#9a7b4f"
    logo_html = f"""
    <div style="display: inline-flex; align-items: center; gap: 12px; cursor: pointer;" onclick="window.location.reload();">
        <svg width="32" height="32" viewBox="0 0 36 36" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path d="M 6.8 21 L 29.2 21 C 30 25 27 32 18 32 C 9 32 6 25 6.8 21 Z" fill="{logo_color}" />
            <line x1="6.8" y1="21" x2="29.2" y2="21" stroke="{text_color}" stroke-width="1.5" />
            <line x1="18" y1="10" x2="18" y2="30" stroke="{text_color}" stroke-width="1" />
            <path d="M 18 32 C 9 32 5 24 7.5 17 C 9 12 13 10 15 10 L 21 10 C 23 10 27 12 28.5 17 C 31 24 27 32 18 32 Z" stroke="{text_color}" stroke-width="2" />
            <rect x="15" y="7" width="6" height="3" stroke="{text_color}" stroke-width="1.5" />
            <rect x="13" y="3" width="10" height="4" rx="1" stroke="{text_color}" stroke-width="1.5" />
            <rect x="16" y="0" width="4" height="3" rx="1" fill="{logo_color}" stroke="{text_color}" stroke-width="1" />
        </svg>
        <span style="font-size: 1.25rem; color: {text_color}; letter-spacing: 0.5px;">
            <span style="font-family: 'Cormorant Garamond', serif; font-weight: 500; font-size: 1.5rem;">Perfume</span><span style="font-family: 'Inter', sans-serif; font-weight: 700; font-size: 1.1rem; text-transform: uppercase; margin-left: 3px;">Trending</span>
        </span>
    </div>
    """
    st.markdown(clean_html(logo_html), unsafe_allow_html=True)

with col_head_switch:
    st.button(" ", on_click=toggle_theme, key="theme_toggle")

st.markdown(f"<hr style='border: none; border-top: 1px solid {border_color}; margin: 20px 0 28px 0;' />", unsafe_allow_html=True)

# 6. ESTRUCTURA PRINCIPAL
left_col, right_col = st.columns([1, 1.4], gap="large")

# --- COLUMNA IZQUIERDA: TARJETA DE PRODUCTO MINIMALISTA ---
with left_col:
    bottle_sketch_svg = f"""
    <svg viewBox="0 0 200 240" fill="none" xmlns="http://www.w3.org/2000/svg" style="width: 100%; height: auto; max-width: 160px;">
        <path d="M70 20 L130 20 L145 35 L145 55 L130 70 L70 70 L55 55 L55 35 Z" stroke="{text_color}" stroke-width="1.8" fill="{card_bg}"/>
        <rect x="75" y="70" width="50" height="15" stroke="{text_color}" stroke-width="1.2" fill="{card_bg}"/>
        <path d="M40 85 L160 85 L175 110 L175 210 L160 225 L40 225 L25 210 L25 110 Z" stroke="{text_color}" stroke-width="1.8" fill="{card_bg}"/>
        <rect x="55" y="115" width="90" height="65" stroke="{border_color}" stroke-width="1" fill="{bg_color}"/>
        <text x="100" y="132" font-size="5.5" font-weight="600" fill="{subtext_color}" text-anchor="middle" letter-spacing="1">SKETCHED SCENTS</text>
        <text x="100" y="150" font-size="9.5" font-weight="700" fill="{text_color}" text-anchor="middle" letter-spacing="1.5">MIDNIGHT</text>
        <text x="100" y="163" font-size="9.5" font-weight="700" fill="{text_color}" text-anchor="middle" letter-spacing="1.5">OUD</text>
        <text x="100" y="174" font-size="5" fill="{subtext_color}" text-anchor="middle">EAU DE PARFUM</text>
    </svg>
    """

    card_left_html = f"""
    <div class="product-card">
        <div style="width: 100%; display: flex; justify-content: center; margin-bottom: 12px;">
            {bottle_sketch_svg}
        </div>
        <div class="product-title">MIDNIGHT OUD</div>
        <div class="product-subtitle">EAU DE PARFUM — 50 ML / 1.7 OZ</div>
        
        <div class="notes-container">
            <div class="note-item">
                <span class="note-label">NOTA DE SALIDA</span>
                <span class="note-value">Madera de Oud Natural</span>
            </div>
            <div class="note-item">
                <span class="note-label">NOTA DE CORAZÓN</span>
                <span class="note-value">Rosa de Bulgaria</span>
            </div>
            <div class="note-item">
                <span class="note-label">NOTA DE FONDO</span>
                <span class="note-value">Ámbar Ahumado</span>
            </div>
        </div>
    </div>
    """
    st.markdown(clean_html(card_left_html), unsafe_allow_html=True)

# --- COLUMNA DERECHA: TABLA DE VERIFICACIÓN EN ESPAÑOL ---
with right_col:
    table_html = f"""
    <div class="trust-table-container">
        <table class="trust-table">
            <thead>
                <tr>
                    <th style="width: 8%;">#</th>
                    <th style="width: 32%;">TIENDA</th>
                    <th style="width: 18%;">PRECIO</th>
                    <th style="width: 24%;">VERIFICACIÓN</th>
                    <th style="width: 18%; text-align: right;">ACCIÓN</th>
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
                        <span class="status-badge-safe">VERIFICADO</span>
                    </td>
                    <td>
                        <a href="#" class="btn-buy-now">COMPRAR</a>
                    </td>
                </tr>
                <tr>
                    <td>02</td>
                    <td>
                        <div class="store-title">THE PERFUME BARN</div>
                    </td>
                    <td><span class="price-tag">$105.00</span></td>
                    <td>
                        <span class="status-badge-danger">ALTO RIESGO</span>
                    </td>
                    <td>
                        <span class="btn-buy-disabled">BLOQUEADO</span>
                    </td>
                </tr>
                <tr>
                    <td>03</td>
                    <td>
                        <div class="store-title">ELEGANT FRAGRANCE</div>
                    </td>
                    <td><span class="price-tag">$112.50</span></td>
                    <td>
                        <span class="status-badge-safe">VERIFICADO</span>
                    </td>
                    <td>
                        <a href="#" class="btn-buy-now">COMPRAR</a>
                    </td>
                </tr>
                <tr>
                    <td>04</td>
                    <td>
                        <div class="store-title">FRAGRANCE DIRECT</div>
                    </td>
                    <td><span class="price-tag">$108.99</span></td>
                    <td>
                        <span class="status-badge-safe">VERIFICADO</span>
                    </td>
                    <td>
                        <a href="#" class="btn-buy-now">COMPRAR</a>
                    </td>
                </tr>
            </tbody>
        </table>
    </div>
    """
    st.markdown(clean_html(table_html), unsafe_allow_html=True)
