import streamlit as st
import streamlit.components.v1 as components

# 1. CONFIGURACIÓN DE LA PÁGINA Y ESTADO
st.set_page_config(page_title="PerfumeTrending", layout="wide", initial_sidebar_state="collapsed")

if 'current_page' not in st.session_state:
    st.session_state['current_page'] = 'home'
if 'theme' not in st.session_state:
    st.session_state['theme'] = 'dark'
if 'selected_perfume' not in st.session_state:
    st.session_state['selected_perfume'] = None

def toggle_theme():
    st.session_state['theme'] = 'dark' if st.session_state['theme'] == 'light' else 'light'

def navigate_to(page, perfume_data=None):
    st.session_state['current_page'] = page
    if perfume_data:
        st.session_state['selected_perfume'] = perfume_data

is_dark = st.session_state['theme'] == 'dark'

# Colores generales refinados (Estilo Sobrio y Profesional)
app_bg_css = "background-color: #0d0f12 !important;" if is_dark else "background-color: #f7f6f4 !important;"
text_color = "#f1f5f9" if is_dark else "#1c1917"
subtext_color = "#94a3b8" if is_dark else "#57534e"

btn_bg = "#181b20" if is_dark else "#ffffff"
btn_text = "#f1f5f9" if is_dark else "#1c1917"
btn_border = "#2a2e37" if is_dark else "#e7e5e4"
btn_hover_bg = "#222630" if is_dark else "#f0ede9"

input_bg = "#181b20" if is_dark else "#ffffff"
input_text = "#f1f5f9" if is_dark else "#1c1917"
input_border = "#2a2e37" if is_dark else "#d6d3d1"

# Posicionamiento del Switch de Tema
bottle_left_pos = "42px" if is_dark else "-2px"
static_icon_pos = "12px center" if is_dark else "calc(100% - 12px) center"

static_icon_svg = (
    "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23ffffff' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><circle cx='12' cy='12' r='4'/><line x1='12' y1='1' x2='12' y2='3'/><line x1='12' y1='21' x2='12' y2='23'/><line x1='4.22' y1='4.22' x2='5.64' y2='5.64'/><line x1='18.36' y1='18.36' x2='19.78' y2='19.78'/><line x1='1' y1='12' x2='3' y2='12'/><line x1='21' y1='12' x2='23' y2='12'/><line x1='4.22' y1='19.78' x2='5.64' y2='18.36'/><line x1='18.36' y1='5.64' x2='19.78' y2='4.22'/></svg>"
    if is_dark else
    "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%231a1a1a' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z'/></svg>"
)

bottle_svg = (
    "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 50 58'><rect x='18' y='2' width='14' height='7' rx='2' fill='%23ffffff' stroke='%23111111' stroke-width='2.5'/><rect x='21' y='9' width='8' height='5' fill='%23ffffff' stroke='%23111111' stroke-width='2.5'/><circle cx='25' cy='34' r='19' fill='%23ffffff' stroke='%23111111' stroke-width='2.5'/><path d='M21 28a8 8 0 0 0 9 10.5 8.5 8.5 0 0 1-9-10.5z' fill='none' stroke='%23111111' stroke-width='2.2' stroke-linecap='round' stroke-linejoin='round'/></svg>"
    if is_dark else
    "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 50 58'><rect x='18' y='2' width='14' height='7' rx='2' fill='%23ffffff' stroke='%23111111' stroke-width='2.5'/><rect x='21' y='9' width='8' height='5' fill='%23ffffff' stroke='%23111111' stroke-width='2.5'/><circle cx='25' cy='34' r='19' fill='%23ffffff' stroke='%23111111' stroke-width='2.5'/><circle cx='25' cy='34' r='5' fill='none' stroke='%23111111' stroke-width='2'/><line x1='25' y1='23' x2='25' y2='26' stroke='%23111111' stroke-width='2' stroke-linecap='round'/><line x1='25' y1='42' x2='25' y2='45' stroke='%23111111' stroke-width='2' stroke-linecap='round'/><line x1='14' y1='34' x2='17' y2='34' stroke='%23111111' stroke-width='2' stroke-linecap='round'/><line x1='33' y1='34' x2='36' y2='34' stroke='%23111111' stroke-width='2' stroke-linecap='round'/><line x1='17' y1='26' x2='19' y2='28' stroke='%23111111' stroke-width='2' stroke-linecap='round'/><line x1='31' y1='40' x2='33' y2='42' stroke='%23111111' stroke-width='2' stroke-linecap='round'/><line x1='17' y1='42' x2='19' y2='40' stroke='%23111111' stroke-width='2' stroke-linecap='round'/><line x1='31' y1='28' x2='33' y2='26' stroke='%23111111' stroke-width='2' stroke-linecap='round'/></svg>"
)

camera_icon_svg = f"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23{text_color[1:]}' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z'/><circle cx='12' cy='13' r='4'/></svg>"

