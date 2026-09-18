import streamlit as st
import streamlit.components.v1 as components

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(
    page_title="Páginas de Confianza - PerfumeTrending",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2. GESTIÓN DEL TEMA Y ESTADO
if "theme" not in st.session_state:
    st.session_state.theme = "dark"

def toggle_theme():
    st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"

is_dark = st.session_state.theme == "dark"

# 3. PALETA DE COLORES MINIMALISTA Y LUXURY
bg_color = "#0c0e12" if is_dark else "#f9f9fb"
card_bg = "#14171d" if is_dark else "#ffffff"
border_color = "#2a2e39" if is_dark else "#e4e4e7"
text_color = "#f0f0f0" if is_dark else "#18181b"
subtext_color = "#9a9a9a" if is_dark else "#71717a"
accent_color = "#d4c2a5" if is_dark else "#8c7b6d"

badge_green_bg = "#162b1e" if is_dark else "#ecfdf5"
badge_green_text = "#b8f5c8" if is_dark else "#047857"
badge_green_border = "#2a543b" if is_dark else "#a7f3d0"

btn_text = "#ffffff" if is_dark else "#18181b"
bottle_left_pos = "38px" if is_dark else "-2px"
static_icon_pos = "12px center" if is_dark else "calc(100% - 12px) center"

# SVGs para Controles
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

# 4. ESTILOS CSS PROFESIONALES Y NÍTIDOS
st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"], .stApp {{
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
        -webkit-font-smoothing: antialiased !important;
        -moz-osx-font-smoothing: grayscale !important;
        background-color: {bg_color} !important;
        color: {text_color} !important;
    }}

    header[data-testid="stHeader"] {{ display: none !important; }}
    
    .block-container {{ 
        padding-top: 1.2rem !important; 
        padding-bottom: 3rem !important; 
        max-width: 1280px !important;
    }}

    /* Banner Hero de Confianza */
    .hero-banner {{
        background: linear-gradient(135deg, {card_bg} 0%, {bg_color} 100%);
        border: 1px solid {border_color};
        border-radius: 16px;
        padding: 28px 32px;
        margin-bottom: 24px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 20px;
    }}
    .hero-text h1 {{
        font-size: 1.6rem;
        font-weight: 700;
        margin: 0 0 6px 0;
        color: {text_color};
        letter-spacing: -0.02em;
    }}
    .hero-text p {{
        font-size: 0.92rem;
        color: {subtext_color};
        margin: 0;
        line-height: 1.5;
    }}
    .trust-badges-row {{
        display: flex;
        gap: 16px;
    }}
    .trust-pill {{
        background-color: {card_bg};
        border: 1px solid {border_color};
        padding: 8px 14px;
        border-radius: 30px;
        font-size: 0.8rem;
        font-weight: 500;
        color: {text_color};
        display: flex;
        align-items: center;
        gap: 6px;
    }}

    /* Tarjetas de Sitios / Tiendas */
    .trust-card {{
        background-color: {card_bg};
        border: 1px solid {border_color};
        border-radius: 14px;
        padding: 20px 22px;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        box-sizing: border-box;
    }}
    .trust-card:hover {{
        transform: translateY(-3px);
        border-color: {accent_color};
        box-shadow: 0 8px 20px rgba(0,0,0,0.12);
    }}
    .card-top {{
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 12px;
    }}
    .card-title-box h3 {{
        margin: 0 0 2px 0;
        font-size: 1.05rem;
        font-weight: 600;
        color: {text_color};
    }}
    .card-category {{
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.6px;
        color: {subtext_color};
        font-weight: 500;
    }}
    .verified-badge {{
        background-color: {badge_green_bg};
        color: {badge_green_text};
        border: 1px solid {badge_green_border};
        padding: 3px 9px;
        border-radius: 20px;
        font-size: 0.72rem;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }}
    .card-desc {{
        font-size: 0.86rem;
        color: {subtext_color};
        line-height: 1.5;
        margin-bottom: 16px;
        flex-grow: 1;
    }}
    .tag-container {{
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        margin-bottom: 16px;
    }}
    .card-footer {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding-top: 12px;
        border-top: 1px solid {border_color};
    }}
    .rating-stars {{
        font-size: 0.82rem;
        color: {accent_color};
        font-weight: 600;
    }}
    .visit-btn {{
        background-color: {bg_color};
        color: {text_color} !important;
        border: 1px solid {border_color};
        padding: 6px 14px;
        border-radius: 8px;
        font-size: 0.8rem;
        font-weight: 500;
        text-decoration: none !important;
        transition: all 0.2s ease;
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }}
    .visit-btn:hover {{
        border-color: {accent_color};
        color: {accent_color} !important;
    }}

    /* Botón Switch de Tema Custom */
    div[data-testid="stColumn"]:nth-child(2) div[data-testid="stButton"] button {{
        background-image: url("{static_icon_svg}");
        background-repeat: no-repeat;
        background-position: {static_icon_pos};
        background-size: 20px;
        background-color: {card_bg};
        border: 1px solid {border_color};
        border-radius: 30px;
        width: 76px !important;
        height: 38px !important;
        position: relative;
        color: transparent !important;
        padding: 0;
        transition: all 0.3s ease;
    }}
    div[data-testid="stColumn"]:nth-child(2) div[data-testid="stButton"] button::after {{
        content: '';
        position: absolute;
        top: 50%;
        left: {bottle_left_pos};
        transform: translateY(-50%);
        width: 32px;
        height: 32px;
        background-image: url("{bottle_svg}");
        background-size: contain;
        background-repeat: no-repeat;
        transition: left 0.35s cubic-bezier(0.68, -0.55, 0.265, 1.55);
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

# 5. HEADER Y LOGO
col_logo, col_controls = st.columns([7, 3], vertical_alignment="center")

with col_logo:
    logo_color = "#8c7b6d"
    logo_html = f"""
    <div style="display: inline-flex; align-items: center; gap: 12px; cursor: pointer;" onclick="window.location.reload();">
        <svg width="36" height="36" viewBox="0 0 36 36" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path d="M 6.8 21 L 29.2 21 C 30 25 27 32 18 32 C 9 32 6 25 6.8 21 Z" fill="{logo_color}" />
            <line x1="6.8" y1="21" x2="29.2" y2="21" stroke="{text_color}" stroke-width="1.5" />
            <line x1="18" y1="10" x2="18" y2="30" stroke="{text_color}" stroke-width="1" />
            <path d="M 18 32 C 9 32 5 24 7.5 17 C 9 12 13 10 15 10 L 21 10 C 23 10 27 12 28.5 17 C 31 24 27 32 18 32 Z" stroke="{text_color}" stroke-width="2" />
            <rect x="15" y="7" width="6" height="3" stroke="{text_color}" stroke-width="1.5" />
            <rect x="13" y="3" width="10" height="4" rx="1" stroke="{text_color}" stroke-width="1.5" />
            <rect x="16" y="0" width="4" height="3" rx="1" fill="{logo_color}" stroke="{text_color}" stroke-width="1" />
        </svg>
        <span style="font-size: 1.4rem; color: {text_color}; letter-spacing: 0.5px;">
            <span style="font-weight: 300;">Perfume</span><span style="font-weight: 700;">Trending</span>
        </span>
    </div>
    """
    st.markdown(logo_html, unsafe_allow_html=True)

with col_controls:
    c_sound, c_theme = st.columns([1, 1], vertical_alignment="center")
    with c_sound:
        st.markdown('<button id="sound-toggle-btn" class="sound-btn" onclick="window.parent.toggleSoundMute()" title="Activar/Desactivar Sonido">🔊</button>', unsafe_allow_html=True)
    with c_theme:
        st.button(" ", on_click=toggle_theme, key="theme_switch_btn")

st.markdown("<div style='margin-top: 16px;'></div>", unsafe_allow_html=True)

# 6. BANNER HERO
hero_html = f"""
<div class="hero-banner">
    <div class="hero-text">
        <h1>🛡️ Directorio de Confianza</h1>
        <p>Comercios, perfumerías y tiendas de decants verificadas para garantizar compras 100% auténticas y seguras.</p>
    </div>
    <div class="trust-badges-row">
        <div class="trust-pill">✨ 100% Originales</div>
        <div class="trust-pill">🔒 Sitios Verificados</div>
    </div>
</div>
"""
st.markdown(hero_html, unsafe_allow_html=True)

# 7. FILTROS LIMPIOS
f_col1, f_col2 = st.columns([2.5, 1], vertical_alignment="center")

with f_col1:
    search_query = st.text_input("Buscar tienda...", placeholder="Buscar por nombre, nota olfativa o tipo de tienda...", label_visibility="collapsed")

with f_col2:
    category = st.selectbox(
        "Categoría",
        ["Todas las Categorías", "Perfumería Nicho", "Tiendas Oficiales", "Decants & Muestras", "Retailers Autorizados"],
        label_visibility="collapsed"
    )

st.markdown("<div style='margin-top: 12px;'></div>", unsafe_allow_html=True)

# 8. BASE DE DATOS DE TIENDAS Y SITIOS
trusted_sites = [
    {
        "name": "L'Essence Botanique",
        "domain": "https://essences.example.com",
        "category": "Perfumería Nicho",
        "rating": 5,
        "verified": True,
        "description": "Atelier exclusivo especializado en alta perfumería artesanal, acordes de bergamota, té verde y vetiver puro.",
        "tags": ["bergamota", "té verde", "jazmín", "vetiver"]
    },
    {
        "name": "Maison Cerise",
        "domain": "https://maisoncerise.example.com",
        "category": "Perfumería Nicho",
        "rating": 5,
        "verified": True,
        "description": "Boutique de fragancias de autor con notas destacadas de cereza, rosa de Grasse y pimienta rosa.",
        "tags": ["cereza", "rosa", "pimienta rosa"]
    },
    {
        "name": "Amber & Oud Luxe",
        "domain": "https://amberoud.example.com",
        "category": "Decants & Muestras",
        "rating": 5,
        "verified": True,
        "description": "Especialistas en fraccionado y decants de elixires orientales infusionados con ámbar, cedro y tonka.",
        "tags": ["ámbar", "cedro", "sándalo", "cacao", "tonka"]
    },
    {
        "name": "Falabella Perfumes",
        "domain": "https://falabella.example.com",
        "category": "Retailers Autorizados",
        "rating": 5,
        "verified": True,
        "description": "Distribuidor oficial directo de marcas internacionales diseñador con garantía total de importación.",
        "tags": ["cítrico", "vainilla", "oficial"]
    },
    {
        "name": "Decant Boutique Club",
        "domain": "https://decantclub.example.com",
        "category": "Decants & Muestras",
        "rating": 4,
        "verified": True,
        "description": "Muestras garantizadas de 2ml a 10ml de perfumes de diseñador y nicho en frascos de vidrio con atomizador de lujo.",
        "tags": ["limón", "cuero", "decant"]
    },
    {
        "name": "Paris Departamental",
        "domain": "https://paris.example.com",
        "category": "Tiendas Oficiales",
        "rating": 5,
        "verified": True,
        "description": "Cadena de retail con catálogo extenso de perfumería comercial y ofertas de temporada auditadas.",
        "tags": ["oficial", "lavanda"]
    }
]

# Filtrado de Datos
filtered_sites = [
    s for s in trusted_sites
    if (
        search_query.lower() in s["name"].lower()
        or search_query.lower() in s["description"].lower()
        or any(search_query.lower() in tag.lower() for tag in s["tags"])
    )
    and (category == "Todas las Categorías" or s["category"] == category)
]

# 9. RENDERIZADO EN GRID EN Mosaico (3 Columnas)
if filtered_sites:
    cols_per_row = 3
    for i in range(0, len(filtered_sites), cols_per_row):
        cols = st.columns(cols_per_row, gap="medium")
        for j in range(cols_per_row):
            if i + j < len(filtered_sites):
                site = filtered_sites[i + j]
                tags_html = "".join([f'<span data-baseweb="tag">{tag}</span>' for tag in site["tags"]])
                badge_html = '<span class="verified-badge">Garantizado 🛡️</span>' if site["verified"] else ''
                stars = "★" * site["rating"] + "☆" * (5 - site["rating"])

                card_html = f"""
                <div class="trust-card essence-card">
                    <div>
                        <div class="card-top">
                            <div class="card-title-box">
                                <h3>{site['name']}</h3>
                                <div class="card-category">{site['category']}</div>
                            </div>
                            {badge_html}
                        </div>
                        <div class="card-desc">{site['description']}</div>
                        <div class="tag-container">{tags_html}</div>
                    </div>
                    <div class="card-footer">
                        <span class="rating-stars">{stars}</span>
                        <a href="{site['domain']}" target="_blank" class="visit-btn">Visitar Tienda ↗</a>
                    </div>
                </div>
                """
                with cols[j]:
                    st.markdown(card_html, unsafe_allow_html=True)
else:
    st.info("No se encontraron tiendas o sitios que coincidan con el criterio de búsqueda.")

# 10. SCRIPT DE COLORES Y SONIDO INTEGRADO
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
            btn.style.opacity = window.parent.soundMuted ? '0.55' : '1';
        }}
    }};

    const colorRules = [
        {{ keywords: ['sangre', 'cereza', 'frambuesa', 'pimienta rosa', 'rosa', 'ruibarbo', 'lichi', 'ciruela', 'grosella', 'peonía', 'geranio'], 
          bg: isDark ? '#3d1a1e' : '#f7eaec', border: isDark ? '#5c282e' : '#e2b3b7', text: isDark ? '#ffd1d6' : '#5c1b22' }},
        {{ keywords: ['marina', 'marinas', 'agua', 'océano', 'mar', 'ozónica', 'ozónicas', 'acuática'], 
          bg: isDark ? '#152933' : '#eaf2f7', border: isDark ? '#224052' : '#a8c7da', text: isDark ? '#c2eeea' : '#173a4b' }},
        {{ keywords: ['albahaca', 'bergamota', 'cardamomo', 'higo', 'manzana', 'menta', 'pachulí', 'pera', 'romero', 'salvia', 'té verde', 'té blanco', 'vetiver', 'abedul', 'eucalipto', 'gálbano', 'hojas de violeta', 'verde'], 
          bg: isDark ? '#162b1e' : '#ebf5ee', border: isDark ? '#234530' : '#a4cca2', text: isDark ? '#b8f5c8' : '#193d25' }},
        {{ keywords: ['iris', 'lavanda', 'jazmín', 'nardos', 'neroli', 'violeta', 'fresia', 'heliotropo', 'mimosa', 'lila', 'magnolia', 'azahar', 'frangipani', 'gardenia', 'ylang', 'floral'], 
          bg: isDark ? '#2b1d33' : '#f2ebf7', border: isDark ? '#432d52' : '#c3b1d4', text: isDark ? '#e7cdfa' : '#391c47' }},
        {{ keywords: ['caramelo', 'miel', 'solares', 'vainilla', 'cacao', 'café', 'canela', 'tonka', 'nuez moscada', 'praliné', 'haba tonka', 'almendra', 'avellana', 'leche', 'malvavisco', 'chocolate', 'ron', 'cognac', 'whisky', 'gourmand'], 
          bg: isDark ? '#332115' : '#f7ede6', border: isDark ? '#523522' : '#d8bca7', text: isDark ? '#f7d3b7' : '#452914' }},
        {{ keywords: ['ámbar gris', 'cedro', 'sándalo', 'tabaco', 'cuero', 'oud', 'incienso', 'ciprés', 'ébano', 'guayac', 'musgo', 'estoraque', 'ládano', 'benjuí'], 
          bg: isDark ? '#23272e' : '#edeef0', border: isDark ? '#373d47' : '#bdc1c9', text: isDark ? '#e1e7f2' : '#292e36' }},
        {{ keywords: ['azafrán', 'ámbar', 'mandarina', 'melocotón', 'durazno', 'mirra', 'naranjo', 'pomelo', 'cítrico', 'cítricos', 'limón', 'lima', 'clementina', 'yuzu', 'petit grain', 'piña', 'jengibre'], 
          bg: isDark ? '#382013' : '#f9ede6', border: isDark ? '#59331e' : '#debca8', text: isDark ? '#ffd8be' : '#4f2711' }}
    ];

    function applyEssenceColorsAndEvents() {{
        const targets = doc.querySelectorAll('span[data-baseweb="tag"]');
        targets.forEach(el => {{
            if (el.dataset.colored === 'true') return;
            const text = (el.innerText || '').toLowerCase();
            if (!text) return;

            for (const rule of colorRules) {{
                if (rule.keywords.some(kw => text.includes(kw))) {{
                    el.style.backgroundColor = rule.bg;
                    el.style.border = '1px solid ' + rule.border;
                    el.style.color = rule.text; 
                    el.style.borderRadius = '6px';
                    el.style.padding = '3px 8px';
                    el.style.fontSize = '0.76rem';
                    el.style.fontWeight = '500';
                    el.dataset.colored = 'true';
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
