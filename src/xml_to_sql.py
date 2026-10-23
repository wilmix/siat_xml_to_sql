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

def run_connectivity_checks(config_file_path="db_config.ini"):
    """
    Prueba la conexión a la base de datos y a DigitalOcean Spaces.
    """
    print("--- Iniciando Pruebas de Conectividad ---")
    db_connection_ok = False
    spaces_connection_ok = False

    # --- Prueba de Conexión a la Base de Datos ---
    print("\\n--- Prueba de Conexión a la Base de Datos ---")
    try:
        db_config = get_db_config(config_file_path)
        print(f"Configuración de Base de Datos cargada desde '{config_file_path}':")
        print(f"  Host: {db_config.get('host')}")
        print(f"  User: {db_config.get('user')}")
        print(f"  Database: {db_config.get('database')}")
        # No mostrar la contraseña

        print(f"Intentando conectar a la base de datos '{db_config.get('database')}' en '{db_config.get('host')}'...")
        cnx = connect_to_db(db_config) # This function already tries to connect to the specific DB
        
        if cnx and cnx.is_connected():
            print(f"¡Conexión exitosa a la base de datos '{db_config.get('database')}'!")
            # Adicionalmente, podríamos verificar si la base de datos realmente existe
            # consultando el catálogo, pero connect_to_db ya falla si la DB no existe.
            # cursor = cnx.cursor()
            # cursor.execute(f"SHOW DATABASES LIKE '{db_config.get('database')}';")
            # result = cursor.fetchone()
            # if result:
            #     print(f"La base de datos '{db_config.get('database')}' existe en el servidor.")
            # else:
            #     print(f"ADVERTENCIA: La conexión al servidor fue exitosa, pero la base de datos '{db_config.get('database')}' no parece existir.")
            # cursor.close()
            cnx.close()
            db_connection_ok = True
        else:
            # connect_to_db ya imprime un error si falla
            print("Fallo al conectar con la base de datos (ver mensaje anterior si existe).")
            
    except FileNotFoundError:
        print(f"Error: Archivo de configuración '{config_file_path}' no encontrado para la sección [DATABASE].")
    except ValueError as e: 
        print(f"Error en la sección [DATABASE] del archivo de configuración: {e}")
    except mysql.connector.Error as err:
        print(f"Error de MySQL al conectar/verificar la base de datos: {err}")
        if err.errno == 1049: # Error code for "Unknown database"
             print(f"  Detalle: La base de datos '{db_config.get('database', 'N/A')}' no existe en el servidor '{db_config.get('host', 'N/A')}'.")
        elif err.errno == 1045: # Error code for "Access denied"
            print(f"  Detalle: Acceso denegado para el usuario '{db_config.get('user', 'N/A')}' en '{db_config.get('host', 'N/A')}'. Verifica usuario y contraseña.")
    except Exception as e:
        print(f"Un error inesperado ocurrió durante la prueba de conexión a la BD: {e}")
    print("--- Prueba de Base de Datos Finalizada ---")

    # --- Prueba de Conexión a DigitalOcean Spaces --- (Código existente de test_spaces_connection)
    print("\\n--- Prueba de Conexión a DigitalOcean Spaces ---")
    try:
        spaces_config = get_spaces_config(config_file_path)
        print(f"Configuración de Spaces cargada desde '{config_file_path}':")
        print(f"  Endpoint URL: {spaces_config.get('endpoint_url')}")
        print(f"  Region Name: {spaces_config.get('region_name')}")
        print(f"  Access Key ID: {spaces_config.get('aws_access_key_id')[:5]}... (oculto)")

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
        spaces_connection_ok = True

    except FileNotFoundError:
        print(f"Error: Archivo de configuración '{config_file_path}' no encontrado para la sección [SPACES].")
    except ValueError as e: 
        print(f"Error en la configuración de Spaces: {e}")
    except (NoCredentialsError, PartialCredentialsError):
        print("Error: Credenciales de AWS/Spaces no encontradas o incompletas.")
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
    except Exception as e:
        print(f"Un error inesperado ocurrió durante la prueba de conexión a Spaces: {e}")
    
    print("--- Prueba de Spaces Finalizada ---")
    print("\\n--- Resumen de Pruebas de Conectividad ---")
    print(f"Conexión a Base de Datos: {'ÉXITO' if db_connection_ok else 'FALLO'}")
    print(f"Conexión a DigitalOcean Spaces: {'ÉXITO' if spaces_connection_ok else 'FALLO'}")
    print("-----------------------------------------")
    return db_connection_ok and spaces_connection_ok


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

