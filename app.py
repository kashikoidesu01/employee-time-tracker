import streamlit as st
from streamlit_autorefresh import st_autorefresh
import pandas as pd
from datetime import datetime, date
from zoneinfo import ZoneInfo
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

# --- CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="Registro de Tiempo de Empleados", page_icon="⏱️", layout="centered")
st.title("⏱️ Registro de Tiempo de Empleados")

# --- ESTILOS ---
st.markdown("""
    <style>
    .big-font { font-size:22px !important; font-weight:bold; }
    .timer { font-size:28px !important; color:#00FFAA; }
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

if "turnos_completos" not in st.session_state:
    st.session_state.turnos_completos = {}

if "form_abierto" not in st.session_state:
    st.session_state.form_abierto = None

# --- VARIABLES ---
usuario = st.radio("Selecciona tu tipo de usuario:", ["dispatcher", "boss"])
grupo = st.selectbox("Selecciona grupo de trabajo:", list(st.session_state.grupos.keys()))

# --- HORA ACTUAL ---
def hora_actual():
    return datetime.now(ZoneInfo("America/New_York")).strftime("%I:%M:%S %p")

# --- INICIAR / PAUSAR / DETENER ---
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("▶️ Iniciar turno"):
        st.session_state.turnos[grupo] = {
            "inicio": datetime.now(ZoneInfo("America/New_York")),
            "pausado": False,
            "pausa_inicio": None,
            "tiempo_total": 0,
            "pausas": []
        }
        st.success(f"Turno iniciado para {grupo}")

with col2:
    if grupo in st.session_state.turnos and st.button("⏸️ Pausar / Reanudar"):
        turno = st.session_state.turnos[grupo]
        if not turno["pausado"]:
            # --- Pausar turno ---
            turno["pausado"] = True
            turno["pausa_inicio"] = datetime.now(ZoneInfo("America/New_York"))
            st.session_state.form_abierto = grupo  # Abrir formulario
            st.info(f"{grupo} pausó trabajo a las {hora_actual()}")
        else:
            # --- Reanudar turno ---
            pausa_duracion = (datetime.now(ZoneInfo("America/New_York")) - turno["pausa_inicio"]).total_seconds()
            turno["tiempo_total"] += pausa_duracion
            turno["pausado"] = False
            st.session_state.form_abierto = None  # Cerrar formulario
            st.info(f"{grupo} reanudó trabajo a las {hora_actual()}")

with col3:
    if grupo in st.session_state.turnos and st.button("⏹️ Terminar"):
        turno = st.session_state.turnos.pop(grupo)
        duracion = (datetime.now(ZoneInfo("America/New_York")) - turno["inicio"]).total_seconds() - turno["tiempo_total"]
        turno["duracion"] = duracion
        st.session_state.turnos_completos[grupo] = turno
        st.success(f"✅ Turno finalizado para {grupo}")

# --- FORMULARIO DE PAUSA ---
if st.session_state.form_abierto:
    g = st.session_state.form_abierto
    st.markdown(f"### 📝 Registrar pausa para {g}")
    with st.form(f"form_{g}"):
        cliente = st.text_input("Cliente", value="")
        direccion = st.text_input("Dirección", value="")
        hora_inicio = st.text_input("Hora de inicio", value="")  # AHORA VACÍO
        tiempo_estimado = st.text_input("Tiempo estimado (min)", value="")
        tiempo_viaje = st.text_input("Tiempo de viaje (min)", value="")
        guardar = st.form_submit_button("Guardar información de pausa")

        if guardar:
            pausa_data = {
                "cliente": cliente,
                "direccion": direccion,
                "hora_inicio": hora_inicio,
                "tiempo_estimado": tiempo_estimado,
                "tiempo_viaje": tiempo_viaje
            }
            st.session_state.turnos[g]["pausas"].append(pausa_data)
            st.session_state.form_abierto = None
            st.success(f"Pausa registrada para {g}")

# --- REFRESCO AUTOMÁTICO ---
st_autorefresh(interval=1000, key="refresco_cronometro")

# --- MOSTRAR GRUPOS ACTIVOS ---
st.markdown("---")
st.subheader("🟢 Grupos activos")

for g, t in st.session_state.turnos.items():
    estado = "Pausado" if t["pausado"] else "Trabajando"
    tiempo_transcurrido = (
        (datetime.now(ZoneInfo("America/New_York")) - t["inicio"]).total_seconds() - t["tiempo_total"]
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

# --- BOTÓN FINAL PARA GENERAR REPORTES ---
st.markdown("---")
if st.button("📄 Terminar y generar reporte (CSV / PDF)"):
    if st.session_state.turnos_completos:
        datos = []
        for g, t in st.session_state.turnos_completos.items():
            for pausa in t.get("pausas", []):
                duracion = str(pd.to_timedelta(t["duracion"], unit="s"))
                datos.append({
                    "grupo": g,
                    "cliente": pausa.get("cliente", ""),
                    "direccion": pausa.get("direccion", ""),
                    "hora_inicio": pausa.get("hora_inicio", ""),
                    "tiempo_estimado": pausa.get("tiempo_estimado", ""),
                    "tiempo_viaje": pausa.get("tiempo_viaje", ""),
                    "duracion": duracion
                })

        df = pd.DataFrame(datos)
        csv_filename = f"reporte_{date.today().strftime('%Y-%m-%d')}.csv"
        df.to_csv(csv_filename, index=False)

        # --- GENERAR PDF ---
        pdf_filename = f"reporte_{date.today().strftime('%Y-%m-%d')}.pdf"
        doc = SimpleDocTemplate(
            pdf_filename,
            pagesize=letter,
            rightMargin=30,
            leftMargin=30,
            topMargin=30,
            bottomMargin=30
        )
        elements = []
        styles = getSampleStyleSheet()
        style_title = styles["Title"]

        elements.append(Paragraph("Reporte Diario de Actividades", style_title))
        elements.append(Spacer(1, 12))

        data = [["Grupo", "Cliente", "Dirección", "Hora inicio", "Tiempo estimado", "Tiempo viaje", "Duración (HH:MM:SS)"]]
        for _, row in df.iterrows():
            data.append(list(row.values))

        col_widths = [1.2*inch, 1.3*inch, 1.6*inch, 1*inch, 1.2*inch, 1.2*inch, 1.2*inch]
        table = Table(data, colWidths=col_widths, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.2, 0.4, 0.6)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("WORDWRAP", (0, 0), (-1, -1), None)
        ]))

        elements.append(table)
        doc.build(elements)

        st.download_button("⬇️ Descargar CSV", open(csv_filename, "rb"), file_name=csv_filename)
        st.download_button("⬇️ Descargar PDF", open(pdf_filename, "rb"), file_name=pdf_filename)
        st.success("✅ Reporte generado correctamente.")
    else:
        st.info("No hay datos para generar el reporte.")
