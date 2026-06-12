import { CommonModule } from '@angular/common';
import {
  Component,
  DestroyRef,
  OnDestroy,
  OnInit,
  computed,
  effect,
  inject,
  signal,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import * as L from 'leaflet';
import { interval, switchMap } from 'rxjs';

import { AuthService } from '../../../core/auth/auth.service';
import { WorkshopSelectionService } from '../../../core/auth/workshop-selection.service';
import { AppCardComponent } from '../../../shared/components/app-card.component';
import { EmptyStateComponent } from '../../../shared/components/empty-state.component';
import { ErrorStateComponent } from '../../../shared/components/error-state.component';
import { LoadingStateComponent } from '../../../shared/components/loading-state.component';
import { PageHeaderComponent } from '../../../shared/components/page-header.component';
import { StatusBadgeComponent } from '../../../shared/components/status-badge.component';
import {
  ServiceTrackingStatus,
  ServiceWithOperator,
  WorkshopTrackingApi,
} from '../data-access/workshop-tracking.api';
import {
  WorkshopTrackingRealtimeEvent,
  WorkshopTrackingRealtimeService,
} from '../data-access/workshop-tracking.realtime';

interface ServiceItem {
  serviceId: number;
  status: ServiceTrackingStatus | null;
  expanded: boolean;
  loading: boolean;
  error: string | null;
}

@Component({
  selector: 'app-service-tracking-page',
  standalone: true,
  imports: [
    CommonModule,
    PageHeaderComponent,
    AppCardComponent,
    StatusBadgeComponent,
    LoadingStateComponent,
    EmptyStateComponent,
    ErrorStateComponent,
  ],
  template: `
    <div class="page">
      <app-page-header
        eyebrow="Monitoreo en vivo"
        title="Tracking de servicios"
        subtitle="Visualiza en tiempo real la ubicacion de los operarios y el estado de los servicios activos."
      >
        <button
          page-actions
          type="button"
          class="app-button app-button--secondary"
          (click)="reload()"
          [disabled]="loading()"
        >
          {{ loading() ? 'Actualizando...' : 'Actualizar' }}
        </button>
      </app-page-header>

      <p class="tracking-connection">{{ realtimeConnectionLabel() }}</p>

      @if (loading() && services().length === 0) {
        <app-loading-state
          title="Cargando servicios"
          message="Consultando servicios activos con tracking."
        />
      } @else if (error()) {
        <app-error-state [message]="error() ?? ''">
          <button error-actions type="button" class="app-button" (click)="reload()">
            Reintentar
          </button>
        </app-error-state>
      } @else {
        <div class="tracking-layout">
          <div class="tracking-map" #mapContainer></div>

          <div class="tracking-list">
            @if (services().length === 0) {
              <app-empty-state
                title="Sin servicios activos"
                message="No hay servicios en curso con tracking disponible."
              />
            } @else {
              @for (svc of services(); track svc.serviceId) {
                <app-card class="tracking-card">
                  <div class="tracking-card__header" (click)="toggleExpand(svc.serviceId)">
                    <div class="tracking-card__info">
                      <strong>#{{ svc.serviceId }}</strong>
                      <app-status-badge [label]="svc.status?.service_state ?? 'UNKNOWN'" />
                    </div>
                    <span class="tracking-card__arrow">
                      {{ svc.expanded ? '▼' : '▶' }}
                    </span>
                  </div>

                  @if (svc.expanded) {
                    <div class="tracking-card__body">
                      @if (svc.loading) {
                        <app-loading-state
                          title="Cargando..."
                          message="Obteniendo ubicacion del operario."
                        />
                      } @else if (svc.error; as err) {
                        <p class="tracking-card__error">{{ err }}</p>
                      } @else if (svc.status; as st) {
                        <div class="tracking-card__detail">
                          <p><strong>Incidente:</strong> #{{ st.incident_id }}</p>
                          @if (st.last_operario_latitud != null) {
                            <p>
                              <strong>Operario:</strong>
                              {{ st.last_operario_latitud.toFixed(5) }},
                              {{ st.last_operario_longitud?.toFixed(5) }}
                            </p>
                          } @else {
                            <p><strong>Operario:</strong> Sin ubicacion aun</p>
                          }
                          @if (st.last_location_at; as date) {
                            <p><strong>Ultima actualizacion:</strong> {{ date | date:'short' }}</p>
                          }
                          @if (st.current_distance_meters != null) {
                            <p>
                              <strong>Distancia:</strong>
                              {{ (st.current_distance_meters! / 1000).toFixed(2) }} km
                            </p>
                          }
                          @if (st.eta_text) {
                            <p><strong>ETA:</strong> {{ st.eta_text }}</p>
                          }
                          @if (st.has_live_location) {
                            <span class="tracking-card__live">● EN VIVO</span>
                          } @else if (st.location_stale) {
                            <span class="tracking-card__stale">● DESACTUALIZADO</span>
                          }
                        </div>
                      }
                    </div>
                  }
                </app-card>
              }
            }
          </div>
        </div>
      }
    </div>
  `,
  styles: [
    `
      .tracking-connection {
        margin: 0 0 var(--space-4);
        color: var(--color-text-muted);
        font-size: 0.9rem;
      }

      .tracking-layout {
        display: flex;
        flex-direction: column;
        gap: var(--space-6);
      }

      .tracking-map {
        height: 400px;
        border-radius: var(--radius-lg);
        border: 1px solid var(--color-border);
        overflow: hidden;
      }

      .tracking-list {
        display: flex;
        flex-direction: column;
        gap: var(--space-3);
      }

      .tracking-card__header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        cursor: pointer;
        padding: var(--space-3) 0;
      }

      .tracking-card__info {
        display: flex;
        align-items: center;
        gap: var(--space-3);
      }

      .tracking-card__arrow {
        font-size: 0.75rem;
        color: var(--color-text-muted);
      }

      .tracking-card__body {
        padding-top: var(--space-3);
        border-top: 1px solid var(--color-border);
      }

      .tracking-card__detail {
        display: flex;
        flex-direction: column;
        gap: var(--space-2);
        font-size: 0.85rem;
      }

      .tracking-card__detail p {
        margin: 0;
      }

      .tracking-card__error {
        color: var(--color-danger);
        font-size: 0.85rem;
        margin: 0;
      }

      .tracking-card__live {
        display: inline-block;
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #16a34a;
        animation: pulse-live 1.5s ease-in-out infinite;
      }

      .tracking-card__stale {
        display: inline-block;
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #d97706;
      }

      @keyframes pulse-live {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.4; }
      }
    `,
  ],
})
export class ServiceTrackingPage implements OnInit, OnDestroy {
  private readonly api = inject(WorkshopTrackingApi);
  private readonly authService = inject(AuthService);
  private readonly workshopSelection = inject(WorkshopSelectionService);
  private readonly realtime = inject(WorkshopTrackingRealtimeService);
  private readonly destroyRef = inject(DestroyRef);

  protected readonly loading = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly services = signal<ServiceItem[]>([]);
  protected readonly realtimeState = this.realtime.connectionState;
  protected readonly realtimeConnectionLabel = computed(() => {
    switch (this.realtimeState()) {
      case 'connected':
        return 'Conectado en tiempo real';
      case 'reconnecting':
        return 'Reconectando';
      default:
        return 'Sin conexion en tiempo real';
    }
  });

  private map: L.Map | null = null;
  private readonly markers = new Map<number, { operario: L.Marker; incidente: L.Marker }>();
  private readonly polylines = new Map<number, L.Polyline>();
  private readonly incidentIcon = L.divIcon({
    className: '',
    html: '<div style="background:#dc2626;color:#fff;width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:16px;box-shadow:0 2px 6px rgba(0,0,0,0.3);">!</div>',
    iconSize: [32, 32],
    iconAnchor: [16, 16],
  });
  private readonly operarioIcon = L.divIcon({
    className: '',
    html: '<div style="background:#16a34a;color:#fff;width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:16px;box-shadow:0 2px 6px rgba(0,0,0,0.3);animation:pulse-live 2s ease-in-out infinite;">O</div>',
    iconSize: [32, 32],
    iconAnchor: [16, 16],
  });

  constructor() {
    effect(() => {
      const workshopId = this.resolveRealtimeWorkshopId();
      if (workshopId == null) {
        this.realtime.disconnect();
        return;
      }
      this.realtime.connect(workshopId);
    });
  }

  ngOnInit(): void {
    this.reload();
    this.realtime.events$
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((event) => this.applyRealtimeEvent(event));
    interval(10000)
      .pipe(
        switchMap(() => this.api.getWorkshopActiveServicesWithTracking()),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (data) => this.updateFromPolling(data),
        error: () => {},
      });
  }

  ngAfterViewInit(): void {
    setTimeout(() => this.initMap(), 100);
  }

  ngOnDestroy(): void {
    this.realtime.disconnect();
    this.map?.remove();
  }

  reload(): void {
    this.loading.set(true);
    this.error.set(null);
    this.api
      .getWorkshopActiveServicesWithTracking()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (data) => {
          this.updateFromPolling(data);
          this.loading.set(false);
        },
        error: (err) => {
          this.error.set(err?.message ?? 'Error al cargar servicios.');
          this.loading.set(false);
        },
      });
  }

  toggleExpand(serviceId: number): void {
    this.services.update((list) =>
      list.map((item) =>
        item.serviceId === serviceId
          ? { ...item, expanded: !item.expanded }
          : item,
      ),
    );
  }

  private resolveRealtimeWorkshopId(): number | null {
    if (this.authService.isGerente()) {
      return this.workshopSelection.selectedWorkshopId();
    }
    return this.authService.currentUser()?.actor_context?.taller_id ?? null;
  }

  private updateFromPolling(data: ServiceWithOperator[]): void {
    this.services.set(
      data.map((item) => ({
        serviceId: item.service_id,
        status: this.toStatusFromWorkshopRow(item),
        expanded: false,
        loading: false,
        error: null,
      })),
    );
    const visibleIds = new Set(data.map((item) => item.service_id));
    this.markers.forEach((_, serviceId) => {
      if (!visibleIds.has(serviceId)) {
        this.removeServiceFromMap(serviceId);
      }
    });
    data.forEach((item) => this.updateMapMarker(item.service_id, this.toStatusFromWorkshopRow(item)));
  }

  private applyRealtimeEvent(event: WorkshopTrackingRealtimeEvent): void {
    const nextState = event.service_state ?? '';
    if (!this.isTrackingState(nextState)) {
      this.services.update((list) => list.filter((item) => item.serviceId !== event.service_id));
      this.removeServiceFromMap(event.service_id);
      return;
    }

    const nextStatus: ServiceTrackingStatus = {
      service_id: event.service_id,
      service_state: nextState,
      incident_id: event.incident_id ?? 0,
      incident_latitud: Number(event.data.incident_latitud ?? 0),
      incident_longitud: Number(event.data.incident_longitud ?? 0),
      last_operario_latitud: event.data.operario_latitud ?? null,
      last_operario_longitud: event.data.operario_longitud ?? null,
      last_location_at: event.data.last_location_at ?? null,
      has_live_location: event.data.has_live_location ?? false,
      location_stale: event.data.location_stale ?? false,
      current_distance_meters: event.data.current_distance_meters ?? null,
      eta_seconds: event.data.eta_seconds ?? null,
      eta_text: event.data.eta_text ?? null,
      route_distance_meters: event.data.route_distance_meters ?? null,
      route_duration_seconds: event.data.route_duration_seconds ?? null,
      route_points: event.data.route_points ?? null,
      tracking_message: '',
    };

    this.services.update((list) => {
      const existing = list.find((item) => item.serviceId === event.service_id);
      if (!existing) {
        return [
          {
            serviceId: event.service_id,
            status: nextStatus,
            expanded: false,
            loading: false,
            error: null,
          },
          ...list,
        ];
      }
      return list.map((item) =>
        item.serviceId === event.service_id
          ? { ...item, status: nextStatus, loading: false, error: null }
          : item,
      );
    });
    this.updateMapMarker(event.service_id, nextStatus);
  }

  private isTrackingState(state: string): boolean {
    return ['ASIGNADO', 'EN_CAMINO', 'EN_SITIO', 'EN_DIAGNOSTICO_FISICO'].includes(state);
  }

  private toStatusFromWorkshopRow(item: ServiceWithOperator): ServiceTrackingStatus {
    return {
      service_id: item.service_id,
      service_state: item.service_state,
      incident_id: item.incident_id,
      incident_latitud: item.incident_latitud,
      incident_longitud: item.incident_longitud,
      last_operario_latitud: item.last_operario_latitud,
      last_operario_longitud: item.last_operario_longitud,
      last_location_at: item.last_location_at ?? null,
      has_live_location: item.has_live_location,
      location_stale: !item.has_live_location && item.last_location_at != null,
      current_distance_meters: item.current_distance_meters ?? null,
      eta_text: item.eta_text ?? null,
      tracking_message: '',
    };
  }

  private initMap(): void {
    const element = document.querySelector('.tracking-map') as HTMLElement | null;
    if (!element) {
      return;
    }
    this.map = L.map(element, {
      center: [-16.5, -68.15],
      zoom: 13,
      zoomControl: true,
    });
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '© OpenStreetMap contributors',
    }).addTo(this.map);
    setTimeout(() => this.map?.invalidateSize(), 200);
  }

  private updateMapMarker(serviceId: number, status: ServiceTrackingStatus): void {
    if (!this.map) {
      return;
    }

    const incidentLatLng: L.LatLngExpression = [
      status.incident_latitud,
      status.incident_longitud,
    ];
    const hasOperario =
      status.last_operario_latitud != null &&
      status.last_operario_longitud != null;
    const operarioLatLng: L.LatLngExpression | null = hasOperario
      ? [status.last_operario_latitud!, status.last_operario_longitud!]
      : null;

    let existing = this.markers.get(serviceId);
    if (!existing) {
      const operarioMarker = L.marker(operarioLatLng ?? incidentLatLng, {
        icon: this.operarioIcon,
      }).addTo(this.map);
      const incidenteMarker = L.marker(incidentLatLng, {
        icon: this.incidentIcon,
      }).addTo(this.map);
      operarioMarker.bindPopup(`Servicio #${serviceId} - Operario`);
      incidenteMarker.bindPopup(`Servicio #${serviceId} - Incidente #${status.incident_id}`);

      const polyline = L.polyline(
        this.resolvePolylinePoints(status, operarioLatLng, incidentLatLng),
        { color: '#2563eb', weight: 3, opacity: 0.6, dashArray: '8 4' },
      ).addTo(this.map);

      existing = { operario: operarioMarker, incidente: incidenteMarker };
      this.markers.set(serviceId, existing);
      this.polylines.set(serviceId, polyline);
    } else {
      if (operarioLatLng) {
        existing.operario.setLatLng(operarioLatLng);
      }
      existing.incidente.setLatLng(incidentLatLng);
      const polyline = this.polylines.get(serviceId);
      if (polyline) {
        polyline.setLatLngs(this.resolvePolylinePoints(status, operarioLatLng, incidentLatLng));
      }
    }

    const allBounds = L.latLngBounds([]);
    this.markers.forEach((markerSet) => {
      allBounds.extend(markerSet.incidente.getLatLng());
      allBounds.extend(markerSet.operario.getLatLng());
    });
    if (allBounds.isValid()) {
      this.map.fitBounds(allBounds, { padding: [50, 50] });
    }
  }

  private resolvePolylinePoints(
    status: ServiceTrackingStatus,
    operarioLatLng: L.LatLngExpression | null,
    incidentLatLng: L.LatLngExpression,
  ): L.LatLngExpression[] {
    const routePoints = status.route_points
      ?.filter((point) => Array.isArray(point) && point.length >= 2)
      .map((point) => [point[0], point[1]] as L.LatLngExpression);
    if (routePoints && routePoints.length >= 2) {
      return routePoints;
    }
    return operarioLatLng ? [operarioLatLng, incidentLatLng] : [incidentLatLng];
  }

  private removeServiceFromMap(serviceId: number): void {
    const markerSet = this.markers.get(serviceId);
    if (markerSet) {
      markerSet.operario.remove();
      markerSet.incidente.remove();
      this.markers.delete(serviceId);
    }
    const polyline = this.polylines.get(serviceId);
    if (polyline) {
      polyline.remove();
      this.polylines.delete(serviceId);
    }
  }
}
