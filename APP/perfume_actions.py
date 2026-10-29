"""
PerfumeTrending.cl — Acciones compartidas sobre perfumes
========================================================
- `boton_abrir_perfume`: hace que toda la tarjeta de un perfume sea cliqueable y lleve
  a su comparativa de precios (conservando la sesión, sin recargar la app).
- `boton_corazon`: corazón sobre el perfume para guardarlo o quitarlo de los favoritos
  del perfil. Si no hay sesión, abre el ingreso y guarda el favorito apenas se inicie sesión.
- `estilos_tarjetas_cliqueables`: CSS común para ambos elementos.
- `mostrar_aviso_favoritos`: muestra el aviso (toast) pendiente tras guardar o quitar.
- `estilos_avatar_usuario`: muestra la foto de perfil en un círculo dentro del botón
  con el nombre del usuario en la cabecera de todas las páginas.

Las tarjetas se envuelven así:

    with st.container(key=f"pcard_<contexto>_<id>"):
        st.markdown(tarjeta_html, unsafe_allow_html=True)
        boton_abrir_perfume(pid, "<contexto>")
        boton_corazon(pid, "<contexto>", nombre)
"""

import streamlit as st
import streamlit.components.v1 as components

from backend.database import (
    agregar_favorito,
    eliminar_favorito,
    obtener_favoritos_Ids_usuario,
)

try:
    from backend.database import obtener_perfil_usuario
except Exception:  # pragma: no cover
    obtener_perfil_usuario = None

try:
    from ui import get_image_src
except Exception:  # pragma: no cover
    get_image_src = None

try:
    from ui import FLAME_RED_SVG as _flame_red_svg
except Exception:  # pragma: no cover
    _flame_red_svg = ""


def _ident_usuario():
    if not st.session_state.get("logged_in"):
        return None
    info = st.session_state.get("user_info") or {}
    return info.get("id") or info.get("email")


def favoritos_ids() -> set:
    """IDs de perfumes favoritos del usuario (se cargan una vez por sesión y usuario)."""
    ident = _ident_usuario()
    if not ident:
        return set()
    if st.session_state.get("_favoritos_cargados_para") != str(ident):
        try:
            email = (st.session_state.get("user_info") or {}).get("email")
            ids = obtener_favoritos_Ids_usuario(ident, email=email) or []
            st.session_state["favoritos"] = [int(x) for x in ids if str(x).isdigit()]
        except Exception:
            st.session_state.setdefault("favoritos", [])
        st.session_state["_favoritos_cargados_para"] = str(ident)
    return {int(x) for x in (st.session_state.get("favoritos") or []) if str(x).isdigit()}


def _toggle_favorito(pid: int, nombre: str = "", recargar_pagina: bool = True):
    """Callback del corazón: guarda o quita el perfume de favoritos."""
    pid = int(pid)
    ident = _ident_usuario()
    if not ident:
        st.session_state["_fav_pendiente"] = pid
        st.session_state["show_login_modal"] = True
        st.session_state["_fav_aviso"] = ("Ingresa con tu correo para guardar tus fragancias favoritas.", "🔐")
        # Siempre se recarga la página completa para que se abra el ingreso,
        # incluso si el corazón estaba dentro de un fragmento o ventana.
        st.session_state["_fav_recargar_app"] = True
        return
    if recargar_pagina:
        st.session_state["_fav_recargar_app"] = True

    actuales = favoritos_ids()
    etiqueta = f" {nombre}" if nombre else ""
    try:
        if pid in actuales:
            eliminar_favorito(ident, pid)
            actuales.discard(pid)
            st.session_state["_fav_aviso"] = (f"Quitaste{etiqueta} de tus favoritos.", "🤍")
        else:
            agregar_favorito(ident, pid)
            actuales.add(pid)
            st.session_state["_fav_aviso"] = (f"Guardaste{etiqueta} en tus favoritos.", "❤️")
        st.session_state["favoritos"] = sorted(actuales)
    except Exception:
        st.session_state["_fav_aviso"] = ("No pudimos actualizar tus favoritos. Inténtalo de nuevo.", "⚠️")


