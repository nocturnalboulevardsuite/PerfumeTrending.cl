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

# Tonos minimalistas y limpios
app_bg_css = "background-color: #fcfcfc !important;" if not is_dark else "background-color: #0a0a0a !important;"
text_color = "#ededed" if is_dark else "#111111"
subtext_color = "#888888" if is_dark else "#666666"

btn_bg = "#141414" if is_dark else "#ffffff"
btn_text = "#ffffff" if is_dark else "#111111"
btn_border = "#2a2a2a" if is_dark else "#e5e5e5"
btn_hover_bg = "#1e1e1e" if is_dark else "#f5f5f5"

input_bg = "#111111" if is_dark else "#ffffff"
input_text = "#ffffff" if is_dark else "#111111"
input_border = "#2a2a2a" if is_dark else "#e5e5e5"

bottle_left_pos = "42px" if is_dark else "-2px"
static_icon_pos = "12px center" if is_dark else "calc(100% - 12px) center"

static_icon_svg = (
    "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23ffffff' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'><circle cx='12' cy='12' r='4'/><line x1='12' y1='1' x2='12' y2='3'/><line x1='12' y1='21' x2='12' y2='23'/><line x1='4.22' y1='4.22' x2='5.64' y2='5.64'/><line x1='18.36' y1='18.36' x2='19.78' y2='19.78'/><line x1='1' y1='12' x2='3' y2='12'/><line x1='21' y1='12' x2='23' y2='12'/><line x1='4.22' y1='19.78' x2='5.64' y2='18.36'/><line x1='18.36' y1='5.64' x2='19.78' y2='4.22'/></svg>"
    if is_dark else
    "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23111111' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'><path d='M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z'/></svg>"
)

bottle_svg = (
    "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 50 58'><rect x='18' y='2' width='14' height='7' rx='2' fill='%23ffffff' stroke='%23111111' stroke-width='1.5'/><rect x='21' y='9' width='8' height='5' fill='%23ffffff' stroke='%23111111' stroke-width='1.5'/><circle cx='25' cy='34' r='19' fill='%23ffffff' stroke='%23111111' stroke-width='1.5'/><path d='M21 28a8 8 0 0 0 9 10.5 8.5 8.5 0 0 1-9-10.5z' fill='none' stroke='%23111111' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'/></svg>"
    if is_dark else
    "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 50 58'><rect x='18' y='2' width='14' height='7' rx='2' fill='%23ffffff' stroke='%23111111' stroke-width='1.5'/><rect x='21' y='9' width='8' height='5' fill='%23ffffff' stroke='%23111111' stroke-width='1.5'/><circle cx='25' cy='34' r='19' fill='%23ffffff' stroke='%23111111' stroke-width='1.5'/><circle cx='25' cy='34' r='5' fill='none' stroke='%23111111' stroke-width='1.5'/><line x1='25' y1='23' x2='25' y2='26' stroke='%23111111' stroke-width='1.5' stroke-linecap='round'/><line x1='25' y1='42' x2='25' y2='45' stroke='%23111111' stroke-width='1.5' stroke-linecap='round'/><line x1='14' y1='34' x2='17' y2='34' stroke='%23111111' stroke-width='1.5' stroke-linecap='round'/><line x1='33' y1='34' x2='36' y2='34' stroke='%23111111' stroke-width='1.5' stroke-linecap='round'/><line x1='17' y1='26' x2='19' y2='28' stroke='%23111111' stroke-width='1.5' stroke-linecap='round'/><line x1='31' y1='40' x2='33' y2='42' stroke='%23111111' stroke-width='1.5' stroke-linecap='round'/><line x1='17' y1='42' x2='19' y2='40' stroke='%23111111' stroke-width='1.5' stroke-linecap='round'/><line x1='31' y1='28' x2='33' y2='26' stroke='%23111111' stroke-width='1.5' stroke-linecap='round'/></svg>"
)

camera_icon_svg = f"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23{input_text[1:]}' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'><path d='M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z'/><circle cx='12' cy='13' r='4'/></svg>"

