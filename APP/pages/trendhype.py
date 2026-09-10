import streamlit as st

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Radar del Hype - PerfumeTrending", layout="wide")

# 2. MANEJO DE ESTADO (Navegación, Tema y Filtro)
if 'current_page' not in st.session_state:
    st.session_state['current_page'] = 'home'
if 'theme' not in st.session_state:
    st.session_state['theme'] = 'light'
if 'selected_perfume' not in st.session_state:
    st.session_state['selected_perfume'] = None
if 'selected_month' not in st.session_state:
    st.session_state['selected_month'] = "Este Mes"

def toggle_theme():
    st.session_state['theme'] = 'dark' if st.session_state['theme'] == 'light' else 'light'

is_dark = st.session_state['theme'] == 'dark'

app_bg_css = "background-color: #f6efe9 !important;" if not is_dark else "background-color: #0e1117 !important;"
text_color = "#ffffff" if is_dark else "#1a1a1a"
subtext_color = "#a0a0a0" if is_dark else "#8c7b6d"

btn_bg = "#1f242d" if is_dark else "#ffffff"
btn_border = "#3a3f4d" if is_dark else "#d4cdc5"
btn_hover_bg = "#2d3340" if is_dark else "#fcfaf8"

# SWITCH DE TEMA
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

# 3. ESTILOS CSS REFINADOS Y ALINEACIÓN PERFECTA
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

    /* SWITCH NEUTRO */
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

    /* TÍTULO Y TOOLTIP */
    .radar-title-container {{
        display: inline-flex;
        align-items: baseline;
        gap: 6px;
    }}

    .radar-title-text {{
        color: #d9787f !important;
        font-weight: 900 !important;
        font-size: 2.1rem !important;
        letter-spacing: 1.5px !important;
        margin: 0;
        display: inline;
        transition: color 0.3s ease !important;
    }}

    .radar-title-text:hover {{
        color: #8b121a !important;
    }}

    .info-icon-container {{
        position: relative;
        display: inline-block;
        vertical-align: super;
        top: -12px;
        left: 3px;
    }}

    .info-btn-badge {{
        width: 18px;
        height: 18px;
        background: linear-gradient(135deg, #d83737 0%, #a81722 100%);
        color: #ffffff;
        border-radius: 50%;
        font-size: 11px;
        font-weight: 900;
        font-family: 'Georgia', serif;
        font-style: italic;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        box-shadow: 0 2px 6px rgba(216, 55, 55, 0.35);
        transition: transform 0.25s ease, box-shadow 0.25s ease;
    }}

    .info-icon-container:hover .info-btn-badge {{
        transform: scale(1.22);
        box-shadow: 0 4px 10px rgba(216, 55, 55, 0.5);
    }}

    .info-tooltip-box {{
        visibility: hidden;
        opacity: 0;
        width: 320px;
        background-color: {"#181a20" if is_dark else "#ffffff"};
        color: {text_color};
        border: 1px solid {"#343846" if is_dark else "#e2dacd"};
        border-radius: 12px;
        padding: 14px 16px;
        position: absolute;
        top: 26px;
        left: -140px;
        z-index: 999;
        box-shadow: 0 12px 30px rgba(0,0,0,0.25);
        font-size: 0.86rem;
        line-height: 1.45;
        transition: opacity 0.25s ease, visibility 0.25s ease, transform 0.25s ease;
        transform: translateY(-6px);
        pointer-events: none;
    }}

    .info-icon-container:hover .info-tooltip-box {{
        visibility: visible;
        opacity: 1;
        transform: translateY(0);
        pointer-events: auto;
    }}

    /* ETIQUETA "FILTRAR POR :" ALINEADA AL BOTÓN */
    .filter-label-text {{
        color: {text_color} !important;
        font-weight: 700 !important;
        font-size: 0.88rem !important;
        margin: 2 !important;
        display: flex;
        align-items: center !important;
        justify-content: flex-start;
        height: 32px;
    }}

    /* ESTILOS IDÉNTICOS Y CENTRADO ABSOLUTO PARA EL BOTÓN POP-OVER Y CHIP YOUTUBE */
    div[data-testid="stPopover"] {{
        display: flex !important;
        align-items: center !important;
        height: 32px !important;
    }}

    div[data-testid="stPopover"] > button,
    div[data-testid="stPopover"] button {{
        background-color: {btn_bg} !important;
        background: {btn_bg} !important;
        border: 1px solid {btn_border} !important;
        border-radius: 8px !important;
        padding: 0 10px !important;
        height: 32px !important;
        min-height: 32px !important;
        max-height: 32px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05) !important;
        transition: all 0.2s cubic-bezier(0.34, 1.56, 0.64, 1) !important;
        outline: none !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 5px !important;
        margin: 0 !important;
        box-sizing: border-box !important;
    }}

    /* Reset de márgenes y flex para alineación vertical idéntica */
    div[data-testid="stPopover"] button *,
    div[data-testid="stPopover"] button p,
    div[data-testid="stPopover"] button span,
    div[data-testid="stPopover"] button div {{
        color: {text_color} !important;
        font-weight: 700 !important;
        font-size: 12px !important;
        line-height: 1 !important;
        margin: 0 !important;
        padding: 0 !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
    }}

    div[data-testid="stPopover"] button svg {{
        fill: {text_color} !important;
        width: 12px !important;
        height: 12px !important;
        margin: 0 !important;
        flex-shrink: 0 !important;
    }}

    /* HOVER MODERNO EN EL BOTÓN POP-OVER */
    div[data-testid="stPopover"] button:hover {{
        background-color: {btn_hover_bg} !important;
        border-color: #d83737 !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 3px 8px rgba(0,0,0,0.08) !important;
    }}

    /* CHIP DE YOUTUBE Y TEXTO ADYACENTE CON MISMA ALTURA Y ESTILO */
    .social-select-box {{
        display: flex;
        align-items: center;
        gap: 8px;
        color: {text_color};
        font-size: 13px;
        width: 100%;
        box-sizing: border-box;
        height: 32px;
    }}

    .social-label {{
        color: {subtext_color};
        font-weight: 600;
        white-space: nowrap;
    }}

    .yt-chip-btn {{
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 6px;
        background-color: {btn_bg};
        border: 1px solid {btn_border};
        border-radius: 8px;
        padding: 0 10px;
        height: 32px;
        box-sizing: border-box;
        color: {text_color};
        font-weight: 700;
        font-size: 12px;
        line-height: 1;
        white-space: nowrap;
        cursor: pointer;
        transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1), background-color 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
        outline: none;
        user-select: none;
    }}

    .yt-chip-btn span {{
        display: inline-flex;
        align-items: center;
        line-height: 1;
    }}

    .yt-chip-btn:hover {{
        transform: translateY(-1px);
        border-color: #d83737;
        background-color: {btn_hover_bg};
        box-shadow: 0 3px 8px rgba(216, 55, 55, 0.15);
    }}

    .yt-chip-btn:active {{
        transform: scale(0.96);
    }}

    .yt-bounce {{
        animation: ytPulseBounce 0.4s ease;
    }}

    @keyframes ytPulseBounce {{
        0% {{ transform: scale(1); }}
        40% {{ transform: scale(1.12) rotate(-3deg); }}
        80% {{ transform: scale(0.96) rotate(2deg); }}
        100% {{ transform: scale(1); }}
    }}

    .yt-particle {{
        position: fixed;
        z-index: 99999;
        pointer-events: none;
        font-size: 18px;
        animation: floatAndFade 0.85s cubic-bezier(0.25, 0.8, 0.25, 1) forwards;
    }}

    @keyframes floatAndFade {{
        0% {{ opacity: 1; transform: translate(0, 0) scale(0.6) rotate(0deg); }}
        100% {{ opacity: 0; transform: translate(var(--dx), var(--dy)) scale(1.4) rotate(360deg); }}
    }}

    .social-desc {{
        font-size: 11px;
        color: {subtext_color};
        font-style: italic;
        line-height: 1.2;
    }}

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

    /* TARJETAS DE PERFUME */
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
        border-color: #d83737;
    }}

    .rank-badge {{
        position: absolute; top: -12px; left: -8px;
        background-color: {btn_bg}; color: {text_color};
        font-size: 16px; font-weight: 900; padding: 3px 10px;
        border: 2px solid {btn_border}; border-radius: 6px; box-shadow: 2px 2px 0px {btn_border}; z-index: 2;
        display: flex; align-items: center; gap: 6px;
        transition: border-color 0.3s ease;
    }}
    .hype-card:hover .rank-badge {{
        border-color: #d83737;
    }}

    @keyframes minimalStarGlow {{
        0%, 100% {{ transform: scale(1); filter: drop-shadow(0 0 2px rgba(216, 55, 55, 0.3)); opacity: 0.92; }}
        50% {{ transform: scale(1.15); filter: drop-shadow(0 0 7px rgba(216, 55, 55, 0.75)); opacity: 1; }}
    }}

    @keyframes goldStarGlow {{
        0%, 100% {{ transform: scale(1); filter: drop-shadow(0 0 2px rgba(212, 175, 55, 0.3)); opacity: 0.92; }}
        50% {{ transform: scale(1.15); filter: drop-shadow(0 0 7px rgba(241, 196, 15, 0.75)); opacity: 1; }}
    }}

    @keyframes silverStarGlow {{
        0%, 100% {{ transform: scale(1); filter: drop-shadow(0 0 2px rgba(148, 163, 184, 0.3)); opacity: 0.92; }}
        50% {{ transform: scale(1.15); filter: drop-shadow(0 0 7px rgba(226, 232, 240, 0.75)); opacity: 1; }}
    }}

    .star-minimal-ruby {{ animation: minimalStarGlow 3s ease-in-out infinite; display: inline-flex; vertical-align: middle; }}
    .star-minimal-gold {{ animation: goldStarGlow 3.2s ease-in-out infinite; display: inline-flex; vertical-align: middle; }}
    .star-minimal-silver {{ animation: silverStarGlow 3.5s ease-in-out infinite; display: inline-flex; vertical-align: middle; }}

    .score-circle {{
        position: absolute; top: 10px; right: 10px; width: 56px; height: 56px; border-radius: 50%;
        border: 2px solid {btn_border}; display: flex; flex-direction: column; justify-content: center;
        align-items: center; background-color: {btn_bg}; padding: 2px;
        box-shadow: inset 0 0 0 2px {btn_bg}, inset 0 0 0 2px {btn_border};
        transition: border-color 0.3s ease;
    }}
    .hype-card:hover .score-circle {{ border-color: #d83737; }}

    .score-title {{ font-size: 7px; font-weight: 800; line-height: 1.0; text-align: center; color: {text_color}; }}
    .score-value {{ font-size: 15px; font-weight: 900; color: {text_color}; }}
    
    .img-wrapper {{ text-align: center; margin-top: 10px; position: relative; overflow: hidden; border-radius: 8px; }}
    .img-wrapper img {{ 
        width: 105px; 
        height: 105px; 
        object-fit: contain; 
        transition: transform 0.4s cubic-bezier(0.25, 0.8, 0.25, 1);
    }}
    
    .hype-card:hover .img-wrapper img {{ transform: scale(1.12); }}

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

    /* BOTONES DE COMPARAR PRECIOS */
    div[data-testid="stElementContainer"] > div.stButton > button:not([aria-label=" "]) {{
        background-color: #d83737 !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 700 !important;
        font-size: 13px !important;
        padding: 10px 16px !important;
        box-shadow: 0 4px 12px rgba(216, 55, 55, 0.22) !important;
        transition: transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1), background-color 0.2s ease, box-shadow 0.25s ease !important;
        width: 100% !important;
    }}

    div[data-testid="stElementContainer"] > div.stButton > button:not([aria-label=" "]):hover {{
        background-color: #be2e2e !important;
        transform: scale(1.03) translateY(-2px) !important;
        box-shadow: 0 6px 18px rgba(216, 55, 55, 0.38) !important;
        color: #ffffff !important;
    }}

    div[data-testid="stElementContainer"] > div.stButton > button:not([aria-label=" "]):active {{
        transform: scale(0.98) translateY(0px) !important;
    }}
    </style>

    <script>
    function triggerYtAnimation(event, btn) {{
        btn.classList.add('yt-bounce');
        setTimeout(() => btn.classList.remove('yt-bounce'), 400);

        const emojis = ['▶️', '🔥', '✨', '🎵', '❤️', '🍿', '🚀', '⭐'];
        const rect = btn.getBoundingClientRect();

        for(let i=0; i<14; i++) {{
            const particle = document.createElement('span');
            particle.innerHTML = emojis[Math.floor(Math.random() * emojis.length)];
            particle.className = 'yt-particle';
            
            const startX = event.clientX || (rect.left + rect.width / 2);
            const startY = event.clientY || (rect.top + rect.height / 2);
            
            const angle = Math.random() * Math.PI * 2;
            const distance = 45 + Math.random() * 85;
            const destX = Math.cos(angle) * distance;
            const destY = Math.sin(angle) * distance - 35;
            
            particle.style.left = startX + 'px';
            particle.style.top = startY + 'px';
            particle.style.setProperty('--dx', destX + 'px');
            particle.style.setProperty('--dy', destY + 'px');
            
            document.body.appendChild(particle);
            setTimeout(() => particle.remove(), 850);
        }}
    }}
    </script>
""", unsafe_allow_html=True)

# 4. CABECERA CON LOGO Y TEMAS
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

# SECCIÓN DEL TÍTULO CON BOTÓN FLOTANTE 'i'
st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
col_header_title, col_back_btn = st.columns([3.4, 1], vertical_alignment="center")

with col_header_title:
    title_html = f"""
    <div class="radar-title-container">
        <h1 class="radar-title-text">RADAR DEL HYPE - VIRAL FRAGRANCES</h1>
        <div class="info-icon-container">
            <div class="info-btn-badge">i</div>
            <div class="info-tooltip-box">
                <div style="font-weight: 800; color: #d83737; margin-bottom: 6px; font-size: 0.92rem;">📡 ¿Qué es el Radar del Hype?</div>
                Es nuestro sistema inteligente que detecta qué fragancias se están volviendo virales en tiempo real analizando menciones y reproducciones en <b>YouTube</b>. Una herramienta clave para <b>revendedores, influencers y entusiastas</b> que buscan adelantarse a las tendencias del mercado.
            </div>
        </div>
    </div>
    """
    st.markdown(title_html, unsafe_allow_html=True)

with col_back_btn:
    st.markdown('<a href="app.py" target="_self" class="nav-back-link">← Volver al Catálogo principal</a>', unsafe_allow_html=True)

st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)

# 5. FILTROS ALINEADOS Y PEGADOS ("Filtrado por :" + Popover)
col_title, col_fecha, col_red = st.columns([0.28, 0.42, 3.3], gap="small", vertical_alignment="center")

with col_title:
    st.markdown("<div class='filter-label-text'>Filtrado por :</div>", unsafe_allow_html=True)

with col_fecha:
    opciones_fecha = ["Este Mes", "Hoy / Día", "Esta Semana", "Este Año", "Año Pasado"]
    with st.popover(f"📅 {st.session_state['selected_month']}", use_container_width=False):
        for opt in opciones_fecha:
            if st.button(opt, key=f"btn_m_{opt}", use_container_width=True):
                st.session_state['selected_month'] = opt
                st.rerun()

with col_red:
    social_select_html = f"""
    <div class="social-select-box">
        <span class="social-label">Red social analizada:</span>
        <button class="yt-chip-btn" onclick="triggerYtAnimation(event, this)">
            <svg width="16" height="12" viewBox="0 0 26 20" fill="none">
                <rect x="1" y="1" width="24" height="18" rx="5" fill="#d83737" />
                <polygon points="10,5 18,10 10,15" fill="#ffffff" />
            </svg>
            <span>YouTube</span>
        </button>
        <span class="social-desc">(Mide la popularidad en tiempo real según menciones y reseñas en video)</span>
    </div>
    """
    st.markdown(social_select_html, unsafe_allow_html=True)

st.write("")

# 6. ICONOS DE ESTRELLAS
star_ruby_svg = """
<div class="star-minimal-ruby">
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
        <defs>
            <linearGradient id="minRuby" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#ff4d5a"/>
                <stop offset="100%" stop-color="#a81722"/>
            </linearGradient>
        </defs>
        <path d="M12 2L14.4 9.6L22 12L14.4 14.4L12 22L9.6 14.4L2 12L9.6 9.6L12 2Z" fill="url(#minRuby)" stroke="#ff8591" stroke-width="0.8"/>
        <circle cx="12" cy="12" r="1.5" fill="#ffffff" opacity="0.9"/>
    </svg>
</div>
"""

star_gold_svg = """
<div class="star-minimal-gold">
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
        <defs>
            <linearGradient id="minGold" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#f3e5ab"/>
                <stop offset="50%" stop-color="#d4af37"/>
                <stop offset="100%" stop-color="#aa7c11"/>
            </linearGradient>
        </defs>
        <path d="M12 2L14.4 9.6L22 12L14.4 14.4L12 22L9.6 14.4L2 12L9.6 9.6L12 2Z" fill="url(#minGold)" stroke="#fff3a8" stroke-width="0.8"/>
        <circle cx="12" cy="12" r="1.5" fill="#ffffff" opacity="0.9"/>
    </svg>
</div>
"""

star_silver_svg = """
<div class="star-minimal-silver">
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
        <defs>
            <linearGradient id="minSilver" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#ffffff"/>
                <stop offset="100%" stop-color="#8a99ad"/>
            </linearGradient>
        </defs>
        <path d="M12 2L14.4 9.6L22 12L14.4 14.4L12 22L9.6 14.4L2 12L9.6 9.6L12 2Z" fill="url(#minSilver)" stroke="#e2e8f0" stroke-width="0.8"/>
        <circle cx="12" cy="12" r="1.5" fill="#ffffff" opacity="0.9"/>
    </svg>
</div>
"""

hype_data = [
    {
        "rank": "#1", "star": star_ruby_svg, "name": "Bleu de Chanel", "score": "95%", "year": "2010", "price": "$180,000 CLP",
        "img": "https://fimgs.net/mdig/rx_perfume/58/28/6005828.jpg",
        "stats": "↗ 75 videos y 1.5M<br>visitas este mes",
        "ai_text": "Tendencia por su versatilidad fresca y estética de 'lujo silencioso' en YouTube."
    },
    {
        "rank": "#2", "star": star_gold_svg, "name": "YSL Libre EDP", "score": "90%", "year": "2019", "price": "$150,000 CLP",
        "img": "https://fimgs.net/mdig/rx_perfume/56/55/5605655.jpg",
        "stats": "↗ 60 videos y 1.0M<br>visitas este mes",
        "ai_text": "Gran popularidad por su elegante nota de lavanda floral para uso diario o de noche."
    },
    {
        "rank": "#3", "star": star_silver_svg, "name": "Dior Sauvage", "score": "88%", "year": "2015", "price": "$165,000 CLP",
        "img": "https://fimgs.net/mdig/rx_perfume/31/86/31861.jpg",
        "stats": "↗ 55 videos y 900k<br>visitas este mes",
        "ai_text": "Dominio constante en redes por su proyección masiva y versatilidad inigualable."
    },
    {
        "rank": "#4", "star": "", "name": "Baccarat Rouge 540", "score": "86%", "year": "2015", "price": "$310,000 CLP",
        "img": "https://fimgs.net/mdig/rx_perfume/30/88/30886.jpg",
        "stats": "↗ 48 videos y 820k<br>visitas este mes",
        "ai_text": "El aroma nicho dulzón y ambarado más clonado e influyente de YouTube."
    },
    {
        "rank": "#5", "star": "", "name": "Club de Nuit Intense", "score": "84%", "year": "2015", "price": "$45,000 CLP",
        "img": "https://fimgs.net/mdig/rx_perfume/27/65/27656.jpg",
        "stats": "↗ 42 videos y 750k<br>visitas este mes",
        "ai_text": "Rey indiscutido de las fragancias árabes relación precio-calidad."
    },
    {
        "rank": "#6", "star": "", "name": "Angels' Share", "score": "82%", "year": "2020", "price": "$240,000 CLP",
        "img": "https://fimgs.net/mdig/rx_perfume/62/61/62615.jpg",
        "stats": "↗ 38 videos y 680k<br>visitas este mes",
        "ai_text": "Tendencia invernal gourmand con notas de licor de canela y praliné."
    }
]

# 7. RENDERIZADO DE TARJETAS EN REJILLA
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
                    <div class="rank-badge">{data['star']}{data['rank']}</div>
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
