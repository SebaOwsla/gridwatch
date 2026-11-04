# Revisión de seguridad y carga local — 3 de noviembre de 2026

## Alcance

Las pruebas se ejecutaron **solo contra `127.0.0.1`** en este equipo. La API
temporal se inició con `MQTT_ENABLED=false`. PostgreSQL/TimescaleDB, MQTT y
Docker no estaban disponibles; `/api/v1/health/ready` devolvió 503. Por ello,
los resultados de carga describen la entrega HTTP básica, no el rendimiento de
sesiones autenticadas con consultas y telemetría reales.

**Actualización posterior:** Docker Desktop ya está instalado. La pila local
arrancó con TimescaleDB, MQTT, API y web saludables; `/api/v1/health/ready`
respondió 200 y se guardaron 12 de 12 mediciones simuladas. Las cifras de carga
de esta revisión siguen correspondiendo a la prueba HTTP inicial.

### Carga autenticada con la pila Docker

Se inició sesión como administrador y se lanzaron 100 clientes concurrentes
contra `GET /api/v1/installations` en `127.0.0.1:8000`. Cada cliente reutilizó
el mismo JWT y realizó tres consultas. Mosquitto, el simulador y TimescaleDB
permanecieron activos. La primera ejecución reveló agotamiento del pool SQL:
100 tiempos de espera con 10 s de límite. Limitar las solicitudes HTTP activas
a 16 y ajustar el pool a 20 conexiones más 5 de reserva resolvió el bloqueo.

| Clientes | Consultas | HTTP 200 | Errores | Duración | Rendimiento | Latencia p95 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 100 | 300 | 300 | 0 | 6,374 s | 47,1 req/s | 4394 ms |

La prueba demuestra que esta API local atendió esa ráfaga de consultas
autenticadas. No mide 100 navegadores independientes, sesiones con WebSocket,
reportes, mezcla de rutas ni capacidad sostenida de producción. El proxy Nginx
aplica además sus propios límites por IP; la carga se dirigió a la API local
para medir el backend sin ese límite.

Con PostgreSQL real se repitieron dos intentos de inyección SQL en el login:
una tautología y una búsqueda dirigida por correo. Ambos devolvieron 401; el
inicio de sesión legítimo posterior devolvió 200. Esta comprobación cubre esa
ruta y esos valores, no constituye una auditoría completa de inyección.

## Resultados

| Comprobación | Resultado |
| --- | --- |
| HTTP de la interfaz local y la API | 200 en `/` y `/api/v1/health/live`. Las rutas de datos sin JWT devuelven 401. |
| HTTPS en 5173 y 8000 | No configurado: el handshake TLS falla porque ambos puertos sirven HTTP. El puerto 443 local está cerrado. |
| SSH local | Puerto 22 cerrado. GridWatch no incluye un servidor SSH; no había un servicio SSH que auditar. |
| Inyección SQL en inicio de sesión | Tres cadenas se mantienen como parámetros SQL. En una base SQLite de prueba, dos intentos no iniciaron sesión ni eliminaron la tabla; el acceso legítimo siguió funcionando. |
| Origen CORS y cabecera `Host` | Un origen externo no recibe permiso CORS; un `Host` no autorizado recibe 400. |
| Dependencias JavaScript | `npm audit`: 0 vulnerabilidades reportadas. |
| Dependencias Python | `pip-audit` detectó avisos en `pip 23.2.1` del entorno virtual. Se actualizó a `pip 26.3` y la segunda ejecución reportó 0 vulnerabilidades conocidas. Los paquetes locales GridWatch no figuran en PyPI y no son auditables por esa herramienta. |

### Carga controlada de 100 usuarios virtuales

Cada prueba usó 100 tareas simultáneas en un solo cliente local, con límite de
10 segundos por solicitud. La latencia p95 corresponde a solicitudes
individuales, no al tiempo de renderizado en un navegador. No se generó tráfico
distribuido ni sostenido.

