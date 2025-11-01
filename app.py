import streamlit as st
from streamlit_autorefresh import st_autorefresh
import pandas as pd
from datetime import datetime, date
from zoneinfo import ZoneInfo

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

# --- VARIABLES ---
usuario = st.radio("Selecciona tu tipo de usuario:", ["dispatcher", "boss"])
grupo = st.selectbox("Selecciona grupo de trabajo:", list(st.session_state.grupos.keys()))

# --- FUNCIÓN DE HORA LOCAL ---
def ahora():
    """Devuelve la hora actual con zona horaria de Maryland"""
    return datetime.now(ZoneInfo("America/New_York"))

def hora_actual():
    """Devuelve hora formateada"""
    return ahora().strftime("%I:%M:%S %p")

# --- INICIAR / PAUSAR / DETENER TURNO ---
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("▶️ Iniciar turno"):
        st.session_state.turnos[grupo] = {
            "inicio": ahora(),
            "pausado": False,
            "pausa_inicio": None,
            "tiempo_total": 0
        }
        st.success(f"Turno iniciado para {grupo}")

with col2:
    if grupo in st.session_state.turnos and st.button("⏸️ Pausar / Reanudar"):
        turno = st.session_state.turnos[grupo]
        if not turno["pausado"]:
            turno["pausado"] = True
            turno["pausa_inicio"] = ahora()
            st.warning(f"{grupo} en pausa desde {hora_actual()}")
        else:
            pausa_duracion = (ahora() - turno["pausa_inicio"]).total_seconds()
            turno["tiempo_total"] += pausa_duracion
            turno["pausado"] = False
            st.info(f"{grupo} reanudó trabajo a las {hora_actual()}")

with col3:
    if grupo in st.session_state.turnos and st.button("⏹️ Detener"):
        turno = st.session_state.turnos.pop(grupo)
        if turno["pausado"]:
            pausa_duracion = (ahora() - turno["pausa_inicio"]).total_seconds()
            turno["tiempo_total"] += pausa_duracion
        duracion = (ahora() - turno["inicio"]).total_seconds() - turno["tiempo_total"]
        horas, resto = divmod(duracion, 3600)
        minutos, segundos = divmod(resto, 60)
        st.success(f"✅ Turno finalizado para {grupo}. Duración: {int(horas):02}:{int(minutos):02}:{int(segundos):02}")
        # Guardar registro
        df = pd.DataFrame([{
            "fecha": date.today().strftime("%Y-%m-%d"),
            "grupo": grupo,
            "inicio": turno["inicio"].strftime("%I:%M:%S %p"),
            "fin": ahora().strftime("%I:%M:%S %p"),
            "duración (segundos)": int(duracion)
        }])
        archivo = f"registros_{date.today().strftime('%Y-%m-%d')}.csv"
        try:
            existente = pd.read_csv(archivo)
            df = pd.concat([existente, df], ignore_index=True)
        except FileNotFoundError:
            pass
        df.to_csv(archivo, index=False)

# --- REFRESCO AUTOMÁTICO PARA MOSTRAR EL TIEMPO EN VIVO ---
st_autorefresh(interval=1000, key="refresco_cronometro")

# --- MOSTRAR GRUPOS ACTIVOS ---
st.markdown("---")
st.subheader("🟢 Grupos activos")

for g, t in st.session_state.turnos.items():
    estado = "Pausado" if t["pausado"] else "Trabajando"
    tiempo_transcurrido = (
        (ahora() - t["inicio"]).total_seconds() - t["tiempo_total"]
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

# --- AGREGAR / ELIMINAR GRUPOS ---
st.markdown("---")
with st.expander("➕ Gestionar grupos de trabajo"):
    st.markdown("### Agregar nuevo grupo")
    nuevo_grupo = st.text_input("Nombre del nuevo grupo:")
    empleados = st.text_input("Empleados (separados por coma):")
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
            if grupo_eliminar in st.session_state.turnos:
                st.session_state.turnos.pop(grupo_eliminar, None)
            st.session_state.grupos.pop(grupo_eliminar, None)
            st.success(f"❌ Grupo '{grupo_eliminar}' eliminado correctamente.")
    else:
        st.info("No hay grupos para eliminar.")

# --- BOTÓN PARA GUARDAR Y DESCARGAR REGISTROS ---
st.markdown("---")
if st.button("💾 Guardar registros del día"):
    archivo = f"registros_{date.today().strftime('%Y-%m-%d')}.csv"
    datos = []

    # Guardar tanto turnos activos como pausados
    for g, t in st.session_state.turnos.items():
        duracion = (ahora() - t["inicio"]).total_seconds() - t["tiempo_total"]
        datos.append({
            "fecha": date.today().strftime("%Y-%m-%d"),
            "grupo": g,
            "inicio": t["inicio"].strftime("%I:%M:%S %p"),
            "fin": ahora().strftime("%I:%M:%S %p"),
            "duración (segundos)": int(duracion)
        })

    if datos:
        df = pd.DataFrame(datos)
        csv_data = df.to_csv(index=False).encode("utf-8")

        st.success(f"✅ Registros generados para el {date.today().strftime('%Y-%m-%d')}")

        # Botón para descargar el archivo
        st.download_button(
            label="⬇️ Descargar archivo CSV",
            data=csv_data,
            file_name=archivo,
            mime="text/csv"
        )
    else:
        st.info("No hay grupos activos para guardar.")