def _texto_o_none(elemento):
    """Devuelve el texto de un elemento XML, o None si está vacío/ausente/nil."""
    if elemento is None:
        return None
    texto = elemento.text
    if texto is None or texto.strip() == "":
        return None
    return texto


def build_insert_factura_siat(xml_string, factura_id, pedido=None):
    """
    Construye un INSERT PARAMETRIZADO para factura_siat a partir del XML.
    Replica exactamente el patrón de las cargas manuales previas ('siatDesktop'):
      - codigoRecepcion = 'siatDesktop'
      - created_at = fechaEmision (sin milisegundos)
      - complemento/cafc/numeroTarjeta = NULL cuando el XML viene vacío/nil
      - leyenda y razón social con mojibake reparado
    Devuelve una tupla (sql, params) lista para cursor.execute(sql, params).
    """
    root = ET.fromstring(xml_string)
    cab = root.find(".//cabecera")

    cuf = cab.findtext("cuf")
    cufd = cab.findtext("cufd")
    codigoSucursal = cab.findtext("codigoSucursal")
    codigoPuntoVenta = cab.findtext("codigoPuntoVenta")
    fechaEmision = cab.findtext("fechaEmision")
    codigoTipoDocumentoIdentidad = cab.findtext("codigoTipoDocumentoIdentidad")
    numeroDocumento = cab.findtext("numeroDocumento")
    complemento = _texto_o_none(cab.find("complemento"))
    nombreRazonSocial = fix_mojibake(cab.findtext("nombreRazonSocial"))
    leyenda = fix_mojibake(_texto_o_none(cab.find("leyenda")))
    cafc = _texto_o_none(cab.find("cafc"))
    codigoMetodoPago = _texto_o_none(cab.find("codigoMetodoPago"))
    numeroTarjeta = _texto_o_none(cab.find("numeroTarjeta"))
    montoTotal = _texto_o_none(cab.find("montoTotal"))
    montoTotalMoneda = _texto_o_none(cab.find("montoTotalMoneda"))
    tipoCambio = _texto_o_none(cab.find("tipoCambio"))

    # created_at = fechaEmision sin milisegundos (patrón confirmado de filas siatDesktop)
    created_at = fechaEmision.split(".")[0].replace("T", " ")

    codigoRecepcion = "siatDesktop"
    pedido_val = pedido if pedido else None

    sql = (
        "INSERT INTO factura_siat ("
        "factura_id, cuf, cufd, codigoSucursal, codigoPuntoVenta, fechaEmision, "
        "codigoTipoDocumentoIdentidad, numeroDocumento, complemento, nombreRazonSocial, "
        "leyenda, pedido, cafc, codigoRecepcion, codigoMetodoPago, numeroTarjeta, "
        "montoTotal, montoTotalMoneda, tipoCambio, created_at"
        ") VALUES ("
        "%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
    )
    params = (
        factura_id, cuf, cufd, codigoSucursal, codigoPuntoVenta, fechaEmision,
        codigoTipoDocumentoIdentidad, numeroDocumento, complemento, nombreRazonSocial,
        leyenda, pedido_val, cafc, codigoRecepcion, codigoMetodoPago, numeroTarjeta,
        montoTotal, montoTotalMoneda, tipoCambio, created_at,
    )
    return sql, params