# 2. SCRIPT JAVASCRIPT EDITADO (Colores mate bien definidos y diferenciables)
js_color_script = f"""
<script>
function applyEssenceColors() {{
    const doc = window.parent.document;
    const isDark = {str(is_dark).lower()};
    
    // Reglas de color mate diferenciadas pero elegantes
    const colorRules = [
        // Rojo Sangre / Rosas / Frutos Rojos (Rojo Borgoña Mate)
        {{ keywords: ['sangre', 'cereza', 'frambuesa', 'pimienta rosa', 'rosa', 'ruibarbo', 'lichi'], bg: 'rgba(153, 27, 27, 0.22)', border: 'rgba(220, 38, 38, 0.65)' }},
        
        // Marinas / Acuáticas (Azul Oceánico Mate)
        {{ keywords: ['marina', 'marinas', 'agua', 'océano'], bg: 'rgba(14, 116, 144, 0.22)', border: 'rgba(6, 182, 212, 0.65)' }},
        
        // Herbal / Hojas / Fresco (Verde Bosque Mate)
        {{ keywords: ['albahaca', 'bergamota', 'cardamomo', 'higo', 'manzana', 'menta', 'pachulí', 'pera', 'romero', 'salvia', 'té verde', 'vetiver'], bg: 'rgba(21, 128, 61, 0.22)', border: 'rgba(34, 197, 94, 0.65)' }},
        
        // Ámbar / Especiados Naranjas (Naranja Terracota Mate)
        {{ keywords: ['azafrán', 'ámbar', 'mandarina', 'melocotón', 'mirra', 'naranjo', 'pomelo'], bg: 'rgba(194, 65, 12, 0.22)', border: 'rgba(249, 115, 22, 0.65)' }},
        
        // Cítricos / Dulces amarillos (Ocre / Mostaza Mate)
        {{ keywords: ['caramelo', 'cítrico', 'cítricos', 'jengibre', 'limón', 'miel', 'solares', 'piña', 'vainilla', 'ylang'], bg: 'rgba(161, 98, 7, 0.22)', border: 'rgba(234, 179, 8, 0.65)' }},
        
        // Florales Violeta / Frutas Oscuras (Ciruela / Lavanda Mate)
        {{ keywords: ['ciruela', 'grosella', 'grosellas', 'iris', 'lavanda'], bg: 'rgba(126, 34, 206, 0.22)', border: 'rgba(168, 85, 247, 0.65)' }},
        
        // Café / Cacao / Especias Cálidas (Café Tostado Oscuro)
        {{ keywords: ['cacao', 'café', 'canela', 'tonka', 'nuez moscada', 'praliné', 'tabaco'], bg: 'rgba(88, 28, 12, 0.35)', border: 'rgba(180, 83, 9, 0.75)' }},
        
        // Resinas / Inciensos (Gris Pizarra Mate)
        {{ keywords: ['ámbar gris', 'incienso'], bg: 'rgba(71, 85, 105, 0.25)', border: 'rgba(148, 163, 184, 0.65)' }},
        
        // Maderas Oscuras / Cueros / Ahumados (Madero Ahumado Mate)
        {{ keywords: ['abedul', 'cedro', 'sándalo', 'civeta', 'cuero', 'oud', 'pimienta negra'], bg: 'rgba(55, 65, 81, 0.35)', border: 'rgba(156, 163, 175, 0.65)' }},
        
        // Almizcle / Florales Blancos (Perla Neutro)
        {{ keywords: ['almizcle', 'coco', 'jazmín', 'nardos', 'neroli', 'pimienta blanca'], bg: isDark ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.05)', border: isDark ? 'rgba(255, 255, 255, 0.3)' : 'rgba(0, 0, 0, 0.3)' }}
    ];

    const targets = doc.querySelectorAll('li[role="option"], div[role="option"], span[data-baseweb="tag"]');

    targets.forEach(el => {{
        const text = el.innerText.toLowerCase();
        for (const rule of colorRules) {{
            if (rule.keywords.some(kw => text.includes(kw))) {{
                el.style.backgroundColor = rule.bg;
                el.style.border = `1px solid ${{rule.border}}`;
                el.style.color = isDark ? '#ededed' : '#111111';
                el.style.borderRadius = '4px';
                el.style.padding = '2px 8px';
                el.style.fontWeight = '500'; 
                el.style.fontSize = '0.9rem';
                el.style.transition = 'all 0.2s ease';
                
                // Mantiene el color mate al pasar el cursor sin destellos
                el.addEventListener('mouseenter', () => {{ el.style.backgroundColor = rule.border; el.style.color = '#ffffff'; }});
                el.addEventListener('mouseleave', () => {{ el.style.backgroundColor = rule.bg; el.style.color = isDark ? '#ededed' : '#111111'; }});
                break;
            }}
        }}
    }});
}}
setInterval(applyEssenceColors, 150);
</script>
"""
components.html(js_color_script, height=0, width=0)