# 2. SCRIPT DE INYECCIÓN JAVASCRIPT PARA CHIPS DE ESENCIAS (TONOS MÁS ELEGANTES Y LUXURY)
js_color_script = f"""
<script>
function applyEssenceColors() {{
    const doc = window.parent.document;
    const isDark = {str(is_dark).lower()};
    
    const colorRules = [
        // Frutos Rojos / Rosa Empties (Tono Palo Rosa / Burdeos Elegante)
        {{ keywords: ['sangre', 'cereza', 'frambuesa', 'pimienta rosa', 'rosa', 'ruibarbo', 'lichi', 'ciruela', 'grosella'], 
          bg: isDark ? 'rgba(85, 45, 55, 0.4)' : '#f9f1f2', 
          border: isDark ? 'rgba(160, 80, 100, 0.5)' : '#e2b6c1',
          text: isDark ? '#f4dfe4' : '#6b2d3e' }},
        
        // Marinas / Acuáticas (Azul Pizarra Oceánico)
        {{ keywords: ['marina', 'marinas', 'agua', 'océano'], 
          bg: isDark ? 'rgba(40, 60, 75, 0.4)' : '#edf3f7', 
          border: isDark ? 'rgba(80, 120, 150, 0.5)' : '#b5cbd8',
          text: isDark ? '#dbe8f0' : '#2c4a5e' }},
        
        // Verdes (Verde Salvia / Musgo Sobrio)
        {{ keywords: ['albahaca', 'bergamota', 'cardamomo', 'higo', 'manzana', 'menta', 'pachulí', 'pera', 'romero', 'salvia', 'té verde', 'vetiver'], 
          bg: isDark ? 'rgba(45, 65, 50, 0.4)' : '#f0f4f1', 
          border: isDark ? 'rgba(80, 130, 95, 0.5)' : '#b8d1c0',
          text: isDark ? '#e0efe4' : '#2d4d36' }},
        
        // Cítricos / Ámbar (Tono Champaña / Ámbar Ahumado)
        {{ keywords: ['azafrán', 'ámbar', 'mandarina', 'melocotón', 'mirra', 'naranjo', 'pomelo', 'cítrico', 'cítricos', 'limón', 'piña'], 
          bg: isDark ? 'rgba(80, 60, 40, 0.4)' : '#f7f4ee', 
          border: isDark ? 'rgba(150, 110, 60, 0.5)' : '#dccbb5',
          text: isDark ? '#f4ebd9' : '#5c4528' }},
        
        // Dulces / Gourmand (Café / Avellana / Caramelo Tostado)
        {{ keywords: ['caramelo', 'miel', 'solares', 'vainilla', 'ylang', 'cacao', 'café', 'canela', 'tonka', 'nuez moscada', 'praliné'], 
          bg: isDark ? 'rgba(70, 50, 40, 0.4)' : '#f6f2ee', 
          border: isDark ? 'rgba(140, 95, 70, 0.5)' : '#d8c4b6',
          text: isDark ? '#f0e6df' : '#4d3324' }},
        
        // Florales Violeta (Malva Polvoso)
        {{ keywords: ['iris', 'lavanda', 'jazmín', 'nardos', 'neroli'], 
          bg: isDark ? 'rgba(65, 50, 80, 0.4)' : '#f5f2f8', 
          border: isDark ? 'rgba(125, 95, 155, 0.5)' : '#cdbece',
          text: isDark ? '#ebdcf2' : '#473154' }},
        
        // Maderas / Cuero (Gris Grafito / Ebano)
        {{ keywords: ['cedro', 'sándalo', 'tabaco', 'abedul', 'cuero', 'oud', 'ámbar gris', 'incienso'], 
          bg: isDark ? 'rgba(50, 55, 65, 0.4)' : '#f1f3f5', 
          border: isDark ? 'rgba(100, 110, 125, 0.5)' : '#c7ced6',
          text: isDark ? '#e2e8f0' : '#2b3440' }},
        
        // Almizcle / Neutro (Lino Purificado)
        {{ keywords: ['almizcle', 'coco', 'civeta', 'pimienta blanca', 'pimienta negra'], 
          bg: isDark ? 'rgba(255, 255, 255, 0.05)' : '#fafafa', 
          border: isDark ? 'rgba(255, 255, 255, 0.15)' : '#e2e8f0',
          text: isDark ? '#f8fafc' : '#334155' }}
    ];

    const targets = doc.querySelectorAll('li[role="option"], div[role="option"], span[data-baseweb="tag"]');

    targets.forEach(el => {{
        const text = el.innerText.toLowerCase();
        for (const rule of colorRules) {{
            if (rule.keywords.some(kw => text.includes(kw))) {{
                el.style.backgroundColor = rule.bg;
                el.style.border = `1px solid ${{rule.border}}`;
                el.style.color = rule.text; 
                el.style.borderRadius = '4px';
                el.style.padding = '3px 9px';
                el.style.marginTop = '3px';
                el.style.marginBottom = '3px';
                el.style.fontSize = '0.82rem';
                el.style.transition = 'all 0.2s ease';
                break;
            }}
        }}
    }});
}}

setInterval(applyEssenceColors, 150);
</script>
"""

components.html(js_color_script, height=0, width=0)

