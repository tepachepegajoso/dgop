import streamlit as st
import pandas as pd
import json
import plotly.express as px
from streamlit_option_menu import option_menu
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore

APP_TITLE = 'Actividades DGOP'
APP_SUB_TITLE = 'MAPA DE AVANCES'

# Diccionario de nombres de estados
ESTADOS = {
    "MX-CMX": "CIUDAD DE MÉXICO",
    "MX-HID": "HIDALGO",
    "MX-TLA": "TLAXCALA",
    "MX-MOR": "MORELOS",
    "MX-GRO": "GUERRERO",
    "MX-MEX": "ESTADO DE MÉXICO",
    "MX-SIN": "SINALOA",
    "MX-SON": "SONORA",
    "MX-NLE": "NUEVO LEÓN",
    "MX-VER": "VERACRUZ",
    "MX-PUE": "PUEBLA",
    "MX-BCN": "TIJUANA",
    "MX-CHH": "CHIHUAHUA",
    "MX-QUE": "QUERÉTARO",
    "MX-CAM": "CAMPECHE",
    "MX-CHP": "CHIAPAS",
    "MX-DUR": "DURANGO",
    "MX-NAY": "NAYARIT",
    "MX-OAX": "OAXACA",
    "MX-TAB": "TABASCO",
    "MX-GUA": "GUANAJUATO",
    "MX-MIC": "MICHOACÁN",
    "MX-YUC": "YUCATÁN",
    "MX-COL": "COLIMA",
    "MX-ROO": "QUINTANA ROO",
    "MX-AGU": "AGUASCALIENTES",
    "MX-BCS": "BAJA CALIFORNIA SUR",
    "MX-COA": "COAHUILA",
    "MX-SLP": "SAN LUIS POTOSÍ",
    "MX-TAM": "TAMAULIPAS",
    "MX-ZAC": "ZACATECAS"
}

# Inicializar Firebase (solo una vez)
if not firebase_admin._apps:
    try:
        firebase_secrets = json.loads(st.secrets["firebase"])
        cred = credentials.Certificate(firebase_secrets)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Error al inicializar Firebase: {e}")
        st.stop()

# Acceder a Firestore
db = firestore.client()

# Funciones para interactuar con Firestore

def save_report(state_progress, report_name, user="admin"):
    report_data = {
        "id": report_name,
        "fecha_creacion": datetime.now().isoformat(),
        "valores_avance": state_progress,
        "usuario": user
    }
    db.collection("reportes").document(report_name).set(report_data)

def load_report(report_name):
    doc = db.collection("reportes").document(report_name).get()
    if doc.exists:
        return doc.to_dict()
    return None

def delete_report(report_name):
    db.collection("reportes").document(report_name).delete()

def list_reports():
    reports = db.collection("reportes").stream()
    return [report.id for report in reports]

def main():
    st.set_page_config(APP_TITLE, layout="wide")
    st.title(APP_TITLE)
    st.caption(APP_SUB_TITLE)
    
    if 'state_progress' not in st.session_state:
        st.session_state.state_progress = {}
    
    menu_option = option_menu(
        menu_title="Selecciona una opción", 
        options=["Visualización del Mapa"],
        icons=["map"], 
        menu_icon="cast", 
        default_index=0, 
        orientation="horizontal"
    )
    
    if menu_option == "Visualización del Mapa":
        df = pd.read_csv('datos_despliegue.csv')
        
        with open('mexicoHigh.json') as f:
            geojson_data = json.load(f)
        
        grouped = df.groupby(['Estado']).size().reset_index(name='Cantidad')
        
        unique_states = list(ESTADOS.keys())
        selected_state = st.sidebar.selectbox('Selecciona un Estado', options=unique_states, format_func=lambda x: ESTADOS[x])
        
        current_value = st.session_state.state_progress.get(selected_state, 50)
        new_value = st.sidebar.slider(f"Porcentaje de avance para {ESTADOS[selected_state]}", min_value=0, max_value=100, value=int(current_value))
        
        if st.sidebar.button("💾 Guardar Cambios"):
            st.session_state.state_progress[selected_state] = new_value
            st.sidebar.success(f"¡Progreso de {ESTADOS[selected_state]} guardado!")
        
        report_name = st.sidebar.text_input("Nombre del Reporte", value=f"Reporte_{datetime.now().strftime('%Y-%m-%d_%H-%M')}")
        
        if st.sidebar.button("📄 Guardar Reporte Actual"):
            try:
                save_report(st.session_state.state_progress, report_name)
                st.sidebar.success(f"Reporte '{report_name}' guardado exitosamente!")
            except Exception as e:
                st.sidebar.error(f"Error: {e}")
        
        st.subheader("Reportes Guardados")
        reports = list_reports()
        
        if reports:
            selected_report = st.selectbox("Selecciona un reporte para ver", options=reports)
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🔍 Ver Reporte"):
                    report_data = load_report(selected_report)
                    if report_data:
                        st.session_state.state_progress = report_data["valores_avance"]
                        st.success(f"Reporte '{selected_report}' cargado exitosamente!")
                    else:
                        st.error("Reporte no encontrado")
            
            with col2:
                if st.button("🗑️ Eliminar Reporte"):
                    delete_report(selected_report)
                    st.success(f"Reporte '{selected_report}' eliminado exitosamente!")
                    st.experimental_rerun()
        else:
            st.info("No hay reportes guardados aún")
        
        fig = px.choropleth_mapbox(
            grouped,
            geojson=geojson_data,
            locations='Estado',
            featureidkey="properties.id",
            color='Cantidad',
            color_continuous_scale="Viridis",
            mapbox_style="carto-positron",
            zoom=5,
            center={"lat": 23.6345, "lon": -102.5528},
            opacity=0.5
        )
        fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=700)
        st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()
