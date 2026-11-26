/**
 * Servidor local de la PWA (sin dependencias externas).
 * - Sirve los archivos estaticos de /public.
 * - Reenvia a NGINX (puerto 8090) SOLO una lista cerrada de rutas.
 * - Para el login agrega el Basic client-id:client-secret desde variables de entorno:
 *   el secreto vive aqui, en el servidor, y nunca llega al navegador.
 * Misma-origen: el navegador solo habla con este servidor (sin CORS).
 */
import { createServer } from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import { resolve, extname, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(fileURLToPath(new URL('.', import.meta.url)));
const TIPOS = {
  '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8', '.png': 'image/png',
  '.webmanifest': 'application/manifest+json; charset=utf-8',
  '.json': 'application/json; charset=utf-8', '.svg': 'image/svg+xml',
};
const MAX_CUERPO = 8 * 1024;

/** Lista cerrada de operaciones que la PWA puede reenviar. */
export function rutaPermitida(metodo, ruta) {
  if (metodo === 'POST' && ruta === '/oauth/token') return { login: true, cuerpo: true };
  if (metodo === 'GET' && (ruta === '/api/vehiculos' || ruta === '/api/compradores')) return {};
  if (metodo === 'POST' && ruta === '/api/ventas') return { cuerpo: true };
  if (metodo === 'GET' && /^\/api\/ventas\/\d{1,12}$/.test(ruta)) return {};
  return null;
}

function leerCuerpo(peticion) {
  return new Promise((ok, fallo) => {
    const partes = []; let total = 0;
    peticion.on('data', (c) => {
      total += c.length;
      if (total > MAX_CUERPO) { fallo(new Error('Cuerpo demasiado grande')); peticion.destroy(); return; }
      partes.push(c);
    });
    peticion.on('end', () => ok(Buffer.concat(partes)));
    peticion.on('error', fallo);
  });
}

function json(respuesta, codigo, objeto) {
  respuesta.writeHead(codigo, { 'Content-Type': 'application/json; charset=utf-8' });
  respuesta.end(JSON.stringify(objeto));
}

export function crearServidor({
  directorio = resolve(ROOT, 'public'),
  apiBase = process.env.API_BASE_URL || 'http://127.0.0.1:8090',
  clientId = process.env.APP_CLIENT_ID,
  clientSecret = process.env.APP_CLIENT_SECRET,
} = {}) {
  const carpeta = resolve(directorio);
  const base = apiBase.replace(/\/$/, '');

  return createServer(async (peticion, respuesta) => {
    const url = new URL(peticion.url || '/', 'http://localhost');
    respuesta.setHeader('X-Content-Type-Options', 'nosniff');
    respuesta.setHeader('Referrer-Policy', 'no-referrer');
    respuesta.setHeader('Cache-Control', 'no-store');

    if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/oauth/')) {
      const regla = rutaPermitida(peticion.method, url.pathname);
      if (!regla) { json(respuesta, 404, { error: 'Endpoint no disponible' }); return; }

      const encabezados = { Accept: 'application/json' };
      let cuerpo;
      if (regla.cuerpo) {
        try { cuerpo = await leerCuerpo(peticion); }
        catch { json(respuesta, 413, { error: 'Cuerpo demasiado grande' }); return; }
        if (peticion.headers['content-type']) encabezados['Content-Type'] = peticion.headers['content-type'];
      }
      if (regla.login) {
        if (!clientId || !clientSecret) {
          json(respuesta, 500, { error: 'Servidor de la PWA sin APP_CLIENT_ID/APP_CLIENT_SECRET' });
          return;
        }
        encabezados.Authorization = 'Basic ' + Buffer.from(`${clientId}:${clientSecret}`).toString('base64');
      } else if (peticion.headers.authorization) {
        encabezados.Authorization = peticion.headers.authorization;
      }
      if (peticion.headers['idempotency-key']) encabezados['Idempotency-Key'] = peticion.headers['idempotency-key'];

      const abortador = new AbortController();
      const temporizador = setTimeout(() => abortador.abort(), 15000);
      try {
        const remoto = await fetch(`${base}${url.pathname}${url.search}`, {
          method: peticion.method, headers: encabezados, body: cuerpo,
          signal: abortador.signal, cache: 'no-store',
        });
        respuesta.writeHead(remoto.status, {
          'Content-Type': remoto.headers.get('content-type') || 'application/json; charset=utf-8',
          'Cache-Control': 'no-store', Vary: 'Authorization',
        });
        respuesta.end(Buffer.from(await remoto.arrayBuffer()));
      } catch (error) {
        const agotado = error.name === 'AbortError';
        json(respuesta, agotado ? 504 : 502, { error: agotado ? 'Tiempo de espera agotado' : 'Backend no disponible' });
      } finally {
        clearTimeout(temporizador);
      }
      return;
    }

    if (peticion.method !== 'GET' && peticion.method !== 'HEAD') { respuesta.writeHead(405); respuesta.end(); return; }
    let ruta;
    try { ruta = decodeURIComponent(url.pathname); }
    catch { respuesta.writeHead(400); respuesta.end(); return; }
    const archivo = resolve(carpeta, '.' + (ruta === '/' ? '/index.html' : ruta));
    if (!(archivo === carpeta || archivo.startsWith(carpeta + sep))) { respuesta.writeHead(403); respuesta.end(); return; }
    try {
      const detalle = await stat(archivo);
      if (!detalle.isFile()) throw new Error('no es archivo');
      respuesta.setHeader('Content-Type', TIPOS[extname(archivo)] || 'application/octet-stream');
      if (peticion.method === 'HEAD') { respuesta.writeHead(200); respuesta.end(); return; }
      respuesta.writeHead(200);
      respuesta.end(await readFile(archivo));
    } catch {
      respuesta.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
      respuesta.end('Recurso no encontrado');
    }
  });
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const argPuerto = process.argv.find((a) => a.startsWith('--port='));
  const argCarpeta = process.argv.find((a) => a.startsWith('--dir='));
  const puerto = Number(argPuerto?.split('=')[1] || process.env.PORT || 5173);
  const host = process.env.HOST || '127.0.0.1';
  const carpeta = resolve(ROOT, argCarpeta?.split('=')[1] || 'public');
  if (!process.env.APP_CLIENT_ID || !process.env.APP_CLIENT_SECRET) {
    console.warn('AVISO: defina APP_CLIENT_ID y APP_CLIENT_SECRET para poder iniciar sesion.');
  }
  crearServidor({ directorio: carpeta }).listen(puerto, host, () => {
    console.log(`PWA disponible: http://localhost:${puerto}`);
    console.log(`Backend (NGINX): ${process.env.API_BASE_URL || 'http://127.0.0.1:8090'}`);
    console.log('Para cerrar: Ctrl + C');
  });
}
