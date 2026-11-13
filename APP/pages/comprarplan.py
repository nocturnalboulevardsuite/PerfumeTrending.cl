"""
PerfumeTrending.cl — Compra del Plan Premium (Checkout de demostración)
=======================================================================
Pantalla de pago con tarjeta de débito o crédito para activar el plan Premium:
- Vista previa de la tarjeta que se actualiza con los datos ingresados.
- Validación real del formulario (algoritmo de Luhn, vencimiento, CVV y titular).
- Tarjetas de prueba: una aprobada y una rechazada, para demostrar ambos casos.
- Al aprobarse, el perfil queda con plan 'premium' y aparece el sello de verificado.

IMPORTANTE: es un pago SIMULADO. No se conecta a ninguna pasarela, no se cobra dinero
y los datos de la tarjeta nunca se guardan (solo se conservan los últimos 4 dígitos
en el comprobante de la sesión).
"""

import streamlit as st
import sys
import os
import math
import time
import uuid
from datetime import datetime, date

# Configuración de rutas canónicas para importar backend y ui
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_DIR = os.path.dirname(APP_DIR)
for _p in (APP_DIR, BASE_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from ui import (
    PERFUME_SVG_FAVICON,
    clean_html as _shared_clean_html,
    escape_html,
    get_theme_palette,
    init_common_session_state,
)
from auth_email import modal_autenticacion

# Persistencia opcional del plan: si backend/database.py define `actualizar_plan_usuario`,
# el plan se guarda en Supabase; si no, queda activo solo durante la sesión.
try:
    from backend.database import actualizar_plan_usuario
except Exception:
    try:
        from APP.backend.database import actualizar_plan_usuario
    except Exception:
        actualizar_plan_usuario = None


def clean_html(html_str: str) -> str:
    return _shared_clean_html(html_str, join_char=" ")


# =============================================================================
# 1. CONFIGURACIÓN Y PALETA
# =============================================================================
st.set_page_config(
    page_title="Activar Premium - PerfumeTrending",
    page_icon=PERFUME_SVG_FAVICON,
    layout="wide",
    initial_sidebar_state="collapsed",
)
init_common_session_state()

pal = get_theme_palette()
is_dark = pal.is_dark
app_bg_css = pal.app_bg_css
text_color = pal.text_color
subtext_color = pal.subtext_color
btn_bg = pal.btn_bg
btn_text = pal.btn_text
btn_border = pal.btn_border
input_bg = pal.input_bg
input_text = pal.input_text
input_border = pal.input_border
if not is_dark:
    app_bg_css = "background: #ffffff !important; background-color: #ffffff !important;"
    text_color = "#1c1917"
    subtext_color = "#6b6159"
    btn_bg = "#ffffff"
    btn_text = "#1c1917"
    btn_border = "#d6cec5"
    input_bg = "#ffffff"
    input_text = "#1c1917"
    input_border = "#d6cec5"

card_bg = btn_bg
border_color = "rgba(255, 255, 255, 0.10)" if is_dark else "#e6e1db"
surface_soft = "rgba(255, 255, 255, 0.03)" if is_dark else "#faf8f5"
accent = "#d83737"
gold_plan = "#e2b857" if is_dark else "#a87b1c"
gold_plan_soft = "rgba(226, 184, 87, 0.12)" if is_dark else "rgba(168, 123, 28, 0.08)"
ok_green = "#4ade80" if is_dark else "#15803d"
font_sans = "'Manrope', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"

PRECIO_PREMIUM = 2000

# Tarjetas de prueba (formato de prueba estándar de las pasarelas, pasan el algoritmo de Luhn)
TARJETA_APROBADA = {"num": "4242 4242 4242 4242", "nombre": "USUARIO DEMO", "venc": "12/30", "cvv": "123"}
TARJETA_RECHAZADA = "4000000000000002"


def sello_verificado(size=22):
    """Insignia Premium verificada: sello ondulado naranjo (estilo verificado de Instagram)
    con un frasco de perfume negro y naranjo en el centro y un aura naranja animada.
    Es un SVG vectorial con animaciones SMIL, así que se anima tanto incrustado en HTML
    como usado de imagen (data URI)."""
    pts = []
    for i in range(24):
        r = 11 if i % 2 == 0 else 9.4
        a = math.pi * i / 12 - math.pi / 2
        pts.append(f"{12 + r * math.cos(a):.2f},{12 + r * math.sin(a):.2f}")
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="-5 -5 34 34" '
        'role="img" aria-label="Premium verificado" style="overflow:visible">'
        '<defs>'
        '<radialGradient id="ptSealAura" cx="0.5" cy="0.5" r="0.5">'
        '<stop offset="0.55" stop-color="#ff7a1a" stop-opacity="0.75"/>'
        '<stop offset="0.78" stop-color="#ff5a00" stop-opacity="0.28"/>'
        '<stop offset="1" stop-color="#ff7a1a" stop-opacity="0"/>'
        '</radialGradient>'
        '<linearGradient id="ptSealRing" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0" stop-color="#ffc46e"/><stop offset="0.35" stop-color="#ff8a1f"/>'
        '<stop offset="0.7" stop-color="#e8590c"/><stop offset="1" stop-color="#ffb04a"/>'
        '<animateTransform attributeName="gradientTransform" type="rotate" '
        'from="0 0.5 0.5" to="360 0.5 0.5" dur="5s" repeatCount="indefinite"/>'
        '</linearGradient>'
        '<linearGradient id="ptSealLiquid" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#ffb04a"/><stop offset="1" stop-color="#ff6a00"/>'
        '</linearGradient>'
        '</defs>'
        # Aura naranja que respira
        '<circle cx="12" cy="12" r="14" fill="url(#ptSealAura)">'
        '<animate attributeName="r" values="13.5;17;13.5" dur="2.6s" repeatCount="indefinite"/>'
        '<animate attributeName="opacity" values="0.5;1;0.5" dur="2.6s" repeatCount="indefinite"/>'
        '</circle>'
        # Sello ondulado con degradado naranjo en rotación
        f'<polygon points="{" ".join(pts)}" fill="url(#ptSealRing)" stroke="url(#ptSealRing)" '
        'stroke-width="1.4" stroke-linejoin="round"/>'
        # Frasco de perfume: tapa, cuello y cuerpo negros con detalles naranjos
        '<rect x="10.4" y="4.9" width="3.2" height="2.1" rx="0.55" fill="#111111"/>'
        '<rect x="10.4" y="4.9" width="3.2" height="0.65" rx="0.3" fill="#ff9a3c"/>'
        '<rect x="11.15" y="6.9" width="1.7" height="1.2" fill="#111111"/>'
        '<rect x="8" y="8" width="8" height="10.4" rx="2.4" fill="#111111" stroke="#ffd3a1" stroke-width="0.45"/>'
        '<rect x="9" y="12.6" width="6" height="4.8" rx="1.5" fill="url(#ptSealLiquid)">'
        '<animate attributeName="y" values="12.6;12.1;12.6" dur="2.6s" repeatCount="indefinite"/>'
        '<animate attributeName="height" values="4.8;5.3;4.8" dur="2.6s" repeatCount="indefinite"/>'
        '</rect>'
        '<path d="M9.5 9.5 V11.3" stroke="#ffffff" stroke-opacity="0.65" stroke-width="0.7" stroke-linecap="round"/>'
        '</svg>'
    )


