import streamlit as st
from streamlit_autorefresh import st_autorefresh
import pandas as pd
from datetime import datetime, date
from zoneinfo import ZoneInfo
from io import BytesIO
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
import os
from glob import glob

# ================= CONFIG =================
st.set_page_config(page_title="Registro de Tiempo", page_icon="⏱️", layout="centered")

TZ = ZoneInfo("America/New_York")

def now():
    return datetime.now(TZ)

# ================= SESSION STATE =================
if "asistencia" not in st.session_state:
    st.session_state.asistencia = None

if "turnos" not in st.session_state:
    st.session_state.turnos = {}

if "turnos_completos" not in st.session_state:
    st.session_state.turnos_completos = {}

# ================= SIDEBAR – CRONÓMETRO ASISTENCIA =================
st.sidebar.title("🕒 Jornada laboral")

if st.session_state.asistencia is None:
    if st.sidebar.button("🟢 Entrada"):
        st.session_state.asistencia = {
            "inicio": now(),
            "activa": True
        }
else:
    inicio = st.session_state.asistencia["inicio"]
    transcurrido = (now() - inicio).total_seconds()

    h, r = divmod(transcurrido, 3600)
    m, s = divmod(r, 60)

    st.sidebar.markdown(
        f"""
        **Tiempo en jornada:**  
        ## ⏱️ {int(h):02}:{int(m):02}:{int(s):02}
        """
    )

    if st.sidebar.button("🔴 Salida / Terminar turno"):
        st.session_state.asistencia["fin"] = now()
        st.session_state.asistencia["activa"] = False
        st.sidebar.success("Jornada finalizada")

# ================= MAIN =================
st.title("⏱️ Registro de Tiempo de Empleados")

usuario = st.radio("Selecciona tu tipo de usuario:", ["dispatcher", "boss"])

grupos = ["Grupo Elizabeth", "Grupo Cecilia", "Grupo Shirley"]
grupo = st.selectbox("Selecciona grupo de trabajo:", grupos)

col1, col2, col3 = st.columns(3)

# ---------- INICIAR TURNO TRABAJO ----------
with col1:
    if st.button("▶️ Iniciar turno"):
        st.session_state.turnos[grupo] = {
            "inicio": now(),
            "pausado": False,
            "pausa_inicio": None,
            "tiempo_pausas": 0,
            "pausas": [],
            "llegadas": []
        }

# ---------- PAUSAR / REANUDAR ----------
with col2:
    if grupo in st.session_state.turnos and st.button("⏸️ Pausar / Reanudar"):
        t = st.session_state.turnos[grupo]
        if not t["pausado"]:
            t["pausado"] = True
            t["pausa_inicio"] = now()
        else:
            pausa = (now() - t["pausa_inicio"]).total_seconds()
            t["tiempo_pausas"] += pausa
            t["pausado"] = False

# ---------- TERMINAR TURNO ----------
with col3:
    if grupo in st.session_state.turnos and st.button("⏹️ Terminar"):
        t = st.session_state.turnos.pop(grupo)
        duracion = (now() - t["inicio"]).total_seconds() - t["tiempo_pausas"]
        t["duracion"] = duracion
        st.session_state.turnos_completos[grupo] = t

# ================= GRUPOS ACTIVOS =================
st.markdown("---")
st.subheader("🟢 Grupos activos")

for g, t in st.session_state.turnos.items():
    tiempo = (now() - t["inicio"]).total_seconds() - t["tiempo_pausas"]
    h, r = divmod(tiempo, 3600)
    m, s = divmod(r, 60)

    st.markdown(f"""
    **{g}**  
    ⏱️ Tiempo de trabajo: **{int(h):02}:{int(m):02}:{int(s):02}**
    """)

# ================= AUTO REFRESH =================
st_autorefresh(interval=1000, key="refresh")