def execute_sql_params(cnx, sql_query, params):
    """Ejecuta un INSERT/consulta parametrizada y hace commit."""
    cursor = None
    try:
        cursor = cnx.cursor()
        cursor.execute(sql_query, params)
        cnx.commit()
        print(f"INSERT ejecutado correctamente (filas afectadas: {cursor.rowcount}).")
        return True
    except mysql.connector.Error as err:
        print(f"Error ejecutando el INSERT: {err}")
        cnx.rollback()
        return False
    finally:
        if cursor:
            cursor.close()


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


def fix_mojibake(texto):
    """
    Repara texto UTF-8 doble-codificado (mojibake), p.ej. 'Ley NÂ° 453' -> 'Ley N° 453'.
    Solo actúa si detecta la firma clásica del problema ('Ã' o 'Â'); si la reparación
    falla, devuelve el texto original sin modificar.
    """
    if not texto or ("Ã" not in texto and "Â" not in texto):
        return texto
    try:
        return texto.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return texto


def _leer_cabecera_min(xml_path):
    """
    Lee de forma ligera los campos de la cabecera necesarios para emparejar
    un XML con una factura: montoTotal, numeroDocumento y fecha de emisión.
    Devuelve un dict o None si el archivo no se puede parsear.
    """
    try:
        root = ET.parse(xml_path).getroot()
        cab = root.find(".//cabecera")
        if cab is None:
            return None
        monto = cab.findtext("montoTotal")
        nit = cab.findtext("numeroDocumento")
        femision = cab.findtext("fechaEmision")
        return {
            "cuf": cab.findtext("cuf"),
            "montoTotal": float(monto) if monto else None,
            "numeroDocumento": nit,
            "fecha": femision.split("T")[0] if femision else None,
        }
    except Exception:
        return None


def find_xml_for_factura(base_path, total, nit, fecha):
    """
    Busca en base_path el/los XML cuya cabecera calce con una factura:
      montoTotal ~= total  AND  numeroDocumento == nit  AND  fecha(emision) == fecha.
    'fecha' debe ser 'YYYY-MM-DD'. Acota la búsqueda a base_path/AAAA/MM cuando existe.
    Devuelve una lista de rutas (puede tener 0, 1 o varios elementos).
    """
    try:
        anio, mes, _ = fecha.split("-")
    except (ValueError, AttributeError):
        anio = mes = None

    # Acotar la búsqueda a la carpeta del año/mes si existe; si no, todo el árbol.
    raiz_busqueda = base_path
    if anio and mes:
        candidato = os.path.join(base_path, anio, mes)
        if os.path.isdir(candidato):
            raiz_busqueda = candidato

    # Agrupar por CUF: los archivos duplicados (mismo CUF, distinto nombre) NO
    # son ambigüedad real. Para cada CUF se prefiere el archivo canónico {CUF}.xml.
    por_cuf = {}
    for root, _dirs, files in os.walk(raiz_busqueda):
        for nombre in files:
            if not nombre.lower().endswith(".xml"):
                continue
            ruta = os.path.join(root, nombre)
            datos = _leer_cabecera_min(ruta)
            if not datos or datos["montoTotal"] is None or not datos["cuf"]:
                continue
            if datos["numeroDocumento"] != str(nit):
                continue
            if datos["fecha"] != fecha:
                continue
            if abs(datos["montoTotal"] - float(total)) > 0.01:
                continue
            cuf = datos["cuf"]
            canonico = os.path.basename(ruta).lower() == f"{cuf}.xml".lower()
            if cuf not in por_cuf or canonico:
                por_cuf[cuf] = ruta
    return list(por_cuf.values())


