# 4. CABECERA Y LOGO CORREGIDOS
col_logo, col_theme = st.columns([6, 1], vertical_alignment="center")

with col_logo:
    logo_color = "#8c7b6d"
    # Se cambia href="app.py" por href="/" para evitar la alerta "Page not found"
    logo_html = f"""
    <a href="/" target="_self" style="text-decoration: none; display: flex; align-items: center; gap: 10px; cursor: pointer;">
        <svg width="34" height="34" viewBox="0 0 36 36" fill="none">
            <path d="M 6.8 21 L 29.2 21 C 30 25 27 32 18 32 C 9 32 6 25 6.8 21 Z" fill="{logo_color}" />
            <line x1="6.8" y1="21" x2="29.2" y2="21" stroke="{text_color}" stroke-width="2" />
            <rect x="13" y="3" width="10" height="4" rx="1" stroke="{text_color}" stroke-width="2.5" />
        </svg>
        <span style="font-family: 'Inter', sans-serif; font-size: 1.4rem; color: {text_color};">
            <span style="font-weight: 800;">Perfume</span><span style="font-weight: 400;">Trending</span>
        </span>
    </a>
    """
    st.markdown(logo_html, unsafe_allow_html=True)

with col_theme:
    st.button(" ", key="theme_toggle", on_click=toggle_theme)

# SECCIÓN DE TÍTULO Y NAVEGACIÓN
col_header_title, col_back_btn = st.columns([3.4, 1], vertical_alignment="center")

with col_header_title:
    title_html = f"""
    <div class="radar-title-container">
        <h1 class="radar-title-text">RADAR DEL HYPE - VIRAL FRAGRANCES</h1>
        <div class="info-icon-container">
            <div class="info-btn-badge">i</div>
            <div class="info-tooltip-box">
                <div style="font-weight: 800; color: #d83737; margin-bottom: 4px;">📡 ¿Qué es el Radar del Hype?</div>
                Mide las fragancias más virales en tiempo real según menciones y reproducciones en <b>YouTube</b>.
            </div>
        </div>
    </div>
    """
    st.markdown(title_html, unsafe_allow_html=True)

with col_back_btn:
    # Se actualiza también el enlace de volver a la raíz
    st.markdown('<a href="/" target="_self" class="nav-back-link">← Volver al Catálogo principal</a>', unsafe_allow_html=True)
