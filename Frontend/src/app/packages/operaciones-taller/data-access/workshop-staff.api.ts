import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';

import { buildApiUrl } from '../../../core/config/api.config';
import {
  WorkshopStaffAvailabilityUpdateRequest,
  WorkshopStaffCreateRequest,
  WorkshopStaffSummary,
} from './workshop-staff.models';

@Injectable({ providedIn: 'root' })
export class WorkshopStaffApi {
  private readonly http = inject(HttpClient);

  listStaff() {
    return this.http.get<WorkshopStaffSummary[]>(buildApiUrl('/workshop/staff'));
  }

  createStaff(payload: WorkshopStaffCreateRequest) {
    return this.http.post<WorkshopStaffSummary>(buildApiUrl('/workshop/staff'), payload);
  }

  updateAvailability(
    operarioId: number,
    payload: WorkshopStaffAvailabilityUpdateRequest,
  ) {
    return this.http.patch<WorkshopStaffSummary>(
      buildApiUrl(`/workshop/staff/${operarioId}/availability`),
      payload,
    );
  }
}
