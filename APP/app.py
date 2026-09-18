import base64
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# 1. CONFIGURACIÓN DE LA PÁGINA Y ESTADO
st.set_page_config(
    page_title="PerfumeTrending", layout="wide", initial_sidebar_state="collapsed"
)

if "current_page" not in st.session_state:
  st.session_state["current_page"] = "home"
if "theme" not in st.session_state:
  st.session_state["theme"] = "dark"
if "selected_perfume" not in st.session_state:
  st.session_state["selected_perfume"] = None


def toggle_theme():
  st.session_state["theme"] = (
      "dark" if st.session_state["theme"] == "light" else "light"
  )


def navigate_to(page, perfume_data=None):
  st.session_state["current_page"] = page
  if perfume_data:
    st.session_state["selected_perfume"] = perfume_data


is_dark = st.session_state["theme"] == "dark"

# Colores dinámicos por tema
app_bg = "#0c0e12" if is_dark else "#f9f9fb"
app_bg_css = f"background-color: {app_bg} !important;"

text_color = "#f0f0f0" if is_dark else "#18181b"
subtext_color = "#9a9a9a" if is_dark else "#666670"

btn_bg = "#161920" if is_dark else "#ffffff"
btn_text = "#ffffff" if is_dark else "#18181b"
btn_border = "#2a2e39" if is_dark else "#d1d5db"

input_bg = "#14171d" if is_dark else "#ffffff"
input_text = "#f0f0f0" if is_dark else "#18181b"
input_border = "#2a2e39" if is_dark else "#d1d5db"


# Función Helper para Base64 SVG (Garantiza visibilidad en CSS)
def svg_to_uri(svg_str):
  return f"data:image/svg+xml;base64,{base64.b64encode(svg_str.encode('utf-8')).decode('utf-8')}"


# Íconos SVG para el Switch
static_icon_raw = (
    """<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='#ffffff' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><circle cx='12' cy='12' r='4'/><line x1='12' y1='1' x2='12' y2='3'/><line x1='12' y1='21' x2='12' y2='23'/><line x1='4.22' y1='4.22' x2='5.64' y2='5.64'/><line x1='18.36' y1='18.36' x2='19.78' y2='19.78'/><line x1='1' y1='12' x2='3' y2='12'/><line x1='21' y1='12' x2='23' y2='12'/><line x1='4.22' y1='19.78' x2='5.64' y2='18.36'/><line x1='18.36' y1='5.64' x2='19.78' y2='4.22'/></svg>"""
    if is_dark
    else """<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='#1a1a1a' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z'/></svg>"""
)

bottle_raw = (
    """<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 50 58'><rect x='18' y='2' width='14' height='7' rx='2' fill='#ffffff' stroke='#111111' stroke-width='2.5'/><rect x='21' y='9' width='8' height='5' fill='#ffffff' stroke='#111111' stroke-width='2.5'/><circle cx='25' cy='34' r='19' fill='#ffffff' stroke='#111111' stroke-width='2.5'/><path d='M21 28a8 8 0 0 0 9 10.5 8.5 8.5 0 0 1-9-10.5z' fill='none' stroke='#111111' stroke-width='2.2' stroke-linecap='round' stroke-linejoin='round'/></svg>"""
    if is_dark
    else """<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 50 58'><rect x='18' y='2' width='14' height='7' rx='2' fill='#ffffff' stroke='#111111' stroke-width='2.5'/><rect x='21' y='9' width='8' height='5' fill='#ffffff' stroke='#111111' stroke-width='2.5'/><circle cx='25' cy='34' r='19' fill='#ffffff' stroke='#111111' stroke-width='2.5'/><circle cx='25' cy='34' r='5' fill='none' stroke='#111111' stroke-width='2'/><line x1='25' y1='23' x2='25' y2='26' stroke='#111111' stroke-width='2' stroke-linecap='round'/><line x1='25' y1='42' x2='25' y2='45' stroke='#111111' stroke-width='2' stroke-linecap='round'/><line x1='14' y1='34' x2='17' y2='34' stroke='#111111' stroke-width='2' stroke-linecap='round'/><line x1='33' y1='34' x2='36' y2='34' stroke='#111111' stroke-width='2' stroke-linecap='round'/></svg>"""
)

static_icon_svg = svg_to_uri(static_icon_raw)
bottle_svg = svg_to_uri(bottle_raw)

camera_raw = f"""<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='{btn_text}' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z'/><circle cx='12' cy='13' r='4'/></svg>"""
user_raw = f"""<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='{btn_text}' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2'/><circle cx='12' cy='7' r='4'/></svg>"""

camera_icon_svg = svg_to_uri(camera_raw)
user_icon_svg = svg_to_uri(user_raw)

