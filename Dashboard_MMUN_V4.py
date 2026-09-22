import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import re
import base64

st.set_page_config(page_title="Dashboard Ejecutivo ATFM - SENEAM V6", page_icon="Seneam_Logo.png", layout="wide")

def get_base64_of_bin_file(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            return base64.b64encode(f.read()).decode()
    except: return None

img_base64 = get_base64_of_bin_file('Seneam_Logo.png')
logo_html = f'<img src="data:image/png;base64,{img_base64}" style="height: 60px; vertical-align: middle; margin-right: 15px;">' if img_base64 else ""

st.markdown("""
    <style>
    /* Forzar fondo oscuro absoluto contra el Modo Claro del sistema operativo */
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background-color: #0c2340 !important;
    }
    
    h1 {color: #FFFFFF !important; font-family: 'Helvetica Neue', sans-serif; display: flex; align-items: center;}
    p, .stSelectbox label p, .stRadio label p, div[role="radiogroup"] label div {color: #FFFFFF !important; font-weight: bold;}
    
    /* Mantener el texto oscuro dentro de las cajas de selección para que sea legible */
    div[data-baseweb="select"] span {color: #000000 !important;}
    </style>
""", unsafe_allow_html=True)

st.markdown(f"<h1>{logo_html} Análisis Dinámico de Rutas RNAV/PBN - MMUN</h1>", unsafe_allow_html=True)
st.markdown("**Fuente de Datos:** Registros TopSky (Llegadas y Salidas) | **Periodo:** Septiembre 2026")
st.markdown("<hr style='border: 1px solid #00FFFF;'>", unsafe_allow_html=True)

COORDENADAS = {
    'CUN': (21.036667, -86.876944),
        'MMUN': (21.036667, -86.876944),
        'VOMAR': (22.0833, -87.8833),
        'URTEL': (22.3833, -88.5833),
        'MATOL': (22.7500, -89.4667),
        'NOSAT': (21.4667, -86.3167),
        'CTM': (18.5092, -88.3336),
        'DUTNA': (24.5000, -91.3347),
        'DUTRO': (28.8308, -106.9019),
        'GOTAS': (19.2944, -95.0577),
        'ILUBA': (20.1894, -85.3413),
        'IRDOV': (24.5000, -88.2058),
        'KEHLI': (24.4861, -89.8401),
        'LIDAM': (21.9797, -95.0000),
        'MMCM': (18.5047, -88.3267),
        'MMCZ': (20.5224, -86.9255),
        'MMMD': (20.9370, -89.6577),
        'MMTG': (16.5616, -93.0257),
        'MMVA': (17.9970, -92.8173),
        'MZBZ': (17.5391, -88.3081),
        'PISAD': (24.2886, -87.1402),
        'SIGMA': (19.6172, -86.3666),
        'XHOL': (21.5197, -87.3827),
        'IPSEV': (24.5000, -92.5336),
        'MMTL': (20.1606, -87.6385),
        'NOREL': (19.0352, -95.1341),
        'OMPAN': (19.4905, -95.0000),
        'XUDUN': (21.3697, -88.4213),
        'AMIDA': (18.6294, -87.3016),
        'ERDAM': (21.2416, -87.0132),
        'MYDIA': (24.0405, -86.1583),
        'UDGUV': (20.8072, -87.7747),
        'KNOST': (28.0007, -83.4233),
        'UBVOV': (20.7450, -95.0000),
        'CAMJO': (30.5088, -82.6863),
        'NOTEN': (23.2852, -94.6258),
        'NUDAL': (21.2633, -85.6203),
        'TAKUX': (20.0270, -85.8960),
        'PAULE': (19.4655, -87.2434)
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

def limpiar_datos(df, columna_filtro):
    if df is not None and not df.empty and columna_filtro in df.columns:
        return df[df[columna_filtro].apply(lambda x: isinstance(x, str) and len(str(x)) == 4)]
    return pd.DataFrame()

@st.cache_data
def cargar_datos_dia(dia_seleccionado):
    try:
        df_lleg_bruto = pd.read_excel('lleg_MMUN_sept_2026.xlsx', sheet_name=dia_seleccionado)
        df_sal_bruto = pd.read_excel('sal_MMUN_sept_2026.xlsx', sheet_name=dia_seleccionado)
        
        df_lleg = limpiar_datos(df_lleg_bruto, 'adep')
        df_sal = limpiar_datos(df_sal_bruto, 'ades')
        return df_lleg, df_sal
    except Exception as e:
        return None, None

try:
    xls = pd.ExcelFile('lleg_MMUN_sept_2026.xlsx')
    dias_disponibles = [hoja for hoja in xls.sheet_names if hoja.startswith('2026-')]
except:
    st.error("Archivos Excel no encontrados.")
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
    tiles_url = 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}'
    attr = 'Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ'
    
    m = folium.Map(location=[21.0366, -86.8770], zoom_start=5, tiles=tiles_url, attr=attr)
    
    if flujo in ["Llegadas", "Llegadas y Salidas"] and not df_lleg.empty:
        for _, row in df_lleg.iterrows():
            trayectoria = extract_trajectory(row['route'], row.get('adep', ''), row.get('ades', ''), is_arrival=True)
            if len(trayectoria) > 1: folium.PolyLine(locations=trayectoria, color="#00FFFF", weight=1.5, opacity=0.4).add_to(m)
                
    if flujo in ["Salidas", "Llegadas y Salidas"] and not df_sal.empty:
        for _, row in df_sal.iterrows():
            trayectoria = extract_trajectory(row['route'], row.get('adep', ''), row.get('ades', ''), is_arrival=False)
            if len(trayectoria) > 1: folium.PolyLine(locations=trayectoria, color="#FF0000", weight=1.5, opacity=0.4).add_to(m)
                
    folium.CircleMarker(location=[21.0366, -86.8770], radius=5, color="white", fill=True, fill_color="white", popup="MMUN").add_to(m)
    
    # --- Añadir Waypoints Destacados ---
    waypoints_cyan = ['VOMAR', 'XUDUN', 'NOSAT', 'PAULE', 'SIGMA']
    waypoints_blancos = [
        'URTEL', 'MATOL', 'CTM', 'DUTNA', 'DUTRO', 'GOTAS', 'ILUBA', 'IRDOV', 
        'KEHLI', 'LIDAM', 'MMCZ', 'MMMD', 'MMTG', 'MMVA', 'MZBZ', 'PISAD', 
        'IPSEV', 'MMTL', 'NOREL', 'OMPAN', 'AMIDA', 'ERDAM', 'MYDIA', 'UDGUV', 
        'KNOST', 'UBVOV', 'CAMJO', 'NOTEN', 'NUDAL', 'TAKUX'
    ]
    
    # Unificar la lista para iterar, asignando color de texto
    todos_waypoints = [(wp, '#00FFFF') for wp in waypoints_cyan] + [(wp, '#FFFFFF') for wp in waypoints_blancos]
    
    for wp, txt_color in todos_waypoints:
        if wp in COORDENADAS:
            lat, lon = COORDENADAS[wp]
            # Añadir el triángulo gris claro usando DivIcon con HTML
            icono_triangulo = folium.DivIcon(
                html=f'<div style="width: 0; height: 0; border-left: 6px solid transparent; border-right: 6px solid transparent; border-bottom: 12px solid #D3D3D3; transform: translate(-50%, -50%);"></div>'
            )
            folium.Marker(location=[lat, lon], icon=icono_triangulo).add_to(m)
            
            # Añadir el nombre del waypoint con tipografía de mapa y el color asignado
            icono_texto = folium.DivIcon(
                html=f'<div style="font-family: \'Helvetica Neue\', Arial, Helvetica, sans-serif; font-size: 10px; font-weight: bold; color: {txt_color}; text-shadow: 1px 1px 2px black; transform: translate(-50%, 8px); white-space: nowrap;">{wp}</div>'
            )
            folium.Marker(location=[lat, lon], icon=icono_texto).add_to(m)

    st_folium(m, width=900, height=600)
