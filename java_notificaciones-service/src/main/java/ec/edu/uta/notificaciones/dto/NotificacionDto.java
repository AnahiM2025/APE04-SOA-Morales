package ec.edu.uta.notificaciones.dto;

import ec.edu.uta.notificaciones.model.Notificacion;

/** Respuesta de GET /api/notificaciones (la consume JavaFX). */
public record NotificacionDto(Long id, String eventoId, String tipo, Integer ventaId,
                              Integer vehiculoId, String mensaje, String creadaEn) {
    public static NotificacionDto de(Notificacion n) {
        return new NotificacionDto(n.getId(), n.getEventoId(), n.getTipo(), n.getVentaId(),
                n.getVehiculoId(), n.getMensaje(), n.getCreadaEn().toString() + "Z");
    }
}
