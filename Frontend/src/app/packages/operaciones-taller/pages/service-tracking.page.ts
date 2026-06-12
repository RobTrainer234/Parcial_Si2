import { CommonModule } from '@angular/common';
import {
  Component,
  DestroyRef,
  OnInit,
  computed,
  effect,
  inject,
  signal,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import * as L from 'leaflet';
import { interval, switchMap } from 'rxjs';

import { AppCardComponent } from '../../../shared/components/app-card.component';
import { EmptyStateComponent } from '../../../shared/components/empty-state.component';
import { ErrorStateComponent } from '../../../shared/components/error-state.component';
import { LoadingStateComponent } from '../../../shared/components/loading-state.component';
import { PageHeaderComponent } from '../../../shared/components/page-header.component';
import { StatusBadgeComponent } from '../../../shared/components/status-badge.component';
import {
  ServiceTrackingStatus,
  WorkshopTrackingApi,
} from '../data-access/workshop-tracking.api';

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
        subtitle="Visualiza en tiempo real la ubicación de los operarios y el estado de los servicios activos."
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
                          message="Obteniendo ubicación del operario."
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
                            <p><strong>Operario:</strong> Sin ubicación aún</p>
                          }
                          @if (st.last_location_at; as date) {
                            <p><strong>Última actualización:</strong> {{ date | date:'short' }}</p>
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
export class ServiceTrackingPage implements OnInit {
  private readonly api = inject(WorkshopTrackingApi);
  private readonly destroyRef = inject(DestroyRef);

  protected readonly loading = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly services = signal<ServiceItem[]>([]);
  protected readonly activeServiceIds = computed(() =>
    this.services()
      .filter((s) => s.status?.has_live_location)
      .map((s) => s.serviceId),
  );

  private map: L.Map | null = null;
  private markers: Map<number, { operario: L.Marker; incidente: L.Marker }> =
    new Map();
  private polylines: Map<number, L.Polyline> = new Map();
  private readonly incidentIcon = L.divIcon({
    className: '',
    html: `<div style="background:#dc2626;color:#fff;width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:16px;box-shadow:0 2px 6px rgba(0,0,0,0.3);">📍</div>`,
    iconSize: [32, 32],
    iconAnchor: [16, 16],
  });
  private readonly operarioIcon = L.divIcon({
    className: '',
    html: `<div style="background:#16a34a;color:#fff;width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:16px;box-shadow:0 2px 6px rgba(0,0,0,0.3);animation:pulse-live 2s ease-in-out infinite;">🔧</div>`,
    iconSize: [32, 32],
    iconAnchor: [16, 16],
  });

  ngOnInit(): void {
    this.reload();
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
      list.map((s) => {
        if (s.serviceId !== serviceId) return s;
        const expanded = !s.expanded;
        if (expanded && s.status === null) {
          this.loadServiceTracking(s.serviceId);
        }
        return { ...s, expanded };
      }),
    );
  }

  private loadServiceTracking(serviceId: number): void {
    this.services.update((list) =>
      list.map((s) =>
        s.serviceId === serviceId ? { ...s, loading: true, error: null } : s,
      ),
    );
    this.api
      .getTrackingStatus(serviceId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (status) => {
          this.services.update((list) =>
            list.map((s) =>
              s.serviceId === serviceId
                ? { ...s, status, loading: false, error: null }
                : s,
            ),
          );
          this.updateMapMarker(serviceId, status);
        },
        error: (err) => {
          this.services.update((list) =>
            list.map((s) =>
              s.serviceId === serviceId
                ? {
                    ...s,
                    loading: false,
                    error: err?.message ?? 'Error al cargar tracking.',
                  }
                : s,
            ),
          );
        },
      });
  }

  private updateFromPolling(
    data: import('../data-access/workshop-tracking.api').ServiceWithOperator[],
  ): void {
    this.services.set(
      data.map((d) => ({
        serviceId: d.service_id,
        status: d.last_operario_latitud != null
          ? ({
              service_id: d.service_id,
              service_state: d.service_state,
              incident_id: d.incident_id,
              incident_latitud: d.incident_latitud,
              incident_longitud: d.incident_longitud,
              last_operario_latitud: d.last_operario_latitud,
              last_operario_longitud: d.last_operario_longitud,
              last_location_at: d.last_location_at,
              has_live_location: d.has_live_location,
              location_stale: false,
              current_distance_meters: d.current_distance_meters,
              eta_text: d.eta_text,
              tracking_message: '',
            } as ServiceTrackingStatus)
          : null,
        expanded: false,
        loading: false,
        error: null,
      })),
    );
    data.forEach((d) => {
      if (d.last_operario_latitud != null) {
        this.updateMapMarker(d.service_id, {
          service_id: d.service_id,
          service_state: d.service_state,
          incident_id: d.incident_id,
          incident_latitud: d.incident_latitud,
          incident_longitud: d.incident_longitud,
          last_operario_latitud: d.last_operario_latitud,
          last_operario_longitud: d.last_operario_longitud,
          last_location_at: d.last_location_at,
          has_live_location: d.has_live_location,
          location_stale: false,
          tracking_message: '',
        });
      }
    });
  }

  private initMap(): void {
    const el = document.querySelector('.tracking-map') as HTMLElement;
    if (!el) return;
    this.map = L.map(el, {
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

  private updateMapMarker(
    serviceId: number,
    status: ServiceTrackingStatus,
  ): void {
    if (!this.map) return;
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
      }).addTo(this.map!);
      const incidenteMarker = L.marker(incidentLatLng, {
        icon: this.incidentIcon,
      }).addTo(this.map!);

      operarioMarker.bindPopup(
        `Servicio #${serviceId} - Operario<br/>Estado: ${status.service_state}`,
      );
      incidenteMarker.bindPopup(
        `Servicio #${serviceId} - Incidente #${status.incident_id}`,
      );

      const polyline = L.polyline(
        operarioLatLng ? [operarioLatLng, incidentLatLng] : [incidentLatLng],
        { color: '#2563eb', weight: 3, opacity: 0.6, dashArray: '8 4' },
      ).addTo(this.map!);

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
        const pts: L.LatLngExpression[] = operarioLatLng
          ? [operarioLatLng, incidentLatLng]
          : [incidentLatLng];
        polyline.setLatLngs(pts);
      }
    }

    const allBounds = L.latLngBounds([]);
    this.markers.forEach((m) => {
      allBounds.extend(m.incidente.getLatLng());
      allBounds.extend(m.operario.getLatLng());
    });
    if (allBounds.isValid()) {
      this.map.fitBounds(allBounds, { padding: [50, 50] });
    }
  }
}
