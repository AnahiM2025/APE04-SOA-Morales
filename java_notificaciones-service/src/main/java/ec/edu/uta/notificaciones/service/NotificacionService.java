package ec.edu.uta.notificaciones.service;

import ec.edu.uta.notificaciones.dto.EventoVenta;
import ec.edu.uta.notificaciones.dto.NotificacionDto;
import ec.edu.uta.notificaciones.dto.NotificacionRequest;
import ec.edu.uta.notificaciones.dto.NotificacionResponse;
import ec.edu.uta.notificaciones.model.Notificacion;
import ec.edu.uta.notificaciones.repository.NotificacionRepository;
import java.util.List;
import java.util.Set;
import java.util.UUID;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;

@Service
public class NotificacionService {
    private static final Set<String> TIPOS_PERMITIDOS =
            Set.of("REGISTRO", "ACTUALIZACION", "ELIMINACION", "VENTA");

    private final NotificacionRepository repositorio;

    public NotificacionService(NotificacionRepository repositorio) {
        this.repositorio = repositorio;
    }

    /** Guarda un evento de venta. Retorna false si el eventoId ya existia (reentrega). */
    public boolean registrarEventoVenta(EventoVenta e) {
        if (e.eventoId() == null || e.eventoId().isBlank() || e.eventoId().length() > 64) {
            throw new IllegalArgumentException("eventoId ausente o demasiado largo");
        }
        if (!"VENTA_REALIZADA".equals(e.tipo())) {
            throw new IllegalArgumentException("tipo de evento no soportado");
        }
        if (e.ventaId() == null || e.ventaId() <= 0 || e.vehiculoId() == null || e.vehiculoId() <= 0) {
            throw new IllegalArgumentException("ventaId y vehiculoId deben ser positivos");
        }
        if (repositorio.existsByEventoId(e.eventoId())) {
            return false;
        }
        Notificacion n = new Notificacion();
        n.setEventoId(e.eventoId());
        n.setTipo("VENTA");
        n.setVentaId(e.ventaId());
        n.setVehiculoId(e.vehiculoId());
        n.setMensaje("Venta " + e.ventaId() + " realizada: vehiculo " + e.vehiculoId());
        try {
            repositorio.saveAndFlush(n);
            return true;
        } catch (DataIntegrityViolationException carrera) {
            return false; // otro hilo guardo el mismo eventoId: la restriccion UNIQUE lo impide
        }
    }

    /** Ruta HTTP existente (la usa la API Java de vehiculos para REGISTRO/ACTUALIZACION...). */
    public NotificacionResponse procesar(NotificacionRequest request) {
        if (request.getVehiculoId() == null || request.getVehiculoId() <= 0) {
            throw new IllegalArgumentException("vehiculoId debe estar presente y ser válido");
        }
        if (request.getDestinatario() == null || request.getDestinatario().trim().isEmpty()) {
            throw new IllegalArgumentException("El destinatario no puede estar vacío");
        }
        if (request.getMensaje() == null || request.getMensaje().trim().isEmpty()) {
            throw new IllegalArgumentException("El mensaje no puede estar vacío");
        }
        if (request.getTipo() == null || !TIPOS_PERMITIDOS.contains(request.getTipo().toUpperCase())) {
            throw new IllegalArgumentException("Tipo de notificación no válido");
        }
        Notificacion n = new Notificacion();
        n.setEventoId(UUID.randomUUID().toString());
        n.setTipo(request.getTipo().toUpperCase());
        n.setVehiculoId(request.getVehiculoId());
        // El destinatario se valida pero no se guarda: es un dato personal innecesario.
        String msg = request.getMensaje().trim();
        n.setMensaje(msg.length() > 250 ? msg.substring(0, 250) : msg);
        repositorio.save(n);
        return new NotificacionResponse(true, "ENVIADA", "Notificación procesada correctamente");
    }

    /** Sin despuesDeId: las ultimas N (mas recientes primero). Con despuesDeId: solo las nuevas. */
    public List<NotificacionDto> listar(Long despuesDeId, int limite) {
        var pagina = PageRequest.of(0, limite);
        var datos = (despuesDeId == null)
                ? repositorio.findAllByOrderByIdDesc(pagina)
                : repositorio.findByIdGreaterThanOrderByIdAsc(despuesDeId, pagina);
        return datos.stream().map(NotificacionDto::de).toList();
    }
}