# 3. CSS GLOBAL Y CONFIGURACIÓN VISUAL
st.markdown(f"""
    <style>
    header[data-testid="stHeader"] {{ display: none !important; }}
    .block-container {{ padding-top: 1.5rem !important; padding-bottom: 2rem !important; }}
    .stApp {{ {app_bg_css} color: {text_color} !important; font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}

    .stApp p, .stApp span, .stApp label, .stMarkdown p, .stTextInput label p, .stMultiSelect label p {{
        color: {text_color} !important;
    }}

    /* NAVEGACIÓN PRINCIPAL */
    .st-key-n_perfumes button, 
    .st-key-n_arabes button, 
    .st-key-n_marcas button, 
    .st-key-n_remates button,
    .st-key-n_disenador button,
    .st-key-n_nicho button,
    .st-key-n_esencias button {{
        background-color: transparent !important;
        border: none !important;
        border-bottom: 2px solid transparent !important;
        border-radius: 0px !important;
        font-weight: 500 !important;
        font-size: 0.85rem !important;
        padding: 0.4rem 0.2rem !important;
        box-shadow: none !important;
        letter-spacing: 0.5px;
    }}

    .st-key-n_perfumes button p, 
    .st-key-n_arabes button p, 
    .st-key-n_marcas button p, 
    .st-key-n_remates button p,
    .st-key-n_disenador button p,
    .st-key-n_nicho button p,
    .st-key-n_esencias button p {{
        color: {subtext_color} !important;
        white-space: nowrap !important;
        transition: color 0.3s ease;
    }}

    .st-key-n_perfumes button:hover p, 
    .st-key-n_arabes button:hover p, 
    .st-key-n_marcas button:hover p, 
    .st-key-n_remates button:hover p,
    .st-key-n_disenador button:hover p,
    .st-key-n_nicho button:hover p,
    .st-key-n_esencias button:hover p {{
        color: {text_color} !important;
    }}

    /* HERRAMIENTAS RÁPIDAS */
    .st-key-btn_trend button, 
    .st-key-btn_trust button, 
    .st-key-btn_compare button {{
        background-color: transparent !important;
        border: 1px solid {btn_border} !important;
        border-radius: 20px !important;
        padding: 0.2rem 0.8rem !important;
        box-shadow: none !important;
    }}
    
    .st-key-btn_trend button p, 
    .st-key-btn_trust button p, 
    .st-key-btn_compare button p {{
        font-size: 0.75rem !important;
        font-weight: 400 !important;
        color: {subtext_color} !important;
        letter-spacing: 0.3px;
    }}

    /* BOTÓN INGRESAR */
    .st-key-login_btn button {{
        background-color: {btn_bg} !important;
        color: {btn_text} !important;
        border: 1px solid {btn_border} !important;
        border-radius: 6px !important;
        font-weight: 500 !important;
        letter-spacing: 0.5px;
    }}

    /* INPUTS, SELECTS Y POPOVERS */
    div[data-baseweb="input"],
    div[data-baseweb="base-input"],
    div[data-baseweb="select"] > div,
    div[data-testid="stPopover"] > button,
    button[data-testid="stPopoverButton"],
    button[data-testid="stBaseButton-secondary"] {{
        background-color: {input_bg} !important;
        border: 1px solid {input_border} !important;
        border-radius: 6px !important;
    }}

    div[data-baseweb="input"] input,
    div[data-baseweb="base-input"] input,
    div[data-baseweb="select"] span[data-baseweb="tag"] span,
    div[data-baseweb="select"] div,
    div[data-testid="stPopover"] button,
    div[data-testid="stPopover"] button *,
    div[data-testid="stPopover"] button p,
    div[data-testid="stPopover"] button span,
    div[data-testid="stPopover"] button div,
    button[data-testid="stPopoverButton"],
    button[data-testid="stPopoverButton"] *,
    button[data-testid="stPopoverButton"] p,
    button[data-testid="stPopoverButton"] span {{
        color: {input_text} !important;
        white-space: nowrap !important;
    }}

    div[data-testid="stPopover"] button svg,
    button[data-testid="stPopoverButton"] svg {{
        stroke: {input_text} !important;
        fill: {input_text} !important;
    }}

    div[data-baseweb="input"] input::placeholder {{
        color: {subtext_color} !important;
        font-weight: 300;
    }}

    .st-key-btn_photo_search button {{
        background-color: {input_bg} !important;
        border: 1px solid {input_border} !important;
        border-radius: 6px !important;
        padding: 0.4rem 0.6rem 0.4rem 2.2rem !important;
        background-image: url("{camera_icon_svg}") !important;
        background-repeat: no-repeat !important;
        background-position: 10px center !important;
        background-size: 16px 16px !important;
        font-size: 0.82rem !important;
    }}
    
    .stApp .st-key-btn_photo_search button,
    .stApp .st-key-btn_photo_search button p {{
        color: {text_color} !important;
        white-space: nowrap !important;
    }}

    /* SWITCH DE TEMA INTERACTIVO */
    .st-key-theme_toggle button {{
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
        width: 82px !important;
        height: 48px !important;
        position: relative !important;
        cursor: pointer !important;
        margin: 0 auto !important;
        display: block !important;
    }}

    .st-key-theme_toggle button * {{ display: none !important; }}
    
    .st-key-theme_toggle button::before {{
        content: '' !important;
        position: absolute !important;
        top: 7px !important; left: 0 !important;
        width: 80px !important; height: 36px !important;
        background-color: {"#262626" if is_dark else "#e5ded7"} !important;
        border: 1px solid {btn_border} !important;
        border-radius: 20px !important;
        box-shadow: inset 0 2px 5px rgba(0,0,0,0.2) !important;
        background-image: url("{static_icon_svg}") !important;
        background-repeat: no-repeat !important;
        background-position: {static_icon_pos} !important;
        background-size: 16px 16px !important;
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
        z-index: 2 !important;
    }}

    /* TARJETAS DE CATÁLOGO */
    .catalog-card {{
        background-color: transparent;
        border: 1px solid {btn_border};
        border-radius: 4px;
        overflow: hidden;
        position: relative;
        margin-bottom: 25px;
        transition: transform 0.4s ease, border-color 0.4s ease;
    }}
    .catalog-card:hover {{
        transform: translateY(-4px);
        border-color: #8c7b6d;
    }}
    .square-img-box {{
        position: relative;
        width: 100%;
        aspect-ratio: 1 / 1;
        background-color: #ffffff;
        display: flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
        padding: 30px;
        box-sizing: border-box;
    }}
    .square-img-box img {{
        max-width: 100%;
        max-height: 100%;
        object-fit: contain;
        transition: transform 0.6s ease;
    }}
    .catalog-card:hover .square-img-box img {{
        transform: scale(1.05);
    }}
    .card-hover-overlay {{
        position: absolute;
        top: 0; left: 0; right: 0; bottom: 0;
        background: rgba(18, 21, 28, 0.95);
        color: #ffffff;
        padding: 20px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        opacity: 0;
        transition: opacity 0.4s ease;
        backdrop-filter: blur(2px);
        text-align: left;
    }}
    .catalog-card:hover .card-hover-overlay {{ opacity: 1; }}
    .overlay-title {{
        font-size: 1rem;
        font-weight: 600;
        color: #e3d3b3;
        margin-bottom: 12px;
        border-bottom: 1px solid rgba(255,255,255,0.1);
        padding-bottom: 8px;
        letter-spacing: 0.5px;
    }}
    .overlay-info {{ font-size: 0.8rem; font-weight: 300; line-height: 1.6; color: #d0d0d0; margin-bottom: 8px; }}
    .card-footer-info {{ padding: 16px; text-align: center; background-color: {btn_bg}; }}
    .card-perfume-name {{ font-size: 0.9rem; font-weight: 600; color: {text_color}; margin-bottom: 4px; letter-spacing: 0.5px; }}
    .card-perfume-brand {{ font-size: 0.75rem; font-weight: 300; color: {subtext_color}; text-transform: uppercase; letter-spacing: 1px; }}

    /* TARJETAS DICCIONARIO DE ESENCIAS */
    .essence-card {{
        border-radius: 8px;
        padding: 18px 22px;
        margin-bottom: 18px;
        transition: all 0.3s ease;
        backdrop-filter: blur(4px);
    }}
    .essence-card:hover {{
        transform: translateY(-2px);
    }}
    .essence-title {{ font-size: 1.05rem; font-weight: 600; margin-bottom: 6px; letter-spacing: 0.5px; }}
    .essence-desc {{ font-size: 0.88rem; font-weight: 400; line-height: 1.65; }}
    </style>
""", unsafe_allow_html=True)

