import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';

import { buildApiUrl } from '../../../core/config/api.config';
import {
  AssignOperarioRequest,
  AssignOperarioResponse,
  OperarioCandidateSummary,
  WaitingAssignmentServiceSummary,
} from './workshop-assignment.models';

function assertPositiveInteger(value: number, name: string): void {
  if (!Number.isInteger(value) || value <= 0) {
    throw new Error(`${name} must be a positive integer.`);
  }
}

@Injectable({ providedIn: 'root' })
export class WorkshopAssignmentApi {
  private readonly http = inject(HttpClient);

  listWaitingAssignmentServices() {
    return this.http.get<WaitingAssignmentServiceSummary[]>(
      buildApiUrl('/workshop/services/waiting-assignment'),
    );
  }

  listOperarioCandidates(serviceId: number) {
    assertPositiveInteger(serviceId, 'serviceId');
    return this.http.get<OperarioCandidateSummary[]>(
      buildApiUrl(`/workshop/services/${serviceId}/operario-candidates`),
    );
  }

  assignOperario(serviceId: number, operarioId: number) {
    assertPositiveInteger(serviceId, 'serviceId');
    assertPositiveInteger(operarioId, 'operarioId');

    const payload: AssignOperarioRequest = {
      id_persona_operario: operarioId,
    };

    return this.http.post<AssignOperarioResponse>(
      buildApiUrl(`/workshop/services/${serviceId}/assign-operario`),
      payload,
    );
  }
}
