"""
PerfumeTrending.cl — Acciones compartidas sobre perfumes
========================================================
- `boton_abrir_perfume`: hace que toda la tarjeta de un perfume sea cliqueable y lleve
  a su comparativa de precios (conservando la sesión, sin recargar la app).
- `boton_corazon`: corazón sobre el perfume para guardarlo o quitarlo de los favoritos
  del perfil. Si no hay sesión, abre el ingreso y guarda el favorito apenas se inicie sesión.
- `estilos_tarjetas_cliqueables`: CSS común para ambos elementos.
- `mostrar_aviso_favoritos`: muestra el aviso (toast) pendiente tras guardar o quitar.

Las tarjetas se envuelven así:

    with st.container(key=f"pcard_<contexto>_<id>"):
        st.markdown(tarjeta_html, unsafe_allow_html=True)
        boton_abrir_perfume(pid, "<contexto>")
        boton_corazon(pid, "<contexto>", nombre)
"""

import streamlit as st

from backend.database import (
    agregar_favorito,
    eliminar_favorito,
    obtener_favoritos_Ids_usuario,
)


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
            try:
                st.query_params["id"] = str(pid)
            except Exception:
                pass
            st.rerun()
        else:
            st.switch_page("pages/compararprecios.py")


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
    </style>
    """
