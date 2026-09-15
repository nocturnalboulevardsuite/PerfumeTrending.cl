import streamlit as st

# Configuración inicial de la página
st.set_page_config(page_title="PerfumeTrending", layout="wide")

# -----------------------------------------------------------------------------
# INYECCIÓN CSS: Efecto Mini-Zoom en botones
# -----------------------------------------------------------------------------
st.markdown("""
<style>
/* Aplicar transición a todos los botones de Streamlit e interfaz */
div.stButton > button,
div.stDownloadButton > button,
button,
.btn-zoom {
    transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    will-change: transform;
}

/* Efecto Mini-Zoom al pasar el cursor (Hover) */
div.stButton > button:hover,
div.stDownloadButton > button:hover,
button:hover,
.btn-zoom:hover {
    transform: scale(1.035) !important;
    cursor: pointer;
}

/* Efecto al presionar (Active) */
div.stButton > button:active,
div.stDownloadButton > button:active,
button:active,
.btn-zoom:active {
    transform: scale(0.98) !important;
}
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# DICCIONARIO DE ESENCIAS Y NOTAS (FRAGRANTICA)
# -----------------------------------------------------------------------------
DICCIONARIO_ESENCIAS = {
    "Cítricos": [
        "Limón", "Bergamota", "Naranja", "Mandarina", "Pomelo (Toronja)", 
        "Lima", "Yuzu", "Clementina", "Neroli", "Petit grain"
    ],
    "Frutas, verduras y nueces": [
        "Manzana", "Pera", "Durazno (Melocotón)", "Ciruela", "Higo", 
        "Coco", "Almendra", "Avellana", "Grosella negra", "Frambuesa"
    ],
    "Flores": [
        "Rosa", "Violeta", "Geranio", "Iris / Orris", "Peonía", 
        "Lilium (Lirio)", "Lavanda", "Fresia", "Heliotropo", "Mimosa"
    ],
    "Flores Blancas": [
        "Jazmín", "Tuberosa (Nardo)", "Flor de Azahar del Naranjo", 
        "Gardenia", "Ylang-Ylang", "Magnolia", "Flor de Frangipani"
    ],
    "Hierbas, verdes y fougères": [
        "Menta", "Albahaca", "Romero", "Té verde", "Hojas de violeta", 
        "Gálbano", "Té negro", "Salvia", "Eucalipto"
    ],
    "Especias": [
        "Canela", "Pimienta negra", "Pimienta rosa", "Cardamomo", 
        "Clavo de olor", "Nuez moscada", "Jengibre", "Azafrán", "Anís estrellado"
    ],
    "Dulces y aromas golosos (Gourmand)": [
        "Vainilla", "Haba tonka", "Cacao / Chocolate", "Caramelo", 
        "Café", "Miel", "Praliné", "Malvavisco", "Leche"
    ],
    "Maderas y musgos": [
        "Sándalo", "Cedro", "Oud (Madera de Agar)", "Vetiver", 
        "Pachulí", "Musgo de roble", "Ciprés", "Guayac", "Ébano"
    ],
    "Resinas y balsámicos": [
        "Ámbar", "Incienso (Olibano)", "Mirra", "Bálsamo del Perú", 
        "Benjuí", "Ládano", "Estoraque"
    ],
    "Almizcle, ámbar y notas animales": [
        "Almizcle blanco", "Ámbar gris", "Castóreo", "Civeta", "Almizcle vegetal"
    ],
    "Bebidas": [
        "Ron", "Cognac", "Champán", "Whisky", "Ginebra", "Amaretto", "Mojito"
    ],
    "Sintéticos y abstractos": [
        "Iso E Super", "Ambroxan", "Notas marinas / Ozónicas", 
        "Aldehídos", "Acorde de Gamuza / Cuero", "Cachemira"
    ]
}

# -----------------------------------------------------------------------------
# INTERFAZ Y NAVEGACIÓN DE PRUEBA
# -----------------------------------------------------------------------------
st.title("PerfumeTrending")

# Botones con efecto mini-zoom
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.button("PERFUMES")
with col2:
    st.button("PERFUMES ÁRABES")
with col3:
    st.button("MARCAS")
with col4:
    st.button("DISEÑADOR")
with col5:
    st.button("NICHO")

st.divider()

# Selector para el Diccionario de Esencias
st.subheader("Diccionario de Esencias")

categoria_sel = st.selectbox("Selecciona una Categoría", list(DICCIONARIO_ESENCIAS.keys()))
notas_disponibles = DICCIONARIO_ESENCIAS[categoria_sel]

nota_sel = st.selectbox("Selecciona una Nota", notas_disponibles)

st.write(f"Has seleccionado la nota **{nota_sel}** dentro de la categoría **{categoria_sel}**.")
