import streamlit as st
import pandas as pd
import json, os, time
from datetime import datetime, timedelta, date

# ==========================
# CONFIGURACIÓN INICIAL
# ==========================
st.set_page_config(page_title="Registro de Empleados", page_icon="⏱️", layout="centered")

DATA_FILE = "data.csv"
GROUPS_FILE = "groups.json"

# ==========================
# FUNCIONES AUXILIARES
# ==========================
def load_groups():
    """Carga o crea grupos base."""
    if not os.path.exists(GROUPS_FILE):
        base = {
            "Grupo Elizabeth": ["Elizabeth", "Cindy"],
            "Grupo Cecilia": ["Cecilia", "Ofelia"],
            "Grupo Shirley": ["Shirley", "Kelly"]
        }
        save_groups(base)
        return base
    with open(GROUPS_FILE, "r") as f:
        return json.load(f)

def save_groups(groups):
    with open(GROUPS_FILE, "w") as f:
        json.dump(groups, f, indent=2)

def load_data():
    try:
        return pd.read_csv(DATA_FILE)
    except FileNotFoundError:
        return pd.DataFrame(columns=["Fecha", "Grupo", "Inicio", "Fin", "Duración (min)"])

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

def guardar_registros_dia():
    hoy = date.today().strftime("%Y-%m-%d")
    df = load_data()
    if df.empty:
        st.warning("⚠️ No hay registros para guardar.")
        return
    df_hoy = df[df["Fecha"] == hoy]
    if df_hoy.empty:
        st.info(f"ℹ️ No hay registros del día {hoy}.")
        return
    nombre = f"registros_{hoy}.csv"
    df_hoy.to_csv(nombre, index=False)
    st.success(f"✅ Registros del día guardados en '{nombre}'")

# ==========================
# SESIÓN STREAMLIT
# ==========================
if "grupos_activos" not in st.session_state:
    st.session_state.grupos_activos = {}
if "running" not in st.session_state:
    st.session_state.running = {}

# ==========================
# INTERFAZ PRINCIPAL
# ==========================
st.title("⏱️ Registro de Tiempo de Empleados")

usuario = st.radio("Selecciona tu tipo de usuario:", ["dispatcher", "boss"], horizontal=True)
grupos = load_groups()
lista_grupos = list(grupos.keys())

grupo_sel = st.selectbox("Selecciona grupo de trabajo:", lista_grupos)

# ==========================
# FUNCIONES DE CONTROL
# ==========================
def start_turn(grupo):
    st.session_state.grupos_activos[grupo] = {
        "inicio": datetime.now(),
        "pausado": False,
        "tiempo_pausa": timedelta(0),
        "ultima_pausa": None
    }
    st.session_state.running[grupo] = True

def pause_resume(grupo):
    datos = st.session_state.grupos_activos[grupo]
    if not datos["pausado"]:
        datos["pausado"] = True
        datos["ultima_pausa"] = datetime.now()
    else:
        datos["pausado"] = False
        datos["tiempo_pausa"] += datetime.now() - datos["ultima_pausa"]

def stop_turn(grupo):
    datos = st.session_state.grupos_activos.pop(grupo, None)
    if not datos: return
    fin = datetime.now()
    duracion = (fin - datos["inicio"] - datos["tiempo_pausa"]).total_seconds() / 60
    df = load_data()
    df.loc[len(df)] = [date.today().strftime("%Y-%m-%d"), grupo, datos["inicio"], fin, round(duracion, 2)]
    save_data(df)
    st.session_state.running[grupo] = False
    st.success(f"✅ Turno finalizado ({round(duracion, 2)} min).")

# ==========================
# BOTONES PRINCIPALES
# ==========================
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("▶️ Iniciar turno"):
        if grupo_sel not in st.session_state.grupos_activos:
            start_turn(grupo_sel)
            st.success(f"Turno iniciado para {grupo_sel}")
        else:
            st.warning("⚠️ Este grupo ya está activo.")
with col2:
    if grupo_sel in st.session_state.grupos_activos:
        st.button("⏸️ Pausar / Reanudar", on_click=pause_resume, args=[grupo_sel])
with col3:
    if grupo_sel in st.session_state.grupos_activos:
        st.button("⏹️ Detener", on_click=stop_turn, args=[grupo_sel])

# ==========================
# MOSTRAR GRUPOS ACTIVOS
# ==========================
st.divider()
st.subheader("🟢 Grupos activos")

if st.session_state.grupos_activos:
    for grupo, datos in st.session_state.grupos_activos.items():
        st.markdown(f"### {grupo}")
        if not datos["pausado"]:
            tiempo = datetime.now() - datos["inicio"] - datos["tiempo_pausa"]
            st.write(f"**Estado:** Trabajando ⏱️  —  **Inicio:** {datos['inicio'].strftime('%H:%M:%S')}")
            st.metric("Tiempo transcurrido", str(tiempo).split(".")[0])
        else:
            st.warning(f"⏸️ En pausa desde {datos['ultima_pausa'].strftime('%H:%M:%S')}")
else:
    st.info("No hay grupos activos actualmente.")

# ==========================
# AGREGAR NUEVO GRUPO / EMPLEADO
# ==========================
st.divider()
with st.expander("➕ Agregar grupo o empleado"):
    nuevo_grupo = st.text_input("Nuevo grupo (opcional):")
    nuevo_empleado = st.text_input("Nuevo empleado:")
    destino = st.selectbox("Agregar a grupo existente:", ["(crear nuevo)"] + lista_grupos)
    if st.button("💾 Guardar nuevo empleado / grupo"):
        if nuevo_empleado:
            if nuevo_grupo:
                grupos[nuevo_grupo] = [nuevo_empleado]
                st.success(f"Grupo '{nuevo_grupo}' creado con '{nuevo_empleado}'.")
            elif destino != "(crear nuevo)":
                grupos[destino].append(nuevo_empleado)
                st.success(f"Empleado '{nuevo_empleado}' agregado a '{destino}'.")
            save_groups(grupos)
        else:
            st.warning("⚠️ Escribe el nombre del empleado.")

# ==========================
# GUARDAR REGISTROS DEL DÍA
# ==========================
st.divider()
st.subheader("📦 Control diario")
st.caption(f"📅 Fecha actual: {date.today().strftime('%Y-%m-%d')}")
if st.button("💾 Guardar registros del día"):
    guardar_registros_dia()

# ==========================
# VISUALIZACIÓN PARA BOSS
# ==========================
if usuario == "boss":
    st.divider()
    st.subheader("📋 Registros históricos")
    df = load_data()
    if not df.empty:
        st.dataframe(df)
    else:
        st.info("No hay registros aún.")
