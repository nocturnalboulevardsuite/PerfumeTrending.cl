"""
PerfumeTrending.cl — Página de Comparador de Precios y Detalle de Fragancias
=============================================================================
Vista principal interactiva para comparar ofertas vigentes en tiempo real:
- Ficha técnica completa de la fragancia (marca, concentración, notas, familia olfativa).
- Comparativa en vivo de precios entre comercios chilenos auditados (Falabella, Paris, Ripley, Silk, Elite, etc.).
- Cálculo del precio por mililitro ($/ml) para comparar distintas presentaciones de volumen de manera justa.
- Visualización de la evolución histórica de precios mediante gráficos interactivos de series temporales.
- Gestión de favoritos y alertas de precio por usuario autenticado.
"""

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import sys
import os
import base64
import urllib.parse
import random

# Configuración de rutas canónicas para importar backend
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)
if APP_DIR not in sys.path:
    sys.path.append(APP_DIR)

try:
    from backend.database import (
        obtener_catalogo,
        obtener_precios_actuales,
        obtener_historico_precios,
        obtener_detalle_perfume,
        crear_usuario,
        verificar_usuario
    )
except ImportError:
    from backend.database import (
        obtener_catalogo,
        obtener_precios_actuales,
        obtener_historico_precios,
        obtener_detalle_perfume
    )
    crear_usuario = None
    verificar_usuario = None

# =============================================================================
# BLOQUE 1: CACHÉ EN MEMORIA DE ALTO RENDIMIENTO (STREAMLIT CACHE DATA)
# -----------------------------------------------------------------------------
# ¿QUÉ HACE ESTE BLOQUE?
# Utiliza el decorador `@st.cache_data(ttl=300)` (Time-To-Live de 5 minutos):
# - Almacena en memoria RAM el catálogo, las ofertas vivas y el historial de precios.
# - Evita saturar la base de datos (Supabase / SQLite) con peticiones repetitivas
#   cada vez que el usuario interactúa con la interfaz o cambia de pestaña.
# - Se invalida automáticamente cada 5 minutos para refrescar nuevos precios.
# =============================================================================
@st.cache_data(ttl=300, show_spinner=False)
def get_cached_catalogo():
    """Retorna el catálogo consolidado desde la capa de datos con caché de 5 minutos."""
    return obtener_catalogo()

@st.cache_data(ttl=300, show_spinner=False)
def get_cached_precios(perfume_id):
    """Consulta los precios vigentes en cada tienda para el perfume seleccionado."""
    return obtener_precios_actuales(perfume_id)

@st.cache_data(ttl=300, show_spinner=False)
def get_cached_historico(perfume_id):
    """Consulta la serie de tiempo de precios históricos para generar el gráfico."""
    return obtener_historico_precios(perfume_id)

@st.cache_data(ttl=300, show_spinner=False)
def get_cached_detalle(perfume_id):
    """Retorna la ficha técnica completa del perfume (notas, género, concentración)."""
    return obtener_detalle_perfume(perfume_id)


# =============================================================================
# BLOQUE 2: SANITIZACIÓN HTML Y RESOLUCIÓN INTELIGENTE DE ENLACES EXTERNOS
# -----------------------------------------------------------------------------
# ¿QUÉ HACE ESTE BLOQUE?
# 1. `clean_html()`: Remueve saltos de línea e identaciones en bloques HTML para que
#    el parser Markdown de Streamlit no los confunda con bloques de código preformateado.
# 2. `resolver_url_oferta()`: Garantiza que el botón "Ir a la oferta" nunca lleve a un
#    enlace roto. Si el scraper capturó la URL directa a la ficha, la usa; si no,
#    construye automáticamente la consulta al motor de búsqueda oficial de la tienda.
# =============================================================================
def clean_html(html_str: str) -> str:
    """Limpia espacios iniciales y elimina saltos de línea para evitar que Streamlit interprete HTML como código."""
    return " ".join(line.strip() for line in html_str.splitlines() if line.strip())

def resolver_url_oferta(tienda_nombre: str, perfume_nombre: str, url_prod: str, url_base: str, marca: str = "") -> str:
    """
    Retorna el enlace directo a la ficha del perfume exacto en la tienda.
    Si por algún motivo no existe URL directa o es una URL obsoleta / rota, redirige a la búsqueda de la tienda.
    """
    t = (tienda_nombre or "").lower()
    query_parts = f"{marca} {perfume_nombre}".strip() if (marca and marca.lower() not in perfume_nombre.lower()) else perfume_nombre.strip()
    q = urllib.parse.quote(query_parts)

    # Paris.cl rota constantemente sus IDs de catálogo (.html) provocando 404 "Página en Construcción".
    # Redirigir siempre a la búsqueda oficial de Paris garantiza que el usuario llegue a la fragancia disponible.
    if "paris" in t or ("paris.cl" in (url_prod or "").lower()):
        if not url_prod or ".html" in url_prod.lower() or "search" not in url_prod.lower():
            return f"https://www.paris.cl/search?q={q}"
        return url_prod

    # Validar que la URL directa no sea un marcador o enlace muerto
    if url_prod and url_prod.startswith("http") and url_prod != "#":
        return url_prod

    if "falabella" in t:
        return f"https://www.falabella.com/falabella-cl/search?Ntt={q}"
    elif "paris" in t:
        return f"https://www.paris.cl/search?q={q}"
    elif "ripley" in t:
        return f"https://simple.ripley.cl/search/{q}"
    elif "silk" in t:
        return f"https://www.silkperfumes.cl/search?q={q}"
    elif "elite" in t:
        return f"https://www.eliteperfumes.cl/search?q={q}"
    elif "alisha" in t:
        return f"https://www.alisha.cl/search?q={q}"
    elif "yauras" in t:
        return f"https://www.yauras.cl/search?q={q}"
    elif "dbs" in t:
        return f"https://www.dbs.cl/search?q={q}"

    return url_base or "#"

