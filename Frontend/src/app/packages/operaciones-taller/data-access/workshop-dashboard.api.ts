import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';

import { buildApiUrl } from '../../../core/config/api.config';
import {
  DashboardOverviewResponse,
  VoiceDashboardReportResponse,
} from './workshop-dashboard.models';

@Injectable({ providedIn: 'root' })
export class WorkshopDashboardApi {
  private readonly http = inject(HttpClient);

  getOverview() {
    return this.http.get<DashboardOverviewResponse>(
      buildApiUrl('/workshop/dashboard/overview'),
    );
  }

  createVoiceReport(audioFile: File) {
    const formData = new FormData();
    formData.append('audio', audioFile);
    formData.append('scope', 'TALLER');
    return this.http.post<VoiceDashboardReportResponse>(
      buildApiUrl('/workshop/dashboard/ai-reports/audio'),
      formData,
    );
  }
}
