from src.xml_to_sql import procesar_e_insertar_factura

if __name__ == "__main__":
    # --- Configuración de la Factura a Procesar ---
    cuf_factura = "447D9700433669B03A2DC5F9994170361F763B86E54B38CDC8B0D1F74"
    id_factura_db = 108657
    pedido_opcional = "OL 24003889"
    numero_factura = "59"
    total_factura = 88670.40

    #id_factura_db = 108658
    #pedido_opcional = "OL 24003889"
    #numero_factura = "59"
    #total_factura = 31111.2 
    
    # --- Configuración de Rutas ---
    ruta_base_xml = "./data"  # Ajusta esta ruta según tu estructura de carpetas XML
    archivo_config_db = "db_config.ini" # Ruta al archivo de configuración de la BD

    # --- Procesar e Intentar Insertar Factura ---
    procesar_e_insertar_factura(
        cuf=cuf_factura,
        factura_id=id_factura_db,
        base_path=ruta_base_xml,
        config_file=archivo_config_db,
        pedido=pedido_opcional,
        numero_factura=numero_factura,  # Agregado para validación
        total_factura=total_factura    # Agregado para validación
    )
