import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { map } from 'rxjs';

import { buildApiUrl } from '../../../core/config/api.config';

export interface ServiceTrackingStatus {
  service_id: number;
  service_state: string;
  incident_id: number;
  incident_latitud: number;
  incident_longitud: number;
  last_operario_latitud?: number | null;
  last_operario_longitud?: number | null;
  last_location_at?: string | null;
  has_live_location: boolean;
  location_stale: boolean;
  current_distance_meters?: number | null;
  eta_seconds?: number | null;
  eta_text?: string | null;
  route_distance_meters?: number | null;
  route_duration_seconds?: number | null;
  route_points?: number[][] | null;
  tracking_message: string;
}

export interface ServiceTrackingHistoryPoint {
  latitud: number;
  longitud: number;
  fecha_hora: string;
}

export interface ClientActiveServiceSummary {
  service_id: number;
  service_state: string;
  incident_id: number;
  incident_state: string;
  workshop_name: string | null;
  operario_name: string | null;
  detected_specialty: string | null;
  ai_summary: string | null;
  created_at: string | null;
  assigned_at: string | null;
}

export interface OperatorLocation {
  id_ubicacion: number;
  latitud: number;
  longitud: number;
  precision_metros?: number | null;
  velocidad_kmh?: number | null;
  fecha_hora: string;
}

export interface ServiceWithOperator {
  service_id: number;
  service_state: string;
  incident_id: number;
  incident_latitud: number;
  incident_longitud: number;
  workshop_name: string;
  operario_name?: string | null;
  last_operario_latitud?: number | null;
  last_operario_longitud?: number | null;
  last_location_at?: string | null;
  has_live_location: boolean;
  current_distance_meters?: number | null;
  eta_text?: string | null;
  detected_specialty?: string | null;
  assigned_at?: string | null;
}

@Injectable({ providedIn: 'root' })
export class WorkshopTrackingApi {
  private readonly http = inject(HttpClient);

  getTrackingStatus(serviceId: number) {
    return this.http.get<ServiceTrackingStatus>(
      buildApiUrl(`/tracking/services/${serviceId}/status`),
    );
  }

  getTrackingHistory(serviceId: number) {
    return this.http.get<ServiceTrackingHistoryPoint[]>(
      buildApiUrl(`/tracking/services/${serviceId}/history`),
    );
  }

  getActiveOperatorLocation(serviceId: number) {
    return this.http.get<OperatorLocation | null>(
      buildApiUrl(`/field/services/${serviceId}/navigation/status`),
    );
  }

  getActiveServicesForWorkshop() {
    return this.http.get<ClientActiveServiceSummary[]>(
      buildApiUrl(`/workshop/services/active`),
    );
  }

  getWorkshopActiveServicesWithTracking() {
    return this.http.get<ServiceWithOperator[]>(
      buildApiUrl(`/workshop/tracking/active`),
    );
  }
}
