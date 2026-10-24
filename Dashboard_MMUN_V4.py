import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import re
import base64
import plotly.express as px

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
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] { background-color: #0c2340 !important; }
    h1 {color: #FFFFFF !important; font-family: 'Helvetica Neue', sans-serif; display: flex; align-items: center;}
    p, .stSelectbox label p, .stRadio label p, div[role="radiogroup"] label div {color: #FFFFFF !important; font-weight: bold;}
    div[data-baseweb="select"] span {color: #000000 !important;}
    </style>
""", unsafe_allow_html=True)

st.markdown(f"<h1>{logo_html} Análisis Dinámico de Rutas RNAV/PBN - MMUN</h1>", unsafe_allow_html=True)
st.markdown("**Fuente de Datos:** Registros TopSky (Llegadas y Salidas) | **Archivos MASTER**")
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
        return df[df[columna_filtro].apply(lambda x: isinstance(x, str) and len(str(x)) == 4)].copy()
    return pd.DataFrame()

def obtener_dias_disponibles(archivo):
    try:
        xls = pd.ExcelFile(archivo)
        return [hoja for hoja in xls.sheet_names if hoja.startswith('2026-')]
    except Exception: return []

@st.cache_data
def cargar_datos_dia(archivo_lleg, archivo_sal, dia_seleccionado):
    try:
        df_lleg = limpiar_datos(pd.read_excel(archivo_lleg, sheet_name=dia_seleccionado), 'adep')
        df_sal = limpiar_datos(pd.read_excel(archivo_sal, sheet_name=dia_seleccionado), 'ades')
        return df_lleg, df_sal
    except Exception as e: return None, None

def generar_grafica_operaciones(df_lleg, df_sal, flujo, dia_seleccionado):
    try:
        datos = []
        if flujo in ["Llegadas", "Llegadas y Salidas"] and df_lleg is not None and not df_lleg.empty:
            df_lleg['Hora'] = pd.to_datetime(df_lleg['ata'], errors='coerce').dt.hour
            c = df_lleg['Hora'].value_counts().sort_index().reset_index()
            c.columns, c['Tipo'] = ['Hora', 'Operaciones'], 'Llegadas'
            datos.append(c)
            
        if flujo in ["Salidas", "Llegadas y Salidas"] and df_sal is not None and not df_sal.empty:
            df_sal['Hora'] = pd.to_datetime(df_sal.get('atd', df_sal.get('ata')), errors='coerce').dt.hour
            c = df_sal['Hora'].value_counts().sort_index().reset_index()
            c.columns, c['Tipo'] = ['Hora', 'Operaciones'], 'Salidas'
            datos.append(c)
            
        if not datos: return None
        df_final = pd.concat(datos).dropna(subset=['Hora'])
        df_final['Hora_Etiqueta'] = df_final['Hora'].astype(int).astype(str).str.zfill(2) + ":00"
        
        fig = px.bar(df_final, x='Hora_Etiqueta', y='Operaciones', color='Tipo', barmode='group',
                     title=f"Volumen Operativo por Hora - MMUN ({dia_seleccionado})",
                     color_discrete_map={'Llegadas': '#00FFFF', 'Salidas': '#FF0000'})
        # Se forzó el color del título a blanco con title_font
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', 
                          font_color='white', title_font=dict(color='white', size=18), 
                          xaxis_title="Hora (UTC)")
        return fig
    except: return None

def agrupar_datos(df_lleg, df_sal, flujo, col_l, col_s, nom, top_n=None, substr=None):
    datos = []
    if flujo in ["Llegadas", "Llegadas y Salidas"] and df_lleg is not None and not df_lleg.empty and col_l in df_lleg.columns:
        d = df_lleg[[col_l]].copy(); d.columns = [nom]; d['Tipo'] = 'Llegadas'
        datos.append(d)
    if flujo in ["Salidas", "Llegadas y Salidas"] and df_sal is not None and not df_sal.empty and col_s in df_sal.columns:
        d = df_sal[[col_s]].copy(); d.columns = [nom]; d['Tipo'] = 'Salidas'
        datos.append(d)
    if not datos: return None
    
    df_f = pd.concat(datos)
    df_f[nom] = df_f[nom].astype(str).str.strip()
    if substr: df_f[nom] = df_f[nom].str[:substr]
    if top_n:
        top = df_f[nom].value_counts().head(top_n).index
        df_f = df_f[df_f[nom].isin(top)]
    return df_f.groupby([nom, 'Tipo']).size().reset_index(name='Operaciones')

def generar_grafica_barras(df_res, x_col, titulo):
    if df_res is None or df_res.empty: return None
    fig = px.bar(df_res, x=x_col, y='Operaciones', color='Tipo', barmode='group', title=titulo,
                 color_discrete_map={'Llegadas': '#00FFFF', 'Salidas': '#FF0000'})
    # Se forzó el color del título a blanco
    fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', 
                      font_color='white', title_font=dict(color='white', size=16), 
                      margin=dict(t=50, b=10))
    return fig

# ===================== INTERFAZ PRINCIPAL =====================
col_filtros, col_mapa = st.columns([1, 3])

with col_filtros:
    st.markdown("<h2 style='color: #FFFFFF;'>Filtros Operativos</h2>", unsafe_allow_html=True)
    mes_seleccionado = st.selectbox("Seleccione el Mes:", ["Septiembre", "Octubre"])
    
    arch_lleg = 'lleg_MMUN_sept_2026_MASTER.xlsx' if mes_seleccionado == "Septiembre" else 'lleg_MMUN_oct_2026_MASTER.xlsx'
    arch_sal = 'sal_MMUN_sept_2026_MASTER.xlsx' if mes_seleccionado == "Septiembre" else 'sal_MMUN_oct_2026_MASTER.xlsx'
        
    dias_disponibles = obtener_dias_disponibles(arch_lleg)
    if not dias_disponibles:
        st.error(f"Archivos de {mes_seleccionado} no encontrados en el repositorio.")
        st.stop()
        
    dia_seleccionado = st.selectbox("Seleccione el Día:", dias_disponibles)
    flujo = st.radio("Flujo de Tránsito:", ["Llegadas", "Salidas", "Llegadas y Salidas"])
    
    df_lleg, df_sal = cargar_datos_dia(arch_lleg, arch_sal, dia_seleccionado)
    if df_lleg is None: 
        st.error("No se pudieron cargar los datos de Excel.")
        st.stop()
        
    total_llegadas = len(df_lleg)
    total_salidas = len(df_sal)
    
    st.markdown("<h3 style='color: #FFFFFF;'>Resumen Estadístico</h3>", unsafe_allow_html=True)
    if flujo == "Llegadas y Salidas":
        st.info(f"Total de operaciones (Llegadas y Salidas): **{total_llegadas + total_salidas}**")
        st.markdown(f"<p style='color: white;'>- Llegadas: {total_llegadas}</p>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: white;'>- Salidas: {total_salidas}</p>", unsafe_allow_html=True)
    elif flujo == "Llegadas": st.info(f"Total de Llegadas: **{total_llegadas}**")
    else: st.info(f"Total de Salidas: **{total_salidas}**")

with col_mapa:
    tiles_url = 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}'
    attr = 'Tiles &copy; Esri'
    
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
    st_folium(m, width=900, height=600)

# ===================== PANEL DE GRÁFICAS DE EXCEL =====================
st.markdown("<br><h2 style='color: #FFFFFF; text-align: center;'>Panel de Análisis Operativo</h2><hr style='border: 1px solid #333333;'>", unsafe_allow_html=True)

fig_hora = generar_grafica_operaciones(df_lleg, df_sal, flujo, dia_seleccionado)
if fig_hora: st.plotly_chart(fig_hora, use_container_width=True)

col_graf_1, col_graf_2 = st.columns(2)

with col_graf_1:
    df_sec = agrupar_datos(df_lleg, df_sal, flujo, 'entry_sector', 'Sector_resuelto', 'Sector')
    fig_sec = generar_grafica_barras(df_sec, 'Sector', "Carga por Sector de Control")
    if fig_sec: st.plotly_chart(fig_sec, use_container_width=True)
        
    df_cia = agrupar_datos(df_lleg, df_sal, flujo, 'callsign', 'callsign', 'Aerolínea', top_n=10, substr=3)
    fig_cia = generar_grafica_barras(df_cia, 'Aerolínea', "Top 10 Aerolíneas (Volumen)")
    if fig_cia: st.plotly_chart(fig_cia, use_container_width=True)
    
    # NUEVO: Gráfica de Niveles de Vuelo
    df_nivel = agrupar_datos(df_lleg, df_sal, flujo, 'rfl', 'rfl', 'Nivel de Vuelo (RFL)', top_n=10)
    fig_nivel = generar_grafica_barras(df_nivel, 'Nivel de Vuelo (RFL)', "Top 10 Niveles de Vuelo (RFL)")
    if fig_nivel: st.plotly_chart(fig_nivel, use_container_width=True)
    
    # NUEVO: Gráfica de Estela Turbulenta
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
        
    # NUEVO: Gráfica de Puntos de Transferencia
    df_punto = agrupar_datos(df_lleg, df_sal, flujo, 'entry_point', 'exit_point', 'Fijo de Ruta', top_n=10)
    fig_punto = generar_grafica_barras(df_punto, 'Fijo de Ruta', "Puntos de Transferencia (Top 10 Fijos)")
    if fig_punto: st.plotly_chart(fig_punto, use_container_width=True)
