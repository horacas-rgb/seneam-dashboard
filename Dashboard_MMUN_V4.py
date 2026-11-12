import os
import re
import base64
import datetime
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

# --- MANEJO SEGURO DE ESTADO DE BÚSQUEDA DE CALLSIGN ---
if "search_callsign_input" not in st.session_state:
    st.session_state["search_callsign_input"] = ""

if st.session_state.get("reset_search_flag", False):
    st.session_state["search_callsign_input"] = ""
    st.session_state["reset_search_flag"] = False

def limpiar_busqueda_callback():
    st.session_state["search_callsign_input"] = ""

@st.cache_data(ttl=86400)
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

# Estilos CSS personalizados (con corrección para el botón de la barra lateral)
st.markdown("""
    <style>
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] { 
        background-color: #0c2340 !important; 
    }
    
    [data-testid="stSidebar"] {
        background-color: #08172c !important;
        border-right: 1px solid #00FFFF !important;
    }

    /* Corrección para hacer visible el botón de colapsar/expandir la barra lateral */
    [data-testid="collapsedControl"] {
        color: #FFFFFF !important;
    }
    [data-testid="collapsedControl"] svg {
        fill: #FFFFFF !important;
        color: #FFFFFF !important;
    }

    h1 { color: #FFFFFF !important; font-family: 'Helvetica Neue', sans-serif; display: flex; align-items: center; }
    h2, h3, h4 { color: #FFFFFF !important; font-family: 'Helvetica Neue', sans-serif; }
    
    [data-testid="stSidebar"] .stRadio label p, 
    [data-testid="stSidebar"] .stCheckbox label p,
    [data-testid="stSidebar"] .stSelectbox label p,
    [data-testid="stSidebar"] .stDateInput label p,
    .stSelectbox label p,
    .stTextInput label p {
        color: #FFFFFF !important; 
        font-size: 18px !important;
        font-weight: 700 !important;
    }

    div[data-baseweb="select"] span, 
    div[data-baseweb="select"] input, 
    div[data-baseweb="input"] input,
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
    'MMTG': (16.5616, -93.0257), 'TGZ': (16.5616, -93.0257), 'MMVA': (17.9970, -92.8173),
    'MZBZ': (17.5391, -88.3081), 'PISAD': (24.2886, -87.1402), 'SIGMA': (19.6172, -86.3666),
    'XHOL': (21.5197, -87.3827), 'IPSEV': (24.5000, -92.5336), 'MMTL': (20.1606, -87.6385),
    'NOREL': (19.0352, -95.1341), 'OMPAN': (19.4905, -95.0000), 'XUDUN': (21.3697, -88.4213),
    'AMIDA': (18.6294, -87.3016), 'ERDAM': (21.2416, -87.0132), 'MYDIA': (24.0405, -86.1583),
    'UDGUV': (20.8072, -87.7747), 'KNOST': (28.0007, -83.4233), 'UBVOV': (20.7450, -95.0000),
    'CAMJO': (30.5088, -82.6863), 'NOTEN': (23.2852, -94.6258), 'NUDAL': (21.2633, -85.6203),
    'TAKUX': (20.0270, -85.8960), 'PAULE': (19.4655, -87.2434)
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
    if not isinstance(coord_str, str): return None
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

    if is_arrival and adep_clean in COORDENADAS: path.append(COORDENADAS[adep_clean])
    elif not is_arrival: path.append(COORDENADAS['MMUN'])
        
    if pd.notna(route_string):
        for word in str(route_string).replace('/', ' ').split():
            word_clean = word.strip().upper()
            coord = parse_coord(word_clean)
            if coord: path.append(coord)
            elif word_clean in COORDENADAS: path.append(COORDENADAS[word_clean])
                
    if is_arrival: path.append(COORDENADAS['MMUN'])
    elif not is_arrival and ades_clean in COORDENADAS: path.append(COORDENADAS[ades_clean])
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
    else: nivel_str = "N/A"
        
    if es_llegada:
        hora_label = "ATA (Actual Time of Arrival)"
        hora_val = row.get('ata', 'N/A')
    else:
        hora_label = "ATD (Actual Time of Departure)"
        hora_val = row.get('atd', row.get('ata', 'N/A'))
        
    hora_str = str(hora_val).split()[-1] if pd.notna(hora_val) and ' ' in str(hora_val) else str(hora_val) if pd.notna(hora_val) else "N/A"
    tipo_flujo = "LLEGADA" if es_llegada else "SALIDA"
    color_header = "#00FFFF" if es_llegada else "#FF4D4D"

    return f"""
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

def limpiar_datos(df, columna_filtro):
    if df is not None and not df.empty and columna_filtro in df.columns:
        return df[df[columna_filtro].astype(str).str.strip().str.len() == 4].copy()
    return pd.DataFrame()

MAPA_ARCHIVOS_MES = {
    1:  ('lleg_MMUN_ene_2026_MASTER.xlsx',  'sal_MMUN_ene_2026_MASTER.xlsx'),
    2:  ('lleg_MMUN_feb_2026_MASTER.xlsx',  'sal_MMUN_feb_2026_MASTER.xlsx'),
    3:  ('lleg_MMUN_mar_2026_MASTER.xlsx',  'sal_MMUN_mar_2026_MASTER.xlsx'),
    4:  ('lleg_MMUN_abr_2026_MASTER.xlsx',  'sal_MMUN_abr_2026_MASTER.xlsx'),
    5:  ('lleg_MMUN_may_2026_MASTER.xlsx',  'sal_MMUN_may_2026_MASTER.xlsx'),
    6:  ('lleg_MMUN_jun_2026_MASTER.xlsx',  'sal_MMUN_jun_2026_MASTER.xlsx'),
    7:  ('lleg_MMUN_jul_2026_MASTER.xlsx',  'sal_MMUN_jul_2026_MASTER.xlsx'),
    8:  ('lleg_MMUN_ago_2026_MASTER.xlsx',  'sal_MMUN_ago_2026_MASTER.xlsx'),
    9:  ('lleg_MMUN_sept_2026_MASTER.xlsx', 'sal_MMUN_sept_2026_MASTER.xlsx'),
    10: ('lleg_MMUN_oct_2026_MASTER.xlsx',  'sal_MMUN_oct_2026_MASTER.xlsx'),
    11: ('lleg_MMUN_nov_2026_MASTER.xlsx',  'sal_MMUN_nov_2026_MASTER.xlsx'),
    12: ('lleg_MMUN_dic_2026_MASTER.xlsx',  'sal_MMUN_dic_2026_MASTER.xlsx')
}

@st.cache_data(ttl=3600)
def obtener_registro_dias_disponibles():
    dias_dict = {}
    for m in range(1, 13):
        arch_l, arch_s = MAPA_ARCHIVOS_MES[m]
        if os.path.exists(arch_l):
            try:
                xls = pd.ExcelFile(arch_l)
                for sheet in xls.sheet_names:
                    if sheet.startswith('2026-'):
                        dias_dict[sheet] = (arch_l, arch_s)
            except Exception: pass
    return dias_dict

@st.cache_data(ttl=3600)
def cargar_datos_dia(archivo_lleg, archivo_sal, dia_seleccionado):
    df_lleg, df_sal = pd.DataFrame(), pd.DataFrame()
    if os.path.exists(archivo_lleg):
        try: df_lleg = limpiar_datos(pd.read_excel(archivo_lleg, sheet_name=dia_seleccionado), 'adep')
        except Exception: pass
    if os.path.exists(archivo_sal):
        try: df_sal = limpiar_datos(pd.read_excel(archivo_sal, sheet_name=dia_seleccionado), 'ades')
        except Exception: pass
    return df_lleg, df_sal

@st.cache_data(ttl=86400)
def cargar_coordenadas_espacio_aereo(archivo_excel):
    if not os.path.exists(archivo_excel): return {}
    try:
        xls = pd.ExcelFile(archivo_excel)
        dict_espacio = {}
        for hoja in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=hoja)
            if 'Área / Sector' in df.columns and 'Latitud (Decimal)' in df.columns and 'Longitud (Decimal)' in df.columns:
                dict_espacio[hoja] = df
        return dict_espacio
    except Exception: return {}