def get_factura_by_id(db_config, id_factura):
    """
    Lee una fila de la tabla 'factura' por idFactura (solo lectura).
    Devuelve un dict con los campos usados para el emparejamiento, o None si no existe.
    """
    cnx = connect_to_db(db_config)
    if not cnx:
        return None
    cursor = None
    try:
        cursor = cnx.cursor(dictionary=True)
        cursor.execute(
            "SELECT idFactura, nFactura, total, fechaFac, ClienteNit, "
            "ClienteFactura, anulada FROM factura WHERE idFactura = %s",
            (id_factura,),
        )
        return cursor.fetchone()
    except mysql.connector.Error as err:
        print(f"Error consultando la factura {id_factura}: {err}")
        return None
    finally:
        if cursor:
            cursor.close()
        cnx.close()


def get_pedido_from_egresos(db_config, id_factura):
    """
    Obtiene (solo lectura) el número de pedido/PO de la factura desde el egreso
    de inventario enlazado: factura_egresos -> egresos.clientePedido.
    Devuelve el pedido (sin espacios) si hay exactamente uno no vacío; None en otro caso.
    """
    cnx = connect_to_db(db_config)
    if not cnx:
        return None
    cursor = None
    try:
        cursor = cnx.cursor()
        cursor.execute(
            "SELECT DISTINCT TRIM(e.clientePedido) "
            "FROM factura_egresos fe "
            "JOIN egresos e ON e.idegresos = fe.idegresos "
            "WHERE fe.idFactura = %s AND TRIM(COALESCE(e.clientePedido, '')) <> ''",
            (id_factura,),
        )
        valores = [row[0] for row in cursor.fetchall()]
        return valores[0] if len(valores) == 1 else None
    except mysql.connector.Error as err:
        print(f"Aviso: no se pudo leer el pedido desde egresos: {err}")
        return None
    finally:
        if cursor:
            cursor.close()
        cnx.close()


def cuf_existe_en_db(db_config, cuf):
    """
    Verifica (solo lectura) si un CUF ya está cargado en factura_siat.
    Devuelve True si existe, False si no, o None si hubo error de conexión.
    """
    cnx = connect_to_db(db_config)
    if not cnx:
        return None
    cursor = None
    try:
        cursor = cnx.cursor()
        cursor.execute("SELECT 1 FROM factura_siat WHERE cuf = %s LIMIT 1", (cuf,))
        return cursor.fetchone() is not None
    except mysql.connector.Error as err:
        print(f"Error verificando el CUF en factura_siat: {err}")
        return None
    finally:
        if cursor:
            cursor.close()
        cnx.close()

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

def subir_xml_a_spaces(config_file, xml_path):
    """
    Sube un XML a DigitalOcean Spaces usando la carpeta configurada en [SPACES].

    La clave se arma con upload_folder + nombre del archivo, por lo que re-subir el
    mismo XML sobrescribe el objeto existente (no lo duplica).
    Devuelve True si la subida fue exitosa, False en caso contrario.
    """
    try:
        spaces_config = get_spaces_config(config_file)
    except FileNotFoundError:
        print(f"Error: Archivo de configuración '{config_file}' no encontrado para la sección [SPACES].")
        return False
    except ValueError as e:
        print(f"Error en la sección [SPACES] del archivo de configuración: {e}")
        return False

    upload_folder = spaces_config.get("upload_folder", "obs/xmls/")
    if upload_folder and not upload_folder.endswith("/"):
        upload_folder += "/"
    spaces_key = f"{upload_folder}{os.path.basename(xml_path)}"

    print(f"Intentando subir '{os.path.basename(xml_path)}' a Spaces en la ruta: '{spaces_config['bucket_name']}/{spaces_key}'...")
    success, public_url = upload_to_spaces(spaces_config, xml_path, spaces_key)
    return success


