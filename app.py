# ================================
# REGISTRO DE TIEMPO DE EMPLEADOS
# Jornada por grupo + cronómetros por estado
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
# UTILIDADES
# ================================

def now():
    return datetime.now(TZ)

def format_td(td: timedelta):
    total = int(td.total_seconds())
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

# ================================
# SESSION STATE
# ================================

if "grupos" not in st.session_state:
    st.session_state.grupos = {}

GRUPOS_DISPONIBLES = [
    "Grupo Elizabeth",
    "Grupo Cecilia",
    "Grupo Shirley"
]

for grupo in GRUPOS_DISPONIBLES:
    if grupo not in st.session_state.grupos:
        st.session_state.grupos[grupo] = {
            "inicio_jornada": None,
            "fin_jornada": None,
            "jornada_activa": False,
            "estado": "Fuera de turno",
            "estado_inicio": None,
            "tiempos": {
                "Viajando": timedelta(),
                "Trabajando": timedelta(),
                "Receso": timedelta()
            },
            "trabajos": []
        }

# ================================
# SIDEBAR – CRONÓMETROS
# ================================

st.sidebar.title("🕒 Jornada por grupo")

for grupo, g in st.session_state.grupos.items():
    if g["jornada_activa"]:
        jornada_td = now() - g["inicio_jornada"]
        estado_td = now() - g["estado_inicio"] if g["estado_inicio"] else timedelta()

        st.sidebar.markdown(f"### 👥 {grupo}")
        st.sidebar.markdown(f"⏱ **Jornada:** {format_td(jornada_td)}")
        st.sidebar.markdown(f"⏳ **{g['estado']}:** {format_td(estado_td)}")
        st.sidebar.markdown(f"**Estado:** {g['estado']}")

        if st.sidebar.button(f"🔴 Salida ({grupo})"):
            delta = now() - g["estado_inicio"]
            g["tiempos"][g["estado"]] += delta
            g["fin_jornada"] = now()
            g["jornada_activa"] = False
            g["estado"] = "Fuera de turno"

# ================================
# UI PRINCIPAL
# ================================

st.title("⏱ Registro de Tiempo de Empleados")

rol = st.radio("Selecciona tu tipo de usuario:", ["dispatcher", "boss"])

grupo_ui = st.selectbox("Selecciona grupo de trabajo:", GRUPOS_DISPONIBLES)
g = st.session_state.grupos[grupo_ui]

# ================================
# BOTONES DE TURNO
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
    grupo_trabajo = st.selectbox(
        "Asignar trabajo al grupo:",
        GRUPOS_DISPONIBLES
    )

    cliente = st.text_input("Cliente")
    direccion = st.text_input("Dirección")
    estimado = st.number_input("Tiempo estimado (min)", min_value=0)

    iniciar_trabajo = st.form_submit_button("🟢 Iniciar trabajo")

if iniciar_trabajo:
    g2 = st.session_state.grupos[grupo_trabajo]

    if g2["jornada_activa"]:
        delta = now() - g2["estado_inicio"]
        g2["tiempos"][g2["estado"]] += delta

        g2["trabajos"].append({
            "cliente": cliente,
            "direccion": direccion,
            "inicio": now(),
            "fin": None,
            "estimado": estimado
        })

        g2["estado"] = "Trabajando"
        g2["estado_inicio"] = now()

# ================================
# TERMINAR TRABAJO
# ================================

if g["trabajos"] and g["trabajos"][-1]["fin"] is None:
    if st.button("✅ Terminar trabajo"):
        trabajo = g["trabajos"][-1]
        trabajo["fin"] = now()

        delta = trabajo["fin"] - g["estado_inicio"]
        g["tiempos"]["Trabajando"] += delta

        g["estado"] = "Viajando"
        g["estado_inicio"] = now()

# ================================
# REPORTES
# ================================

if st.button("📄 Generar PDF y CSV"):
    rows = []

    for t in g["trabajos"]:
        real = (
            (t["fin"] - t["inicio"]).total_seconds() / 60
            if t["fin"] else 0
        )
        diff = real - t["estimado"]

        rows.append([
            t["cliente"],
            t["direccion"],
            t["inicio"].strftime("%H:%M"),
            t["fin"].strftime("%H:%M") if t["fin"] else "",
            t["estimado"],
            round(real, 2),
            round(diff, 2)
        ])

    df = pd.DataFrame(
        rows,
        columns=["Cliente", "Dirección", "Inicio", "Fin", "Estimado", "Real", "Diferencia"]
    )

    st.download_button(
        "⬇ Descargar CSV",
        df.to_csv(index=False),
        file_name=f"{grupo_ui}.csv"
    )

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()

    elements = [
        Paragraph(f"Reporte de trabajos – {grupo_ui}", styles["Title"]),
        Spacer(1, 12)
    ]

    table = Table([df.columns.tolist()] + df.values.tolist())
    table.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 1, colors.grey),
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey)
    ]))

    elements.append(table)
    doc.build(elements)

    st.download_button(
        "⬇ Descargar PDF",
        buffer.getvalue(),
        file_name=f"{grupo_ui}.pdf"
    )
