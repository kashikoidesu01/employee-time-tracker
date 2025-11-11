import streamlit as st
from streamlit_autorefresh import st_autorefresh
import pandas as pd
from datetime import datetime, date
from zoneinfo import ZoneInfo
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
import os
from glob import glob
import time

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
            turno["pausado"] = True
            turno["pausa_inicio"] = datetime.now(ZoneInfo("America/New_York"))
            st.session_state.form_abierto = grupo
            st.info(f"{grupo} pausó trabajo a las {hora_actual()}")
        else:
            pausa_duracion = (datetime.now(ZoneInfo("America/New_York")) - turno["pausa_inicio"]).total_seconds()
            turno["tiempo_total"] += pausa_duracion
            turno["pausado"] = False
            st.session_state.form_abierto = None
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
        hora_inicio = st.text_input("Hora de inicio", value="")
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
# 🔧 solo refrescar si NO hay formulario abierto
if not st.session_state.form_abierto:
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

# --- GENERAR REPORTES ---
st.markdown("---")

if "ultimo_reporte_pdf" not in st.session_state:
    st.session_state.ultimo_reporte_pdf = None
if "ultimo_reporte_csv" not in st.session_state:
    st.session_state.ultimo_reporte_csv = None

##---------------------------------------------------##
if st.button("📄 Terminar y generar reporte (CSV / PDF)"):
    if st.session_state.turnos_completos:
        hoy = date.today()
        datos = []

        for g, t in st.session_state.turnos_completos.items():
            if t["inicio"].date() == hoy:
                duracion_real = (t["duracion"] / 60)  # segundos → minutos

                for pausa in t.get("pausas", []):
                    try:
                        tiempo_estimado = float(pausa.get("tiempo_estimado", 0))
                    except ValueError:
                        tiempo_estimado = 0.0

                    # Calcular diferencia (estimado - real)
                    diferencia = round(tiempo_estimado - duracion_real, 1)

                    duracion_timedelta = pd.to_timedelta(t["duracion"], unit="s")
                    duracion_str = str(duracion_timedelta).split(".")[0].replace("0 days ", "")

                    datos.append({
                        "grupo": g,
                        "cliente": pausa.get("cliente", ""),
                        "direccion": pausa.get("direccion", ""),
                        "hora_inicio": pausa.get("hora_inicio", ""),
                        "tiempo_estimado (min)": tiempo_estimado,
                        "tiempo_viaje (min)": pausa.get("tiempo_viaje", ""),
                        "duracion_real": duracion_str,
                        "diferencia (min)": diferencia
                    })

        if not datos:
            st.warning("⚠️ No hay datos de hoy para generar el reporte.")
            st.stop()

        df = pd.DataFrame(datos)

        # --- NOMBRE ÚNICO PARA ARCHIVOS ---
        from glob import glob
        import os

        fecha_str = hoy.strftime("%m-%d-%y")
        existing_files = glob(f"{fecha_str}-*.pdf")
        next_number = len(existing_files) + 1
        file_suffix = f"{next_number:02d}"

        csv_filename = f"{fecha_str}-{file_suffix}.csv"
        pdf_filename = f"{fecha_str}-{file_suffix}.pdf"

        # --- GUARDAR CSV ---
        df.to_csv(csv_filename, index=False)

        # --- GENERAR PDF ---
        from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, SimpleDocTemplate
        from reportlab.lib.pagesizes import letter, landscape
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch

        doc = SimpleDocTemplate(
            pdf_filename,
            pagesize=landscape(letter),
            rightMargin=30,
            leftMargin=30,
            topMargin=30,
            bottomMargin=30
        )

        elements = []
        styles = getSampleStyleSheet()
        style_title = styles["Title"]
        style_cell = ParagraphStyle(name="CellStyle", fontSize=9, alignment=1, leading=12)

        elements.append(Paragraph(f"Reporte Diario de Actividades – {hoy.strftime('%d/%m/%Y')}", style_title))
        elements.append(Spacer(1, 12))

        data = [["Grupo", "Cliente", "Dirección", "Hora inicio", "Estimado (min)", "Viaje (min)", "Duración", "Dif. (min)"]]

        for _, row in df.iterrows():
            diferencia_valor = row["diferencia (min)"]

            # Color condicional
            if diferencia_valor > 0:
                color_html = "green"
            elif diferencia_valor < 0:
                color_html = "red"
            else:
                color_html = "black"

            diferencia_texto = f"<font color='{color_html}'>{diferencia_valor:+.1f}</font>"

            data.append([
                Paragraph(str(row["grupo"]), style_cell),
                Paragraph(str(row["cliente"]), style_cell),
                Paragraph(str(row["direccion"]), style_cell),
                Paragraph(str(row["hora_inicio"]), style_cell),
                Paragraph(str(row["tiempo_estimado (min)"]), style_cell),
                Paragraph(str(row["tiempo_viaje (min)"]), style_cell),
                Paragraph(str(row["duracion_real"]), style_cell),
                Paragraph(diferencia_texto, style_cell),
            ])

        col_widths = [1.2*inch, 1.5*inch, 2.8*inch, 1.0*inch, 1.2*inch, 1.2*inch, 1.4*inch, 1.0*inch]
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
        ]))

        elements.append(table)
        doc.build(elements)

        # --- GUARDAR NOMBRES DE ARCHIVOS ---
        st.session_state.ultimo_reporte_csv = csv_filename
        st.session_state.ultimo_reporte_pdf = pdf_filename

        st.success(f"✅ Reporte generado correctamente: {pdf_filename}")

# --- BOTONES DE DESCARGA ---
if "ultimo_reporte_csv" in st.session_state and os.path.exists(st.session_state.ultimo_reporte_csv):
    with open(st.session_state.ultimo_reporte_csv, "rb") as csv_file:
        st.download_button(
            "⬇️ Descargar CSV",
            csv_file,
            file_name=st.session_state.ultimo_reporte_csv,
            mime="text/csv",
            key="download_csv"
        )

if "ultimo_reporte_pdf" in st.session_state and os.path.exists(st.session_state.ultimo_reporte_pdf):
    with open(st.session_state.ultimo_reporte_pdf, "rb") as pdf_file:
        st.download_button(
            "⬇️ Descargar PDF",
            pdf_file,
            file_name=st.session_state.ultimo_reporte_pdf,
            mime="application/pdf",
            key="download_pdf"
        )