@st.cache_data(ttl=86400)
def cargar_waypoints_y_vors(archivo_excel):
    if not os.path.exists(archivo_excel): return pd.DataFrame()
    try:
        xls = pd.ExcelFile(archivo_excel)
        df_list = []
        if 'Aerovias_Waypoints' in xls.sheet_names:
            df1 = pd.read_excel(xls, sheet_name='Aerovias_Waypoints', header=3)[['Nombre del Punto Significativo / Waypoint', 'Latitud (Decimal)', 'Longitud (Decimal)']].dropna()
            df1.columns = ['Punto', 'Latitud', 'Longitud']
            df_list.append(df1)
        if 'Waypoints_Unicos' in xls.sheet_names:
            df2 = pd.read_excel(xls, sheet_name='Waypoints_Unicos', header=3)[['Nombre del Punto / Waypoint', 'Latitud (Decimal)', 'Longitud (Decimal)']].dropna()
            df2.columns = ['Punto', 'Latitud', 'Longitud']
            df_list.append(df2)
        if not df_list: return pd.DataFrame()
        df_all = pd.concat(df_list).dropna().reset_index(drop=True)
        df_all = pd.concat([df_all, pd.DataFrame([{'Punto': 'VOR TUXTLA (TGZ)', 'Latitud': 16.5616, 'Longitud': -93.0257}])], ignore_index=True)
        def clasificar_punto(row):
            s = str(row['Punto']).strip()
            return 'VOR / Radioayuda' if s.startswith('VOR') or (len(s)==3 and s.isalpha()) else 'Waypoint'
        def obtener_codigo_3_letras(row):
            s = str(row['Punto']).strip()
            match = re.search(r'\(([A-Z]{3})\)', s)
            if match: return match.group(1)
            if len(s) == 3 and s.isalpha(): return s.upper()
            if s.startswith('VOR '): return s.replace('VOR ', '').strip()[:3].upper()
            return s
        df_all['Tipo'] = df_all.apply(clasificar_punto, axis=1)
        df_all['Codigo_3L'] = df_all.apply(obtener_codigo_3_letras, axis=1)
        return df_all.drop_duplicates(subset=['Codigo_3L', 'Latitud', 'Longitud']).reset_index(drop=True)
    except Exception: return pd.DataFrame()

