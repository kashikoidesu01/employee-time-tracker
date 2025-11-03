# app.py
import streamlit as st
from streamlit_autorefresh import st_autorefresh
import pandas as pd
from datetime import datetime, date
from zoneinfo import ZoneInfo
import io
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

# -------- CONFIG ----------
TZ = "America/New_York"  # zona horaria Maryland
DATE_FMT = "%Y-%m-%d"
TIME_FMT = "%I:%M:%S %p"

st.set_page_config(page_title="Registro de Tiempo de Empleados", page_icon="⏱️", layout="centered")
st.title("⏱️ Registro de Tiempo de Empleados")

# ---------- Estado inicial ----------
if "grupos" not in st.session_state:
    st.session_state.grupos = {
        "Grupo Elizabeth": ["Elizabeth", "Cindy"],
        "Grupo Cecilia": ["Cecilia", "Ofelia"],
        "Grupo Shirley": ["Shirley", "Kelly"],
    }

# turnos: dict por grupo => { inicio, pausado, pausa_inicio, tiempo_total, activo }
if "turnos" not in st.session_state:
    st.session_state.turnos = {}

# records: lista de dicts guardados al pausar (servicios) y a terminar
if "records" not in st.session_state:
    st.session_state.records = []

# modal flag: nombre del grupo cuya pausa abrió el modal (None si no)
if "show_modal_for" not in st.session_state:
    st.session_state.show_modal_for = None

# csv/pdf bytes para descarga (se setean al terminar)
if "csv_bytes" not in st.session_state:
    st.session_state.csv_bytes = None
if "pdf_bytes" not in st.session_state:
    st.session_state.pdf_bytes = None

# ---------- utilidades ----------
def ahora():
    return datetime.now(ZoneInfo(TZ))

def hora_str(dt):
    return dt.strftime(TIME_FMT)

def hoy_str():
    return date.today().strftime(DATE_FMT)

def append_record(record):
    st.session_state.records.append(record)

def save_record_to_daily_csv(record):
    """Agrega un registro (dict) al CSV diario (registros_YYYY-MM-DD.csv)."""
    archivo = f"registros_{hoy_str()}.csv"
    df = pd.DataFrame([record])
    try:
        existente = pd.read_csv(archivo)
        nuevo = pd.concat([existente, df], ignore_index=True)
    except FileNotFoundError:
        nuevo = df
    nuevo.to_csv(archivo, index=False)

def generate_csv_bytes(records):
    """Devuelve bytes CSV para descarga a partir de records (lista de dict)."""
    df = pd.DataFrame(records)
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    return csv_bytes

