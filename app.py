# ================================
# REGISTRO DE TIEMPO DE EMPLEADOS
# Jornada por grupo + múltiples trabajos
# Copiar y pegar en Streamlit Cloud
# ================================

import streamlit as st
from streamlit_autorefresh import st_autorefresh
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import pandas as pd
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

# ================================
# CONFIGURACIÓN GENERAL
# ================================

TZ = ZoneInfo("America/New_York")
st.set_page_config(page_title="Registro de Tiempo", layout="wide")
st_autorefresh(interval=1000, key="refresh")

# ================================
# SESSION STATE INICIAL
# ================================

if "grupos" not in st.session_state:
    st.session_state.grupos = {}

# ================================
# FUNCIONES UTILIDAD
# ================================

def now():
    return datetime.now(TZ)

def format_td(td: timedelta):
    total_seconds = int(td.total_seconds())
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

# ================================
# SIDEBAR – CRONÓMETRO DE JORNADA
# ================================

st.sidebar.title("🕒 Jornada por grupo")

for grupo, g in st.session_state.grupos.items():
    if g["jornada_activa"]:
        elapsed = now() - g["inicio_jornada"]
        st.sidebar.markdown(f"### 👥 {grupo}")
        st.sidebar.markdown(f"⏱ {format_td(elapsed)}")
        st.sidebar.markdown(f"**Estado:** {g['estado']}")
        if st.sidebar.button(f"🔴 Salida ({grupo})"):
            g["fin_jornada"] = now()
            g["jornada_activa"] = False
            g["estado"] = "Fuera de turno"

# ================================
# UI PRINCIPAL
# ================================

st.title("⏱ Registro de Tiempo de Empleados")

rol = st.radio("Selecciona tu tipo de usuario:", ["dispatcher", "boss"])

grupo = st.selectbox(
    "Selecciona grupo de trabajo:",
    ["Grupo Elizabeth", "Grupo Cecilia", "Grupo Shirley"],
)

# ================================
# INICIALIZAR GRUPO
# ================================

if grupo not in st.session_state.grupos:
    st.session_state.grupos[grupo] = {
        "inicio_jornada": None,
        "fin_jornada": None,
        "jornada_activa": False,
        "estado": "Fuera de turno",
        "estado_inicio": None,
        "tiempos": {"Viajando": timedelta(), "Trabajando": timedelta(), "Receso": timedelta()},
        "trabajos": [],
    }

g = st.session_state.grupos[grupo]

# ================================
# BOTONES PRINCIPALES
# ================================

col1, col2, col3 = st.columns(3)

if col1.button("▶ Iniciar turno") and not g["jornada_activa"]:
    g["inicio_jornada"] = now()
    g["estado_inicio"] = now()
    g["estado"] = "Viajando"
    g["jornada_activa"] = True

if col2.button("⏸ Receso") and g["jornada_activa"]:
    delta = now() - g["estado_inicio"]
    g["tiempos"][g["estado"]] += delta
    g["estado"] = "Receso"
    g["estado_inicio"] = now()

if col3.button("⏹ Terminar turno") and g["jornada_activa"]:
    delta = now() - g["estado_inicio"]
    g["tiempos"][g["estado"]] += delta
    g["fin_jornada"] = now()
    g["jornada_activa"] = False
    g["estado"] = "Fuera de turno"

# ================================
# FORMULARIO DE TRABAJO
# ================================

st.subheader("🧾 Registrar trabajo")

with st.form("trabajo_form"):
    cliente = st.text_input("Cliente")
    direccion = st.text_input("Dirección")
    estimado = st.number_input("Tiempo estimado (min)", min_value=0)

    iniciar = st.form_submit_button("🟢 Iniciar trabajo")

    if iniciar and g["jornada_activa"]:
        delta = now() - g["estado_inicio"]
        g["tiempos"][g["estado"]] += delta

        g["trabajos"].append({
            "cliente": cliente,
            "direccion": direccion,
            "inicio": now(),
            "fin": None,
            "estimado": estimado,
        })

        g["estado"] = "Trabajando"
        g["estado_inicio"] = now()

if g["trabajos"] and g["trabajos"][-1]["fin"] is None:
    if st.button("✅ Terminar trabajo"):
        trabajo = g["trabajos"][-1]
        trabajo["fin"] = now()
        delta = trabajo["fin"] - g["estado_inicio"]
        g["tiempos"]["Trabajando"] += delta
        g["estado"] = "Viajando"
        g["estado_inicio"] = now()

# ================================
# GENERAR REPORTES
# ================================

if st.button("📄 Generar PDF y CSV"):
    rows = []
    for t in g["trabajos"]:
        real = (t["fin"] - t["inicio"]).total_seconds() / 60 if t["fin"] else 0
        diff = real - t["estimado"]
        rows.append([
            t["cliente"], t["direccion"], t["inicio"].strftime("%H:%M"),
            t["fin"].strftime("%H:%M") if t["fin"] else "",
            t["estimado"], round(real, 2), round(diff, 2)
        ])

    df = pd.DataFrame(rows, columns=["Cliente", "Dirección", "Inicio", "Fin", "Estimado", "Real", "Diferencia"])
    st.download_button("⬇ CSV", df.to_csv(index=False), file_name=f"{grupo}.csv")

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elems = [Paragraph(f"Reporte - {grupo}", styles['Title']), Spacer(1, 12)]

    table = Table([df.columns.tolist()] + df.values.tolist())
    table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 1, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey)
    ]))

    elems.append(table)
    doc.build(elems)

    st.download_button("⬇ PDF", buffer.getvalue(), file_name=f"{grupo}.pdf")
