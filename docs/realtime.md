# Telemetría simulada en tiempo real

## Flujo

1. `gridwatch_simulator` publica JSON ficticio bajo
   `gridwatch/demo/measurements/<equipment_id>` cada dos segundos.
2. FastAPI se suscribe al broker MQTT, valida el tópico y el mensaje, guarda la
   medición en TimescaleDB y evalúa las reglas de alerta.
3. Tras confirmar la transacción, difunde la lectura por
   `/api/v1/ws/measurements`. Los clientes autenticados actualizan gráficos y
   alertas. La consulta HTTP cada 15 segundos sirve de respaldo.

El WebSocket exige el subprotocolo `gridwatch` y un JWT válido de un usuario
activo en el primer mensaje JSON: `{ "type": "auth", "token": "..." }`.
El token no aparece en la URL ni en las cabeceras del handshake. El servidor
confirma con `{ "type": "ready" }` antes de difundir lecturas. También comprueba
el `Origin` contra `CORS_ORIGINS`. El WebSocket es de solo lectura.

## Arranque local

Se necesita PostgreSQL con TimescaleDB y un broker MQTT local. La
[guía Docker/CI](devops.md) levanta ambos servicios con Compose; también puedes
usar un broker Mosquitto instalado localmente, escuchando **solo en
127.0.0.1:1883** para esta demostración. No uses este broker anónimo en una red
compartida.

Desde la raíz del proyecto, después de configurar `.env` y aplicar las
migraciones:

```powershell
Set-Location backend
.\.venv\Scripts\python -m pip install -e ".[dev]" -e ../simulator
.\.venv\Scripts\python -m app.cli seed-demo
.\.venv\Scripts\python -m app.cli create-admin --email admin@example.com --name "Admin GridWatch"
.\.venv\Scripts\python -m uvicorn app.main:app --reload
```

En otra terminal, desde `backend/`:

```powershell
.\.venv\Scripts\python -m gridwatch_simulator --dry-run
.\.venv\Scripts\python -m gridwatch_simulator
```

Desde `frontend/`, ejecuta `npm run dev` e inicia sesión con el administrador.
El comando `seed-demo` funciona solo con la tabla de instalaciones vacía y
rechaza `APP_ENV=production`. El modo "Vista demo local" sigue disponible sin
base de datos ni broker, pero sus números son estáticos.

## Contrato y límites

- Mensajes JSON de hasta 16 KiB, con `source=simulator`, tiempo con zona horaria
  y al menos una magnitud eléctrica válida. El UUID del tópico debe coincidir
  con `equipment_id`.
- Publicación QoS 1 y persistencia idempotente por equipo e instante.
- El backend no publica comandos MQTT ni implementa protocolos de control.
- La integración local con Mosquitto y TimescaleDB se comprobó en Docker:
  tres ciclos publicaron 12 lecturas ficticias y las 12 se guardaron en la
  tabla de mediciones. El simulador continuo se puede iniciar con el perfil
  `live` de Compose.
