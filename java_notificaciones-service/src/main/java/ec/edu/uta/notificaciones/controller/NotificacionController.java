package ec.edu.uta.notificaciones.controller;

import ec.edu.uta.notificaciones.dto.NotificacionDto;
import ec.edu.uta.notificaciones.dto.NotificacionRequest;
import ec.edu.uta.notificaciones.dto.NotificacionResponse;
import ec.edu.uta.notificaciones.service.NotificacionService;
import java.util.List;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/notificaciones")
public class NotificacionController {
    private final NotificacionService servicio;

    public NotificacionController(NotificacionService servicio) {
        this.servicio = servicio;
    }

    /** Emisor interno (API de vehiculos). Protegido por X-Notification-Key. */
    @PostMapping
    public ResponseEntity<NotificacionResponse> crear(@RequestBody NotificacionRequest request) {
        return ResponseEntity.status(HttpStatus.CREATED).body(servicio.procesar(request));
    }

    /** Historial para JavaFX. Protegido por JWT (CONSULTA, OPERADOR o ADMIN). */
    @GetMapping
    public List<NotificacionDto> listar(@RequestParam(required = false) Long despuesDeId,
                                        @RequestParam(defaultValue = "100") int limite) {
        return servicio.listar(despuesDeId, Math.min(Math.max(limite, 1), 500));
    }
}
