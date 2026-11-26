package ec.edu.uta.notificaciones.model;

import jakarta.persistence.*;
import java.time.LocalDateTime;
import java.time.ZoneOffset;

/** Aviso persistido. evento_id es unico: un evento reentregado no se duplica. */
@Entity
@Table(name = "notificaciones")
public class Notificacion {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "evento_id", nullable = false, unique = true, length = 64)
    private String eventoId;

    @Column(nullable = false, length = 30)
    private String tipo;

    @Column(name = "venta_id")
    private Integer ventaId;

    @Column(name = "vehiculo_id", nullable = false)
    private Integer vehiculoId;

    @Column(nullable = false, length = 250)
    private String mensaje;

    @Column(name = "creada_en", nullable = false)
    private LocalDateTime creadaEn = LocalDateTime.now(ZoneOffset.UTC);

    public Long getId() { return id; }
    public String getEventoId() { return eventoId; }
    public void setEventoId(String eventoId) { this.eventoId = eventoId; }
    public String getTipo() { return tipo; }
    public void setTipo(String tipo) { this.tipo = tipo; }
    public Integer getVentaId() { return ventaId; }
    public void setVentaId(Integer ventaId) { this.ventaId = ventaId; }
    public Integer getVehiculoId() { return vehiculoId; }
    public void setVehiculoId(Integer vehiculoId) { this.vehiculoId = vehiculoId; }
    public String getMensaje() { return mensaje; }
    public void setMensaje(String mensaje) { this.mensaje = mensaje; }
    public LocalDateTime getCreadaEn() { return creadaEn; }
}