@st.cache_data(ttl=86400)
def obtener_frontera_mexico():
    url_geojson = "https://raw.githubusercontent.com/johan/world.geo.json/master/countries/MEX.geo.json"
    try:
        response = requests.get(url_geojson, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return None

def obtener_top_10_aerolineas_ordenadas(df_lleg, df_sal, flujo):
    callsigns = []
    if flujo in ["Llegadas", "Llegadas y Salidas"] and df_lleg is not None and not df_lleg.empty and 'callsign' in df_lleg.columns:
        callsigns.extend(df_lleg['callsign'].dropna().astype(str).str.strip().str[:3].tolist())
    if flujo in ["Salidas", "Llegadas y Salidas"] and df_sal is not None and not df_sal.empty and 'callsign' in df_sal.columns:
        callsigns.extend(df_sal['callsign'].dropna().astype(str).str.strip().str[:3].tolist())
    if not callsigns: return []
    top_codes = pd.Series(callsigns).value_counts().head(10).index.tolist()
    return [(code, NOMBRES_AEROLINEAS.get(code, f"Aerolínea ({code})")) for code in top_codes]

def generar_grafica_operaciones(df_lleg, df_sal, flujo, dia_seleccionado):
    try:
        datos = []
        if flujo in ["Llegadas", "Llegadas y Salidas"] and df_lleg is not None and not df_lleg.empty:
            df_lleg_c = df_lleg.copy()
            df_lleg_c['Hora'] = pd.to_datetime(df_lleg_c['ata'], errors='coerce').dt.hour
            c = df_lleg_c['Hora'].value_counts().sort_index().reset_index()
            c.columns, c['Tipo'] = ['Hora', 'Operaciones'], 'Llegadas'
            datos.append(c)
        if flujo in ["Salidas", "Llegadas y Salidas"] and df_sal is not None and not df_sal.empty:
            df_sal_c = df_sal.copy()
            df_sal_c['Hora'] = pd.to_datetime(df_sal_c['atd' if 'atd' in df_sal_c.columns else 'ata'], errors='coerce').dt.hour
            c = df_sal_c['Hora'].value_counts().sort_index().reset_index()
            c.columns, c['Tipo'] = ['Hora', 'Operaciones'], 'Salidas'
            datos.append(c)
        if not datos: return None
        df_final = pd.concat(datos).dropna(subset=['Hora'])
        df_final['Hora_Etiqueta'] = df_final['Hora'].astype(int).astype(str).str.zfill(2) + ":00"
        fig = px.bar(df_final, x='Hora_Etiqueta', y='Operaciones', color='Tipo', barmode='group',
                     title=f"Volumen Operativo por Hora - MMUN ({dia_seleccionado})",
                     color_discrete_map={'Llegadas': '#00FFFF', 'Salidas': '#FF0000'})
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='white', xaxis_title="Hora (UTC)")
        return fig
    except Exception: return None