# 4. CABECERA
col_logo, col_espacio, col_actions = st.columns([4, 3, 2.5], vertical_alignment="center")

with col_logo:
    logo_color = "#8c7b6d"
    logo_html = f"""
    <div style="display: flex; align-items: center; gap: 12px; cursor: pointer;" onclick="window.location.reload();">
        <svg width="36" height="36" viewBox="0 0 36 36" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path d="M 6.8 21 L 29.2 21 C 30 25 27 32 18 32 C 9 32 6 25 6.8 21 Z" fill="{logo_color}" />
            <line x1="6.8" y1="21" x2="29.2" y2="21" stroke="{text_color}" stroke-width="1.5" />
            <line x1="18" y1="10" x2="18" y2="30" stroke="{text_color}" stroke-width="1" />
            <path d="M 18 32 C 9 32 5 24 7.5 17 C 9 12 13 10 15 10 L 21 10 C 23 10 27 12 28.5 17 C 31 24 27 32 18 32 Z" stroke="{text_color}" stroke-width="2" />
            <rect x="15" y="7" width="6" height="3" stroke="{text_color}" stroke-width="1.5" />
            <rect x="13" y="3" width="10" height="4" rx="1" stroke="{text_color}" stroke-width="1.5" />
            <rect x="16" y="0" width="4" height="3" rx="1" fill="{logo_color}" stroke="{text_color}" stroke-width="1" />
            <path d="M 23 5 L 26 4" stroke="{text_color}" stroke-width="1.5" />
            <ellipse cx="29" cy="3" rx="3.5" ry="2.5" transform="rotate(-25 29 3)" fill="{logo_color}" stroke="{text_color}" stroke-width="1" />
        </svg>
        <span style="font-size: 1.4rem; color: {text_color}; letter-spacing: 1px;">
            <span style="font-weight: 300;">Perfume</span><span style="font-weight: 600;">Trending</span>
        </span>
    </div>
    """
    st.markdown(logo_html, unsafe_allow_html=True)

with col_actions:
    btn_col1, btn_col2 = st.columns([1.5, 1], vertical_alignment="center")
    with btn_col1:
        st.button("👤 Ingresar", key="login_btn", use_container_width=True)
    with btn_col2:
        st.button(" ", key="theme_toggle", on_click=toggle_theme)

# 5. NAVEGACIÓN
st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
nav_cols = st.columns([1.1, 1.6, 0.9, 1.0, 1.1, 0.9, 1.0, 1.5], vertical_alignment="center")

