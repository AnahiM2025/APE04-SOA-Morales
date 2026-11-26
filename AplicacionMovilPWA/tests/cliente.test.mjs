import test from 'node:test';
import assert from 'node:assert/strict';
import { iniciarSesion, cerrarSesion, haySesion, registrarVenta, listarVehiculos, consultarVenta } from '../public/api.js';

const resp = (codigo, cuerpo) => async () => new Response(cuerpo === undefined ? null : JSON.stringify(cuerpo), { status: codigo });

test('login guarda el JWT solo en memoria y cerrarSesion lo borra', async () => {
  cerrarSesion();
  await iniciarSesion('operador', 'x', resp(200, { access_token: 'jwt1', expires_in: 900 }));
  assert.equal(haySesion(), true);
  cerrarSesion();
  assert.equal(haySesion(), false);
});

test('login con credenciales malas da mensaje claro y no deja sesion', async () => {
  cerrarSesion();
  await assert.rejects(() => iniciarSesion('a', 'b', resp(401, { error: 'x' })), /incorrectos/);
  assert.equal(haySesion(), false);
});

test('registrarVenta envia Idempotency-Key, JWT y numeros', async () => {
  await iniciarSesion('operador', 'x', resp(200, { access_token: 'jwtX' }));
  let visto;
  const f = async (ruta, op) => { visto = { ruta, op }; return new Response(JSON.stringify({ id: 5, estado: 'COMPLETADA' }), { status: 201 }); };
  const r = await registrarVenta('3', '4', 'clave-12345', f);
  assert.equal(r.codigoHttp, 201);
  assert.equal(visto.ruta, '/api/ventas');
  assert.equal(visto.op.headers.get('Idempotency-Key'), 'clave-12345');
  assert.equal(visto.op.headers.get('Authorization'), 'Bearer jwtX');
  assert.deepEqual(JSON.parse(visto.op.body), { vehiculoId: 3, compradorId: 4 });
});

test('errores: 403/409 son definitivos; 503 y red caida son inciertos', async () => {
  await iniciarSesion('operador', 'x', resp(200, { access_token: 'j' }));
  await assert.rejects(() => registrarVenta(1, 1, 'clave-12345', resp(403, {})), (e) => e.codigoHttp === 403 && !e.incierto);
  await assert.rejects(() => registrarVenta(1, 1, 'clave-12345', resp(409, {})), (e) => e.codigoHttp === 409 && !e.incierto);
  await assert.rejects(() => registrarVenta(1, 1, 'clave-12345', resp(503, {})), (e) => e.incierto === true);
  await assert.rejects(() => registrarVenta(1, 1, 'clave-12345', async () => { throw new TypeError('red'); }), (e) => e.incierto === true);
});

test('listados exigen arreglo y consultarVenta valida el ID', async () => {
  await iniciarSesion('operador', 'x', resp(200, { access_token: 'j' }));
  await assert.rejects(() => listarVehiculos(resp(200, { no: 'arreglo' })), /arreglo/);
  await assert.rejects(() => consultarVenta('12abc'), /entero/);
});