def cargar_factura_siat(id_factura, base_path, config_file, pedido=None, cuf_override=None, solo_spaces=False):
    """
    Flujo optimizado: dado el idFactura de la tabla 'factura', localiza el XML SIAT
    correspondiente (por monto + NIT + fecha), valida, y previa confirmación del usuario
    inserta en factura_siat y opcionalmente sube el XML a Spaces.

    Si el CUF ya existe en factura_siat no se inserta nada, pero se ofrece subir solo el
    XML a Spaces. Con solo_spaces=True se omite por completo la inserción y se sube
    únicamente el XML (útil para recuperar subidas fallidas sin duplicar filas).

    Solo realiza operaciones de LECTURA (SELECT) y, tras confirmación explícita, un INSERT.
    Nunca ejecuta DELETE ni UPDATE.
    """
    db_config = get_db_config(config_file)

    # 1) Leer la factura de la BD (solo lectura)
    factura = get_factura_by_id(db_config, id_factura)
    if not factura:
        print(f"No se encontró ninguna factura con idFactura = {id_factura}.")
        return
    fecha_fac = factura["fechaFac"]
    fecha_str = fecha_fac.strftime("%Y-%m-%d") if hasattr(fecha_fac, "strftime") else str(fecha_fac)

    # Pedido: si no se pasó por parámetro, se obtiene del egreso enlazado.
    if pedido is None:
        pedido = get_pedido_from_egresos(db_config, id_factura)
        if pedido:
            print(f"Pedido obtenido automáticamente del egreso: {pedido}")

    print("--- Factura encontrada en la BD ---")
    print(f"  idFactura : {factura['idFactura']}")
    print(f"  nFactura  : {factura['nFactura']}")
    print(f"  Cliente   : {factura['ClienteFactura']}  (NIT {factura['ClienteNit']})")
    print(f"  Total     : {factura['total']}")
    print(f"  Fecha     : {fecha_str}")
    if factura.get("anulada"):
        print("  ADVERTENCIA: esta factura está marcada como ANULADA.")

    # 2) Localizar el XML
    if cuf_override:
        xml_path = find_xml_by_cuf(cuf_override, base_path)
        if not xml_path:
            print(f"No se encontró el XML para el CUF indicado: {cuf_override}")
            return
    else:
        candidatos = find_xml_for_factura(base_path, factura["total"], factura["ClienteNit"], fecha_str)
        if len(candidatos) == 0:
            print("\nNo se encontró ningún XML que calce (monto + NIT + fecha).")
            print("  Verifica que el XML ya esté descargado o pasa el CUF manualmente (--cuf).")
            return
        if len(candidatos) > 1:
            print(f"\nSe encontraron {len(candidatos)} XML que calzan (facturas idénticas el mismo día):")
            for ruta in candidatos:
                print(f"  - {os.path.basename(ruta)}")
            print("  Vuelve a ejecutar indicando el CUF exacto con --cuf.")
            return
        xml_path = candidatos[0]

    # 3) Leer el XML y validar contra la factura
    with open(xml_path, "r", encoding="utf-8") as fh:
        xml_string = fh.read()
    root = ET.fromstring(xml_string)
    cab = root.find(".//cabecera")
    cuf = cab.findtext("cuf")
    xml_total = float(cab.findtext("montoTotal"))
    xml_nit = cab.findtext("numeroDocumento")
    xml_fecha = cab.findtext("fechaEmision").split("T")[0]

    if abs(xml_total - float(factura["total"])) > 0.01:
        print(f"\nADVERTENCIA: el monto del XML ({xml_total}) no coincide con la factura ({factura['total']}).")
    if xml_nit != str(factura["ClienteNit"]):
        print(f"ADVERTENCIA: el NIT del XML ({xml_nit}) no coincide con la factura ({factura['ClienteNit']}).")
    if xml_fecha != fecha_str:
        print(f"ADVERTENCIA: la fecha del XML ({xml_fecha}) no coincide con la factura ({fecha_str}).")

    # 4) Pre-chequeo de duplicado por CUF (se omite en modo --solo-spaces)
    if not solo_spaces:
        existe = cuf_existe_en_db(db_config, cuf)
        if existe is None:
            print("\nNo se pudo verificar duplicados; se aborta por precaución.")
            return
        if existe is True:
            print("\nEl CUF ya está cargado en factura_siat. No se insertará (sin duplicados).")
            resp = input(f"¿Subir solo el XML '{os.path.basename(xml_path)}' a Spaces? (s/n): ").strip().lower()
            if resp == "s":
                subir_xml_a_spaces(config_file, xml_path)
            else:
                print("Subida a Spaces cancelada por el usuario.")
            return

    # 5) Construir el INSERT parametrizado y mostrar resumen
    sql, params = build_insert_factura_siat(xml_string, id_factura, pedido)
    print("\n--- XML a cargar ---")
    print(f"  Archivo   : {os.path.basename(xml_path)}")
    print(f"  CUF       : {cuf}")
    print(f"  Nº SIAT   : {cab.findtext('numeroFactura')}")
    print(f"  Cliente   : {fix_mojibake(cab.findtext('nombreRazonSocial'))}")
    print(f"  Monto     : {xml_total}")
    print(f"  Pedido    : {pedido if pedido else '(sin pedido)'}")

    # 6) Modo solo Spaces: no se toca la base de datos
    if solo_spaces:
        print("\nModo --solo-spaces: se omite la inserción en factura_siat.")
        subir_xml_a_spaces(config_file, xml_path)
        return

    # 7) Confirmar e insertar
    resp = input("\n¿Insertar esta factura en factura_siat? (s/n): ").strip().lower()
    if resp != "s":
        print("Inserción cancelada por el usuario.")
        return
    cnx = connect_to_db(db_config)
    if not cnx:
        print("No se pudo conectar a la base de datos.")
        return
    ok = execute_sql_params(cnx, sql, params)
    cnx.close()
    if not ok:
        print("No se insertó la factura.")
        return
    print("Factura insertada correctamente en factura_siat.")

    # 8) Subida opcional a Spaces
    resp_sp = input(f"¿Subir el XML '{os.path.basename(xml_path)}' a DigitalOcean Spaces? (s/n): ").strip().lower()
    if resp_sp != "s":
        print("Subida a Spaces cancelada por el usuario.")
        return
    subir_xml_a_spaces(config_file, xml_path)


