import test from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { crearServidor, rutaPermitida } from '../server.mjs';

const escuchar = (srv) => new Promise((ok) => srv.listen(0, '127.0.0.1', () => ok(srv.address().port)));

async function entorno() {
  const recibidas = [];
  const backend = createServer((req, res) => {
    const partes = []; req.on('data', (c) => partes.push(c));
    req.on('end', () => {
      recibidas.push({ metodo: req.method, url: req.url, h: req.headers, cuerpo: Buffer.concat(partes).toString() });
      res.writeHead(200, { 'Content-Type': 'application/json' }); res.end('{"ok":true}');
    });
  });
  const pb = await escuchar(backend);
  const pwa = crearServidor({ apiBase: `http://127.0.0.1:${pb}`, clientId: 'cli', clientSecret: 'sec-no-visible' });
  const pp = await escuchar(pwa);
  return { recibidas, url: `http://127.0.0.1:${pp}`, cerrar: () => { backend.close(); pwa.close(); } };
}

test('lista cerrada de rutas', () => {
  assert.ok(rutaPermitida('POST', '/oauth/token'));
  assert.ok(rutaPermitida('POST', '/api/ventas'));
  assert.ok(rutaPermitida('GET', '/api/ventas/12'));
  assert.equal(rutaPermitida('POST', '/api/vehiculos'), null);   // la PWA no crea vehiculos
  assert.equal(rutaPermitida('DELETE', '/api/vehiculos'), null);
  assert.equal(rutaPermitida('GET', '/api/ventas/../x'), null);
  assert.equal(rutaPermitida('GET', '/api/ventas'), null);       // el listado general no es de la PWA
});

test('login: el servidor agrega Basic y no reenvia el Authorization del navegador', async () => {
  const e = await entorno();
  const r = await fetch(`${e.url}/oauth/token`, { method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded', Authorization: 'Bearer falso' },
    body: 'grant_type=password&username=operador&password=x' });
  assert.equal(r.status, 200);
  const q = e.recibidas[0];
  assert.equal(q.url, '/oauth/token');
  assert.equal(q.h.authorization, 'Basic ' + Buffer.from('cli:sec-no-visible').toString('base64'));
  assert.match(q.cuerpo, /grant_type=password/);
  e.cerrar();
});

test('venta: reenvia JWT, Idempotency-Key y cuerpo', async () => {
  const e = await entorno();
  const r = await fetch(`${e.url}/api/ventas`, { method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: 'Bearer abc', 'Idempotency-Key': 'clave-1234' },
    body: JSON.stringify({ vehiculoId: 1, compradorId: 2 }) });
  assert.equal(r.status, 200);
  const q = e.recibidas[0];
  assert.equal(q.metodo, 'POST');
  assert.equal(q.h.authorization, 'Bearer abc');
  assert.equal(q.h['idempotency-key'], 'clave-1234');
  assert.deepEqual(JSON.parse(q.cuerpo), { vehiculoId: 1, compradorId: 2 });
  e.cerrar();
});

test('rutas no permitidas devuelven 404 y no llegan al backend', async () => {
  const e = await entorno();
  for (const [m, ruta] of [['POST', '/api/vehiculos'], ['DELETE', '/api/vehiculos'], ['GET', '/api/otro'], ['GET', '/api/ventas']]) {
    const r = await fetch(`${e.url}${ruta}`, { method: m });
    assert.equal(r.status, 404, `${m} ${ruta}`);
  }
  assert.equal(e.recibidas.length, 0);
  e.cerrar();
});

test('consulta de ventas y listados llegan por GET con query', async () => {
  const e = await entorno();
  await fetch(`${e.url}/api/vehiculos?marca=Kia`, { headers: { Authorization: 'Bearer t' } });
  await fetch(`${e.url}/api/ventas/7`, { headers: { Authorization: 'Bearer t' } });
  assert.equal(e.recibidas[0].url, '/api/vehiculos?marca=Kia');
  assert.equal(e.recibidas[1].url, '/api/ventas/7');
  e.cerrar();
});

test('backend caido: 502 JSON; sin client-secret el login falla con 500', async () => {
  const pwa = crearServidor({ apiBase: 'http://127.0.0.1:1', clientId: 'a', clientSecret: 'b' });
  const p = await escuchar(pwa);
  const r = await fetch(`http://127.0.0.1:${p}/api/vehiculos`, { headers: { Authorization: 'Bearer t' } });
  assert.equal(r.status, 502);
  pwa.close();
  const sin = crearServidor({ apiBase: 'http://127.0.0.1:1', clientId: '', clientSecret: '' });
  const p2 = await escuchar(sin);
  const l = await fetch(`http://127.0.0.1:${p2}/oauth/token`, { method: 'POST', body: 'x=1' });
  assert.equal(l.status, 500);
  sin.close();
});

test('los archivos publicos no contienen secretos ni usan almacenamiento del navegador', async () => {
  for (const f of ['public/main.js', 'public/api.js', 'public/index.html']) {
    const t = await readFile(new URL(`../${f}`, import.meta.url), 'utf8');
    assert.doesNotMatch(t, /client[_-]?secret|localStorage|sessionStorage/i, f);
  }
});
