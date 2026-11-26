package ec.edu.uta.notificaciones.config;

import org.springframework.amqp.core.Queue;
import org.springframework.amqp.core.QueueBuilder;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class RabbitConfig {
    /** Cola durable; debe declararse igual que en el publicador (solo durable, sin argumentos). */
    @Bean
    public Queue colaVentas(@Value("${app.rabbit.queue}") String nombre) {
        return QueueBuilder.durable(nombre).build();
    }
}
