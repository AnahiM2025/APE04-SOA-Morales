/**
 * Cliente HTTP de la PWA. No conoce la interfaz ni MySQL.
 * Todas las rutas son relativas: server.mjs las reenvia a NGINX.
 * El JWT vive solo en esta variable (memoria): no se guarda en el almacenamiento del navegador ni en cookies.
 */
let jwt = '';

export const haySesion = () => Boolean(jwt);
export const cerrarSesion = () => { jwt = ''; };

export function nuevaClave() {
  // Idempotency-Key: 8-100 caracteres [A-Za-z0-9_-]; un UUID cumple.
  return globalThis.crypto?.randomUUID?.() ?? `k${Date.now()}${Math.random().toString(36).slice(2, 12)}`;
}

const MENSAJES = {
  400: 'HTTP 400: solicitud incorrecta.',
  401: 'HTTP 401: sesión ausente, inválida o vencida. Inicie sesión de nuevo.',
  403: 'HTTP 403: su usuario no tiene permiso para esta operación.',
  404: 'HTTP 404: recurso no encontrado.',
  409: 'HTTP 409: conflicto (el vehículo ya no está disponible o la clave se reutilizó con otros datos).',
  422: 'HTTP 422: datos inválidos.',
  502: 'HTTP 502: el backend no está disponible.',
  503: 'HTTP 503: servicio no disponible.',
  504: 'HTTP 504: el backend no respondió a tiempo.',
};

async function pedir(metodo, ruta, { cuerpo, cabeceras = {}, autenticado = true } = {}, f = fetch) {
  const h = new Headers({ Accept: 'application/json', ...cabeceras });
  if (autenticado && jwt) h.set('Authorization', `Bearer ${jwt}`);
  let r;
  try {
    r = await f(ruta, { method: metodo, headers: h, body: cuerpo, cache: 'no-store' });
  } catch {
    const e = new Error('No se pudo conectar con el servicio. Compruebe la red y el backend.');
    e.incierto = true; // la peticion pudo o no llegar: el resultado se desconoce
    throw e;
  }
  let datos = null;
  try { datos = await r.json(); } catch { /* cuerpo vacio o no JSON */ }
  if (!r.ok) {
    const detalle = datos && (datos.mensaje || datos.message || datos.error_description || datos.error);
    const e = new Error(`${MENSAJES[r.status] || `HTTP ${r.status}: operación no completada.`}${detalle ? ` (${detalle})` : ''}`);
    e.codigoHttp = r.status;
    e.incierto = r.status >= 500; // un 5xx no garantiza que la venta no se haya registrado
    throw e;
  }
  return { codigoHttp: r.status, datos };
}

export async function iniciarSesion(usuario, clave, f = fetch) {
  if (!usuario || !clave) throw new Error('Ingrese usuario y contraseña.');
  const cuerpo = new URLSearchParams({ grant_type: 'password', username: usuario.trim(), password: clave });
  try {
    const { datos } = await pedir('POST', '/oauth/token',
      { cuerpo, cabeceras: { 'Content-Type': 'application/x-www-form-urlencoded' }, autenticado: false }, f);
    if (!datos?.access_token) throw new Error('La respuesta de autenticación no contiene un token.');
    jwt = datos.access_token;
    return { expiraEn: datos.expires_in };
  } catch (e) {
    if (e.codigoHttp === 400 || e.codigoHttp === 401) e.message = 'Usuario o contraseña incorrectos.';
    throw e;
  }
}

const arreglo = (datos, que) => {
  if (!Array.isArray(datos)) throw new Error(`La API debe devolver un arreglo de ${que}.`);
  return datos;
};

export async function listarVehiculos(f = fetch) {
  const r = await pedir('GET', '/api/vehiculos', {}, f);
  return { codigoHttp: r.codigoHttp, vehiculos: arreglo(r.datos, 'vehículos') };
}

export async function listarCompradores(f = fetch) {
  const r = await pedir('GET', '/api/compradores', {}, f);
  return { codigoHttp: r.codigoHttp, compradores: arreglo(r.datos, 'compradores') };
}

export async function registrarVenta(vehiculoId, compradorId, clave, f = fetch) {
  const r = await pedir('POST', '/api/ventas', {
    cuerpo: JSON.stringify({ vehiculoId: Number(vehiculoId), compradorId: Number(compradorId) }),
    cabeceras: { 'Content-Type': 'application/json', 'Idempotency-Key': clave },
  }, f);
  return { codigoHttp: r.codigoHttp, venta: r.datos };
}

export async function consultarVenta(id, f = fetch) {
  if (!/^\d+$/.test(String(id).trim())) throw new Error('El ID de venta debe ser un número entero.');
  const r = await pedir('GET', `/api/ventas/${String(id).trim()}`, {}, f);
  return { codigoHttp: r.codigoHttp, venta: r.datos };
}
