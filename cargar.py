"""
Carga una factura SIAT (XML) en factura_siat a partir del idFactura de la BD.

Flujo:
  1. Lee la factura de la tabla `factura` (producción) por su idFactura.
  2. Localiza automáticamente el XML SIAT que calza por monto + NIT + fecha.
  3. Valida, muestra un resumen y pide confirmación antes de insertar.
  4. Opcionalmente sube el XML a DigitalOcean Spaces.

Solo hace SELECT (lectura) y, tras tu confirmación, un INSERT. Nunca DELETE/UPDATE.

Uso:
  uv run cargar.py 116634
  uv run cargar.py 116634 --pedido "PO 125806"
  uv run cargar.py 116634 --cuf 447D97...      (override si hay 2 facturas idénticas el mismo día)
  uv run cargar.py 116634 --base "C:\\Users\\willy\\OneDrive\\Documentos\\xml"
  uv run cargar.py 116634 --solo-spaces         (no inserta en BD, solo sube el XML a Spaces)
"""
import argparse

from src.xml_to_sql import cargar_factura_siat

# Ruta base donde se buscan los XML (estructura xml\AAAA\MM\D\{CUF}.xml)
RUTA_BASE_XML = r"C:\Users\willy\OneDrive\Documentos\xml"
ARCHIVO_CONFIG = "db_config.ini"


def main():
    parser = argparse.ArgumentParser(
        description="Carga una factura SIAT en factura_siat a partir de su idFactura."
    )
    parser.add_argument("id_factura", type=int, help="idFactura de la tabla `factura`.")
    parser.add_argument("--pedido", default=None, help="Número de pedido/OL/PO (opcional).")
    parser.add_argument(
        "--cuf",
        default=None,
        help="CUF exacto del XML (opcional; úsalo si hay varias facturas idénticas el mismo día).",
    )
    parser.add_argument(
        "--base",
        default=RUTA_BASE_XML,
        help="Ruta base donde buscar los XML.",
    )
    parser.add_argument(
        "--config",
        default=ARCHIVO_CONFIG,
        help="Ruta al archivo de configuración de la BD/Spaces.",
    )
    parser.add_argument(
        "--solo-spaces",
        action="store_true",
        help="No inserta en factura_siat: solo localiza el XML y lo sube a Spaces.",
    )
    args = parser.parse_args()

    cargar_factura_siat(
        id_factura=args.id_factura,
        base_path=args.base,
        config_file=args.config,
        pedido=args.pedido,
        cuf_override=args.cuf,
        solo_spaces=args.solo_spaces,
    )


if __name__ == "__main__":
    main()