with nav_cols[0]: st.button("PERFUMES", key="n_perfumes", on_click=navigate_to, args=('home',), use_container_width=True)
with nav_cols[1]: st.button("PERFUMES ÁRABES", key="n_arabes", on_click=navigate_to, args=('home',), use_container_width=True)
with nav_cols[2]: st.button("MARCAS", key="n_marcas", on_click=navigate_to, args=('home',), use_container_width=True)
with nav_cols[3]: st.button("REMATES", key="n_remates", on_click=navigate_to, args=('hype',), use_container_width=True)
with nav_cols[4]: st.button("DISEÑADOR", key="n_disenador", on_click=navigate_to, args=('home',), use_container_width=True)
with nav_cols[5]: st.button("NICHO", key="n_nicho", on_click=navigate_to, args=('home',), use_container_width=True)
with nav_cols[6]: st.button("ESENCIAS", key="n_esencias", on_click=navigate_to, args=('esencias_page',), use_container_width=True)

st.markdown(f"<hr style='margin: 8px 0 30px 0; border: none; border-bottom: 1px solid {btn_border}; opacity: 0.3;'>", unsafe_allow_html=True)

# 6. LISTADO OFICIAL DE ESENCIAS (62 NOTAS OLFATIVAS COMPLETAS)
raw_notes = [
    "Abedul", "Albahaca", "Almizcle (Blanco/Musk)", "Ámbar (Cálido)", "Ámbar Gris",
    "Azafrán", "Bergamota", "Cacao", "Café", "Canela",
    "Caramelo", "Cardamomo", "Cedro", "Cereza", "Ciruela", "Cítricos",
    "Civeta", "Coco", "Cuero", "Frambuesa", "Grosellas Negras",
    "Haba Tonka", "Higo", "Incienso", "Iris", "Jazmín", "Jengibre",
    "Lavanda", "Lichi", "Limón", "Mandarina", "Manzana", "Melocotón",
    "Menta", "Miel", "Mirra", "Naranjo", "Nardos", "Neroli",
    "Notas Marinas", "Notas Solares", "Nuez Moscada", "Oud",
    "Pachulí", "Pera", "Pimienta Blanca", "Pimienta Negra", "Pimienta Rosa",
    "Piña", "Pomelo", "Praliné", "Romero", "Rosa", "Ruibarbo",
    "Salvia", "Sándalo", "Sangre (Metálica)", "Tabaco", "Té Verde",
    "Vainilla", "Vetiver", "Ylang-Ylang"
]

all_notes = sorted(raw_notes)

# 7. BÚSQUEDA Y SELECCIÓN DE ESENCIAS
col_search, col_filter, col_separator, col_photo = st.columns([5.2, 1.8, 0.2, 2.3], vertical_alignment="center")

with col_search:
    search_query = st.text_input("🔍 Buscar", placeholder="🔍 Buscar perfume, marca o esencias...", label_visibility="collapsed")

with col_filter:
    with st.popover("Esencias", use_container_width=True):
        selected_essences = st.multiselect(
            "Selecciona notas olfativas:",
            options=all_notes,
            placeholder="Elige esencias...",
            label_visibility="collapsed"
        )

with col_separator:
    st.markdown(f"<div style='border-left: 1px solid {btn_border}; height: 35px; margin: auto;'></div>", unsafe_allow_html=True)

with col_photo:
    st.button("Búsqueda visual", key="btn_photo_search", help="Buscar perfume por imagen", use_container_width=True)

# 8. CHIPS DE NAVEGACIÓN RÁPIDA
st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
col_chip1, col_chip2, col_chip3, col_chip_space = st.columns([1.5, 1.8, 1.6, 5.1], vertical_alignment="center")

with col_chip1:
    if st.button("Trend Del Hype", key="btn_trend", use_container_width=True):
        st.switch_page("pages/trendhype.py")
with col_chip2:
    st.button("Páginas de Confianza", key="btn_trust", on_click=navigate_to, args=('trust_page',), use_container_width=True)
with col_chip3:
    st.button("Comparar Precios", key="btn_compare", on_click=navigate_to, args=('compare_page',), use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)

