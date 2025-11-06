# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python application for processing SIAT (Sistema de Facturación) XML invoice files from the Bolivian tax authority and inserting them into a MySQL database, with optional upload to DigitalOcean Spaces for cloud storage.

## Core Architecture

### Main Processing Flow (src/xml_to_sql.py)

The application follows this workflow:

1. **XML Discovery**: Search for XML files by CUF (Código Único de Factura) code in nested directory structures
2. **XML Parsing**: Parse XML to extract invoice header data (cabecera) including dates, amounts, customer info
3. **Validation**: Optional validation of invoice number and total amount against expected values
4. **SQL Generation**: Generate INSERT statement for `factura_siat` table with proper NULL handling
5. **Database Insertion**: Interactive prompt to insert into MySQL database
6. **Cloud Upload**: Interactive prompt to upload XML to DigitalOcean Spaces with public-read ACL

### Key Functions

- `procesar_e_insertar_factura()`: Main entry point for processing invoices (lines 319-386)
- `process_factura_by_cuf()`: Finds XML by CUF and validates/generates SQL (lines 282-317)
- `parse_xml_and_generate_insert()`: Parses XML and builds SQL INSERT query (lines 154-207)
- `find_xml_by_cuf()`: Recursively searches for XML files (lines 209-221)
- `upload_to_spaces()`: Uploads XML to DigitalOcean Spaces with explicit ContentType (lines 233-280)
- `run_connectivity_checks()`: Tests both database and Spaces connectivity (lines 45-151)

## Configuration

### Database & Spaces Config (db_config.ini)

IMPORTANT: `db_config.ini` contains sensitive credentials and is gitignored. Use `db_config.ini.example` as template.

Required sections:
- `[DATABASE]`: MySQL connection (host, user, password, database, port, charset)
- `[SPACES]`: DigitalOcean Spaces S3-compatible storage (region_name, endpoint_url, aws_access_key_id, aws_secret_access_key, bucket_name, upload_folder)

## Common Commands

### Install Dependencies
```bash
uv sync
```

This will create a `.venv` virtual environment and install all dependencies from `pyproject.toml`:
- `mysql-connector-python`: MySQL database connector
- `boto3`: AWS SDK for DigitalOcean Spaces

### Run Invoice Processing
```bash
uv run example.py
```

Edit `example.py` to configure:
- `cuf_factura`: Unique invoice code to search for
- `id_factura_db`: Database ID for the invoice record
- `pedido_opcional`: Optional purchase order number
- `numero_factura`: Invoice number for validation
- `total_factura`: Expected total amount for validation
- `ruta_base_xml`: Base path to search for XML files (supports nested directories)

### Test Connectivity
```bash
uv run test_do_connection.py
```

Tests both MySQL database and DigitalOcean Spaces connectivity with detailed error reporting.

### Set Up Configuration
```bash
cp db_config.ini.example db_config.ini
# Edit db_config.ini with actual credentials
```

### Add New Dependencies
```bash
uv add package-name
```

### Update Dependencies
```bash
uv lock --upgrade
uv sync
```

## Database Schema Notes

### factura_siat Table

The INSERT query targets a table named `factura_siat` with these key fields:
- `factura_id`: Primary/foreign key linking to main factura table
- `cuf`: Código Único de Factura (unique invoice identifier)
- `cufd`: CUFD code
- `codigoSucursal`, `codigoPuntoVenta`: Branch and point of sale codes
- `fechaEmision`: Emission date (parsed from ISO format)
- Customer fields: `codigoTipoDocumentoIdentidad`, `numeroDocumento`, `complemento`, `nombreRazonSocial`
- Payment: `codigoMetodoPago`, `numeroTarjeta`
- Amounts: `montoTotal`, `montoTotalMoneda`, `tipoCambio`
- `pedido`: Optional purchase order reference
- `leyenda`, `cafc`: Optional fields
- `codigoRecepcion`: Fixed value "siatDesktop"
- `created_at`: Timestamp from XML fechaEmision

## XML File Organization

The application searches recursively from `ruta_base_xml` for files named `{CUF}.xml`. Common structure:
```
C:\Users\willy\OneDrive\Documentos\xml\
  2025/
    [CUF].xml
    [CUF].xml
  2024/
    [CUF].xml
```

## Error Handling & Validation

- **Validation failures**: If `numero_factura` or `total_factura` don't match XML, processing stops with error message (lines 301-311)
- **Database errors**: Handles MySQL-specific error codes (1049 for unknown database, 1045 for access denied)
- **Spaces errors**: Handles S3 client errors with specific suggestions for InvalidAccessKeyId, SignatureDoesNotMatch, NoSuchBucket
- **NULL handling**: Carefully handles optional XML fields that may be missing (complemento, leyenda, cafc, etc.)

## Interactive Prompts

The main processing function prompts for user confirmation before:
1. Database insertion (line 342)
2. Spaces upload (line 365)

This prevents accidental data operations during development/testing.

## DigitalOcean Spaces Integration

- Files uploaded with `ACL: 'public-read'` and `ContentType: 'application/xml'`
- Public URL format: `{endpoint_url}/{bucket_name}/{upload_folder}{filename}`
- Upload path constructed from config `upload_folder` (e.g., "obs/xmls/") + XML filename
