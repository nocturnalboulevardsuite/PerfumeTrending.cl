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

camera_icon_svg = f"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23{btn_text[1:]}' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z'/><circle cx='12' cy='13' r='4'/></svg>"
user_icon_svg = f"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23{btn_text[1:]}' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2'/><circle cx='12' cy='7' r='4'/></svg>"

# NUEVO ICONO DE TREN CLÁSICO (Perfil lateral de locomotora con vías, muy claro y legible)
trend_red_svg = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23ff3838' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'><line x1='1' y1='20' x2='23' y2='20' stroke-width='2'/><circle cx='6' cy='17' r='2.5' fill='%23ff3838'/><circle cx='12' cy='17' r='2.5' fill='%23ff3838'/><circle cx='18' cy='17.5' r='1.5' fill='%23ff3838'/><path d='M3 17V7h5v10z' fill='%23ff3838'/><path d='M8 14V9h7v5z' fill='%23ff3838'/><path d='M12 9V4h3v5z' fill='%23ff3838'/><path d='M19 17l-3-4v4z' fill='%23ff3838'/><path d='M14 3a2 2 0 0 1 2-2' stroke='%23ff3838'/><path d='M16 4a2 2 0 0 1 2-2' stroke='%23ff3838'/></svg>"

shield_red_svg = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23ff3838' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z'/><path d='m9 12 2 2 4-4'/></svg>"
tag_red_svg = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23ff3838' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M12 2H2v10l11.29 11.29a1 1 0 0 0 1.41 0l7.58-7.58a1 1 0 0 0 0-1.41L12 2z'/><circle cx='7.5' cy='7.5' r='1.5' fill='%23ff3838'/></svg>"

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
                    el.style.fontSize = '0.85rem';
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

