# SIAT XML to SQL

Aplicación Python para procesar archivos XML de facturas SIAT (Sistema de Facturación) del Servicio de Impuestos Nacionales de Bolivia, insertarlos en una base de datos MySQL y opcionalmente subirlos a DigitalOcean Spaces.

## Características

- **Procesamiento de XML**: Extrae datos de facturas SIAT desde archivos XML
- **Validación**: Verifica número de factura y monto total contra valores esperados
- **Base de datos MySQL**: Inserta datos estructurados en tabla `factura_siat`
- **Almacenamiento en la nube**: Subida opcional a DigitalOcean Spaces con URLs públicas
- **Búsqueda recursiva**: Encuentra archivos XML por CUF en estructuras de directorios anidadas

## Instalación

### Requisitos previos
- Python 3.11 o superior
- MySQL Server
- Cuenta de DigitalOcean Spaces (opcional)

### Instalación con uv
```bash
uv sync
```

### Instalación tradicional
```bash
pip install -r requirements.txt
```

## Configuración

1. Copia el archivo de configuración de ejemplo:
```bash
cp db_config.ini.example db_config.ini
```

2. Edita `db_config.ini` con tus credenciales:

### Base de datos MySQL
```ini
[DATABASE]
host = tu_servidor_mysql
user = tu_usuario
password = tu_contraseña
database = tu_base_datos
port = 3306
charset = utf8mb4
```

### DigitalOcean Spaces (opcional)
```ini
[SPACES]
region_name = nyc3
endpoint_url = https://nyc3.digitaloceanspaces.com
aws_access_key_id = tu_access_key
aws_secret_access_key = tu_secret_key
bucket_name = tu_bucket
upload_folder = obs/xmls/
```

## Uso

### Procesar una factura

Edita `example.py` con los datos de la factura:

```python
from src.xml_to_sql import procesar_e_insertar_factura

# Configuración de la factura
cuf_factura = "TU_CUF_AQUI"
id_factura_db = 12345
pedido_opcional = "PO 12345"
numero_factura = "92"
total_factura = 1723.50

# Ruta base donde buscar archivos XML
ruta_base_xml = r"C:\Users\tu_usuario\Documents\xml"

# Procesar
procesar_e_insertar_factura(
    cuf=cuf_factura,
    factura_id=id_factura_db,
    base_path=ruta_base_xml,
    config_file="db_config.ini",
    pedido=pedido_opcional,
    numero_factura=numero_factura,
    total_factura=total_factura
)
```

Ejecuta el procesamiento:
```bash
uv run example.py
```

### Probar conectividad

Verifica las conexiones a base de datos y Spaces:
```bash
uv run test_do_connection.py
```

## Estructura del proyecto

```
siat_xml_to_sql/
├── src/
│   └── xml_to_sql.py          # Lógica principal de procesamiento
├── tests/
├── data/                      # Directorio para archivos XML
├── example.py                 # Ejemplo de uso
├── test_do_connection.py      # Pruebas de conectividad
├── db_config.ini.example      # Plantilla de configuración
├── pyproject.toml             # Configuración del proyecto
├── requirements.txt           # Dependencias
└── README.md                  # Este archivo
```

## Dependencias

- `mysql-connector-python`: Conector para MySQL
- `boto3`: SDK de AWS para DigitalOcean Spaces

## Funcionalidades principales

### Procesamiento de XML
- Extrae cabecera de factura (CUF, CUFD, fechas, montos, datos del cliente)
- Maneja campos opcionales con valores NULL apropiados
- Valida número de factura y monto total si se proporcionan

### Base de datos
- Genera consultas INSERT para tabla `factura_siat`
- Maneja conexiones MySQL con manejo de errores específico
- Confirmación interactiva antes de inserción

### Almacenamiento en la nube
- Subida a DigitalOcean Spaces con ACL público
- URLs públicas generadas automáticamente
- Content-Type correcto para archivos XML

## Manejo de errores

- Validación de archivos de configuración
- Manejo específico de errores MySQL (base de datos inexistente, acceso denegado)
- Manejo de errores de DigitalOcean Spaces (credenciales inválidas, bucket inexistente)
- Mensajes de error descriptivos en español

## Licencia

Ver archivo LICENSE para detalles.</content>
<parameter name="filePath">c:\Users\willy\dev\projects\siat_xml_to_sql\README.md
