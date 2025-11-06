from src.xml_to_sql import procesar_e_insertar_factura

if __name__ == "__main__":
    # --- Configuración de la Factura a Procesar ---
    cuf_factura = "447D97004336CA901C7AFAE366C66201411A70EEC1437D0299D542F74"
    id_factura_db = 111730
    pedido_opcional = "PO 125806"
    numero_factura = "94"
    total_factura =  27845.99


   
    # --- Configuración de Rutas ---
    # Ajusta las rutas según tu estructura de carpetas C:/Users/willy/OneDrive/Desktop/obsFacturas/siat_xml_to_sql/data
    ruta_base_xml = r"C:\Users\willy\OneDrive\Documentos\xml\2025"  # Ajusta esta ruta según tu estructura de carpetas XML
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
