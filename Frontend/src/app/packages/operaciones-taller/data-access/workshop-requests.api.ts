import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';

import { buildApiUrl } from '../../../core/config/api.config';
import {
  WorkshopRequestDecisionRequest,
  WorkshopRequestDecisionResponse,
  WorkshopRequestDetailResponse,
  WorkshopRequestSummary,
} from './workshop-request.models';

function assertPositiveRequestId(requestId: number): void {
  if (!Number.isInteger(requestId) || requestId <= 0) {
    throw new Error('requestId must be a positive integer.');
  }
}

@Injectable({ providedIn: 'root' })
export class WorkshopRequestsApi {
  private readonly http = inject(HttpClient);

  listPendingRequests() {
    return this.http.get<WorkshopRequestSummary[]>(
      buildApiUrl('/workshop/requests/pending'),
    );
  }

  getRequestDetail(requestId: number) {
    assertPositiveRequestId(requestId);
    return this.http.get<WorkshopRequestDetailResponse>(
      buildApiUrl(`/workshop/requests/${requestId}`),
    );
  }

  decideRequest(
    requestId: number,
    payload: WorkshopRequestDecisionRequest,
  ) {
    assertPositiveRequestId(requestId);
    return this.http.post<WorkshopRequestDecisionResponse>(
      buildApiUrl(`/workshop/requests/${requestId}/decision`),
      payload,
    );
  }
}