def generate_pdf_bytes(records):
    """Genera un PDF (bytes) con tablas por grupo y lista de servicios."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
    styles = getSampleStyleSheet()
    story = []

    title = Paragraph(f"Registros del día {hoy_str()}", styles["Title"])
    story.append(title)
    story.append(Spacer(1, 12))

    if not records:
        story.append(Paragraph("No hay registros.", styles["Normal"]))
        doc.build(story)
        buf.seek(0)
        return buf.getvalue()

    df = pd.DataFrame(records)

    # Agrupar por grupo
    grupos = df["grupo"].unique().tolist()
    for g in grupos:
        story.append(Paragraph(f"Grupo: {g}", styles["Heading2"]))
        sub = df[df["grupo"] == g]

        # tabla de servicios/entradas del grupo
        # columns: fecha, tipo (si existe), cliente, direccion, inicio_servicio, pausa(fin), duracion(seg), est_min, viaje_min
        cols = []
        # determine columns available
        if "cliente" in sub.columns:
            cols = ["fecha", "grupo", "cliente", "direccion", "inicio_servicio", "pausa_en", "duración (segundos)", "tiempo_estimado_min", "tiempo_viaje_min"]
        else:
            cols = ["fecha", "grupo", "inicio", "fin", "duración (segundos)"]

        # Build table header row
        header = [c.replace("_", " ").capitalize() for c in cols]
        data = [header]

        for _, row in sub.iterrows():
            r = []
            for c in cols:
                val = row.get(c, "")
                if pd.isna(val):
                    val = ""
                r.append(str(val))
            data.append(r)

        tbl = Table(data, repeatRows=1)
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#2E4E6E")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("ALIGN", (0,0), (-1,-1), "LEFT"),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 12))

    doc.build(story)
    buf.seek(0)
    return buf.getvalue()

# ---------- UI principal ----------
st_autorefresh(interval=1000, key="refresher")  # refresca cada 1s para cronómetro en vivo

usuario = st.radio("Selecciona tu tipo de usuario:", ["dispatcher", "boss"], horizontal=True)
grupo_sel = st.selectbox("Selecciona grupo de trabajo:", list(st.session_state.grupos.keys()))

c1, c2, c3 = st.columns([1,1,1])
with c1:
    if st.button("▶️ Iniciar turno"):
        if grupo_sel in st.session_state.turnos:
            st.warning("El grupo ya tiene un turno activo.")
        else:
            st.session_state.turnos[grupo_sel] = {
                "inicio": ahora(),
                "pausado": False,
                "pausa_inicio": None,
                "tiempo_total": 0,
                "activo": True
            }
            st.success(f"Turno iniciado para {grupo_sel}")

with c2:
    if st.button("⏸️ Pausar / Reanudar"):
        # Si aún no tiene turno, no hay nada que pausar
        if grupo_sel not in st.session_state.turnos:
            st.info("El grupo no tiene un turno iniciado.")
        else:
            turno = st.session_state.turnos[grupo_sel]
            if not turno["pausado"]:
                # pausar -> abrir modal para ingresar datos del servicio
                turno["pausado"] = True
                turno["pausa_inicio"] = ahora()
                st.session_state.show_modal_for = grupo_sel  # abrir modal en este rerun
            else:
                # reanudar -> acumular tiempo de pausa
                pausa_duracion = (ahora() - turno["pausa_inicio"]).total_seconds()
                turno["tiempo_total"] += pausa_duracion
                turno["pausado"] = False
                turno["pausa_inicio"] = None
                st.success(f"{grupo_sel} reanudó trabajo")

with c3:
    if st.button("🛑 Terminar día & Exportar"):
        # Guardar registros actuales (services saved earlier)
        # Además, agregar resumen final por grupo activo al registro
        # Prepara lista final de registros: tomar st.session_state.records y agregar estado final entries
        final_records = list(st.session_state.records)  # copia
        # Añadir resumen de cada turno activo como 'turn_end' entries
        for g, t in st.session_state.turnos.items():
            # calcular duracion actual excluyendo pausas (incluyendo current pause if existe)
            extra_pause = 0
            if t["pausado"] and t["pausa_inicio"] is not None:
                extra_pause = (ahora() - t["pausa_inicio"]).total_seconds()
            dur = (ahora() - t["inicio"]).total_seconds() - t["tiempo_total"] - extra_pause
            record = {
                "fecha": hoy_str(),
                "grupo": g,
                "inicio": t["inicio"].strftime(TIME_FMT),
                "fin": ahora().strftime(TIME_FMT),
                "duración (segundos)": int(max(0, dur)),
                "tipo": "turn_end"
            }
            final_records.append(record)

        # Guardar CSV en variable y como archivo (opcional)
        csv_bytes = generate_csv_bytes(final_records)
        pdf_bytes = generate_pdf_bytes(final_records)

        # Also persist CSV to server-side file (optional)
        server_file = f"registros_{hoy_str()}.csv"
        try:
            # if file exists, merge
            existente = pd.read_csv(server_file)
            df_final = pd.concat([existente, pd.read_csv(io.BytesIO(csv_bytes))], ignore_index=True)
        except FileNotFoundError:
            df_final = pd.read_csv(io.BytesIO(csv_bytes))
        df_final.to_csv(server_file, index=False)

        # set session bytes for showing download buttons
        st.session_state.csv_bytes = csv_bytes
        st.session_state.pdf_bytes = pdf_bytes

        st.success("✅ Registros consolidados. Descargas disponibles abajo.")

# ---------- Modal: aparece cuando se pausó y show_modal_for está seteado ----------
if st.session_state.show_modal_for:
    gname = st.session_state.show_modal_for
    with st.modal(f"Registrar servicio para {gname}"):
        st.markdown(f"**Grupo:** {gname}")
        # Pre-fill hora de inicio servicio con hora actual (Maryland)
        inicio_serv = ahora()
        col_a, col_b = st.columns([1,1])
        with col_a:
            cliente = st.text_input("Cliente")
            direccion = st.text_input("Dirección del cliente")
        with col_b:
            inicio_input = st.time_input("Hora inicio servicio", value=inicio_serv.time())
            est_min = st.number_input("Tiempo estimado (min)", min_value=0, step=1)
            travel_min = st.number_input("Tiempo de viaje (min)", min_value=0, step=1)

        submitted = st.button("💾 Guardar servicio y cerrar")
        if submitted:
            # calcular tiempo trabajado hasta la pausa (segundos)
            turno = st.session_state.turnos.get(gname)
            if not turno:
                st.error("No existe el turno (posible inconsistencia).")
            else:
                # tiempo hasta pausa = pausa_inicio - inicio - tiempo_total (no contar pausa actual)
                tiempo_hasta_pausa = (turno["pausa_inicio"] - turno["inicio"]).total_seconds() - turno["tiempo_total"]
                rec = {
                    "fecha": hoy_str(),
                    "grupo": gname,
                    "cliente": cliente or "",
                    "direccion": direccion or "",
                    "inicio_servicio": inicio_input.strftime("%I:%M:%S %p"),
                    "pausa_en": turno["pausa_inicio"].strftime(TIME_FMT),
                    "duración (segundos)": int(max(0, tiempo_hasta_pausa)),
                    "tiempo_estimado_min": int(est_min),
                    "tiempo_viaje_min": int(travel_min),
                    "tipo": "service_pause"
                }
                append_record(rec)
                save_record_to_daily_csv(rec)  # also persist immediately to daily CSV
                st.success("✅ Servicio guardado en el registro diario.")
                # Close modal: unset flag
                st.session_state.show_modal_for = None
                # leave turno paused (they will reanudar via button). We DO NOT add pause duration yet to tiempo_total
                # Rerun to refresh UI
                st.experimental_rerun()

# ---------- Mostrar grupos activos y cronometro ----------
st.markdown("---")
st.subheader("🟢 Grupos activos")

if not st.session_state.turnos:
    st.info("No hay grupos activos actualmente.")
else:
    for g, t in st.session_state.turnos.items():
        if not t.get("activo", True):
            continue
        estado = "Pausado" if t["pausado"] else "Trabajando"
        # calcular tiempo transcurrido (no contar pausas acumuladas; si está en pausa actual, no contar desde pausa)
        if t["pausado"]:
            tiempo_transcurrido = (t["pausa_inicio"] - t["inicio"]).total_seconds() - t["tiempo_total"]
        else:
            tiempo_transcurrido = (ahora() - t["inicio"]).total_seconds() - t["tiempo_total"]
        horas, resto = divmod(max(0, tiempo_transcurrido), 3600)
        minutos, segundos = divmod(resto, 60)

        st.markdown(f"**{g}**")
        st.write(f"- Estado: {estado}")
        st.write(f"- Inicio: {t['inicio'].strftime(TIME_FMT)}")
        st.markdown(f"- Tiempo transcurrido: <span style='color:#00ff99;font-weight:bold'>{int(horas):02}:{int(minutos):02}:{int(segundos):02}</span>", unsafe_allow_html=True)
        st.markdown("---")

# ---------- Panel de gestión: agregar / eliminar grupos ----------
with st.expander("➕ Gestionar grupos de trabajo"):
    st.markdown("### Agregar nuevo grupo")
    nuevo_grupo = st.text_input("Nombre del nuevo grupo:", key="new_group_input")
    empleados = st.text_input("Empleados (separados por coma):", key="new_group_emps")
    if st.button("Agregar grupo"):
        if nuevo_grupo and empleados:
            lista = [e.strip() for e in empleados.split(",") if e.strip()]
            st.session_state.grupos[nuevo_grupo] = lista
            st.success(f"✅ Grupo '{nuevo_grupo}' agregado con empleados: {', '.join(lista)}")
        else:
            st.warning("Debes ingresar un nombre y al menos un empleado.")

    st.markdown("---")
    st.markdown("### 🗑️ Eliminar grupo existente")
    if st.session_state.grupos:
        grupo_eliminar = st.selectbox("Selecciona grupo a eliminar:", list(st.session_state.grupos.keys()), key="delbox")
        if st.button("Eliminar grupo"):
            # if active, remove turn too
            st.session_state.turnos.pop(grupo_eliminar, None)
            st.session_state.grupos.pop(grupo_eliminar, None)
            st.success(f"❌ Grupo '{grupo_eliminar}' eliminado correctamente.")
    else:
        st.info("No hay grupos para eliminar.")

# ---------- Botón guardar del día (adicional): muestra descargas si ya generadas ----------
st.markdown("---")
st.subheader("📦 Control diario / Descargas")

# If CSV/PDF bytes exist in session (from Terminar), show download buttons
if st.session_state.csv_bytes:
    st.download_button("⬇️ Descargar CSV del día", st.session_state.csv_bytes, file_name=f"registros_{hoy_str()}.csv", mime="text/csv")
if st.session_state.pdf_bytes:
    st.download_button("⬇️ Descargar PDF del día", st.session_state.pdf_bytes, file_name=f"registros_{hoy_str()}.pdf", mime="application/pdf")

# Also offer manual generation: guardar actual (activa y forzar guardado actual de turnos y records)
if st.button("💾 Generar archivos del día (CSV + PDF)"):
    # combine session records + current turn summaries
    final = list(st.session_state.records)
    for g, t in st.session_state.turnos.items():
        extra_pause = 0
        if t["pausado"] and t["pausa_inicio"] is not None:
            extra_pause = (ahora() - t["pausa_inicio"]).total_seconds()
        dur = (ahora() - t["inicio"]).total_seconds() - t["tiempo_total"] - extra_pause
        final.append({
            "fecha": hoy_str(),
            "grupo": g,
            "inicio": t["inicio"].strftime(TIME_FMT),
            "fin": ahora().strftime(TIME_FMT),
            "duración (segundos)": int(max(0, dur)),
            "tipo": "turn_snapshot"
        })
    st.session_state.csv_bytes = generate_csv_bytes(final)
    st.session_state.pdf_bytes = generate_pdf_bytes(final)
    st.success("✅ Archivos generados. Usa los botones de descarga arriba para bajar CSV/PDF.")

# show a quick preview table of today's saved records (if any)
if st.session_state.records:
    st.markdown("### Vista rápida: registros guardados por pausa")
    df_preview = pd.DataFrame(st.session_state.records)
    st.dataframe(df_preview)

# EOF
