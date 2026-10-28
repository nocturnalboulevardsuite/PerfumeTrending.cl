"""
PerfumeTrending.cl — Sistema Unificado de Tema, Iconografía SVG y Estado Base
==============================================================================
Elimina la duplicación de ~1.500 líneas de SVGs, variables cromáticas y CSS de
cabecera/popover/switch entre las 6 páginas del portal manteniendo 100% de fidelidad visual.
"""

from dataclasses import dataclass
import streamlit as st


PERFUME_SVG_FAVICON = (
    "data:image/svg+xml;utf8,"
    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 36 36' fill='none'>"
    "<path d='M 7 21 A 11 11 0 0 0 29 21 Z' fill='%238c7b6d'/>"
    "<circle cx='18' cy='21' r='11' stroke='%23ffffff' stroke-width='2.2'/>"
    "<line x1='18' y1='10' x2='18' y2='32' stroke='%23ffffff' stroke-width='2'/>"
    "<line x1='7' y1='21' x2='29' y2='21' stroke='%23ffffff' stroke-width='2'/>"
    "<rect x='15' y='7' width='6' height='3' fill='%2314171d' stroke='%23ffffff' stroke-width='2'/>"
    "<rect x='13' y='2' width='10' height='5' rx='1.5' fill='%238c7b6d' stroke='%23ffffff' stroke-width='2'/>"
    "</svg>"
)

TREND_RED_SVG = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23d83737' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><polyline points='23 6 13.5 15.5 8.5 10.5 1 18'/><polyline points='17 6 23 6 23 12'/></svg>"
SHIELD_RED_SVG = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23d83737' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z'/><polyline points='9 12 11 14 15 10'/></svg>"
TAG_RED_SVG = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23d83737' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z'/><circle cx='7' cy='7' r='1.5' fill='%23d83737'/></svg>"
HOME_RED_SVG = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23d83737' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z'/><polyline points='9 22 9 12 15 12 15 22'/></svg>"
FLAME_RED_SVG = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23d83737' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z'/></svg>"
GRID_ICON_SVG = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23d83737' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><rect x='3' y='3' width='7' height='7'/><rect x='14' y='3' width='7' height='7'/><rect x='14' y='14' width='7' height='7'/><rect x='3' y='14' width='7' height='7'/></svg>"
DIAMOND_ICON_SVG = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23d83737' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M6 3h12l4 6-10 12L2 9z'/></svg>"


@dataclass(frozen=True)
class ThemePalette:
    is_dark: bool
    app_bg: str
    app_bg_css: str
    card_bg: str
    border_color: str
    text_color: str
    subtext_color: str
    btn_bg: str
    btn_text: str
    btn_border: str
    input_bg: str
    input_text: str
    input_border: str
    bottle_left_pos: str
    static_icon_pos: str
    static_icon_svg: str
    bottle_svg: str
    user_icon_svg: str
    settings_icon_svg: str
    logout_icon_svg: str
    camera_icon_svg: str
    logo_svg_data: str


