import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';

import { buildApiUrl } from '../../../core/config/api.config';
import {
  WorkshopCatalogServiceCreateRequest,
  WorkshopCatalogServiceResponse,
  WorkshopCatalogServiceUpdateRequest,
} from './workshop-catalog.models';

@Injectable({ providedIn: 'root' })
export class WorkshopCatalogApi {
  private readonly http = inject(HttpClient);

  listCatalog(includeInactive = false) {
    let params = new HttpParams();
    if (includeInactive) {
      params = params.set('include_inactive', 'true');
    }

    return this.http.get<WorkshopCatalogServiceResponse[]>(
      buildApiUrl('/workshop/catalog'),
      { params },
    );
  }

  createCatalogService(payload: WorkshopCatalogServiceCreateRequest) {
    return this.http.post<WorkshopCatalogServiceResponse>(
      buildApiUrl('/workshop/catalog'),
      payload,
    );
  }

  updateCatalogService(
    catalogId: number,
    payload: WorkshopCatalogServiceUpdateRequest,
  ) {
    return this.http.put<WorkshopCatalogServiceResponse>(
      buildApiUrl(`/workshop/catalog/${catalogId}`),
      payload,
    );
  }

  deactivateCatalogService(catalogId: number) {
    return this.http.patch<WorkshopCatalogServiceResponse>(
      buildApiUrl(`/workshop/catalog/${catalogId}/deactivate`),
      {},
    );
  }

  activateCatalogService(catalogId: number) {
    return this.http.patch<WorkshopCatalogServiceResponse>(
      buildApiUrl(`/workshop/catalog/${catalogId}/activate`),
      {},
    );
  }
}
