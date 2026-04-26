import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';

import { buildApiUrl } from '../../../core/config/api.config';
import { DashboardOverviewResponse } from './workshop-dashboard.models';

@Injectable({ providedIn: 'root' })
export class WorkshopDashboardApi {
  private readonly http = inject(HttpClient);

  getOverview() {
    return this.http.get<DashboardOverviewResponse>(
      buildApiUrl('/workshop/dashboard/overview'),
    );
  }
}