def process_factura_by_cuf(cuf, factura_id, base_path=".", pedido=None, numero_factura=None, total_factura=None):
    """
    Process invoice by CUF, finding the XML file and generating the SQL insert.
    Validates invoice number and total amount if provided.
    Returns a tuple (sql_query, xml_file_path) if successful, (None, None) otherwise.
    """
    xml_path = find_xml_by_cuf(cuf, base_path)
    if not xml_path:
        print(f"No se encontró el archivo XML para el CUF: {cuf}")
        return None, None
    
    try:
        with open(xml_path, 'r', encoding='utf-8') as file:
            xml_string = file.read()
        
        # Validate invoice number and total amount if provided
        root = ET.fromstring(xml_string)
        cabecera = root.find(".//cabecera")
        
        if numero_factura is not None:
            xml_numero = cabecera.find("numeroFactura").text
            if xml_numero != numero_factura:
                print(f"Error de validación: El número de factura proporcionado ({numero_factura}) no coincide con el XML ({xml_numero})")
                return None, None
        
        if total_factura is not None:
            xml_total = float(cabecera.find("montoTotal").text)
            if abs(xml_total - total_factura) > 0.01:  # Using small epsilon for float comparison
                print(f"Error de validación: El monto total proporcionado ({total_factura}) no coincide con el XML ({xml_total})")
                return None, None
            
        sql_query = parse_xml_and_generate_insert(xml_string, factura_id, pedido)
        return sql_query, xml_path
    except Exception as e:
        print(f"Error procesando el archivo XML: {e}")
        return None, None

def procesar_e_insertar_factura(cuf, factura_id, base_path, config_file, pedido=None, numero_factura=None, total_factura=None):
    """
    Procesa una factura por su CUF, valida los datos si se proporcionan, genera el SQL, 
    opcionalmente la inserta en la BD y opcionalmente sube el XML a DigitalOcean Spaces.
    """
    sql_query, xml_file_path = process_factura_by_cuf(cuf, factura_id, base_path, pedido, numero_factura, total_factura)
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
