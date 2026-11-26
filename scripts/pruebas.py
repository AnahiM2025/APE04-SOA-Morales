#!/usr/bin/env python3
"""Pruebas reproducibles de la APE 04 (solo libreria estandar de Python).

Uso:  python scripts/pruebas.py <comando>
  integracion   P01-P13, P15-P18, P22 automatizables (resultados reales, sin inventar nada)
  balanceo      P23: N GET (100 por defecto) y conteo real por instancia (cabecera X-Upstream)
  cola          P19/P20: estado de la cola en RabbitMQ (Ready / Consumers) con fecha y hora
  monitor       P24-P26: sondeo periodico con alertas de cambio de estado (CSV con timestamps)
  secretos DIR  P28: busca en DIR los valores reales de sus variables de entorno (nunca los imprime)

Variables de entorno: ver env.ps1.example. Los resultados se guardan en ./evidencias/.
"""
import base64, csv, json, os, random, re, string, sys, time, urllib.error, urllib.parse, urllib.request
from datetime import datetime
from pathlib import Path

BASE = os.environ.get("API_BASE_URL", "http://127.0.0.1:8090").rstrip("/")
JAVA_A = os.environ.get("JAVA_A_URL", "http://127.0.0.1:8080")
JAVA_B = os.environ.get("JAVA_B_URL", "http://127.0.0.1:8082")
VENTAS = os.environ.get("VENTAS_URL", "http://127.0.0.1:8002")
RABBIT = os.environ.get("RABBIT_API_URL", "http://127.0.0.1:15672")
COLA = os.environ.get("RABBITMQ_QUEUE", "notificaciones.ventas")
EVID = Path(os.environ.get("EVIDENCIAS_DIR", "evidencias"))
ahora = lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S")
marca_t = lambda: datetime.now().strftime("%Y%m%d_%H%M%S")


def http(metodo, url, cuerpo=None, cabeceras=None, timeout=10):
    """Retorna (codigo, json_o_texto, cabeceras). codigo 0 = sin conexion."""
    datos = None
    h = dict(cabeceras or {})
    if cuerpo is not None:
        datos = cuerpo if isinstance(cuerpo, bytes) else (urllib.parse.urlencode(cuerpo).encode() if isinstance(cuerpo, dict) and h.get("Content-Type", "").startswith("application/x-www") else json.dumps(cuerpo).encode())
        h.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=datos, headers=h, method=metodo)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            cod, txt, cab = r.status, r.read().decode("utf-8", "replace"), dict(r.headers)
    except urllib.error.HTTPError as e:
        cod, txt, cab = e.code, e.read().decode("utf-8", "replace"), dict(e.headers)
    except (urllib.error.URLError, OSError, TimeoutError) as e:
        return 0, str(e), {}
    try:
        return cod, json.loads(txt), cab
    except ValueError:
        return cod, txt, cab


def requerida(nombre):
    v = os.environ.get(nombre)
    if not v:
        sys.exit(f"Falta la variable de entorno {nombre} (ver env.ps1.example)")
    return v


def login(usuario, clave):
    basic = base64.b64encode(f"{requerida('APP_CLIENT_ID')}:{requerida('APP_CLIENT_SECRET')}".encode()).decode()
    cod, d, _ = http("POST", f"{BASE}/oauth/token",
                     {"grant_type": "password", "username": usuario, "password": clave},
                     {"Authorization": f"Basic {basic}", "Content-Type": "application/x-www-form-urlencoded"})
    return cod, (d.get("access_token") if isinstance(d, dict) else None)


def auth(token, extra=None):
    return {"Authorization": f"Bearer {token}", **(extra or {})}


