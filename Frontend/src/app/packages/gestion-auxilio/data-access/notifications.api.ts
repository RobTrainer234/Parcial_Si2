import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { buildApiUrl } from '../../../core/config/api.config';
import { NotificationFilters, NotificationSummary } from './notifications.models';

function isPositiveInteger(value: unknown): value is number {
  return typeof value === 'number' && Number.isInteger(value) && value > 0;
}

function assertPositiveInteger(value: number, name: string): void {
  if (!isPositiveInteger(value)) {
    throw new Error(`Invalid ${name}: must be a positive integer.`);
  }
}

@Injectable({ providedIn: 'root' })
export class NotificationsPageApi {
  private readonly http = inject(HttpClient);

  listNotifications(filters?: NotificationFilters): Observable<NotificationSummary[]> {
    const params = this.buildParams(filters);
    return this.http.get<NotificationSummary[]>(buildApiUrl('/notifications/me'), { params });
  }

  markAsRead(notificationId: number): Observable<void> {
    assertPositiveInteger(notificationId, 'notificationId');
    return this.http.post<void>(buildApiUrl(`/notifications/${notificationId}/read`), {});
  }

  private buildParams(filters?: NotificationFilters): HttpParams {
    let params = new HttpParams();
    if (!filters) {
      return params;
    }

    const trim = (val: string | null | undefined): string | null => {
      const trimmed = (val ?? '').trim();
      return trimmed.length > 0 ? trimmed : null;
    };

    const status = trim(filters.status);
    if (status === 'unread') params = params.set('only_unread', 'true');

    return params;
  }
}
