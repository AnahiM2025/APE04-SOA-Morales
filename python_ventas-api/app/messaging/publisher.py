"""Publicador de eventos de venta hacia RabbitMQ.

Es independiente de los endpoints: el servicio de ventas solo llama a
``publicar_evento_venta`` cuando la venta ya está COMPLETADA y confirmada en MySQL.
La cola es durable y el mensaje es persistente (delivery_mode=2); además se usan
confirmaciones del broker (publisher confirms) para saber si RabbitMQ lo aceptó.
"""
import json
import logging

import pika
from pika.exceptions import AMQPError

from app.config import RABBITMQ_URL, RABBITMQ_QUEUE


class PublicacionError(Exception):
    """RabbitMQ no está disponible o no confirmó el mensaje."""


def publicar_evento_venta(evento: dict) -> None:
    """Publica el evento y retorna solo si RabbitMQ lo confirmó."""
    cuerpo = json.dumps(evento, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    parametros = pika.URLParameters(RABBITMQ_URL)
    parametros.socket_timeout = 3
    parametros.blocked_connection_timeout = 3
    parametros.connection_attempts = 1
    try:
        conexion = pika.BlockingConnection(parametros)
        try:
            canal = conexion.channel()
            # Cola durable: sobrevive a un reinicio del broker.
            canal.queue_declare(queue=RABBITMQ_QUEUE, durable=True)
            # Confirmaciones: basic_publish lanza error si el broker rechaza el mensaje.
            canal.confirm_delivery()
            canal.basic_publish(
                exchange="",
                routing_key=RABBITMQ_QUEUE,
                body=cuerpo,
                properties=pika.BasicProperties(
                    delivery_mode=2,  # mensaje persistente
                    content_type="application/json",
                    message_id=str(evento.get("eventoId", "")),
                ),
                mandatory=True,
            )
        finally:
            try:
                conexion.close()
            except Exception:  # cerrar no debe invalidar una publicación ya confirmada
                pass
    except (AMQPError, OSError) as ex:
        # Se registra el tipo de fallo, nunca el contenido ni las credenciales.
        logging.warning("RabbitMQ no confirmó el evento: %s", type(ex).__name__)
        raise PublicacionError("RabbitMQ no disponible") from ex
