package ec.edu.uta.notificaciones.security;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.time.Duration;
import java.util.Set;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;
import org.springframework.web.filter.OncePerRequestFilter;

/**
 * Protege los GET de /api/notificaciones: reenvia el JWT a /api/identidad de la API Java
 * (la que lo firma y lo valida) y exige un rol de lectura. No se inventa ni se desactiva
 * ninguna validacion: 401 sin/invalido/vencido, 403 rol insuficiente, 503 si Java no responde.
 */
@Component
public class IdentidadFilter extends OncePerRequestFilter {
    private static final Set<String> ROLES = Set.of("ROLE_CONSULTA", "ROLE_OPERADOR", "ROLE_ADMIN");
    private final RestClient client;
    private final ObjectMapper mapper;

    public IdentidadFilter(@Value("${app.identidad-url}") String url, ObjectMapper mapper) {
        var f = new SimpleClientHttpRequestFactory();
        f.setConnectTimeout(Duration.ofSeconds(2));
        f.setReadTimeout(Duration.ofSeconds(4));
        this.client = RestClient.builder().baseUrl(url).requestFactory(f).build();
        this.mapper = mapper;
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest req) {
        return !"GET".equals(req.getMethod()) || !req.getRequestURI().startsWith("/api/notificaciones");
    }

    @Override
    protected void doFilterInternal(HttpServletRequest req, HttpServletResponse res, FilterChain chain)
            throws IOException, ServletException {
        String auth = req.getHeader("Authorization");
        if (auth == null || !auth.startsWith("Bearer ")) {
            rechazar(res, 401, "No autenticado");
            return;
        }
        try {
            String cuerpo = client.get().uri("/api/identidad").header("Authorization", auth)
                    .retrieve().body(String.class);
            JsonNode roles = mapper.readTree(cuerpo).path("roles");
            boolean permitido = false;
            for (JsonNode r : roles) {
                if (ROLES.contains(r.asText())) permitido = true;
            }
            if (!permitido) {
                rechazar(res, 403, "Sin permiso");
                return;
            }
        } catch (HttpClientErrorException e) {
            rechazar(res, e.getStatusCode().value() == 403 ? 403 : 401, "Token no autorizado");
            return;
        } catch (RestClientException | IOException e) {
            rechazar(res, 503, "No se pudo validar la identidad");
            return;
        }
        chain.doFilter(req, res);
    }

    private void rechazar(HttpServletResponse res, int status, String titulo) throws IOException {
        res.setStatus(status);
        res.setContentType("application/problem+json");
        res.getWriter().write("{\"title\":\"" + titulo + "\",\"status\":" + status + "}");
    }
}
