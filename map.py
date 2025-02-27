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

# Extraer los datos de Firebase desde st.secrets y construir un diccionario nativo
try:
    firebase_creds = {
        "type": st.secrets["firebase"]["type"],
        "project_id": st.secrets["firebase"]["project_id"],
        "private_key_id": st.secrets["firebase"]["private_key_id"],
        "private_key": st.secrets["firebase"]["private_key"].replace("\\n", "\n"),
        "client_email": st.secrets["firebase"]["client_email"],
        "client_id": st.secrets["firebase"]["client_id"],
        "auth_uri": st.secrets["firebase"]["auth_uri"],
        "token_uri": st.secrets["firebase"]["token_uri"],
        "auth_provider_x509_cert_url": st.secrets["firebase"]["auth_provider_x509_cert_url"]
    }

    # Inicializar Firebase
    cred = credentials.Certificate(firebase_creds)
    firebase_admin.initialize_app(cred)
    db = firestore.client()

    st.write("✅ Firebase inicializado correctamente")

except Exception as e:
    st.error(f"❌ Error al inicializar Firebase: {e}")

# Acceder a Firestore
db = firestore.client()

# Función para guardar un reporte en Firestore
def save_report(state_progress, report_name, user="admin"):
    report_data = {
        "id": report_name,
        "fecha_creacion": datetime.now().isoformat(),
        "valores_avance": state_progress,
        "usuario": user
    }
    db.collection("reportes").document(report_name).set(report_data)

# Función para cargar un reporte desde Firestore
def load_report(report_name):
    doc = db.collection("reportes").document(report_name).get()
    if doc.exists:
        return doc.to_dict()
    return None

# Función para eliminar un reporte de Firestore
def delete_report(report_name):
    db.collection("reportes").document(report_name).delete()

# Función para listar todos los reportes de Firestore
def list_reports():
    reports = db.collection("reportes").stream()
    return [report.id for report in reports]

def main():
    st.set_page_config(APP_TITLE, layout="wide")
    st.title(APP_TITLE)
    st.caption(APP_SUB_TITLE)

    # Inicializar session_state si no existe
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

        # Procesamiento de datos
        last_5_columns = df.columns[-5:]
        correct_headers = [
            'Fecha Planeada Update',
            'Fecha Real Update',
            'Estatus Update',
            'Estatus Impresión',
            'Observaciones'
        ]
        df_temp = df[last_5_columns].copy()
        df_temp.columns = correct_headers
        extra_columns = df[['Estado', 'HOSTNAME', 'OP']].copy()
        df_temp = pd.concat([extra_columns, df_temp], axis=1)
        grouped = df_temp.groupby(['Estado', 'HOSTNAME', 'OP']).agg(lambda x: ' '.join(x.astype(str))).reset_index()

        # Widgets en sidebar
        unique_states = list(ESTADOS.keys())
        
        # Selección individual de estado
        selected_state = st.sidebar.selectbox(
            'Selecciona un Estado',
            options=unique_states,
            format_func=lambda x: ESTADOS[x]  # Mostrar nombres completos
        )

        # Slider para estado seleccionado
        current_value = st.session_state.state_progress.get(selected_state, 50)
        new_value = st.sidebar.slider(
            f"Porcentaje de avance para {ESTADOS[selected_state]}",
            min_value=0,
            max_value=100,
            value=int(current_value)  # Cierre correcto del paréntesis
        )
        
        # Botón para guardar cambios
        if st.sidebar.button("💾 Guardar Cambios"):
            st.session_state.state_progress[selected_state] = new_value
            st.sidebar.success(f"¡Progreso de {ESTADOS[selected_state]} guardado!")

        # Campo para nombre personalizado del reporte
        report_name = st.sidebar.text_input("Nombre del Reporte", value=f"Reporte_{datetime.now().strftime('%Y-%m-%d_%H-%M')}")

        # Botón para generar reporte
        if st.sidebar.button("📄 Guardar Reporte Actual"):
            try:
                save_report(st.session_state.state_progress, report_name)
                st.sidebar.success(f"Reporte '{report_name}' guardado exitosamente!")
            except Exception as e:
                st.sidebar.error(f"Error: {e}")

        # Mostrar reportes guardados
        st.subheader("Reportes Guardados")
        reports = list_reports()
        
        if reports:
            selected_report = st.selectbox(
                "Selecciona un reporte para ver",
                options=reports
            )
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🔍 Ver Reporte"):
                    # Cargar datos del reporte seleccionado
                    report_data = load_report(selected_report)
                    if report_data:
                        # Actualizar el estado actual con los valores del reporte
                        st.session_state.state_progress = report_data["valores_avance"]
                        st.success(f"Reporte '{selected_report}' cargado exitosamente!")
                    else:
                        st.error("Reporte no encontrado")
            
            with col2:
                if st.button("🗑️ Eliminar Reporte"):
                    if delete_report(selected_report):
                        st.success(f"Reporte '{selected_report}' eliminado exitosamente!")
                        # Actualizar la lista de reportes después de eliminar
                        st.experimental_rerun()  # Recargar la aplicación para actualizar la lista
                    else:
                        st.error("No se pudo eliminar el reporte.")
        else:
            st.info("No hay reportes guardados aún")

        # Aplicar progreso a todos los estados
        grouped['Weighted OK Count'] = grouped['Estado'].map(
            lambda x: st.session_state.state_progress.get(x, 50)/100
        )

        # Mapa coroplético
        fig = px.choropleth_mapbox(
            grouped,
            geojson=geojson_data,
            locations='Estado',
            featureidkey="properties.id",
            color='Weighted OK Count',
            color_continuous_scale=[
                "#d73027", "#f46d43", "#fdae61", 
                "#fee08b", "#d9ef8b", "#a6d96a",
                "#66bd63", "#1a9850", "#006837"
            ],
            range_color=(0, 1),
            mapbox_style="carto-positron",
            zoom=5,
            center={"lat": 23.6345, "lon": -102.5528},
            opacity=0.5,
            hover_name='Estado',
            hover_data={'Estado': False, 'Weighted OK Count': ':.0%'}
        )

        fig.update_layout(
            coloraxis_colorbar=dict(
                title="Avance",
                tickvals=[i/10 for i in range(11)],
                ticktext=[f"{i*10}%" for i in range(11)]
            ),
            margin={"r":0,"t":0,"l":0,"b":0},
            height=700
        )

        st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()
