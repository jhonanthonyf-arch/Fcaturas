import streamlit as st
import pandas as pd
import os
from datetime import datetime
from fpdf import FPDF

# Configuración de la página
st.set_page_config(page_title="Generador de Facturas", page_icon="📄", layout="centered")

st.title("📄 Generador Automático de Facturas")
st.write("Selecciona los productos y cantidades para generar la factura.")

# Rutas de la "base de datos" en CSV
DB_FACTURAS = "facturas_db.csv"       # Un registro por factura (encabezado + totales)
DB_DETALLE = "detalle_facturas_db.csv"  # Una fila por producto dentro de cada factura

# 1. Cargar la base de datos de productos desde el CSV generado
@st.cache_data
def cargar_datos():
    return pd.read_csv('productos_facturacion.csv')

try:
    df_productos = cargar_datos()
except FileNotFoundError:
    st.error("No se encontró el archivo 'productos_facturacion.csv'. Por favor, asegúrate de colocarlo en el mismo directorio.")
    st.stop()


# --- Utilidades de persistencia (base de datos en CSV) ---

def guardar_factura_en_db(nro_factura, fecha_factura, nombre_cliente, ruc_dni,
                           df_detalle, subtotal, iva, total_general):
    """Agrega la factura al CSV de encabezados y sus líneas al CSV de detalle."""
    encabezado = pd.DataFrame([{
        "nro_factura": nro_factura,
        "fecha": fecha_factura.strftime("%Y-%m-%d"),
        "cliente": nombre_cliente,
        "ruc_dni": ruc_dni,
        "subtotal": subtotal,
        "iva": iva,
        "total": total_general,
        "fecha_registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }])

    existe_encabezado = os.path.isfile(DB_FACTURAS)
    encabezado.to_csv(DB_FACTURAS, mode="a", header=not existe_encabezado, index=False)

    detalle = df_detalle.copy()
    detalle.insert(0, "nro_factura", nro_factura)
    existe_detalle = os.path.isfile(DB_DETALLE)
    detalle.to_csv(DB_DETALLE, mode="a", header=not existe_detalle, index=False)


def generar_pdf_factura(nro_factura, fecha_factura, nombre_cliente, ruc_dni,
                         df_detalle, subtotal, iva, total_general):
    """Genera el PDF de la factura y devuelve los bytes listos para descargar."""
    pdf = FPDF()
    pdf.add_page()

    # Encabezado
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 12, "FACTURA", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(2)

    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, f"N° de Factura: {nro_factura}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, f"Fecha de Emisión: {fecha_factura.strftime('%d/%m/%Y')}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, f"Cliente: {nombre_cliente}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, f"RUC / DNI: {ruc_dni}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # Tabla de productos
    col_widths = [80, 35, 25, 35]
    headers = ["Producto", "Precio Unit.", "Cantidad", "Total"]

    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(230, 230, 230)
    for w, h in zip(col_widths, headers):
        pdf.cell(w, 8, h, border=1, align="C", fill=True)
    pdf.ln()

    pdf.set_font("Helvetica", "", 10)
    for _, fila in df_detalle.iterrows():
        pdf.cell(col_widths[0], 8, str(fila["Producto"]), border=1)
        pdf.cell(col_widths[1], 8, f"${fila['Precio Unitario']:,.2f}", border=1, align="R")
        pdf.cell(col_widths[2], 8, str(int(fila["Cantidad"])), border=1, align="C")
        pdf.cell(col_widths[3], 8, f"${fila['Total']:,.2f}", border=1, align="R")
        pdf.ln()

    pdf.ln(4)

    # Totales alineados a la derecha
    ancho_total = sum(col_widths[:3])
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(ancho_total, 7, "Subtotal:", align="R")
    pdf.cell(col_widths[3], 7, f"${subtotal:,.2f}", align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.cell(ancho_total, 7, "IVA (18%):", align="R")
    pdf.cell(col_widths[3], 7, f"${iva:,.2f}", align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(ancho_total, 9, "TOTAL:", align="R")
    pdf.cell(col_widths[3], 9, f"${total_general:,.2f}", align="R", new_x="LMARGIN", new_y="NEXT")

    return bytes(pdf.output())


# 2. Datos del Cliente e Información de la Factura
st.subheader("👤 Datos de Facturación")
col_cliente, col_factura = st.columns(2)

with col_cliente:
    nombre_cliente = st.text_input("Nombre del Cliente / Empresa", "Juan Pérez")
    ruc_dni = st.text_input("RUC / DNI / Identificación", "12345678901")

with col_factura:
    fecha_factura = st.date_input("Fecha de Emisión", datetime.now())
    nro_factura = st.text_input("Número de Factura", "FAC-0001")

st.markdown("---")

# 3. Selección de Productos
st.subheader("🛒 Selección de Productos")

productos_seleccionados = st.multiselect(
    "Elige los productos a incluir en la factura:",
    options=df_productos['producto'].sort_values().tolist()
)

lineas_factura = []

if productos_seleccionados:
    st.write("Define las cantidades:")
    for producto in productos_seleccionados:
        row = df_productos[df_productos['producto'] == producto].iloc[0]
        precio_unitario = float(row['precio'])

        col_p, col_c, col_t = st.columns([2, 1, 1])
        with col_p:
            st.text(f"{producto} (${precio_unitario:,.2f} c/u)")
        with col_c:
            cantidad = st.number_input(f"Cantidad para {producto}", min_value=1, value=1, step=1, key=f"cant_{producto}")
        with col_t:
            total_linea = precio_unitario * cantidad
            st.text(f"Total: ${total_linea:,.2f}")

        lineas_factura.append({
            "Producto": producto,
            "Precio Unitario": precio_unitario,
            "Cantidad": cantidad,
            "Total": total_linea
        })

    st.markdown("---")

    # 4. Cálculos Financieros
    df_detalle = pd.DataFrame(lineas_factura)
    subtotal = df_detalle['Total'].sum()
    iva = subtotal * 0.18  # Asumiendo un 18% de IVA/IGV, puedes ajustarlo
    total_general = subtotal + iva

    # 5. Vista Previa de la Factura Impresa
    st.subheader("📝 Vista Previa de la Factura")

    factura_box = st.container(border=True)
    with factura_box:
        st.markdown(f"### **FACTURA: {nro_factura}**")
        st.write(f"**Fecha:** {fecha_factura.strftime('%d/%m/%Y')}")
        st.write(f"**Cliente:** {nombre_cliente} | **ID/RUC:** {ruc_dni}")
        st.markdown("---")

        st.dataframe(
            df_detalle.set_index("Producto"),
            use_container_width=True
        )

        st.markdown("---")
        c1, c2 = st.columns([3, 1])
        with c2:
            st.write(f"**Subtotal:** ${subtotal:,.2f}")
            st.write(f"**IVA (18%):** ${iva:,.2f}")
            st.markdown("### **Total: ${:,.2f}**".format(total_general))

    # 6. Procesar factura: guardar en CSV "base de datos" y generar PDF
    if st.button("💾 Procesar y Registrar Factura", type="primary"):
        guardar_factura_en_db(
            nro_factura, fecha_factura, nombre_cliente, ruc_dni,
            df_detalle, subtotal, iva, total_general
        )
        pdf_bytes = generar_pdf_factura(
            nro_factura, fecha_factura, nombre_cliente, ruc_dni,
            df_detalle, subtotal, iva, total_general
        )
        st.session_state["ultima_factura_pdf"] = pdf_bytes
        st.session_state["ultima_factura_nombre"] = f"{nro_factura}.pdf"
        st.success(f"Factura {nro_factura} para {nombre_cliente} registrada exitosamente en la base de datos.")

    # Botón de descarga (aparece una vez procesada la factura)
    if "ultima_factura_pdf" in st.session_state:
        st.download_button(
            label="⬇️ Descargar Factura en PDF",
            data=st.session_state["ultima_factura_pdf"],
            file_name=st.session_state["ultima_factura_nombre"],
            mime="application/pdf",
        )
else:
    st.info("Por favor, selecciona al menos un producto arriba para empezar a estructurar la factura.")

# 7. Historial de facturas registradas
st.markdown("---")
st.subheader("📚 Historial de Facturas Registradas")

if os.path.isfile(DB_FACTURAS):
    df_historial = pd.read_csv(DB_FACTURAS)
    st.dataframe(df_historial, use_container_width=True)
else:
    st.caption("Aún no se ha registrado ninguna factura.")