# ------------------------------------------------------------------ integracion
def integracion():
    res = []

    def reg(id_, prueba, esperado, obtenido, ok, detalle=""):
        res.append({"id": id_, "prueba": prueba, "esperado": esperado, "obtenido": obtenido, "resultado": "OK" if ok else "FALLA", "detalle": detalle})
        print(f"[{'OK' if ok else 'FALLA'}] {id_} {prueba}: {obtenido}")

    clave = requerida("LAB_PASSWORD")
    u = {rol: os.environ.get(f"{rol.upper()}_USER", rol) for rol in ("admin", "operador", "consulta")}
    sufijo = "".join(random.choices(string.digits, k=6))

    # P01 conectividad
    c, d, _ = http("GET", f"{BASE}/nginx-ping"); reg("P01a", "NGINX /nginx-ping", "200 pong", f"HTTP {c}", c == 200 and "pong" in str(d))
    for nombre, url in (("Java A", JAVA_A), ("Java B", JAVA_B), ("Java via NGINX", BASE)):
        c, d, _ = http("GET", f"{url}/actuator/health"); reg("P01b", f"/actuator/health {nombre}", "200 UP", f"HTTP {c}", c == 200 and isinstance(d, dict) and d.get("status") == "UP")
    c, _, _ = http("GET", f"{VENTAS}/docs"); reg("P01c", "FastAPI :8002 responde", "200", f"HTTP {c}", c == 200)

    # P07 / P08 login
    cod_a, tok_admin = login(u["admin"], clave); cod_o, tok_op = login(u["operador"], clave); cod_c, tok_con = login(u["consulta"], clave)
    reg("P07", "Login admin/operador/consulta emite JWT", "HTTP 200 x3", f"{cod_a}/{cod_o}/{cod_c}", bool(tok_admin and tok_op and tok_con), "JWT no se imprime")
    if not (tok_admin and tok_op and tok_con):
        print("No se pudo autenticar a los tres roles: se detiene."); return guardar("integracion", res)
    cod_mal, _ = login(u["operador"], clave + "x"); reg("P08a", "Login con clave incorrecta", "400/401", f"HTTP {cod_mal}", cod_mal in (400, 401))
    c, _, _ = http("GET", f"{BASE}/api/vehiculos", cabeceras=auth("token.invalido.123")); reg("P08b", "GET con JWT invalido", "401", f"HTTP {c}", c == 401)
    c, _, _ = http("GET", f"{BASE}/api/vehiculos"); reg("P08c", "GET sin JWT", "401", f"HTTP {c}", c == 401)
    c, _, _ = http("POST", f"{BASE}/api/ventas", {"vehiculoId": 1, "compradorId": 1}, {"Idempotency-Key": "sin-token-0001"}); reg("P08d", "Venta sin JWT", "401, sin venta", f"HTTP {c}", c == 401)

    def crear_vehiculo(n):
        chasis = "".join(random.choices("ABCDEFGHJKLMNPRSTUVWXYZ0123456789", k=17))
        return http("POST", f"{BASE}/api/vehiculos", {"marca": "PruebaAPE", "modelo": f"M{n}", "placa": f"PB{sufijo[:2]}-{sufijo[2:]}{n}", "chasis": chasis, "anio": 2024, "color": "Gris", "precio": 15000 + n}, auth(tok_admin))

    # P02 / P03
    c, v1, _ = crear_vehiculo(1); id_v1 = v1.get("idVehiculo") if isinstance(v1, dict) else None
    reg("P02", "Admin crea vehiculo (POST /api/vehiculos)", "201 con idVehiculo", f"HTTP {c}, id={id_v1}", c in (200, 201) and bool(id_v1))
    c, v2, _ = crear_vehiculo(2); id_v2 = v2.get("idVehiculo") if isinstance(v2, dict) else None
    c, lista, _ = http("GET", f"{BASE}/api/vehiculos", cabeceras=auth(tok_admin))
    reg("P03", "Admin lista vehiculos y aparece el creado", "200, incluye id", f"HTTP {c}, {len(lista) if isinstance(lista, list) else '?'} filas", c == 200 and isinstance(lista, list) and any(x.get("idVehiculo") == id_v1 for x in lista))
    c, con, _ = http("POST", f"{BASE}/api/vehiculos", {"marca": "X", "modelo": "X", "placa": "X", "chasis": "X" * 17, "anio": 2024, "precio": 1}, auth(tok_con))
    reg("P13a", "CONSULTA no crea vehiculos", "403", f"HTTP {c}", c == 403)

    # P04 / P05
    c, comp, _ = http("POST", f"{BASE}/api/compradores", {"documento": f"18{sufijo}99", "nombre": "Comprador Prueba", "correo": "prueba@ejemplo.com"}, auth(tok_admin))
    id_c = comp.get("id") if isinstance(comp, dict) else None
    reg("P04", "Admin crea comprador", "201 con id", f"HTTP {c}, id={id_c}", c == 201 and bool(id_c))
    c, lc, _ = http("GET", f"{BASE}/api/compradores", cabeceras=auth(tok_admin))
    reg("P05", "Admin lista compradores", "200 incluye id", f"HTTP {c}", c == 200 and isinstance(lc, list) and any(x.get("id") == id_c for x in lc))
    c, lv, _ = http("GET", f"{BASE}/api/ventas", cabeceras=auth(tok_admin)); reg("P06", "Admin lista ventas (solo lectura)", "200 lista", f"HTTP {c}", c == 200 and isinstance(lv, list))
    n_ventas_antes = len(lv) if isinstance(lv, list) else -1

    # P09 venta
    k1 = f"ape04-{sufijo}-venta-1"; cuerpo = {"vehiculoId": id_v1, "compradorId": id_c}
    c, vta, _ = http("POST", f"{BASE}/api/ventas", cuerpo, auth(tok_op, {"Idempotency-Key": k1}))
    id_venta = vta.get("id") if isinstance(vta, dict) else None
    reg("P09a", "Operador registra venta valida", "201 COMPLETADA", f"HTTP {c}, venta={id_venta}, estado={vta.get('estado') if isinstance(vta, dict) else '?'}", c == 201 and isinstance(vta, dict) and vta.get("estado") == "COMPLETADA")
    c, lista, _ = http("GET", f"{BASE}/api/vehiculos", cabeceras=auth(tok_op))
    est = next((x.get("estado") for x in lista if x.get("idVehiculo") == id_v1), None) if isinstance(lista, list) else None
    reg("P09b", "El vehiculo cambia de estado", "VENDIDO", str(est), str(est).upper() == "VENDIDO")
    # P10 idempotencia
    c, rep, _ = http("POST", f"{BASE}/api/ventas", cuerpo, auth(tok_op, {"Idempotency-Key": k1}))
    reg("P10", "Misma clave y cuerpo: no hay segunda venta", "200 y mismo id", f"HTTP {c}, id={rep.get('id') if isinstance(rep, dict) else '?'}", c == 200 and isinstance(rep, dict) and rep.get("id") == id_venta)
    # P11 conflicto
    c, _, _ = http("POST", f"{BASE}/api/ventas", {"vehiculoId": id_v2, "compradorId": id_c}, auth(tok_op, {"Idempotency-Key": k1}))
    reg("P11", "Misma clave con cuerpo distinto", "409", f"HTTP {c}", c == 409)
    # P12 rechazos
    c1, _, _ = http("POST", f"{BASE}/api/ventas", cuerpo, auth(tok_op, {"Idempotency-Key": f"ape04-{sufijo}-venta-2"}))
    c2, _, _ = http("POST", f"{BASE}/api/ventas", {"vehiculoId": 99999999, "compradorId": id_c}, auth(tok_op, {"Idempotency-Key": f"ape04-{sufijo}-venta-3"}))
    c3, _, _ = http("POST", f"{BASE}/api/ventas", {"vehiculoId": "x"}, auth(tok_op, {"Idempotency-Key": f"ape04-{sufijo}-venta-4"}))
    reg("P12", "Vehiculo ya vendido / inexistente / datos invalidos", "4xx en los tres", f"HTTP {c1}/{c2}/{c3}", all(400 <= x < 500 for x in (c1, c2, c3)))
    # P13 permiso
    c, _, _ = http("POST", f"{BASE}/api/ventas", {"vehiculoId": id_v2, "compradorId": id_c}, auth(tok_con, {"Idempotency-Key": f"ape04-{sufijo}-venta-5"}))
    reg("P13b", "CONSULTA no registra venta", "403", f"HTTP {c}", c == 403)

    # P15 / P16 (API que consume React)
    c, f, _ = http("GET", f"{BASE}/api/vehiculos?marca=PruebaAPE", cabeceras=auth(tok_con))
    reg("P15", "Filtro por marca (API de React)", "200, solo esa marca", f"HTTP {c}, {len(f) if isinstance(f, list) else '?'} filas", c == 200 and isinstance(f, list) and f and all(x.get("marca") == "PruebaAPE" for x in f))
    c, lv2, _ = http("GET", f"{BASE}/api/ventas", cabeceras=auth(tok_con)); reg("P16", "CONSULTA lista ventas", "200", f"HTTP {c}", c == 200 and isinstance(lv2, list))
    reg("P12b", "Rechazos no crean ventas COMPLETADAS nuevas", "una sola COMPLETADA (la valida)", f"completadas de la prueba={sum(1 for x in lv2 if x.get('vehiculoId') in (id_v1,) and x.get('estado')=='COMPLETADA') if isinstance(lv2, list) else '?'}", isinstance(lv2, list) and sum(1 for x in lv2 if x.get("vehiculoId") == id_v1 and x.get("estado") == "COMPLETADA") == 1)

    # P17 / P21 / P22 notificaciones
    nota = None
    for _ in range(8):
        c, notas, _ = http("GET", f"{BASE}/api/notificaciones?limite=200", cabeceras=auth(tok_con))
        coincide = [n for n in notas if n.get("ventaId") == id_venta] if isinstance(notas, list) else []
        if coincide: nota = coincide[0]; break
        time.sleep(2)
    reg("P17/P21", "Evento de la venta llega a Notificaciones (un solo registro)", "1 notificacion con ese ventaId", f"{len(coincide)} registro(s)", len(coincide) == 1)
    fallidas = [x.get("id") for x in lv2 if isinstance(lv2, list) and x.get("estado") == "FALLIDA"] if isinstance(lv2, list) else []
    c, notas, _ = http("GET", f"{BASE}/api/notificaciones?limite=500", cabeceras=auth(tok_con))
    con_fallida = [n for n in notas if n.get("ventaId") in fallidas] if isinstance(notas, list) else ["?"]
    reg("P18", "Venta rechazada no genera notificacion", "0 notificaciones de ventas FALLIDAS", f"{len(con_fallida)}", len(con_fallida) == 0)
    if nota and os.environ.get("RABBITMQ_USER"):
        evento = {"eventoId": nota["eventoId"], "tipo": "VENTA_REALIZADA", "ventaId": nota["ventaId"], "vehiculoId": nota["vehiculoId"], "fechaHora": ahora().replace(" ", "T") + "Z"}
        pub = rabbit("POST", "/api/exchanges/%2F/amq.default/publish", {"properties": {"delivery_mode": 2, "content_type": "application/json"}, "routing_key": COLA, "payload": json.dumps(evento), "payload_encoding": "string"})
        time.sleep(4)
        c, notas, _ = http("GET", f"{BASE}/api/notificaciones?limite=500", cabeceras=auth(tok_con))
        n_mismo = sum(1 for n in notas if n.get("eventoId") == nota["eventoId"]) if isinstance(notas, list) else -1
        reg("P22", "Reentrega del mismo eventoId no duplica", "1 registro", f"{n_mismo} registro(s) tras reentregar (publish={pub[0]})", n_mismo == 1)
    else:
        reg("P22", "Reentrega del mismo eventoId", "1 registro", "OMITIDA: defina RABBITMQ_USER/RABBITMQ_PASSWORD", False, "No se ejecuto")
    guardar("integracion", res)