def agrupar_datos(df_lleg, df_sal, flujo, col_l, col_s, nom, top_n=None, substr=None):
    datos = []
    if flujo in ["Llegadas", "Llegadas y Salidas"] and df_lleg is not None and not df_lleg.empty and col_l in df_lleg.columns:
        d = df_lleg[[col_l]].dropna().copy()
        d.columns, d['Tipo'] = [nom], 'Llegadas'
        datos.append(d)
    if flujo in ["Salidas", "Llegadas y Salidas"] and df_sal is not None and not df_sal.empty and col_s in df_sal.columns:
        d = df_sal[[col_s]].dropna().copy()
        d.columns, d['Tipo'] = [nom], 'Salidas'
        datos.append(d)
    if not datos: return None
    df_f = pd.concat(datos)
    df_f[nom] = df_f[nom].astype(str).str.strip()
    if substr: df_f[nom] = df_f[nom].str[:substr]
    if top_n: df_f = df_f[df_f[nom].isin(df_f[nom].value_counts().head(top_n).index)]
    return df_f.groupby([nom, 'Tipo']).size().reset_index(name='Operaciones')

def generar_grafica_barras(df_res, x_col, titulo):
    if df_res is None or df_res.empty: return None
    fig = px.bar(df_res, x=x_col, y='Operaciones', color='Tipo', barmode='group', title=titulo,
                 color_discrete_map={'Llegadas': '#00FFFF', 'Salidas': '#FF0000'})
    fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='white', margin=dict(t=50, b=10))
    return fig

# ===================== BARRA LATERAL (FILTROS) =====================
with st.sidebar:
    st.markdown("<h2 style='color: #FFFFFF;'>Filtros Operativos</h2>", unsafe_allow_html=True)
    registro_dias = obtener_registro_dias_disponibles()
    lista_dias_str = sorted(list(registro_dias.keys()))
    if not lista_dias_str:
        st.error("No se encontraron hojas de días disponibles.")
        st.stop()
        
    fecha_defecto = datetime.datetime.strptime(lista_dias_str[-1], "%Y-%m-%d").date()
    fecha_seleccionada = st.date_input("Seleccione Fecha", value=fecha_defecto, min_value=datetime.date(2026, 1, 1), max_value=datetime.date(2026, 12, 31))
    dia_seleccionado_str = fecha_seleccionada.strftime("%Y-%m-%d")
    arch_lleg, arch_sal = registro_dias.get(dia_seleccionado_str, MAPA_ARCHIVOS_MES.get(fecha_seleccionada.month, ('lleg_MMUN_nov_2026_MASTER.xlsx', 'sal_MMUN_nov_2026_MASTER.xlsx')))

    flujo = st.radio("Flujo de Tránsito:", ["Llegadas", "Salidas", "Llegadas y Salidas"], index=0)
    
    st.markdown("<h3 style='color: #FFFFFF;'>Capas de Espacio Aéreo</h3>", unsafe_allow_html=True)
    mostrar_firs = st.checkbox("Ver FIRs", value=True)
    mostrar_acc_mid = st.checkbox("ACC Mérida", value=True)
    mostrar_acc_mty = st.checkbox("ACC Monterrey", value=False)
    mostrar_acc_mex = st.checkbox("ACC México", value=False)
    mostrar_acc_mzt = st.checkbox("ACC Mazatlán", value=False)
    
    st.markdown("<h3 style='color: #FFFFFF;'>Waypoints y VORs</h3>", unsafe_allow_html=True)
    mostrar_vors = st.checkbox("Mostrar VORs / Radioayudas", value=False)
    mostrar_waypoints = st.checkbox("Mostrar Waypoints (Fijos)", value=False)
    
    df_lleg, df_sal = cargar_datos_dia(arch_lleg, arch_sal, dia_seleccionado_str)
    dict_espacio = cargar_coordenadas_espacio_aereo('Coordenadas_Espacio_Aereo_SENEAM.xlsx')
    df_pts_enr = cargar_waypoints_y_vors('Coordenadas_Waypoints_ENR_3.3.xlsx')
    
    t_lleg = len(df_lleg) if df_lleg is not None else 0
    t_sal = len(df_sal) if df_sal is not None else 0
    
    st.markdown("<h3 style='color: #FFFFFF;'>Resumen Estadístico</h3>", unsafe_allow_html=True)
    if flujo == "Llegadas y Salidas":
        st.info(f"Total de operaciones: **{t_lleg + t_sal}**")
        st.markdown(f"<p style='color: white;'>- Llegadas: {t_lleg}</p><p style='color: white;'>- Salidas: {t_sal}</p>", unsafe_allow_html=True)
    elif flujo == "Llegadas": st.info(f"Total de Llegadas: **{t_lleg}**")
    else: st.info(f"Total de Salidas: **{t_sal}**")

