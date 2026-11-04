# GridWatch

Plataforma web de demostración para monitoreo eléctrico industrial. El proyecto
representa instalaciones y equipos de minería, centrales hidroeléctricas y
subestaciones mediante datos simulados. No incluye conexión de control a equipos
eléctricos reales.

## Estado

**Fases 1 a 6 implementadas y verificadas localmente:** estructura, esquema de
datos, API REST, interfaz React responsive, telemetría simulada y Docker Compose.
La pila arrancó con TimescaleDB 2.31.0, Mosquitto, FastAPI y Nginx; el simulador
publicó 12 mediciones MQTT y las 12 se guardaron en TimescaleDB. Abre
`http://127.0.0.1:8080/` para ver la aplicación local. Consulta
[la arquitectura](docs/architecture.md),
[el modelo de datos](docs/data-model.md), [la API](docs/backend-api.md),
[la interfaz](docs/frontend.md), [la telemetría](docs/realtime.md) y
[la guía Docker/CI](docs/devops.md).
La [revisión de seguridad y carga](docs/security-review.md) registra las
pruebas locales de 100 usuarios virtuales y los límites actuales.
Una prueba integral local comprueba también inicio de sesión, WebSocket,
alertas, historial, reportes PDF/Excel y auditoría; está incorporada al CI.
Los gráficos de 24 horas y 7 días usan intervalos de TimescaleDB y muestran
estadísticas de todo el periodo, aunque la tabla de lecturas recientes esté
limitada a 1000 filas.
Los reportes PDF y Excel resumido admiten hasta 31 días; el Excel detallado
conserva un límite de 5000 muestras para mantener acotado el archivo.
Las mediciones tienen retención de 35 días. La
[guía Docker/CI](docs/devops.md) incluye respaldo y restauración de prueba.

## Estructura

| Ruta | Propósito |
| --- | --- |
| `backend/app/api/v1/` | Rutas HTTP versionadas de FastAPI |
| `backend/app/core/` | Configuración, autenticación y errores comunes |
| `backend/app/db/` | Configuración y modelos de PostgreSQL/TimescaleDB |
| `backend/migrations/` | Migraciones versionadas con Alembic |
| `backend/app/modules/` | Funciones de dominio: usuarios, instalaciones, equipos, mediciones, alertas, reportes y auditoría |
| `backend/app/realtime/` | Consumo MQTT y publicación WebSocket |
| `backend/tests/` | Pruebas automatizadas del backend |
| `frontend/src/app/` | Arranque, rutas y estado de sesión de React |
| `frontend/src/features/` | Vistas y lógica por función |
| `frontend/src/components/` | Componentes visuales compartidos |
| `frontend/src/lib/` | Cliente HTTP, WebSocket y utilidades |
| `simulator/` | Generador de telemetría ficticia |
| `infra/mqtt/` | Configuración del broker de demostración |
| `.github/workflows/` | Pruebas y comprobación de integración en CI |

## Preparación del entorno

1. Instala Python 3.12 o superior, Node.js con npm, Git y Docker con Compose.
2. Copia `.env.example` a `.env` y asigna valores propios a
   `POSTGRES_PASSWORD` y `JWT_SECRET_KEY`. En Windows puedes usar
   `Copy-Item .env.example .env`.
3. Genera un secreto JWT aleatorio, por ejemplo con
   `py -3.12 -c "import secrets; print(secrets.token_urlsafe(48))"`.

`.env` queda fuera de Git. Para levantar el proyecto completo, sigue
[la guía Docker/CI](docs/devops.md).

### Aplicar el esquema de datos

Se necesita una instancia PostgreSQL con TimescaleDB 2.13 o posterior y una base
`gridwatch` creada. El usuario de la migración debe poder crear la extensión
`timescaledb` si aún no está habilitada. Configura la conexión en `.env` y, desde
la raíz del proyecto, ejecuta en PowerShell:

```powershell
Set-Location backend
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -e .
.\.venv\Scripts\python -m alembic upgrade head
```

Para revisar las revisiones aplicadas, ejecuta
`.\.venv\Scripts\python -m alembic current` desde `backend/`.
La migración ya se aplicó en la instancia local de Docker Compose.

### Ejecutar la API

Desde `backend/`, instala el proyecto con herramientas de prueba y arranca
FastAPI:

```powershell
.\.venv\Scripts\python -m pip install -e ".[dev]"
.\.venv\Scripts\python -m uvicorn app.main:app --reload
```

La documentación interactiva queda en `http://127.0.0.1:8000/docs` y el estado
básico en `/api/v1/health/live`. El endpoint `/api/v1/health/ready` y las rutas
con datos requieren una base migrada; devuelven 503 si no está disponible.
Después de aplicar la migración, crea el primer administrador de forma
interactiva:

```powershell
.\.venv\Scripts\python -m app.cli create-admin --email admin@example.com --name "Admin GridWatch"
```

El comando solicita la contraseña sin mostrarla y solo funciona cuando la tabla
de usuarios está vacía. Ejecuta las pruebas con
`.\.venv\Scripts\python -m pytest -q tests` desde `backend/`.

Para activar la telemetría simulada, instala también `../simulator`, carga los
activos de demostración con `python -m app.cli seed-demo` y sigue
[la guía de telemetría](docs/realtime.md). Se necesita un broker MQTT local;
`python -m gridwatch_simulator --dry-run` permite revisar las muestras sin él.

### Ejecutar la interfaz

Desde `frontend/`, ejecuta `npm install` y `npm run dev`. Abre
`http://127.0.0.1:5173`; puedes entrar a la **vista demo local** sin base de
datos para revisar el dashboard y la navegación. El inicio de sesión JWT y las
operaciones persistentes requieren la API y una base migrada. `npm run build`
verifica TypeScript y compila la aplicación; `npm run test` comprueba el acceso
demo y sus límites de solo lectura. Consulta [la guía del frontend](docs/frontend.md).

## Fases

1. Estructura, arquitectura y configuración inicial.
2. Modelo relacional, esquema de mediciones y migraciones de TimescaleDB.
3. API, JWT, roles, validaciones, alertas, reportes y auditoría.
4. Interfaz responsive con gráficos, historial y consulta periódica a la API.
5. Simulador MQTT, WebSockets e integración de extremo a extremo.
6. Docker Compose, pruebas de integración y GitHub Actions.

La fase 6 incluye Compose, imágenes y un workflow de CI. La integración local
con broker y base de datos se comprobó con 12 lecturas; el workflow de GitHub
Actions queda pendiente de una ejecución remota.