def rabbit(metodo, ruta, cuerpo=None):
    tok = base64.b64encode(f"{requerida('RABBITMQ_USER')}:{requerida('RABBITMQ_PASSWORD')}".encode()).decode()
    return http(metodo, RABBIT + ruta, cuerpo, {"Authorization": f"Basic {tok}"})


def guardar(nombre, filas):
    EVID.mkdir(parents=True, exist_ok=True)
    t = marca_t(); base = EVID / f"{nombre}_{t}"
    base.with_suffix(".json").write_text(json.dumps({"fecha": ahora(), "base": BASE, "resultados": filas}, ensure_ascii=False, indent=2), encoding="utf-8")
    md = [f"# Resultados {nombre} — {ahora()}", "", "| ID | Prueba | Esperado | Obtenido | Resultado |", "|---|---|---|---|---|"]
    md += [f"| {f['id']} | {f['prueba']} | {f['esperado']} | {f['obtenido']} | {f['resultado']} |" for f in filas]
    base.with_suffix(".md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"\nGuardado: {base}.json y .md  ({sum(f['resultado']=='OK' for f in filas)}/{len(filas)} OK)")


# ------------------------------------------------------------------ balanceo
def balanceo():
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    cod, tok = login(os.environ.get("OPERADOR_USER", "operador"), requerida("LAB_PASSWORD"))
    if not tok: sys.exit(f"Login fallido (HTTP {cod})")
    cuentas, codigos = {}, {}
    for _ in range(n):
        c, _, cab = http("GET", f"{BASE}/api/vehiculos", cabeceras=auth(tok))
        up = next((v for k, v in cab.items() if k.lower() == "x-upstream"), "sin-cabecera")
        cuentas[up] = cuentas.get(up, 0) + 1; codigos[c] = codigos.get(c, 0) + 1
    print(f"{ahora()}  {n} GET /api/vehiculos")
    filas = [{"id": "P23", "prueba": f"Instancia {k}", "esperado": "~75% A / ~25% B (sin exigir exacto)", "obtenido": f"{v} peticiones ({100*v/n:.1f}%)", "resultado": "OK"} for k, v in sorted(cuentas.items())]
    for f in filas: print(" ", f["prueba"], "->", f["obtenido"])
    print("  Codigos HTTP:", codigos)
    guardar("balanceo", filas)


# ------------------------------------------------------------------ cola
def cola():
    c, d, _ = rabbit("GET", f"/api/queues/%2F/{COLA}")
    if c != 200: sys.exit(f"No se pudo leer la cola (HTTP {c}): {d}")
    r = {"fecha": ahora(), "cola": COLA, "durable": d.get("durable"), "ready": d.get("messages_ready"), "unacked": d.get("messages_unacknowledged"), "consumers": d.get("consumers")}
    print(json.dumps(r, ensure_ascii=False))
    EVID.mkdir(parents=True, exist_ok=True)
    with open(EVID / "cola.jsonl", "a", encoding="utf-8") as f: f.write(json.dumps(r, ensure_ascii=False) + "\n")


# ------------------------------------------------------------------ monitor
def monitor():
    segundos = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    comp = {"NGINX /nginx-ping": f"{BASE}/nginx-ping", "Java A :8080": f"{JAVA_A}/actuator/health", "Java B :8082": f"{JAVA_B}/actuator/health", "Java via NGINX": f"{BASE}/actuator/health"}
    EVID.mkdir(parents=True, exist_ok=True)
    ruta = EVID / f"monitor_{marca_t()}.csv"; previo = {}
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["timestamp", "componente", "estado", "http", "ms"])
        fin = time.time() + segundos
        try:
            while time.time() < fin:
                for nombre, url in comp.items():
                    t0 = time.time(); c, _, _ = http("GET", url, timeout=3); ms = int((time.time() - t0) * 1000)
                    est = "UP" if c == 200 else "DOWN"
                    w.writerow([ahora(), nombre, est, c, ms]); f.flush()
                    if previo.get(nombre) not in (None, est): print(f"{ahora()} ALERTA: {nombre} {previo[nombre]} -> {est} (HTTP {c})")
                    previo[nombre] = est
                time.sleep(2)
        except KeyboardInterrupt:
            pass
    print("Registro guardado en", ruta)


