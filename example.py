from src.xml_to_sql import procesar_e_insertar_factura

if __name__ == "__main__":
    # --- Configuración de la Factura a Procesar ---
    cuf_factura = "447D970043365B9E7ED61468A988E40421693879A26D610A2ABFB1F74"
    id_factura_db = 108594
    pedido_opcional = "OL 24003956"
    
    # --- Configuración de Rutas ---
    ruta_base_xml = "./data"  # Ajusta esta ruta según tu estructura de carpetas XML
    archivo_config_db = "db_config.ini" # Ruta al archivo de configuración de la BD

    # --- Procesar e Intentar Insertar Factura ---
    procesar_e_insertar_factura(
        cuf=cuf_factura,
        factura_id=id_factura_db,
        base_path=ruta_base_xml,
        config_file=archivo_config_db,
        pedido=pedido_opcional

    )
