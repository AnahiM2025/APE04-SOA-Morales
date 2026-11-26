package ec.edu.uta.notificaciones.messaging;

import com.fasterxml.jackson.databind.ObjectMapper;
import ec.edu.uta.notificaciones.dto.EventoVenta;
import ec.edu.uta.notificaciones.service.NotificacionService;
import java.io.IOException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.amqp.AmqpRejectAndDontRequeueException;
import org.springframework.amqp.core.Message;
import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.stereotype.Component;

/**
 * Consumidor real de RabbitMQ. El ack (modo AUTO) ocurre solo si el metodo termina sin
 * excepcion, es decir, despues de guardar en MySQL. Si MySQL falla, el mensaje vuelve a la cola.
 * Un mensaje malformado se descarta (no tiene sentido reintentarlo).
 */
@Component
public class VentaEventListener {
    private static final Logger log = LoggerFactory.getLogger(VentaEventListener.class);
    private final NotificacionService servicio;
    private final ObjectMapper mapper;

    public VentaEventListener(NotificacionService servicio, ObjectMapper mapper) {
        this.servicio = servicio;
        this.mapper = mapper;
    }

    @RabbitListener(queues = "${app.rabbit.queue}")
    public void recibir(Message mensaje) {
        EventoVenta evento;
        try {
            evento = mapper.readValue(mensaje.getBody(), EventoVenta.class);
        } catch (IOException ex) {
            throw new AmqpRejectAndDontRequeueException("Evento ilegible", ex);
        }
        try {
            boolean nueva = servicio.registrarEventoVenta(evento);
            log.info("Evento {} (venta {}) {}", evento.eventoId(), evento.ventaId(),
                    nueva ? "registrado" : "duplicado: se ignora");
        } catch (IllegalArgumentException ex) {
            throw new AmqpRejectAndDontRequeueException("Evento invalido: " + ex.getMessage(), ex);
        }
    }
}
