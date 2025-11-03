import streamlit as st
from streamlit_autorefresh import st_autorefresh
import pandas as pd
import datetime
import pytz
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Image, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import io

# --- Configuración de la página ---
st.set_page_config(page_title="Registro de Tiempo de Empleados", layout="centered")

# --- Zona horaria Maryland ---
tz = pytz.timezone("America/New_York")

# --- Inicializar variables en sesión ---
if "grupos" not in st.session_state:
    st.session_state["grupos"] = {"Grupo Elizabeth": {}, "Grupo Cecilia": {}, "Grupo Shirley": {}}
if "servicios" not in st.session_state:
    st.session_state["servicios"] = {}

# --- Título principal ---
st.markdown("## ⏱️ Registro de Tiempo de Empleados")

# --- Selección de usuario y grupo ---
tipo_usuario = st.radio("Selecciona tu tipo de usuario:", ["dispatcher", "boss"])
grupo = st.selectbox("Selecciona grupo de trabajo:", list(st.session_state["grupos"].keys()))
st.divider()

# --- Funciones auxiliares ---
def iniciar_turno(g):
    st.session_state[f"inicio_{g}"] = datetime.datetime.now(tz)
    st.session_state[f"trabajando_{g}"] = True
    st.session_state[f"pausado_{g}"] = False
    st.session_state[f"tiempo_total_{g}"] = 0
    st.session_state[f"ultimo_inicio_{g}"] = datetime.datetime.now(tz)
    st.success(f"✅ Turno iniciado para {g}")

def pausar_reanudar_turno(g):
    if st.session_state.get(f"trabajando_{g}", False):
        if st.session_state.get(f"pausado_{g}", False):
            # Reanudar
            st.session_state[f"pausado_{g}"] = False
            st.session_state[f"ultimo_inicio_{g}"] = datetime.datetime.now(tz)
            st.success(f"▶️ Reanudando turno para {g}")
        else:
            # Pausar
            tiempo = (datetime.datetime.now(tz) - st.session_state[f"ultimo_inicio_{g}"]).total_seconds()
            st.session_state[f"tiempo_total_{g}"] += tiempo
            st.session_state[f"pausado_{g}"] = True
            st.success(f"⏸️ Turno pausado para {g}")
    else:
        st.warning("Primero inicia el turno.")

def detener_turno(g):
    if st.session_state.get(f"trabajando_{g}", False):
        tiempo = (datetime.datetime.now(tz) - st.session_state[f"ultimo_inicio_{g}"]).total_seconds()
        st.session_state[f"tiempo_total_{g}"] += tiempo
        st.session_state[f"trabajando_{g}"] = False
        st.session_state[f"pausado_{g}"] = False
        st.success(f"🛑 Turno detenido para {g}")
    else:
        st.warning("No hay turno activo para detener.")

# --- Botones de control ---
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("▶️ Iniciar turno"):
        iniciar_turno(grupo)
with col2:
    if st.button("⏸️ Pausar / Reanudar"):
        pausar_reanudar_turno(grupo)
with col3:
    if st.button("📤 Terminar día y Exportar"):
        detener_turno(grupo)

# --- Formulario al pausar ---
if st.session_state.get(f"pausado_{grupo}", False):
    with st.expander(f"📝 Registrar servicio para {grupo}", expanded=True):
        cliente = st.text_input(f"Cliente ({grupo})")
        direccion = st.text_input(f"Dirección del cliente ({grupo})")
        hora_inicio_servicio = st.time_input(f"Hora de inicio del servicio ({grupo})")
        tiempo_estimado = st.text_input(f"Tiempo estimado (ej. 1h 30m) ({grupo})")
        tiempo_viaje = st.text_input(f"Tiempo de viaje (ej. 20m) ({grupo})")

        if st.button(f"💾 Guardar servicio ({grupo})"):
            if grupo not in st.session_state["servicios"]:
                st.session_state["servicios"][grupo] = []

            st.session_state["servicios"][grupo].append({
                "grupo": grupo,
                "cliente": cliente,
                "direccion": direccion,
                "hora_inicio_servicio": str(hora_inicio_servicio),
                "tiempo_estimado": tiempo_estimado,
                "tiempo_viaje": tiempo_viaje,
                "tiempo_trabajado": str(datetime.timedelta(seconds=int(st.session_state.get(f"tiempo_total_{grupo}", 0)))),
                "fecha_registro": datetime.datetime.now(tz).strftime("%Y-%m-%d %I:%M:%S %p")
            })
            st.success(f"✅ Servicio guardado para {grupo}")
            st.session_state[f"pausado_{grupo}"] = False

# --- Mostrar grupos activos ---
st.divider()
st.markdown("### 🟢 Grupos activos")

for gname in st.session_state["grupos"].keys():
    if st.session_state.get(f"trabajando_{gname}", False):
        estado = "Pausado" if st.session_state.get(f"pausado_{gname}", False) else "Trabajando"
        tiempo_total = st.session_state.get(f"tiempo_total_{gname}", 0)
        if not st.session_state.get(f"pausado_{gname}", False):
            tiempo_total += (datetime.datetime.now(tz) - st.session_state[f"ultimo_inicio_{gname}"]).total_seconds()

        st.write(f"**{gname}** — Estado: {estado}")
        st.write(f"Tiempo transcurrido: ⏰ {str(datetime.timedelta(seconds=int(tiempo_total)))}")

# --- Exportar todo (PDF / CSV) ---
if st.button("📄 Generar Reporte PDF / CSV"):
    if not any(st.session_state["servicios"].values()):
        st.warning("⚠️ No hay servicios registrados para exportar.")
    else:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        elements.append(Paragraph("<b>REPORTE DE SERVICIOS DIARIOS</b>", styles["Title"]))
        elements.append(Spacer(1, 12))

        # Agregar logos
        elements.append(Image("quality_logo.png", width=70, height=70))
        elements[-1].hAlign = 'LEFT'
        elements.append(Image("happyfeet_logo.png", width=70, height=70))
        elements[-1].hAlign = 'RIGHT'

        for g, servicios in st.session_state["servicios"].items():
            elements.append(Paragraph(f"<b>{g}</b>", styles["Heading2"]))
            data = [["Cliente", "Dirección", "Hora Inicio", "Tiempo Estimado", "Viaje", "Tiempo Trabajado", "Fecha"]]
            for s in servicios:
                data.append([
                    s["cliente"], s["direccion"], s["hora_inicio_servicio"],
                    s["tiempo_estimado"], s["tiempo_viaje"], s["tiempo_trabajado"], s["fecha_registro"]
                ])

            table = Table(data, repeatRows=1)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
            ]))
            elements.append(table)
            elements.append(Spacer(1, 20))

        doc.build(elements)
        pdf_data = buffer.getvalue()
        st.download_button("⬇️ Descargar PDF", pdf_data, file_name="reporte_servicios.pdf", mime="application/pdf")

        # CSV
        csv_buffer = io.StringIO()
        all_data = []
        for g, servicios in st.session_state["servicios"].items():
            for s in servicios:
                all_data.append(s)
        df = pd.DataFrame(all_data)
        df.to_csv(csv_buffer, index=False)
        st.download_button("⬇️ Descargar CSV", csv_buffer.getvalue(), file_name="reporte_servicios.csv", mime="text/csv")
