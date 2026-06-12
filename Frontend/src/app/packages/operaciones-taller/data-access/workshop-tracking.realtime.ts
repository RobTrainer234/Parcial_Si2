import { Injectable, inject, signal } from '@angular/core';
import { Subject } from 'rxjs';

import { AuthService } from '../../../core/auth/auth.service';
import { buildWebSocketUrl } from '../../../core/config/api.config';

export type WorkshopTrackingConnectionState =
  | 'connected'
  | 'reconnecting'
  | 'disconnected';

export interface WorkshopTrackingRealtimeEvent {
  type: string;
  service_id: number;
  incident_id: number | null;
  workshop_id: number | null;
  service_state: string | null;
  timestamp: string;
  data: {
    incident_latitud?: number | null;
    incident_longitud?: number | null;
    operario_latitud?: number | null;
    operario_longitud?: number | null;
    route_points?: number[][] | null;
    route_distance_meters?: number | null;
    route_duration_seconds?: number | null;
    last_location_at?: string | null;
    current_distance_meters?: number | null;
    eta_seconds?: number | null;
    eta_text?: string | null;
    has_live_location?: boolean;
    location_stale?: boolean;
    workshop_name?: string | null;
    operario_name?: string | null;
    detected_specialty?: string | null;
    assigned_at?: string | null;
  };
}

@Injectable({ providedIn: 'root' })
export class WorkshopTrackingRealtimeService {
  private readonly authService = inject(AuthService);
  private readonly eventsSubject = new Subject<WorkshopTrackingRealtimeEvent>();

  readonly events$ = this.eventsSubject.asObservable();
  readonly connectionState = signal<WorkshopTrackingConnectionState>('disconnected');

  private socket: WebSocket | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private manualClose = false;
  private currentWorkshopId: number | null = null;

  connect(workshopId: number): void {
    const token = this.authService.getToken();
    if (!token) {
      this.disconnect();
      return;
    }

    const socketReady = this.socket?.readyState;
    if (
      this.currentWorkshopId === workshopId &&
      (socketReady === WebSocket.OPEN || socketReady === WebSocket.CONNECTING)
    ) {
      return;
    }

    this.currentWorkshopId = workshopId;
    this.manualClose = false;
    this.clearReconnectTimer();
    this.closeSocket();
    this.openSocket(workshopId, token, false);
  }

  disconnect(): void {
    this.manualClose = true;
    this.currentWorkshopId = null;
    this.clearReconnectTimer();
    this.closeSocket();
    this.connectionState.set('disconnected');
  }

  private openSocket(workshopId: number, token: string, isReconnect: boolean): void {
    const socket = new WebSocket(
      buildWebSocketUrl(`/ws/workshops/${workshopId}/tracking`, { token }),
    );
    this.socket = socket;
    this.connectionState.set(isReconnect ? 'reconnecting' : 'disconnected');

    socket.onopen = () => {
      if (this.socket !== socket) {
        socket.close();
        return;
      }
      this.connectionState.set('connected');
    };

    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as WorkshopTrackingRealtimeEvent;
        this.eventsSubject.next(payload);
      } catch {}
    };

    socket.onerror = () => {
      if (this.socket === socket) {
        socket.close();
      }
    };

    socket.onclose = () => {
      if (this.socket === socket) {
        this.socket = null;
      }
      if (this.manualClose || this.currentWorkshopId === null) {
        this.connectionState.set('disconnected');
        return;
      }
      this.connectionState.set('reconnecting');
      this.scheduleReconnect();
    };
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer !== null || this.currentWorkshopId === null) {
      return;
    }
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      const token = this.authService.getToken();
      if (!token || this.currentWorkshopId === null) {
        this.disconnect();
        return;
      }
      this.openSocket(this.currentWorkshopId, token, true);
    }, 3000);
  }

  private clearReconnectTimer(): void {
    if (this.reconnectTimer !== null) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  private closeSocket(): void {
    const socket = this.socket;
    this.socket = null;
    if (socket && socket.readyState !== WebSocket.CLOSED) {
      socket.close();
    }
  }
}
