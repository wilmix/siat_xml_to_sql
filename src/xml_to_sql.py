import xml.etree.ElementTree as ET
from datetime import datetime
import os
import configparser
import mysql.connector

def get_db_config(config_file_path="db_config.ini"):
    """Reads database configuration from an INI file."""
    config = configparser.ConfigParser()
    if not os.path.exists(config_file_path):
        raise FileNotFoundError(f"Configuration file {config_file_path} not found.")
    config.read(config_file_path)
    if 'DATABASE' not in config:
        raise ValueError("DATABASE section not found in the configuration file.")
    return config['DATABASE']

def connect_to_db(db_config):
    """Connects to the MySQL database."""
    try:
        cnx = mysql.connector.connect(**db_config)
        return cnx
    except mysql.connector.Error as err:
        print(f"Error connecting to database: {err}")
        return None

def execute_sql(cnx, sql_query):
    """Executes an SQL query on the given database connection."""
    cursor = None
    try:
        cursor = cnx.cursor()
        cursor.execute(sql_query)
        cnx.commit()
        print("SQL query executed successfully.")
        return True
    except mysql.connector.Error as err:
        print(f"Error executing SQL query: {err}")
        cnx.rollback()
        return False
    finally:
        if cursor:
            cursor.close()

def parse_xml_and_generate_insert(xml_string, factura_id, pedido=None):
    """
    Parse XML content and generate SQL INSERT statement
    """
    root = ET.fromstring(xml_string)
    cabecera = root.find(".//cabecera")
    
    # Extraer datos del XML
    cuf = cabecera.find("cuf").text
    cufd = cabecera.find("cufd").text
    codigoSucursal = cabecera.find("codigoSucursal").text
    codigoPuntoVenta = cabecera.find("codigoPuntoVenta").text
    fechaEmision = cabecera.find("fechaEmision").text
    codigoTipoDocumentoIdentidad = cabecera.find("codigoTipoDocumentoIdentidad").text
    numeroDocumento = cabecera.find("numeroDocumento").text
    complemento_element = cabecera.find("complemento")
    complemento = complemento_element.text if complemento_element is not None and complemento_element.text else "NULL"
    nombreRazonSocial = cabecera.find("nombreRazonSocial").text
    leyenda_element = cabecera.find("leyenda")
    leyenda = leyenda_element.text if leyenda_element is not None and leyenda_element.text else "NULL"
    cafc_element = cabecera.find("cafc")
    cafc = cafc_element.text if cafc_element is not None and cafc_element.text else "NULL"
    codigoRecepcion = "siatDesktop" # Assuming this is a fixed value or needs to be sourced differently
    codigoMetodoPago_element = cabecera.find("codigoMetodoPago")
    codigoMetodoPago = codigoMetodoPago_element.text if codigoMetodoPago_element is not None and codigoMetodoPago_element.text else "NULL"
    numeroTarjeta_element = cabecera.find("numeroTarjeta")
    numeroTarjeta = numeroTarjeta_element.text if numeroTarjeta_element is not None and numeroTarjeta_element.text else "NULL"
    montoTotal_element = cabecera.find("montoTotal")
    montoTotal = montoTotal_element.text if montoTotal_element is not None and montoTotal_element.text else "NULL"
    montoTotalMoneda_element = cabecera.find("montoTotalMoneda")
    montoTotalMoneda = montoTotalMoneda_element.text if montoTotalMoneda_element is not None and montoTotalMoneda_element.text else "NULL"
    tipoCambio_element = cabecera.find("tipoCambio")
    tipoCambio = tipoCambio_element.text if tipoCambio_element is not None and tipoCambio_element.text else "NULL"
    
    # Formatear las fechas para la base de datos
    created_at = fechaEmision.split("T")[0] + " " + fechaEmision.split("T")[1].split('.')[0] # Ensure correct time format
    
    # Construir la consulta INSERT
    # Ensure proper quoting for string values and handling of NULLs
    query = f"""
    INSERT INTO factura_siat (
        factura_id, cuf, cufd, codigoSucursal, codigoPuntoVenta, fechaEmision,
        codigoTipoDocumentoIdentidad, numeroDocumento, complemento, nombreRazonSocial,
        leyenda, pedido, cafc, codigoRecepcion, codigoMetodoPago, numeroTarjeta,
        montoTotal, montoTotalMoneda, tipoCambio, created_at
    ) VALUES (
        {factura_id}, '{cuf}', '{cufd}', {codigoSucursal}, {codigoPuntoVenta}, '{fechaEmision}',
        {codigoTipoDocumentoIdentidad}, '{numeroDocumento}', {f"'{complemento}'" if complemento not in ["NULL", None] else "NULL"}, '{nombreRazonSocial}',
        {f"'{leyenda}'" if leyenda not in ["NULL", None] else "NULL"}, {f"'{pedido}'" if pedido else "NULL"}, {f"'{cafc}'" if cafc not in ["NULL", None] else "NULL"},
        '{codigoRecepcion}', {codigoMetodoPago if codigoMetodoPago not in ["NULL", None] else "NULL"}, {f"'{numeroTarjeta}'" if numeroTarjeta not in ["NULL", None] else "NULL"},
        {montoTotal if montoTotal not in ["NULL", None] else "NULL"}, {montoTotalMoneda if montoTotalMoneda not in ["NULL", None] else "NULL"}, {tipoCambio if tipoCambio not in ["NULL", None] else "NULL"}, '{created_at}'
    );
    """
    return query.strip()

