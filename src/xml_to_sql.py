import xml.etree.ElementTree as ET
from datetime import datetime
import os
import configparser
import mysql.connector
import boto3 # Import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError, ClientError # Import specific exceptions

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

def get_spaces_config(config_file_path="db_config.ini"):
    """Reads DigitalOcean Spaces configuration from an INI file."""
    config = configparser.ConfigParser()
    if not os.path.exists(config_file_path):
        raise FileNotFoundError(f"Configuration file {config_file_path} not found.")
    config.read(config_file_path)
    if 'SPACES' not in config:
        raise ValueError("SPACES section not found in the configuration file.")
    return config['SPACES']

def upload_to_spaces(spaces_config, local_file_path, spaces_file_key):
    """
    Uploads a file to DigitalOcean Spaces.
    Ensures the ContentType is set to application/xml.
    """
    try:
        session = boto3.session.Session()
        client = session.client('s3',
                                region_name=spaces_config['region_name'],
                                endpoint_url=spaces_config['endpoint_url'],
                                aws_access_key_id=spaces_config['aws_access_key_id'],
                                aws_secret_access_key=spaces_config['aws_secret_access_key'])

        client.upload_file(
            Filename=local_file_path,
            Bucket=spaces_config['bucket_name'],
            Key=spaces_file_key,
            ExtraArgs={
                'ACL': 'public-read',
                'ContentType': 'application/xml'  # Explicitly set ContentType
            }
        )
        print(f"Archivo '{os.path.basename(local_file_path)}' subido exitosamente a Spaces como '{spaces_file_key}'.")
        # Construct and print the public URL
        public_url = f"{spaces_config['endpoint_url']}/{spaces_config['bucket_name']}/{spaces_file_key}"
        print(f"URL pública: {public_url}")
        return True, public_url
    except FileNotFoundError:
        print(f"Error: El archivo local '{local_file_path}' no fue encontrado.")
        return False, None
    except (NoCredentialsError, PartialCredentialsError):
        print("Error: Credenciales de AWS/Spaces no encontradas o incompletas. Asegúrese de que estén configuradas en db_config.ini.")
        return False, None
    except ClientError as e:
        # More specific error handling for S3-related errors
        error_code = e.response.get("Error", {}).get("Code")
        if error_code == "InvalidAccessKeyId":
            print("Error: AWS Access Key ID inválido.")
        elif error_code == "SignatureDoesNotMatch":
            print("Error: AWS Secret Access Key inválido.")
        elif error_code == "NoSuchBucket":
            print(f"Error: El bucket '{spaces_config['bucket_name']}' no existe.")
        else:
            print(f"Error de Cliente al subir a Spaces: {e} (Código: {error_code})")
        return False, None
    except Exception as e:
        print(f"Un error inesperado ocurrió al subir a Spaces: {e}")
        return False, None

def process_factura_by_cuf(cuf, factura_id, base_path=".", pedido=None):
    """
    Process invoice by CUF, finding the XML file and generating the SQL insert.
    Returns a tuple (sql_query, xml_file_path) if successful, (None, None) otherwise.
    """
    xml_path = find_xml_by_cuf(cuf, base_path)
    if not xml_path:
        print(f"No se encontró el archivo XML para el CUF: {cuf}")
        return None, None
    
    try:
        with open(xml_path, 'r', encoding='utf-8') as file:
            xml_string = file.read()
        sql_query = parse_xml_and_generate_insert(xml_string, factura_id, pedido)
        return sql_query, xml_path  # Return both SQL query and XML path
    except Exception as e:
        print(f"Error procesando el archivo XML: {e}")
        return None, None

