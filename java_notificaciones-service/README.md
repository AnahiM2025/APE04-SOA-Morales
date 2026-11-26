# Servicio de notificaciones (Spring Boot · puerto 8081)

- **Consumidor RabbitMQ** (`@RabbitListener`) de la cola durable `notificaciones.ventas`; `ack` solo tras guardar en MySQL; deduplicación por `evento_id` (UNIQUE).
- **MySQL**: esquema propio `notificaciones_vehiculos` (tabla `notificaciones`, creada por Hibernate).
- `GET /api/notificaciones[?despuesDeId=N&limite=M]` — historial para JavaFX; exige JWT (CONSULTA, OPERADOR o ADMIN), validado contra `/api/identidad`.
- `POST /api/notificaciones` — ruta interna (API de vehículos), protegida por `X-Notification-Key`.

Variables: `RABBITMQ_USER`, `RABBITMQ_PASSWORD`, `RABBITMQ_QUEUE`, `NOTIFICACIONES_KEY`, `DB_*`, `IDENTIDAD_URL` (por defecto NGINX).
Ejecución: `mvn spring-boot:run`. Si MySQL falla el mensaje vuelve a la cola; si el mensaje es ilegible o inválido se descarta (sin bucle infinito).
