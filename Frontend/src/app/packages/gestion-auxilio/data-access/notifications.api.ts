import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { buildApiUrl } from '../../../core/config/api.config';
import { NotificationDetail, NotificationFilters, NotificationSummary } from './notifications.models';

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

  getNotificationDetail(notificationId: number): Observable<NotificationDetail> {
    assertPositiveInteger(notificationId, 'notificationId');
    return this.http.get<NotificationDetail>(buildApiUrl(`/notifications/${notificationId}`));
  }

  markAsRead(notificationId: number): Observable<void> {
    assertPositiveInteger(notificationId, 'notificationId');
    return this.http.patch<void>(buildApiUrl(`/notifications/${notificationId}/read`), {});
  }

  markAllAsRead(): Observable<void> {
    return this.http.patch<void>(buildApiUrl('/notifications/me/read-all'), {});
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
    if (status && status !== 'all') params = params.set('status', status);

    const type = trim(filters.type);
    if (type) params = params.set('type', type);

    const priority = trim(filters.priority);
    if (priority) params = params.set('priority', priority);

    const dateFrom = trim(filters.date_from);
    if (dateFrom) params = params.set('date_from', dateFrom);

    const dateTo = trim(filters.date_to);
    if (dateTo) params = params.set('date_to', dateTo);

    if (isPositiveInteger(filters.service_id)) params = params.set('service_id', filters.service_id);
    if (isPositiveInteger(filters.incident_id)) params = params.set('incident_id', filters.incident_id);
    if (isPositiveInteger(filters.request_id)) params = params.set('request_id', filters.request_id);

    return params;
  }
}
