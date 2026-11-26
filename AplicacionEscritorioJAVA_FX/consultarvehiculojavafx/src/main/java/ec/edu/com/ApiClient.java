package ec.edu.com;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.Base64;
import java.util.List;

/**
 * Cliente REST de JavaFX. Habla solo con NGINX (8090). El JWT vive en memoria.
 * Credenciales OAuth del cliente: variables de entorno APP_CLIENT_ID y APP_CLIENT_SECRET.
 */
public final class ApiClient {
    public static final class ApiException extends Exception {
        public final int codigo;
        public ApiException(String mensaje, int codigo) { super(mensaje); this.codigo = codigo; }
    }

    private final HttpClient http = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(4)).build();
    private final ObjectMapper mapper = new ObjectMapper();
    private final String base;
    private volatile String jwt;

    public ApiClient() {
        String url = System.getenv("API_BASE_URL");
        this.base = (url == null || url.isBlank() ? "http://127.0.0.1:8090" : url).replaceAll("/+$", "");
    }

    public boolean haySesion() { return jwt != null; }
    public void cerrarSesion() { jwt = null; }

    public void iniciarSesion(String usuario, String clave) throws ApiException {
        String id = System.getenv("APP_CLIENT_ID"), secreto = System.getenv("APP_CLIENT_SECRET");
        if (id == null || id.isBlank() || secreto == null || secreto.isBlank()) {
            throw new ApiException("Defina las variables de entorno APP_CLIENT_ID y APP_CLIENT_SECRET.", 0);
        }
        String cuerpo = "grant_type=password&username=" + enc(usuario) + "&password=" + enc(clave);
        HttpRequest req = HttpRequest.newBuilder(URI.create(base + "/oauth/token"))
                .timeout(Duration.ofSeconds(8))
                .header("Content-Type", "application/x-www-form-urlencoded")
                .header("Authorization", "Basic " + Base64.getEncoder()
                        .encodeToString((id + ":" + secreto).getBytes(StandardCharsets.UTF_8)))
                .POST(HttpRequest.BodyPublishers.ofString(cuerpo)).build();
        HttpResponse<String> r = enviar(req);
        if (r.statusCode() == 400 || r.statusCode() == 401) {
            throw new ApiException("Usuario o contraseña incorrectos.", r.statusCode());
        }
        verificar(r);
        try {
            JsonNode token = mapper.readTree(r.body()).path("access_token");
            if (token.isMissingNode() || token.asText().isBlank()) {
                throw new ApiException("La respuesta no contiene un token.", r.statusCode());
            }
            jwt = token.asText();
        } catch (IOException e) {
            throw new ApiException("Respuesta de autenticación no válida.", r.statusCode());
        }
    }

    /** Sin despuesDeId: las ultimas N (mas recientes primero). Con despuesDeId: solo las nuevas (ascendente). */
    public List<Notificacion> listar(Long despuesDeId) throws ApiException {
        String q = "?limite=100" + (despuesDeId == null ? "" : "&despuesDeId=" + despuesDeId);
        HttpRequest.Builder b = HttpRequest.newBuilder(URI.create(base + "/api/notificaciones" + q))
                .timeout(Duration.ofSeconds(6)).header("Accept", "application/json").GET();
        if (jwt != null) b.header("Authorization", "Bearer " + jwt);
        HttpResponse<String> r = enviar(b.build());
        verificar(r);
        try {
            return mapper.readValue(r.body(), new TypeReference<List<Notificacion>>() {});
        } catch (IOException e) {
            throw new ApiException("La API devolvió una respuesta que no es JSON válido.", r.statusCode());
        }
    }

    private HttpResponse<String> enviar(HttpRequest req) throws ApiException {
        try {
            return http.send(req, HttpResponse.BodyHandlers.ofString());
        } catch (IOException e) {
            throw new ApiException("No se pudo conectar con el servicio (NGINX/backend no disponible).", 0);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new ApiException("Operación interrumpida.", 0);
        }
    }

    private static void verificar(HttpResponse<String> r) throws ApiException {
        int c = r.statusCode();
        if (c >= 200 && c < 300) return;
        String m = switch (c) {
            case 401 -> "HTTP 401: sesión inválida o vencida. Inicie sesión de nuevo.";
            case 403 -> "HTTP 403: su usuario no tiene permiso para consultar notificaciones.";
            case 502, 503, 504 -> "HTTP " + c + ": servicio de notificaciones no disponible.";
            default -> "HTTP " + c + ": consulta no completada.";
        };
        throw new ApiException(m, c);
    }

    private static String enc(String s) { return URLEncoder.encode(s, StandardCharsets.UTF_8); }
}
