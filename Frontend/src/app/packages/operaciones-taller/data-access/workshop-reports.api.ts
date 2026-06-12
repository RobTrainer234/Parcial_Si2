import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';

import { buildApiUrl } from '../../../core/config/api.config';
import {
  DynamicReportRequest,
  DynamicReportResponse,
  StaticReportSummaryResponse,
  WorkshopReportResponse,
} from './workshop-reports.models';

@Injectable({ providedIn: 'root' })
export class WorkshopReportsApi {
  private readonly http = inject(HttpClient);

  listStaticReports() {
    return this.http.get<StaticReportSummaryResponse[]>(
      buildApiUrl('/workshop/reports/static'),
    );
  }

  getStaticReport(filters: {
    reportType: string;
    dateFrom?: string | null;
    dateTo?: string | null;
    status?: string | null;
    severity?: string | null;
    specialtyId?: number | null;
  }) {
    let params = new HttpParams();
    if (filters.dateFrom) {
      params = params.set('date_from', this.toStartOfDayIso(filters.dateFrom));
    }
    if (filters.dateTo) {
      params = params.set('date_to', this.toEndOfDayIso(filters.dateTo));
    }
    if (filters.status) {
      params = params.set('status', filters.status);
    }
    if (filters.severity) {
      params = params.set('severity', filters.severity);
    }
    if (filters.specialtyId !== null && filters.specialtyId !== undefined) {
      params = params.set('specialty_id', String(filters.specialtyId));
    }

    return this.http.get<WorkshopReportResponse>(
      buildApiUrl(`/workshop/reports/static/${filters.reportType}`),
      { params },
    );
  }

  createDynamicTextReport(payload: DynamicReportRequest) {
    const normalizedPayload: DynamicReportRequest = {
      ...payload,
      date_from: this.normalizeStartDate(payload.date_from),
      date_to: this.normalizeEndDate(payload.date_to),
    };
    return this.http.post<DynamicReportResponse>(
      buildApiUrl('/workshop/reports/dynamic/text'),
      normalizedPayload,
    );
  }

  createDynamicAudioReport(filters: {
    audioFile: File;
    dateFrom?: string | null;
    dateTo?: string | null;
    scope?: string | null;
  }) {
    const formData = new FormData();
    formData.append('audio_file', filters.audioFile);
    if (filters.dateFrom) {
      formData.append('date_from', this.toStartOfDayIso(filters.dateFrom));
    }
    if (filters.dateTo) {
      formData.append('date_to', this.toEndOfDayIso(filters.dateTo));
    }
    formData.append('scope', filters.scope || 'TALLER');

    return this.http.post<DynamicReportResponse>(
      buildApiUrl('/workshop/reports/dynamic/audio'),
      formData,
    );
  }

  private normalizeStartDate(value: string | null | undefined): string | null | undefined {
    if (!value) {
      return value;
    }
    return this.toStartOfDayIso(value);
  }

  private normalizeEndDate(value: string | null | undefined): string | null | undefined {
    if (!value) {
      return value;
    }
    return this.toEndOfDayIso(value);
  }

  private toStartOfDayIso(value: string): string {
    return this.isDateOnly(value) ? `${value}T00:00:00` : value;
  }

  private toEndOfDayIso(value: string): string {
    return this.isDateOnly(value) ? `${value}T23:59:59.999999` : value;
  }

  private isDateOnly(value: string): boolean {
    return /^\d{4}-\d{2}-\d{2}$/.test(value);
  }
}
