import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';

import { buildApiUrl } from '../../../core/config/api.config';
import {
  WorkshopServiceHistoryDetail,
  WorkshopServiceHistoryFilters,
  WorkshopServiceHistorySummary,
} from './workshop-service-history.models';

function assertPositiveInteger(value: number, name: string): void {
  if (!Number.isInteger(value) || value <= 0) {
    throw new Error(`Invalid ${name}: must be a positive integer.`);
  }
}

@Injectable({ providedIn: 'root' })
export class WorkshopServiceHistoryApi {
  private readonly http = inject(HttpClient);

  listServices(filters?: WorkshopServiceHistoryFilters) {
    let params = new HttpParams();
    const normalizedEstado = (filters?.estado ?? '').trim();
    if (normalizedEstado) {
      params = params.set('estado', normalizedEstado);
    }
    const normalizedDesde = (filters?.desde ?? '').trim();
    if (normalizedDesde) {
      params = params.set('desde', normalizedDesde);
    }
    const normalizedHasta = (filters?.hasta ?? '').trim();
    if (normalizedHasta) {
      params = params.set('hasta', normalizedHasta);
    }
    if (
      typeof filters?.operario_id === 'number' &&
      Number.isInteger(filters.operario_id) &&
      filters.operario_id > 0
    ) {
      params = params.set('operario_id', filters.operario_id);
    }
    if (
      typeof filters?.limit === 'number' &&
      Number.isInteger(filters.limit) &&
      filters.limit > 0
    ) {
      params = params.set('limit', filters.limit);
    }
    if (
      typeof filters?.offset === 'number' &&
      Number.isInteger(filters.offset) &&
      filters.offset >= 0
    ) {
      params = params.set('offset', filters.offset);
    }

    return this.http.get<WorkshopServiceHistorySummary[]>(
      buildApiUrl('/workshop/services/history'),
      { params },
    );
  }

  getServiceDetail(serviceId: number) {
    assertPositiveInteger(serviceId, 'serviceId');
    return this.http.get<WorkshopServiceHistoryDetail>(
      buildApiUrl(`/workshop/services/${serviceId}/history-detail`),
    );
  }
}