# 9. VISTAS DE PÁGINA
if st.session_state['current_page'] == 'home':
    st.markdown(f"<h3 style='text-align: center; margin-bottom: 35px; color: {text_color}; letter-spacing: 2px; font-weight: 300;'>CATÁLOGO Y TENDENCIAS</h3>", unsafe_allow_html=True)
    
    if selected_essences:
        st.write(f"**Filtro activo:** {', '.join(selected_essences)}")

    catalog_perfumes = [
        {
            "name": "Bleu de Chanel",
            "brand": "Chanel",
            "country": "Francia 🇫🇷",
            "perfumer": "Jacques Polge",
            "notes": "Toronja, Limón, Menta, Jengibre, Incienso, Cedro, Sándalo",
            "img": "https://fimgs.net/mdig/rx_perfume/58/28/6005828.jpg"
        },
        {
            "name": "Sauvage Elixir",
            "brand": "Dior",
            "country": "Francia 🇫🇷",
            "perfumer": "François Demachy",
            "notes": "Canela, Nuez Moscada, Lavanda, Regaliz, Sándalo, Ámbar",
            "img": "https://fimgs.net/mdig/rx_perfume/31/86/31861.jpg"
        },
        {
            "name": "Baccarat Rouge 540",
            "brand": "Maison Francis Kurkdjian",
            "country": "Francia 🇫🇷",
            "perfumer": "Francis Kurkdjian",
            "notes": "Azafrán, Jazmín, Ámbar Gris, Madera de Cedro, Resina de Abeto",
            "img": "https://fimgs.net/mdig/rx_perfume/30/88/30886.jpg"
        },
        {
            "name": "Club de Nuit Intense",
            "brand": "Armaf",
            "country": "Emiratos Árabes Unidos 🇦🇪",
            "perfumer": "Christian Provenzano",
            "notes": "Limón, Piña, Grosellas Negras, Abedul, Jasmine, Almizcle",
            "img": "https://fimgs.net/mdig/rx_perfume/27/65/27656.jpg"
        },
        {
            "name": "Angels' Share",
            "brand": "Kilian",
            "country": "Francia 🇫🇷",
            "perfumer": "Benoist Lapouza",
            "notes": "Cognac, Canela, Haba Tonka, Roble, Vainilla, Sándalo, Praliné",
            "img": "https://fimgs.net/mdig/rx_perfume/62/61/62615.jpg"
        },
        {
            "name": "YSL Libre EDP",
            "brand": "Yves Saint Laurent",
            "country": "Francia 🇫🇷",
            "perfumer": "Anne Flipo & Carlos Benaïm",
            "notes": "Lavanda, Mandarina, Grosellas Negras, Flor de Azahar, Vainilla",
            "img": "https://fimgs.net/mdig/rx_perfume/56/55/5605655.jpg"
        }
    ]

    cols_per_row = 3
    for i in range(0, len(catalog_perfumes), cols_per_row):
        cols = st.columns(cols_per_row, gap="large")
        for j in range(cols_per_row):
            if i + j < len(catalog_perfumes):
                p = catalog_perfumes[i + j]
                card_html = f"""
                <div class="catalog-card">
                    <div class="square-img-box">
                        <img src="{p['img']}" alt="{p['name']}">
                        <div class="card-hover-overlay">
                            <div class="overlay-title">{p['name']}</div>
                            <div class="overlay-info"><b>📍 Origen:</b> {p['country']}</div>
                            <div class="overlay-info"><b>👤 Nariz:</b> {p['perfumer']}</div>
                            <div class="overlay-info" style="margin-top: 8px;"><b>🌿 Notas:</b> {p['notes']}</div>
                        </div>
                    </div>
                    <div class="card-footer-info">
                        <div class="card-perfume-name">{p['name']}</div>
                        <div class="card-perfume-brand">{p['brand']}</div>
                    </div>
                </div>
                """
                with cols[j]:
                    st.markdown(card_html, unsafe_allow_html=True)