# 2. SCRIPT DE COLORES Y SONIDOS
js_color_script = f"""
<script>
(function() {{
    const doc = window.parent.document;
    const isDark = {str(is_dark).lower()};
    
    window.parent.playBubbleSound = function() {{
        try {{
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            if (!AudioContext) return;
            if (!window.parent.audioCtx) {{
                window.parent.audioCtx = new AudioContext();
            }}
            const ctx = window.parent.audioCtx;
            if (ctx.state === 'suspended') {{ ctx.resume(); }}
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

    const colorRules = [
        {{ keywords: ['sangre', 'cereza', 'frambuesa', 'pimienta rosa', 'rosa', 'ruibarbo', 'lichi', 'ciruela', 'grosella', 'peonía', 'geranio'], 
          bg: isDark ? '#3d1a1e' : '#f7eaec', border: isDark ? '#6e3037' : '#e2b3b7', text: isDark ? '#ffd1d6' : '#5c1b22' }},
        {{ keywords: ['marina', 'marinas', 'agua', 'océano', 'mar', 'ozónica', 'ozónicas', 'acuática', 'acuoso'], 
          bg: isDark ? '#152933' : '#eaf2f7', border: isDark ? '#2b536b' : '#a8c7da', text: isDark ? '#c2eeea' : '#173a4b' }},
        {{ keywords: ['albahaca', 'bergamota', 'cardamomo', 'higo', 'manzana', 'menta', 'pachulí', 'pera', 'romero', 'salvia', 'té verde', 'té blanco', 'vetiver', 'abedul', 'eucalipto', 'gálbano', 'hojas de violeta', 'herbal', 'verde'], 
          bg: isDark ? '#162b1e' : '#ebf5ee', border: isDark ? '#2a543b' : '#a4cca2', text: isDark ? '#b8f5c8' : '#193d25' }},
        {{ keywords: ['iris', 'lavanda', 'jazmín', 'nardos', 'neroli', 'violeta', 'fresia', 'heliotropo', 'mimosa', 'lila', 'magnolia', 'azahar', 'frangipani', 'gardenia', 'ylang', 'floral'], 
          bg: isDark ? '#2b1d33' : '#f2ebf7', border: isDark ? '#533863' : '#c3b1d4', text: isDark ? '#e7cdfa' : '#391c47' }},
        {{ keywords: ['caramelo', 'miel', 'solares', 'vainilla', 'cacao', 'café', 'canela', 'tonka', 'nuez moscada', 'praliné', 'haba tonka', 'almendra', 'avellana', 'leche', 'malvavisco', 'chocolate', 'ron', 'cognac', 'whisky', 'gourmand'], 
          bg: isDark ? '#332115' : '#f7ede6', border: isDark ? '#613f28' : '#d8bca7', text: isDark ? '#f7d3b7' : '#452914' }},
        {{ keywords: ['ámbar gris', 'cedro', 'sándalo', 'tabaco', 'cuero', 'oud', 'incienso', 'ciprés', 'ébano', 'guayac', 'musgo', 'estoraque', 'ládano', 'benjuí', 'maderosa'], 
          bg: isDark ? '#23272e' : '#edeef0', border: isDark ? '#434b59' : '#bdc1c9', text: isDark ? '#e1e7f2' : '#292e36' }},
        {{ keywords: ['azafrán', 'ámbar', 'mandarina', 'melocotón', 'durazno', 'mirra', 'naranjo', 'pomelo', 'cítrico', 'cítricos', 'limón', 'lima', 'clementina', 'yuzu', 'petit grain', 'piña', 'jengibre', 'cítrica'], 
          bg: isDark ? '#382013' : '#f9ede6', border: isDark ? '#693e25' : '#debca8', text: isDark ? '#ffd8be' : '#4f2711' }},
        {{ keywords: ['almizcle', 'coco', 'civeta', 'castóreo', 'pimienta blanca', 'pimienta negra', 'iso e super', 'ambroxan', 'aldehídos', 'cachemira', 'sintética'], 
          bg: isDark ? '#1f2228' : '#f2f4f7', border: isDark ? '#424957' : '#cad0d9', text: isDark ? '#e3e8f2' : '#2b3038' }}
    ];

    function applyEssenceColorsAndEvents() {{
        const targets = doc.querySelectorAll('.essence-card, li[role="option"], div[role="option"], span[data-baseweb="tag"], div[data-baseweb="option"]');
        targets.forEach(el => {{
            if (el.dataset.colored === 'true') return;
            const text = (el.innerText || '').toLowerCase();
            if (!text) return;

            for (const rule of colorRules) {{
                if (rule.keywords.some(kw => text.includes(kw))) {{
                    el.style.backgroundColor = rule.bg;
                    el.style.borderColor = rule.border;
                    el.style.color = rule.text;
                    el.dataset.colored = 'true';
                    el.querySelectorAll('*').forEach(child => {{ child.style.color = rule.text; }});
                    break;
                }}
            }}
        }});

        const essenceCards = doc.querySelectorAll('.essence-card');
        essenceCards.forEach(card => {{
            if (!card.dataset.soundAttached) {{
                card.dataset.soundAttached = 'true';
                card.addEventListener('click', () => window.parent.playBubbleSound());
            }}
        }});
    }}

    let debounceTimer = null;
    const observer = new MutationObserver(() => {{
        if (debounceTimer) clearTimeout(debounceTimer);
        debounceTimer = setTimeout(applyEssenceColorsAndEvents, 100);
    }});
    
    observer.observe(doc.body, {{ childList: true, subtree: true }});
    applyEssenceColorsAndEvents();
}})();
</script>
"""

components.html(js_color_script, height=0, width=0)

