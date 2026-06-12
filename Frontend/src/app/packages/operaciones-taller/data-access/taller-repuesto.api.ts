import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { buildApiUrl } from '../../../core/config/api.config';
import {
  TallerRepuestoCreateRequest,
  TallerRepuestoResponse,
  TallerRepuestoUpdateRequest,
} from './taller-repuesto.models';

@Injectable({ providedIn: 'root' })
export class TallerRepuestoApi {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = buildApiUrl('/workshop/spare-parts');

  list(onlyActive = false): Observable<TallerRepuestoResponse[]> {
    return this.http.get<TallerRepuestoResponse[]>(this.baseUrl, {
      params: { only_active: onlyActive },
    });
  }

  create(payload: TallerRepuestoCreateRequest): Observable<TallerRepuestoResponse> {
    return this.http.post<TallerRepuestoResponse>(this.baseUrl, payload);
  }

  update(
    id: number,
    payload: TallerRepuestoUpdateRequest,
  ): Observable<TallerRepuestoResponse> {
    return this.http.patch<TallerRepuestoResponse>(`${this.baseUrl}/${id}`, payload);
  }

  deactivate(id: number): Observable<TallerRepuestoResponse> {
    return this.http.patch<TallerRepuestoResponse>(
      `${this.baseUrl}/${id}/deactivate`,
      {},
    );
  }

  activate(id: number): Observable<TallerRepuestoResponse> {
    return this.http.patch<TallerRepuestoResponse>(
      `${this.baseUrl}/${id}/activate`,
      {},
    );
  }
}
