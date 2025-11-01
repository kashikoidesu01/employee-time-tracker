import streamlit as st
import pandas as pd
import time
from datetime import datetime, date

st.set_page_config("Registro de Tiempo de Empleados", "⏱️")

# ==========================
# CONFIGURACIÓN INICIAL
# ==========================
if "grupos" not in st.session_state:
    st.session_state.grupos = {
        "Grupo Elizabeth": ["Elizabeth", "Cindy"],
        "Grupo Cecilia": ["Cecilia", "Ofelia"],
        "Grupo Shirley": ["Shirley", "Kelly"]
    }

if "tiempos" not in st.session_state:
    st.session_state.tiempos = {}

# ==========================
# FUNCIONES
# ==========================
def formatear_hora(hora):
    return hora.strftime("%I:%M:%S %p")

def iniciar_turno(nombre):
    st.session_state.tiempos[nombre] = {
        "inicio": datetime.now(),
        "pausado": False,
        "pausa_inicio": None,
        "total_pausa": 0,
        "activo": True
    }

def pausar_reanudar(nombre):
    d = st.session_state.tiempos[nombre]
    if not d["pausado"]:
        d["pausado"] = True
        d["pausa_inicio"] = datetime.now()
    else:
        d["pausado"] = False
        d["total_pausa"] += (datetime.now() - d["pausa_inicio"]).total_seconds()
        d["pausa_inicio"] = None

def detener_turno(nombre):
    d = st.session_state.tiempos[nombre]
    d["activo"] = False

def guardar_registros():
    hoy = date.today().strftime("%Y-%m-%d")
    datos = []
    for grupo, info in st.session_state.tiempos.items():
        if "inicio" in info:
            fin = datetime.now()
            total = (fin - info["inicio"]).total_seconds() - info["total_pausa"]
            datos.append({
                "Fecha": hoy,
                "Grupo": grupo,
                "Inicio": formatear_hora(info["inicio"]),
                "Fin": formatear_hora(fin),
                "Tiempo trabajado (min)": round(total / 60, 2)
            })
    if datos:
        df = pd.DataFrame(datos)
        df.to_csv(f"registros_{hoy}.csv", index=False)
        st.success(f"✅ Registros guardados como registros_{hoy}.csv")
    else:
        st.warning("⚠️ No hay datos para guardar.")

# ==========================
# INTERFAZ PRINCIPAL
# ==========================
st.title("⏱️ Registro de Tiempo de Empleados")

tipo = st.radio("Selecciona tu tipo de usuario:", ["dispatcher", "boss"], horizontal=True)
grupo = st.selectbox("Selecciona grupo de trabajo:", list(st.session_state.grupos.keys()))

col1, col2, col3 = st.columns(3)
with col1:
    if st.button("▶️ Iniciar turno"):
        iniciar_turno(grupo)
        st.success(f"Turno iniciado para {grupo}")

with col2:
    if grupo in st.session_state.tiempos:
        if st.button("⏸️ Pausar / Reanudar"):
            pausar_reanudar(grupo)

with col3:
    if grupo in st.session_state.tiempos:
        if st.button("⏹️ Detener"):
            detener_turno(grupo)

# ==========================
# SECCIÓN: GRUPOS ACTIVOS
# ==========================
st.divider()
st.subheader("🟢 Grupos activos")

for nombre, datos in st.session_state.tiempos.items():
    if datos["activo"]:
        estado = "En pausa" if datos["pausado"] else "Trabajando"
        st.markdown(f"### {nombre}")
        st.write(f"**Estado:** {estado}")
        st.write(f"**Inicio:** {formatear_hora(datos['inicio'])}")

        tiempo_placeholder = st.empty()
        while datos["activo"] and not datos["pausado"]:
            transcurrido = (datetime.now() - datos["inicio"]).total_seconds() - datos["total_pausa"]
            h, m, s = int(transcurrido // 3600), int((transcurrido % 3600) // 60), int(transcurrido % 60)
            tiempo_placeholder.markdown(f"**Tiempo transcurrido:** ⏱️ {h:02}:{m:02}:{s:02}")
            time.sleep(1)
            st.experimental_rerun()

# ==========================
# AGREGAR NUEVO GRUPO
# ==========================
st.divider()
with st.expander("➕ Agregar grupo o empleado"):
    nuevo_grupo = st.text_input("Nombre del nuevo grupo")
    empleados = st.text_input("Empleados (separa por comas)")
    if st.button("Agregar"):
        if nuevo_grupo and empleados:
            st.session_state.grupos[nuevo_grupo] = [e.strip() for e in empleados.split(",")]
            st.success(f"✅ Grupo '{nuevo_grupo}' agregado correctamente.")
        else:
            st.warning("⚠️ Ingresa el nombre del grupo y al menos un empleado.")

# ==========================
# GUARDAR REGISTROS
# ==========================
st.divider()
st.subheader("📦 Control diario")
st.write(f"📅 Fecha actual: {date.today().strftime('%Y-%m-%d')}")

if st.button("💾 Guardar registros del día"):
    guardar_registros()