# 3. CSS COMPLETO Y CORREGIDO
st.markdown(
    f"""
    <style>
    html, body, .stApp {{
        -webkit-font-smoothing: antialiased !important;
        -moz-osx-font-smoothing: grayscale !important;
        text-rendering: optimizeLegibility !important;
    }}

    header[data-testid="stHeader"] {{ display: none !important; }}
    
    .block-container {{ 
        padding-top: 1rem !important; 
        padding-bottom: 2rem !important; 
        max-width: 1400px !important;
    }}
    
    .stApp {{ {app_bg_css} color: {text_color} !important; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }}

    .stApp p, .stApp span, .stApp label, .stMarkdown p {{
        color: {text_color} !important;
        font-size: 0.88rem !important;
        -webkit-font-smoothing: antialiased !important;
    }}

    /* Estilos generales de botones */
    div.stButton > button,
    div.stDownloadButton > button,
    div[data-testid="stPopover"] > button,
    button[data-testid="stPopoverButton"],
    .st-key-btn_photo_search button,
    .st-key-login_btn button,
    a[data-testid="stPageLink-NavLink"] {{
        transition: transform 0.2s ease, box-shadow 0.2s ease, background-color 0.15s ease, border-color 0.15s ease !important;
        -webkit-font-smoothing: antialiased !important;
        box-shadow: 0 2px 5px rgba(0,0,0,0.08) !important;
        outline: none !important;
    }}

    div.stButton > button p,
    div[data-testid="stPopover"] > button p,
    button[data-testid="stPopoverButton"] p {{
        color: {btn_text} !important;
    }}

    div.stButton > button:hover,
    div[data-testid="stPopover"] > button:hover,
    button[data-testid="stPopoverButton"]:hover,
    .st-key-btn_photo_search button:hover,
    .st-key-login_btn button:hover,
    a[data-testid="stPageLink-NavLink"]:hover {{
        transform: scale(1.03) translateY(-1px) !important;
        box-shadow: 0 6px 14px rgba(0, 0, 0, 0.25) !important;
        cursor: pointer !important;
    }}

    .st-key-login_btn button {{
        background-color: {btn_bg} !important;
        color: {btn_text} !important;
        border: 1px solid {btn_border} !important;
        border-radius: 6px !important;
        height: 40px !important;
        min-height: 40px !important;
        padding: 0 1rem 0 2.4rem !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        background-image: url("{user_icon_svg}") !important;
        background-repeat: no-repeat !important;
        background-position: 12px center !important;
        background-size: 16px 16px !important;
        font-size: 0.88rem !important;
    }}

    /* --- SWITCH DE TEMA FIX VISIBILIDAD Y POSICIÓN --- */
    .st-key-theme_toggle {{
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        width: 100% !important;
    }}

    .st-key-theme_toggle > button {{
        background-color: {"#16181f" if is_dark else "#eae8e6"} !important;
        border: 1px solid {btn_border} !important;
        border-radius: 20px !important;
        width: 78px !important;
        min-width: 78px !important;
        max-width: 78px !important;
        height: 38px !important;
        min-height: 38px !important;
        max-height: 38px !important;
        position: relative !important;
        cursor: pointer !important;
        padding: 0 !important;
        margin: 0 !important;
        overflow: hidden !important;
        box-shadow: inset 0 2px 4px rgba(0,0,0,0.25) !important;
        transform: none !important;
    }}

    .st-key-theme_toggle > button:hover {{
        transform: scale(1.04) !important;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3) !important;
    }}

    /* Ocultar texto/nodos de Streamlit dentro del botón */
    .st-key-theme_toggle > button * {{
        display: none !important;
        opacity: 0 !important;
        visibility: hidden !important;
    }}

    /* Ícono Sol/Luna estático */
    .st-key-theme_toggle > button::before {{
        content: '' !important;
        position: absolute !important;
        top: 50% !important;
        transform: translateY(-50%) !important;
        width: 18px !important;
        height: 18px !important;
        background-image: url("{static_icon_svg}") !important;
        background-repeat: no-repeat !important;
        background-size: contain !important;
        background-position: center !important;
        left: {"12px" if is_dark else "calc(100% - 30px)"} !important;
        opacity: 0.9 !important;
        z-index: 1 !important;
        pointer-events: none !important;
    }}

    /* Botella de perfume deslizante */
    .st-key-theme_toggle > button::after {{
        content: '' !important;
        position: absolute !important;
        top: 3px !important;
        left: {"41px" if is_dark else "3px"} !important;
        width: 32px !important;
        height: 32px !important;
        background-image: url("{bottle_svg}") !important;
        background-repeat: no-repeat !important;
        background-size: contain !important;
        background-position: center !important;
        transition: left 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
        z-index: 2 !important;
        pointer-events: none !important;
    }}

    /* Pestañas de Navegación Superior */
    .st-key-n_perfumes button, .st-key-n_remates button, .st-key-n_esencias button {{
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0.4rem 0rem !important;
    }}
    .st-key-n_perfumes button p, .st-key-n_remates button p, .st-key-n_esencias button p {{
        color: {text_color} !important;
        font-weight: 700 !important;
        font-size: 0.82rem !important;
        letter-spacing: 0.8px !important;
    }}

    /* Chips */
    .st-key-btn_trend button, .st-key-btn_trust button, .st-key-btn_compare button {{
        background-color: {btn_bg} !important;
        border: 1px solid {btn_border} !important;
        border-radius: 16px !important;
        padding: 0.35rem 0.85rem !important;
    }}

    div[data-baseweb="input"], div[data-baseweb="base-input"], div[data-baseweb="select"] > div, div[data-testid="stPopover"] > button {{
        background-color: {input_bg} !important;
        border: 1px solid {input_border} !important;
        border-radius: 6px !important;
        min-height: 40px !important;
        color: {input_text} !important;
    }}

    .st-key-btn_photo_search button {{
        background-color: {input_bg} !important;
        border: 1px solid {input_border} !important;
        border-radius: 6px !important;
        padding: 0.3rem 0.6rem 0.3rem 2.1rem !important;
        background-image: url("{camera_icon_svg}") !important;
        background-repeat: no-repeat !important;
        background-position: 10px center !important;
        background-size: 15px 15px !important;
        font-size: 0.85rem !important;
        min-height: 40px !important;
    }}

    /* Tarjetas de Catálogo */
    .catalog-card {{
        background-color: transparent;
        border: 1px solid {btn_border};
        border-radius: 6px;
        overflow: hidden;
        position: relative;
        margin-bottom: 16px;
        transition: border-color 0.2s ease, transform 0.2s ease;
    }}
    .catalog-card:hover {{
        border-color: #7a6a5d;
        transform: scale(1.03);
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
        padding: 14px;
        box-sizing: border-box;
    }}
    .square-img-box img {{
        max-width: 100%;
        max-height: 100%;
        object-fit: contain;
    }}
    .card-hover-overlay {{
        position: absolute;
        top: 0; left: 0; right: 0; bottom: 0;
        background: rgba(12, 14, 18, 0.94);
        color: #ffffff;
        padding: 14px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        opacity: 0;
        transition: opacity 0.2s ease;
        text-align: left;
    }}
    .catalog-card:hover .card-hover-overlay {{ opacity: 1; }}
    .overlay-title {{ font-size: 0.88rem; font-weight: 600; color: #d4c2a5; margin-bottom: 6px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 4px; }}
    .overlay-info {{ font-size: 0.76rem; font-weight: 400; line-height: 1.4; color: #b8b8b8; margin-bottom: 4px; }}
    .card-footer-info {{ padding: 10px 12px; text-align: center; background-color: {btn_bg}; }}
    .card-perfume-name {{ font-size: 0.85rem; font-weight: 500; color: {text_color}; margin-bottom: 3px; }}
    .card-perfume-brand {{ font-size: 0.7rem; font-weight: 400; color: {subtext_color}; text-transform: uppercase; letter-spacing: 0.5px; }}

    /* Tarjetas de Esencias */
    .essence-card {{ 
        border-radius: 8px; 
        padding: 14px 16px; 
        margin-bottom: 12px; 
        border-width: 1px; 
        border-style: solid;
        border-color: {btn_border};
        background-color: {btn_bg};
        cursor: pointer;
        user-select: none;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        height: 100%;
        box-sizing: border-box;
    }}
    .essence-card:hover {{
        transform: scale(1.02) translateY(-2px);
        box-shadow: 0 6px 16px rgba(0, 0, 0, 0.25);
    }}
    .essence-title {{ 
        font-size: 0.95rem; 
        font-weight: 700; 
        margin-bottom: 6px; 
        letter-spacing: 0.3px; 
        display: flex; 
        justify-content: space-between; 
        align-items: center; 
    }}
    .essence-title span:last-child {{
        font-size: 0.78rem; 
        font-weight: 500; 
    }}
    .essence-desc {{ 
        font-size: 0.84rem; 
        font-weight: 500; 
        line-height: 1.45; 
    }}
    </style>
""",
    unsafe_allow_html=True,
)