# 3. CSS ADAPTABLE Y SWITCH
st.markdown(f"""
    <style>
    header[data-testid="stHeader"] {{ display: none !important; }}
    
    .block-container {{ 
        padding-top: 1.2rem !important; 
        padding-bottom: 2rem !important; 
        max-width: 1200px !important;
    }}
    
    .stApp {{ {app_bg_css} color: {text_color} !important; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }}

    .stApp p, .stApp span, .stApp label, .stMarkdown p {{
        color: {text_color} !important;
        font-size: 1rem !important;
        text-shadow: none !important;
    }}

    /* EFECTO DE BOTONES Y ENLACES PAGE_LINK */
    div.stButton > button,
    div.stDownloadButton > button,
    div[data-testid="stPopover"] > button,
    button[data-testid="stPopoverButton"],
    .st-key-btn_photo_search button,
    .st-key-login_btn button,
    a[data-testid="stPageLink-NavLink"] {{
        transition: transform 0.22s cubic-bezier(0.34, 1.56, 0.64, 1), background-color 0.15s ease, border-color 0.15s ease, color 0.15s ease !important;
        text-shadow: none !important;
        box-shadow: none !important;
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
    div.stButton > button:focus,
    a[data-testid="stPageLink-NavLink"]:hover {{
        transform: scale(1.04) !important;
        cursor: pointer !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
        filter: none !important;
        outline: none !important;
    }}

    div.stButton > button:active,
    a[data-testid="stPageLink-NavLink"]:active {{
        transform: scale(0.98) !important;
    }}

    .st-key-login_btn, .st-key-theme_toggle {{
        display: flex !important;
        align-items: center !important;
        height: 100% !important;
    }}

    .st-key-login_btn button {{
        background-color: {btn_bg} !important;
        color: {btn_text} !important;
        border: 1px solid {btn_border} !important;
        border-radius: 8px !important;
        height: 44px !important;
        min-height: 44px !important;
        padding: 0 1rem 0 2.5rem !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        background-image: url("{user_icon_svg}") !important;
        background-repeat: no-repeat !important;
        background-position: 14px center !important;
        background-size: 18px 18px !important;
        font-size: 0.95rem !important;
        margin: 0 !important;
    }}
    .st-key-login_btn button p {{
        font-size: 0.95rem !important;
        line-height: 1 !important;
        margin: 0 !important;
        color: {btn_text} !important;
        font-weight: 600 !important;
    }}

    /* SWITCH TEMA */
    .st-key-theme_toggle,
    .st-key-theme_toggle div[data-testid="stButton"] {{
        background: transparent !important;
        background-color: transparent !important;
        display: flex !important;
        align-items: center !important;
        justify-content: flex-end !important;
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
        transform: none !important;
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

    /* NAVEGACIÓN SUPERIOR */
    .st-key-n_perfumes button, 
    .st-key-n_remates button,
    .st-key-n_esencias button {{
        background-color: transparent !important;
        border: none !important;
        border-bottom: 1px solid transparent !important;
        border-radius: 0px !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        padding: 0.6rem 0rem !important;
        box-shadow: none !important;
        letter-spacing: 0.8px !important;
        min-height: 0px !important;
        height: auto !important;
        transition: transform 0.22s cubic-bezier(0.34, 1.56, 0.64, 1), color 0.15s ease !important;
    }}

    .st-key-n_perfumes button p, 
    .st-key-n_remates button p,
    .st-key-n_esencias button p {{
        color: {text_color} !important;
        font-weight: 600 !important;
        white-space: nowrap !important;
        font-size: 0.95rem !important;
    }}

    .st-key-n_perfumes button:hover, 
    .st-key-n_remates button:hover,
    .st-key-n_esencias button:hover {{
        transform: scale(1.08) !important;
    }}

    /* CHIPS DE ACCESO RÁPIDO Y PAGE LINKS */
    a[data-testid="stPageLink-NavLink"] {{
        background-color: {btn_bg} !important;
        border: 1px solid {btn_border} !important;
        border-radius: 20px !important;
        padding: 0.45rem 1rem !important;
        box-shadow: none !important;
        width: 100% !important;
        min-height: 0px !important;
        height: auto !important;
        filter: none !important;
        text-decoration: none !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        box-sizing: border-box !important;
    }}
    
    a[data-testid="stPageLink-NavLink"] p,
    a[data-testid="stPageLink-NavLink"] span {{
        font-size: 0.85rem !important;
        font-weight: 600 !important;
        color: {btn_text} !important;
        letter-spacing: 0.2px;
        white-space: nowrap !important;
        text-overflow: clip !important;
        overflow: visible !important;
        margin: 0 !important;
    }}

    /* DIBUJOS ILUSTRADOS EN ROJO */
    a[data-testid="stPageLink-NavLink"][href*="trendhype"],
    a[data-testid="stPageLink-NavLink"][href*="trustpage"],
    a[data-testid="stPageLink-NavLink"][href*="compararprecios"] {{
        position: relative !important;
        padding-left: 2.8rem !important;
        padding-right: 1.1rem !important;
        overflow: hidden !important;
    }}

    /* 1. Trend Del Hype: Perfil lateral de tren rotado para escalar (hacia arriba) */
    a[data-testid="stPageLink-NavLink"][href*="trendhype"]::before {{
        content: '' !important;
        position: absolute !important;
        left: 14px !important;
        top: 50% !important;
        transform: translateY(-50%) rotate(-45deg) !important; 
        /* Gira el tren lateral para que apunte hacia arriba a la derecha */
        width: 20px !important;
        height: 20px !important;
        background-image: url("{trend_red_svg}") !important;
        background-repeat: no-repeat !important;
        background-size: contain !important;
        background-position: center !important;
        z-index: 1 !important;
    }}

    /* 2. Páginas de Confianza: Escudo rojo */
    a[data-testid="stPageLink-NavLink"][href*="trustpage"]::before {{
        content: '' !important;
        position: absolute !important;
        left: 14px !important;
        top: 50% !important;
        transform: translateY(-50%) !important;
        width: 18px !important;
        height: 18px !important;
        background-image: url("{shield_red_svg}") !important;
        background-repeat: no-repeat !important;
        background-size: contain !important;
        background-position: center !important;
        z-index: 1 !important;
    }}

    /* 3. Comparar Precios: Etiqueta (Tag) roja */
    a[data-testid="stPageLink-NavLink"][href*="compararprecios"]::before {{
        content: '' !important;
        position: absolute !important;
        left: 14px !important;
        top: 50% !important;
        transform: translateY(-50%) !important;
        width: 18px !important;
        height: 18px !important;
        background-image: url("{tag_red_svg}") !important;
        background-repeat: no-repeat !important;
        background-size: contain !important;
        background-position: center !important;
        z-index: 1 !important;
    }}

    /* ELIMINAR CUALQUIER ÍCONO NATIVO DE STREAMLIT SI EXISTIERA (para que no choquen) */
    a[data-testid="stPageLink-NavLink"][href*="trendhype"] span[data-testid="stPageLinkIcon"],
    a[data-testid="stPageLink-NavLink"][href*="trustpage"] span[data-testid="stPageLinkIcon"],
    a[data-testid="stPageLink-NavLink"][href*="compararprecios"] span[data-testid="stPageLinkIcon"] {{
        display: none !important;
    }}

    </style>
""", unsafe_allow_html=True)


