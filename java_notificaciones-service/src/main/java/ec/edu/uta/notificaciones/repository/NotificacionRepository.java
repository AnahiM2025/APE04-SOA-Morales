package ec.edu.uta.notificaciones.repository;

import ec.edu.uta.notificaciones.model.Notificacion;
import java.util.List;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

public interface NotificacionRepository extends JpaRepository<Notificacion, Long> {
    boolean existsByEventoId(String eventoId);
    List<Notificacion> findAllByOrderByIdDesc(Pageable pagina);
    List<Notificacion> findByIdGreaterThanOrderByIdAsc(Long id, Pageable pagina);
}
