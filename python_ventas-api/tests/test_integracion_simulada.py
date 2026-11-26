"""Pruebas con SQLite temporal y servicios HTTP simulados; NO reemplazan a Java/MySQL reales."""
import importlib
import os
import sys
from pathlib import Path

import pytest
import httpx
from fastapi.testclient import TestClient
from sqlalchemy import create_engine as sqlalchemy_create_engine
from sqlalchemy.pool import StaticPool


@pytest.fixture
def sistema(monkeypatch):
    # Arranca con una base SQLite aislada y conexión compartida en memoria.
    engine = sqlalchemy_create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    # La app sigue generando la URL de MySQL, pero para la prueba utiliza SQLite.
    import sqlalchemy
    monkeypatch.setattr(sqlalchemy, 'create_engine', lambda *args, **kwargs: engine)
    for k,v in {'DB_USER':'pruebas','DB_HOST':'127.0.0.1','DB_NAME':'venta_vehiculos',
                'JAVA_URL':'http://127.0.0.1:8080', 'VENTAS_SERVICE_KEY':'clave_prueba_java_con_32_caracteres_1234',
                'RABBITMQ_URL':'amqp://usuario:clave@127.0.0.1:5672/%2F'}.items():
        monkeypatch.setenv(k,v)
    # Fuerza a cargar los módulos para usar el motor temporal de pruebas.
    for name in list(sys.modules):
        if name == 'app' or name.startswith('app.'):
            del sys.modules[name]
    from app.db import Base
    from app import models
    Base.metadata.create_all(engine)
    from app.main import app
    import app.services.venta_service as svc
    import app.security as sec
    import app.clients.vehiculos_client as veh
    # Servidor Java simulado con las mismas rutas y estados de reserva del contrato real.
    estado={'reservas':{},'vehiculos':{1:'DISPONIBLE',2:'DISPONIBLE'},'avisos':[], 'notificaciones_activas':True}
    def identidad(url, **kw):
        assert url.endswith('/api/identidad')
        auth = kw.get('headers',{}).get('Authorization','')
        if auth=='Bearer valido':return httpx.Response(200,json={'usuario':'operador','roles':['ROLE_OPERADOR']})
        if auth=='Bearer consulta':return httpx.Response(200,json={'usuario':'lector','roles':['ROLE_CONSULTA']})
        return httpx.Response(401,json={'error':'token inválido'})
    def java(method,url,**kw):
        assert kw['headers']['X-Service-Key']=='clave_prueba_java_con_32_caracteres_1234'
        route=url.split(':8080')[-1]
        if method=='GET' and route=='/api/reservas':
            op=kw['params']['operacionId'];r=estado['reservas'].get(op)
            return httpx.Response(200,json=r) if r else httpx.Response(404,json={'error':'no existe'})
        if method=='POST' and route.startswith('/api/vehiculos/'):
            vehiculo=int(route.split('/')[3]);op=kw['json']['operacionId']
            if vehiculo not in estado['vehiculos']:return httpx.Response(404,json={'error':'inexistente'})
            if estado['vehiculos'][vehiculo]!='DISPONIBLE':return httpx.Response(409,json={'error':'vendido'})
            estado['vehiculos'][vehiculo]='RESERVADO'
            r={'id':op,'operacionId':op,'vehiculoId':vehiculo,'precio':'18000.00','moneda':'USD','estado':'RESERVADA'}
            estado['reservas'][op]=r
            return httpx.Response(200,json=r)
        if method=='PUT' and route.endswith('/confirmacion'):
            reserva=route.split('/')[3];r=estado['reservas'][reserva]
            r['estado']='CONFIRMADA';estado['vehiculos'][r['vehiculoId']]='VENDIDO'
            return httpx.Response(200,json=r)
        raise AssertionError(f'Ruta inesperada: {method} {route}')
    import app.messaging.publisher as pub
    def publicar(evento):
        # Simula RabbitMQ: acepta el evento o falla como un broker apagado.
        if not estado['notificaciones_activas']:raise pub.PublicacionError('RabbitMQ apagado')
        estado['avisos'].append(evento)
    monkeypatch.setattr(httpx,'get',identidad)
    monkeypatch.setattr(httpx,'request',java)
    monkeypatch.setattr(svc,'publicar_evento_venta',publicar)
    return TestClient(app),estado