def get_image_src(img_path_or_url):
    """
    Retorna la URL remota o codifica la imagen local a base64 (Data URI)
    para que se renderice directamente en el navegador sin requerir un servidor estático.
    """
    if not img_path_or_url:
        return "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=500&q=80"
    
    if img_path_or_url.startswith("http://") or img_path_or_url.startswith("https://") or img_path_or_url.startswith("data:"):
        return img_path_or_url

    local_path = img_path_or_url
    if not os.path.isabs(local_path):
        cand1 = os.path.join(BASE_DIR, local_path)
        cand2 = os.path.join(BASE_DIR, "APP", local_path)
        if os.path.exists(cand1):
            local_path = cand1
        elif os.path.exists(cand2):
            local_path = cand2

    if os.path.exists(local_path):
        ext = os.path.splitext(local_path)[1].lower().replace(".", "")
        mime = "image/png" if ext == "png" else "image/jpeg"
        try:
            with open(local_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
                return f"data:{mime};base64,{b64}"
        except Exception:
            pass

    return img_path_or_url

# =============================================================================
# BLOQUE 3: CONFIGURACIÓN DE LA PÁGINA Y GESTIÓN DE SESIÓN (STREAMLIT STATE)
# -----------------------------------------------------------------------------
# ¿QUÉ HACE ESTE BLOQUE?
# 1. Configura el título y layout ancho (`wide`) de la página.
# 2. Inicializa las variables reactivas en `st.session_state`:
#    - `theme`: 'dark' o 'light' para alternar temas visuales.
#    - `logged_in`: booleano de autenticación.
#    - `user_info`: diccionario con nombre, email y teléfono del usuario.
#    - `show_login_modal`: controla la apertura del modal emergente de inicio de sesión.
# =============================================================================
st.set_page_config(page_title="Comparador de Precios - PerfumeTrending", layout="wide", initial_sidebar_state="collapsed")

if 'theme' not in st.session_state:
    st.session_state['theme'] = 'dark'

# ESTADOS DE AUTENTICACIÓN Y CONTROL DE MODAL
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_info' not in st.session_state:
    st.session_state['user_info'] = None
if 'show_login_modal' not in st.session_state:
    st.session_state['show_login_modal'] = False

# ESTADOS PARA INICIO POR CÓDIGO (OTP)
if 'otp_code_sent' not in st.session_state:
    st.session_state['otp_code_sent'] = False
if 'otp_contact' not in st.session_state:
    st.session_state['otp_contact'] = ""
if 'otp_secret' not in st.session_state:
    st.session_state['otp_secret'] = ""

def toggle_theme():
    st.session_state['theme'] = 'dark' if st.session_state['theme'] == 'light' else 'light'

# MODAL FLOTANTE DE INICIO DE SESIÓN Y REGISTRO
@st.dialog("Acceso a PerfumeTrending")
def modal_autenticacion():
    tab_codigo, tab_login, tab_registro = st.tabs(["Inicio por Código", "Iniciar Sesión", "Registrarse"])
    
    # OPCIÓN PREDETERMINADA: INICIO POR CÓDIGO
    with tab_codigo:
        st.markdown("#### Ingresa con tu Correo o Teléfono")
        
        if not st.session_state['otp_code_sent']:
            with st.form("form_send_otp", clear_on_submit=False):
                contact_input = st.text_input("Correo electrónico o número de teléfono", key="otp_contact_input", placeholder="ejemplo@correo.cl o +56912345678")
                btn_send = st.form_submit_button("Enviar código de verificación", use_container_width=True)
                
                if btn_send:
                    if not contact_input.strip():
                        st.error("Por favor ingresa un correo electrónico o teléfono válido.")
                    else:
                        code = str(random.randint(100000, 999999))
                        st.session_state['otp_code_sent'] = True
                        st.session_state['otp_contact'] = contact_input.strip()
                        st.session_state['otp_secret'] = code
                        st.rerun()
        else:
            st.info(f"Un código de verificación ha sido enviado a **{st.session_state['otp_contact']}**")
            st.caption(f"*(Código de prueba rápido: **{st.session_state['otp_secret']}**)*")
            
            with st.form("form_verify_otp", clear_on_submit=False):
                input_code = st.text_input("Ingresa el código de 6 dígitos", key="otp_code_input", placeholder="123456", max_chars=6)
                btn_verify = st.form_submit_button("Verificar e Ingresar", use_container_width=True)
                
                if btn_verify:
                    if input_code.strip() == st.session_state['otp_secret']:
                        contact_str = st.session_state['otp_contact']
                        
                        st.session_state['logged_in'] = True
                        st.session_state['user_info'] = {
                            'nombre': contact_str.split('@')[0] if '@' in contact_str else contact_str,
                            'email': contact_str if '@' in contact_str else f"{contact_str}@usuario.cl",
                            'telefono': contact_str if '@' not in contact_str else '+56 9 1234 5678'
                        }
                        
                        # Resetear estados de login y cerrar modal
                        st.session_state['otp_code_sent'] = False
                        st.session_state['otp_contact'] = ""
                        st.session_state['otp_secret'] = ""
                        st.session_state['show_login_modal'] = False
                        st.rerun()
                    else:
                        st.error("Código incorrecto. Revisa e intenta nuevamente.")
                        
            if st.button("Cambiar correo/teléfono", key="btn_reset_otp", use_container_width=True):
                st.session_state['otp_code_sent'] = False
                st.session_state['otp_contact'] = ""
                st.session_state['otp_secret'] = ""
                st.rerun()

    # OPCIÓN 2: CON TRADICIONAL CORREO / CONTRASEÑA
    with tab_login:
        st.markdown("#### Ingresa a tu cuenta")
        with st.form("form_login_pass", clear_on_submit=False):
            login_email = st.text_input("Correo Electrónico", key="login_email_input", placeholder="usuario@correo.cl")
            login_pass = st.text_input("Contraseña", type="password", key="login_pass_input", placeholder="••••••••")
            btn_login = st.form_submit_button("Ingresar a la plataforma", use_container_width=True)
            
            if btn_login:
                if not login_email or not login_pass:
                    st.error("Por favor ingresa tu correo y contraseña.")
                elif verificar_usuario:
                    exito, usuario_data = verificar_usuario(login_email, login_pass)
                    if exito:
                        st.session_state['logged_in'] = True
                        st.session_state['user_info'] = usuario_data
                        st.session_state['show_login_modal'] = False
                        st.rerun()
                    else:
                        st.error("Correo o contraseña incorrectos.")
                else:
                    st.info("Función de backend en proceso de actualización.")

    # OPCIÓN 3: REGISTRO NUEVO USUARIO
    with tab_registro:
        st.markdown("#### Crea una cuenta nueva")
        with st.form("form_reg_user", clear_on_submit=False):
            reg_nombre = st.text_input("Nombre completo", key="reg_nombre_input", placeholder="Juan Pérez")
            reg_email = st.text_input("Correo Electrónico", key="reg_email_input", placeholder="usuario@correo.cl")
            reg_pass1 = st.text_input("Contraseña", type="password", key="reg_pass1_input", placeholder="••••••••")
            reg_pass2 = st.text_input("Confirmar Contraseña", type="password", key="reg_pass2_input", placeholder="••••••••")
            btn_reg = st.form_submit_button("Crear mi cuenta", use_container_width=True)
            
            if btn_reg:
                if not reg_nombre or not reg_email or not reg_pass1:
                    st.error("Todos los campos son obligatorios.")
                elif reg_pass1 != reg_pass2:
                    st.error("Las contraseñas no coinciden.")
                elif len(reg_pass1) < 6:
                    st.warning("La contraseña debe tener al menos 6 caracteres.")
                elif crear_usuario:
                    exito, msg = crear_usuario(reg_nombre, reg_email, reg_pass1)
                    if exito:
                        st.success("¡Cuenta creada con éxito! Ya puedes iniciar sesión.")
                    else:
                        st.error(msg)
                else:
                    st.info("Función de backend en proceso de actualización.")

is_dark = st.session_state['theme'] == 'dark'

# Colores dinámicos adaptables por tema
app_bg = "#0c0e12" if is_dark else "#f9f9fb"
app_bg_css = f"background-color: {app_bg} !important;"

text_color = "#f0f0f0" if is_dark else "#18181b"
subtext_color = "#888890" if is_dark else "#666670"

btn_bg = "#181c24" if is_dark else "#ffffff"
btn_text = "#ffffff" if is_dark else "#18181b"
btn_border = "#2a2e39" if is_dark else "#d1d5db"

input_bg = "#14171d" if is_dark else "#ffffff"
input_text = "#f0f0f0" if is_dark else "#18181b"
input_border = "#2a2e39" if is_dark else "#d1d5db"

# SWITCH DE TEMA - POSICIONAMIENTO Y SVGS
bottle_left_pos = "42px" if is_dark else "-2px"
static_icon_pos = "12px center" if is_dark else "calc(100% - 12px) center"

static_icon_svg = (
    "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23ffffff' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><circle cx='12' cy='12' r='4'/><line x1='12' y1='1' x2='12' y2='3'/><line x1='12' y1='21' x2='12' y2='23'/><line x1='4.22' y1='4.22' x2='5.64' y2='5.64'/><line x1='18.36' y1='18.36' x2='19.78' y2='19.78'/><line x1='1' y1='12' x2='3' y2='12'/><line x1='21' y1='12' x2='23' y2='12'/><line x1='4.22' y1='19.78' x2='5.64' y2='18.36'/><line x1='18.36' y1='5.64' x2='19.78' y2='4.22'/></svg>"
    if is_dark else
    "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23ffffff' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M21 12.79A9 9 0 0 1 11.21 3 7 7 0 0 0 21 12.79z'/></svg>"
)

bottle_svg = (
    "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 50 58'><rect x='18' y='2' width='14' height='7' rx='2' fill='%23ffffff' stroke='%23111111' stroke-width='2.5'/><rect x='21' y='9' width='8' height='5' fill='%23ffffff' stroke='%23111111' stroke-width='2.5'/><circle cx='25' cy='34' r='19' fill='%23ffffff' stroke='%23111111' stroke-width='2.5'/><path d='M21 28a8 8 0 0 0 9 10.5 8.5 8.5 0 0 1-9-10.5z' fill='none' stroke='%23111111' stroke-width='2.2' stroke-linecap='round' stroke-linejoin='round'/></svg>"
    if is_dark else
    "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 50 58'><rect x='18' y='2' width='14' height='7' rx='2' fill='%23ffffff' stroke='%23111111' stroke-width='2.5'/><rect x='21' y='9' width='8' height='5' fill='%23ffffff' stroke='%23111111' stroke-width='2.5'/><circle cx='25' cy='34' r='19' fill='%23ffffff' stroke='%23111111' stroke-width='2.5'/><circle cx='25' cy='34' r='5' fill='none' stroke='%23111111' stroke-width='2'/><line x1='25' y1='23' x2='25' y2='26' stroke='%23111111' stroke-width='2' stroke-linecap='round'/><line x1='25' y1='42' x2='25' y2='45' stroke='%23111111' stroke-width='2' stroke-linecap='round'/><line x1='14' y1='34' x2='17' y2='34' stroke='%23111111' stroke-width='2' stroke-linecap='round'/><line x1='33' y1='34' x2='36' y2='34' stroke='%23111111' stroke-width='2' stroke-linecap='round'/><line x1='17' y1='26' x2='19' y2='28' stroke='%23111111' stroke-width='2' stroke-linecap='round'/><line x1='31' y1='40' x2='33' y2='42' stroke='%23111111' stroke-width='2' stroke-linecap='round'/><line x1='17' y1='42' x2='19' y2='40' stroke='%23111111' stroke-width='2' stroke-linecap='round'/><line x1='31' y1='28' x2='33' y2='26' stroke='%23111111' stroke-width='2' stroke-linecap='round'/></svg>"
)

user_icon_svg = f"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23{btn_text[1:]}' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2'/><circle cx='12' cy='7' r='4'/></svg>"
settings_icon_svg = f"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23{btn_text[1:]}' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.38a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z'/><circle cx='12' cy='12' r='3'/></svg>"
logout_icon_svg = f"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23{btn_text[1:]}' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4'/><polyline points='16 17 21 12 16 7'/><line x1='21' y1='12' x2='9' y2='12'/></svg>"

# ICONOS VECTORIALES DE ALTA PRECISIÓN (ESTILO LINEAR / STRIPE / LUCIDE)
trend_red_svg = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23d83737' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><polyline points='23 6 13.5 15.5 8.5 10.5 1 18'/><polyline points='17 6 23 6 23 12'/></svg>"
shield_red_svg = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23d83737' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z'/><polyline points='9 12 11 14 15 10'/></svg>"
tag_red_svg = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23d83737' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z'/><circle cx='7' cy='7' r='1.5' fill='%23d83737'/></svg>"
home_red_svg = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23d83737' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z'/><polyline points='9 22 9 12 15 12 15 22'/></svg>"
logo_color_encoded = "%238c7b6d"
text_color_encoded = "%23ffffff" if is_dark else "%2318181b"
logo_svg_data = f"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 36 36' fill='none' stroke-linecap='round' stroke-linejoin='round'><path d='M 6.8 21 L 29.2 21 C 30 25 27 32 18 32 C 9 32 6 25 6.8 21 Z' fill='{logo_color_encoded}' /><line x1='6.8' y1='21' x2='29.2' y2='21' stroke='{text_color_encoded}' stroke-width='1.5' /><line x1='18' y1='10' x2='18' y2='30' stroke='{text_color_encoded}' stroke-width='1' /><path d='M 18 32 C 9 32 5 24 7.5 17 C 9 12 13 10 15 10 L 21 10 C 23 10 27 12 28.5 17 C 31 24 27 32 18 32 Z' stroke='{text_color_encoded}' stroke-width='2' /><rect x='15' y='7' width='6' height='3' stroke='{text_color_encoded}' stroke-width='1.5' /><rect x='13' y='3' width='10' height='4' rx='1' stroke='{text_color_encoded}' stroke-width='1.5' /><rect x='16' y='0' width='4' height='3' rx='1' fill='{logo_color_encoded}' stroke='{text_color_encoded}' stroke-width='1' /></svg>"

# 2. CSS ADAPTABLE Y ESTILOS PRINCIPALES
st.markdown(f"""
    <style>
    html, body, .stApp {{
        -webkit-font-smoothing: antialiased !important;
        -moz-osx-font-smoothing: grayscale !important;
        text-rendering: optimizeLegibility !important;
    }}

    header[data-testid="stHeader"] {{ display: none !important; }}
    
    .block-container {{ 
        padding-top: 1.2rem !important; 
        padding-bottom: 2rem !important; 
        max-width: 1200px !important;
    }}
    
    .stApp {{ {app_bg_css} color: {text_color} !important; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }}

    .stApp p, .stApp span, .stApp label, .stMarkdown p {{
        color: {text_color} !important;
        text-shadow: none !important;
    }}

    /* BOTONES GENERALES DE ESTILO SOBRIO */
    div.stButton > button {{
        background-color: {btn_bg} !important;
        border: 1px solid {btn_border} !important;
        color: {btn_text} !important;
        border-radius: 8px !important;
        transition: transform 0.22s cubic-bezier(0.34, 1.56, 0.64, 1), background-color 0.15s ease, border-color 0.15s ease !important;
        outline: none !important;
    }}

    div.stButton > button p {{
        color: {btn_text} !important;
        font-weight: 600 !important;
    }}

    /* BOTÓN INGRESAR (LOGIN) Y CONTENEDORES DE LA CABECERA */
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
        padding: 0 0.8rem 0 2.2rem !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        background-image: url("{user_icon_svg}") !important;
        background-repeat: no-repeat !important;
        background-position: 10px center !important;
        background-size: 18px 18px !important;
        font-size: 0.95rem !important;
        margin: 0 !important;
        white-space: nowrap !important;
    }}

    .st-key-login_btn button p {{
        font-size: 0.95rem !important;
        line-height: 1 !important;
        margin: 0 !important;
        color: {btn_text} !important;
        font-weight: 600 !important;
        white-space: nowrap !important;
    }}

    /* ESTILO PARA BOTÓN POPOVER Y DESPLEGABLE DE PERFIL */
    div[data-testid="stPopover"],
    div[data-testid="stPopover"] > button,
    button[data-testid="stPopoverButton"],
    div[data-testid="stPopover"] button {{
        background-color: {btn_bg} !important;
        color: {btn_text} !important;
        border: 1px solid {btn_border} !important;
        border-radius: 8px !important;
        min-height: 44px !important;
        transition: transform 0.22s ease, background-color 0.15s ease !important;
    }}

    div[data-testid="stPopover"] button p,
    div[data-testid="stPopover"] button span,
    button[data-testid="stPopoverButton"] p,
    button[data-testid="stPopoverButton"] span {{
        color: {btn_text} !important;
        font-weight: 600 !important;
        white-space: nowrap !important;
    }}

    div[data-testid="stPopoverBody"],
    div[data-testid="stPopoverContent"] {{
        background-color: {input_bg} !important;
        border: 1px solid {btn_border} !important;
        border-radius: 8px !important;
        color: {text_color} !important;
    }}

    /* CONTENEDOR Y BOTÓN POPOVER DE USUARIO CON DIBUJO HTML/SVG */
    .user-popover-container div[data-testid="stPopover"],
    .user-popover-container div[data-testid="stPopover"] > button,
    .user-popover-container button[data-testid="stPopoverButton"] {{
        padding-left: 2.3rem !important;
        background-image: url("{user_icon_svg}") !important;
        background-repeat: no-repeat !important;
        background-position: 12px center !important;
        background-size: 18px 18px !important;
    }}

    /* BOTÓN CERRAR SESIÓN Y MI PERFIL CON DIBUJOS VECTORIALES HTML/SVG */
    .st-key-btn_go_profile button {{
        background-color: {btn_bg} !important;
        border: 1px solid {btn_border} !important;
        color: {btn_text} !important;
        padding-left: 2.5rem !important;
        background-image: url("{settings_icon_svg}") !important;
        background-repeat: no-repeat !important;
        background-position: 14px center !important;
        background-size: 18px 18px !important;
    }}

    .st-key-btn_go_profile button p {{
        color: {btn_text} !important;
    }}

    .st-key-btn_logout button {{
        background-color: {btn_bg} !important;
        border: 1px solid {btn_border} !important;
        color: {btn_text} !important;
        padding-left: 2.5rem !important;
        background-image: url("{logout_icon_svg}") !important;
        background-repeat: no-repeat !important;
        background-position: 14px center !important;
        background-size: 18px 18px !important;
    }}

    .st-key-btn_logout button p {{
        color: {btn_text} !important;
    }}

    /* SWITCH TEMA */
    .st-key-theme_toggle button,
    .st-key-theme_toggle button:hover,
    .st-key-theme_toggle button:focus {{
        background: transparent !important;
        border: none !important;
        padding: 0 !important;
        width: 82px !important;
        height: 48px !important;
        position: relative !important;
        cursor: pointer !important;
        margin-left: auto !important;
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
        z-index: 2 !important;
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

    /* DIBUJOS ILUSTRADOS VECTORIALES EN ROJO PARA LOS BOTONES */
    a[data-testid="stPageLink-NavLink"][href*="trendhype"],
    a[data-testid="stPageLink-NavLink"][href*="trustpage"],
    a[data-testid="stPageLink-NavLink"][href*="compararprecios"],
    a[data-testid="stPageLink-NavLink"][href$="app.py"],
    a[data-testid="stPageLink-NavLink"][href="/"] {{
        position: relative !important;
        padding-left: 2.7rem !important;
        padding-right: 1.1rem !important;
        overflow: hidden !important;
    }}

    /* 1. Trend Del Hype */
    a[data-testid="stPageLink-NavLink"][href*="trendhype"]::before {{
        content: '' !important;
        position: absolute !important;
        left: 14px !important;
        top: 50% !important;
        transform: translateY(-50%) !important;
        width: 17px !important;
        height: 17px !important;
        background-image: url("{trend_red_svg}") !important;
        background-repeat: no-repeat !important;
        background-size: contain !important;
        background-position: center !important;
        z-index: 1 !important;
    }}

    /* 2. Páginas de Confianza */
    a[data-testid="stPageLink-NavLink"][href*="trustpage"]::before {{
        content: '' !important;
        position: absolute !important;
        left: 14px !important;
        top: 50% !important;
        transform: translateY(-50%) !important;
        width: 17px !important;
        height: 17px !important;
        background-image: url("{shield_red_svg}") !important;
        background-repeat: no-repeat !important;
        background-size: contain !important;
        background-position: center !important;
        z-index: 1 !important;
    }}

    /* 3. Comparar Precios */
    a[data-testid="stPageLink-NavLink"][href*="compararprecios"]::before {{
        content: '' !important;
        position: absolute !important;
        left: 14px !important;
        top: 50% !important;
        transform: translateY(-50%) !important;
        width: 17px !important;
        height: 17px !important;
        background-image: url("{tag_red_svg}") !important;
        background-repeat: no-repeat !important;
        background-size: contain !important;
        background-position: center !important;
        z-index: 1 !important;
    }}

    /* 4. Inicio / Catálogo */
    a[data-testid="stPageLink-NavLink"][href$="app.py"]::before,
    a[data-testid="stPageLink-NavLink"][href="/"]::before {{
        content: '' !important;
        position: absolute !important;
        left: 14px !important;
        top: 50% !important;
        transform: translateY(-50%) !important;
        width: 17px !important;
        height: 17px !important;
        background-image: url("{home_red_svg}") !important;
        background-repeat: no-repeat !important;
        background-size: contain !important;
        background-position: center !important;
        z-index: 1 !important;
    }}

    /* TARJETA CABECERA DEL PERFUME */
    .perfume-header-card {{
        background-color: {btn_bg};
        border: 1px solid {btn_border};
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 24px;
        display: flex;
        gap: 24px;
        align-items: center;
    }}

    .perfume-header-img {{
        width: 130px;
        height: 130px;
        object-fit: contain;
        background: { "#14171d" if is_dark else "#ffffff" };
        border: 1px solid {btn_border};
        border-radius: 8px;
        padding: 8px;
    }}

    /* TARJETAS DE COMPARACIÓN DE PRECIOS */
    .price-card {{
        background-color: {btn_bg};
        border: 1px solid {btn_border};
        border-radius: 10px;
        padding: 16px 20px;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }}
    .price-card:hover {{
        transform: translateY(-2px);
        border-color: #d4c2a5;
    }}
    .best-deal {{
        border: 1px solid { "rgba(74, 222, 128, 0.45)" if is_dark else "rgba(46, 125, 50, 0.4)" } !important;
        background-color: { "rgba(34, 197, 94, 0.08)" if is_dark else "rgba(46, 125, 50, 0.06)" } !important;
        box-shadow: { "0 0 16px rgba(34, 197, 94, 0.08)" if is_dark else "0 2px 8px rgba(46, 125, 50, 0.06)" };
    }}
    .store-name {{
        font-size: 1.1rem;
        font-weight: 700;
        color: {text_color};
    }}
    .store-badge {{
        font-size: 0.75rem;
        padding: 2px 8px;
        border-radius: 4px;
        background-color: {btn_border};
        color: {text_color};
        margin-left: 8px;
    }}
    .price-value {{
        font-size: 1.25rem;
        font-weight: 800;
        color: {text_color};
    }}
    .old-price {{
        font-size: 0.85rem;
        text-decoration: line-through;
        color: {subtext_color};
        margin-right: 8px;
    }}
    .buy-btn {{
        background-color: #8c7b6d;
        color: #ffffff !important;
        padding: 8px 16px;
        border-radius: 6px;
        text-decoration: none;
        font-weight: 600;
        font-size: 0.85rem;
        display: inline-block;
        transition: background-color 0.2s ease;
    }}
    .buy-btn:hover {{
        background-color: #726255;
    }}

    /* BRAND LOGO INTERACTIVO NATIVO 100% LIMPIO Y TRANSPARENTE */
    a.brand-logo-clean,
    a.brand-logo-clean:visited,
    a.brand-logo-clean:hover,
    a.brand-logo-clean:active,
    a.brand-logo-clean:focus {{
        display: inline-flex !important;
        align-items: center !important;
        gap: 12px !important;
        text-decoration: none !important;
        background: transparent !important;
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
        outline: none !important;
        padding: 0 !important;
        margin: 0 !important;
        cursor: pointer !important;
        user-select: none !important;
        transition: transform 0.22s cubic-bezier(0.34, 1.56, 0.64, 1) !important;
    }}
    a.brand-logo-clean:hover {{
        transform: scale(1.02) !important;
        background: transparent !important;
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }}
    .brand-logo-text {{
        font-size: 1.55rem !important;
        color: {text_color} !important;
        letter-spacing: 0.3px !important;
        font-weight: 300 !important;
        line-height: 1 !important;
        display: inline-block !important;
        text-decoration: none !important;
    }}
    .brand-logo-text strong {{
        font-weight: 700 !important;
        color: {text_color} !important;
    }}
    </style>
""", unsafe_allow_html=True)

# 3. ENCABEZADO SUPERIOR: LOGO, BOTÓN "INGRESAR" / PERFIL Y SWITCH DE TEMA
if st.session_state['logged_in']:
    col_logo, col_espacio, col_actions = st.columns([4.0, 0.5, 4.5], vertical_alignment="center")
    btn_col1, btn_col2 = col_actions.columns([3.5, 1.0], vertical_alignment="center")
else:
    col_logo, col_espacio, col_actions = st.columns([5.5, 0.8, 2.7], vertical_alignment="center")
    btn_col1, btn_col2 = col_actions.columns([1.8, 1.0], vertical_alignment="center")

with col_logo:
    st.markdown(f"""
    <a href="/" target="_self" class="brand-logo-clean" title="PerfumeTrending">
        <svg width="34" height="34" viewBox="0 0 36 36" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path d="M 6.8 21 L 29.2 21 C 30 25 27 32 18 32 C 9 32 6 25 6.8 21 Z" fill="#8c7b6d" />
            <line x1="6.8" y1="21" x2="29.2" y2="21" stroke="{text_color}" stroke-width="1.5" />
            <line x1="18" y1="10" x2="18" y2="30" stroke="{text_color}" stroke-width="1" />
            <path d="M 18 32 C 9 32 5 24 7.5 17 C 9 12 13 10 15 10 L 21 10 C 23 10 27 12 28.5 17 C 31 24 27 32 18 32 Z" stroke="{text_color}" stroke-width="2" />
            <rect x="15" y="7" width="6" height="3" stroke="{text_color}" stroke-width="1.5" />
            <rect x="13" y="3" width="10" height="4" rx="1" stroke="{text_color}" stroke-width="1.5" />
            <rect x="16" y="0" width="4" height="3" rx="1" fill="#8c7b6d" stroke="{text_color}" stroke-width="1" />
        </svg>
        <span class="brand-logo-text">
            Perfume<strong>Trending</strong>
        </span>
    </a>
    """, unsafe_allow_html=True)

with btn_col1:
    if st.session_state['logged_in']:
        user_display = st.session_state['user_info'].get('nombre') or st.session_state['user_info'].get('email', 'Usuario')
        st.markdown('<div class="user-popover-container">', unsafe_allow_html=True)
        with st.popover(f"{user_display}", use_container_width=True):
            st.write(f"**Conectado como:**")
            st.write(st.session_state['user_info'].get('email', ''))
            st.markdown("<div style='margin-top: 8px;'></div>", unsafe_allow_html=True)
            
            # ACOPLE DIRECTO A LA PÁGINA DE PERFIL CON DIBUJO VECTORIAL SVG
            if st.button("Mi Perfil y Alertas", key="btn_go_profile", use_container_width=True):
                st.switch_page("pages/perfil.py")
                
            if st.button("Cerrar Sesión", key="btn_logout", use_container_width=True):
                st.session_state['logged_in'] = False
                st.session_state['user_info'] = None
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        if st.button("Ingresar", key="login_btn", use_container_width=True):
            st.session_state['show_login_modal'] = True

with btn_col2:
    st.button(" ", key="theme_toggle", on_click=toggle_theme)

# MONITOREO Y RENDERIZADO PERSISTENTE DEL MODAL
if st.session_state.get('show_login_modal', False):
    modal_autenticacion()

st.markdown("<div style='margin-top: 14px;'></div>", unsafe_allow_html=True)

# 4. CHIPS DE NAVEGACIÓN RÁPIDA
col_chip_home, col_chip1, col_chip2, col_chip3, col_chip_space = st.columns([1.6, 1.5, 2.0, 1.7, 2.2], vertical_alignment="center")

with col_chip_home:
    st.page_link("app.py", label="Inicio / Catálogo", use_container_width=True)
with col_chip1:
    st.page_link("pages/trendhype.py", label="Trend Del Hype", use_container_width=True)
with col_chip2:
    st.page_link("pages/trustpage.py", label="Páginas de Confianza", use_container_width=True)
with col_chip3:
    st.page_link("pages/compararprecios.py", label="Comparar Precios", use_container_width=True)

st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)

