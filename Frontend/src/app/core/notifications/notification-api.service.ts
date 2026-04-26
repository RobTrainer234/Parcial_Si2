import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Subject } from 'rxjs';

import { buildApiUrl } from '../config/api.config';
import { UnreadCountResponse } from './notification.models';

@Injectable({ providedIn: 'root' })
export class NotificationApiService {
  private readonly http = inject(HttpClient);

  readonly refreshUnreadCount$ = new Subject<void>();

  getUnreadCount() {
    return this.http.get<UnreadCountResponse>(buildApiUrl('/notifications/me/unread-count'));
  }

  triggerUnreadCountRefresh() {
    this.refreshUnreadCount$.next();
  }
}