# 4. CABECERA CON LOGO Y SWITCH RESTAURADO
col_logo, col_espacio, col_actions = st.columns(
    [5, 1.8, 2.4], vertical_alignment="center"
)

with col_logo:
  logo_color = "#8c7b6d"
  logo_html = f"""
    <div style="display: inline-flex; align-items: center; gap: 12px; cursor: pointer; width: fit-content; transition: transform 0.2s ease;" onmouseover="this.style.transform='scale(1.03)'" onmouseout="this.style.transform='scale(1)'" onclick="window.location.reload();">
        <svg width="34" height="34" viewBox="0 0 36 36" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path d="M 6.8 21 L 29.2 21 C 30 25 27 32 18 32 C 9 32 6 25 6.8 21 Z" fill="{logo_color}" />
            <line x1="6.8" y1="21" x2="29.2" y2="21" stroke="{text_color}" stroke-width="1.5" />
            <line x1="18" y1="10" x2="18" y2="30" stroke="{text_color}" stroke-width="1" />
            <path d="M 18 32 C 9 32 5 24 7.5 17 C 9 12 13 10 15 10 L 21 10 C 23 10 27 12 28.5 17 C 31 24 27 32 18 32 Z" stroke="{text_color}" stroke-width="2" />
            <rect x="15" y="7" width="6" height="3" stroke="{text_color}" stroke-width="1.5" />
            <rect x="13" y="3" width="10" height="4" rx="1" stroke="{text_color}" stroke-width="1.5" />
            <rect x="16" y="0" width="4" height="3" rx="1" fill="{logo_color}" stroke="{text_color}" stroke-width="1" />
        </svg>
        <span style="font-size: 1.35rem; color: {text_color}; letter-spacing: 0.5px; -webkit-font-smoothing: antialiased;">
            <span style="font-weight: 300;">Perfume</span><span style="font-weight: 700;">Trending</span>
        </span>
    </div>
    """
  st.markdown(logo_html, unsafe_allow_html=True)

with col_actions:
  btn_col1, btn_col2 = st.columns([1.4, 1], vertical_alignment="center")
  with btn_col1:
    st.button("Ingresar", key="login_btn", use_container_width=True)
  with btn_col2:
    st.button(" ", key="theme_toggle", on_click=toggle_theme)

# 5. NAVEGACIÓN
st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
nav_cols = st.columns([1, 1, 1], vertical_alignment="center")

with nav_cols[0]:
  st.button(
      "PERFUMES",
      key="n_perfumes",
      on_click=navigate_to,
      args=("home",),
      use_container_width=True,
  )
with nav_cols[1]:
  st.button(
      "REMATES",
      key="n_remates",
      on_click=navigate_to,
      args=("hype",),
      use_container_width=True,
  )
with nav_cols[2]:
  st.button(
      "ESENCIAS",
      key="n_esencias",
      on_click=navigate_to,
      args=("esencias_page",),
      use_container_width=True,
  )

st.markdown(
    f"<hr style='margin: 6px 0 18px 0; border: none; border-bottom: 1px solid"
    f" {btn_border}; opacity: 0.3;'>",
    unsafe_allow_html=True,
)

