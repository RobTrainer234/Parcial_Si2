import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { buildApiUrl } from '../../../core/config/api.config';
import {
  AuditFilterOptions,
  AuditLogDetail,
  AuditLogFilters,
  AuditLogPageResponse,
  ServiceTimelineItem,
} from './audit.models';

function assertPositiveInteger(value: number, name: string): void {
  if (!Number.isInteger(value) || value <= 0) {
    throw new Error(`Invalid ${name}: must be a positive integer.`);
  }
}

function isPositiveInteger(value: unknown): value is number {
  return typeof value === 'number' && Number.isInteger(value) && value > 0;
}

@Injectable({ providedIn: 'root' })
export class AuditApi {
  private readonly http = inject(HttpClient);

  listAuditLogs(filters?: AuditLogFilters): Observable<AuditLogPageResponse> {
    const params = this.buildParams(filters);
    return this.http.get<AuditLogPageResponse>(buildApiUrl('/reputation/audit-logs'), {
      params,
    });
  }

  getFilterOptions(): Observable<AuditFilterOptions> {
    return this.http.get<AuditFilterOptions>(
      buildApiUrl('/reputation/audit-logs/filter-options'),
    );
  }

  getAuditDetail(auditId: number): Observable<AuditLogDetail> {
    assertPositiveInteger(auditId, 'auditId');
    return this.http.get<AuditLogDetail>(
      buildApiUrl(`/reputation/audit-logs/${auditId}`),
    );
  }

  getServiceTimeline(serviceId: number): Observable<ServiceTimelineItem[]> {
    assertPositiveInteger(serviceId, 'serviceId');
    return this.http.get<ServiceTimelineItem[]>(
      buildApiUrl(`/reputation/services/${serviceId}/timeline`),
    );
  }

  exportCsv(filters?: AuditLogFilters): Observable<Blob> {
    const params = this.buildParams(filters);
    return this.http.get(buildApiUrl('/reputation/audit-logs/export.csv'), {
      params,
      responseType: 'blob',
    });
  }

  private buildParams(filters?: AuditLogFilters): HttpParams {
    let params = new HttpParams();
    if (!filters) {
      return params;
    }

    const trim = (val: string | null | undefined): string | null => {
      const trimmed = (val ?? '').trim();
      return trimmed.length > 0 ? trimmed : null;
    };

    const dateFrom = trim(filters.date_from);
    if (dateFrom) params = params.set('date_from', dateFrom);

    const dateTo = trim(filters.date_to);
    if (dateTo) params = params.set('date_to', dateTo);

    const action = trim(filters.action);
    if (action) params = params.set('action', action);

    const eventType = trim(filters.event_type);
    if (eventType) params = params.set('event_type', eventType);

    const mainEntity = trim(filters.main_entity);
    if (mainEntity) params = params.set('main_entity', mainEntity);

    if (isPositiveInteger(filters.service_id)) params = params.set('service_id', filters.service_id);
    if (isPositiveInteger(filters.incident_id)) params = params.set('incident_id', filters.incident_id);
    if (isPositiveInteger(filters.request_id)) params = params.set('request_id', filters.request_id);
    if (isPositiveInteger(filters.payment_id)) params = params.set('payment_id', filters.payment_id);
    if (isPositiveInteger(filters.actor_user_id)) params = params.set('actor_user_id', filters.actor_user_id);

    const search = trim(filters.search);
    if (search) params = params.set('search', search);
    if (isPositiveInteger(filters.limit)) params = params.set('limit', filters.limit);
    if (typeof filters.offset === 'number' && Number.isInteger(filters.offset) && filters.offset >= 0) {
      params = params.set('offset', filters.offset);
    }

    return params;
  }
}
