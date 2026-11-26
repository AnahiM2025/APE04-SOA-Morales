# API de Ventas y Compradores — Python FastAPI

**Autor:** Javier Vargas

## 1. Software necesario

- Windows 10 u 11 y Visual Studio Code.
- Python 3.13 con `pip` y `venv`.
- MySQL o XAMPP con la base `venta_vehiculos` disponible.
- API Java de vehículos (instancias 8080/8082) detrás de NGINX en `http://127.0.0.1:8090`.
- RabbitMQ en `127.0.0.1:5672` (ver `infra/rabbitmq/docker-compose.yml`).

## 2. Preparar el proyecto

1. Se descarga o clona `soa-ventas-python` y se abre la carpeta que contiene `requirements.txt` y `alembic.ini`.
2. Se abre PowerShell y se crea el entorno virtual:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

3. Se copia y configura el archivo local de variables:

```powershell
Copy-Item .env.example .env
notepad .env
```

4. En `.env` se ajustan los datos de MySQL, `JAVA_URL` (NGINX, puerto 8090), `VENTAS_SERVICE_KEY` (igual a `app.security.ventas-key` de Java) y `RABBITMQ_URL`/`RABBITMQ_QUEUE`. Nunca se sube el `.env` real a Git.
5. Con MySQL en funcionamiento, se aplican las migraciones incluidas:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```

## 3. Comprobar el código

```powershell
.\.venv\Scripts\python.exe -m compileall app alembic
```

## 4. Ejecutar la API

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8002 --reload
```

Se comprueba `http://127.0.0.1:8002/health` y se revisan los endpoints en `http://127.0.0.1:8002/docs`.

## 5. Ejecutar el proceso de recuperación (cuando corresponda)

En otra terminal, desde la misma carpeta:

```powershell
.\.venv\Scripts\python.exe -m app.worker
```

Se detienen los procesos con `Ctrl + C`. El archivo `.env` no se publica en Git.

## 6. Endpoints

| Método y ruta | Roles | Descripción |
|---|---|---|
| `POST /api/compradores` | OPERADOR, ADMIN | Registra comprador (201). |
| `GET /api/compradores` | CONSULTA, OPERADOR, ADMIN | Lista compradores (`limite`, `desplazamiento`). |
| `POST /api/ventas` | OPERADOR, ADMIN | Registra venta; exige `Idempotency-Key`. 201 nueva, 200 repetida, 202 pendiente. |
| `GET /api/ventas` | CONSULTA, OPERADOR, ADMIN | Lista ventas, más recientes primero (`estado`, `limite`, `desplazamiento`). |
| `GET /api/ventas/{id}` | CONSULTA, OPERADOR, ADMIN | Consulta una venta. |

## 7. Evento de venta (RabbitMQ)

Tras confirmar una venta (`COMPLETADA`) se publica en la cola durable `notificaciones.ventas` un mensaje persistente:

```json
{"eventoId":"<uuid5 de la operación>","tipo":"VENTA_REALIZADA","ventaId":12,"vehiculoId":3,"fechaHora":"2026-11-22T15:04:05Z"}
```

- No lleva JWT ni datos personales. Una venta rechazada o pendiente no publica nada.
- `eventoId` es estable: un reintento reenvía el mismo identificador y el consumidor puede descartar duplicados.
- Si RabbitMQ está caído, la venta queda `COMPLETADA` con `notificacion=PENDIENTE` y `python -m app.worker` reintenta hasta que el broker confirme (entrega al menos una vez).

## 8. Pruebas

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

Las pruebas usan SQLite y un RabbitMQ/Java simulados: **no reemplazan** la prueba real contra MySQL, Java y RabbitMQ.
