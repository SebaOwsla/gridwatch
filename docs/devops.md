# Ejecución local con Docker Compose

Esta configuración levanta PostgreSQL/TimescaleDB, Mosquitto, FastAPI, el
frontend React compilado y el servicio de retención. El simulador se activa por separado después de cargar
los activos ficticios. **Es un entorno local de demostración:** solo publica
puertos en `127.0.0.1`, sirve HTTP y usa un broker MQTT anónimo aislado.

## Preparación

1. Instala Docker Desktop con Compose.
2. En la raíz, copia `.env.example` a `.env` si aún no existe y configura
   `POSTGRES_PASSWORD` y `JWT_SECRET_KEY` con valores propios. Mantén `.env`
   fuera del repositorio.
3. Inicia los servicios:

```powershell
docker compose config --quiet
docker compose up -d --build
docker compose ps
```

La API ejecuta `alembic upgrade head` al arrancar, después de que PostgreSQL
pase su comprobación de salud. El frontend queda en
`http://127.0.0.1:8080/`, la documentación API en
`http://127.0.0.1:8000/docs` y la ruta de disponibilidad en
`http://127.0.0.1:8080/api/v1/health/ready`.

## Abrir la página desde un celular en la misma red Wi-Fi

Busca la IPv4 del computador con `ipconfig` y asigna esa dirección a
`GRIDWATCH_WEB_BIND_IP` en `.env`. Luego aplica el cambio:

```powershell
docker compose up -d api web
```

Desde el celular, conectado a la misma red Wi-Fi, abre
`http://<IPv4-del-computador>:8080/`. El acceso se sirve por HTTP dentro de la
red local. La API y MQTT conservan sus puertos publicados únicamente en
`127.0.0.1`; Nginx transmite las solicitudes de la web a la API dentro de
Docker. Si cambia la IPv4 del computador, actualiza `.env`, reinicia los
servicios y vuelve a ejecutar el script del firewall con la nueva dirección
y subred.

En Windows, el firewall puede impedir conexiones de otros equipos. Ejecuta
PowerShell como administrador y permite solo el puerto 8080 y la subred local;
por ejemplo, para `192.168.1.8/24`:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\infra\windows\allow-gridwatch-lan.ps1 -LocalAddress 192.168.1.8 -RemoteSubnet 192.168.1.0/24
```

La regla se llama `GridWatch Demo LAN (TCP 8080)`. Verifica el puerto desde el
computador con `http://<IPv4-del-computador>:8080/api/v1/health/ready` y
desde el celular abriendo la página. No se configura acceso por Internet.

## Datos de demostración y simulador

Una vez, con la base vacía:

```powershell
docker compose exec api python -m app.cli seed-demo
docker compose exec api python -m app.cli create-admin --email admin@example.com --name "Admin GridWatch"
docker compose --profile live up -d --build simulator
```

El segundo comando solicita una contraseña en la terminal. Como alternativa,
añade `--generate-password` para recibir una contraseña aleatoria una sola vez.
Para automatización local se puede usar `--password-stdin` y enviar la contraseña
por entrada estándar, sin incluirla como argumento del proceso.
Inicia sesión en
la página para ver lecturas en vivo. La vista demo local funciona sin iniciar
sesión, pero presenta datos estáticos. El perfil `live` evita que el simulador
publique antes de cargar los equipos.

Para revisar logs o detener la pila conservando los datos:

```powershell
docker compose logs --tail=100 api mqtt simulator
docker compose down
```

`docker compose down -v` **elimina también la base de datos**. Se usa solo en
el trabajo temporal de CI.

## Respaldo, restauración de prueba y retención

Con Docker Desktop encendido, ejecuta desde la raíz:

```powershell
py -3.12 backend/tools/backup_db.py --verify
```

El script crea un archivo comprimido de PostgreSQL en `backups/`, calcula su
SHA-256, lo restaura en una base temporal del mismo contenedor y comprueba que
la hipertabla y sus tablas son legibles. En esa base temporal inserta una
medición de 70 días, ejecuta la retención y confirma que las lecturas recientes
se conservan. Elimina esa base temporal al
terminar. `backups/` está excluido de Git porque contiene cuentas e historial;
guarda una copia adicional fuera del computador si quieres protección ante
fallas del disco. Conserva la versión de PostgreSQL y TimescaleDB al restaurar.
La prueba usa el mismo contenedor y por ello verifica el archivo y el proceso
de restauración, no una recuperación ante pérdida completa del computador.

