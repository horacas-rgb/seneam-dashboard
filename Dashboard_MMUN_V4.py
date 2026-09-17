import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import re
import base64

# Configuración de la página
st.set_page_config(
    page_title="Dashboard Ejecutivo ATFM - SENEAM V4", 
    page_icon="Seneam_Logo.png", 
    layout="wide"
)

def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

try:
    img_base64 = get_base64_of_bin_file('Seneam_Logo.png')
    logo_html = f'<img src="data:image/png;base64,{img_base64}" style="height: 60px; vertical-align: middle; margin-right: 15px;">'
except:
    logo_html = ""

st.markdown("""
    <style>
    /* Fondo de la aplicación */
    .main {background-color: #0c2340;}
    
    /* Títulos principales */
    h1 {
        color: #FFFFFF !important; 
        font-family: 'Helvetica Neue', sans-serif;
        display: flex;
        align-items: center;
    }
    
    p {color: #FFFFFF;}
    
    .stSelectbox label p, 
    .stRadio label p, 
    div[role="radiogroup"] label div {
        color: #FFFFFF !important;
        font-weight: bold;
    }
    
    div[data-baseweb="select"] span {
        color: #000000 !important;
    }
    </style>
""", unsafe_allow_html=True)

# Título
st.markdown(f"<h1>{logo_html} Análisis Dinámico de Rutas RNAV/PBN - MMUN</h1>", unsafe_allow_html=True)
st.markdown("**Fuente de Datos:** Registros TopSky (Llegadas y Salidas) | **Periodo:** Septiembre 2026")
st.markdown("<hr style='border: 1px solid #00FFFF;'>", unsafe_allow_html=True)

# DICCIONARIO BASE DE COORDENADAS SENEAM
COORDENADAS = {
    'MMUN': (21.0366, -86.8770),
    'MMMX': (19.4361, -99.0719), 'MMMY': (25.7785, -100.1069), 'MMSM': (19.7573, -99.0165),
    'MMGL': (20.5218, -103.3112), 'MMTO': (19.3371, -99.5660), 'MMTJ': (32.5411, -116.9702),
    'KIAH': (29.9902, -95.3368), 'KJFK': (40.6413, -73.7781), 'KATL': (33.6407, -84.4277),
    'CYYZ': (43.6777, -79.6248), 'MPTO': (9.0715, -79.3835), 'LEMD': (40.4839, -3.5679),
    'MUFH': (23.1340, -82.3980), 'SKBO': (4.7016, -74.1469), 'SPJC': (-12.0219, -77.1143),
    'NOSAT': (21.8000, -86.1000), 'VOMAR': (22.0000, -87.8000), 'XUDUN': (21.8000, -87.5000),
    'KEHLI': (24.0000, -89.8000), 'SIGMA': (19.6000, -86.4000), 'UDGUV': (20.8000, -88.1000),
    'GOTAS': (19.5000, -90.0000), 'LIDAM': (18.5000, -88.0000), 'ILUBA': (20.0000, -85.0000),
    'UBVOV': (20.5000, -89.0000), 'MYDIA': (22.5000, -87.0000), 'NOTEN': (21.0000, -90.0000),
    'NUDAL': (22.0000, -85.0000), 'TAKUX': (23.0000, -88.0000), 'MATOL': (24.0000, -91.0000),
    'PAULE': (20.2000, -86.2000), 'PISAD': (23.5000, -86.5000), 'IRDOV': (22.8000, -89.5000),
    'SHARQ': (23.0000, -86.0000), 'ALCZM': (21.5000, -89.0000), 'NUBIT': (20.8000, -87.5000)
}

def parse_coord(coord_str):
    match = re.match(r'^(\d{2})(\d{2})?(N|S)(\d{3})(\d{2})?(E|W)$', coord_str)
    if match:
        lat = float(match.group(1)) + (float(match.group(2)) if match.group(2) else 0)/60.0
        if match.group(3) == 'S': lat = -lat
        lon = float(match.group(4)) + (float(match.group(5)) if match.group(5) else 0)/60.0
        if match.group(6) == 'W': lon = -lon
        return (lat, lon)
    return None