# 6. DATOS DE ESENCIAS COMPLETOS
essences_catalog = [
    {
        "name": "Bergamota",
        "family": "Cítrica",
        "desc": (
            "Cítrico fresco, chispeante y amargo con matices florales y"
            " teáceos."
        ),
    },
    {
        "name": "Clementina",
        "family": "Cítrica",
        "desc": (
            "Jugosa, dulce y refrescante, aporta un toque cítrico efervescente."
        ),
    },
    {
        "name": "Limón",
        "family": "Cítrica",
        "desc": "Nota limpia, brillante y efervescente que brinda vitalidad inicial.",
    },
    {
        "name": "Lima",
        "family": "Cítrica",
        "desc": "Cítrico punzante, verde y tropical con acidez vibrante.",
    },
    {
        "name": "Mandarina",
        "family": "Cítrica",
        "desc": "Cítrico dulce, festivo y afrutado con tonalidades cálidas.",
    },
    {
        "name": "Neroli",
        "family": "Cítrica / Floral",
        "desc": "Aceite de la flor de azahar, fresco, verde y blanco floral.",
    },
    {
        "name": "Petit Grain",
        "family": "Cítrica / Verde",
        "desc": (
            "Extraído de las hojas de naranjo amargo, verde, terroso y cítrico."
        ),
    },
    {
        "name": "Pomelo (Toronja)",
        "family": "Cítrica",
        "desc": "Cítrico amargo, fresco y energizante.",
    },
    {
        "name": "Yuzu",
        "family": "Cítrica",
        "desc": (
            "Cítrico oriental entre mandarina y pomelo con notas exóticas."
        ),
    },
    {
        "name": "Almendra",
        "family": "Gourmand",
        "desc": "Nota suave, lactónica, ligeramente amarga y cremosa.",
    },
    {
        "name": "Avellana",
        "family": "Gourmand",
        "desc": "Cálida, tostada y untuosa con matices de frutos secos.",
    },
    {
        "name": "Ciruela",
        "family": "Frutal",
        "desc": "Fruta oscura, jugosa, licorosa y aterciopelada.",
    },
    {
        "name": "Coco",
        "family": "Frutal / Gourmand",
        "desc": "Exótico, cremoso y solar con acordes tropicales.",
    },
    {
        "name": "Durazno (Melocotón)",
        "family": "Frutal",
        "desc": "Afrutado, aterciopelado, dulce y jugoso.",
    },
    {
        "name": "Frambuesa",
        "family": "Frutal",
        "desc": "Baya dulce, ácida y vibrante con matices de cuero o ante.",
    },
    {
        "name": "Grosellas Negras",
        "family": "Frutal",
        "desc": "Frutal ácido, verde y ligeramente silvestre.",
    },
    {
        "name": "Higo",
        "family": "Frutal / Verde",
        "desc": "Verde, dulce y lactónico con recuerdo a hojas de higuera.",
    },
    {
        "name": "Lichi",
        "family": "Frutal",
        "desc": "Afrutado, acuoso y rosado con dulzura tropical.",
    },
    {
        "name": "Manzana",
        "family": "Frutal",
        "desc": "Crujiente, fresca, ácida o dulce según su variedad.",
    },
    {
        "name": "Melón",
        "family": "Frutal / Acuática",
        "desc": "Jugoso, acuoso y refrescante para composiciones estivales.",
    },
    {
        "name": "Pera",
        "family": "Frutal",
        "desc": "Fresca, crujiente, dulce y cristalina.",
    },
    {
        "name": "Piña",
        "family": "Frutal",
        "desc": "Tropical, efervescente, jugosa y ligeramente ahumada.",
    },
    {
        "name": "Ruibarbo",
        "family": "Frutal / Verde",
        "desc": "Ácido, vegetal, cortante y de perfil moderno.",
    },
    {
        "name": "Sandía",
        "family": "Frutal / Acuática",
        "desc": "Acuosa, fresca y dulce con sensación estival.",
    },
    {
        "name": "Fresia",
        "family": "Floral",
        "desc": "Floral limpia, jabonosa, picante y cristalina.",
    },
    {
        "name": "Geranio",
        "family": "Floral / Verde",
        "desc": "Fresco, mentolado, rosado y ligeramente terroso.",
    },
    {
        "name": "Heliotropo",
        "family": "Floral / Gourmand",
        "desc": "Atalcado, almendrado con matices de vainilla y cereza.",
    },
    {
        "name": "Iris (Orris)",
        "family": "Floral",
        "desc": "Lujoso, atalcado, terroso, elegante y empolvado.",
    },
    {
        "name": "Lavanda",
        "family": "Floral / Aromática",
        "desc": "Aromática, limpia, herbal y relajante.",
    },
    {
        "name": "Lilium (Lirio)",
        "family": "Floral",
        "desc": "Floral blanco denso, especiado y opulento.",
    },
    {
        "name": "Mimosa",
        "family": "Floral",
        "desc": "Cálida, atalcada, mielada y solar.",
    },
    {
        "name": "Peonía",
        "family": "Floral",
        "desc": "Rosa fresca, ligera, acuosa y romántica.",
    },
    {
        "name": "Rosa",
        "family": "Floral",
        "desc": "La reina de las flores: elegante, rica, melosa y atemporal.",
    },
    {
        "name": "Violeta",
        "family": "Floral / Verde",
        "desc": "Atalcada, dulce, verde y empolvada.",
    },
    {
        "name": "Flor de Azahar del Naranjo",
        "family": "Floral Blanco",
        "desc": "Cálida, embriagadora, dulce y solar.",
    },
    {
        "name": "Flor de Frangipani",
        "family": "Floral Blanco",
        "desc": "Exótica, tropical, lactónica y embriagadora.",
    },
    {
        "name": "Gardenia",
        "family": "Floral Blanco",
        "desc": "Cremosa, opulenta, lactónica y verde.",
    },
    {
        "name": "Jazmín",
        "family": "Floral Blanco",
        "desc": "Sensual, embriagador, indólico y luminoso.",
    },
    {
        "name": "Magnolia",
        "family": "Floral Blanco",
        "desc": "Cítrica, suave, cerosa y delicada.",
    },
    {
        "name": "Tuberosa (Nardo)",
        "family": "Floral Blanco",
        "desc": "Intensa, carnal, cremosa y fascinante.",
    },
    {
        "name": "Ylang-Ylang",
        "family": "Floral Blanco",
        "desc": "Exótica, platanosa, especiada y sensual.",
    },
    {
        "name": "Abedul",
        "family": "Maderosa / Cuero",
        "desc": (
            "Ahumado, alquitranado, leñoso y con carácter de cuero."
        ),
    },
    {
        "name": "Albahaca",
        "family": "Herbal",
        "desc": "Aromática, verde, anisada y fresca.",
    },
    {
        "name": "Eucalipto",
        "family": "Herbal",
        "desc": "Fresco, alcanforado, mentolado y vivificante.",
    },
    {
        "name": "Gálbano",
        "family": "Verde",
        "desc": "Resinoso, verde intenso, vegetal y cortante.",
    },
    {
        "name": "Hojas de Violeta",
        "family": "Verde",
        "desc": "Verde, terroso, acuático y crujiente.",
    },
    {
        "name": "Menta",
        "family": "Herbal",
        "desc": "Refrescante, efervescente, mentolada y picante.",
    },
    {
        "name": "Pachulí",
        "family": "Terrosa / Maderosa",
        "desc": "Terroso, oscuro, alcanforado y balsámico.",
    },
    {
        "name": "Romero",
        "family": "Herbal",
        "desc": "Aromático, alcanforado, herbal y estimulante.",
    },
    {
        "name": "Salvia",
        "family": "Herbal",
        "desc": "Aromática, ambarina, con tonos de cuero y té.",
    },
    {
        "name": "Té Blanco",
        "family": "Aromática",
        "desc": "Delicado, limpio, suave y zen.",
    },
    {
        "name": "Té Negro",
        "family": "Aromática",
        "desc": "Ahumado, denso, tánico y especiado.",
    },
    {
        "name": "Té Verde",
        "family": "Aromática",
        "desc": "Fresco, vegetal, estimulante y sereno.",
    },
    {
        "name": "Vetiver",
        "family": "Terrosa / Maderosa",
        "desc": (
            "Maderoso, terroso, ahumado y con notas salinas o secas."
        ),
    },
    {
        "name": "Anís Estrellado",
        "family": "Especiada",
        "desc": "Dulce, picante, aromático y anisado.",
    },
    {
        "name": "Azafrán",
        "family": "Especiada / Cuero",
        "desc": "Especiado, con matices de cuero y metálicos.",
    },
    {
        "name": "Canela",
        "family": "Especiada",
        "desc": "Cálida, picante, dulce y envolvente.",
    },
    {
        "name": "Cardamomo",
        "family": "Especiada",
        "desc": "Verde, cítrico, resinoso y picante.",
    },
    {
        "name": "Clavo de Olor",
        "family": "Especiada",
        "desc": "Cálido, eugenólico, intenso y punzante.",
    },
    {
        "name": "Jengibre",
        "family": "Especiada",
        "desc": "Picante, cítrico, efervescente y fresco.",
    },
    {
        "name": "Nuez Moscada",
        "family": "Especiada",
        "desc": "Cálida, dulce, leñosa y especiada.",
    },
    {
        "name": "Pimienta Blanca",
        "family": "Especiada",
        "desc": "Seca, picante y suavemente terrosa.",
    },
    {
        "name": "Pimienta Negra",
        "family": "Especiada",
        "desc": "Picante, punzante, efervescente y madura.",
    },
    {
        "name": "Pimienta Rosa",
        "family": "Especiada / Frutal",
        "desc": "Fresca, efervescente, rosada y levemente afrutada.",
    },
    {
        "name": "Cacao / Chocolate",
        "family": "Gourmand",
        "desc": "Oscuro, rico, amargo y reconfortante.",
    },
    {
        "name": "Café",
        "family": "Gourmand",
        "desc": "Tostado, amargo, estimulante y profundo.",
    },
    {
        "name": "Caramelo",
        "family": "Gourmand",
        "desc": "Dulce, mantecoso, tostado y adictivo.",
    },
    {
        "name": "Haba Tonka",
        "family": "Gourmand / Balsámica",
        "desc": "Cálida, con aromas a vainilla, almendra y heno.",
    },
    {
        "name": "Leche",
        "family": "Gourmand",
        "desc": "Lactónica, reconfortante, suave y cremosa.",
    },
    {
        "name": "Malvavisco",
        "family": "Gourmand",
        "desc": "Esponjoso, dulce y atalcado.",
    },
    {
        "name": "Miel",
        "family": "Gourmand",
        "desc": "Dulce, dorada, cerosa y animalik.",
    },
    {
        "name": "Praliné",
        "family": "Gourmand",
        "desc": "Frutos secos caramelizados, dulce y crujiente.",
    },
    {
        "name": "Vainilla",
        "family": "Gourmand / Oriental",
        "desc": "Cálida, reconfortante, dulce y licorosa.",
    },
    {
        "name": "Cedro",
        "family": "Maderosa",
        "desc": "Seco, leñoso, noble y elegante.",
    },
    {
        "name": "Ciprés",
        "family": "Maderosa / Verde",
        "desc": "Fresco, resinoso, leñoso y aromático.",
    },
    {
        "name": "Ébano",
        "family": "Maderosa",
        "desc": "Oscuro, denso, místico y maderoso.",
    },
    {
        "name": "Guayac",
        "family": "Maderosa / Ahumada",
        "desc": "Ahumado, balsámico, leñoso y con matices de té.",
    },
    {
        "name": "Musgo de Roble",
        "family": "Chipre / Terrosa",
        "desc": "Terroso, húmedo, boscoso y clásico.",
    },
    {
        "name": "Oud (Madera de Agar)",
        "family": "Maderosa / Resinosa",
        "desc": "Opulento, ahumado, animalik, complejo y místico.",
    },
    {
        "name": "Sándalo",
        "family": "Maderosa",
        "desc": "Cremoso, suave, cálido y maderoso.",
    },
    {
        "name": "Ámbar (Cálido)",
        "family": "Resinosa",
        "desc": "Acorde cálido, amielado, resinoso y envolvente.",
    },
    {
        "name": "Bálsamo del Perú",
        "family": "Resinosa",
        "desc": "Cálido, vainillado, balsámico y rico.",
    },
    {
        "name": "Benjuí",
        "family": "Resinosa",
        "desc": "Resina dulce, vainillada, amielada y balsámica.",
    },
    {
        "name": "Estoraque",
        "family": "Resinosa",
        "desc": "Resinoso, leñoso, con toque de cuero y floral.",
    },
    {
        "name": "Incienso (Olíbano)",
        "family": "Resinosa",
        "desc": "Ahumado, místico, cítrico y resinoso.",
    },
    {
        "name": "Ládano",
        "family": "Resinosa",
        "desc": "Ambarino, cuero, amielado y resinoso.",
    },
    {
        "name": "Mirra",
        "family": "Resinosa",
        "desc": "Cálida, resinosa, medicinal y picante.",
    },
    {
        "name": "Almizcle (Blanco/Musk)",
        "family": "Sintética",
        "desc": "Limpio, suave, empolvado y con sensación a piel.",
    },
    {
        "name": "Almizcle Vegetal",
        "family": "Sintética",
        "desc": "Botánico, suave y sedoso.",
    },
    {
        "name": "Ámbar Gris",
        "family": "Acuática",
        "desc": "Salado, ambarino, marino, mineral y sensual.",
    },
    {
        "name": "Castóreo",
        "family": "Cuero",
        "desc": "Cuero intenso, cálido y profundo.",
    },
    {
        "name": "Civeta",
        "family": "Sintética",
        "desc": "Intensa, cálida, almizclada y seductora.",
    },
    {
        "name": "Amaretto",
        "family": "Gourmand",
        "desc": "Licoroso, de almendras dulces y cereza.",
    },
    {
        "name": "Champán",
        "family": "Gourmand",
        "desc": "Efervescente, chispeante, frutal y festivo.",
    },
    {
        "name": "Cognac",
        "family": "Gourmand",
        "desc": "Rico, maderoso, licoroso y añejo.",
    },
    {
        "name": "Ginebra",
        "family": "Herbal",
        "desc": "Cítrica, efervescente y con bayas de enebro.",
    },
    {
        "name": "Mojito",
        "family": "Herbal",
        "desc": "Menta, lima, azúcar y ron fresco.",
    },
    {
        "name": "Ron",
        "family": "Gourmand",
        "desc": "Cálido, meloso, especiado y embriagador.",
    },
    {
        "name": "Whisky",
        "family": "Gourmand",
        "desc": "Ahumado, maderoso, malteado y turbado.",
    },
    {
        "name": "Aldehídos",
        "family": "Sintética",
        "desc": "Efervescente, jabonosa, aireada y brillante.",
    },
    {
        "name": "Ambroxan",
        "family": "Sintética",
        "desc": "Moderna, ambarina, limpia, salina y difusiva.",
    },
    {
        "name": "Cachemira (Cashmeran)",
        "family": "Sintética",
        "desc": "Aterciopelada, cálida, maderosa y almizclada.",
    },
    {
        "name": "Cuero",
        "family": "Cuero",
        "desc": "Ahumado, elegancia curtida, intenso y sofisticado.",
    },
    {
        "name": "Iso E Super",
        "family": "Sintética",
        "desc": (
            "Velada maderosa de cedro y ámbar, sutil e hipnótica."
        ),
    },
    {
        "name": "Notas Marinas",
        "family": "Acuática",
        "desc": "Brisa salada, yodada, fresca y oceánica.",
    },
    {
        "name": "Notas Solares",
        "family": "Sintética",
        "desc": (
            "Sensación de piel expuesta al sol, cálida y luminosa."
        ),
    },
    {
        "name": "Sangre (Metálica)",
        "family": "Sintética",
        "desc": "Nota metálica, punzante y salina vanguardista.",
    },
]