# =============================================================================
# 2. VALIDACIONES DE LA TARJETA
# =============================================================================
def solo_digitos(valor):
    return "".join(ch for ch in str(valor or "") if ch.isdigit())


def luhn_valido(numero):
    if not numero:
        return False
    total = 0
    for i, d in enumerate(reversed(numero)):
        n = int(d)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def marca_tarjeta(numero):
    if numero.startswith("4"):
        return "VISA"
    if numero[:2] in ("51", "52", "53", "54", "55") or numero[:4].isdigit() and 2221 <= int(numero[:4] or 0) <= 2720:
        return "Mastercard"
    return ""


def parsear_vencimiento(valor):
    d = solo_digitos(valor)
    if len(d) != 4:
        return None
    mes, anio = int(d[:2]), 2000 + int(d[2:])
    if not 1 <= mes <= 12:
        return None
    return mes, anio


def validar(numero, nombre, venc, cvv):
    errores = []
    if len(numero) != 16 or not luhn_valido(numero):
        errores.append("El número de tarjeta no es válido.")
    if len(nombre.strip()) < 3:
        errores.append("Ingrese el nombre del titular tal como aparece en la tarjeta.")
    v = parsear_vencimiento(venc)
    hoy = date.today()
    if not v:
        errores.append("La fecha de vencimiento debe tener el formato MM/AA.")
    elif (v[1], v[0]) < (hoy.year, hoy.month):
        errores.append("La tarjeta está vencida.")
    if len(cvv) != 3:
        errores.append("El código de seguridad (CVV) debe tener 3 dígitos.")
    return errores