def boton_corazon(pid, contexto: str, nombre: str = "", en_linea: bool = False, recargar_pagina: bool = True):
    """Corazón para guardar/quitar favorito. Por defecto flota sobre la tarjeta (arriba a la derecha).

    `recargar_pagina=False` sirve dentro de ventanas emergentes para no cerrarlas al marcar el corazón.
    """
    # Si un corazón se tocó dentro de un fragmento (p. ej. el catálogo paginado), se recarga
    # la página completa para actualizar todos los corazones, el aviso y abrir el ingreso si hace falta.
    if st.session_state.pop("_fav_recargar_app", False):
        st.rerun()
    pid = int(pid)
    es_fav = pid in favoritos_ids()
    prefijo = "favline" if en_linea else "favbtn"
    estado = "on" if es_fav else "off"
    st.button(
        "♥" if es_fav else "♡",
        key=f"{prefijo}_{estado}_{contexto}_{pid}",
        on_click=_toggle_favorito,
        args=(pid, nombre, recargar_pagina),
        help="Quitar de favoritos" if es_fav else "Guardar en favoritos",
    )


def boton_abrir_perfume(pid, contexto: str, misma_pagina: bool = False):
    """Capa invisible que cubre la tarjeta: al hacer clic abre la comparativa del perfume."""
    pid = int(pid)
    if st.button("Ver perfume", key=f"open_{contexto}_{pid}"):
        st.session_state["selected_perfume"] = pid
        if misma_pagina:
            # No se escribe en st.query_params (crearía entradas extra en el historial del navegador);
            # el comparador actualiza la dirección con sincronizar_id_en_url().
            st.rerun()
        else:
            st.switch_page("pages/compararprecios.py")


def sincronizar_id_en_url(pid):
    """Pone ?id=<pid> en la dirección del navegador REEMPLAZANDO la entrada actual del historial.

    `st.query_params[...] = ...` agrega una entrada nueva cada vez y eso hacía que el botón
    "Atrás" pareciera no funcionar (había que pulsarlo dos veces). Aquí se usa replaceState.
    """
    pid = str(pid)
    st.session_state["_cp_id_en_url"] = pid
    script = f"""
    <script>
    (function() {{
        try {{
            const w = window.parent || window;
            const url = new URL(w.location.href);
            if (url.searchParams.get("id") !== "{pid}") {{
                url.searchParams.set("id", "{pid}");
                w.history.replaceState(w.history.state, "", url.toString());
            }}
        }} catch (e) {{}}
    }})();
    </script>
    """
    try:
        st.html(script, unsafe_allow_javascript=True)
    except Exception:
        components.html(script, height=0, width=0)


def mostrar_aviso_favoritos():
    """Se llama al inicio de cada página (ejecución completa): muestra el aviso pendiente."""
    # Esta ejecución ya es completa, así que no hace falta recargar otra vez.
    st.session_state.pop("_fav_recargar_app", None)
    aviso = st.session_state.pop("_fav_aviso", None)
    if aviso:
        texto, icono = aviso
        try:
            st.toast(texto, icon=icono)
        except Exception:
            st.toast(texto)