# 4. DISPOSICIÓN DEL MENÚ SUPERIOR (NAVEGACIÓN)
col_l, col_c, col_r = st.columns([2.5, 6, 2.5], vertical_alignment="center")

with col_l:
    if st.button("Log In / Registrar", key="login_btn", use_container_width=True):
        st.session_state['current_page'] = 'login'
        st.rerun()

with col_c:
    st.markdown("""
        <div style="display:flex; justify-content:center; align-items:center; height:100%; font-family:serif; font-size:1.8rem; font-weight:bold; letter-spacing:1px; color:#ff3838; white-space:nowrap;">
            PerfumeTrending
        </div>
    """, unsafe_allow_html=True)

with col_r:
    st.button("T", key="theme_toggle", on_click=toggle_theme)

st.markdown("<div style='margin-bottom:0.8rem;'></div>", unsafe_allow_html=True)

nc1, nc2, nc3 = st.columns([1,1,1])
with nc1:
    if st.button("Perfumes", key="n_perfumes", use_container_width=True): navigate_to('home')
with nc2:
    if st.button("Remates (9+)", key="n_remates", use_container_width=True): navigate_to('remates')
with nc3:
    if st.button("Esencias", key="n_esencias", use_container_width=True): navigate_to('esencias')

st.markdown(f"<hr style='margin:0 0 1rem 0; border-color:{btn_border};'>", unsafe_allow_html=True)


# 5. CHIPS DE ACCESO RÁPIDO (USANDO ST.PAGE_LINK Y CSS INYECTADO)
if st.session_state['current_page'] == 'home':
    c1, c2, c3 = st.columns([1,1,1])
    with c1:
        st.page_link("pages/trendhype.py", label="Trend Del Hype", use_container_width=True)
    with c2:
        st.page_link("pages/trustpage.py", label="Páginas de Confianza", use_container_width=True)
    with c3:
        st.page_link("pages/compararprecios.py", label="Comparar Precios", use_container_width=True)

    st.markdown("<div style='margin-bottom:1rem;'></div>", unsafe_allow_html=True)

    st.markdown("<h3>Catálogo de Perfumes</h3>", unsafe_allow_html=True)
    st.info("Catálogo principal aquí...")

elif st.session_state['current_page'] == 'login':
    st.markdown("<h2>Log In / Registrarse</h2>", unsafe_allow_html=True)
    st.write("Pantalla de inicio de sesión.")
elif st.session_state['current_page'] == 'remates':
    st.markdown("<h2>Remates Activos</h2>", unsafe_allow_html=True)
    st.write("Lista de remates.")
elif st.session_state['current_page'] == 'esencias':
    st.markdown("<h2>Diccionario de Esencias</h2>", unsafe_allow_html=True)
    st.write("Buscador de esencias.")