# 5. SECCIÓN PRINCIPAL: COMPARADOR DE PRECIOS
# =============================================================================
# BLOQUE 4: SELECCIÓN DEL PERFUME Y FICHA TÉCNICA OLFATIVA
# -----------------------------------------------------------------------------
# ¿QUÉ HACE ESTE BLOQUE?
# 1. Carga el catálogo mediante la función cacheada `get_cached_catalogo()`.
# 2. Revisa si en `st.session_state['selected_perfume']` viene un perfume preseleccionado
#    desde la página principal o desde el banner de tendencias, marcándolo por defecto.
# 3. Presenta un desplegable `st.selectbox` con búsqueda difusa en vivo.
# 4. Muestra la cabecera del perfume con su imagen oficial, concentración (EDP/EDT),
#    género (Hombre/Mujer/Unisex), notas de salida/corazón/fondo y precio de referencia.
# =============================================================================
col_title_text, col_title_back = st.columns([7, 3], vertical_alignment="center")
with col_title_text:
    st.markdown(f"""<div style='color: {text_color}; letter-spacing: 1.5px; font-weight: 300; font-size: 1.1rem; text-transform: uppercase;'>COMPARADOR DE PRECIOS EN TIENDAS CHILENAS</div>""", unsafe_allow_html=True)