def estilos_tarjetas_cliqueables(accent: str, card_bg: str, border_color: str, subtext_color: str, is_dark: bool) -> str:
    fondo_corazon = "rgba(17, 20, 26, 0.78)" if is_dark else "rgba(255, 255, 255, 0.92)"
    return f"""
    <style>
    /* Tarjeta de perfume cliqueable */
    div[class*="st-key-pcard_"] {{
        position: relative !important;
        gap: 0 !important;
    }}
    div[class*="st-key-open_"] {{
        position: absolute !important;
        inset: 0 !important;
        width: 100% !important;
        height: 100% !important;
        margin: 0 !important;
        z-index: 3 !important;
    }}
    div[class*="st-key-open_"] div.stButton,
    div[class*="st-key-open_"] div[data-testid="stButton"],
    div[class*="st-key-open_"] button {{
        width: 100% !important;
        height: 100% !important;
        min-height: 100% !important;
        margin: 0 !important;
        padding: 0 !important;
        opacity: 0 !important;
        cursor: pointer !important;
    }}
    div[class*="st-key-pcard_"]:has(div[class*="st-key-open_"] button:focus-visible) {{
        outline: 2px solid {accent} !important;
        outline-offset: 3px !important;
        border-radius: 16px !important;
    }}

    /* Corazón de favoritos sobre el perfume */
    div[class*="st-key-favbtn_"] {{
        position: absolute !important;
        top: var(--heart-top, 12px) !important;
        right: var(--heart-right, 12px) !important;
        width: auto !important;
        margin: 0 !important;
        z-index: 6 !important;
    }}
    div[class*="st-key-favbtn_"] button,
    div[class*="st-key-favline_"] button {{
        width: 38px !important;
        height: 38px !important;
        min-height: 38px !important;
        min-width: 38px !important;
        padding: 0 !important;
        border-radius: 50% !important;
        background-color: {fondo_corazon} !important;
        border: 1px solid {border_color} !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, {0.35 if is_dark else 0.10}) !important;
        backdrop-filter: blur(6px) !important;
        -webkit-backdrop-filter: blur(6px) !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        transition: transform 0.15s ease, border-color 0.15s ease !important;
    }}
    div[class*="st-key-favbtn_"] button:hover,
    div[class*="st-key-favline_"] button:hover {{
        transform: scale(1.08) !important;
        border-color: {accent} !important;
    }}
    div[class*="st-key-favbtn_"] button:active,
    div[class*="st-key-favline_"] button:active {{ transform: scale(0.94) !important; }}
    div[class*="st-key-favbtn_"] button p,
    div[class*="st-key-favline_"] button p {{
        font-size: 1.15rem !important;
        line-height: 1 !important;
        margin: 0 !important;
        font-weight: 400 !important;
        color: {subtext_color} !important;
    }}
    div[class*="st-key-favbtn_on_"] button p,
    div[class*="st-key-favline_on_"] button p {{ color: {accent} !important; }}
    div[class*="st-key-favbtn_on_"] button,
    div[class*="st-key-favline_on_"] button {{ border-color: {accent} !important; }}

    /* Acceso rápido "Remates & Flash" con su ícono de llama */
    a[data-testid="stPageLink-NavLink"][href*="remates"] {{
        position: relative !important;
        padding-left: 2.6rem !important;
        padding-right: 1.1rem !important;
        overflow: hidden !important;
    }}
    a[data-testid="stPageLink-NavLink"][href*="remates"]::before {{
        content: '' !important;
        position: absolute !important;
        left: 15px !important;
        top: 50% !important;
        transform: translateY(-50%) !important;
        width: 16px !important;
        height: 16px !important;
        background-image: url("{_flame_red_svg}") !important;
        background-repeat: no-repeat !important;
        background-size: contain !important;
        background-position: center !important;
        z-index: 1 !important;
    }}

    /* Botón del usuario: el nombre no choca con la flecha del menú */
    html body div[data-testid="stHorizontalBlock"]:has(.st-key-theme_toggle) div[data-testid="stColumn"] button[data-testid="stPopoverButton"] {{
        padding-right: 1rem !important;
    }}
    html body div[data-testid="stHorizontalBlock"]:has(.st-key-theme_toggle) div[data-testid="stColumn"] button[data-testid="stPopoverButton"] p {{
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }}
    </style>
    """ + estilos_avatar_usuario("#d4c2a5" if is_dark else "#8c7b6d")


# -----------------------------------------------------------------------------
# Foto de perfil en el botón del usuario (cabecera)
# -----------------------------------------------------------------------------
def _foto_perfil_usuario() -> str:
    """URL segura de la foto de perfil del usuario conectado, o "" si no tiene."""
    if not st.session_state.get("logged_in"):
        return ""
    info = st.session_state.get("user_info") or {}
    foto = str(info.get("foto_perfil") or "").strip()

    # Si la sesión aún no trae la foto (p. ej. recién ingresó desde el Inicio), se consulta una vez.
    if not foto and not st.session_state.get("_avatar_sync_intentado") and obtener_perfil_usuario:
        st.session_state["_avatar_sync_intentado"] = True
        ident = info.get("id") or info.get("email")
        if ident:
            try:
                perfil = obtener_perfil_usuario(ident) or {}
                foto = str(perfil.get("foto_perfil") or "").strip()
                if foto:
                    st.session_state["user_info"]["foto_perfil"] = foto
            except Exception:
                foto = ""
    if not foto:
        return ""

    src = ""
    if get_image_src:
        try:
            # Nunca se leen rutas locales del servidor desde el avatar (misma regla que en el perfil)
            src = get_image_src(foto, allow_local=False, default_src="") or ""
        except TypeError:
            src = ""
        except Exception:
            src = ""
    if not src and (foto.startswith("https://") or foto.startswith("data:image/")):
        src = foto
    if not (src.startswith("https://") or src.startswith("data:image/")):
        return ""
    # Escapes mínimos para usarla dentro de url("...") en CSS
    return src.replace("\\", "%5C").replace('"', "%22").replace("\n", "").replace("\r", "")


