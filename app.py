import streamlit as st
from streamlit_autorefresh import st_autorefresh
import pandas as pd
from datetime import datetime, date
from zoneinfo import ZoneInfo
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
import os
from glob import glob

# -------------------------------------------------
# CONFIGURACIÓN INICIAL
# -------------------------------------------------
st.set_page_config(
    page_title="Registro de Tiempo de Empleados",
    page_icon="⏱️",
    layout="centered"
)

st.title("⏱️ Registro de Tiempo de Empleados")

# -------------------------------------------------
# ESTILOS
# -------------------------------------------------
st.markdown("""
<style>
.timer { font-size:28px; color:#00FFAA; font-weight:bold; }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------
# FUNCIONES
# -------------------------------------------------
def now():
    return datetime.now(ZoneInfo("America/New_York"))

def format_seconds(seconds):
    h, r = divmod(int(seconds), 3600)
    m, s = divmod(r, 60)
    return f"{h:02}:{m:02}:{s:02}"

# -------------------------------------------------
# SESSION STATE BASE
# -------------------------------------------------
if "grupos" not in st.session_state:
    st.session_state.grupos = {
        "Grupo Elizabeth": ["Elizabeth", "Cindy"],
        "Grupo Cecilia": ["Cecilia", "Ofelia"],
        "Grupo Shirley": ["Shirley", "Kelly"],
    }

if "turnos" not in st.session_state:
    st.session_state.turnos = {}

if "turnos_completos" not in st.session_state:
    st.session_state.turnos_completos = {}

if "form_abierto" not in st.session_state:
    st.session_state.form_abierto = None

if "asistencia" not in st.session_state:
    st.session_state.asistencia = {}

# -------------------------------------------------
# SIDEBAR – CRONÓMETRO GENERAL POR GRUPO
# -------------------------------------------------
st.sidebar.title("🕒 Jornada por grupo")

for g in st.session_state.grupos.keys():
    st.sidebar.markdown(f"### 👥 {g}")

    if g not in st.session_state.asistencia:
        if st.sidebar.button(f"🟢 Entrada ({g})", key=f"entrada_{g}"):
            st.session_state.asistencia[g] = {
                "inicio": now(),
                "fin": None,
                "activa": True
            }

    else:
        a = st.session_state.asistencia[g]

        if a["activa"]:
            elapsed = (now() - a["inicio"]).total_seconds()
            st.sidebar.markdown(f"⏱️ {format_seconds(elapsed)}")

            if st.sidebar.button(f"🔴 Salida ({g})", key=f"salida_{g}"):
                a["fin"] = now()
                a["activa"] = False
                st.sidebar.success("Turno finalizado")

        else:
            total = (a["fin"] - a["inicio"]).total_seconds()
            st.sidebar.markdown(f"✅ Total: {format_seconds(total)}")

    st.sidebar.markdown("---")

# -------------------------------------------------
# INTERFAZ PRINCIPAL
# -------------------------------------------------
usuario = st.radio("Selecciona tu tipo de usuario:", ["dispatcher", "boss"])
grupo = st.selectbox("Selecciona grupo de trabajo:", list(st.session_state.grupos.keys()))

col1, col2, col3 = st.columns(3)

# -------------------------------------------------
# INICIAR TURNO DE TRABAJO
# -------------------------------------------------
with col1:
    if st.button("▶️ Iniciar turno"):
        st.session_state.turnos[grupo] = {
            "inicio": now(),
            "pausado": False,
            "pausa_inicio": None,
            "tiempo_pausa": 0,
            "pausas": []
        }
        st.success("Turno iniciado")

# -------------------------------------------------
# PAUSAR / REANUDAR
# -------------------------------------------------
with col2:
    if grupo in st.session_state.turnos and st.button("⏸️ Pausar / Reanudar"):
        t = st.session_state.turnos[grupo]

        if not t["pausado"]:
            t["pausado"] = True
            t["pausa_inicio"] = now()
            st.session_state.form_abierto = grupo
        else:
            t["tiempo_pausa"] += (now() - t["pausa_inicio"]).total_seconds()
            t["pausado"] = False
            st.session_state.form_abierto = None

# -------------------------------------------------
# TERMINAR TURNO
# -------------------------------------------------
with col3:
    if grupo in st.session_state.turnos and st.button("⏹️ Terminar"):
        t = st.session_state.turnos.pop(grupo)
        duracion = (now() - t["inicio"]).total_seconds() - t["tiempo_pausa"]
        t["duracion"] = duracion
        st.session_state.turnos_completos[grupo] = t
        st.success("Turno finalizado")

# -------------------------------------------------
# FORMULARIO DE PAUSA
# -------------------------------------------------
if st.session_state.form_abierto:
    g = st.session_state.form_abierto
    with st.form(f"form_{g}"):
        cliente = st.text_input("Cliente")
        direccion = st.text_input("Dirección")
        tiempo_estimado = st.number_input("Tiempo estimado (min)", min_value=0)
        guardar = st.form_submit_button("Guardar")

        if guardar:
            st.session_state.turnos[g]["pausas"].append({
                "cliente": cliente,
                "direccion": direccion,
                "tiempo_estimado": tiempo_estimado
            })
            st.session_state.form_abierto = None
            st.success("Pausa guardada")

# -------------------------------------------------
# MOSTRAR GRUPOS ACTIVOS
# -------------------------------------------------
st.markdown("---")
st.subheader("🟢 Grupos activos")

for g, t in st.session_state.turnos.items():
    trans = (now() - t["inicio"]).total_seconds() - t["tiempo_pausa"]
    st.markdown(
        f"**{g}** — ⏱️ <span class='timer'>{format_seconds(trans)}</span>",
        unsafe_allow_html=True
    )

# -------------------------------------------------
# REFRESH
# -------------------------------------------------
st_autorefresh(interval=1000, key="refresh")