all_notes = sorted([e["name"] for e in essences_catalog])

# 7. BÚSQUEDA Y SELECCIÓN DE ESENCIAS
col_search, col_filter, col_separator, col_photo = st.columns(
    [5.5, 1.8, 0.1, 2.0], vertical_alignment="center"
)

with col_search:
  search_query = st.text_input(
      "Buscar",
      placeholder="Buscar perfume, marca o esencias...",
      label_visibility="collapsed",
  )

with col_filter:
  with st.popover("Esencias", use_container_width=True):
    selected_essences = st.multiselect(
        "Selecciona notas olfativas:",
        options=all_notes,
        placeholder="Filtrar...",
        label_visibility="collapsed",
    )

with col_separator:
  st.markdown(
      f"<div style='border-left: 1px solid {btn_border}; height: 26px; margin:"
      " auto;'></div>",
      unsafe_allow_html=True,
  )

with col_photo:
  st.button(
      "Búsqueda visual",
      key="btn_photo_search",
      help="Buscar por imagen",
      use_container_width=True,
  )

# 8. CHIPS DE NAVEGACIÓN RÁPIDA
st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
col_chip1, col_chip2, col_chip3, col_chip_space = st.columns(
    [1.3, 2.0, 1.7, 4.0], vertical_alignment="center"
)