def test_venta_con_jwt_e_idempotencia(sistema):
    client,estado=sistema
    assert client.get('/health').json()=={'status':'UP'}
    auth={'Authorization':'Bearer valido'}
    comprador=client.post('/api/compradores',json={'documento':'1801111111','nombre':'Ana','correo':'ana@ejemplo.com'},headers=auth)
    assert comprador.status_code==201, comprador.text
    cid=comprador.json()['id']
    headers={**auth,'Idempotency-Key':'laboratorio0001'}
    payload={'vehiculoId':1,'compradorId':cid}
    creado=client.post('/api/ventas',json=payload,headers=headers)
    assert creado.status_code==201, creado.text
    assert creado.json()['estado']=='COMPLETADA'
    assert creado.json()['notificacion']=='ENVIADA'
    assert estado['vehiculos'][1]=='VENDIDO'
    assert len(estado['avisos'])==1
    aviso=estado['avisos'][0]
    assert set(aviso)=={'eventoId','tipo','ventaId','vehiculoId','fechaHora'}  # sin JWT ni datos personales
    assert aviso['tipo']=='VENTA_REALIZADA' and aviso['vehiculoId']==1
    assert aviso['ventaId']==creado.json()['id']
    mismo=client.post('/api/ventas',json=payload,headers=headers)
    assert mismo.status_code==200 and mismo.json()['id']==creado.json()['id']
    assert len(estado['avisos'])==1
    incorrecto=client.post('/api/ventas',json={'vehiculoId':2,'compradorId':cid},headers=headers)
    assert incorrecto.status_code==409
    no_disponible=client.post('/api/ventas',json=payload,headers={**auth,'Idempotency-Key':'laboratorio0002'})
    assert no_disponible.status_code==409


def test_seguridad_validaciones_y_reenvio(sistema):
    client,estado=sistema
    data={'documento':'1805555555','nombre':'Ana','correo':'ana@ejemplo.com'}
    assert client.post('/api/compradores',json=data).status_code==401
    assert client.post('/api/compradores',json=data,headers={'Authorization':'Bearer consulta'}).status_code==403
    auth={'Authorization':'Bearer valido'}
    assert client.post('/api/compradores',json={'nombre':'Ana'},headers=auth).status_code==422
    cid=client.post('/api/compradores',json=data,headers=auth).json()['id']
    estado['notificaciones_activas']=False
    venta=client.post('/api/ventas',json={'vehiculoId':2,'compradorId':cid},headers={**auth,'Idempotency-Key':'laboratorio0003'})
    assert venta.status_code==201
    assert venta.json()['notificacion']=='PENDIENTE'
    estado['notificaciones_activas']=True
    from app.worker import ciclo
    ciclo()
    compr=client.get(f"/api/ventas/{venta.json()['id']}",headers=auth)
    assert compr.json()['notificacion']=='ENVIADA'
    assert len(estado['avisos'])==1
    assert estado['avisos'][0]['ventaId']==venta.json()['id']
    ciclo()  # un segundo barrido no vuelve a publicar un evento ya enviado
    assert len(estado['avisos'])==1


def _comprador_y_venta(client, clave='laboratorio0100', vehiculo=1):
    auth={'Authorization':'Bearer valido'}
    cid=client.post('/api/compradores',json={'documento':'1809999999','nombre':'Luis','correo':'luis@ejemplo.com'},headers=auth).json()['id']
    venta=client.post('/api/ventas',json={'vehiculoId':vehiculo,'compradorId':cid},headers={**auth,'Idempotency-Key':clave})
    return cid, venta


