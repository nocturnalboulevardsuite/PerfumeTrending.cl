"""
Paquete compartido de interfaz, seguridad, tema y autenticación de PerfumeTrending.cl.
"""

from .security import (
    DEFAULT_AVATAR_SVG,
    DEFAULT_PERFUME_IMAGE,
    clean_html,
    escape_html,
    get_image_src,
    is_valid_https_image_url,
    resolver_url_oferta,
    sanitize_external_url,
)
from .theme import (
    DIAMOND_ICON_SVG,
    FLAME_RED_SVG,
    GRID_ICON_SVG,
    HOME_RED_SVG,
    PERFUME_SVG_FAVICON,
    SHIELD_RED_SVG,
    TAG_RED_SVG,
    TREND_RED_SVG,
    ThemePalette,
    get_theme_palette,
    init_common_session_state,
    toggle_theme,
)
from .auth_modal import (
    cerrar_sesion_usuario,
    hidratar_sesion_usuario,
    modal_autenticacion,
)

__all__ = [
    "DEFAULT_AVATAR_SVG",
    "DEFAULT_PERFUME_IMAGE",
    "DIAMOND_ICON_SVG",
    "FLAME_RED_SVG",
    "GRID_ICON_SVG",
    "HOME_RED_SVG",
    "PERFUME_SVG_FAVICON",
    "SHIELD_RED_SVG",
    "TAG_RED_SVG",
    "TREND_RED_SVG",
    "ThemePalette",
    "cerrar_sesion_usuario",
    "clean_html",
    "escape_html",
    "get_image_src",
    "get_theme_palette",
    "hidratar_sesion_usuario",
    "init_common_session_state",
    "is_valid_https_image_url",
    "modal_autenticacion",
    "resolver_url_oferta",
    "sanitize_external_url",
    "toggle_theme",
]

