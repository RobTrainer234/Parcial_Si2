import { Injectable, OnDestroy, inject, signal } from '@angular/core';
import { Subject } from 'rxjs';

import { AuthService } from '../auth/auth.service';
import { buildWebSocketUrl } from '../config/api.config';

export interface NotificationRealtimeEvent {
  event: string;
  transport: string;
  notification_id?: number;
  service_id?: number | null;
  request_id?: number | null;
  channel?: string;
  title?: string;
  message?: string;
  payload?: Record<string, unknown>;
  status?: string;
  provider?: string;
  created_at?: string;
  sent_at?: string | null;
  read_at?: string | null;
  type?: string;
  entity_type?: string;
  entity_id?: number | null;
  route_suggested?: string | null;
}

export type NotificationRealtimeConnectionState =
  | 'connected'
  | 'reconnecting'
  | 'disconnected';

@Injectable({ providedIn: 'root' })
export class NotificationRealtimeService implements OnDestroy {
  private readonly authService = inject(AuthService);
  private readonly eventsSubject = new Subject<NotificationRealtimeEvent>();
  private readonly stateSignal = signal<NotificationRealtimeConnectionState>('disconnected');

  readonly events$ = this.eventsSubject.asObservable();
  readonly connectionState = this.stateSignal.asReadonly();

  private socket: WebSocket | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private manualClose = false;
  private cursor = 0;

  connect(): void {
    const token = this.authService.getToken();
    if (!token) {
      this.disconnect();
      return;
    }

    const socketReady = this.socket?.readyState;
    if (socketReady === WebSocket.OPEN || socketReady === WebSocket.CONNECTING) {
      return;
    }

    this.manualClose = false;
    this.clearReconnectTimer();
    this.closeSocket();
    this.openSocket(token, false);
  }

  disconnect(): void {
    this.manualClose = true;
    this.clearReconnectTimer();
    this.closeSocket();
    this.stateSignal.set('disconnected');
  }

  ngOnDestroy(): void {
    this.disconnect();
  }

  private openSocket(token: string, isReconnect: boolean): void {
    const socket = new WebSocket(
      buildWebSocketUrl('/realtime/ws', { token, cursor: this.cursor }),
    );
    this.socket = socket;
    this.stateSignal.set(isReconnect ? 'reconnecting' : 'disconnected');

    socket.onopen = () => {
      if (this.socket !== socket) {
        socket.close();
        return;
      }
      this.stateSignal.set('connected');
    };

    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as NotificationRealtimeEvent;
        if (payload.event === 'notification.created' && payload.notification_id) {
          this.cursor = payload.notification_id;
        }
        this.eventsSubject.next(payload);
      } catch {
        // Ignorar mensajes mal formados
      }
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
      if (this.manualClose) {
        this.stateSignal.set('disconnected');
        return;
      }
      this.stateSignal.set('reconnecting');
      this.scheduleReconnect(token);
    };
  }

  private scheduleReconnect(token: string): void {
    if (this.reconnectTimer !== null) {
      return;
    }
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      if (this.authService.getToken()) {
        this.openSocket(token, true);
      } else {
        this.disconnect();
      }
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