# ===================== VISTA PRINCIPAL (MAPA & BÚSQUEDA) =====================
col_filtro_aero, col_search, col_reset = st.columns([2.5, 1.5, 0.8])
with col_filtro_aero:
    top_10_tuples = obtener_top_10_aerolineas_ordenadas(df_lleg, df_sal, flujo)
    lista_opciones_str = [f"Todas las {flujo}"] + [n for c, n in top_10_tuples]
    st.markdown("<h4 style='color: #FFFFFF;'>✈️ Seleccione Aerolínea:</h4>", unsafe_allow_html=True)
    aerolinea_seleccionada_str = st.selectbox("Filtro", options=lista_opciones_str, index=0, key="select_aerolinea_flujo", label_visibility="collapsed")
with col_search:
    st.markdown("<h4 style='color: #FFFFFF;'>🔍 Search Callsign:</h4>", unsafe_allow_html=True)
    st.text_input("Buscar", key="search_callsign_input", placeholder="Ej: VIV2015, AMX...", label_visibility="collapsed")
with col_reset:
    st.markdown("<h4 style='color: transparent;'>Clean</h4>", unsafe_allow_html=True)
    st.button("❌ Limpiar", key="btn_clear_search", on_click=limpiar_busqueda_callback)

search_callsign = st.session_state["search_callsign_input"].strip().upper()
codigo_seleccionado = next((c for c, n in top_10_tuples if n == aerolinea_seleccionada_str), "TODAS")

tiles_url = 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}'
m = folium.Map(location=[21.0366, -86.8770], zoom_start=6, tiles=tiles_url, attr='Tiles &copy; Esri')

# -------------------------------------------------------------------------
# FUSIÓN GEOGRÁFICA (LINESTRING EXACTO POR VECTORES)
# -------------------------------------------------------------------------
mexico_frontera = obtener_frontera_mexico()
dict_espacio_procesado = {}

