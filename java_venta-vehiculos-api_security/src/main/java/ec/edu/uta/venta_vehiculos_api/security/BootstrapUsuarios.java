package ec.edu.uta.venta_vehiculos_api.security;

import ec.edu.uta.venta_vehiculos_api.model.UsuarioApi;
import ec.edu.uta.venta_vehiculos_api.repository.UsuarioApiRepository;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.context.annotation.Profile;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;

/**
 * Crea los usuarios de laboratorio SOLO con el perfil "local" (SPRING_PROFILES_ACTIVE=local).
 * Formato de app.bootstrap.users:  usuario:ROL,usuario:ROL   (ROL = ADMIN | OPERADOR | CONSULTA).
 * La clave sale de APP_BOOTSTRAP_PASSWORD; nunca se guarda en el repositorio.
 */
@Component
@Profile("local")
public class BootstrapUsuarios implements ApplicationRunner {
    private final UsuarioApiRepository repo;
    private final PasswordEncoder encoder;
    private final String usuarios;
    private final String clave;

    public BootstrapUsuarios(UsuarioApiRepository repo, PasswordEncoder encoder,
                             @Value("${app.bootstrap.users}") String usuarios,
                             @Value("${app.bootstrap.password}") String clave) {
        this.repo = repo;
        this.encoder = encoder;
        this.usuarios = usuarios;
        this.clave = clave;
    }

    @Override
    public void run(ApplicationArguments args) {
        if (clave == null || clave.length() < 8) {
            throw new IllegalStateException("Defina APP_BOOTSTRAP_PASSWORD (minimo 8 caracteres)");
        }
        for (String par : usuarios.split(",")) {
            String[] p = par.trim().split(":");
            if (p.length != 2 || repo.findByUsername(p[0]).isPresent()) continue;
            UsuarioApi u = new UsuarioApi();
            u.setUsername(p[0]);
            u.setRol(p[1]);
            u.setPassword(encoder.encode(clave));
            repo.save(u);
            System.out.println("Usuario de laboratorio creado: " + p[0] + " (" + p[1] + ")");
        }
    }
}