def extract_trajectory(route_string, adep, ades, is_arrival):
    path = []
    if is_arrival and adep in COORDENADAS: path.append(COORDENADAS[adep])
    elif not is_arrival: path.append(COORDENADAS['MMUN'])
        
    if pd.notna(route_string):
        words = str(route_string).replace('/', ' ').split()
        for word in words:
            coord = parse_coord(word)
            if coord: path.append(coord)
            elif word in COORDENADAS: path.append(COORDENADAS[word])
                
    if is_arrival: path.append(COORDENADAS['MMUN'])
    elif not is_arrival and ades in COORDENADAS: path.append(COORDENADAS[ades])
    return path

@st.cache_data
def cargar_datos_dia(dia_seleccionado):
    try:
        df_lleg = pd.read_excel('lleg_MMUN_sept_2026.xlsx', sheet_name=dia_seleccionado)
        df_sal = pd.read_excel('sal_MMUN_sept_2026.xlsx', sheet_name=dia_seleccionado)
        return df_lleg, df_sal
    except Exception as e:
        return None, None

try:
    xls = pd.ExcelFile('lleg_MMUN_sept_2026.xlsx')
    dias_disponibles = [hoja for hoja in xls.sheet_names if hoja.startswith('2026-')]
except:
    st.error("Asegúrate de colocar 'lleg_MMUN_sept_2026.xlsx' y 'sal_MMUN_sept_2026.xlsx' en esta carpeta.")
    st.stop()

col_filtros, col_mapa = st.columns([1, 3])

with col_filtros:
    st.markdown("<h2 style='color: #FFFFFF;'>Filtros Operativos</h2>", unsafe_allow_html=True)
    
    dia_seleccionado = st.selectbox("Seleccione el Día:", dias_disponibles)
    flujo = st.radio("Flujo de Tránsito:", ["Llegadas", "Salidas", "Llegadas y Salidas"])
    
    df_lleg, df_sal = cargar_datos_dia(dia_seleccionado)
    if df_lleg is None: st.stop()
        
    total_llegadas = len(df_lleg)
    total_salidas = len(df_sal)
    
    st.markdown("<h3 style='color: #FFFFFF;'>Resumen Estadístico</h3>", unsafe_allow_html=True)
    if flujo == "Llegadas y Salidas":
        st.info(f"Total de operaciones (Llegadas y Salidas): **{total_llegadas + total_salidas}**")
        st.markdown(f"<p style='color: white;'>- Llegadas: {total_llegadas}</p>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: white;'>- Salidas: {total_salidas}</p>", unsafe_allow_html=True)
    elif flujo == "Llegadas":
        st.info(f"Total de Llegadas: **{total_llegadas}**")
    else:
        st.info(f"Total de Salidas: **{total_salidas}**")

with col_mapa:
    # Solución definitiva para el fondo oscuro: Esri Dark Gray Canvas
    # Este mapa es gratuito, no requiere API KEY y es un estándar en GIS/Aviación
    tiles_url = 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}'
    attr = 'Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ'
    
    m = folium.Map(location=[21.0366, -86.8770], zoom_start=5, tiles=tiles_url, attr=attr)
    
    if flujo in ["Llegadas", "Llegadas y Salidas"]:
        for _, row in df_lleg.iterrows():
            trayectoria = extract_trajectory(row['route'], row['adep'], row['ades'], is_arrival=True)
            if len(trayectoria) > 1:
                folium.PolyLine(locations=trayectoria, color="#00FFFF", weight=1.5, opacity=0.4).add_to(m)
                
    if flujo in ["Salidas", "Llegadas y Salidas"]:
        for _, row in df_sal.iterrows():
            trayectoria = extract_trajectory(row['route'], row['adep'], row['ades'], is_arrival=False)
            if len(trayectoria) > 1:
                folium.PolyLine(locations=trayectoria, color="#FF0000", weight=1.5, opacity=0.4).add_to(m)
                
    folium.CircleMarker(
        location=[21.0366, -86.8770], radius=5, color="white", fill=True, fill_color="white", popup="MMUN"
    ).add_to(m)
    
    st_folium(m, width=900, height=600)