with col_chip1:
  if st.button("Trend Del Hype", key="btn_trend", use_container_width=True):
    st.switch_page("pages/trendhype.py")
with col_chip2:
  st.page_link(
      "pages/trustpage.py",
      label="Páginas de Confianza",
      icon="🛡️",
      use_container_width=True,
  )
with col_chip3:
  st.button(
      "Comparar Precios",
      key="btn_compare",
      on_click=navigate_to,
      args=("compare_page",),
      use_container_width=True,
  )

st.markdown("<div style='margin-top: 18px;'></div>", unsafe_allow_html=True)

# 9. VISTAS DE PÁGINA Y CATÁLOGO
if st.session_state["current_page"] == "home":
  st.markdown(
      f"<div style='text-align: center; margin-bottom: 24px; color:"
      f" {text_color}; letter-spacing: 1.5px; font-weight: 300; font-size:"
      " 1.05rem; text-transform: uppercase;'>CATÁLOGO Y TENDENCIAS</div>",
      unsafe_allow_html=True,
  )

  if selected_essences:
    st.write(f"**Filtro activo:** {', '.join(selected_essences)}")

  catalog_perfumes = [
      {
          "name": "Bleu de Chanel",
          "brand": "Chanel",
          "country": "Francia 🇫🇷",
          "perfumer": "Jacques Polge",
          "notes": (
              "Toronja, Limón, Menta, Jengibre, Incienso, Cedro, Sándalo"
          ),
          "img": (
              "https://m.media-amazon.com/images/I/71R2e1U3JYL._SL1500_.jpg"
          ),
      },
      {
          "name": "Sauvage Elixir",
          "brand": "Dior",
          "country": "Francia 🇫🇷",
          "perfumer": "François Demachy",
          "notes": "Canela, Nuez Moscada, Lavanda, Regaliz, Sándalo, Ámbar",
          "img": (
              "https://m.media-amazon.com/images/I/71xSg5Wf0-L._SL1500_.jpg"
          ),
      },
      {
          "name": "Baccarat Rouge 540",
          "brand": "Maison Francis Kurkdjian",
          "country": "Francia 🇫🇷",
          "perfumer": "Francis Kurkdjian",
          "notes": (
              "Azafrán, Jazmín, Ámbar Gris, Madera de Cedro, Resina de Abeto"
          ),
          "img": (
              "https://m.media-amazon.com/images/I/61yD-8sK6yL._SL1500_.jpg"
          ),
      },
      {
          "name": "Club de Nuit Intense",
          "brand": "Armaf",
          "country": "Emiratos Árabes 🇦🇪",
          "perfumer": "Christian Provenzano",
          "notes": "Limón, Piña, Grosellas Negras, Abedul, Jazmín, Almizcle",
          "img": (
              "https://m.media-amazon.com/images/I/61Yg40gX3mL._SL1500_.jpg"
          ),
      },
      {
          "name": "Angels' Share",
          "brand": "Kilian",
          "country": "Francia 🇫🇷",
          "perfumer": "Benoist Lapouza",
          "notes": (
              "Cognac, Canela, Haba Tonka, Roble, Vainilla, Sándalo, Praliné"
          ),
          "img": (
              "https://m.media-amazon.com/images/I/61sN52z4wEL._SL1500_.jpg"
          ),
      },
      {
          "name": "YSL Libre EDP",
          "brand": "Yves Saint Laurent",
          "country": "Francia 🇫🇷",
          "perfumer": "Anne Flipo & Carlos Benaïm",
          "notes": (
              "Lavanda, Mandarina, Grosellas Negras, Flor de Azahar, Vainilla"
          ),
          "img": (
              "https://m.media-amazon.com/images/I/61A+-0V2VFL._SL1500_.jpg"
          ),
      },
  ]

  cols_per_row = 3
  for i in range(0, len(catalog_perfumes), cols_per_row):
    cols = st.columns(cols_per_row, gap="medium")
    for j in range(cols_per_row):
      if i + j < len(catalog_perfumes):
        p = catalog_perfumes[i + j]
        card_html = f"""
                <div class="catalog-card">
                    <div class="square-img-box">
                        <img src="{p['img']}" alt="{p['name']}" referrerpolicy="no-referrer">
                        <div class="card-hover-overlay">
                            <div class="overlay-title">{p['name']}</div>
                            <div class="overlay-info"><b>Orígenes:</b> {p['country']}</div>
                            <div class="overlay-info"><b>Perfumista:</b> {p['perfumer']}</div>
                            <div class="overlay-info" style="margin-top: 4px;"><b>Notas:</b> {p['notes']}</div>
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

elif st.session_state["current_page"] == "esencias_page":
  st.markdown(
      f"<div style='text-align: center; color: {text_color}; letter-spacing:"
      " 1.5px; font-weight: 300; margin-bottom: 20px; font-size: 1.05rem;"
      " text-transform: uppercase;'>DICCIONARIO DE ESENCIAS Y NOTAS"
      " OLFATIVAS</div>",
      unsafe_allow_html=True,
  )

  filtered_essences = essences_catalog

  if search_query:
    q = search_query.lower()
    filtered_essences = [
        e
        for e in filtered_essences
        if q in e["name"].lower()
        or q in e["family"].lower()
        or q in e["desc"].lower()
    ]

  if selected_essences:
    filtered_essences = [
        e
        for e in filtered_essences
        if any(s.lower() in e["name"].lower() for s in selected_essences)
    ]

  st.markdown(
      f"<div style='margin-bottom: 16px; color: {subtext_color}; font-size:"
      f" 0.85rem;'>Mostrando {len(filtered_essences)} esencias disponibles. Haz"
      " clic en cualquier tarjeta para escuchar su tono acuático.</div>",
      unsafe_allow_html=True,
  )

  if filtered_essences:
    cols_per_row = 3
    for i in range(0, len(filtered_essences), cols_per_row):
      cols = st.columns(cols_per_row, gap="small")
      for j in range(cols_per_row):
        if i + j < len(filtered_essences):
          e = filtered_essences[i + j]
          card_html = f"""
                    <div class="essence-card">
                        <div class="essence-title">
                            <span>{e['name']}</span>
                            <span>{e['family']}</span>
                        </div>
                        <div class="essence-desc">{e['desc']}</div>
                    </div>
                    """
          with cols[j]:
            st.markdown(card_html, unsafe_allow_html=True)
  else:
    st.info(
        "No se encontraron esencias que coincidan con la búsqueda o filtro"
        " seleccionado."
    )

elif st.session_state["current_page"] == "trust_page":
  st.markdown(
      f"<div style='text-align: center; color: {text_color}; font-weight: 300;"
      " font-size: 0.95rem;'>Páginas de Confianza (Próximamente)</div>",
      unsafe_allow_html=True,
  )
elif st.session_state["current_page"] == "compare_page":
  st.markdown(
      f"<div style='text-align: center; color: {text_color}; font-weight: 300;"
      " font-size: 0.95rem;'>Comparador de Precios (Próximamente)</div>",
      unsafe_allow_html=True,
  )