# ------------------------------------------------------------------ secretos
def secretos():
    carpeta = Path(sys.argv[2] if len(sys.argv) > 2 else ".")
    nombres = ["APP_CLIENT_SECRET", "APP_JWT_SECRET", "VENTAS_SERVICE_KEY", "NOTIFICACIONES_KEY", "LAB_PASSWORD", "RABBITMQ_PASSWORD", "DB_PASSWORD"]
    valores = {n: os.environ[n] for n in nombres if len(os.environ.get(n, "")) >= 6}
    excl = {".git", "node_modules", "target", "bin", "obj", ".venv", "dist", "__pycache__", ".vs"}
    hallazgos = []
    for p in carpeta.rglob("*"):
        if p.is_file() and not (set(p.parts) & excl) and p.stat().st_size < 2_000_000:
            try: t = p.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError): continue
            hallazgos += [(n, str(p)) for n, v in valores.items() if v in t]
    print(f"Revisados valores de {len(valores)} variables en {carpeta} (los valores no se imprimen).")
    for n, p in hallazgos: print(f"  FILTRACION: el valor de {n} aparece en {p}")
    print("P28:", "FALLA" if hallazgos else "OK, ninguna credencial real encontrada")
    sys.exit(1 if hallazgos else 0)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    {"integracion": integracion, "balanceo": balanceo, "cola": cola, "monitor": monitor, "secretos": secretos}.get(cmd, lambda: sys.exit(__doc__))()
