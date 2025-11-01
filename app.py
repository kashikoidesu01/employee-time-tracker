import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta

# ==========================
# CONFIGURACIÓN INICIAL
# ==========================
st.set_page_config(page_title="Time Tracker", page_icon="⏱️", layout="centered")

USERS = ["dispatcher", "boss"]
EMPLOYEES = ["Cecilia", "Ofelia", "Elizabeth", "Cindy", "Sandra", "Shirley", "Kelly"]
DATA_FILE = "data.csv"

# ==========================
# FUNCIONES AUXILIARES
# ==========================
def load_data():
    try:
        return pd.read_csv(DATA_FILE)
    except FileNotFoundError:
        return pd.DataFrame(columns=["Empleado", "Inicio", "Fin", "Duración (min)"])

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

# ==========================
# INTERFAZ DE USUARIO
# ==========================
st.title("⏱️ Registro de Tiempo de Empleados")

# Selección de usuario
user = st.radio("Selecciona tu tipo de usuario:", USERS, horizontal=True)

# Selección de empleado
employee = st.selectbox("Selecciona empleado:", EMPLOYEES)

# Estado guardado en sesión
if "running" not in st.session_state:
    st.session_state.running = False
if "start_time" not in st.session_state:
    st.session_state.start_time = None
if "elapsed" not in st.session_state:
    st.session_state.elapsed = timedelta(0)
if "pause_time" not in st.session_state:
    st.session_state.pause_time = None
if "paused" not in st.session_state:
    st.session_state.paused = False

# ==========================
# FUNCIONES DE CONTROL
# ==========================
def start_stop():
    if not st.session_state.running:
        st.session_state.start_time = datetime.now()
        st.session_state.running = True
        st.session_state.elapsed = timedelta(0)
    else:
        # Detener el conteo
        end_time = datetime.now()
        duration = (end_time - st.session_state.start_time - st.session_state.elapsed).total_seconds() / 60
        df = load_data()
        df.loc[len(df)] = [employee, st.session_state.start_time, end_time, round(duration, 2)]
        save_data(df)
        st.session_state.running = False
        st.session_state.start_time = None
        st.session_state.elapsed = timedelta(0)
        st.session_state.paused = False
        st.success(f"✅ Turno finalizado. Duración: {round(duration, 2)} minutos.")

def pause_resume():
    if not st.session_state.paused:
        st.session_state.pause_time = datetime.now()
        st.session_state.paused = True
    else:
        st.session_state.elapsed += datetime.now() - st.session_state.pause_time
        st.session_state.paused = False

# ==========================
# BOTONES
# ==========================
col1, col2 = st.columns(2)
with col1:
    st.button("▶️ Start / Stop Turn", on_click=start_stop)
with col2:
    if st.session_state.running:
        st.button("⏸️ Pause / Resume", on_click=pause_resume)

# Mostrar tiempo en vivo
if st.session_state.running:
    if st.session_state.paused:
        st.warning("⏸️ En pausa")
    else:
        elapsed = datetime.now() - st.session_state.start_time - st.session_state.elapsed
        st.metric("Tiempo trabajado", str(elapsed).split(".")[0])
else:
    st.info("Turno detenido o no iniciado.")

# ==========================
# MOSTRAR REGISTROS (solo jefe)
# ==========================
if user == "boss":
    st.subheader("📋 Registros de trabajo")
    df = load_data()
    if len(df) > 0:
        st.dataframe(df)
    else:
        st.info("Aún no hay registros guardados.")