def usar_tarjeta_prueba():
    st.session_state["cp_num"] = TARJETA_APROBADA["num"]
    st.session_state["cp_nombre"] = TARJETA_APROBADA["nombre"]
    st.session_state["cp_venc"] = TARJETA_APROBADA["venc"]
    st.session_state["cp_cvv"] = TARJETA_APROBADA["cvv"]
    st.session_state.pop("cp_errores", None)


def volver_a_planes():
    st.session_state["current_page"] = "planes_page"


# =============================================================================
# 3. ESTILOS
# =============================================================================
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap');
header[data-testid="stHeader"] {{ display: none !important; }}
.block-container {{ padding-top: 1.6rem !important; max-width: 1080px !important; }}
.stApp {{ {app_bg_css} color: {text_color} !important; font-family: {font_sans}; }}
[data-testid="stAppViewContainer"], [data-testid="stMain"] {{ background: transparent !important; }}
.stApp p, .stApp label, .stMarkdown p {{ color: {text_color} !important; font-family: {font_sans} !important; }}

.cp-title {{ font-size: clamp(1.6rem, 3vw, 2.1rem); font-weight: 800; letter-spacing: -0.025em; color: {text_color}; line-height: 1.1; }}
.cp-lede {{ font-size: 0.98rem; color: {subtext_color}; margin-top: 8px; max-width: 60ch; line-height: 1.5; }}
.cp-step {{ font-size: 1rem; font-weight: 800; color: {text_color}; margin: 22px 0 10px; }}

/* Selector Débito / Crédito */
div[data-testid="stRadio"] div[role="radiogroup"] {{
    display: grid !important; grid-template-columns: 1fr 1fr; gap: 10px;
}}
div[data-testid="stRadio"] div[role="radiogroup"] > label {{
    margin: 0 !important; padding: 13px 16px !important;
    border: 1.5px solid {btn_border}; border-radius: 14px; background: {surface_soft};
    cursor: pointer; transition: border-color 0.18s ease, background-color 0.18s ease;
}}
div[data-testid="stRadio"] div[role="radiogroup"] > label:has(input:checked) {{
    border-color: {gold_plan}; background: {gold_plan_soft};
}}
div[data-testid="stRadio"] div[role="radiogroup"] > label p {{ font-weight: 700 !important; }}

