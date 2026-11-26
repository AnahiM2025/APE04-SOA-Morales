package ec.edu.com;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

/** Notificacion devuelta por GET /api/notificaciones. */
@JsonIgnoreProperties(ignoreUnknown = true)
public record Notificacion(long id, String eventoId, String tipo, Integer ventaId,
                           Integer vehiculoId, String mensaje, String creadaEn) {}