def init_common_session_state() -> None:
    """Inicializa el estado compartido de sesión para tema, autenticación y favoritos."""
    defaults = {
        "theme": "dark",
        "logged_in": False,
        "user_info": None,
        "show_login_modal": False,
        "show_visual_modal": False,
        "selected_perfume": None,
        "favoritos": [],
        "login_failed_attempts": 0,
        "login_lockout_until": 0.0,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = list(val) if isinstance(val, list) else val


def toggle_theme() -> None:
    """Alterna entre modo oscuro y modo claro cerrando modales abiertos."""
    cur = st.session_state.get("theme", "dark")
    st.session_state["theme"] = "dark" if cur == "light" else "light"
    st.session_state["show_login_modal"] = False
    st.session_state["show_visual_modal"] = False


def get_theme_palette(light_bg: str = "#f8f9fa") -> ThemePalette:
    """Construye la paleta cromática y SVGs dinámicos según el tema activo."""
    is_dark = st.session_state.get("theme", "dark") == "dark"
    app_bg = "#0c0e12" if is_dark else light_bg
    app_bg_css = "radial-gradient(ellipse at top, #181c24 0%, #0c0e12 75%)" if is_dark else app_bg
    card_bg = "#14171d" if is_dark else "#ffffff"
    border_color = "#2a2e39" if is_dark else "#e4e4e7"
    text_color = "#f0f0f0" if is_dark else "#18181b"
    subtext_color = "#888890" if is_dark else "#666670"

    btn_bg = "#181c24" if is_dark else "#ffffff"
    btn_text = "#ffffff" if is_dark else "#18181b"
    btn_border = "#2a2e39" if is_dark else "#d1d5db"

    input_bg = "#14171d" if is_dark else "#ffffff"
    input_text = "#f0f0f0" if is_dark else "#18181b"
    input_border = "#2a2e39" if is_dark else "#d1d5db"

    bottle_left_pos = "42px" if is_dark else "-2px"
    static_icon_pos = "12px center" if is_dark else "calc(100% - 12px) center"

    static_icon_svg = (
        "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23ffffff' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><circle cx='12' cy='12' r='4'/><line x1='12' y1='1' x2='12' y2='3'/><line x1='12' y1='21' x2='12' y2='23'/><line x1='4.22' y1='4.22' x2='5.64' y2='5.64'/><line x1='18.36' y1='18.36' x2='19.78' y2='19.78'/><line x1='1' y1='12' x2='3' y2='12'/><line x1='21' y1='12' x2='23' y2='12'/><line x1='4.22' y1='19.78' x2='5.64' y2='18.36'/><line x1='18.36' y1='5.64' x2='19.78' y2='4.22'/></svg>"
        if is_dark
        else "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23ffffff' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M21 12.79A9 9 0 0 1 11.21 3 7 7 0 0 0 21 12.79z'/></svg>"
    )

    bottle_svg = (
        "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 50 58'><rect x='18' y='2' width='14' height='7' rx='2' fill='%23ffffff' stroke='%23111111' stroke-width='2.5'/><rect x='21' y='9' width='8' height='5' fill='%23ffffff' stroke='%23111111' stroke-width='2.5'/><circle cx='25' cy='34' r='19' fill='%23ffffff' stroke='%23111111' stroke-width='2.5'/><path d='M21 28a8 8 0 0 0 9 10.5 8.5 8.5 0 0 1-9-10.5z' fill='none' stroke='%23111111' stroke-width='2.2' stroke-linecap='round' stroke-linejoin='round'/></svg>"
        if is_dark
        else "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 50 58'><rect x='18' y='2' width='14' height='7' rx='2' fill='%23ffffff' stroke='%23111111' stroke-width='2.5'/><rect x='21' y='9' width='8' height='5' fill='%23ffffff' stroke='%23111111' stroke-width='2.5'/><circle cx='25' cy='34' r='19' fill='%23ffffff' stroke='%23111111' stroke-width='2.5'/><circle cx='25' cy='34' r='5' fill='none' stroke='%23111111' stroke-width='2'/><line x1='25' y1='23' x2='25' y2='26' stroke='%23111111' stroke-width='2' stroke-linecap='round'/><line x1='25' y1='42' x2='25' y2='45' stroke='%23111111' stroke-width='2' stroke-linecap='round'/><line x1='14' y1='34' x2='17' y2='34' stroke='%23111111' stroke-width='2' stroke-linecap='round'/><line x1='33' y1='34' x2='36' y2='34' stroke='%23111111' stroke-width='2' stroke-linecap='round'/><line x1='17' y1='26' x2='19' y2='28' stroke='%23111111' stroke-width='2' stroke-linecap='round'/><line x1='31' y1='40' x2='33' y2='42' stroke='%23111111' stroke-width='2' stroke-linecap='round'/><line x1='17' y1='42' x2='19' y2='40' stroke='%23111111' stroke-width='2' stroke-linecap='round'/><line x1='31' y1='28' x2='33' y2='26' stroke='%23111111' stroke-width='2' stroke-linecap='round'/></svg>"
    )

    stroke_hex = btn_text[1:]
    user_icon_svg = f"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23{stroke_hex}' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2'/><circle cx='12' cy='7' r='4'/></svg>"
    settings_icon_svg = f"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23{stroke_hex}' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.38a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z'/><circle cx='12' cy='12' r='3'/></svg>"
    logout_icon_svg = f"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23{stroke_hex}' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4'/><polyline points='16 17 21 12 16 7'/><line x1='21' y1='12' x2='9' y2='12'/></svg>"
    camera_icon_svg = f"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23{stroke_hex}' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z'/><circle cx='12' cy='13' r='4'/></svg>"

    text_color_encoded = "%23ffffff" if is_dark else "%2318181b"
    logo_svg_data = f"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 36 36' fill='none' stroke-linecap='round' stroke-linejoin='round'><path d='M 6.8 21 L 29.2 21 C 30 25 27 32 18 32 C 9 32 6 25 6.8 21 Z' fill='%238c7b6d' /><line x1='6.8' y1='21' x2='29.2' y2='21' stroke='{text_color_encoded}' stroke-width='1.5' /><line x1='18' y1='10' x2='18' y2='30' stroke='{text_color_encoded}' stroke-width='1' /><path d='M 18 32 C 9 32 5 24 7.5 17 C 9 12 13 10 15 10 L 21 10 C 23 10 27 12 28.5 17 C 31 24 27 32 18 32 Z' stroke='{text_color_encoded}' stroke-width='2' /><rect x='15' y='7' width='6' height='3' stroke='{text_color_encoded}' stroke-width='1.5' /><rect x='13' y='3' width='10' height='4' rx='1' stroke='{text_color_encoded}' stroke-width='1.5' /><rect x='16' y='0' width='4' height='3' rx='1' fill='%238c7b6d' stroke='{text_color_encoded}' stroke-width='1' /></svg>"

    return ThemePalette(
        is_dark=is_dark,
        app_bg=app_bg,
        app_bg_css=app_bg_css,
        card_bg=card_bg,
        border_color=border_color,
        text_color=text_color,
        subtext_color=subtext_color,
        btn_bg=btn_bg,
        btn_text=btn_text,
        btn_border=btn_border,
        input_bg=input_bg,
        input_text=input_text,
        input_border=input_border,
        bottle_left_pos=bottle_left_pos,
        static_icon_pos=static_icon_pos,
        static_icon_svg=static_icon_svg,
        bottle_svg=bottle_svg,
        user_icon_svg=user_icon_svg,
        settings_icon_svg=settings_icon_svg,
        logout_icon_svg=logout_icon_svg,
        camera_icon_svg=camera_icon_svg,
        logo_svg_data=logo_svg_data,
    )