def estilos_avatar_usuario(borde: str = "#8c7b6d") -> str:
    """CSS que reemplaza el ícono genérico del botón de usuario por su foto en un círculo."""
    base = """
    <style>
    html body div[data-testid="stHorizontalBlock"]:has(.st-key-theme_toggle) div[data-testid="stColumn"] button[data-testid="stPopoverButton"] {
        padding-right: 1rem !important;
    }
    </style>
    """
    src = _foto_perfil_usuario()
    if not src:
        return base if st.session_state.get("logged_in") else ""
    return base + f"""
    <style>
    html body div[data-testid="stHorizontalBlock"]:has(.st-key-theme_toggle) div[data-testid="stColumn"] button[data-testid="stPopoverButton"] {{
        position: relative !important;
        background-image: none !important;
        padding-left: 3rem !important;
    }}
    html body div[data-testid="stHorizontalBlock"]:has(.st-key-theme_toggle) div[data-testid="stColumn"] button[data-testid="stPopoverButton"]::before {{
        content: "" !important;
        position: absolute !important;
        left: 8px !important;
        top: 50% !important;
        transform: translateY(-50%) !important;
        width: 28px !important;
        height: 28px !important;
        border-radius: 50% !important;
        background-image: url("{src}") !important;
        background-size: cover !important;
        background-position: center !important;
        background-repeat: no-repeat !important;
        box-shadow: 0 0 0 2px {borde} !important;
    }}
    </style>
    """


