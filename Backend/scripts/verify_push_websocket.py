from __future__ import annotations

import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.main import create_app


def main() -> None:
    app = create_app()
    websocket_routes = {route.path for route in app.routes if route.__class__.__name__ == "APIWebSocketRoute"}
    http_routes = {route.path for route in app.routes}

    assert "/realtime/ws" in websocket_routes
    assert "/notifications/devices/register" in http_routes
    assert "/notifications/me" in http_routes

    print("PUSH_VS_WEBSOCKET_STRUCTURAL_CHECK: OK")
    print("Push: FCM device registration and background delivery endpoints mounted.")
    print("WebSocket: authenticated /realtime/ws live channel mounted.")
    print("Difference: Push wakes/notifies background devices; WebSocket streams while connected.")


if __name__ == "__main__":
    main()