| Destino | Solicitudes | HTTP 200 | Duración | Rendimiento | Latencia p95 |
| --- | ---: | ---: | ---: | ---: | ---: |
| API `/health/live`, 3 solicitudes por usuario | 300 | 300 | 5,505 s | 54,5 req/s | 3914 ms |
| Interfaz compilada, HTML + CSS + JS por usuario | 300 | 300 | 3,222 s | 93,1 req/s | 2401 ms |
| Servidor Vite de desarrollo, solo HTML, 3 solicitudes por usuario | 300 | 300 | 6,077 s | 49,4 req/s | 4377 ms |

**Conclusión de capacidad:** 100 clientes HTTP concurrentes completaron esas
solicitudes sin error en esta máquina. El umbral real de personas simultáneas no
puede estimarse todavía: faltan pruebas con usuarios autenticados, base de
datos, gráficos, WebSockets y una infraestructura de producción. Esta ráfaga
local no demuestra resistencia a un DDoS.

## Cambios realizados durante la revisión

- La API restringe `Host` mediante `TRUSTED_HOSTS` y añade
  `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
  `Referrer-Policy: no-referrer` y `Cache-Control: no-store` para `/api/`.
- Vite añade las tres cabeceras de navegador a las vistas de desarrollo y
  preview. Se comprobaron por HTTP en 5173, 4173 y 8000.
- El WebSocket recibe el JWT en su primer mensaje, tras abrir el canal, en vez
  de incluirlo en la URL o en una cabecera del handshake. Exige origen permitido
  y un usuario activo.
- Las pruebas automatizadas cubren cadenas de inyección SQL, rechazo de
  `Host`/CORS, JWT, roles y autenticación WebSocket.

## Riesgos pendientes antes de publicar

1. **TLS:** configurar un proxy HTTPS con certificado válido, redirección de
   HTTP a HTTPS y HSTS solo después de confirmar el despliegue HTTPS. HTTPS y
   WSS no se pudieron verificar aquí porque no existe ese proxy.
2. **Abuso y DDoS:** la configuración Nginx incluye límites básicos de
   solicitudes por IP. Falta protección en el borde
   para tráfico distribuido; un proceso local de carga no puede validarla.
3. **Integración:** la ingesta real de 12 muestras y una ráfaga de 100 clientes
   autenticados se verificaron en Docker. Sigue pendiente medir una mezcla de
   rutas, reportes, WebSockets, cuentas distintas y duración sostenida. El
   workflow CI comprueba también la ingesta cuando se ejecute en GitHub Actions.
4. **Sesiones y contenido:** el JWT se mantiene en `sessionStorage`; una XSS
   podría leerlo. Definir CSP de producción y revisar el modelo de sesión antes
   de exponer la aplicación públicamente.
5. **Broker:** MQTT de demostración debe permanecer aislado en red local y
   autenticarse si se expone a otro entorno.

## Repetir las pruebas

Desde `backend/`, con API y preview local en ejecución:

```powershell
.\.venv\Scripts\python -m pytest -q tests ../simulator/tests
.\.venv\Scripts\python tools/load_probe.py http://127.0.0.1:8000/api/v1/health/live --users 100 --requests-per-user 3
.\.venv\Scripts\python tools/load_probe.py http://127.0.0.1:4173/ --users 100 --requests-per-user 1 --page
```

Para repetir la carga autenticada, guarda temporalmente un JWT obtenido de
`/api/v1/auth/login` en `GRIDWATCH_LOAD_TOKEN` y ejecuta:

```powershell
.\.venv\Scripts\python tools/load_probe.py http://127.0.0.1:8000/api/v1/installations --users 100 --requests-per-user 3 --bearer-token-env GRIDWATCH_LOAD_TOKEN
```

El script de carga **rechaza destinos remotos** y limita cada ejecución a 100
usuarios virtuales, cinco ciclos por usuario y diez recursos adicionales por
página. Las cifras dependen del
equipo y de otros procesos activos.

Referencias de criterio: [OWASP SQL Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet),
[OWASP HTTP Headers](https://cheatsheetseries.owasp.org/cheatsheets/HTTP_Headers_Cheat_Sheet),
[OWASP Denial of Service](https://cheatsheetseries.owasp.org/cheatsheets/Denial_of_Service_Cheat_Sheet).