def find_xml_by_cuf(cuf, base_path="."):
    """
    Search for XML file by CUF in any directory under base_path.
    Returns the full path to the XML file if found, None otherwise.
    """
    try:
        for root, dirs, files in os.walk(base_path):
            if f"{cuf}.xml" in files:
                return os.path.join(root, f"{cuf}.xml")
        return None
    except Exception as e:
        print(f"Error searching for XML file: {e}")
        return None

def process_factura_by_cuf(cuf, factura_id, base_path=".", pedido=None):
    """
    Process invoice by CUF, finding the XML file and generating the SQL insert.
    Returns the SQL query if successful, None if file not found.
    """
    xml_path = find_xml_by_cuf(cuf, base_path)
    if not xml_path:
        print(f"No se encontró el archivo XML para el CUF: {cuf}")
        return None
    
    try:
        with open(xml_path, 'r', encoding='utf-8') as file:
            xml_string = file.read()
        return parse_xml_and_generate_insert(xml_string, factura_id, pedido)
    except Exception as e:
        print(f"Error procesando el archivo XML: {e}")
        return None

def procesar_e_insertar_factura(cuf, factura_id, base_path, config_file, pedido=None):
    """
    Procesa una factura por su CUF, genera el SQL y opcionalmente la inserta en la BD.
    """
    sql_query = process_factura_by_cuf(cuf, factura_id, base_path, pedido)
    if not sql_query:
        print(f"No se pudo procesar la factura con CUF: {cuf}")
        return

    print("SQL generado exitosamente:")
    print(sql_query)

    try:
        db_config = get_db_config(config_file)
        print("\\nDatos de conexión a la base de datos:")
        for key, value in db_config.items():
            # Evitar imprimir la contraseña directamente si existe
            if key.lower() == 'password':
                print(f"{key.capitalize()}: ********")
            else:
                print(f"{key.capitalize()}: {value}")

        respuesta = input("¿Desea insertar estos datos en la base de datos? (s/n): ").strip().lower()
        if respuesta == 's':
            cnx = connect_to_db(db_config)
            if cnx:
                if execute_sql(cnx, sql_query):
                    print("Datos insertados correctamente en la base de datos.")
                else:
                    print("No se pudieron insertar los datos en la base de datos.")
                cnx.close()
            else:
                print("No se pudo establecer la conexión con la base de datos.")
        else:
            print("Inserción cancelada por el usuario.")
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print(f"Asegúrese de que el archivo '{config_file}' exista y esté en la ruta correcta.")
    except ValueError as e:
        print(f"Error en el archivo de configuración: {e}")
    except Exception as e:
        print(f"Ocurrió un error inesperado durante la interacción con la base de datos: {e}")
