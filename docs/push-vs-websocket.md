# Evidencia: Push vs WebSocket

## Diferencia funcional

| Canal | Cuando funciona | Uso en el proyecto |
|---|---|---|
| Push / FCM | App cerrada, suspendida o en segundo plano | Despierta/notifica al dispositivo sobre asignaciones, llegada, progreso y pagos |
| WebSocket | App abierta y conectada | Entrega inmediatamente las notificaciones persistidas y refresca la interfaz |
| Polling de respaldo | Si el WebSocket falla temporalmente | Actualiza cada dos minutos sin sustituir los canales principales |

## Flujo Push

1. La app obtiene el token FCM.
2. Registra el dispositivo mediante `POST /notifications/devices/register`.
3. El backend guarda una `Notificacion`.
4. `_auto_dispatch_notifications` envía el mensaje al proveedor Push.
5. Firebase entrega el mensaje aunque la app no tenga una conexión abierta con el backend.

## Flujo WebSocket

1. La app autenticada abre `WS /realtime/ws?token=<JWT>&cursor=<ultimo_id>`.
2. El backend valida el JWT y limita los eventos al usuario autenticado.
3. El canal permanece conectado mientras la app está abierta.
4. Cada nueva notificación se transmite como `notification.created`.
5. El cursor evita repetir eventos durante reconexiones.
6. La pantalla de notificaciones muestra `WebSocket conectado`.

## Demostración sugerida

1. Iniciar sesión en móvil y abrir **Notificaciones**.
2. Verificar el texto `WebSocket conectado`.
3. Desde el taller, aceptar una solicitud o asignar un operario.
4. Observar la actualización instantánea sin pulsar **Actualizar**.
5. Cerrar o suspender la app y generar otro evento.
6. Observar la notificación Push del sistema operativo.

## Verificación estructural

Ejecutar:

```powershell
cd Backend
.\.venv\Scripts\python.exe scripts\verify_push_websocket.py
```
