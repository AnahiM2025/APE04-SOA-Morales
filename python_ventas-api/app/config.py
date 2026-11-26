"""Parámetros de integración obtenidos del archivo .env de ventas-api."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Carga el .env desde la raíz del proyecto, aunque se ejecute desde otra ruta.
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")


def requerido(nombre):
    """Obliga a configurar cada parámetro indispensable."""
    valor = os.environ.get(nombre, "")
    if not valor:
        raise RuntimeError(f"Falta configurar {nombre}")
    return valor


# Dirección base de la API Java (en el entorno final: NGINX, puerto 8090).
JAVA_URL = requerido("JAVA_URL").rstrip("/")
# Clave privada que Java verifica en X-Service-Key para las rutas internas.
SERVICE_KEY = requerido("VENTAS_SERVICE_KEY")
# Conexión AMQP a RabbitMQ y cola durable de eventos de venta.
RABBITMQ_URL = requerido("RABBITMQ_URL")
RABBITMQ_QUEUE = os.environ.get("RABBITMQ_QUEUE", "notificaciones.ventas")

if len(SERVICE_KEY) < 32:
    raise RuntimeError("La clave de servicio debe tener al menos 32 caracteres")
if SERVICE_KEY.startswith("COLOCA_"):
    raise RuntimeError("Reemplaza las claves de ejemplo en el archivo .env")
