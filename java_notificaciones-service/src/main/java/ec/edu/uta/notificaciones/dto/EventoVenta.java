package ec.edu.uta.notificaciones.dto;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

/** Contrato del mensaje publicado por FastAPI en la cola notificaciones.ventas. */
@JsonIgnoreProperties(ignoreUnknown = true)
public record EventoVenta(String eventoId, String tipo, Integer ventaId,
                          Integer vehiculoId, String fechaHora) {}