def test_listados_y_roles_de_solo_lectura(sistema):
    client,estado=sistema
    consulta={'Authorization':'Bearer consulta'}
    cid,venta=_comprador_y_venta(client)
    assert venta.status_code==201
    # Sin token: 401 en los dos listados.
    assert client.get('/api/compradores').status_code==401
    assert client.get('/api/ventas').status_code==401
    # CONSULTA puede leer lo creado por otro usuario (datos compartidos entre clientes).
    compradores=client.get('/api/compradores',headers=consulta)
    assert compradores.status_code==200
    assert [c['id'] for c in compradores.json()]==[cid]
    assert set(compradores.json()[0])=={'id','documento','nombre','correo'}
    ventas=client.get('/api/ventas',headers=consulta)
    assert ventas.status_code==200 and ventas.json()[0]['id']==venta.json()['id']
    assert client.get(f"/api/ventas/{venta.json()['id']}",headers=consulta).status_code==200
    assert len(client.get('/api/ventas?estado=COMPLETADA',headers=consulta).json())==1
    assert client.get('/api/ventas?estado=FALLIDA',headers=consulta).json()==[]
    assert client.get('/api/ventas?estado=INVENTADO',headers=consulta).status_code==422
    # Pero CONSULTA no puede escribir: ni comprador ni venta (HTTP 403).
    datos={'documento':'1800000001','nombre':'Eva','correo':'eva@ejemplo.com'}
    assert client.post('/api/compradores',json=datos,headers=consulta).status_code==403
    denegada=client.post('/api/ventas',json={'vehiculoId':2,'compradorId':cid},headers={**consulta,'Idempotency-Key':'laboratorio0101'})
    assert denegada.status_code==403
    assert estado['vehiculos'][2]=='DISPONIBLE' and len(estado['avisos'])==1


def test_venta_rechazada_no_publica_evento(sistema):
    client,estado=sistema
    cid,venta=_comprador_y_venta(client, clave='laboratorio0200', vehiculo=99)  # vehículo inexistente
    assert venta.status_code==404
    assert estado['avisos']==[]
    ventas=client.get('/api/ventas?estado=FALLIDA',headers={'Authorization':'Bearer consulta'}).json()
    assert len(ventas)==1 and ventas[0]['estado']=='FALLIDA'


def test_publicador_usa_cola_durable_y_mensaje_persistente(sistema, monkeypatch):
    import json
    import pika
    import app.messaging.publisher as pub
    capturado={}
    class Canal:
        def __init__(self): self.llamadas=[]
        def queue_declare(self, **kw): self.llamadas.append(('queue_declare',kw))
        def confirm_delivery(self): self.llamadas.append(('confirm_delivery',{}))
        def basic_publish(self, **kw): self.llamadas.append(('basic_publish',kw))
    class Conexion:
        def __init__(self, parametros): self.canal=Canal(); self.cerrada=False; capturado['c']=self
        def channel(self): return self.canal
        def close(self): self.cerrada=True
    monkeypatch.setattr(pika,'BlockingConnection',Conexion)
    evento={'eventoId':'e1','tipo':'VENTA_REALIZADA','ventaId':7,'vehiculoId':3,'fechaHora':'2026-11-22T10:00:00Z'}
    pub.publicar_evento_venta(evento)
    c=capturado['c']; nombres=[n for n,_ in c.canal.llamadas]
    assert nombres==['queue_declare','confirm_delivery','basic_publish'] and c.cerrada
    declarada=c.canal.llamadas[0][1]; publicada=c.canal.llamadas[2][1]
    assert declarada['durable'] is True and declarada['queue']=='notificaciones.ventas'
    assert publicada['routing_key']=='notificaciones.ventas'
    assert publicada['properties'].delivery_mode==2
    assert json.loads(publicada['body'])==evento


def test_publicador_traduce_fallos_de_rabbitmq(sistema, monkeypatch):
    import pika
    import app.messaging.publisher as pub
    def caido(parametros): raise pika.exceptions.AMQPConnectionError('sin broker')
    monkeypatch.setattr(pika,'BlockingConnection',caido)
    with pytest.raises(pub.PublicacionError):
        pub.publicar_evento_venta({'eventoId':'e2'})
