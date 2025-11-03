import streamlit as st
from streamlit_autorefresh import st_autorefresh
import pandas as pd
from datetime import datetime, date
from zoneinfo import ZoneInfo
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
import io

# --- CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="Registro de Tiempo", page_icon="⏱️", layout="centered")
st.title("⏱️ Registro de Tiempo de Empleados")

# --- ESTILOS ---
st.markdown("""
    <style>
    .timer { font-size:28px !important; color:#00FFAA; font-weight:bold; }
    </style>
""", unsafe_allow_html=True)

# --- DATOS BASE ---
if "grupos" not in st.session_state:
    st.session_state.grupos = {
        "Grupo Elizabeth": ["Elizabeth", "Cindy"],
        "Grupo Cecilia": ["Cecilia", "Ofelia"],
        "Grupo Shirley": ["Shirley", "Kelly"],
    }

if "turnos" not in st.session_state:
    st.session_state.turnos = {}

if "pausas" not in st.session_state:
    st.session_state.pausas = []

if "mostrar_formulario" not in st.session_state:
    st.session_state.mostrar_formulario = None

# --- VARIABLES ---
usuario = st.radio("Selecciona tu tipo de usuario:", ["dispatcher", "boss"])
grupo = st.selectbox("Selecciona grupo de trabajo:", list(st.session_state.grupos.keys()))

# --- FUNCIÓN HORA LOCAL ---
def hora_actual():
    tz = ZoneInfo("America/New_York")  # Maryland / East Coast
    return datetime.now(tz)

# --- REFRESCO AUTOMÁTICO ---
st_autorefresh(interval=1000, key="refresco_cronometro")

# --- BOTONES DE CONTROL ---
col1, col2, col3 = st.columns(3)

# INICIAR
with col1:
    if st.button("▶️ Iniciar turno"):
        st.session_state.turnos[grupo] = {
            "inicio": hora_actual(),
            "pausado": False,
            "pausa_inicio": None,
            "tiempo_total": 0
        }
        st.success(f"Turno iniciado para {grupo}")
        st.session_state.mostrar_formulario = None

# PAUSAR / REANUDAR
with col2:
    if grupo in st.session_state.turnos:
        turno = st.session_state.turnos[grupo]
        if st.button("⏸️ Pausar / Reanudar"):
            if not turno["pausado"]:
                turno["pausado"] = True
                turno["pausa_inicio"] = hora_actual()
                st.session_state.mostrar_formulario = grupo  # <<< mantener abierto el formulario
            else:
                pausa_duracion = (hora_actual() - turno["pausa_inicio"]).total_seconds()
                turno["tiempo_total"] += pausa_duracion
                turno["pausado"] = False
                st.session_state.mostrar_formulario = None
                st.info(f"{grupo} reanudó trabajo a las {hora_actual().strftime('%I:%M:%S %p')}")

# DETENER
with col3:
    if grupo in st.session_state.turnos and st.button("⏹️ Terminar"):
        turno = st.session_state.turnos.pop(grupo)
        if turno["pausado"]:
            pausa_duracion = (hora_actual() - turno["pausa_inicio"]).total_seconds()
            turno["tiempo_total"] += pausa_duracion
        duracion = (hora_actual() - turno["inicio"]).total_seconds() - turno["tiempo_total"]
        horas, resto = divmod(duracion, 3600)
        minutos, segundos = divmod(resto, 60)
        st.success(f"✅ Turno finalizado para {grupo}. Duración: {int(horas):02}:{int(minutos):02}:{int(segundos):02}")
        st.session_state.mostrar_formulario = None

# --- FORMULARIO DE PAUSA (persistente) ---
if st.session_state.mostrar_formulario == grupo:
    with st.expander(f"📝 Registrar servicio para {grupo}", expanded=True):
        cliente = st.text_input("Cliente:", key=f"cliente_{grupo}")
        direccion = st.text_input("Dirección:", key=f"direccion_{grupo}")
        tiempo_estimado = st.text_input("Tiempo estimado (min):", key=f"estimado_{grupo}")
        tiempo_viaje = st.text_input("Tiempo de viaje (min):", key=f"viaje_{grupo}")

        if st.button("💾 Guardar servicio", key=f"guardar_{grupo}"):
            turno = st.session_state.turnos[grupo]
            st.session_state.pausas.append({
                "fecha": date.today().strftime("%Y-%m-%d"),
                "grupo": grupo,
                "cliente": cliente,
                "direccion": direccion,
                "hora_inicio": turno["inicio"].strftime("%I:%M:%S %p"),
                "tiempo_estimado": tiempo_estimado,
                "tiempo_viaje": tiempo_viaje,
                "tiempo_trabajado": round((hora_actual() - turno["inicio"]).total_seconds() / 60, 2)
            })
            st.session_state.mostrar_formulario = None
            st.success("✅ Servicio guardado correctamente.")

# --- MOSTRAR GRUPOS ACTIVOS ---
st.markdown("---")
st.subheader("🟢 Grupos activos")

for g, t in st.session_state.turnos.items():
    estado = "⏸️ Pausado" if t["pausado"] else "🟢 Trabajando"
    tiempo_transcurrido = (
        (hora_actual() - t["inicio"]).total_seconds() - t["tiempo_total"]
        if not t["pausado"]
        else (t["pausa_inicio"] - t["inicio"]).total_seconds() - t["tiempo_total"]
    )
    horas, resto = divmod(max(0, tiempo_transcurrido), 3600)
    minutos, segundos = divmod(resto, 60)
    st.markdown(f"""
    **{g}**  
    - Estado: {estado}  
    - Inicio: {t["inicio"].strftime("%I:%M:%S %p")}  
    - Tiempo transcurrido: <span class='timer'>{int(horas):02}:{int(minutos):02}:{int(segundos):02}</span>
    """, unsafe_allow_html=True)

# --- GUARDAR Y DESCARGAR REGISTROS ---
if st.button("💾 Terminar y generar reporte (CSV / PDF)"):
    if st.session_state.pausas:
        df = pd.DataFrame(st.session_state.pausas)
        archivo_csv = f"registros_{date.today().strftime('%Y-%m-%d')}.csv"
        df.to_csv(archivo_csv, index=False)

        # Crear PDF limpio
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        elements = []

        elements.append(Paragraph("Reporte Diario de Servicios", styles["Title"]))
        elements.append(Spacer(1, 12))
        data = [df.columns.tolist()] + df.values.tolist()
        tabla = Table(data)
        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        elements.append(tabla)
        doc.build(elements)
        pdf_data = buffer.getvalue()
        buffer.close()

        st.success("✅ Registros guardados correctamente.")
        st.download_button("⬇️ Descargar CSV", data=df.to_csv(index=False), file_name=archivo_csv, mime="text/csv")
        st.download_button("⬇️ Descargar PDF", data=pdf_data, file_name=archivo_csv.replace(".csv", ".pdf"), mime="application/pdf")
    else:
        st.info("No hay registros para guardar.")