/* Tarjeta visual */
.cp-card {{
    position: relative; overflow: hidden; box-sizing: border-box;
    width: 100%; max-width: 420px; aspect-ratio: 1.586 / 1; margin: 6px 0 18px;
    border-radius: 18px; padding: 22px 24px; color: #fff;
    display: flex; flex-direction: column; justify-content: space-between;
    box-shadow: 0 24px 44px -22px rgba(0,0,0,0.6);
    font-family: {font_sans};
}}
.cp-card-credito {{ background: linear-gradient(135deg, #2b2620 0%, #14110d 55%, #3a2f1c 100%); }}
.cp-card-debito {{ background: linear-gradient(135deg, #8f1f2a 0%, #4a0f18 60%, #2a0910 100%); }}
.cp-card::before {{
    content: ""; position: absolute; width: 280px; height: 280px; border-radius: 50%;
    right: -90px; top: -120px; background: radial-gradient(circle, rgba(226,184,87,0.30), transparent 65%);
}}
.cp-card-row {{ display: flex; justify-content: space-between; align-items: center; position: relative; }}
.cp-card-bank {{ font-size: 0.95rem; font-weight: 800; letter-spacing: -0.01em; }}
.cp-card-type {{ font-size: 0.72rem; font-weight: 700; opacity: 0.8; letter-spacing: 0.4px; }}
.cp-chip {{ width: 42px; height: 31px; border-radius: 6px; background: linear-gradient(135deg, #f3d488, #b8892a); position: relative; }}
.cp-chip::after {{ content: ""; position: absolute; inset: 7px 9px; border: 1px solid rgba(60,40,10,0.45); border-radius: 3px; }}
.cp-card-num {{ font-size: clamp(1.05rem, 2.6vw, 1.4rem); font-weight: 700; letter-spacing: 2px; font-variant-numeric: tabular-nums; position: relative; }}
.cp-card-label {{ font-size: 0.62rem; opacity: 0.65; letter-spacing: 0.4px; }}
.cp-card-val {{ font-size: 0.88rem; font-weight: 700; letter-spacing: 0.5px; max-width: 230px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.cp-card-brand {{ font-size: 1.15rem; font-weight: 800; font-style: italic; letter-spacing: -0.02em; }}

/* Campos */
[data-testid="stTextInputRootElement"], div[data-baseweb="input"] {{
    background-color: {input_bg} !important; border: 1px solid {input_border} !important;
    border-radius: 12px !important; min-height: 46px !important;
}}
[data-testid="stTextInputRootElement"]:focus-within, div[data-baseweb="input"]:focus-within {{
    border-color: {gold_plan} !important; box-shadow: 0 0 0 3px {gold_plan_soft} !important;
}}
[data-testid="stTextInputRootElement"] input, div[data-baseweb="input"] input {{
    color: {input_text} !important; background: transparent !important; font-size: 0.98rem !important;
}}
[data-testid="stWidgetLabel"] p {{ font-size: 0.84rem !important; font-weight: 600 !important; color: {subtext_color} !important; }}

/* Nota de tarjetas de prueba */
.cp-demo {{
    border: 1px dashed {gold_plan}; background: {gold_plan_soft}; border-radius: 14px;
    padding: 12px 16px; font-size: 0.86rem; color: {text_color}; line-height: 1.55; margin-bottom: 10px;
}}
.cp-demo b {{ font-variant-numeric: tabular-nums; }}

/* Botones */
div.stButton > button {{
    border-radius: 12px !important; min-height: 46px !important;
    background: transparent !important; border: 1.5px solid {btn_border} !important; box-shadow: none !important;
}}
div.stButton > button p {{ color: {btn_text} !important; font-weight: 700 !important; }}
div.stButton > button:hover {{ border-color: {gold_plan} !important; }}
div.st-key-btn_pagar div.stButton > button {{
    min-height: 54px !important; border: 1px solid #c99a2f !important;
    background: linear-gradient(135deg, #f7dc8f 0%, #e2b857 45%, #b98a26 100%) !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.55), 0 12px 26px -14px #c9992f !important;
}}
div.st-key-btn_pagar div.stButton > button p {{ color: #2a1f05 !important; font-size: 1.02rem !important; }}
div.st-key-btn_pagar div.stButton > button:hover {{ filter: brightness(1.05); }}

/* Resumen */
.cp-summary {{
    border: 1px solid {gold_plan}; border-radius: 20px; padding: 24px;
    background: linear-gradient(180deg, {gold_plan_soft} 0%, transparent 60%), {card_bg};
    box-shadow: 0 22px 44px -30px {gold_plan};
}}
.cp-sum-name {{ font-size: 1.3rem; font-weight: 800; color: {gold_plan}; }}
.cp-sum-for {{ font-size: 0.86rem; color: {subtext_color}; margin-top: 2px; }}
.cp-sum-list {{ margin: 18px 0; display: flex; flex-direction: column; gap: 10px; }}
.cp-sum-item {{ display: flex; gap: 10px; font-size: 0.9rem; color: {text_color}; line-height: 1.4; }}
.cp-sum-dot {{ flex: 0 0 18px; height: 18px; border-radius: 50%; background: {gold_plan}; display: inline-flex; align-items: center; justify-content: center; margin-top: 1px; }}
.cp-sum-line {{ display: flex; justify-content: space-between; font-size: 0.9rem; color: {subtext_color}; padding: 8px 0; border-top: 1px solid {border_color}; }}
.cp-sum-total {{ display: flex; justify-content: space-between; align-items: baseline; padding-top: 12px; border-top: 1px solid {border_color}; }}
.cp-sum-total-label {{ font-size: 0.95rem; font-weight: 700; color: {text_color}; }}
.cp-sum-total-val {{ font-size: 1.6rem; font-weight: 800; color: {text_color}; letter-spacing: -0.02em; font-variant-numeric: tabular-nums; }}
.cp-secure {{ display: flex; gap: 8px; align-items: flex-start; font-size: 0.8rem; color: {subtext_color}; margin-top: 14px; line-height: 1.45; }}

/* Éxito */
.cp-success {{
    max-width: 560px; margin: 10px auto 0; text-align: center;
    border: 1px solid {gold_plan}; border-radius: 22px; padding: 34px 28px 26px;
    background: linear-gradient(180deg, {gold_plan_soft} 0%, transparent 55%), {card_bg};
}}
.cp-success-seal {{ display: flex; justify-content: center; margin-bottom: 14px; }}
.cp-success-title {{ font-size: 1.6rem; font-weight: 800; color: {text_color}; letter-spacing: -0.02em; }}
.cp-success-text {{ font-size: 0.95rem; color: {subtext_color}; margin: 8px auto 20px; max-width: 42ch; line-height: 1.5; }}
.cp-receipt {{ text-align: left; border-top: 1px dashed {border_color}; padding-top: 14px; }}
.cp-receipt-row {{ display: flex; justify-content: space-between; gap: 12px; font-size: 0.88rem; padding: 5px 0; color: {subtext_color}; }}
.cp-receipt-row b {{ color: {text_color}; font-variant-numeric: tabular-nums; }}

@media (max-width: 768px) {{
    .block-container {{ padding-left: 0.9rem !important; padding-right: 0.9rem !important; }}
    div[data-testid="stColumn"] {{ width: 100% !important; flex: 1 1 100% !important; }}
}}
</style>
""", unsafe_allow_html=True)

svg_check_dark = '<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#2a1f05" stroke-width="3.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="20 6 9 17 4 12"/></svg>'
svg_lock = f'<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="{subtext_color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" style="flex:0 0 15px; margin-top:1px;"><rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/></svg>'


# =============================================================================
# 4. ENCABEZADO
# =============================================================================
c_back, _ = st.columns([2.2, 7.8])
with c_back:
    if st.button("‹ Volver a planes", key="btn_volver_planes", use_container_width=True, on_click=volver_a_planes):
        st.switch_page("app.py")

if st.session_state.get("show_login_modal"):
    st.session_state["show_login_modal"] = False
    modal_autenticacion()

# Usuario sin sesión: no puede comprar
if not st.session_state.get("logged_in") or not st.session_state.get("user_info"):
    st.markdown(clean_html("""
        <div class="cp-title">Activar Premium</div>
        <div class="cp-lede">Para contratar el plan Premium es necesario iniciar sesión con su cuenta.</div>
    """), unsafe_allow_html=True)
    st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)
    c_login, _ = st.columns([2.4, 7.6])
    with c_login:
        if st.button("Iniciar sesión", key="btn_cp_login", use_container_width=True):
            st.session_state["show_login_modal"] = True
            st.rerun()
    st.stop()

user_info = st.session_state["user_info"]
u_ident = user_info.get("id") or user_info.get("email")
u_plan = str(user_info.get("plan") or "free").strip().lower()
recibo = st.session_state.get("cp_recibo")


# =============================================================================
# 5. PANTALLA DE ÉXITO (o usuario que ya es Premium)
# =============================================================================
if u_plan in ("premium", "vip", "socios_vip"):
    if recibo:
        filas = "".join(
            f'<div class="cp-receipt-row"><div>{k}</div><b>{escape_html(v)}</b></div>'
            for k, v in [
                ("N.º de orden", recibo["orden"]),
                ("Fecha", recibo["fecha"]),
                ("Medio de pago", f'{recibo["tipo"]} {recibo["marca"]} terminada en {recibo["last4"]}'),
                ("Total pagado", f'${recibo["monto"]:,.0f} CLP'.replace(",", ".")),
            ]
        )
        titulo, texto = "Pago aprobado", "Su cuenta ahora es Premium verificada. Ya puede activar las alertas de precio desde su perfil."
    else:
        filas = ""
        titulo, texto = "Su cuenta ya es Premium", "El plan Premium está activo y su perfil muestra el sello de verificado."

    st.markdown(clean_html(f"""
        <div class="cp-success">
            <div class="cp-success-seal">{sello_verificado(76)}</div>
            <div class="cp-success-title">{titulo}</div>
            <div class="cp-success-text">{texto}</div>
            {f'<div class="cp-receipt">{filas}</div>' if filas else ''}
        </div>
    """), unsafe_allow_html=True)
    st.markdown("<div style='margin-top:18px;'></div>", unsafe_allow_html=True)
    _, c1, c2, _ = st.columns([1.2, 2, 2, 1.2])
    with c1:
        if st.button("Ir a mi perfil", key="btn_cp_perfil", use_container_width=True):
            st.switch_page("pages/perfil.py")
    with c2:
        if st.button("Volver al catálogo", key="btn_cp_catalogo", use_container_width=True):
            st.session_state["current_page"] = "home"
            st.switch_page("app.py")
    st.stop()


# =============================================================================
# 6. CHECKOUT
# =============================================================================
st.markdown(clean_html("""
    <div class="cp-title">Activar Premium</div>
    <div class="cp-lede">Complete los datos de su tarjeta para activar las alertas de precio de sus fragancias favoritas.</div>
"""), unsafe_allow_html=True)

col_pago, col_resumen = st.columns([6, 4], gap="large")

with col_pago:
    st.markdown("<div class='cp-step'>Medio de pago</div>", unsafe_allow_html=True)
    tipo = st.radio("Tipo de tarjeta", ["Débito", "Crédito"], horizontal=True, key="cp_tipo", label_visibility="collapsed")

    # Vista previa con los valores actuales de los campos
    num_prev = solo_digitos(st.session_state.get("cp_num", ""))[:16]
    num_fmt = " ".join(
        (num_prev + "•" * (16 - len(num_prev)))[i:i + 4] for i in range(0, 16, 4)
    )
    nombre_prev = escape_html((st.session_state.get("cp_nombre") or "NOMBRE DEL TITULAR").upper())
    venc_prev = escape_html(st.session_state.get("cp_venc") or "MM/AA")
    marca_prev = marca_tarjeta(num_prev)
    clase_tarjeta = "cp-card-debito" if tipo == "Débito" else "cp-card-credito"

    st.markdown(clean_html(f"""
        <div class="cp-card {clase_tarjeta}" aria-hidden="true">
            <div class="cp-card-row">
                <div class="cp-card-bank">Banco Demo</div>
                <div class="cp-card-type">{tipo.upper()}</div>
            </div>
            <div class="cp-card-row"><div class="cp-chip"></div></div>
            <div class="cp-card-num">{num_fmt}</div>
            <div class="cp-card-row">
                <div>
                    <div class="cp-card-label">TITULAR</div>
                    <div class="cp-card-val">{nombre_prev}</div>
                </div>
                <div>
                    <div class="cp-card-label">VENCE</div>
                    <div class="cp-card-val">{venc_prev}</div>
                </div>
                <div class="cp-card-brand">{marca_prev}</div>
            </div>
        </div>
    """), unsafe_allow_html=True)

    st.markdown(clean_html(f"""
        <div class="cp-demo">
            Entorno de demostración: no se realiza ningún cargo real.<br>
            Tarjeta aprobada: <b>4242 4242 4242 4242</b>, vence <b>12/30</b>, CVV <b>123</b>.<br>
            Tarjeta rechazada: <b>4000 0000 0000 0002</b>, con cualquier fecha futura.
        </div>
    """), unsafe_allow_html=True)
    c_demo, _ = st.columns([2.6, 4])
    with c_demo:
        st.button("Usar tarjeta de prueba", key="btn_cp_demo", on_click=usar_tarjeta_prueba, use_container_width=True)

    st.markdown("<div class='cp-step'>Datos de la tarjeta</div>", unsafe_allow_html=True)
    st.text_input("Número de tarjeta", key="cp_num", placeholder="0000 0000 0000 0000", max_chars=19)
    st.text_input("Nombre del titular", key="cp_nombre", placeholder="Como aparece en la tarjeta", max_chars=40)
    c_venc, c_cvv = st.columns(2)
    with c_venc:
        st.text_input("Vencimiento", key="cp_venc", placeholder="MM/AA", max_chars=5)
    with c_cvv:
        st.text_input("CVV", key="cp_cvv", placeholder="123", max_chars=3, type="password")

    st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
    pagar = st.button(f"Pagar $2.000 CLP", key="btn_pagar", use_container_width=True)

    if pagar:
        numero = solo_digitos(st.session_state.get("cp_num"))
        nombre = st.session_state.get("cp_nombre") or ""
        venc = st.session_state.get("cp_venc") or ""
        cvv = solo_digitos(st.session_state.get("cp_cvv"))
        errores = validar(numero, nombre, venc, cvv)

        if errores:
            st.error("\n\n".join(errores))
        else:
            with st.spinner("Procesando pago..."):
                time.sleep(1.6)
            if numero == TARJETA_RECHAZADA:
                st.error("Pago rechazado por el banco emisor. Intente con otra tarjeta.")
            else:
                # Pago aprobado: activar el plan (sesión + base de datos si existe la función)
                st.session_state["user_info"]["plan"] = "premium"
                if actualizar_plan_usuario and u_ident:
                    try:
                        actualizar_plan_usuario(u_ident, "premium")
                    except Exception:
                        pass
                st.session_state["cp_recibo"] = {
                    "orden": "PT-" + uuid.uuid4().hex[:8].upper(),
                    "fecha": datetime.now().strftime("%d-%m-%Y %H:%M"),
                    "tipo": tipo,
                    "marca": marca_tarjeta(numero) or "Tarjeta",
                    "last4": numero[-4:],
                    "monto": PRECIO_PREMIUM,
                }
                # Los datos de la tarjeta no se conservan
                for k in ("cp_num", "cp_nombre", "cp_venc", "cp_cvv"):
                    st.session_state.pop(k, None)
                st.rerun()

with col_resumen:
    st.markdown("<div class='cp-step'>Resumen</div>", unsafe_allow_html=True)
    items = "".join(
        f'<div class="cp-sum-item"><div class="cp-sum-dot">{svg_check_dark}</div><div>{t}</div></div>'
        for t in [
            "Incluye todos los beneficios del plan Free",
            "Notificación cuando un perfume favorito baja de precio",
            "Detalle de la tienda y del nuevo precio",
            "Sello de usuario verificado en su perfil",
        ]
    )
    st.markdown(clean_html(f"""
        <div class="cp-summary">
            <div class="cp-sum-name">Plan Premium</div>
            <div class="cp-sum-for">Suscripción mensual</div>
            <div class="cp-sum-list">{items}</div>
            <div class="cp-sum-line"><div>Plan Premium (1 mes)</div><div>$2.000</div></div>
            <div class="cp-sum-total">
                <div class="cp-sum-total-label">Total</div>
                <div class="cp-sum-total-val">$2.000 CLP</div>
            </div>
            <div class="cp-secure">{svg_lock}<div>Pago simulado. Los datos de la tarjeta no se almacenan.</div></div>
        </div>
    """), unsafe_allow_html=True)