La migración `0003_measurement_retention` crea la función de mantenimiento. El
servicio `retention` la ejecuta diariamente para eliminar chunks de
`measurements` anteriores a 35 días. La imagen Apache/OSS de TimescaleDB no
incluye `add_retention_policy`, por lo que esta tarea usa `drop_chunks`, que sí
está disponible. Los reportes permiten 31 días;
alertas, instalaciones, usuarios y auditoría permanecen. Antes de cambiar el
plazo, crea y verifica un respaldo. Puedes consultar la política con:

```powershell
docker compose logs --tail=20 retention
docker compose exec db psql -U gridwatch -d gridwatch -c "SELECT proname FROM pg_proc WHERE proname = 'gridwatch_apply_measurement_retention'"
```

El CI también crea y restaura una copia temporal tras la prueba integral.
Procedimiento basado en la [guía oficial de respaldo lógico](https://www.tigerdata.com/docs/deploy/self-hosted/backup-and-restore/logical-backup)
y la [API `drop_chunks`](https://www.tigerdata.com/docs/reference/timescaledb/hypertable/drop_chunks).


## Seguridad y alcance

- El proxy Nginx aplica cabeceras de navegador, una CSP básica, límites por IP
  para API y login, y un tamaño máximo de solicitud de 64 KiB. Mantiene el
  paso de WebSocket para las mediciones.
- PostgreSQL no publica puerto al equipo anfitrión. MQTT, API y frontend se
  vinculan solo a `127.0.0.1`.
- Para publicar fuera del equipo se requiere un proxy HTTPS con certificado
  válido, WSS, HSTS y protección de tráfico en el borde. Los límites locales
  de Nginx no equivalen a defensa contra DDoS distribuido.

## Integración continua

El workflow [ci.yml](../.github/workflows/ci.yml) ejecuta pruebas Python y
React, compilación, auditorías de dependencias y una comprobación con Compose.
Esta última migra la base, carga los activos, publica tres ciclos de cuatro
mediciones mediante MQTT y verifica al menos 12 filas en TimescaleDB. Después
crea un administrador temporal con contraseña aleatoria y ejecuta
`backend/tools/integration_smoke.py`: comprueba JWT, WebSocket, una alerta,
historial, tendencias de 24 horas y 7 días, PDF de 24 horas, Excel detallado,
Excel resumido y auditoría a través de los puertos locales de la pila.

La misma prueba se puede repetir en este equipo con los servicios activos y
un administrador ya creado. Define `GRIDWATCH_SMOKE_EMAIL` y
`GRIDWATCH_SMOKE_PASSWORD` solo en la sesión de terminal y ejecuta desde la
raíz:

```powershell
.\backend\.venv\Scripts\python backend/tools/integration_smoke.py
```

La prueba publica dos lecturas ficticias del alimentador principal; detén
temporalmente el simulador continuo para comprobar la transición de la alerta
sin interferencia de otras lecturas.

La pila local se construyó y arrancó en Docker Desktop. Se verificaron los
estados saludables de la base, API y web, la extensión TimescaleDB 2.31.0,
las migraciones, la persistencia de 12 lecturas publicadas por MQTT y la prueba
integral autenticada. El primer workflow de GitHub Actions pasó sus tres
trabajos: backend, frontend e integración Docker.

### Ejecutar GitHub Actions

El repositorio público está en
[SebaOwsla/gridwatch](https://github.com/SebaOwsla/gridwatch). `origin` apunta a
esa dirección. Cada `git push` a `main` ejecuta `GridWatch CI` de forma
automática. Para iniciarlo manualmente desde la consola:

```powershell
gh workflow run ci.yml --repo SebaOwsla/gridwatch
gh run list --repo SebaOwsla/gridwatch --limit 5
```

También puedes abrir la pestaña **Actions**, elegir **GridWatch CI** y pulsar
**Run workflow**.
Los tres trabajos comprueban backend, frontend e integración Docker; esta
última incluye respaldo, restauración y prueba de retención en una base
temporal. El workflow usa contraseñas ficticias solo dentro del runner de CI,
por lo que no necesita secretos de tu instalación local. `.env`, `backups/`
y los archivos compilados están fuera del repositorio.

Si un trabajo falla, abre su registro en Actions. El trabajo de integración
publica los últimos mensajes de los contenedores al fallar y borra los
volúmenes temporales al terminar.
