# ================================
# REGISTRO DE TIEMPO DE EMPLEADOS
# PDF consolidado por grupo
# ================================

import streamlit as st
from streamlit_autorefresh import st_autorefresh
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

# ====== NUEVO: GOOGLE DRIVE ======
import gspread
from google.oauth2.service_account import Credentials

@st.cache_resource
def conectar_drive():
    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ],
    )
    return gspread.authorize(credentials)

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
# GESTIÓN DE ESTADO POR GRUPO
# ================================

st.subheader("🔄 Gestión de estado")

grupo_estado = st.selectbox(
    "Seleccionar grupo para gestionar",
    GRUPOS,
    key="selector_estado"
)

g_estado = st.session_state.grupos[grupo_estado]

if g_estado["jornada_activa"]:

    # Si está trabajando → permitir finalizar
    if g_estado["estado"] == "Trabajando":
        if st.button("Finalizar trabajo", key="btn_finalizar"):
            ahora = now()

            if g_estado["trabajos"]:
                ultimo = g_estado["trabajos"][-1]
                if ultimo.get("fin_trabajo") is None:
                    ultimo["fin_trabajo"] = ahora
                    ultimo["tiempo_real"] = ahora - ultimo["inicio_trabajo"]

            g_estado["estado"] = "Viajando"
            g_estado["estado_inicio"] = ahora

            st.rerun()

    # Si está viajando → solo informativo
    elif g_estado["estado"] == "Viajando":
        st.info("El grupo está viajando. Puede iniciar un nuevo trabajo desde el formulario.")

else:
    st.warning("Este grupo no ha iniciado turno.")

# ================================
# BOTÓN ACTUALIZAR DRIVE (FORMATO EXACTO SHEET)
# ================================

st.divider()
st.subheader("🔄 Sincronizar con Google Drive")

def formato_tiempo(td):
    if not td:
        return "0"
    total_min = int(td.total_seconds() // 60)
    horas = total_min // 60
    minutos = total_min % 60

    if horas > 0 and minutos > 0:
        return f"{horas} H {minutos} MIN"
    elif horas > 0:
        return f"{horas} H"
    elif minutos > 0:
        return f"{minutos} MIN"
    else:
        return "0"

if st.button("🔄 Actualizar Drive"):
    try:
        client = conectar_drive()
        spreadsheet = client.open("PLANILLA_HORAS_REALES_2026")
        worksheet = spreadsheet.worksheet("PLANTILLA")

        mapa_filas = {
            "Grupo Cecilia": 3,
            "Grupo Elizabeth": 13,
            "Grupo Shirley": 23
        }

        for nombre_grupo, g_data in st.session_state.grupos.items():

            if nombre_grupo not in mapa_filas:
                continue

            fila_inicio = mapa_filas[nombre_grupo]
            trabajos = g_data["trabajos"]

            # Limitar a máximo 4 trabajos por bloque
            trabajos = trabajos[:4]

            for i, t in enumerate(trabajos):

                fila = fila_inicio + i

                ordinal = ["1ST JOB", "2ND JOB", "3RD JOB", "4TH JOB"][i]

                tiempo_trabajado = formato_tiempo(t["tiempo_real"])

                # Escribimos exactamente como tu Sheet lo espera
                worksheet.update(f"C{fila}", [[ordinal]])
                worksheet.update(f"D{fila}", [[tiempo_trabajado]])
                worksheet.update(f"E{fila}", [["0"]])  # Tiempo viaje por ahora 0

        st.success("Datos enviados con formato correcto ✅")

    except Exception as e:
        st.error(f"Error al actualizar Drive: {e}")


# ================================
# GENERAR REPORTE PDF
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
