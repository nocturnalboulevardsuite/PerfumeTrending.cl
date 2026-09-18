import streamlit as st
import streamlit.components.v1 as components

# -----------------------------------------------------------------------------
# 1. GESTIÓN DEL TEMA Y ESTADOS
# -----------------------------------------------------------------------------
if "theme" not in st.session_state:
    st.session_state.theme = "light"

def toggle_theme():
    st.session_state.theme = "dark" if st.session_state.theme == "light" else "light"

is_dark = st.session_state.theme == "dark"

# -----------------------------------------------------------------------------
# 2. DEFINICIÓN DE PALETA Y SVGS DEL SWITCH Y DE ICONOS
# -----------------------------------------------------------------------------
btn_text = "#FAFAFA" if is_dark else "#111827"
bg_color = "#0E1117" if is_dark else "#FAFAFA"
card_bg = "#161B22" if is_dark else "#FFFFFF"
border_color = "#30363D" if is_dark else "#E5E7EB"
text_color = "#FAFAFA" if is_dark else "#111827"
subtext_color = "#9CA3AF" if is_dark else "#4B5563"
accent_color = "#2563EB" if is_dark else "#3B82F6"

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

# -----------------------------------------------------------------------------
# 3. ESTILOS CSS PROFESIONALES Y MINIMALISTAS
# -----------------------------------------------------------------------------
st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }}

    .stApp {{
        background-color: {bg_color};
        color: {text_color};
    }}

    /* Tarjetas de Sitios de Confianza */
    .trust-card {{
        background-color: {card_bg};
        border: 1px solid {border_color};
        border-radius: 14px;
        padding: 22px;
        margin-bottom: 16px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
        transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.2s ease, border-color 0.2s ease;
        cursor: pointer;
    }}

    .trust-card:hover {{
        transform: translateY(-2px);
        border-color: {accent_color};
        box-shadow: 0 12px 24px rgba(0, 0, 0, 0.08);
    }}

    .trust-card-header {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 8px;
    }}

    .trust-card h4 {{
        margin: 0;
        color: {text_color};
        font-size: 1.125rem;
        font-weight: 600;
        letter-spacing: -0.01em;
    }}

    .trust-card p {{
        margin: 6px 0;
        color: {subtext_color};
        font-size: 0.925rem;
        line-height: 1.5;
    }}

    .trust-card a {{
        color: {accent_color};
        text-decoration: none;
        font-weight: 500;
    }}

    .trust-card a:hover {{
        text-decoration: underline;
    }}

    .tag-container {{
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        margin-top: 12px;
    }}

    /* Rediseño del botón nativo de Streamlit para convertirse en el Switch SVG */
    div[data-testid="stColumn"]:nth-child(3) div[data-testid="stButton"] button {{
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
        box-shadow: inset 0 1px 3px rgba(0,0,0,0.1);
    }}

    div[data-testid="stColumn"]:nth-child(3) div[data-testid="stButton"] button:hover {{
        border-color: {accent_color};
    }}

    div[data-testid="stColumn"]:nth-child(3) div[data-testid="stButton"] button::after {{
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
        font-size: 1.1rem;
        transition: all 0.2s ease;
    }}

    .sound-btn:hover {{
        border-color: {accent_color};
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# -----------------------------------------------------------------------------
# 4. ENCABEZADO Y CONTROLES SUPERIORES
# -----------------------------------------------------------------------------
col_title, col_sound, col_toggle = st.columns([0.76, 0.09, 0.15])

with col_title:
    st.title("🛡️ Páginas de Confianza")
    st.caption("Directorio de sitios web verificados, comercios seguros y notas aromáticas.")

with col_sound:
    st.markdown('<div style="padding-top: 14px;"><button id="sound-toggle-btn" class="sound-btn" onclick="window.parent.toggleSoundMute()" title="Activar/Desactivar Sonido">🔊</button></div>', unsafe_allow_html=True)

with col_toggle:
    st.button("Tema", on_click=toggle_theme, key="theme_switch_btn")

st.divider()

# -----------------------------------------------------------------------------
# 5. FILTROS DE BÚSQUEDA
# -----------------------------------------------------------------------------
search_query = st.text_input("🔍 Buscar por nombre, dominio o palabra clave...", "")

cat_col, trust_col = st.columns(2)
with cat_col:
    category = st.selectbox("Categoría", ["Todas", "Finanzas", "Educación", "Tecnología", "Gobierno", "Perfumería & Esencias"])
with trust_col:
    min_rating = st.slider("Nivel de confianza mínimo", 1, 5, 4)

# -----------------------------------------------------------------------------
# 6. DATOS DE EJEMPLO Y RENDERIZADO
# -----------------------------------------------------------------------------
trusted_sites = [
    {
        "name": "Banco Nacional",
        "domain": "https://banconacional.example.com",
        "category": "Finanzas",
        "rating": 5,
        "description": "Entidad bancaria con cifrado SSL de grado militar y doble factor de autenticación.",
        "tags": ["Finanzas", "Oficial"]
    },
    {
        "name": "L'Essence Botanique",
        "domain": "https://essences.example.com",
        "category": "Perfumería & Esencias",
        "rating": 5,
        "description": "Atelier de alta perfumería especializado en acordes de bergamota, té verde, jazmín y vetiver.",
        "tags": ["bergamota", "té verde", "jazmín", "vetiver"]
    },
    {
        "name": "Maison Cerise",
        "domain": "https://maisoncerise.example.com",
        "category": "Perfumería & Esencias",
        "rating": 5,
        "description": "Fragancias exclusivas de nicho formuladas con cereza, rosa y pimienta rosa.",
        "tags": ["cereza", "rosa", "pimienta rosa"]
    },
    {
        "name": "Portal Educativo Abierto",
        "domain": "https://educacion.example.org",
        "category": "Educación",
        "rating": 4,
        "description": "Recursos académicos abiertos respaldados por universidades e instituciones internacionales.",
        "tags": ["Educación", "Open Source"]
    },
    {
        "name": "Amber & Oud Luxe",
        "domain": "https://amberoud.example.com",
        "category": "Perfumería & Esencias",
        "rating": 5,
        "description": "Elixires orientales infusionados con ámbar, cedro, sándalo, cacao y tonka.",
        "tags": ["ámbar", "cedro", "sándalo", "cacao", "tonka"]
    },
    {
        "name": "Servicios Ciudadanos",
        "domain": "https://gobierno.example.gob",
        "category": "Gobierno",
        "rating": 5,
        "description": "Plataforma centralizada para tramitación estatal con autenticación biométrica.",
        "tags": ["Gobierno", "Oficial"]
    }
]

# Filtrado dinámico
filtered_sites = [
    site for site in trusted_sites
    if (
        search_query.lower() in site["name"].lower()
        or search_query.lower() in site["domain"].lower()
        or any(search_query.lower() in tag.lower() for tag in site.get("tags", []))
    )
    and (category == "Todas" or site["category"] == category)
    and site["rating"] >= min_rating
]

# Renderizado con soporte para el Script JS (clase essence-card y atributo data-baseweb)
if filtered_sites:
    for site in filtered_sites:
        stars = "⭐" * site["rating"]
        tags_html = "".join([f'<span data-baseweb="tag">{tag}</span>' for tag in site.get("tags", [])])
        
        st.markdown(
            f"""
            <div class="trust-card essence-card">
                <div class="trust-card-header">
                    <h4>{site['name']}</h4>
                    <span style="font-size: 0.85rem; font-weight: 500; color: {subtext_color};">{stars} ({site['rating']}/5)</span>
                </div>
                <p><strong>URL:</strong> <a href="{site['domain']}" target="_blank">{site['domain']}</a></p>
                <p>{site['description']}</p>
                <div class="tag-container">{tags_html}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
else:
    st.info("No se encontraron páginas de confianza que coincidan con los filtros seleccionados.")

# -----------------------------------------------------------------------------
# 7. SCRIPT DE COLORES Y SISTEMA DE SONIDO INTEGRADO
# -----------------------------------------------------------------------------
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
                    el.style.borderRadius = '6px';
                    el.style.padding = '3px 8px';
                    el.style.margin = '2px 0';
                    el.style.fontSize = '0.78rem';
                    el.style.fontWeight = '500';
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
