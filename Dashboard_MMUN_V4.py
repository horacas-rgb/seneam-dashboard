import os
import re
import base64
import requests
import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium
import plotly.express as px

# Configuración de página con Sidebar desplegada por defecto
st.set_page_config(
    page_title="Dashboard Ejecutivo ATFM - SENEAM V7",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- MANEJO SEGURO DE ESTADO DE BÚSQUEDA ---
# 1. Inicializar la clave del widget
if "search_callsign_input" not in st.session_state:
    st.session_state["search_callsign_input"] = ""

# 2. Si se activó la bandera de reseteo (por clic en el mapa), limpiamos ANTES de declarar el text_input
if st.session_state.get("reset_search_flag", False):
    st.session_state["search_callsign_input"] = ""
    st.session_state["reset_search_flag"] = False

# Función callback para el botón "Limpiar"
def limpiar_busqueda_callback():
    st.session_state["search_callsign_input"] = ""

def get_base64_of_bin_file(bin_file):
    try:
        if os.path.exists(bin_file):
            with open(bin_file, 'rb') as f:
                return base64.b64encode(f.read()).decode()
    except Exception:
        pass
    return None

img_base64 = get_base64_of_bin_file('Seneam_Logo.png')
logo_html = f'<img src="data:image/png;base64,{img_base64}" style="height: 60px; vertical-align: middle; margin-right: 15px;">' if img_base64 else ""

# Estilos CSS
st.markdown("""
    <style>
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] { 
        background-color: #0c2340 !important; 
    }
    
    [data-testid="stSidebar"] {
        background-color: #08172c !important;
        border-right: 1px solid #00FFFF !important;
    }

    h1 { color: #FFFFFF !important; font-family: 'Helvetica Neue', sans-serif; display: flex; align-items: center; }
    h2, h3, h4 { color: #FFFFFF !important; font-family: 'Helvetica Neue', sans-serif; }
    
    [data-testid="stSidebar"] .stRadio label p, 
    [data-testid="stSidebar"] .stCheckbox label p,
    [data-testid="stSidebar"] .stSelectbox label p,
    .stSelectbox label p,
    .stTextInput label p {
        color: #FFFFFF !important; 
        font-size: 18px !important;
        font-weight: 700 !important;
    }

    div[data-baseweb="select"] span, 
    div[data-baseweb="select"] input, 
    ul[data-baseweb="menu"] li {
        color: #000000 !important; 
        font-size: 18px !important;
        font-weight: bold !important;
    }

    .stTextInput input {
        color: #000000 !important;
        font-size: 18px !important;
        font-weight: bold !important;
        background-color: #FFFFFF !important;
        border-radius: 5px !important;
    }

    .stAlert p, div[data-testid="stNotification"] p {
        font-size: 18px !important;
        font-weight: bold !important;
    }
    
    iframe {
        width: 100% !important;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown(f"<h1>{logo_html} Mapa Dinámico de Trayectorias de Vuelo Aeropuerto de Cancún</h1>", unsafe_allow_html=True)
st.markdown("**Fuente de Datos:** Registros TopSky (Llegadas y Salidas)")
st.markdown("<hr style='border: 1px solid #00FFFF;'>", unsafe_allow_html=True)

COORDENADAS = {
    'CUN': (21.036667, -86.876944), 'MMUN': (21.036667, -86.876944),
    'VOMAR': (22.0833, -87.8833), 'URTEL': (22.3833, -88.5833), 'MATOL': (22.7500, -89.4667),
    'NOSAT': (21.4667, -86.3167), 'CTM': (18.5092, -88.3336), 'DUTNA': (24.5000, -91.3347),
    'DUTRO': (28.8308, -106.9019), 'GOTAS': (19.2944, -95.0577), 'ILUBA': (20.1894, -85.3413),
    'IRDOV': (24.5000, -88.2058), 'KEHLI': (24.4861, -89.8401), 'LIDAM': (21.9797, -95.0000),
    'MMCM': (18.5047, -88.3267), 'MMCZ': (20.5224, -86.9255), 'MMMD': (20.9370, -89.6577),
    'MMTG': (16.5616, -93.0257), 'MMVA': (17.9970, -92.8173), 'MZBZ': (17.5391, -88.3081),
    'PISAD': (24.2886, -87.1402), 'SIGMA': (19.6172, -86.3666), 'XHOL': (21.5197, -87.3827),
    'IPSEV': (24.5000, -92.5336), 'MMTL': (20.1606, -87.6385), 'NOREL': (19.0352, -95.1341),
    'OMPAN': (19.4905, -95.0000), 'XUDUN': (21.3697, -88.4213), 'AMIDA': (18.6294, -87.3016),
    'ERDAM': (21.2416, -87.0132), 'MYDIA': (24.0405, -86.1583), 'UDGUV': (20.8072, -87.7747),
    'KNOST': (28.0007, -83.4233), 'UBVOV': (20.7450, -95.0000), 'CAMJO': (30.5088, -82.6863),
    'NOTEN': (23.2852, -94.6258), 'NUDAL': (21.2633, -85.6203), 'TAKUX': (20.0270, -85.8960),
    'PAULE': (19.4655, -87.2434)
}

NOMBRES_AEROLINEAS = {
    'VMT': 'VivaAerobus (VMT)', 'VIV': 'VivaAerobus (VIV)',
    'VOI': 'Volaris (VOI)',     'AMX': 'Aeroméxico (AMX)',
    'SLI': 'Aeroméxico Connect (SLI)', 'AAL': 'American Airlines (AAL)',
    'UAL': 'United Airlines (UAL)',   'DAL': 'Delta Air Lines (DAL)',
    'JBU': 'JetBlue (JBU)',           'NKS': 'Spirit Airlines (NKS)',
    'SWR': 'Discover / Swiss (SWR)',   'BAW': 'British Airways (BAW)',
    'AFR': 'Air France (AFR)',        'WJA': 'WestJet (WJA)',
    'ACA': 'Air Canada (ACA)',        'SWA': 'Southwest (SWA)'
}

def parse_coord(coord_str):
    if not isinstance(coord_str, str):
        return None
    match = re.match(r'^(\d{2})(\d{2})?(N|S)(\d{3})(\d{2})?(E|W)$', coord_str.strip())
    if match:
        lat = float(match.group(1)) + (float(match.group(2)) if match.group(2) else 0) / 60.0
        if match.group(3) == 'S': lat = -lat
        lon = float(match.group(4)) + (float(match.group(5)) if match.group(5) else 0) / 60.0
        if match.group(6) == 'W': lon = -lon
        return (lat, lon)
    return None

def extract_trajectory(route_string, adep, ades, is_arrival):
    path = []
    adep_clean = str(adep).strip().upper() if pd.notna(adep) else ""
    ades_clean = str(ades).strip().upper() if pd.notna(ades) else ""

    if is_arrival and adep_clean in COORDENADAS:
        path.append(COORDENADAS[adep_clean])
    elif not is_arrival:
        path.append(COORDENADAS['MMUN'])
        
    if pd.notna(route_string):
        words = str(route_string).replace('/', ' ').split()
        for word in words:
            word_clean = word.strip().upper()
            coord = parse_coord(word_clean)
            if coord:
                path.append(coord)
            elif word_clean in COORDENADAS:
                path.append(COORDENADAS[word_clean])
                
    if is_arrival:
        path.append(COORDENADAS['MMUN'])
    elif not is_arrival and ades_clean in COORDENADAS:
        path.append(COORDENADAS[ades_clean])
        
    return path

def construir_popup_html(row, es_llegada=True):
    callsign = row.get('callsign', 'N/A')
    ac_type = row.get('aircraft_type', 'N/A')
    adep = row.get('adep', 'N/A')
    ades = row.get('ades', 'N/A')
    route = row.get('route', 'Directo / No especificada')
    
    nivel = row.get('entry_level', row.get('rfl', 'N/A'))
    if pd.notna(nivel):
        nivel_str = f"FL{int(float(nivel))}" if str(nivel).replace('.','',1).isdigit() else str(nivel)
    else:
        nivel_str = "N/A"
        
    if es_llegada:
        hora_label = "ATA (Actual Time of Arrival)"
        hora_val = row.get('ata', 'N/A')
    else:
        hora_label = "ATD (Actual Time of Departure)"
        hora_val = row.get('atd', row.get('ata', 'N/A'))
        
    if pd.notna(hora_val):
        hora_str = str(hora_val).split()[-1] if ' ' in str(hora_val) else str(hora_val)
    else:
        hora_str = "N/A"

    tipo_flujo = "LLEGADA" if es_llegada else "SALIDA"
    color_header = "#00FFFF" if es_llegada else "#FF4D4D"

    html = f"""
    <div style="font-family: Arial, sans-serif; font-size: 11px; width: 230px; color: #333;">
        <div style="background-color: {color_header}; padding: 5px; text-align: center; font-weight: bold; color: #0c2340; border-radius: 3px 3px 0 0;">
            ✈️ {callsign} ({tipo_flujo})
        </div>
        <table style="width: 100%; border-collapse: collapse; margin-top: 5px;">
            <tr><td><b>Tipo Aeronave:</b></td><td>{ac_type}</td></tr>
            <tr><td><b>ADEP - ADES:</b></td><td>{adep} ➔ {ades}</td></tr>
            <tr><td><b>Nivel Entrada:</b></td><td>{nivel_str}</td></tr>
            <tr><td><b>{hora_label}:</b></td><td><b>{hora_str} UTC</b></td></tr>
        </table>
        <div style="margin-top: 6px; padding-top: 4px; border-top: 1px solid #ccc; font-size: 10px; word-wrap: break-word;">
            <b>Ruta:</b> <span style="color: #05508a;">{route}</span>
        </div>
    </div>
    """
    return html

def limpiar_datos(df, columna_filtro):
    if df is not None and not df.empty and columna_filtro in df.columns:
        return df[df[columna_filtro].astype(str).str.strip().str.len() == 4].copy()
    return pd.DataFrame()

@st.cache_data(ttl=3600)
def obtener_dias_disponibles(archivo):
    if not os.path.exists(archivo):
        return []
    try:
        xls = pd.ExcelFile(archivo)
        return sorted([hoja for hoja in xls.sheet_names if hoja.startswith('2026-')])
    except Exception:
        return []

@st.cache_data(ttl=3600)
def cargar_datos_dia(archivo_lleg, archivo_sal, dia_seleccionado):
    df_lleg, df_sal = pd.DataFrame(), pd.DataFrame()
    if os.path.exists(archivo_lleg):
        try:
            df_lleg = limpiar_datos(pd.read_excel(archivo_lleg, sheet_name=dia_seleccionado), 'adep')
        except Exception:
            pass
    if os.path.exists(archivo_sal):
        try:
            df_sal = limpiar_datos(pd.read_excel(archivo_sal, sheet_name=dia_seleccionado), 'ades')
        except Exception:
            pass
    return df_lleg, df_sal

@st.cache_data(ttl=3600)
def cargar_coordenadas_espacio_aereo(archivo_excel):
    if not os.path.exists(archivo_excel):
        return {}
    try:
        xls = pd.ExcelFile(archivo_excel)
        dict_espacio = {}
        for hoja in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=hoja)
            if 'Área / Sector' in df.columns and 'Latitud (Decimal)' in df.columns and 'Longitud (Decimal)' in df.columns:
                dict_espacio[hoja] = df
        return dict_espacio
    except Exception:
        return {}

def obtener_top_10_aerolineas_ordenadas(df_lleg, df_sal, flujo):
    callsigns = []
    if flujo in ["Llegadas", "Llegadas y Salidas"] and df_lleg is not None and not df_lleg.empty and 'callsign' in df_lleg.columns:
        callsigns.extend(df_lleg['callsign'].dropna().astype(str).str.strip().str[:3].tolist())
    if flujo in ["Salidas", "Llegadas y Salidas"] and df_sal is not None and not df_sal.empty and 'callsign' in df_sal.columns:
        callsigns.extend(df_sal['callsign'].dropna().astype(str).str.strip().str[:3].tolist())
    
    if not callsigns:
        return []
    
    s = pd.Series(callsigns)
    top_codes = s.value_counts().head(10).index.tolist()
    
    opciones = []
    for code in top_codes:
        nombre_ext = NOMBRES_AEROLINEAS.get(code, f"Aerolínea ({code})")
        opciones.append((code, nombre_ext))
    return opciones

def generar_grafica_operaciones(df_lleg, df_sal, flujo, dia_seleccionado):
    try:
        datos = []
        if flujo in ["Llegadas", "Llegadas y Salidas"] and df_lleg is not None and not df_lleg.empty:
            df_lleg_c = df_lleg.copy()
            df_lleg_c['Hora'] = pd.to_datetime(df_lleg_c['ata'], errors='coerce').dt.hour
            c = df_lleg_c['Hora'].value_counts().sort_index().reset_index()
            c.columns = ['Hora', 'Operaciones']
            c['Tipo'] = 'Llegadas'
            datos.append(c)
            
        if flujo in ["Salidas", "Llegadas y Salidas"] and df_sal is not None and not df_sal.empty:
            df_sal_c = df_sal.copy()
            col_hora = 'atd' if 'atd' in df_sal_c.columns else 'ata'
            df_sal_c['Hora'] = pd.to_datetime(df_sal_c[col_hora], errors='coerce').dt.hour
            c = df_sal_c['Hora'].value_counts().sort_index().reset_index()
            c.columns = ['Hora', 'Operaciones']
            c['Tipo'] = 'Salidas'
            datos.append(c)
            
        if not datos: 
            return None
            
        df_final = pd.concat(datos).dropna(subset=['Hora'])
        df_final['Hora_Etiqueta'] = df_final['Hora'].astype(int).astype(str).str.zfill(2) + ":00"
        
        fig = px.bar(
            df_final, x='Hora_Etiqueta', y='Operaciones', color='Tipo', barmode='group',
            title=f"Volumen Operativo por Hora - MMUN ({dia_seleccionado})",
            color_discrete_map={'Llegadas': '#00FFFF', 'Salidas': '#FF0000'}
        )
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', 
            font_color='white', title_font=dict(color='white', size=18), 
            xaxis_title="Hora (UTC)"
        )
        return fig
    except Exception:
        return None

def agrupar_datos(df_lleg, df_sal, flujo, col_l, col_s, nom, top_n=None, substr=None):
    datos = []
    if flujo in ["Llegadas", "Llegadas y Salidas"] and df_lleg is not None and not df_lleg.empty and col_l in df_lleg.columns:
        d = df_lleg[[col_l]].dropna().copy()
        d.columns = [nom]
        d['Tipo'] = 'Llegadas'
        datos.append(d)
    if flujo in ["Salidas", "Llegadas y Salidas"] and df_sal is not None and not df_sal.empty and col_s in df_sal.columns:
        d = df_sal[[col_s]].dropna().copy()
        d.columns = [nom]
        d['Tipo'] = 'Salidas'
        datos.append(d)
    if not datos: 
        return None
    
    df_f = pd.concat(datos)
    df_f[nom] = df_f[nom].astype(str).str.strip()
    if substr: 
        df_f[nom] = df_f[nom].str[:substr]
    if top_n:
        top = df_f[nom].value_counts().head(top_n).index
        df_f = df_f[df_f[nom].isin(top)]
    return df_f.groupby([nom, 'Tipo']).size().reset_index(name='Operaciones')

def generar_grafica_barras(df_res, x_col, titulo):
    if df_res is None or df_res.empty: 
        return None
    fig = px.bar(
        df_res, x=x_col, y='Operaciones', color='Tipo', barmode='group', title=titulo,
        color_discrete_map={'Llegadas': '#00FFFF', 'Salidas': '#FF0000'}
    )
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', 
        font_color='white', title_font=dict(color='white', size=16), 
        margin=dict(t=50, b=10)
    )
    return fig

# ===================== BARRA LATERAL (FILTROS) =====================
with st.sidebar:
    st.markdown("<h2 style='color: #FFFFFF;'>Filtros Operativos</h2>", unsafe_allow_html=True)
    
    meses_disponibles = ["Noviembre", "Octubre", "Septiembre"]
    mes_seleccionado = st.selectbox("Seleccione el Mes:", meses_disponibles)
    
    mapa_archivos = {
        "Noviembre":  ('lleg_MMUN_nov_2026_MASTER.xlsx',  'sal_MMUN_nov_2026_MASTER.xlsx'),
        "Octubre":    ('lleg_MMUN_oct_2026_MASTER.xlsx',  'sal_MMUN_oct_2026_MASTER.xlsx'),
        "Septiembre": ('lleg_MMUN_sept_2026_MASTER.xlsx', 'sal_MMUN_sept_2026_MASTER.xlsx')
    }
    
    arch_lleg, arch_sal = mapa_archivos[mes_seleccionado]
        
    dias_disponibles = obtener_dias_disponibles(arch_lleg)
    if not dias_disponibles:
        st.error(f"No se encontró el archivo máster '{arch_lleg}'.")
        st.stop()
        
    dia_seleccionado = st.selectbox("Seleccione el Día:", dias_disponibles)
    flujo = st.radio("Flujo de Tránsito:", ["Llegadas", "Salidas", "Llegadas y Salidas"])
    
    st.markdown("<h3 style='color: #FFFFFF;'>Capas de Espacio Aéreo</h3>", unsafe_allow_html=True)
    mostrar_firs = st.checkbox("Ver FIRs", value=True)
    mostrar_acc_mid = st.checkbox("ACC Mérida", value=True)
    mostrar_acc_mty = st.checkbox("ACC Monterrey", value=False)
    mostrar_acc_mex = st.checkbox("ACC México", value=False)
    mostrar_acc_mzt = st.checkbox("ACC Mazatlán", value=False)
    
    df_lleg, df_sal = cargar_datos_dia(arch_lleg, arch_sal, dia_seleccionado)
    dict_espacio = cargar_coordenadas_espacio_aereo('Coordenadas_Espacio_Aereo_SENEAM.xlsx')
    
    total_llegadas = len(df_lleg) if df_lleg is not None else 0
    total_salidas = len(df_sal) if df_sal is not None else 0
    
    st.markdown("<h3 style='color: #FFFFFF;'>Resumen Estadístico</h3>", unsafe_allow_html=True)
    if flujo == "Llegadas y Salidas":
        st.info(f"Total de operaciones: **{total_llegadas + total_salidas}**")
        st.markdown(f"<p style='color: white;'>- Llegadas: {total_llegadas}</p>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: white;'>- Salidas: {total_salidas}</p>", unsafe_allow_html=True)
    elif flujo == "Llegadas": 
        st.info(f"Total de Llegadas: **{total_llegadas}**")
    else: 
        st.info(f"Total de Salidas: **{total_salidas}**")

# ===================== VISTA PRINCIPAL (MAPA & BÚSQUEDA) =====================

col_filtro_aero, col_search, col_reset = st.columns([2.5, 1.5, 0.8])

with col_filtro_aero:
    opcion_todas = f"Todas las {flujo}"
    top_10_tuples = obtener_top_10_aerolineas_ordenadas(df_lleg, df_sal, flujo)
    lista_opciones_str = [opcion_todas] + [nombre_ext for code, nombre_ext in top_10_tuples]
    
    st.markdown("<h4 style='color: #FFFFFF;'>✈️ Seleccione Aerolínea:</h4>", unsafe_allow_html=True)
    aerolinea_seleccionada_str = st.selectbox(
        label="Filtro de Aerolíneas",
        options=lista_opciones_str,
        index=0,
        key="select_aerolinea_flujo",
        label_visibility="collapsed"
    )

with col_search:
    st.markdown("<h4 style='color: #FFFFFF;'>🔍 Search Callsign:</h4>", unsafe_allow_html=True)
    
    # Campo de texto instanciado con la clave oficial de sesión
    st.text_input(
        label="Buscar vuelo por matrícula",
        key="search_callsign_input",
        placeholder="Ej: VIV2015, AMX...",
        label_visibility="collapsed"
    )

with col_reset:
    st.markdown("<h4 style='color: transparent;'>Clean</h4>", unsafe_allow_html=True)
    # Uso seguro de callback 'on_click'
    st.button("❌ Limpiar", key="btn_clear_search", on_click=limpiar_busqueda_callback)

search_callsign = st.session_state["search_callsign_input"].strip().upper()

codigo_seleccionado = "TODAS"
for code, nombre_ext in top_10_tuples:
    if nombre_ext == aerolinea_seleccionada_str:
        codigo_seleccionado = code
        break

# Inicializar Mapa Folium
tiles_url = 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}'
attr = 'Tiles &copy; Esri'

m = folium.Map(location=[21.0366, -86.8770], zoom_start=6, tiles=tiles_url, attr=attr)

# FUSIÓN ALGORÍTMICA SECTORIZADA
url_geojson = "https://raw.githubusercontent.com/johan/world.geo.json/master/countries/MEX.geo.json"
dict_espacio_procesado = {}

try:
    mexico_frontera = requests.get(url_geojson).json()
    coords_fisicas = []
    for feature in mexico_frontera['features']:
        geom = feature['geometry']
        if geom['type'] == 'MultiPolygon':
            largest_poly = max(geom['coordinates'], key=lambda poly: len(poly[0]))
            coords_fisicas = largest_poly[0]
        elif geom['type'] == 'Polygon':
            coords_fisicas = geom['coordinates'][0]
            
    def distance(p1, p2): return (p1[0]-p2[0])**2 + (p1[1]-p2[1])**2
    def get_border_slice(lon1, lat1, lon2, lat2):
        idx1 = min(range(len(coords_fisicas)), key=lambda i: distance(coords_fisicas[i], [lon1, lat1]))
        idx2 = min(range(len(coords_fisicas)), key=lambda i: distance(coords_fisicas[i], [lon2, lat2]))
        if idx1 <= idx2:
            slice_a = coords_fisicas[idx1:idx2+1]
            slice_b = coords_fisicas[idx2:] + coords_fisicas[:idx1+1]
        else:
            slice_a = coords_fisicas[idx1:] + coords_fisicas[:idx2+1]
            slice_b = coords_fisicas[idx2:idx1+1]
        return slice_a if len(slice_a) < len(slice_b) else slice_b[::-1]

    def is_in_usa_border(lon, lat): return lat >= 25.8 and -118.0 <= lon <= -95.0
    def is_in_south_border(lon, lat): return lat <= 18.5 and -93.0 <= lon <= -87.0
        
    for nombre_hoja, df_sheet in dict_espacio.items():
        dict_espacio_procesado[nombre_hoja] = {}
        for sector_name, df_subsector in df_sheet.groupby('Área / Sector'):
            sector_coords = df_subsector[['Latitud (Decimal)', 'Longitud (Decimal)']].to_dict('records')
            new_coords = []
            n = len(sector_coords)
            
            for i in range(n):
                lat1, lon1 = sector_coords[i]['Latitud (Decimal)'], sector_coords[i]['Longitud (Decimal)']
                new_coords.append([lat1, lon1])
                next_i = (i + 1) % n
                lat2, lon2 = sector_coords[next_i]['Latitud (Decimal)'], sector_coords[next_i]['Longitud (Decimal)']
                
                if is_in_usa_border(lon1, lat1) and is_in_usa_border(lon2, lat2) and coords_fisicas:
                    b_slice = get_border_slice(lon1, lat1, lon2, lat2)
                    for p in b_slice[1:-1]: new_coords.append([p[1], p[0]])
                elif is_in_south_border(lon1, lat1) and is_in_south_border(lon2, lat2) and coords_fisicas:
                    b_slice = get_border_slice(lon1, lat1, lon2, lat2)
                    for p in b_slice[1:-1]: new_coords.append([p[1], p[0]])
            
            dict_espacio_procesado[nombre_hoja][sector_name] = pd.DataFrame(new_coords, columns=['Latitud (Decimal)', 'Longitud (Decimal)'])
except Exception as e:
    st.warning(f"Error en Fusión Algorítmica: {e}")
    for nombre_hoja, df_sheet in dict_espacio.items():
        dict_espacio_procesado[nombre_hoja] = {s: d for s, d in df_sheet.groupby('Área / Sector')}

# CAPA DE ESPACIO AÉREO
capa_espacio = folium.FeatureGroup(name="Límites de Espacio Aéreo")
for nombre_hoja, sectores in dict_espacio_procesado.items():
    is_fir = "FIR" in nombre_hoja
    if is_fir and not mostrar_firs: continue
    if not is_fir:
        if "Mérida" in nombre_hoja and not mostrar_acc_mid: continue
        if "Monterrey" in nombre_hoja and not mostrar_acc_mty: continue
        if "México" in nombre_hoja and not mostrar_acc_mex: continue
        if "Mazatlán" in nombre_hoja and not mostrar_acc_mzt: continue
    
    if "MÉXICO" in nombre_hoja.upper() and not is_fir:
        color_sector = "#2ECC71"
    elif "OCEÁNICA" in nombre_hoja.upper() or "OCEANICA" in nombre_hoja.upper():
        color_sector = "#FF5555"
    elif is_fir:
        color_sector = "#00FFFF"
    else:
        color_sector = "#00E5FF"
    
    for sector_name, df_sector in sectores.items():
        coords = list(zip(df_sector['Latitud (Decimal)'], df_sector['Longitud (Decimal)']))
        
        es_perimetro = "PERIMETRO" in str(sector_name).upper()
        weight = 2.5 if es_perimetro else 1.2
        fill_op = 0.03 if es_perimetro else (0.06 if "OCEÁNICA" in nombre_hoja.upper() else 0.08)
        
        folium.Polygon(
            locations=coords, color=color_sector, weight=weight, opacity=0.7, fill=True, fill_opacity=fill_op, 
            tooltip=f"Sector: {sector_name}"
        ).add_to(capa_espacio)
        
        if not es_perimetro and not is_fir:
            lats = [c[0] for c in coords]
            lons = [c[1] for c in coords]
            cent_lat, cent_lon = sum(lats)/len(lats), sum(lons)/len(lons)
            
            match = re.search(r'SEC\s*\d+', str(sector_name).upper())
            etiqueta_sector = match.group(0) if match else sector_name
            
            folium.map.Marker(
                [cent_lat, cent_lon],
                icon=folium.DivIcon(
                    icon_size=(60, 20),
                    icon_anchor=(30, 10),
                    html=f'<div style="font-size: 8pt; color: #E0FFFF; font-weight: bold; text-align: center; text-shadow: 1px 1px 2px black;">{etiqueta_sector}</div>'
                )
            ).add_to(capa_espacio)
            
capa_espacio.add_to(m)

# DIBUJO DE TRAYECTORIAS
capa_trayectorias = folium.FeatureGroup(name="Trayectorias de Vuelo")
vuelo_encontrado = False

if flujo in ["Llegadas", "Llegadas y Salidas"] and df_lleg is not None and not df_lleg.empty:
    for _, row in df_lleg.iterrows():
        callsign_full = str(row.get('callsign', '')).strip().upper()
        cs_prefix = callsign_full[:3]
        
        if search_callsign:
            if search_callsign not in callsign_full:
                continue
            vuelo_encontrado = True
        elif codigo_seleccionado != "TODAS" and cs_prefix != codigo_seleccionado:
            continue
                
        trayectoria = extract_trajectory(row.get('route', ''), row.get('adep', ''), row.get('ades', ''), is_arrival=True)
        if len(trayectoria) > 1: 
            popup_content = construir_popup_html(row, es_llegada=True)
            hora_ata = str(row.get('ata', '')).split()[-1] if pd.notna(row.get('ata')) else 'N/A'
            
            es_busqueda_activa = bool(search_callsign)
            ancho_linea = 3.5 if es_busqueda_activa else 1.5
            opacidad_linea = 0.95 if es_busqueda_activa else 0.4
            
            popup_obj = folium.Popup(popup_content, max_width=250, show=es_busqueda_activa)
            
            folium.PolyLine(
                locations=trayectoria, 
                color="#00FFFF", 
                weight=ancho_linea, 
                opacity=opacidad_linea,
                tooltip=f"Llegada: {callsign_full} (ATA: {hora_ata} UTC)",
                popup=popup_obj
            ).add_to(capa_trayectorias)

if flujo in ["Salidas", "Llegadas y Salidas"] and df_sal is not None and not df_sal.empty:
    for _, row in df_sal.iterrows():
        callsign_full = str(row.get('callsign', '')).strip().upper()
        cs_prefix = callsign_full[:3]
        
        if search_callsign:
            if search_callsign not in callsign_full:
                continue
            vuelo_encontrado = True
        elif codigo_seleccionado != "TODAS" and cs_prefix != codigo_seleccionado:
            continue
                
        trayectoria = extract_trajectory(row.get('route', ''), row.get('adep', ''), row.get('ades', ''), is_arrival=False)
        if len(trayectoria) > 1: 
            popup_content = construir_popup_html(row, es_llegada=False)
            hora_atd = str(row.get('atd', row.get('ata', ''))).split()[-1] if pd.notna(row.get('atd', row.get('ata'))) else 'N/A'
            
            es_busqueda_activa = bool(search_callsign)
            ancho_linea = 3.5 if es_busqueda_activa else 1.5
            opacidad_linea = 0.95 if es_busqueda_activa else 0.4
            
            popup_obj = folium.Popup(popup_content, max_width=250, show=es_busqueda_activa)
            
            folium.PolyLine(
                locations=trayectoria, 
                color="#FF0000", 
                weight=ancho_linea, 
                opacity=opacidad_linea,
                tooltip=f"Salida: {callsign_full} (ATD: {hora_atd} UTC)",
                popup=popup_obj
            ).add_to(capa_trayectorias)

capa_trayectorias.add_to(m)
folium.CircleMarker(location=[21.0366, -86.8770], radius=5, color="white", fill=True, fill_color="white", popup="MMUN").add_to(m)

folium.LayerControl().add_to(m)

# RENDERIZADO DEL MAPA Y CAPTURA DE CLIC PARA REINICIAR BÚSQUEDA
map_data = st_folium(m, use_container_width=True, height=700, returned_objects=["last_clicked"])

# Si se hace clic en el mapa estando en búsqueda activa, marcamos la bandera y refrescamos de forma segura
if map_data and map_data.get("last_clicked") is not None and search_callsign:
    st.session_state["reset_search_flag"] = True
    st.rerun()

if search_callsign and not vuelo_encontrado:
    st.warning(f"No se encontró ninguna operación registrada con el Callsign '{search_callsign}' en la fecha seleccionada.")

# ===================== PANEL DE GRÁFICAS =====================
st.markdown("<br><h2 style='color: #FFFFFF; text-align: center;'>Panel de Análisis Operativo</h2><hr style='border: 1px solid #333333;'>", unsafe_allow_html=True)

fig_hora = generar_grafica_operaciones(df_lleg, df_sal, flujo, dia_seleccionado)
if fig_hora: 
    st.plotly_chart(fig_hora, use_container_width=True)

col_graf_1, col_graf_2 = st.columns(2)

with col_graf_1:
    df_sec = agrupar_datos(df_lleg, df_sal, flujo, 'entry_sector', 'Sector_resuelto', 'Sector')
    fig_sec = generar_grafica_barras(df_sec, 'Sector', "Carga por Sector de Control")
    if fig_sec: st.plotly_chart(fig_sec, use_container_width=True)
        
    df_cia = agrupar_datos(df_lleg, df_sal, flujo, 'callsign', 'callsign', 'Aerolínea', top_n=10, substr=3)
    fig_cia = generar_grafica_barras(df_cia, 'Aerolínea', "Top 10 Aerolíneas (Volumen)")
    if fig_cia: st.plotly_chart(fig_cia, use_container_width=True)
    
    df_nivel = agrupar_datos(df_lleg, df_sal, flujo, 'rfl', 'rfl', 'Nivel de Vuelo (RFL)', top_n=10)
    fig_nivel = generar_grafica_barras(df_nivel, 'Nivel de Vuelo (RFL)', "Top 10 Niveles de Vuelo (RFL)")
    if fig_nivel: st.plotly_chart(fig_nivel, use_container_width=True)
    
    df_wtc = agrupar_datos(df_lleg, df_sal, flujo, 'wtc', 'wtc', 'Estela Turbulenta')
    fig_wtc = generar_grafica_barras(df_wtc, 'Estela Turbulenta', "Categoría de Estela Turbulenta (WTC)")
    if fig_wtc: st.plotly_chart(fig_wtc, use_container_width=True)

with col_graf_2:
    df_flota = agrupar_datos(df_lleg, df_sal, flujo, 'aircraft_type', 'aircraft_type', 'Aeronave', top_n=10)
    fig_flota = generar_grafica_barras(df_flota, 'Aeronave', "Mix de Flota (Top 10 Aeronaves)")
    if fig_flota: st.plotly_chart(fig_flota, use_container_width=True)
        
    df_pista = agrupar_datos(df_lleg, df_sal, flujo, 'arr_runway', 'dep_runway', 'Pista', top_n=3)
    fig_pista = generar_grafica_barras(df_pista, 'Pista', "Configuración de Pistas en Uso")
    if fig_pista: st.plotly_chart(fig_pista, use_container_width=True)
        
    df_punto = agrupar_datos(df_lleg, df_sal, flujo, 'entry_point', 'exit_point', 'Fijo de Ruta', top_n=10)
    fig_punto = generar_grafica_barras(df_punto, 'Fijo de Ruta', "Puntos de Transferencia (Top 10 Fijos)")
    if fig_punto: st.plotly_chart(fig_punto, use_container_width=True)
