import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { buildApiUrl } from '../../../core/config/api.config';
import {
  AuditFilterOptions,
  AuditLogDetail,
  AuditLogFilters,
  AuditLogSummary,
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

  listAuditLogs(filters?: AuditLogFilters): Observable<AuditLogSummary[]> {
    const params = this.buildParams(filters);
    return this.http.get<AuditLogSummary[]>(buildApiUrl('/reputation/audit-logs'), {
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

    const entityType = trim(filters.entity_type);
    if (entityType) params = params.set('entity_type', entityType);

    if (isPositiveInteger(filters.service_id)) params = params.set('service_id', filters.service_id);
    if (isPositiveInteger(filters.incident_id)) params = params.set('incident_id', filters.incident_id);
    if (isPositiveInteger(filters.request_id)) params = params.set('request_id', filters.request_id);
    if (isPositiveInteger(filters.actor_id)) params = params.set('actor_id', filters.actor_id);
    if (isPositiveInteger(filters.user_id)) params = params.set('user_id', filters.user_id);

    return params;
  }
}
