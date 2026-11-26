package ec.edu.com;

import java.time.LocalTime;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.ScheduledFuture;
import java.util.concurrent.TimeUnit;
import javafx.application.Application;
import javafx.application.Platform;
import javafx.beans.property.SimpleStringProperty;
import javafx.collections.FXCollections;
import javafx.collections.ObservableList;
import javafx.geometry.Insets;
import javafx.scene.Scene;
import javafx.scene.control.*;
import javafx.scene.layout.*;
import javafx.stage.Stage;

/**
 * Cliente JavaFX: muestra las notificaciones de venta casi en tiempo real.
 * Sondea GET /api/notificaciones cada 4 s pidiendo solo las nuevas (despuesDeId).
 * Si el servicio cae, informa el error y reintenta; no inventa notificaciones.
 */
public class NotificacionesApp extends Application {
    private static final int INTERVALO_SEGUNDOS = 4;
    private static final DateTimeFormatter HORA = DateTimeFormatter.ofPattern("HH:mm:ss");

    private final ApiClient api = new ApiClient();
    private final ObservableList<Notificacion> datos = FXCollections.observableArrayList();
    private final ScheduledExecutorService ejecutor = Executors.newSingleThreadScheduledExecutor(r -> {
        Thread t = new Thread(r, "sondeo-notificaciones");
        t.setDaemon(true);
        return t;
    });
    private ScheduledFuture<?> sondeo;
    private Long ultimoId = null; // null = aun no se hizo la primera carga
    private int nuevas = 0;

    private final TextField usuario = new TextField();
    private final PasswordField clave = new PasswordField();
    private final Button entrar = new Button("Iniciar sesión");
    private final Button salir = new Button("Cerrar sesión");
    private final Label estado = new Label("Inicie sesión para ver las notificaciones.");
    private final Label contador = new Label("Nuevas desde el inicio: 0");

    @Override
    public void start(Stage stage) {
        usuario.setPromptText("Usuario");
        clave.setPromptText("Contraseña");
        salir.setDisable(true);

        TableView<Notificacion> tabla = new TableView<>(datos);
        tabla.setPlaceholder(new Label("Sin notificaciones."));
        tabla.getColumns().add(col("ID", 70, n -> String.valueOf(n.id())));
        tabla.getColumns().add(col("Tipo", 90, n -> n.tipo()));
        tabla.getColumns().add(col("Venta", 70, n -> String.valueOf(n.ventaId() == null ? "—" : n.ventaId())));
        tabla.getColumns().add(col("Vehículo", 80, n -> String.valueOf(n.vehiculoId())));
        tabla.getColumns().add(col("Mensaje", 380, n -> n.mensaje()));
        tabla.getColumns().add(col("Fecha (UTC)", 190, n -> n.creadaEn()));

        HBox barra = new HBox(8, new Label("Usuario"), usuario, new Label("Contraseña"), clave, entrar, salir);
        barra.setPadding(new Insets(10));
        HBox pie = new HBox(20, estado, contador);
        pie.setPadding(new Insets(8, 10, 8, 10));

        BorderPane raiz = new BorderPane(tabla);
        raiz.setTop(barra);
        raiz.setBottom(pie);

        entrar.setDefaultButton(true);
        entrar.setOnAction(e -> iniciarSesion());
        salir.setOnAction(e -> cerrarSesion("Sesión cerrada."));

        stage.setTitle("Notificaciones de ventas — JavaFX");
        stage.setScene(new Scene(raiz, 960, 560));
        stage.show();
    }

    private TableColumn<Notificacion, String> col(String titulo, double ancho,
                                                  java.util.function.Function<Notificacion, String> f) {
        TableColumn<Notificacion, String> c = new TableColumn<>(titulo);
        c.setPrefWidth(ancho);
        c.setCellValueFactory(x -> new SimpleStringProperty(f.apply(x.getValue())));
        return c;
    }

    private void iniciarSesion() {
        String u = usuario.getText().trim(), p = clave.getText();
        if (u.isEmpty() || p.isEmpty()) { estado.setText("Ingrese usuario y contraseña."); return; }
        entrar.setDisable(true);
        estado.setText("Iniciando sesión…");
        ejecutor.submit(() -> {
            try {
                api.iniciarSesion(u, p);
                Platform.runLater(() -> {
                    clave.clear();
                    salir.setDisable(false);
                    datos.clear();
                    ultimoId = null;
                    nuevas = 0;
                    contador.setText("Nuevas desde el inicio: 0");
                    estado.setText("Sesión iniciada. Cargando notificaciones…");
                });
                sondeo = ejecutor.scheduleWithFixedDelay(this::sondear, 0, INTERVALO_SEGUNDOS, TimeUnit.SECONDS);
            } catch (ApiClient.ApiException ex) {
                Platform.runLater(() -> { estado.setText(ex.getMessage()); entrar.setDisable(false); });
            }
        });
    }

    /** Se ejecuta en el hilo del ejecutor; toda actualizacion de la UI va por Platform.runLater. */
    private void sondear() {
        try {
            List<Notificacion> lista = api.listar(ultimoId);
            Platform.runLater(() -> aplicar(lista));
        } catch (ApiClient.ApiException ex) {
            if (ex.codigo == 401) {
                Platform.runLater(() -> cerrarSesion(ex.getMessage()));
            } else {
                Platform.runLater(() -> estado.setText(ex.getMessage() + " Reintentando…"));
            }
        } catch (RuntimeException ex) {
            Platform.runLater(() -> estado.setText("Error inesperado al consultar notificaciones."));
        }
    }

    private void aplicar(List<Notificacion> lista) {
        if (ultimoId == null) {
            // Primera carga: la API entrega las ultimas N, mas recientes primero.
            datos.setAll(lista);
            ultimoId = lista.stream().mapToLong(Notificacion::id).max().orElse(0L);
        } else {
            // Siguientes: solo las posteriores a ultimoId, en orden ascendente; la mas nueva arriba.
            for (Notificacion n : lista) {
                datos.add(0, n);
                ultimoId = Math.max(ultimoId, n.id());
                nuevas++;
            }
            contador.setText("Nuevas desde el inicio: " + nuevas);
        }
        estado.setText("Conectado · " + datos.size() + " notificación(es) · actualizado " + LocalTime.now().format(HORA));
    }

    private void cerrarSesion(String mensaje) {
        if (sondeo != null) sondeo.cancel(false);
        api.cerrarSesion();
        datos.clear();
        ultimoId = null;
        salir.setDisable(true);
        entrar.setDisable(false);
        estado.setText(mensaje);
    }

    @Override
    public void stop() { ejecutor.shutdownNow(); }
}
