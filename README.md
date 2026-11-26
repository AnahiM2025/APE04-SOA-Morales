# APE 04 · Arquitectura multicanal de vehículos, compradores, ventas y notificaciones

```
Windows Forms (admin) ─┐
PWA móvil (ventas) ────┤                     ┌─► Java vehículos A :8080 ┐
React (consulta) ──────┼─► NGINX :8090 ──────┤                          ├─► MySQL venta_vehiculos
JavaFX (avisos) ───────┘                     └─► Java vehículos B :8082 ┘
                                 ├─► FastAPI ventas :8002 ─► MySQL ventas_compradores
                                 │        └─(evento VENTA_REALIZADA)─► RabbitMQ :5672 (cola durable notificaciones.ventas)
                                 └─► Notificaciones :8081 ◄─(consume)───┘      └─► MySQL notificaciones_vehiculos
```
Solo la **PWA** registra ventas; Windows Forms crea/lista; React solo consulta; JavaFX muestra notificaciones por sondeo (4 s).

| Componente | Carpeta | Puerto |
|---|---|---|
| NGINX | `infra/nginx` | 8090 |
| API Java vehículos A / B | `java_venta-vehiculos-api_security` | 8080 / 8082 |
| API Python ventas | `python_ventas-api` | 8002 |
| Notificaciones | `java_notificaciones-service` | 8081 |
| RabbitMQ (AMQP / panel) | `infra/rabbitmq` | 5672 / 15672 |
| MySQL | XAMPP | 3306 |
| PWA / React | `AplicacionMovilPWA` / `AplicacionWebREACT/react-fetch-vehiculos` | 5174 / 5173 |
| Windows Forms / JavaFX | `AplicacionEscritorioWINDOWS_FORMS` / `AplicacionEscritorioJAVA_FX` | — |

## Requisitos
JDK 17+, Maven, .NET SDK 8, Python 3.11+, Node.js 20+, MySQL/XAMPP, NGINX, Docker (para RabbitMQ) o RabbitMQ instalado.

## Configuración (sin secretos en el repositorio)
```powershell
Copy-Item scripts\env.ps1.example scripts\env.ps1     # completar valores reales (archivo excluido de Git)
. .\scripts\env.ps1                                    # cargar variables en CADA terminal que arranque un servicio
```
Python usa además `python_ventas-api\.env` (copiar de `.env.example`: `DB_NAME=ventas_compradores`, `JAVA_URL=http://127.0.0.1:8090`, `VENTAS_SERVICE_KEY`, `RABBITMQ_URL`).

## Orden de arranque
1. **MySQL** (XAMPP) y esquemas: `mysql -u root < scripts\sql\00_esquemas.sql`
2. **RabbitMQ**: `cd infra\rabbitmq; Copy-Item .env.example .env` (completar) `; docker compose --env-file .env up -d` → panel http://127.0.0.1:15672
3. **Java vehículos A** (crea tablas y usuarios): `cd java_venta-vehiculos-api_security; mvn spring-boot:run`
4. **Java vehículos B**: otra terminal, `. .\scripts\env.ps1; $env:SERVER_PORT="8082"; $env:SPRING_PROFILES_ACTIVE=""; mvn spring-boot:run`
5. **Notificaciones**: `cd java_notificaciones-service; mvn spring-boot:run`
6. **FastAPI**: `cd python_ventas-api; python -m venv .venv; .\.venv\Scripts\pip install -r requirements.txt; .\.venv\Scripts\alembic upgrade head; .\.venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8002` y, en otra terminal, el reintento de eventos: `.\.venv\Scripts\python -m app.worker`
7. **NGINX**: `nginx -p <ruta>\infra\nginx -c nginx.conf -t` y luego `nginx -p <ruta>\infra\nginx -c nginx.conf`
8. **Clientes**: Windows Forms (`dotnet run --project AplicacionEscritorioWINDOWS_FORMS\ConsultaVehiculosWinForms`), PWA (`$env:PORT="5174"; npm start`), React (`npm install; npm run dev`), JavaFX (`mvn clean javafx:run`). Cada README indica sus variables (`APP_CLIENT_ID`, `APP_CLIENT_SECRET`, `API_BASE_URL`).

## Pruebas reproducibles
```powershell
python scripts\pruebas.py integracion      # P01–P13, P15–P18, P22 con resultados reales en evidencias\
python scripts\pruebas.py balanceo 100     # P23: conteo real por instancia (cabecera X-Upstream de NGINX)
python scripts\pruebas.py monitor 120      # P24–P26: estados con timestamps y alertas (detenga B durante la prueba)
python scripts\pruebas.py cola             # P19/P20: Ready y Consumers de la cola (antes/después de detener el consumidor)
python scripts\pruebas.py secretos .       # P28: ningún valor real de sus variables aparece en el código
cd python_ventas-api; .\.venv\Scripts\python -m pytest -q   # pruebas unitarias de FastAPI
cd AplicacionMovilPWA; npm test                              # pruebas de la PWA (12)
```
Pruebas manuales con captura: P02–P06 (Windows Forms), P09 (PWA), P14–P16 (React), P19–P21 y P27 (RabbitMQ, JavaFX), P24–P25 (detener y reiniciar Java B).

## Decisiones técnicas
- Evento por RabbitMQ con `eventoId` determinista (uuid5 de la operación): el reintento reenvía el mismo id y el consumidor deduplica (entrega *al menos una vez*).
- Si RabbitMQ cae, la venta queda `COMPLETADA` con `notificacion=PENDIENTE`; `app.worker` reintenta (patrón outbox simplificado).
- Compradores y ventas son datos compartidos entre roles autorizados; la escritura exige OPERADOR/ADMIN y la lectura también CONSULTA.
- FastAPI valida el JWT preguntando a `/api/identidad` de Java (vía NGINX); no duplica la clave de firma.
- Los GET de notificaciones usan el mismo mecanismo; el POST interno usa `X-Notification-Key`.