# 3. CSS GLOBAL MINIMALISTA
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');
    
    * {{ font-family: 'Inter', sans-serif !important; }}
    
    header[data-testid="stHeader"] {{ display: none !important; }}
    .block-container {{ padding-top: 1.5rem !important; padding-bottom: 2rem !important; }}
    .stApp {{ {app_bg_css} color: {text_color} !important; }}

    .stApp p, .stApp span, .stApp label, .stMarkdown p, .stTextInput label p, .stMultiSelect label p {{
        color: {text_color} !important;
    }}

    /* NAVEGACIÓN PRINCIPAL LIMPIA */
    .st-key-n_perfumes button, .st-key-n_arabes button, .st-key-n_marcas button, 
    .st-key-n_remates button, .st-key-n_disenador button, .st-key-n_nicho button, .st-key-n_esencias button {{
        background-color: transparent !important;
        border: none !important;
        border-radius: 0px !important;
        font-weight: 500 !important;
        font-size: 0.85rem !important;
        padding: 0.4rem 0.2rem !important;
        box-shadow: none !important;
        opacity: 0.7;
        transition: opacity 0.2s ease;
    }}
    .st-key-n_perfumes button:hover, .st-key-n_arabes button:hover, .st-key-n_marcas button:hover, 
    .st-key-n_remates button:hover, .st-key-n_disenador button:hover, .st-key-n_nicho button:hover, .st-key-n_esencias button:hover {{
        opacity: 1;
    }}

    /* HERRAMIENTAS RÁPIDAS (Bordes finos) */
    .st-key-btn_trend button, .st-key-btn_trust button, .st-key-btn_compare button {{
        background-color: {btn_bg} !important;
        border: 1px solid {btn_border} !important;
        border-radius: 20px !important;
        padding: 0.3rem 0.8rem !important;
        box-shadow: none !important;
        transition: all 0.2s ease;
    }}
    .st-key-btn_trend button:hover, .st-key-btn_trust button:hover, .st-key-btn_compare button:hover {{
        background-color: {btn_hover_bg} !important;
    }}
    
    .st-key-btn_trend button p, .st-key-btn_trust button p, .st-key-btn_compare button p {{
        font-size: 0.75rem !important;
        font-weight: 500 !important;
        color: {text_color} !important;
    }}

    /* BOTÓN INGRESAR Y BÚSQUEDA */
    .st-key-login_btn button, .st-key-btn_photo_search button, div[data-testid="stPopover"] > button {{
        background-color: {btn_bg} !important;
        color: {text_color} !important;
        border: 1px solid {btn_border} !important;
        border-radius: 6px !important;
        font-weight: 500 !important;
        transition: background-color 0.2s ease;
    }}
    
    .st-key-btn_photo_search button {{
        padding: 0.4rem 0.6rem 0.4rem 2rem !important;
        background-image: url("{camera_icon_svg}") !important;
        background-repeat: no-repeat !important;
        background-position: 10px center !important;
        background-size: 16px 16px !important;
        font-size: 0.8rem !important;
    }}

    /* INPUTS Y SELECTS SUTILES */
    div[data-baseweb="input"], div[data-baseweb="select"] > div {{
        background-color: {input_bg} !important;
        border: 1px solid {input_border} !important;
        border-radius: 6px !important;
    }}
    
    div[data-baseweb="input"] input, div[data-baseweb="select"] span[data-baseweb="tag"] span, div[data-baseweb="select"] div {{
        color: {input_text} !important;
        font-size: 0.9rem !important;
    }}
    
    div[data-baseweb="input"] input::placeholder {{ color: {subtext_color} !important; opacity: 0.6; }}

    /* TARJETAS DE CATÁLOGO (Elevación suave) */
    .catalog-card {{
        background-color: {btn_bg};
        border: 1px solid {btn_border};
        border-radius: 8px;
        overflow: hidden;
        position: relative;
        margin-bottom: 25px;
        transition: transform 0.3s ease, box-shadow 0.3s ease, border-color 0.3s ease;
    }}
    .catalog-card:hover {{
        transform: translateY(-4px);
        box-shadow: 0 8px 16px rgba(0,0,0,0.06);
        border-color: #8c7b6d;
    }}
    .square-img-box {{
        position: relative; width: 100%; aspect-ratio: 1 / 1;
        background-color: #ffffff; display: flex; align-items: center; justify-content: center;
        overflow: hidden; padding: 25px; box-sizing: border-box;
    }}
    .square-img-box img {{ max-width: 100%; max-height: 100%; object-fit: contain; transition: transform 0.5s ease; }}
    .catalog-card:hover .square-img-box img {{ transform: scale(1.05); }}
    
    .card-hover-overlay {{
        position: absolute; top: 0; left: 0; right: 0; bottom: 0;
        background: rgba(0, 0, 0, 0.85); color: #ffffff; padding: 20px;
        display: flex; flex-direction: column; justify-content: center;
        opacity: 0; transition: opacity 0.3s ease; text-align: left;
    }}
    .catalog-card:hover .card-hover-overlay {{ opacity: 1; }}
    .overlay-title {{ font-size: 1rem; font-weight: 600; color: #ffffff; margin-bottom: 12px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 8px; }}
    .overlay-info {{ font-size: 0.8rem; line-height: 1.5; color: #cccccc; margin-bottom: 6px; }}
    .card-footer-info {{ padding: 12px 15px; text-align: center; background-color: {btn_bg}; border-top: 1px solid {btn_border}; }}
    .card-perfume-name {{ font-size: 0.9rem; font-weight: 500; color: {text_color}; }}
    .card-perfume-brand {{ font-size: 0.75rem; color: {subtext_color}; margin-top: 2px; }}

    /* DICCIONARIO ESENCIAS (Minimal) */
    .essence-card {{ border-radius: 6px; padding: 20px; margin-bottom: 15px; transition: transform 0.2s ease; }}
    .essence-card:hover {{ transform: scale(1.01); }}
    .essence-title {{ font-size: 1rem; font-weight: 600; color: {text_color}; margin-bottom: 8px; }}
    .essence-desc {{ font-size: 0.85rem; color: {subtext_color}; line-height: 1.6; }}
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
    
    # Tarjetas sincronizadas con la nueva paleta de colores mate
    esencias_dict = [
        {
            "title": "Notas Marinas (Acuáticas)", 
            "color_border": "rgba(6, 182, 212, 0.65)", 
            "color_bg": "rgba(14, 116, 144, 0.22)", 
            "desc": "Las notas marinas capturan el aroma del océano, la brisa marina, la sal y el yodo. Aportan una frescura ozónica, limpia y cristalina."
        },
        {
            "title": "Almizcle (Blanco / Musk)", 
            "color_border": "rgba(200, 210, 220, 0.4)", 
            "color_bg": "rgba(220, 225, 230, 0.08)", 
            "desc": "El almizcle blanco recrea una sensación pura de 'piel limpia', suavidad algodonosa y aporta fijación duradera."
        },
        {
            "title": "Sangre (Metálica)", 
            "color_border": "rgba(220, 38, 38, 0.65)", 
            "color_bg": "rgba(153, 27, 27, 0.22)", 
            "desc": "Una nota vanguardista y nicho que evoca el hierro. Aporta una sensación carnal, férrea, salada y metálica muy distintiva."
        },
        {
            "title": "Café (Gourmand)", 
            "color_border": "rgba(180, 83, 9, 0.75)", 
            "color_bg": "rgba(88, 28, 12, 0.35)", 
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
