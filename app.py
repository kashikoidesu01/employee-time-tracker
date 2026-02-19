# ================================
# REGISTRO DE TIEMPO DE EMPLEADOS
# PDF consolidado por grupo
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
# CONFIG
# ================================

TZ = ZoneInfo("America/New_York")
st.set_page_config(page_title="Registro de Tiempo", layout="wide")
st_autorefresh(interval=1000, key="refresh")

# ================================
# UTILS
# ================================

def now():
    return datetime.now(TZ)

def format_td(td):
    s = int(td.total_seconds())
    return f"{s//3600:02d}:{(s%3600)//60:02d}:{s%60:02d}"

# ================================
# STATE
# ================================

if "grupos" not in st.session_state:
    st.session_state.grupos = {}

if "reporte_generado" not in st.session_state:
    st.session_state.reporte_generado = False

GRUPOS = ["Grupo Elizabeth", "Grupo Cecilia", "Grupo Shirley"]

for g in GRUPOS:
    if g not in st.session_state.grupos:
        st.session_state.grupos[g] = {
            "inicio_jornada": None,
            "estado": "Fuera de turno",
            "estado_inicio": None,
            "jornada_activa": False,
            "trabajos": []
        }

# ================================
# SIDEBAR
# ================================

st.sidebar.title("🕒 Jornada por grupo")

for nombre, g in st.session_state.grupos.items():
    if g["jornada_activa"]:
        st.sidebar.markdown(f"### 👥 {nombre}")
        st.sidebar.markdown(f"⏱ Jornada: {format_td(now()-g['inicio_jornada'])}")
        st.sidebar.markdown(f"⏳ {g['estado']}: {format_td(now()-g['estado_inicio'])}")

# ================================
# UI
# ================================

st.title("⏱ Registro de Tiempo")

grupo_ui = st.selectbox("Grupo activo", GRUPOS)
g = st.session_state.grupos[grupo_ui]

if st.button("▶ Iniciar turno") and not g["jornada_activa"]:
    g["inicio_jornada"] = now()
    g["estado"] = "Viajando"
    g["estado_inicio"] = now()
    g["jornada_activa"] = True

# ================================
# FORMULARIO TRABAJO
# ================================

st.subheader("🧾 Registrar trabajo")

with st.form("trabajo"):
    grupo_trabajo = st.selectbox("Grupo", GRUPOS)
    cliente = st.text_input("Cliente")
    direccion = st.text_input("Dirección")

    col1, col2 = st.columns(2)
    with col1:
        horas = st.number_input("Horas estimadas", min_value=0)
    with col2:
        minutos = st.number_input("Minutos estimados", min_value=0, max_value=59)

    submit = st.form_submit_button("🟢 Iniciar trabajo")

if submit:
    g2 = st.session_state.grupos[grupo_trabajo]
    if g2["jornada_activa"]:
        g2["trabajos"].append({
            "grupo": grupo_trabajo,
            "cliente": cliente,
            "direccion": direccion,
            "inicio_turno": g2["inicio_jornada"],
            "inicio_trabajo": now(),
            "fin_trabajo": None,
            "estimado_min": horas * 60 + minutos,
            "tiempo_real": None
        })
        g2["estado"] = "Trabajando"
        g2["estado_inicio"] = now()

# ================================
# TERMINAR TRABAJO
# ================================

if g["trabajos"] and g["trabajos"][-1]["fin_trabajo"] is None:
    if st.button("✅ Terminar trabajo"):
        t = g["trabajos"][-1]
        t["fin_trabajo"] = now()
        t["tiempo_real"] = now() - t["inicio_trabajo"]
        g["estado"] = "Viajando"
        g["estado_inicio"] = now()

# ================================
# GENERAR REPORTE
# ================================

if st.button("📄 Generar reporte"):
    st.session_state.reporte_generado = True

if st.session_state.reporte_generado:
    rows = []

    for grupo, g in st.session_state.grupos.items():
        for t in g["trabajos"]:
            rows.append([
                t["grupo"],
                t["cliente"],
                t["direccion"],
                t["inicio_turno"].strftime("%H:%M"),
                t["inicio_trabajo"].strftime("%H:%M"),
                f"{t['estimado_min']//60}H {t['estimado_min']%60}MIN",
                format_td(t["tiempo_real"]) if t["tiempo_real"] else ""
            ])

    df = pd.DataFrame(rows, columns=[
        "Grupo", "Cliente", "Dirección",
        "Inicio Turno", "Inicio Trabajo",
        "Estimado", "Tiempo Trabajado"
    ])

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()

    table = Table([df.columns.tolist()] + df.values.tolist())
    table.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 1, colors.grey),
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey)
    ]))

    doc.build([
        Paragraph("Reporte Consolidado por Grupo", styles["Title"]),
        Spacer(1, 12),
        table
    ])

    st.download_button("⬇ Descargar PDF", buffer.getvalue(), "reporte_grupos.pdf")
    st.download_button("⬇ Descargar CSV", df.to_csv(index=False), "reporte_grupos.csv")

