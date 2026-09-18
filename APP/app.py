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

# Colores dinámicos adaptables por tema
app_bg = "#0c0e12" if is_dark else "#f9f9fb"
app_bg_css = f"background-color: {app_bg} !important;"

text_color = "#f0f0f0" if is_dark else "#18181b"
subtext_color = "#888890" if is_dark else "#666670"

btn_bg = "#161920" if is_dark else "#ffffff"
btn_text = "#ffffff" if is_dark else "#18181b"
btn_border = "#2a2e39" if is_dark else "#d1d5db"

input_bg = "#14171d" if is_dark else "#ffffff"
input_text = "#f0f0f0" if is_dark else "#18181b"
input_border = "#2a2e39" if is_dark else "#d1d5db"

# Posicionamiento del Switch de Tema
bottle_left_pos = "38px" if is_dark else "-2px"
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

camera_icon_svg = f"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23{btn_text[1:]}' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z'/><circle cx='12' cy='13' r='4'/></svg>"
user_icon_svg = f"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23{btn_text[1:]}' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2'/><circle cx='12' cy='7' r='4'/></svg>"

# 2. SCRIPT DE COLORES Y SISTEMA DE SONIDO DE BURBUJA
js_color_script = f"""
<script>
(function() {{
    const doc = window.parent.document;
    const isDark = {str(is_dark).lower()};
    
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
            btn.title = window.parent.soundMuted ? 'Sonido desactivado' : 'Sonido activado';
            btn.style.opacity = window.parent.soundMuted ? '0.55' : '1';
        }}
    }};

    const colorRules = [
        {{ keywords: ['sangre', 'cereza', 'frambuesa', 'pimienta rosa', 'rosa', 'ruibarbo', 'lichi', 'ciruela', 'grosella', 'peonía', 'geranio'], 
          bg: isDark ? '#3d1a1e' : '#f7eaec', border: isDark ? '#5c282e' : '#e2b3b7', text: isDark ? '#f0adb4' : '#5c1b22' }},
        {{ keywords: ['marina', 'marinas', 'agua', 'océano', 'mar', 'ozónica', 'ozónicas'], 
          bg: isDark ? '#152933' : '#eaf2f7', border: isDark ? '#224052' : '#a8c7da', text: isDark ? '#92ccdb' : '#173a4b' }},
        {{ keywords: ['albahaca', 'bergamota', 'cardamomo', 'higo', 'manzana', 'menta', 'pachulí', 'pera', 'romero', 'salvia', 'té verde', 'té blanco', 'vetiver', 'abedul', 'eucalipto', 'gálbano', 'hojas de violeta'], 
          bg: isDark ? '#162b1e' : '#ebf5ee', border: isDark ? '#234530' : '#a4cca2', text: isDark ? '#93d1a3' : '#193d25' }},
        {{ keywords: ['iris', 'lavanda', 'jazmín', 'nardos', 'neroli', 'violeta', 'fresia', 'heliotropo', 'mimosa', 'lila', 'magnolia', 'azahar', 'frangipani', 'gardenia', 'ylang'], 
          bg: isDark ? '#2b1d33' : '#f2ebf7', border: isDark ? '#432d52' : '#c3b1d4', text: isDark ? '#c7a9db' : '#391c47' }},
        {{ keywords: ['caramelo', 'miel', 'solares', 'vainilla', 'cacao', 'café', 'canela', 'tonka', 'nuez moscada', 'praliné', 'haba tonka', 'almendra', 'avellana', 'leche', 'malvavisco', 'chocolate', 'ron', 'cognac', 'whisky'], 
          bg: isDark ? '#332115' : '#f7ede6', border: isDark ? '#523522' : '#d8bca7', text: isDark ? '#dbb193' : '#452914' }},
        {{ keywords: ['ámbar gris', 'cedro', 'sándalo', 'tabaco', 'cuero', 'oud', 'incienso', 'ciprés', 'ébano', 'guayac', 'musgo', 'estoraque', 'ládano', 'benjuí'], 
          bg: isDark ? '#23272e' : '#edeef0', border: isDark ? '#373d47' : '#bdc1c9', text: isDark ? '#aeb5c2' : '#292e36' }},
        {{ keywords: ['azafrán', 'ámbar', 'mandarina', 'melocotón', 'durazno', 'mirra', 'naranjo', 'pomelo', 'cítrico', 'cítricos', 'limón', 'lima', 'clementina', 'yuzu', 'petit grain', 'piña', 'jengibre'], 
          bg: isDark ? '#382013' : '#f9ede6', border: isDark ? '#59331e' : '#debca8', text: isDark ? '#dfab8c' : '#4f2711' }},
        {{ keywords: ['almizcle', 'coco', 'civeta', 'castóreo', 'pimienta blanca', 'pimienta negra', 'iso e super', 'ambroxan', 'aldehídos', 'cachemira'], 
          bg: isDark ? '#1f2228' : '#f2f4f7', border: isDark ? '#333842' : '#cad0d9', text: isDark ? '#bcc2cc' : '#2b3038' }}
    ];

    function applyEssenceColorsAndEvents() {{
        const targets = doc.querySelectorAll('li[role="option"], div[role="option"], span[data-baseweb="tag"], div[data-baseweb="option"]');
        targets.forEach(el => {{
            if (el.dataset.colored === 'true') return;
            const text = (el.innerText || '').toLowerCase();
            if (!text) return;

            for (const rule of colorRules) {{
                if (rule.keywords.some(kw => text.includes(kw))) {{
                    el.style.backgroundColor = rule.bg;
                    el.style.border = '1px solid ' + rule.border;
                    el.style.color = rule.text; 
                    el.style.borderRadius = '3px';
                    el.style.padding = '2px 6px';
                    el.style.margin = '1px 0';
                    el.style.fontSize = '0.75rem';
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

        const btn = doc.getElementById('sound-toggle-btn');
        if (btn) {{
            btn.innerHTML = window.parent.soundMuted ? '🔇' : '🔊';
            btn.style.opacity = window.parent.soundMuted ? '0.55' : '1';
        }}
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

# 3. CSS ADAPTABLE, EFECTOS DE ZOOM Y NITIDEZ
st.markdown(f"""
    <style>
    html, body, .stApp {{
        zoom: 1.0;
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

    /* Estilizado global de botones con zoom grande, nitidez forzada y sombras */
    div.stButton > button,
    div.stDownloadButton > button,
    div[data-testid="stPopover"] > button,
    button[data-testid="stPopoverButton"],
    .st-key-btn_photo_search button,
    .st-key-login_btn button,
    a[data-testid="stPageLink-NavLink"] {{
        transition: transform 0.25s cubic-bezier(0.2, 0.8, 0.2, 1), box-shadow 0.25s cubic-bezier(0.2, 0.8, 0.2, 1), background-color 0.15s ease, border-color 0.15s ease, color 0.15s ease !important;
        -webkit-font-smoothing: antialiased !important;
        -moz-osx-font-smoothing: grayscale !important;
        text-rendering: optimizeLegibility !important;
        backface-visibility: hidden !important; /* Soluciona la fuente borrosa en animaciones */
        transform: translateZ(0) !important; /* Aceleración por hardware para nitidez */
        box-shadow: 0 2px 5px rgba(0,0,0,0.08) !important;
        outline: none !important;
        will-change: transform, box-shadow;
    }}

    div.stButton > button p,
    div[data-testid="stPopover"] > button p,
    button[data-testid="stPopoverButton"] p {{
        color: {btn_text} !important;
    }}

    /* Efecto Zoom Grande y Elevación Profesional en Hover */
    div.stButton > button:hover,
    div[data-testid="stPopover"] > button:hover,
    button[data-testid="stPopoverButton"]:hover,
    .st-key-btn_photo_search button:hover,
    .st-key-login_btn button:hover,
    a[data-testid="stPageLink-NavLink"]:hover,
    div.stButton > button:focus {{
        transform: scale(1.05) translateY(-2px) translateZ(0) !important;
        box-shadow: 0 8px 16px rgba(0, 0, 0, 0.25) !important; /* Sombra profesional */
        cursor: pointer !important;
        outline: none !important;
    }}
    
    /* Respuesta táctil al hacer clic */
    div.stButton > button:active,
    .st-key-btn_photo_search button:active,
    .st-key-login_btn button:active,
    a[data-testid="stPageLink-NavLink"]:active {{
        transform: scale(0.97) translateY(0) translateZ(0) !important;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.15) !important;
    }}

    /* El login button */
    .st-key-login_btn, .st-key-theme_toggle {{
        display: flex !important;
        align-items: center !important;
        height: 100% !important;
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
        margin: 0 !important;
    }}
    .st-key-login_btn button p {{
        font-size: 0.88rem !important;
        line-height: 1 !important;
        margin: 0 !important;
        color: {btn_text} !important;
        font-weight: 600 !important;
    }}

    /* Botones de navegación superior (Pestañas) */
    .st-key-n_perfumes button, 
    .st-key-n_remates button,
    .st-key-n_esencias button {{
        background-color: transparent !important;
        border: none !important;
        border-bottom: 1px solid transparent !important;
        border-radius: 0px !important;
        padding: 0.4rem 0rem !important;
        box-shadow: none !important;
        min-height: 0px !important;
        height: auto !important;
    }}

    /* Aumentando la escala hover específica para pestañas de texto para no romper su línea */
    .st-key-n_perfumes button:hover, 
    .st-key-n_remates button:hover,
    .st-key-n_esencias button:hover {{
        transform: scale(1.06) translateY(-1px) translateZ(0) !important;
        box-shadow: none !important;
    }}

    .st-key-n_perfumes button p, 
    .st-key-n_remates button p,
    .st-key-n_esencias button p {{
        color: {text_color} !important;
        font-weight: 700 !important; /* Más peso para nitidez */
        white-space: nowrap !important;
        font-size: 0.82rem !important; /* Tamaño ligeramente incrementado */
        letter-spacing: 0.8px !important;
    }}

    /* Botones tipo Chip */
    .st-key-btn_trend button, 
    .st-key-btn_trust button, 
    .st-key-btn_compare button {{
        background-color: {btn_bg} !important;
        border: 1px solid {btn_border} !important;
        border-radius: 16px !important;
        padding: 0.35rem 0.85rem !important;
        width: 100% !important;
        min-height: 0px !important;
        height: auto !important;
    }}
    
    .st-key-btn_trend button p, 
    .st-key-btn_trust button p, 
    .st-key-btn_compare button p {{
        font-size: 0.78rem !important;
        font-weight: 600 !important;
        color: {btn_text} !important;
        letter-spacing: 0.2px;
        white-space: nowrap !important;
    }}

    .st-key-btn_trend button:hover, 
    .st-key-btn_trust button:hover, 
    .st-key-btn_compare button:hover {{
        border-color: {"#4a5061" if is_dark else "#b5b5c0"} !important;
        background-color: {"#1a1d26" if is_dark else "#f0f0f5"} !important;
    }}

    /* Estilizado para st.page_link (Páginas de Confianza) */
    a[data-testid="stPageLink-NavLink"] {{
        background-color: {btn_bg} !important;
        border: 1px solid {btn_border} !important;
        border-radius: 16px !important;
        padding: 0.35rem 0.85rem !important;
        text-decoration: none !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
    }}
    a[data-testid="stPageLink-NavLink"] span,
    a[data-testid="stPageLink-NavLink"] p {{
        color: {btn_text} !important;
        font-size: 0.78rem !important;
        font-weight: 600 !important;
    }}

    /* Campos de Entrada e Inputs */
    div[data-baseweb="input"],
    div[data-baseweb="base-input"],
    div[data-baseweb="select"] > div,
    div[data-testid="stPopover"] > button,
    button[data-testid="stBaseButton-secondary"] {{
        background-color: {input_bg} !important;
        border: 1px solid {input_border} !important;
        border-radius: 6px !important;
        box-shadow: none !important;
        padding-top: 3px !important;
        padding-bottom: 3px !important;
        min-height: 40px !important;
        color: {input_text} !important;
    }}

    div[data-baseweb="input"] input,
    div[data-baseweb="base-input"] input {{
        font-size: 0.88rem !important;
        padding: 6px 10px !important;
        color: {input_text} !important;
        background-color: {input_bg} !important;
    }}

    div[data-baseweb="input"] input::placeholder {{
        color: {subtext_color} !important;
        font-size: 0.85rem !important;
    }}

    /* Botón de tema excluido del escalado y sombra para no desalinearse */
    .st-key-theme_toggle,
    .st-key-theme_toggle button,
    .st-key-theme_toggle button[data-testid="stBaseButton-secondary"],
    div.st-key-theme_toggle > button {{
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
        width: 80px !important; 
        height: 42px !important; 
        min-height: 42px !important;
        position: relative !important;
        cursor: pointer !important;
        margin: 0 auto !important;
        display: block !important;
        transform: none !important;
    }}

    .st-key-theme_toggle button:hover,
    .st-key-theme_toggle button:focus,
    .st-key-theme_toggle button:active {{
        transform: none !important;
        box-shadow: none !important;
        background: transparent !important;
    }}

    .st-key-theme_toggle button * {{ display: none !important; }}
    
    .st-key-theme_toggle button::before {{
        content: '' !important;
        position: absolute !important;
        top: 4px !important; left: 0 !important;
        width: 76px !important; height: 34px !important;
        background-color: {"#1c1f26" if is_dark else "#eae8e6"} !important;
        border: 1px solid {btn_border} !important;
        border-radius: 17px !important;
        background-image: url("{static_icon_svg}") !important;
        background-repeat: no-repeat !important;
        background-position: {static_icon_pos} !important;
        background-size: 16px 16px !important; 
    }}
    
    .st-key-theme_toggle button::after {{
        content: '' !important;
        position: absolute !important;
        top: 0px !important;
        left: {bottle_left_pos} !important;
        width: 38px !important; height: 42px !important;
        background-image: url("{bottle_svg}") !important;
        background-repeat: no-repeat !important;
        background-size: contain !important;
        transition: left 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
        z-index: 2 !important;
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
    
    .stApp .st-key-btn_photo_search button p {{
        font-size: 0.85rem !important;
        color: {btn_text} !important;
        font-weight: 600 !important;
    }}

    /* Tarjetas */
    .catalog-card {{
        background-color: transparent;
        border: 1px solid {btn_border};
        border-radius: 6px;
        overflow: hidden;
        position: relative;
        margin-bottom: 16px;
        transition: border-color 0.2s ease, transform 0.25s cubic-bezier(0.2, 0.8, 0.2, 1), box-shadow 0.25s ease;
        will-change: transform;
        backface-visibility: hidden;
        transform: translateZ(0);
    }}
    .catalog-card:hover {{
        border-color: #7a6a5d;
        transform: scale(1.04) translateY(-2px);
        box-shadow: 0 10px 20px rgba(0, 0, 0, 0.2);
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
    .overlay-title {{
        font-size: 0.88rem;
        font-weight: 600;
        color: #d4c2a5;
        margin-bottom: 6px;
        border-bottom: 1px solid rgba(255,255,255,0.1);
        padding-bottom: 4px;
    }}
    .overlay-info {{ font-size: 0.76rem; font-weight: 300; line-height: 1.4; color: #b8b8b8; margin-bottom: 4px; }}
    .card-footer-info {{ padding: 10px 12px; text-align: center; background-color: {btn_bg}; }}
    .card-perfume-name {{ font-size: 0.85rem; font-weight: 500; color: {text_color}; margin-bottom: 3px; }}
    .card-perfume-brand {{ font-size: 0.7rem; font-weight: 300; color: {subtext_color}; text-transform: uppercase; letter-spacing: 0.5px; }}

    /* Tarjetas de Esencias */
    .essence-card {{ 
        border-radius: 8px; 
        padding: 12px 14px; 
        margin-bottom: 10px; 
        border-width: 1px; 
        border-style: solid;
        cursor: pointer;
        user-select: none;
        transition: transform 0.25s cubic-bezier(0.2, 0.8, 0.2, 1), box-shadow 0.25s ease, border-color 0.25s ease;
        will-change: transform;
        backface-visibility: hidden;
        transform: translateZ(0);
    }}
    .essence-card:hover {{
        transform: scale(1.04) translateY(-3px) translateZ(0);
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.15);
    }}
    .essence-card:active {{
        transform: scale(0.97) translateY(0) translateZ(0);
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
    }}
    .essence-title {{ font-size: 0.85rem; font-weight: 600; margin-bottom: 4px; letter-spacing: 0.3px; }}
    .essence-desc {{ font-size: 0.78rem; font-weight: 400; line-height: 1.4; opacity: 0.9; }}
    </style>
""", unsafe_allow_html=True)

# 4. CABECERA CON LOGO AMPLIADO
col_logo, col_espacio, col_actions = st.columns([5, 1.8, 2.4], vertical_alignment="center")

with col_logo:
    logo_color = "#8c7b6d"
    logo_html = f"""
    <div style="display: inline-flex; align-items: center; gap: 12px; cursor: pointer; width: fit-content; transition: transform 0.25s cubic-bezier(0.2, 0.8, 0.2, 1); backface-visibility: hidden; transform: translateZ(0);" onmouseover="this.style.transform='scale(1.05) translateY(-1px) translateZ(0)'" onmouseout="this.style.transform='scale(1) translateY(0) translateZ(0)'" onclick="window.location.reload();">
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

with nav_cols[0]: st.button("PERFUMES", key="n_perfumes", on_click=navigate_to, args=('home',), use_container_width=True)
with nav_cols[1]: st.button("REMATES", key="n_remates", on_click=navigate_to, args=('hype',), use_container_width=True)
with nav_cols[2]: st.button("ESENCIAS", key="n_esencias", on_click=navigate_to, args=('esencias_page',), use_container_width=True)

st.markdown(f"<hr style='margin: 6px 0 18px 0; border: none; border-bottom: 1px solid {btn_border}; opacity: 0.3;'>", unsafe_allow_html=True)

# 6. BÚSQUEDA Y SELECCIÓN DE ESENCIAS
col_search, col_filter, col_separator, col_photo = st.columns([5.5, 1.8, 0.1, 2.0], vertical_alignment="center")

with col_search:
    search_query = st.text_input("Buscar", placeholder="Buscar perfume, marca o esencias...", label_visibility="collapsed")

raw_notes = [
    "Bergamota", "Clementina", "Limón", "Lima", "Mandarina", "Neroli", "Petit Grain", "Pomelo (Toronja)", "Yuzu",
    "Almendra", "Avellana", "Ciruela", "Coco", "Durazno (Melocotón)", "Frambuesa", "Grosellas Negras", 
    "Higo", "Lichi", "Manzana", "Melón", "Pera", "Piña", "Ruibarbo", "Sandía",
    "Fresia", "Geranio", "Heliotropo", "Iris (Orris)", "Lavanda", "Lilium (Lirio)", "Mimosa", "Peonía", "Rosa", "Violeta",
    "Flor de Azahar del Naranjo", "Flor de Frangipani", "Gardenia", "Jazmín", "Magnolia", "Tuberosa (Nardo)", "Ylang-Ylang",
    "Abedul", "Albahaca", "Eucalipto", "Gálbano", "Hojas de Violeta", "Menta", "Pachulí", "Romero", "Salvia", "Té Blanco", "Té Negro", "Té Verde", "Vetiver",
    "Anís Estrellado", "Azafrán", "Canela", "Cardamomo", "Clavo de Olor", "Jengibre", "Nuez Moscada", "Pimienta Blanca", "Pimienta Negra", "Pimienta Rosa",
    "Cacao / Chocolate", "Café", "Caramelo", "Haba Tonka", "Leche", "Malvavisco", "Miel", "Praliné", "Vainilla",
    "Cedro", "Ciprés", "Ébano", "Guayac", "Musgo de Roble", "Oud (Madera de Agar)", "Sándalo",
    "Ámbar (Cálido)", "Bálsamo del Perú", "Benjuí", "Estoraque", "Incienso (Olíbano)", "Ládano", "Mirra",
    "Almizcle (Blanco/Musk)", "Almizcle Vegetal", "Ámbar Gris", "Castóreo", "Civeta",
    "Amaretto", "Champán", "Cognac", "Ginebra", "Mojito", "Ron", "Whisky",
    "Aldehídos", "Ambroxan", "Cachemira (Cashmeran)", "Cuero", "Iso E Super", "Notas Marinas", "Notas Solares", "Sangre (Metálica)"
]

all_notes = sorted(raw_notes)

with col_filter:
    with st.popover("Esencias", use_container_width=True):
        selected_essences = st.multiselect(
            "Selecciona notas olfativas:",
            options=all_notes,
            placeholder="Filtrar...",
            label_visibility="collapsed"
        )

with col_separator:
    st.markdown(f"<div style='border-left: 1px solid {btn_border}; height: 26px; margin: auto;'></div>", unsafe_allow_html=True)

with col_photo:
    st.button("Búsqueda visual", key="btn_photo_search", help="Buscar por imagen", use_container_width=True)

# 7. CHIPS DE NAVEGACIÓN RÁPIDA
st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
col_chip1, col_chip2, col_chip3, col_chip_space = st.columns([1.3, 2.0, 1.7, 4.0], vertical_alignment="center")

with col_chip1:
    if st.button("Trend Del Hype", key="btn_trend", use_container_width=True):
        st.switch_page("pages/trendhype.py")
with col_chip2:
    st.page_link("pages/trustpage.py", label="Páginas de Confianza", icon="🛡️", use_container_width=True)
with col_chip3:
    st.button("Comparar Precios", key="btn_compare", on_click=navigate_to, args=('compare_page',), use_container_width=True)

st.markdown("<div style='margin-top: 18px;'></div>", unsafe_allow_html=True)

# 8. VISTAS DE PÁGINA
if st.session_state['current_page'] == 'home':
    st.markdown(f"<div style='text-align: center; margin-bottom: 24px; color: {text_color}; letter-spacing: 1.5px; font-weight: 300; font-size: 1.05rem; text-transform: uppercase;'>CATÁLOGO Y TENDENCIAS</div>", unsafe_allow_html=True)
    
    if selected_essences:
        st.write(f"**Filtro activo:** {', '.join(selected_essences)}")

    catalog_perfumes = [
        {
            "name": "Bleu de Chanel",
            "brand": "Chanel",
            "country": "Francia 🇫🇷",
            "perfumer": "Jacques Polge",
            "notes": "Toronja, Limón, Menta, Jengibre, Incienso, Cedro, Sándalo",
            "img": "https://m.media-amazon.com/images/I/71R2e1U3JYL._SL1500_.jpg"
        },
        {
            "name": "Sauvage Elixir",
            "brand": "Dior",
            "country": "Francia 🇫🇷",
            "perfumer": "François Demachy",
            "notes": "Canela, Nuez Moscada, Lavanda, Regaliz, Sándalo, Ámbar",
            "img": "https://m.media-amazon.com/images/I/71xSg5Wf0-L._SL1500_.jpg"
        },
        {
            "name": "Baccarat Rouge 540",
            "brand": "Maison Francis Kurkdjian",
            "country": "Francia 🇫🇷",
            "perfumer": "Francis Kurkdjian",
            "notes": "Azafrán, Jazmín, Ámbar Gris, Madera de Cedro, Resina de Abeto",
            "img": "https://m.media-amazon.com/images/I/61yD-8sK6yL._SL1500_.jpg"
        },
        {
            "name": "Club de Nuit Intense",
            "brand": "Armaf",
            "country": "Emiratos Árabes 🇦🇪",
            "perfumer": "Christian Provenzano",
            "notes": "Limón, Piña, Grosellas Negras, Abedul, Jazmín, Almizcle",
            "img": "https://m.media-amazon.com/images/I/61Yg40gX3mL._SL1500_.jpg"
        },
        {
            "name": "Angels' Share",
            "brand": "Kilian",
            "country": "Francia 🇫🇷",
            "perfumer": "Benoist Lapouza",
            "notes": "Cognac, Canela, Haba Tonka, Roble, Vainilla, Sándalo, Praliné",
            "img": "https://m.media-amazon.com/images/I/61sN52z4wEL._SL1500_.jpg"
        },
        {
            "name": "YSL Libre EDP",
            "brand": "Yves Saint Laurent",
            "country": "Francia 🇫🇷",
            "perfumer": "Anne Flipo & Carlos Benaïm",
            "notes": "Lavanda, Mandarina, Grosellas Negras, Flor de Azahar, Vainilla",
            "img": "https://m.media-amazon.com/images/I/61A+-0V2VFL._SL1500_.jpg"
        }
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

elif st.session_state['current_page'] == 'esencias_page':
    st.markdown(f"<div style='text-align: center; color: {text_color}; letter-spacing: 1px; font-weight: 300; margin-bottom: 24px; font-size: 1.05rem; text-transform: uppercase;'>DICCIONARIO DE ESENCIAS Y NOTAS</div>", unsafe_allow_html=True)
    
elif st.session_state['current_page'] == 'trust_page':
    st.markdown(f"<div style='text-align: center; color: {text_color}; font-weight: 300; font-size: 0.95rem;'>Páginas de Confianza (Próximamente)</div>", unsafe_allow_html=True)
elif st.session_state['current_page'] == 'compare_page':
    st.markdown(f"<div style='text-align: center; color: {text_color}; font-weight: 300; font-size: 0.95rem;'>Comparador de Precios (Próximamente)</div>", unsafe_allow_html=True)
