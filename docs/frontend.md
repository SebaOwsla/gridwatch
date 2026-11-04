# Interfaz web

El frontend usa React, TypeScript, Tailwind CSS y Recharts. La dirección visual
prioriza azul pastel, superficies blancas, bordes suaves y jerarquía clara para
leer magnitudes eléctricas sin distracciones.

## Vistas

| Ruta | Contenido |
| --- | --- |
| `/login` | Acceso JWT o vista demo local. |
| `/dashboard` | Indicadores, voltajes por fase, alertas y estado de instalaciones. |
| `/installations` | Inventario de sitios y equipos; creación y cambios de estado según rol. |
| `/history` | Gráfico interactivo, filtros por equipo, magnitud y periodo, y tabla de lecturas. |
| `/alerts` | Eventos, filtros, reconocimiento y creación de reglas según rol. |
| `/reports` | PDF completo, Excel resumido o Excel detallado según el periodo. |
| `/admin` | Usuarios y auditoría, solo para administrador. |

La vista demo muestra **datos de muestra generados en el navegador** y es de
solo lectura. No inicia sesión real, no escribe en la base y deshabilita las
descargas que requieren la API. El indicador superior la identifica como
"Vista demo local". En modo autenticado, el frontend consulta la API cada
15 segundos y recibe muestras nuevas por WebSocket. Si el canal en vivo se
interrumpe, las consultas periódicas siguen actualizando las vistas. El estado
de la conexión aparece en el encabezado.

Los gráficos de 24 horas y 7 días consultan promedios por intervalos a
TimescaleDB: cinco minutos para el primer periodo y una hora para el segundo.
Mínimo, promedio y máximo se calculan sobre todas las muestras válidas del
periodo. La tabla de lecturas recientes conserva un límite de 1000 filas por
consulta y muestra las 20 más nuevas.

La vista de reportes ofrece PDF y Excel resumido para intervalos de hasta
31 días. El Excel detallado conserva el máximo de 5000 lecturas e indica al
usuario que acorte el periodo o use el resumen si lo supera.

## Desarrollo local

Desde `frontend/`:

```powershell
npm install
npm run dev
```

Vite sirve el frontend en `http://127.0.0.1:5173` y redirige `/api` a
`http://127.0.0.1:8000` durante el desarrollo. Copia `.env.example` a `.env`
solo si necesitas cambiar `VITE_API_BASE_URL`. Las variables `VITE_` se
incluyen en el código del navegador y no deben contener secretos.

Para verificar el acceso demo ejecuta `npm run test`; para revisar tipos y
generar la versión de producción, ejecuta `npm run build`. El modo demo funciona sin backend; iniciar sesión y usar
datos persistidos exige FastAPI y PostgreSQL/TimescaleDB en funcionamiento.