# -----------------------------------------------------------------------------
# Ajustes para celulares (se aplican en todas las páginas)
# -----------------------------------------------------------------------------
def estilos_moviles(accent: str = "#d83737", border_color: str = "#e6e1db", is_dark: bool = True) -> str:
    """CSS responsivo común: cabecera ordenada, textos sin encimarse y tarjetas cómodas en celular."""
    fila_riesgo = "rgba(239, 68, 68, 0.06)" if is_dark else "rgba(239, 68, 68, 0.04)"
    return f"""
    <style>
    @media (max-width: 768px) {{
        /* En celular la pantalla se usa al 100 % (el zoom de escritorio encimaba textos) */
        html body .block-container {{
            zoom: 1 !important;
            padding: 0.6rem 0.95rem 1.6rem 0.95rem !important;
        }}
        html body .stMarkdown p, html body .stMarkdown li {{ line-height: 1.5 !important; }}

        /* ---- Cabecera: logo arriba; botón de usuario/Ingresar y switch en la fila de abajo ---- */
        html body div[data-testid="stHorizontalBlock"]:has(.brand-logo-clean) {{
            flex-wrap: wrap !important;
            row-gap: 10px !important;
            column-gap: 0 !important;
        }}
        html body div[data-testid="stHorizontalBlock"]:has(.brand-logo-clean) > div[data-testid="stColumn"] {{
            flex: 1 1 100% !important;
            width: 100% !important;
            min-width: 0 !important;
        }}
        html body div[data-testid="stHorizontalBlock"]:has(.brand-logo-clean) > div[data-testid="stColumn"]:nth-child(2) {{
            display: none !important;
        }}
        html body div[data-testid="stHorizontalBlock"]:has(.st-key-theme_toggle):not(:has(.brand-logo-clean)) {{
            flex-wrap: nowrap !important;
            align-items: center !important;
            justify-content: flex-end !important;
            gap: 10px !important;
        }}
        html body div[data-testid="stHorizontalBlock"]:has(.st-key-theme_toggle):not(:has(.brand-logo-clean)) > div[data-testid="stColumn"]:first-child {{
            flex: 1 1 auto !important;
            width: auto !important;
            min-width: 0 !important;
        }}
        html body div[data-testid="stHorizontalBlock"]:has(.st-key-theme_toggle):not(:has(.brand-logo-clean)) > div[data-testid="stColumn"]:last-child {{
            flex: 0 0 auto !important;
            width: auto !important;
        }}
        html body .brand-logo-text {{ font-size: 1.4rem !important; white-space: nowrap !important; }}
        html body a.brand-logo-clean svg {{ width: 30px !important; height: 30px !important; }}
        html body div[data-testid="stHorizontalBlock"]:has(.st-key-theme_toggle) button[data-testid="stPopoverButton"] {{
            min-height: 40px !important;
        }}
        html body div[data-testid="stHorizontalBlock"]:has(.st-key-theme_toggle) button[data-testid="stPopoverButton"] p {{
            font-size: 0.9rem !important;
        }}

        /* ---- Accesos rápidos: 2 por fila, texto centrado y legible ---- */
        html body div[data-testid="stHorizontalBlock"]:has(a[data-testid="stPageLink-NavLink"][href*="trustpage"]) {{
            flex-wrap: wrap !important;
            gap: 8px !important;
        }}
        html body div[data-testid="stHorizontalBlock"]:has(a[data-testid="stPageLink-NavLink"][href*="trustpage"]) > div[data-testid="stColumn"] {{
            flex: 1 1 calc(50% - 4px) !important;
            width: calc(50% - 4px) !important;
            min-width: 0 !important;
        }}
        html body a[data-testid="stPageLink-NavLink"],
        html body div.st-key-chip_home div.stButton > button,
        html body div.st-key-chip_remates div.stButton > button {{
            justify-content: center !important;
            min-height: 42px !important;
            padding: 0.4rem 0.6rem 0.4rem 2.1rem !important;
        }}
        html body a[data-testid="stPageLink-NavLink"] p,
        html body a[data-testid="stPageLink-NavLink"] span,
        html body div.st-key-chip_home div.stButton > button p,
        html body div.st-key-chip_remates div.stButton > button p {{
            font-size: 0.82rem !important;
            line-height: 1.2 !important;
            white-space: normal !important;
            text-align: center !important;
        }}

        /* ---- Títulos de sección y botón "Volver al catálogo" ---- */
        html body .pt-display, html body .pt-title, html body .radar-title-text, html body .trust-head-title {{
            font-size: 1.65rem !important;
            line-height: 1.15 !important;
        }}
        html body .pt-lede, html body .radar-subtitle, html body .trust-head-sub {{
            font-size: 0.93rem !important;
            line-height: 1.55 !important;
            margin-bottom: 4px !important;
        }}
        html body div[data-testid="stColumn"]:has(> div > div > a[data-testid="stPageLink-NavLink"][href$="app.py"]:only-child),
        html body div[data-testid="stColumn"]:has(a[data-testid="stPageLink-NavLink"]):not(:has(a[href*="trustpage"])) {{
            margin-top: 12px !important;
        }}
        html body .info-tooltip-box {{ left: auto !important; right: -10px !important; width: min(300px, 85vw) !important; }}

        /* ---- Filtros, buscadores y selectores a todo el ancho ---- */
        html body div[data-testid="stTextInput"] input,
        html body div[data-testid="stSelectbox"] div,
        html body div[data-testid="stTextArea"] textarea {{ font-size: 16px !important; }} /* evita el zoom automático del iPhone */
        html body .filter-label-text {{ height: auto !important; margin-top: 4px !important; }}
        html body .social-select-box {{ gap: 6px 8px !important; }}

        /* ---- Tarjetas de perfume ---- */
        html body .square-img-box {{ max-height: 250px !important; }}
        html body .card-footer-info {{ padding: 12px 14px !important; }}
        html body .card-perfume-name, html body .remate-title, html body .perfume-title {{ font-size: 1.02rem !important; }}
        html body .img-wrapper {{ height: 170px !important; }}
        html body .remate-img-box {{ height: 180px !important; }}
        html body div[data-testid="stColumn"]:has(.catalog-card),
        html body div[data-testid="stColumn"]:has(.hype-card),
        html body div[data-testid="stColumn"]:has(.remate-card) {{ margin-bottom: 14px !important; }}
        html body .stats-row {{ flex-wrap: wrap !important; }}

        /* Recomendadas del comparador: 2 por fila */
        html body div[data-testid="stHorizontalBlock"]:has(.rel-card) {{
            flex-wrap: wrap !important;
            gap: 10px !important;
        }}
        html body div[data-testid="stColumn"]:has(.rel-card) {{
            flex: 1 1 calc(50% - 5px) !important;
            width: calc(50% - 5px) !important;
            min-width: 0 !important;
            margin-bottom: 8px !important;
        }}
        html body .rel-stage {{ height: 110px !important; }}
        html body .rel-name {{ font-size: 0.86rem !important; }}

        /* Ficha del perfume en el comparador */
        html body .perfume-header-stage {{ min-height: 180px !important; margin-bottom: 6px !important; }}
        html body .perfume-name {{ font-size: 1.45rem !important; }}
        html body .perfume-ref-row {{ gap: 8px !important; }}

        /* Ofertas: precio y botón en una fila bajo el nombre de la tienda */
        html body .price-card {{ flex-direction: column !important; align-items: stretch !important; gap: 12px !important; padding: 14px !important; }}
        html body .price-card-right {{ justify-content: space-between !important; }}
        html body .price-block {{ text-align: left !important; }}
        html body span.pt-price-ml {{ text-align: left !important; }}
        html body .offer-toolbar {{ flex-direction: column !important; align-items: flex-start !important; }}

        /* ---- Tabla de tiendas (Páginas de Confianza) convertida en tarjetas ---- */
        html body .trust-table-container {{ padding: 6px 10px !important; overflow: visible !important; }}
        html body table.trust-table {{ min-width: 0 !important; }}
        html body table.trust-table thead {{ display: none !important; }}
        html body table.trust-table, html body table.trust-table tbody {{ display: block !important; width: 100% !important; }}
        html body table.trust-table tbody tr {{
            display: grid !important;
            grid-template-columns: 34px 1fr auto;
            grid-template-areas:
                "num name name"
                "num score status"
                "num action action";
            gap: 8px 10px;
            padding: 14px 4px !important;
            border-bottom: 1px solid {border_color} !important;
        }}
        html body table.trust-table tbody tr:last-child {{ border-bottom: none !important; }}
        html body table.trust-table tbody tr.trust-row-risk {{ background: {fila_riesgo} !important; border-radius: 12px; }}
        html body table.trust-table td {{ display: block !important; padding: 0 !important; border: none !important; background: transparent !important; }}
        html body table.trust-table td:nth-child(1) {{ grid-area: num; padding-top: 3px !important; }}
        html body table.trust-table td:nth-child(2) {{ grid-area: name; }}
        html body table.trust-table td:nth-child(3) {{ grid-area: score; }}
        html body table.trust-table td:nth-child(4) {{ grid-area: status; align-self: center; }}
        html body table.trust-table td:nth-child(5) {{ grid-area: action; text-align: left !important; }}
        html body table.trust-table td:nth-child(5) a,
        html body table.trust-table td:nth-child(5) span {{ display: block !important; text-align: center !important; }}
        html body .product-card {{ margin-bottom: 18px !important; }}

        /* ---- Perfil ---- */
        html body .avatar-help {{ margin-bottom: 10px !important; }}
        html body .st-key-profile_card div[data-testid="stColumn"]:has(.profile-name) {{ margin-top: 14px !important; }}
        html body .profile-contact {{ flex-direction: column !important; align-items: center !important; gap: 4px !important; }}
        html body div[class*="st-key-fav_row_"] div[data-testid="stHorizontalBlock"] {{
            flex-wrap: wrap !important;
            gap: 10px !important;
            align-items: center !important;
        }}
        html body div[class*="st-key-fav_row_"] div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-child(1) {{
            flex: 0 0 44px !important; width: 44px !important;
        }}
        html body div[class*="st-key-fav_row_"] div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-child(2) {{
            flex: 1 1 calc(100% - 54px) !important; width: calc(100% - 54px) !important;
        }}
        html body div[class*="st-key-fav_row_"] div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-child(3) {{
            flex: 1 1 100% !important; width: 100% !important;
        }}
        html body div[class*="st-key-fav_row_"] div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-child(4),
        html body div[class*="st-key-fav_row_"] div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-child(5) {{
            flex: 1 1 calc(50% - 5px) !important; width: calc(50% - 5px) !important;
        }}
        html body div[data-testid="stTabs"] button[role="tab"] {{ margin-right: 10px !important; }}

        /* ---- Ventana de ingreso ---- */
        html body [role="dialog"] {{ width: calc(100vw - 24px) !important; max-width: 480px !important; }}

        /* ---- Corazón un poco más grande para el dedo ---- */
        html body div[class*="st-key-favbtn_"] button,
        html body div[class*="st-key-favline_"] button {{
            width: 40px !important; height: 40px !important; min-width: 40px !important; min-height: 40px !important;
        }}
        html body .pt-footer {{ margin-top: 28px !important; }}
    }}
    </style>
    """
