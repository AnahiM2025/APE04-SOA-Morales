"""Endpoints REST de compradores y ventas."""
# Carga tipos y funciones que se utilizarán más abajo.
from typing import Annotated
# Publica endpoints web y valida solicitudes.
from fastapi import APIRouter, Depends, Header, Query, Response
# Importa el componente local correspondiente a esta responsabilidad.
from app.db import SessionLocal
from app.models import Venta, Comprador
from app.schemas import CrearVenta, CrearComprador
from app.security import identidad, vendedor, lector
from app.errors import ApiError
from app.repositories.venta_repository import VentaRepository
from app.services import venta_service as service
# Crea el agrupador de rutas HTTP con prefijo /api.
router = APIRouter(prefix="/api")


# Expone POST /api/compradores; cuando crea devuelve HTTP 201.
@router.post("/compradores", status_code=201)
# Recibe JSON validado y usuario autenticado por Java.
def crear_comprador(d: CrearComprador, u=Depends(identidad)):
    # Comprueba permisos de OPERADOR o ADMIN.
    vendedor(u)
    # Abre una transacción que confirma automáticamente al concluir.
    with SessionLocal.begin() as db:
        # Crea el comprador y guarda el propietario real autenticado.
        c = Comprador(usuario=u["usuario"], **d.model_dump())
        # Registra la entidad y ejecuta el INSERT para obtener el ID.
        db.add(c); db.flush()
        # Envía al cliente el nuevo comprador sin exponer campos internos.
        return {"id": c.id, "documento": c.documento, "nombre": c.nombre, "correo": c.correo}


# Expone POST /api/ventas; requiere JWT y Idempotency-Key.
@router.post("/ventas")
# Acepta el cuerpo validado, la respuesta y la clave idempotente.
def crear(d: CrearVenta, response: Response,
          # Declara cabecera HTTP obligatoria Idempotency-Key.
          idempotency_key: Annotated[str, Header(
              # Limita longitud y caracteres admitidos en la clave.
              min_length=8, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")],
          # Pide a FastAPI validar la identidad antes de entrar al endpoint.
          u=Depends(identidad)):
    # Comprueba permisos de OPERADOR o ADMIN.
    vendedor(u)
    # Delegación: las reglas y comunicación Java viven en el Service.
    resultado, codigo = service.crear(d, idempotency_key, u)
    # Asigna 201, 200 o 202 según el resultado.
    response.status_code = codigo
    # Informa la URL REST donde puede consultarse esta venta.
    response.headers["Location"] = f"/api/ventas/{resultado['id']}"
    # Entrega el JSON generado por el servicio.
    return resultado


# Expone GET /api/ventas/{id} para consultar la operación.
@router.get("/ventas/{id}")
# Obtiene un identificador y usuario autenticado.
def obtener(id: int, u=Depends(identidad)):
    lector(u)
    # Gestiona automáticamente la apertura y cierre del recurso.
    with SessionLocal() as db:
        # Busca la venta mediante clave primaria.
        v = db.get(Venta, id)
        # Comprueba si la venta solicitada no existe.
        if v is None:
            # Responde 404 en vez de un error genérico.
            raise ApiError(404, "VENTA_NO_EXISTE", "Venta inexistente")
        # Devuelve el mismo formato JSON que POST.
        return service.salida(v)


# Expone GET /api/compradores: listado para Windows Forms y la PWA.
@router.get("/compradores")
def listar_compradores(u=Depends(identidad),
                       limite: int = Query(100, ge=1, le=500),
                       desplazamiento: int = Query(0, ge=0)):
    # Permite CONSULTA, OPERADOR y ADMIN.
    lector(u)
    with SessionLocal() as db:
        return [{"id": c.id, "documento": c.documento, "nombre": c.nombre,
                 "correo": c.correo}
                for c in VentaRepository(db).listar_compradores(limite, desplazamiento)]


# Expone GET /api/ventas: listado administrativo y consulta web (React).
@router.get("/ventas")
def listar_ventas(u=Depends(identidad),
                  estado: str | None = Query(
                      None, pattern=r"^(PENDIENTE|EN_REVISION|COMPLETADA|FALLIDA)$"),
                  limite: int = Query(100, ge=1, le=500),
                  desplazamiento: int = Query(0, ge=0)):
    # Permite CONSULTA, OPERADOR y ADMIN; solo lectura.
    lector(u)
    with SessionLocal() as db:
        return [service.salida(v)
                for v in VentaRepository(db).listar_ventas(estado, limite, desplazamiento)]