def procesar_e_insertar_factura(cuf, factura_id, base_path, config_file, pedido=None):
    """
    Procesa una factura por su CUF, genera el SQL, opcionalmente la inserta en la BD
    y opcionalmente sube el XML a DigitalOcean Spaces.
    """
    sql_query, xml_file_path = process_factura_by_cuf(cuf, factura_id, base_path, pedido) # Capture xml_file_path
    if not sql_query:
        # Error message already printed by process_factura_by_cuf
        return

    print("SQL generado exitosamente:")
    print(sql_query)

    # Database insertion logic (existing)
    try:
        db_config = get_db_config(config_file)
        print("\\nDatos de conexión a la base de datos:")
        for key, value in db_config.items():
            if key.lower() == 'password':
                print(f"{key.capitalize()}: ********")
            else:
                print(f"{key.capitalize()}: {value}")

        respuesta_db = input("¿Desea insertar estos datos en la base de datos? (s/n): ").strip().lower()
        if respuesta_db == 's':
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
            print("Inserción en la base de datos cancelada por el usuario.")
    except FileNotFoundError:
        print(f"Error: Archivo de configuración '{config_file}' no encontrado para la sección [DATABASE].")
    except ValueError as e:
        print(f"Error en la sección [DATABASE] del archivo de configuración: {e}")
    except Exception as e:
        print(f"Ocurrió un error inesperado durante la interacción con la base de datos: {e}")

    # DigitalOcean Spaces upload logic (new)
    if xml_file_path: # Proceed only if XML path is valid
        try:
            respuesta_spaces = input(f"¿Desea subir el archivo XML '{os.path.basename(xml_file_path)}' a DigitalOcean Spaces? (s/n): ").strip().lower()
            if respuesta_spaces == 's':
                spaces_config = get_spaces_config(config_file)
                file_name = os.path.basename(xml_file_path)
                # Ensure upload_folder ends with a slash if it's not empty
                upload_folder = spaces_config.get('upload_folder', 'obs/xmls/')
                if upload_folder and not upload_folder.endswith('/'):
                    upload_folder += '/'
                spaces_key = f"{upload_folder}{file_name}"
                
                print(f"Intentando subir '{file_name}' a Spaces en la ruta: '{spaces_config['bucket_name']}/{spaces_key}'...")
                success, public_url = upload_to_spaces(spaces_config, xml_file_path, spaces_key)
                # The upload_to_spaces function already prints success/error and URL
            else:
                print("Subida a DigitalOcean Spaces cancelada por el usuario.")
        except FileNotFoundError: 
            print(f"Error: Archivo de configuración '{config_file}' no encontrado para la sección [SPACES].")
        except ValueError as e: 
            print(f"Error en la sección [SPACES] del archivo de configuración: {e}")
        except Exception as e:
            print(f"Ocurrió un error inesperado durante la subida a Spaces: {e}")

def test_spaces_connection(config_file_path="db_config.ini"):
    """
    Prueba la conexión a DigitalOcean Spaces listando los buckets.
    """
    print("\\n--- Iniciando Prueba de Conexión a DigitalOcean Spaces ---")
    try:
        spaces_config = get_spaces_config(config_file_path)
        print(f"Configuración de Spaces cargada desde '{config_file_path}':")
        print(f"  Endpoint URL: {spaces_config.get('endpoint_url')}")
        print(f"  Region Name: {spaces_config.get('region_name')}")
        print(f"  Access Key ID: {spaces_config.get('aws_access_key_id')[:5]}... (oculto)") # Mostrar solo una parte
        # No mostrar la secret key

        session = boto3.session.Session()
        client = session.client('s3',
                                region_name=spaces_config['region_name'],
                                endpoint_url=spaces_config['endpoint_url'],
                                aws_access_key_id=spaces_config['aws_access_key_id'],
                                aws_secret_access_key=spaces_config['aws_secret_access_key'])

        print("Intentando listar buckets...")
        response = client.list_buckets()
        
        print("¡Conexión exitosa a DigitalOcean Spaces!")
        buckets = [bucket['Name'] for bucket in response.get('Buckets', [])]
        if buckets:
            print("Buckets encontrados:")
            for bucket_name in buckets:
                print(f"  - {bucket_name}")
        else:
            print("No se encontraron buckets (o no tienes permiso para listarlos).")
        print("--- Prueba de Conexión Finalizada ---")
        return True

    except FileNotFoundError:
        print(f"Error: Archivo de configuración '{config_file_path}' no encontrado para la sección [SPACES].")
    except ValueError as e: # Para errores en la sección [SPACES] o claves faltantes
        print(f"Error en la configuración de Spaces: {e}")
    except (NoCredentialsError, PartialCredentialsError):
        print("Error: Credenciales de AWS/Spaces no encontradas o incompletas. Asegúrese de que estén configuradas correctamente en db_config.ini.")
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code")
        print(f"Error de Cliente al conectar con Spaces: {e} (Código: {error_code})")
        if error_code == "InvalidAccessKeyId":
            print("  Sugerencia: Verifica tu 'aws_access_key_id'.")
        elif error_code == "SignatureDoesNotMatch":
            print("  Sugerencia: Verifica tu 'aws_secret_access_key' y asegúrate de que el 'endpoint_url' y 'region_name' sean correctos y coincidan.")
            print("              Asegúrate también de que la hora de tu sistema esté sincronizada.")
        elif error_code == "InvalidRequest" and "The authorization mechanism you have provided is not supported. Please use AWS4-HMAC-SHA256" in str(e):
             print("  Sugerencia: El endpoint o la región podrían no estar configurados para usar la firma v4. Revisa la configuración de tu cliente S3 o el endpoint.")
        else:
            print(f"  Detalles del error del cliente: {e}")
    except Exception as e:
        print(f"Un error inesperado ocurrió durante la prueba de conexión a Spaces: {e}")
    
    print("--- Prueba de Conexión Finalizada con Errores ---")
    return False