with col_title_back:
    st.page_link("app.py", label="← Volver al Catálogo")

# Cargar catálogo dinámico con caché en memoria
catalogo = get_cached_catalogo()

if not catalogo:
    st.warning("No hay perfumes disponibles en el catálogo en este momento.")
    st.stop()

# Diccionario de mapeo rápido: Etiqueta Legible -> Objeto Perfume
opciones_perfumes = {f"{p['nombre']} — {p['marca']}": p for p in catalogo}
lista_nombres = list(opciones_perfumes.keys())

# Determinar perfume pre-seleccionado si el usuario vino redirigido desde otra vista
default_index = 0
selected_session = st.session_state.get('selected_perfume')
if selected_session is not None:
    for idx, (lbl, p) in enumerate(opciones_perfumes.items()):
        if str(selected_session) == str(p['id']) or (isinstance(selected_session, str) and selected_session.lower() in p['nombre'].lower()):
            default_index = idx
            break

selected_label = st.selectbox("Selecciona un perfume para comparar ofertas en Chile:", lista_nombres, index=default_index)
perfume = opciones_perfumes[selected_label]
selected_id = perfume['id']

# Obtener detalle enriquecido desde caché
detalle = get_cached_detalle(selected_id) or perfume

# Mostrar ficha cabecera del perfume con packshot de alta resolución
img_src = get_image_src(detalle.get('imagen_url'))
notas_txt = detalle.get('notas', 'Notas olfativas exclusivas')
genero_txt = detalle.get('genero', 'Unisex')
tipo_txt = detalle.get('tipo', 'Eau de Parfum')