elif st.session_state['current_page'] == 'esencias_page':
    st.markdown(f"<h3 style='text-align: center; color: {text_color}; letter-spacing: 1px; font-weight: 300; margin-bottom: 10px;'>DICCIONARIO COMPLETO DE ESENCIAS</h3>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; color: {subtext_color}; margin-bottom: 40px; font-size: 0.95rem;'>Guía exhaustiva con las 62 notas olfativas más influyentes de la alta perfumería.</p>", unsafe_allow_html=True)
    
    # DICCIONARIO CON LAS 62 ESENCIAS DEFINIDAS DE FORMA PROFESIONAL Y ESTILIZADAS
    dict_details = {
        "Abedul": ("Maderas / Ahumados", "Nota amaderada, ahumada y alquitranada; fundamental para otorgar un carácter leñoso intenso y matices de cuero refinado."),
        "Albahaca": ("Verdes / Herbales", "Hierba aromática vibrante y ligeramente picante que aporta un dulzor balsámico, herbal y energizante."),
        "Almizcle (Blanco/Musk)": ("Almizclados / Limpios", "Acorde puro, sedoso y envolvente que evoca la sensación de piel limpia y proporciona una fijación excepcional."),
        "Ámbar (Cálido)": ("Ámbar / Orientales", "Mezcla resinosa, dulzona y cálida de resinas que añade cuerpo, sensualidad y misterio al fondo de la fragancia."),
        "Ámbar Gris": ("Marinos / Exóticos", "Nota marina y animal refinada de aroma salado y aterciopelado que maximiza la fijación y longevidad."),
        "Azafrán": ("Especiados / Lujo", "El 'oro rojo' de las especias; picante, amaderado y levemente amargo con lujosos matices de gamuza."),
        "Bergamota": ("Cítricos / Frescos", "Cítrico noble de la Calabria; efervescente, amargo y con destellos florales que ilumina las salidas."),
        "Cacao": ("Gourmand / Calidos", "Nota dulce y amarga de gran profundidad que evoca el chocolate negro, aportando una calidez adictiva."),
        "Café": ("Gourmand / Tostados", "Acorde tostado, amargo y energizante de personalidad vanguardista que aporta un toque oscuro y sensual."),
        "Canela": ("Especiados / Cálidos", "Especia aromática dulce y picante que transmite confort oriental y gran calidez envolvente."),
        "Caramelo": ("Gourmand / Dulces", "Nota golosa y tostada que aporta una textura untuosa y un matiz reconfortante e inductivo."),
        "Cardamomo": ("Especiados / Frescos", "Especia de gran lujo con matices resinosos, cítricos y alcanforados sumamente elegantes."),
        "Cedro": ("Maderas Noble", "Madera seca, estructurada y limpia con recuerdos de lápiz de grafito que brinda solidez atemporal."),
        "Cereza": ("Frutales / Licorosos", "Fruta oscura, jugosa y dulce que aporta un carácter nocturno, maduro y carnal a los acordes gourmand."),
        "Ciruela": ("Frutales / Opulentos", "Nota frutal aterciopelada y licorosa que aporta riqueza, opulencia y sensualidad a fragancias orientales."),
        "Cítricos": ("Cítricos / Chispeantes", "Acorde efervescente de hespérides que insufla aire puro, vitalidad y frescor inmediato."),
        "Civeta": ("Animales / Clásicos", "Nota animal pulida (sintética) que otorga volumen, calor, densidad y una textura altamente seductora."),
        "Coco": ("Exóticos / Gourmand", "Nota láctea, cremosa y tropical que transmite un espíritu solar, relajado y veraniego."),
        "Cuero": ("Maderas / Ahumados", "Acorde ahumado y sofisticado que evoca gamuza fina o piel noble; aporta distinción y firmeza."),
        "Frambuesa": ("Frutales / Chispeantes", "Fruta agridulce y radiante que armoniza perfectamente con notas de rosa, azafrán y maderas oscuras."),
        "Grosellas Negras": ("Frutales / Verdes", "Frutal ácida, verdosa y licorosa que ofrece un matiz frutal silvestre de alta intensidad."),
        "Haba Tonka": ("Gourmand / Bálsamos", "Semilla aromática rica en cumarina con recuerdos de vainilla, almendra tostada y tabaco dulce."),
        "Higo": ("Frutales / Mediterráneos", "Nota dual que combina la frescura verde de la hoja con la cremosidad láctea del fruto maduro."),
        "Incienso": ("Resinas / Místicos", "Resina mística que otorga facetas minerales, frías, ahumadas y balsámicas de gran sobriedad."),
        "Iris": ("Florales / Empolvados", "Nota mantecosa, terrosa y aristocrática que proyecta elegancia polvosa y sobriedad sofisticada."),
        "Jazmín": ("Florales / Opulentos", "Flor blanca reina de la perfumería; radiante, magnética, indólica y profundamente sensual."),
        "Jengibre": ("Especiados / Tónicos", "Especia vibrante, efervescente y cítrica que proporciona un choque inicial de energía limpia."),
        "Lavanda": ("Aromáticos / Herbales", "Aromática, limpia y herbal; pilar atemporal de la perfumería masculina de refinamiento clásico."),
        "Lichi": ("Frutales / Exóticos", "Fruta exótica cristalina y acuosa que añade una faceta frutal dulzona muy cercana a la rosa fresca."),
        "Limón": ("Cítricos / Tónicos", "Nota cítrica ácida, limpia y radiante que aporta luminosidad e higiene cristalina."),
        "Mandarina": ("Cítricos / Dulces", "Cítrico frutal y jugoso de carácter festivo que dulcifica la apertura con calidez solar."),
        "Manzana": ("Frutales / Frescos", "Nota crujiente, verde y jugosa que aporta ligereza, juventud y espontaneidad."),
        "Melocotón": ("Frutales / Aterciopelados", "Frutal carnoso y suave que envuelve la fragancia en una textura aterciopelada y sutil."),
        "Menta": ("Aromáticos / Helados", "Hierba ultra-fresca de impacto helado que vigoriza las notas superiores al instante."),
        "Miel": ("Gourmand / Dorados", "Nota rica, dorada y viscosa que ofrece un dulzor profundo con matices animales y reconfortantes."),
        "Mirra": ("Resinas / Orientales", "Resina antigua cálida y balsámica con destellos levemente especiados y amaderados."),
        "Naranjo": ("Verdes / Sol", "Acorde vegetal integral que evoca tanto la hoja verde picante como la flor efervescente."),
        "Nardos": ("Florales / Carnales", "Flor blanca narcótica, embriagadora y cremosa que exhibe una presencia inolvidable."),
        "Neroli": ("Florales / Frescos", "Aceite extraído del azahar; cítrico, verdoso, transparente y delicadamente floral."),
        "Notas Marinas": ("Marinos / Ozónicos", "Acorde acuático salino y ozónico que evoca el soplo de la brisa marina y la libertad oceánica."),
        "Notas Solares": ("Exóticos / Calidos", "Sensación abstracta de la calidez del sol bronceando la piel y la arena tibia."),
        "Nuez Moscada": ("Especiados / Cálidos", "Especia amaderada y seca que proporciona un matiz picante sofisticado al corazón olfativo."),
        "Oud": ("Maderas / Lujo", "Madera de agar resinosa y mística; opulenta, leñosa, ahumada y referencia absoluta del lujo."),
        "Pachulí": ("Maderas / Terrosos", "Nota amaderada, humeda y terrosa con matices de chocolate oscuro y estética bohemia."),
        "Pera": ("Frutales / Acuosos", "Fruta acuosa, suave y crujiente que equilibra arreglos florales con su dulzor transparente."),
        "Pimienta Blanca": ("Especiados / Secos", "Picante suave y seco que aporta una pátina de sofisticación ligera y refinada."),
        "Pimienta Negra": ("Especiados / Picantes", "Especia cálida, picante y estimulante que añade empuje e intensidad en la salida."),
        "Pimienta Rosa": ("Especiados / Rosados", "Especia chispeante, rosada y levemente cítrica de gran versatilidad moderna."),
        "Piña": ("Frutales / Tropícales", "Fruta tropical ácida y jugosa emblemática por su energía radiante y muy adictiva."),
        "Pomelo": ("Cítricos / Amargos", "Cítrico tónico y levemente amargo de perfil efervescente extremadamente limpio."),
        "Praliné": ("Gourmand / Dulces", "Nota crujiente de frutos secos garrapiñados y azúcar tostado que añade un matiz goloso."),
        "Romero": ("Aromáticos / Herbales", "Aromática mediterránea de matices leñosos y alcanforados que infunde vigor natural."),
        "Rosa": ("Florales / Clásicos", "La reina floral por excelencia; poética, atemporal, delicada o intensamente sensual."),
        "Ruibarbo": ("Verdes / Vanguardistas", "Nota vegetal agridulce y crujiente que aporta un contraste verde moderno y vibrante."),
        "Salvia": ("Aromáticos / Secos", "Herbal suave de facetas amaderadas y recuerdos de té con fondo ligeramente ambarino."),
        "Sándalo": ("Maderas / Cremositos", "Madera mística suave, balsámica y cremosa que aporta paz, confort y notable persistencia."),
        "Sangre (Metálica)": ("Vanguardistas / Metálicos", "Acorde conceptual metálico con matices salados e ferrosos de propuesta arriesgada."),
        "Tabaco": ("Maderas / Cálidos", "Hoja seca, rica y dulce con notas de miel y madera ahumada de notable distinción."),
        "Té Verde": ("Verdes / Zen", "Acorde cristalino, herbal y desintoxicante que aporta serenidad y calma sofisticada."),
        "Vainilla": ("Gourmand / Cremosos", "Nota oriental dulce, licorosa y reconfortante; arquetipo de la adicción gourmand."),
        "Vetiver": ("Maderas / Terrosos", "Raíz profunda, terrosa, verde y ahumada que otorga elegancia seca y madura."),
        "Ylang-Ylang": ("Florales / Exóticos", "Flor tropical cremosa y solar de matriz exótica que aporta riqueza voluptuosa.")
    }

    # Asignación de paleta tonal sofisticada para tarjetas
    def get_card_style(category, is_dark_mode):
        if any(w in category for w in ["Cítricos", "Marinos", "Verdes", "Aromáticos"]):
            border = "rgba(70, 130, 110, 0.45)" if is_dark_mode else "rgba(160, 195, 180, 0.8)"
            bg = "rgba(25, 45, 38, 0.35)" if is_dark_mode else "#f0f4f2"
            text_t = "#80e6b8" if is_dark_mode else "#244d3b"
        elif any(w in category for w in ["Gourmand", "Ámbar", "Especiados"]):
            border = "rgba(150, 100, 60, 0.45)" if is_dark_mode else "rgba(215, 185, 150, 0.8)"
            bg = "rgba(45, 32, 22, 0.35)" if is_dark_mode else "#f8f4ef"
            text_t = "#f5c996" if is_dark_mode else "#5c3d23"
        elif any(w in category for w in ["Florales", "Frutales"]):
            border = "rgba(140, 80, 100, 0.45)" if is_dark_mode else "rgba(210, 170, 185, 0.8)"
            bg = "rgba(40, 24, 30, 0.35)" if is_dark_mode else "#f9f2f4"
            text_t = "#f5b8cc" if is_dark_mode else "#632d41"
        else: # Maderas, Almizclados, Vanguardistas
            border = "rgba(100, 110, 125, 0.45)" if is_dark_mode else "rgba(190, 198, 208, 0.8)"
            bg = "rgba(28, 32, 38, 0.4)" if is_dark_mode else "#f2f4f6"
            text_t = "#cbd5e1" if is_dark_mode else "#334155"
            
        return border, bg, text_t

    col_es_1, col_es_2 = st.columns(2, gap="large")
    
    sorted_dict_keys = sorted(dict_details.keys())
    
    for i, name in enumerate(sorted_dict_keys):
        cat, desc = dict_details[name]
        b_color, bg_color, t_color = get_card_style(cat, is_dark)
        
        tarjeta_html = f"""
        <div class="essence-card" style="border: 1px solid {b_color}; background-color: {bg_color};">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                <span class="essence-title" style="color: {text_color};">{name}</span>
                <span style="font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.8px; padding: 2px 7px; border-radius: 4px; background: rgba(0,0,0,0.15); color: {t_color}; font-weight: 500;">{cat}</span>
            </div>
            <div class="essence-desc" style="color: {subtext_color};">{desc}</div>
        </div>
        """
        if i % 2 == 0:
            with col_es_1:
                st.markdown(tarjeta_html, unsafe_allow_html=True)
        else:
            with col_es_2:
                st.markdown(tarjeta_html, unsafe_allow_html=True)

elif st.session_state['current_page'] == 'trust_page':
    st.markdown(f"<h3 style='text-align: center; color: {text_color}; font-weight: 300;'>Páginas de Confianza (Próximamente)</h3>", unsafe_allow_html=True)
elif st.session_state['current_page'] == 'compare_page':
    st.markdown(f"<h3 style='text-align: center; color: {text_color}; font-weight: 300;'>Comparador de Precios (Próximamente)</h3>", unsafe_allow_html=True)
