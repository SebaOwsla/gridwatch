# API inicial

Base: `/api/v1`. La especificación OpenAPI se sirve en `/docs` cuando la API
está en ejecución. Los endpoints de datos usan PostgreSQL/TimescaleDB y exigen
haber aplicado la migración inicial.

| Método y ruta | Acceso | Uso |
| --- | --- | --- |
| `GET /health/live` | Público | Comprueba que la API responde, sin consultar la base. |
| `GET /health/ready` | Público | Comprueba la conexión con la base. |
| `POST /auth/login` | Público | Recibe formulario OAuth2 con `username` (correo) y `password`; devuelve JWT. |
| `GET /auth/me` | Autenticado | Devuelve el usuario activo. |
| `GET /auth/users` | Administrador | Lista usuarios con `limit` y `offset`. |
| `POST /auth/users` | Administrador | Crea usuarios con rol `admin`, `operator` o `viewer`. |
| `GET /installations` | Autenticado | Lista instalaciones con `limit` y `offset`. |
| `GET /installations/{id}` | Autenticado | Consulta una instalación. |
| `POST /installations` | Administrador u operador | Crea una instalación. |
| `PUT /installations/{id}` | Administrador u operador | Reemplaza los campos editables. |
| `GET /equipment` | Autenticado | Lista equipos; filtro opcional `installation_id`. |
| `GET /equipment/{id}` | Autenticado | Consulta un equipo. |
| `POST /equipment` | Administrador u operador | Crea un equipo en una instalación. |
| `PUT /equipment/{id}` | Administrador u operador | Actualiza el equipo sin cambiarlo de instalación. |
| `GET /measurements` | Autenticado | Historial de un equipo entre `start` y `end` (UTC o con zona). |
| `GET /measurements/trend` | Autenticado | Promedios por intervalos y estadísticas completas de un equipo durante 24 o 168 horas. |
| `GET /measurements/latest/{equipment_id}` | Autenticado | Última muestra del equipo. |
| `GET /alert-rules` y `GET /alert-rules/{id}` | Autenticado | Consulta reglas; la lista admite `equipment_id`. |
| `POST /alert-rules` | Administrador u operador | Define umbrales de una magnitud. |
| `PUT /alert-rules/{id}` | Administrador u operador | Cambia umbrales o activa/desactiva la regla. |
| `GET /alert-events` | Autenticado | Lista eventos; filtros `equipment_id` y `status`. |
| `POST /alert-events/{id}/acknowledge` | Administrador u operador | Reconoce una alerta abierta. |
| `GET /reports/measurements.xlsx` | Autenticado | Exporta las muestras de un equipo a Excel. |
| `GET /reports/summary.xlsx` | Autenticado | Exporta estadísticas y promedios por intervalos a Excel. |
| `GET /reports/measurements.pdf` | Autenticado | Exporta un resumen estadístico del periodo completo en PDF. |
| `GET /audit-events` | Administrador | Consulta acciones registradas. |

La API usa `Authorization: Bearer <token>`. Los permisos se verifican en cada
solicitud contra el rol actual en la base. Los tokens no incorporan el rol para
que un cambio de permisos tenga efecto sin esperar a que venza el JWT.

Los códigos relevantes son 401 para credenciales inválidas o usuario inactivo,
403 para permisos insuficientes, 404 para recursos ausentes, 409 para conflictos
de integridad, 422 para errores de validación y 503 si la base no responde.
Las operaciones de escritura registran un evento de auditoría en la misma
transacción. No hay borrado físico de instalaciones o equipos en esta API;
se utiliza `is_active` o el estado del equipo para preservar el historial.

## Historial, alertas y exportación

El historial y los reportes requieren `equipment_id`, `start` y `end`. El
intervalo es **[start, end)**, con fechas que incluyan zona horaria, y puede
abarcar hasta 31 días. El historial devuelve hasta 1000 filas por página,
ordenadas desde la más reciente. El Excel detallado acepta hasta 5000 filas;
si el intervalo contiene más, responde 422. El PDF y el Excel resumido
calculan estadísticas sobre todas las filas del periodo. El Excel resumido
agrupa las muestras válidas cada 5 minutos hasta un día, cada hora hasta
siete días y cada seis horas para periodos más largos.

La tendencia requiere `equipment_id` y admite `hours=24` o `hours=168`.
TimescaleDB agrupa las muestras válidas con `time_bucket` en intervalos de
cinco minutos o una hora, respectivamente. El resultado incluye como máximo
350 intervalos y estadísticas exactas de todo el periodo para cada magnitud;
no depende de la página de 1000 filas del historial.

El Excel detallado incluye cada muestra, con la fecha en UTC y sin zona en
la celda porque Excel no conserva zonas horarias. El Excel resumido tiene
hojas de estadísticas e intervalos. El PDF resume mínimo, promedio y máximo
de las muestras válidas. Los archivos indican que los datos son simulados y
las exportaciones quedan registradas en auditoría.

La ingesta no se expone por HTTP. `app.modules.telemetry.ingest_measurement`
recibe mensajes del consumidor MQTT. Acepta solo `source=simulator`,
rechaza métricas no finitas, ignora muestras repetidas para el mismo equipo e
instante y evita que muestras atrasadas cambien el estado de las alertas.
Una regla abre un evento al salir de rango y lo resuelve cuando vuelve al rango;
una muestra con calidad `invalid` no cambia las alertas. La segunda migración
impide dos eventos activos para una misma regla.

El primer administrador se crea con `python -m app.cli create-admin`, después
de migrar la base. El comando pide la contraseña de forma interactiva y rechaza
ejecutarse si ya hay usuarios. Las cuentas posteriores se crean con
`POST /auth/users` por un administrador autenticado.

La firma JWT usa un secreto de al menos 32 caracteres almacenado en `.env` o en
el entorno. Las contraseñas se almacenan con Argon2. Esta implementación sigue
el patrón de [seguridad JWT de FastAPI](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/).

La API valida la cabecera `Host` con `TRUSTED_HOSTS`, restringe orígenes
CORS y añade cabeceras de seguridad a las respuestas. El WebSocket autentica
con el primer mensaje del canal; consulta [telemetría en tiempo real](realtime.md)
y [revisión de seguridad](security-review.md).