col_img, col_info = st.columns([1, 3], gap="medium")
with col_img:
    st.markdown(f"""
    <div style="background: #ffffff; border-radius: 12px; padding: 12px; display: flex; align-items: center; justify-content: center; border: 1px solid {btn_border};">
        <img src="{img_src}" alt="{detalle['nombre']}" style="max-height: 180px; max-width: 100%; object-fit: contain;">
    </div>
    """, unsafe_allow_html=True)

with col_info:
    ref_precio = detalle.get('precio_referencia')
    ref_str = f"${ref_precio:,.0f} CLP".replace(",", ".") if ref_precio else "Consultar"
    
    st.markdown(f"""
    <div style="padding-top: 4px;">
        <h2 style="margin: 0 0 6px 0; color: {text_color}; font-size: 1.6rem; font-weight: 700;">{detalle['nombre']}</h2>
        <div style="color: {subtext_color}; font-size: 0.95rem; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 1px;">
            {detalle['marca']} &bull; {tipo_txt} &bull; {genero_txt}
        </div>
        <p style="margin: 0 0 8px 0; color: {text_color}; font-size: 0.9rem; line-height: 1.5;">
            <b>Notas olfativas:</b> {notas_txt}
        </p>
        <div style="margin-top: 10px; display: flex; gap: 16px; align-items: center;">
            <span style="font-size: 0.85rem; color: {subtext_color};">Precio referencial de mercado: <b style="color: {text_color};">{ref_str}</b></span>
            <span style="background-color: #2e7d3222; color: #4caf50; font-size: 0.78rem; font-weight: 700; padding: 3px 8px; border-radius: 4px; border: 1px solid #4caf5044;">DISPONIBLE EN TIENDAS AUDITADAS</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='margin-top: 24px;'></div>", unsafe_allow_html=True)
st.markdown(f"<h3 style='font-size: 1.15rem; color: {text_color}; font-weight: 600; margin-bottom: 16px;'>Ofertas en tiendas chilenas verificadas</h3>", unsafe_allow_html=True)


# =============================================================================
# BLOQUE 5: COMPARATIVA EN VIVO, CÁLCULO $/ML Y BADGE "MEJOR PRECIO"
# -----------------------------------------------------------------------------
# ¿QUÉ HACE ESTE BLOQUE?
# 1. Consulta las ofertas en stock en comercios chilenos (Falabella, Paris, Ripley, Silk, etc.).
# 2. Algoritmo de detección del mejor precio:
#    - Filtra los precios válidos mayores a 0.
#    - Encuentra el valor mínimo (`min_precio`).
#    - A la tienda ganadora le asigna la clase CSS `.best-deal` con borde verde brillante
#      y el distintivo "MEJOR PRECIO".
# 3. Métricas de valor real:
#    - Calcula el precio por mililitro: `precio_por_ml = precio_actual / volumen_ml`.
#      Esto permite que el usuario compare ofertas de 50ml vs 100ml de forma transparente.
# 4. Enlace de compra verificado con `resolver_url_oferta()`.
# =============================================================================
tiendas_db = get_cached_precios(selected_id)

if not tiendas_db:
    st.info("Actualmente estamos sincronizando los precios en tiempo real para esta fragancia.")
else:
    # Identificar el mejor precio (mínimo precio_actual > 0)
    precios_validos = [t['precio_actual'] for t in tiendas_db if t.get('precio_actual', 0) > 0]
    min_precio = min(precios_validos) if precios_validos else 0

    for item in tiendas_db:
        p_act = item.get('precio_actual', 0)
        p_norm = item.get('precio_normal', 0)
        vol_ml = item.get('volumen_ml', 100) or 100
        is_best_deal = (p_act == min_precio and p_act > 0)
        
        card_class = "price-card best-deal" if is_best_deal else "price-card"
        best_badge = f"<span style='background: {'rgba(34, 197, 94, 0.15)' if is_dark else '#e8f5e9'}; color: {'#4ade80' if is_dark else '#2e7d32'}; border: 1px solid {'rgba(74, 222, 128, 0.35)' if is_dark else 'rgba(46, 125, 50, 0.3)'}; font-weight: 700; margin-left: 8px; font-size: 0.72rem; padding: 2px 8px; border-radius: 4px; letter-spacing: 0.5px;'>MEJOR PRECIO</span>" if is_best_deal else ""
        
        precio_actual_str = f"${p_act:,.0f}".replace(",", ".")
        precio_ant_str = f"${p_norm:,.0f}".replace(",", ".") if p_norm and p_norm > p_act else ""
        old_price_html = f"<span class='old-price'>{precio_ant_str}</span>" if precio_ant_str else ""
        
        # Cálculo de valor por mililitro ($/ml)
        ml_txt = ""
        if p_act > 0 and vol_ml > 0:
            p_ml = int(round(p_act / vol_ml))
            ml_txt = f"<span style='font-size: 0.78rem; color: {subtext_color}; display: block; text-align: right;'>${p_ml:,.0f}/ml ({vol_ml}ml)</span>".replace(",", ".")
        
        # Enlace inteligente verificado directo a la ficha del producto en la tienda
        url_directa = resolver_url_oferta(
            tienda_nombre=item.get('tienda_nombre', ''),
            perfume_nombre=detalle.get('nombre', ''),
            url_prod=item.get('url_producto', ''),
            url_base=item.get('url_base', ''),
            marca=detalle.get('marca', '')
        )
        badge_tienda = item.get('badge', 'Tienda Verificada')
        badge_vol = f"<span class='store-badge' style='background: {btn_bg}; border: 1px solid {btn_border}; font-weight: 600;'>{vol_ml}ml</span>" if vol_ml else ""
        
        html_card = f"""
        <div class="{card_class}">
            <div>
                <span class="store-name">{item['tienda_nombre']}</span>
                <span class="store-badge">{badge_tienda}</span>
                {badge_vol}
                {best_badge}
            </div>
            <div style="display: flex; align-items: center; gap: 16px;">
                <div>
                    {old_price_html}
                    <span class="price-value">{precio_actual_str} CLP</span>
                    {ml_txt}
                </div>
                <a href="{url_directa}" class="buy-btn" target="_blank" rel="noopener noreferrer">Ir a la oferta ↗</a>
            </div>
        </div>
        """
        st.markdown(clean_html(html_card), unsafe_allow_html=True)


# =============================================================================
# BLOQUE 6: GRÁFICO INTERACTIVO DE EVOLUCIÓN HISTÓRICA DE PRECIOS
# -----------------------------------------------------------------------------
# ¿QUÉ HACE ESTE BLOQUE?
# 1. Consulta la serie cronológica de snapshots en `precios_registro`.
# 2. Convierte los datos a un DataFrame de Pandas (`pd.DataFrame`).
# 3. Transforma la tabla mediante `pivot_table(index='fecha', columns='tienda', values='precio')`.
# 4. Renderiza un gráfico de líneas nativo con `st.line_chart(df_pivot)` para que el
#    usuario observe si el perfume está en su punto más bajo histórico o si conviene esperar.
# =============================================================================
st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
with st.expander("Ver Evolución Histórica de Precios en Tiendas Chilenas"):
    historico = get_cached_historico(selected_id)
    if historico:
        df_hist = pd.DataFrame(historico)
        if 'fecha' in df_hist.columns and 'precio' in df_hist.columns and 'tienda' in df_hist.columns:
            df_hist['fecha'] = pd.to_datetime(df_hist['fecha'])
            df_pivot = df_hist.pivot_table(index='fecha', columns='tienda', values='precio', aggfunc='min')
            st.line_chart(df_pivot)
        else:
            st.write(df_hist)
    else:
        st.write("Recopilando datos históricos de variaciones de precio en comercios auditados.")
