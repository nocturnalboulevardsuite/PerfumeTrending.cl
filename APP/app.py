import streamlit as st
import streamlit.components.v1 as components
import pandas as pd

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

# Colores generales
app_bg_css = "background-color: #0e1117 !important;" if is_dark else "background-color: #f8f6f3 !important;"
text_color = "#ffffff" if is_dark else "#1a1a1a"
subtext_color = "#a0a0a0" if is_dark else "#444444"

btn_bg = "#1f242d" if is_dark else "#ffffff"
btn_text = "#ffffff" if is_dark else "#1a1a1a"
btn_border = "#3a3f4d" if is_dark else "#d4cdc5"
btn_hover_bg = "#2d3340" if is_dark else "#f2ebe4"

input_bg = "#1f242d" if is_dark else "#ffffff"
input_text = "#ffffff" if is_dark else "#1a1a1a"
input_border = "#3a3f4d" if is_dark else "#d4cdc5"

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

# 2. SCRIPT DE INYECCIÓN JAVASCRIPT PARA CHIPS DE ESENCIAS (DESPLEGABLE Y TAGS)
js_color_script = f"""
<script>
function applyEssenceColors() {{
    const doc = window.parent.document;
    const isDark = {str(is_dark).lower()};
    
    const colorRules = [
        // Rojos / Rosas
        {{ keywords: ['sangre', 'cereza', 'frambuesa', 'pimienta rosa', 'rosa', 'ruibarbo', 'lichi', 'ciruela', 'grosella', 'grosellas'], 
          bg: isDark ? 'rgba(168, 50, 75, 0.35)' : '#ffe4e6', 
          border: isDark ? 'rgba(244, 63, 94, 0.7)' : '#f43f5e',
          text: isDark ? '#fecdd3' : '#881337' }},
        
        // Marinas / Acuáticas
        {{ keywords: ['marina', 'marinas', 'agua', 'océano', 'mar'], 
          bg: isDark ? 'rgba(14, 116, 144, 0.35)' : '#e0f2fe', 
          border: isDark ? 'rgba(56, 189, 248, 0.7)' : '#0284c7',
          text: isDark ? '#bae6fd' : '#075985' }},
        
        // Verdes / Herbales
        {{ keywords: ['albahaca', 'bergamota', 'cardamomo', 'higo', 'manzana', 'menta', 'pachulí', 'pera', 'romero', 'salvia', 'té verde', 'vetiver'], 
          bg: isDark ? 'rgba(21, 128, 61, 0.35)' : '#dcfce7', 
          border: isDark ? 'rgba(74, 222, 128, 0.7)' : '#16a34a',
          text: isDark ? '#bbf7d0' : '#14532d' }},
        
        // Florales Violeta / Blancos
        {{ keywords: ['iris', 'lavanda', 'jazmín', 'nardos', 'neroli'], 
          bg: isDark ? 'rgba(126, 34, 206, 0.35)' : '#f3e8ff', 
          border: isDark ? 'rgba(192, 132, 252, 0.7)' : '#9333ea',
          text: isDark ? '#f3e8ff' : '#581c87' }},

        // Dulces / Gourmet
        {{ keywords: ['caramelo', 'miel', 'solares', 'vainilla', 'ylang', 'cacao', 'café', 'canela', 'tonka', 'nuez moscada', 'praliné', 'haba tonka'], 
          bg: isDark ? 'rgba(180, 83, 9, 0.35)' : '#fef3c7', 
          border: isDark ? 'rgba(245, 158, 11, 0.7)' : '#d97706',
          text: isDark ? '#fef3c7' : '#78350f' }},

        // Maderas / Cuero / Resinas
        {{ keywords: ['ámbar gris', 'cedro', 'sándalo', 'tabaco', 'abedul', 'cuero', 'oud', 'incienso'], 
          bg: isDark ? 'rgba(71, 85, 105, 0.4)' : '#f1f5f9', 
          border: isDark ? 'rgba(148, 163, 184, 0.7)' : '#64748b',
          text: isDark ? '#f1f5f9' : '#0f172a' }},

        // Cítricos / Ámbar / Especias
        {{ keywords: ['azafrán', 'ámbar', 'mandarina', 'melocotón', 'mirra', 'naranjo', 'pomelo', 'cítrico', 'cítricos', 'limón', 'piña', 'jengibre'], 
          bg: isDark ? 'rgba(194, 65, 12, 0.35)' : '#ffedd5', 
          border: isDark ? 'rgba(251, 146, 60, 0.7)' : '#ea580c',
          text: isDark ? '#ffedd5' : '#7c2d12' }},
        
        // Almizcle / Neutro
        {{ keywords: ['almizcle', 'coco', 'civeta', 'pimienta blanca', 'pimienta negra'], 
          bg: isDark ? 'rgba(255, 255, 255, 0.12)' : '#f8fafc', 
          border: isDark ? 'rgba(255, 255, 255, 0.35)' : '#cbd5e1',
          text: isDark ? '#ffffff' : '#1e293b' }}
    ];

    const targets = doc.querySelectorAll('li[role="option"], div[role="option"], span[data-baseweb="tag"], div[data-baseweb="option"]');

    targets.forEach(el => {{
        const text = el.innerText.toLowerCase();
        for (const rule of colorRules) {{
            if (rule.keywords.some(kw => text.includes(kw))) {{
                el.style.backgroundColor = rule.bg;
                el.style.border = `1px solid ${{rule.border}}`;
                el.style.color = rule.text; 
                el.style.borderRadius = '6px';
                el.style.padding = '3px 10px';
                el.style.marginTop = '2px';
                el.style.marginBottom = '2px';
                el.style.transition = 'all 0.2s ease';
                el.querySelectorAll('*').forEach(child => {{
                    child.style.color = rule.text;
                }});
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
    .stApp {{ {app_bg_css} color: {text_color} !important; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; }}

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

    /* INPUTS, SELECTS Y BOTÓN POPOVER (SIN BORDE ROJO) */
    div[data-baseweb="input"],
    div[data-baseweb="base-input"],
    div[data-baseweb="select"] > div,
    div[data-testid="stPopover"] > button,
    button[data-testid="stPopoverButton"],
    button[data-testid="stBaseButton-secondary"] {{
        background-color: {input_bg} !important;
        border: 1px solid {input_border} !important;
        border-radius: 6px !important;
        box-shadow: none !important;
        outline: none !important;
    }}

    /* REMOVER BORDE ROJO DE FOCUS EN MULTISELECT */
    div[data-baseweb="select"] > div:focus-within,
    div[data-baseweb="base-input"]:focus-within,
    div[data-baseweb="input"]:focus-within {{
        border-color: #8c7b6d !important;
        box-shadow: 0 0 0 1px #8c7b6d !important;
    }}

    /* TEXTO INTERNO DE BUSCADOR Y BOTÓN ESENCIAS */
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

    /* ÍCONO DE FLECHA DE POPOVER Y BUSCADOR */
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

    /* TARJETAS DE DICCIONARIO DE ESENCIAS */
    .essence-card {{ border-radius: 6px; padding: 20px; margin-bottom: 15px; transition: all 0.3s ease; }}
    .essence-title {{ font-size: 1rem; font-weight: 600; color: {text_color} !important; margin-bottom: 8px; letter-spacing: 0.5px; }}
    .essence-desc {{ font-size: 0.88rem; font-weight: 400; color: {subtext_color} !important; line-height: 1.6; }}
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

# 6. BÚSQUEDA Y SELECCIÓN DE ESENCIAS
col_search, col_filter, col_separator, col_photo = st.columns([5.2, 1.8, 0.2, 2.3], vertical_alignment="center")

with col_search:
    search_query = st.text_input("🔍 Buscar", placeholder="🔍 Buscar perfume, marca o esencias...", label_visibility="collapsed")

with col_filter:
    with st.popover("Esencias", use_container_width=True):
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

# 7. CHIPS DE NAVEGACIÓN RÁPIDA
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

# 8. VISTAS DE PÁGINA
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
    st.markdown(f"<h3 style='text-align: center; color: {text_color}; letter-spacing: 1px; font-weight: 300; margin-bottom: 30px;'>DICCIONARIO DE ESENCIAS</h3>", unsafe_allow_html=True)
    st.write("Descubre qué significa cada nota olfativa y cómo aporta personalidad a tus fragancias favoritas.")
    
    esencias_dict = [
        {
            "title": "Notas Marinas (Acuáticas)", 
            "color_border": "rgba(40, 150, 180, 0.6)" if is_dark else "rgba(2, 132, 199, 0.5)", 
            "color_bg": "rgba(20, 110, 140, 0.25)" if is_dark else "rgba(224, 242, 254, 0.85)", 
            "desc": "Las notas marinas capturan el aroma del océano, la brisa marina, la sal y el yodo. Aportan una frescura ozónica, limpia y cristalina."
        },
        {
            "title": "Almizcle (Blanco / Musk)", 
            "color_border": "rgba(180, 180, 180, 0.4)" if is_dark else "rgba(148, 163, 184, 0.5)", 
            "color_bg": "rgba(160, 160, 160, 0.15)" if is_dark else "rgba(248, 250, 252, 0.95)", 
            "desc": "El almizcle blanco recrea una sensación pura de 'piel limpia', suavidad algodonosa y aporta fijación duradera."
        },
        {
            "title": "Sangre (Metálica)", 
            "color_border": "rgba(200, 70, 95, 0.6)" if is_dark else "rgba(244, 63, 94, 0.5)", 
            "color_bg": "rgba(168, 50, 75, 0.25)" if is_dark else "rgba(255, 228, 230, 0.85)", 
            "desc": "Una nota vanguardista y nicho que evoca el hierro. Aporta una sensación carnal, férrea, salada y metálica muy distintiva."
        },
        {
            "title": "Café (Gourmand)", 
            "color_border": "rgba(160, 90, 60, 0.6)" if is_dark else "rgba(217, 119, 6, 0.5)", 
            "color_bg": "rgba(110, 60, 40, 0.3)" if is_dark else "rgba(254, 243, 199, 0.85)", 
            "desc": "Aporta un matiz tostado, cálido, energizante y vagamente amargo. Ideal para perfumes con carácter adictivo."
        }
    ]

    col_es_1, col_es_2 = st.columns(2, gap="large")
    
    for i, item in enumerate(esencias_dict):
        tarjeta_html = f"""
        <div class="essence-card" style="border: 1px solid {item['color_border']}; background-color: {item['color_bg']};">
            <div class="essence-title">{item['title']}</div>
            <div class="essence-desc">{item['desc']}</div>
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