try:
    if mexico_frontera and 'features' in mexico_frontera:
        coords_fisicas = []
        for feature in mexico_frontera['features']:
            geom = feature['geometry']
            if geom['type'] == 'MultiPolygon':
                coords_fisicas = max(geom['coordinates'], key=lambda poly: len(poly[0]))[0]
            elif geom['type'] == 'Polygon':
                coords_fisicas = geom['coordinates'][0]

        def distance_geo(p1, p2): return ((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)**0.5
        def find_closest_index(lon, lat, coords): return min(range(len(coords)), key=lambda i: distance_geo(coords[i], [lon, lat]))

        def get_path_length(indices, coords):
            return sum(distance_geo(coords[indices[i]], coords[indices[i+1]]) for i in range(len(indices)-1))

        def extract_line_string(idx_start, idx_end, coords):
            n = len(coords)
            sf = []; c = idx_start
            while True:
                sf.append(c)
                if c == idx_end or len(sf) > n: break
                c = (c + 1) % n
            sb = []; c = idx_start
            while True:
                sb.append(c)
                if c == idx_end or len(sb) > n: break
                c = (c - 1) % n
            return [coords[i] for i in (sf if get_path_length(sf, coords) < get_path_length(sb, coords) else sb)]

        idx_tj = find_closest_index(-117.12, 32.53, coords_fisicas)
        idx_mat = find_closest_index(-97.14, 25.95, coords_fisicas)
        usa_line = extract_line_string(idx_tj, idx_mat, coords_fisicas)

        idx_tap = find_closest_index(-92.21, 14.53, coords_fisicas)
        idx_xcalak = find_closest_index(-87.75, 18.15, coords_fisicas)
        south_line = extract_line_string(idx_tap, idx_xcalak, coords_fisicas)

        def is_on_line(lon, lat, line_coords, threshold=0.8):
            if not line_coords: return False
            return min(distance_geo([lon, lat], p) for p in line_coords) < threshold

        def get_subline(lon1, lat1, lon2, lat2, line_coords):
            i1, i2 = find_closest_index(lon1, lat1, line_coords), find_closest_index(lon2, lat2, line_coords)
            if i1 <= i2: return line_coords[i1:i2+1]
            else: return line_coords[i1:i2-1:-1] if i2 > 0 else line_coords[i1::-1]

        for nombre_hoja, df_sheet in dict_espacio.items():
            dict_espacio_procesado[nombre_hoja] = {}
            for sector_name, df_subsector in df_sheet.groupby('Área / Sector'):
                sector_coords = df_subsector[['Latitud (Decimal)', 'Longitud (Decimal)']].to_dict('records')
                new_coords = []
                num_pts = len(sector_coords)
                
                for i in range(num_pts):
                    lat1, lon1 = sector_coords[i]['Latitud (Decimal)'], sector_coords[i]['Longitud (Decimal)']
                    lat2, lon2 = sector_coords[(i + 1) % num_pts]['Latitud (Decimal)'], sector_coords[(i + 1) % num_pts]['Longitud (Decimal)']
                    new_coords.append([lat1, lon1])
                    
                    if is_on_line(lon1, lat1, usa_line) and is_on_line(lon2, lat2, usa_line):
                        for p in get_subline(lon1, lat1, lon2, lat2, usa_line)[1:-1]: new_coords.append([p[1], p[0]])
                    elif is_on_line(lon1, lat1, south_line) and is_on_line(lon2, lat2, south_line):
                        for p in get_subline(lon1, lat1, lon2, lat2, south_line)[1:-1]: new_coords.append([p[1], p[0]])

                dict_espacio_procesado[nombre_hoja][sector_name] = pd.DataFrame(new_coords, columns=['Latitud (Decimal)', 'Longitud (Decimal)'])
    else:
        raise Exception("No se pudo cargar el GeoJSON de la frontera.")
except Exception:
    for nombre_hoja, df_sheet in dict_espacio.items():
        dict_espacio_procesado[nombre_hoja] = {s: d for s, d in df_sheet.groupby('Área / Sector')}

# 1. CAPA DE ESPACIO AÉREO
capa_espacio = folium.FeatureGroup(name="Límites de Espacio Aéreo")
for nombre_hoja, sectores in dict_espacio_procesado.items():
    is_fir = "FIR" in nombre_hoja
    if is_fir and not mostrar_firs: continue
    if "UTA" in nombre_hoja.upper(): continue
    if not is_fir:
        if "Mérida" in nombre_hoja and not mostrar_acc_mid: continue
        if "Monterrey" in nombre_hoja and not mostrar_acc_mty: continue
        if "México" in nombre_hoja and not mostrar_acc_mex: continue
        if "Mazatlán" in nombre_hoja and not mostrar_acc_mzt: continue
    
    if "MÉXICO" in nombre_hoja.upper() and not is_fir: color_sector = "#2ECC71"
    elif "OCEÁNICA" in nombre_hoja.upper() or "OCEANICA" in nombre_hoja.upper(): color_sector = "#FF5555"
    elif is_fir: color_sector = "#00FFFF"
    else: color_sector = "#00E5FF"
    
    for sector_name, df_sector in sectores.items():
        coords = list(zip(df_sector['Latitud (Decimal)'], df_sector['Longitud (Decimal)']))
        if len(coords) < 3: continue
            
        es_perimetro = "PERIMETRO" in str(sector_name).upper()
        folium.Polygon(
            locations=coords, color=color_sector, weight=2.5 if es_perimetro else 1.2, opacity=0.7, fill=True, 
            fill_opacity=0.03 if es_perimetro else (0.06 if "OCEÁNICA" in nombre_hoja.upper() else 0.08), 
            tooltip=f"Sector: {sector_name}"
        ).add_to(capa_espacio)
        
        if not es_perimetro and not is_fir:
            match = re.search(r'SEC\s*\d+', str(sector_name).upper())
            etiq = match.group(0) if match else sector_name
            
            if "MERIDA SEC 1" in str(sector_name).upper():
                cent_lat, cent_lon = 17.50, -93.50
            else:
                cent_lat, cent_lon = sum([c[0] for c in coords])/len(coords), sum([c[1] for c in coords])/len(coords)
                
            folium.map.Marker(
                [cent_lat, cent_lon],
                icon=folium.DivIcon(icon_size=(60, 20), icon_anchor=(30, 10), html=f'<div style="font-size: 8pt; color: #E0FFFF; font-weight: bold; text-align: center; text-shadow: 1px 1px 2px black;">{etiq}</div>')
            ).add_to(capa_espacio)
capa_espacio.add_to(m)

# 2. CAPA DE WAYPOINTS Y VORs
if df_pts_enr is not None and not df_pts_enr.empty:
    capa_navaids = folium.FeatureGroup(name="Waypoints & Radioayudas")
    for _, row_pt in df_pts_enr.iterrows():
        lat_pt, lon_pt, tipo_pt = row_pt['Latitud'], row_pt['Longitud'], row_pt['Tipo']
        if tipo_pt == 'VOR / Radioayuda' and mostrar_vors:
            cod = str(row_pt['Codigo_3L']).strip().upper()
            folium.CircleMarker(location=[lat_pt, lon_pt], radius=3.5, color="#FFC107", fill=True, fill_color="#FFC107", fill_opacity=0.9, tooltip=f"VOR: {cod}", popup=f"<b>VOR:</b> {cod}<br>{lat_pt:.4f}, {lon_pt:.4f}").add_to(capa_navaids)
            folium.map.Marker([lat_pt, lon_pt], icon=folium.DivIcon(icon_size=(30, 15), icon_anchor=(15, -4), html=f'<div style="font-size: 7.5pt; color: #FFD54F; font-weight: bold; text-shadow: 1px 1px 2px black;">{cod}</div>')).add_to(capa_navaids)
        elif tipo_pt == 'Waypoint' and mostrar_waypoints:
            nom = str(row_pt['Punto']).strip().upper()
            folium.CircleMarker(location=[lat_pt, lon_pt], radius=2.0, color="#00E5FF", fill=True, fill_color="#00E5FF", fill_opacity=0.7, tooltip=f"Waypoint: {nom}", popup=f"<b>Waypoint:</b> {nom}<br>{lat_pt:.4f}, {lon_pt:.4f}").add_to(capa_navaids)
    capa_navaids.add_to(m)

# 3. DIBUJO DE TRAYECTORIAS
capa_tray = folium.FeatureGroup(name="Trayectorias")
vuelo_encontrado = False

for df_flujo, is_arr, col_color in [(df_lleg, True, "#00FFFF"), (df_sal, False, "#FF0000")]:
    if flujo in (["Llegadas", "Llegadas y Salidas"] if is_arr else ["Salidas", "Llegadas y Salidas"]) and df_flujo is not None and not df_flujo.empty:
        for _, row in df_flujo.iterrows():
            cs_full = str(row.get('callsign', '')).strip().upper()
            if search_callsign:
                if search_callsign not in cs_full: continue
                vuelo_encontrado = True
            elif codigo_seleccionado != "TODAS" and cs_full[:3] != codigo_seleccionado: continue
                    
            trayectoria = extract_trajectory(row.get('route', ''), row.get('adep', ''), row.get('ades', ''), is_arr)
            if len(trayectoria) > 1: 
                h_val = str(row.get('ata', '')).split()[-1] if is_arr else str(row.get('atd', row.get('ata', ''))).split()[-1]
                b_act = bool(search_callsign)
                folium.PolyLine(
                    locations=trayectoria, color=col_color, weight=3.5 if b_act else 1.5, opacity=0.95 if b_act else 0.4, 
                    tooltip=f"{'Llegada' if is_arr else 'Salida'}: {cs_full} (Hora: {h_val} UTC)",
                    popup=folium.Popup(construir_popup_html(row, is_arr), max_width=250, show=b_act)
                ).add_to(capa_tray)

capa_tray.add_to(m)
folium.CircleMarker(location=[21.0366, -86.8770], radius=5, color="white", fill=True, fill_color="white", popup="MMUN").add_to(m)
folium.LayerControl().add_to(m)

map_data = st_folium(m, use_container_width=True, height=700, returned_objects=["last_clicked"])
if map_data and map_data.get("last_clicked") is not None and search_callsign:
    st.session_state["reset_search_flag"] = True
    st.rerun()
if search_callsign and not vuelo_encontrado:
    st.warning(f"No se encontró el Callsign '{search_callsign}' en la fecha ({dia_seleccionado_str}).")

# ===================== PANEL DE GRÁFICAS =====================
st.markdown("<br><h2 style='color: #FFFFFF; text-align: center;'>Panel de Análisis Operativo</h2><hr style='border: 1px solid #333333;'>", unsafe_allow_html=True)
fig_hora = generar_grafica_operaciones(df_lleg, df_sal, flujo, dia_seleccionado_str)
if fig_hora: st.plotly_chart(fig_hora, use_container_width=True)

c1, c2 = st.columns(2)
with c1:
    fig_sec = generar_grafica_barras(agrupar_datos(df_lleg, df_sal, flujo, 'entry_sector', 'Sector_resuelto', 'Sector'), 'Sector', "Carga por Sector de Control")
    if fig_sec: st.plotly_chart(fig_sec, use_container_width=True)
    fig_cia = generar_grafica_barras(agrupar_datos(df_lleg, df_sal, flujo, 'callsign', 'callsign', 'Aerolínea', top_n=10, substr=3), 'Aerolínea', "Top 10 Aerolíneas")
    if fig_cia: st.plotly_chart(fig_cia, use_container_width=True)
    fig_nivel = generar_grafica_barras(agrupar_datos(df_lleg, df_sal, flujo, 'rfl', 'rfl', 'Nivel de Vuelo', top_n=10), 'Nivel de Vuelo', "Top 10 Niveles (RFL)")
    if fig_nivel: st.plotly_chart(fig_nivel, use_container_width=True)
    fig_wtc = generar_grafica_barras(agrupar_datos(df_lleg, df_sal, flujo, 'wtc', 'wtc', 'Estela Turbulenta'), 'Estela Turbulenta', "Categoría de Estela (WTC)")
    if fig_wtc: st.plotly_chart(fig_wtc, use_container_width=True)
with c2:
    fig_flota = generar_grafica_barras(agrupar_datos(df_lleg, df_sal, flujo, 'aircraft_type', 'aircraft_type', 'Aeronave', top_n=10), 'Aeronave', "Mix de Flota (Top 10)")
    if fig_flota: st.plotly_chart(fig_flota, use_container_width=True)
    fig_pista = generar_grafica_barras(agrupar_datos(df_lleg, df_sal, flujo, 'arr_runway', 'dep_runway', 'Pista', top_n=3), 'Pista', "Configuración de Pistas")
    if fig_pista: st.plotly_chart(fig_pista, use_container_width=True)
    fig_punto = generar_grafica_barras(agrupar_datos(df_lleg, df_sal, flujo, 'entry_point', 'exit_point', 'Fijo', top_n=10), 'Fijo', "Puntos de Transferencia")
    if fig_punto: st.plotly_chart(fig_punto, use_container_width=True)
