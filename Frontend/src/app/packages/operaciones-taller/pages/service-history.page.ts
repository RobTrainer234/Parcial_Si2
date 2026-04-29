import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  computed,
  inject,
  signal,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';

import { AppCardComponent } from '../../../shared/components/app-card.component';
import { EmptyStateComponent } from '../../../shared/components/empty-state.component';
import { ErrorStateComponent } from '../../../shared/components/error-state.component';
import { LoadingStateComponent } from '../../../shared/components/loading-state.component';
import { MetricCardComponent } from '../../../shared/components/metric-card.component';
import { PageHeaderComponent } from '../../../shared/components/page-header.component';
import {
  formatLocalDateTime,
  localizeBackendMessage,
  localizeStatusLabel,
} from '../../../shared/utils/user-facing-text';
import { WorkshopServiceHistoryApi } from '../data-access/workshop-service-history.api';
import {
  WorkshopServiceHistoryDetail,
  WorkshopServiceHistorySummary,
} from '../data-access/workshop-service-history.models';
import { WorkshopStaffApi } from '../data-access/workshop-staff.api';
import { WorkshopStaffSummary } from '../data-access/workshop-staff.models';

@Component({
  selector: 'app-service-history-page',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    CommonModule,
    FormsModule,
    RouterLink,
    AppCardComponent,
    EmptyStateComponent,
    ErrorStateComponent,
    LoadingStateComponent,
    MetricCardComponent,
    PageHeaderComponent,
  ],
  template: `
    <div class="page">
      <app-page-header
        eyebrow="Operacion / Historial"
        title="Servicios realizados"
        subtitle="Consulta los servicios atendidos por el taller, el operario asignado, pago y calificacion."
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

      <section class="summary-grid">
        <app-metric-card
          label="Total servicios"
          [value]="formatInteger(totalServices())"
          hint="Servicios cargados con los filtros actuales"
        />
        <app-metric-card
          label="En atencion"
          [value]="formatInteger(inAttentionCount())"
          hint="Servicios activos o en coordinacion"
        />
        <app-metric-card
          label="Pendientes de pago"
          [value]="formatInteger(pendingPaymentCount())"
          hint="Esperando confirmacion de pago del cliente"
        />
        <app-metric-card
          label="Pagados"
          [value]="formatInteger(paidCount())"
          hint="Servicios cerrados con pago confirmado"
        />
        <app-metric-card
          label="Calificacion promedio"
          [value]="formatRating(averageRating())"
          hint="Promedio de las calificaciones disponibles"
        />
      </section>

      <app-card
        title="Filtros"
        subtitle="Refina el historial por estado, operario o rango de fechas."
      >
        <div class="filters">
          <label class="field">
            <span>Estado</span>
            <select [(ngModel)]="estadoFilter">
              <option value="">Todos</option>
              @for (item of stateOptions; track item.value) {
                <option [value]="item.value">{{ item.label }}</option>
              }
            </select>
          </label>

          <label class="field">
            <span>Operario</span>
            <select [(ngModel)]="operarioFilter">
              <option value="">Todos</option>
              @for (operario of operarios(); track operario.operario_id) {
                <option [value]="operario.operario_id">{{ operario.nombre_completo }}</option>
              }
            </select>
          </label>

          <label class="field">
            <span>Fecha desde</span>
            <input type="date" [(ngModel)]="desdeFilter" />
          </label>

          <label class="field">
            <span>Fecha hasta</span>
            <input type="date" [(ngModel)]="hastaFilter" />
          </label>

          <div class="field field--actions">
            <button type="button" class="app-button" (click)="reload()" [disabled]="loading()">
              Actualizar
            </button>
          </div>
        </div>
      </app-card>

      @if (loading() && !services().length) {
        <app-loading-state
          title="Cargando historial"
          message="Consultando servicios del taller."
        />
      } @else if (pageError() && !services().length) {
        <app-error-state [message]="pageError()">
          <button error-actions type="button" class="app-button" (click)="reload()">
            Intentar nuevamente
          </button>
        </app-error-state>
      } @else if (!services().length) {
        <app-empty-state
          title="Sin servicios registrados"
          message="No hay servicios registrados para este taller."
        />
      } @else {
        <section class="layout">
          <div class="layout__main">
            <app-card
              title="Historial del taller"
              subtitle="Listado de servicios atendidos y su estado actual."
            >
              <div class="table-wrap">
                <table class="history-table">
                  <thead>
                    <tr>
                      <th>Fecha</th>
                      <th>Servicio</th>
                      <th>Estado</th>
                      <th>Especialidad</th>
                      <th>Operario</th>
                      <th>Monto</th>
                      <th>Pago</th>
                      <th>Calificacion</th>
                      <th>Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    @for (item of services(); track item.service_id) {
                      <tr>
                        <td>{{ formatDate(resolveDisplayDate(item)) }}</td>
                        <td>
                          <div class="service-ref">
                            <strong>Servicio de auxilio</strong>
                            <span class="text-muted">Referencia #{{ item.service_id }}</span>
                          </div>
                        </td>
                        <td>{{ localizeStatus(item.service_state) }}</td>
                        <td>{{ item.specialty || 'Sin especialidad' }}</td>
                        <td>{{ item.operario_name || 'Sin asignar' }}</td>
                        <td>{{ formatCurrency(item.final_amount) }}</td>
                        <td>{{ localizeStatus(item.payment_status || 'PENDIENTE') }}</td>
                        <td>{{ formatRating(item.rating_average) }}</td>
                        <td>
                          <button
                            type="button"
                            class="app-button app-button--ghost"
                            (click)="openDetail(item.service_id)"
                            [disabled]="detailLoadingId() === item.service_id"
                          >
                            {{ detailLoadingId() === item.service_id ? 'Cargando...' : 'Ver detalle' }}
                          </button>
                        </td>
                      </tr>
                    }
                  </tbody>
                </table>
              </div>
            </app-card>
          </div>

          <div class="layout__side">
            @if (selectedDetail(); as detail) {
              <app-card
                title="Detalle del servicio"
                subtitle="Resumen operativo, tecnico, financiero y de calificacion."
              >
                <div class="detail-grid">
                  <div>
                    <span class="detail-label">Servicio</span>
                    <strong>Servicio de auxilio</strong>
                    <small class="text-muted">Referencia #{{ detail.service_id }}</small>
                  </div>
                  <div>
                    <span class="detail-label">Estado del servicio</span>
                    <strong>{{ localizeStatus(detail.service_state) }}</strong>
                  </div>
                  <div>
                    <span class="detail-label">Estado del incidente</span>
                    <strong>{{ localizeStatus(detail.incident_state) }}</strong>
                  </div>
                  <div>
                    <span class="detail-label">Cliente</span>
                    <strong>{{ detail.client_name || 'No disponible' }}</strong>
                  </div>
                  <div>
                    <span class="detail-label">Operario</span>
                    <strong>{{ detail.operario_name || 'Sin asignar' }}</strong>
                  </div>
                  <div>
                    <span class="detail-label">Especialidad</span>
                    <strong>{{ detail.detected_specialty || detail.specialty || 'Sin especialidad' }}</strong>
                  </div>
                  <div>
                    <span class="detail-label">Pre-cotizacion</span>
                    <strong>{{ formatPrequotation(detail) }}</strong>
                  </div>
                  <div>
                    <span class="detail-label">Pago</span>
                    <strong>{{ localizeStatus(detail.payment_status || 'PENDIENTE') }}</strong>
                    <small class="text-muted">{{ formatCurrency(detail.payment_amount || detail.final_amount) }}</small>
                  </div>
                  <div>
                    <span class="detail-label">Calificacion</span>
                    <strong>{{ formatRating(detail.rating_average) }}</strong>
                    <small class="text-muted">{{ detail.rating_comment || 'Sin comentario' }}</small>
                  </div>
                </div>

                <div class="detail-section">
                  <h4>Diagnostico IA</h4>
                  <p>{{ detail.ai_summary || 'No hay un diagnostico IA registrado.' }}</p>
                </div>

                <div class="detail-section">
                  <h4>Reporte tecnico</h4>
                  <p><strong>Trabajo realizado:</strong> {{ detail.trabajo_realizado || 'No disponible' }}</p>
                  <p><strong>Diagnostico fisico:</strong> {{ detail.diagnostico_fisico || 'No disponible' }}</p>
                  <p><strong>Observaciones:</strong> {{ detail.observaciones || 'Sin observaciones' }}</p>
                  <p><strong>Recomendaciones:</strong> {{ detail.recomendaciones || 'Sin recomendaciones' }}</p>
                </div>

                <div class="detail-section">
                  <h4>Fechas principales</h4>
                  <div class="detail-grid detail-grid--dates">
                    <div>
                      <span class="detail-label">Creado</span>
                      <strong>{{ formatDate(detail.created_at) }}</strong>
                    </div>
                    <div>
                      <span class="detail-label">Asignado</span>
                      <strong>{{ formatDate(detail.assigned_at) }}</strong>
                    </div>
                    <div>
                      <span class="detail-label">Completado</span>
                      <strong>{{ formatDate(detail.completed_at) }}</strong>
                    </div>
                    <div>
                      <span class="detail-label">Pagado</span>
                      <strong>{{ formatDate(detail.paid_at) }}</strong>
                    </div>
                  </div>
                </div>

                <div class="detail-actions">
                  <a
                    class="app-button app-button--secondary"
                    [routerLink]="['/admin/services', detail.service_id, 'timeline']"
                  >
                    Ver timeline
                  </a>
                  <button type="button" class="app-button app-button--ghost" (click)="clearDetail()">
                    Cerrar detalle
                  </button>
                </div>
              </app-card>
            } @else if (detailError()) {
              <app-error-state [message]="detailError()">
                <button error-actions type="button" class="app-button" (click)="clearDetail()">
                  Cerrar
                </button>
              </app-error-state>
            } @else {
              <app-card
                title="Detalle del servicio"
                subtitle="Selecciona un servicio para revisar diagnostico, pago y calificacion."
              >
                <app-empty-state
                  title="Sin detalle seleccionado"
                  message="Elige un servicio desde la lista para ver su historial completo."
                />
              </app-card>
            }
          </div>
        </section>
      }
    </div>
  `,
  styles: [
    `
      .summary-grid {
        display: grid;
        gap: var(--space-4);
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      }

      .filters {
        display: grid;
        gap: var(--space-4);
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      }

      .field {
        display: flex;
        flex-direction: column;
        gap: var(--space-2);
      }

      .field span {
        color: var(--color-text-muted);
        font-size: 0.86rem;
      }

      .field select,
      .field input {
        min-height: 2.8rem;
        border-radius: var(--radius-md);
        border: 1px solid var(--color-border);
        background: var(--color-surface);
        color: var(--color-text);
        padding: 0 0.9rem;
      }

      .field--actions {
        justify-content: flex-end;
      }

      .layout {
        display: grid;
        gap: var(--space-5);
        grid-template-columns: minmax(0, 1.5fr) minmax(320px, 1fr);
        align-items: start;
      }

      .layout__main,
      .layout__side {
        min-width: 0;
      }

      .table-wrap {
        overflow-x: auto;
      }

      .history-table {
        width: 100%;
        border-collapse: collapse;
      }

      .history-table th,
      .history-table td {
        padding: 0.85rem 0.75rem;
        border-bottom: 1px solid color-mix(in srgb, var(--color-border) 75%, transparent);
        vertical-align: top;
        text-align: left;
      }

      .history-table th {
        color: var(--color-text-muted);
        font-size: 0.84rem;
        font-weight: 600;
      }

      .service-ref {
        display: flex;
        flex-direction: column;
        gap: 0.2rem;
      }

      .detail-grid {
        display: grid;
        gap: var(--space-4);
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      }

      .detail-grid--dates {
        margin-top: var(--space-3);
      }

      .detail-label {
        display: block;
        margin-bottom: 0.35rem;
        color: var(--color-text-muted);
        font-size: 0.84rem;
      }

      .detail-section {
        margin-top: var(--space-5);
      }

      .detail-section h4,
      .detail-section p {
        margin: 0 0 0.65rem;
      }

      .detail-actions {
        display: flex;
        flex-wrap: wrap;
        gap: var(--space-3);
        margin-top: var(--space-5);
      }

      .text-muted {
        color: var(--color-text-muted);
      }

      @media (max-width: 1160px) {
        .layout {
          grid-template-columns: 1fr;
        }
      }
    `,
  ],
})
export class ServiceHistoryPage {
  private readonly historyApi = inject(WorkshopServiceHistoryApi);
  private readonly staffApi = inject(WorkshopStaffApi);
  private readonly destroyRef = inject(DestroyRef);

  protected readonly loading = signal(false);
  protected readonly pageError = signal('');
  protected readonly services = signal<WorkshopServiceHistorySummary[]>([]);
  protected readonly operarios = signal<WorkshopStaffSummary[]>([]);
  protected readonly selectedDetail = signal<WorkshopServiceHistoryDetail | null>(null);
  protected readonly detailError = signal('');
  protected readonly detailLoadingId = signal<number | null>(null);

  protected estadoFilter = '';
  protected operarioFilter = '';
  protected desdeFilter = '';
  protected hastaFilter = '';

  protected readonly totalServices = computed(() => this.services().length);
  protected readonly inAttentionCount = computed(() =>
    this.services().filter((item) =>
      [
        'EN_ESPERA_ASIGNACION',
        'ASIGNADO',
        'EN_CAMINO',
        'EN_SITIO',
        'EN_DIAGNOSTICO_FISICO',
        'EN_REPARACION',
      ].includes(item.service_state),
    ).length,
  );
  protected readonly pendingPaymentCount = computed(() =>
    this.services().filter((item) => item.service_state === 'FINALIZADO_PENDIENTE_PAGO').length,
  );
  protected readonly paidCount = computed(() =>
    this.services().filter((item) => item.service_state === 'PAGADO').length,
  );
  protected readonly averageRating = computed(() => {
    const values = this.services()
      .map((item) => this.asNumber(item.rating_average))
      .filter((value) => value > 0);
    if (!values.length) {
      return null;
    }
    return values.reduce((sum, value) => sum + value, 0) / values.length;
  });

  protected readonly stateOptions = [
    { value: 'EN_ESPERA_ASIGNACION', label: 'En espera de asignacion' },
    { value: 'ASIGNADO', label: 'Asignado' },
    { value: 'EN_CAMINO', label: 'En camino' },
    { value: 'EN_SITIO', label: 'En sitio' },
    { value: 'EN_DIAGNOSTICO_FISICO', label: 'Diagnostico fisico' },
    { value: 'EN_REPARACION', label: 'En reparacion' },
    { value: 'COMPLETADO_PENDIENTE_CONFIRMACION', label: 'Pendiente de confirmacion' },
    { value: 'FINALIZADO_PENDIENTE_PAGO', label: 'Pendiente de pago' },
    { value: 'PAGADO', label: 'Pagado' },
  ];

  constructor() {
    this.loadOperarios();
    this.reload();
  }

  protected reload(): void {
    this.loading.set(true);
    this.pageError.set('');

    this.historyApi
      .listServices({
        estado: this.estadoFilter || null,
        operario_id: this.parsePositiveInteger(this.operarioFilter),
        desde: this.toApiDateStart(this.desdeFilter),
        hasta: this.toApiDateEnd(this.hastaFilter),
        limit: 100,
        offset: 0,
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => {
          this.services.set(response);
          this.loading.set(false);
        },
        error: (error) => {
          this.pageError.set(this.mapPageError(error));
          this.loading.set(false);
        },
      });
  }

  protected openDetail(serviceId: number): void {
    this.detailLoadingId.set(serviceId);
    this.detailError.set('');

    this.historyApi
      .getServiceDetail(serviceId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => {
          this.selectedDetail.set(response);
          this.detailLoadingId.set(null);
        },
        error: (error) => {
          this.selectedDetail.set(null);
          this.detailError.set(this.mapDetailError(error));
          this.detailLoadingId.set(null);
        },
      });
  }

  protected clearDetail(): void {
    this.selectedDetail.set(null);
    this.detailError.set('');
    this.detailLoadingId.set(null);
  }

  protected localizeStatus(value: string | null | undefined): string {
    return localizeStatusLabel(value);
  }

  protected formatDate(value: string | null | undefined): string {
    return formatLocalDateTime(value);
  }

  protected formatInteger(value: number | string | null | undefined): string {
    return new Intl.NumberFormat('es-BO', { maximumFractionDigits: 0 }).format(
      this.asNumber(value),
    );
  }

  protected formatCurrency(value: number | string | null | undefined): string {
    if (value === null || value === undefined || value === '') {
      return 'Sin monto';
    }
    return `BOB ${new Intl.NumberFormat('es-BO', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(this.asNumber(value))}`;
  }

  protected formatRating(value: number | string | null | undefined): string {
    const numericValue = this.asNumber(value);
    if (numericValue <= 0) {
      return 'Sin calificacion';
    }
    return `${numericValue.toFixed(1)} / 5`;
  }

  protected resolveDisplayDate(item: WorkshopServiceHistorySummary): string {
    return item.paid_at || item.completed_at || item.assigned_at || item.created_at;
  }

  protected formatPrequotation(detail: WorkshopServiceHistoryDetail): string {
    if (detail.estimated_min === null || detail.estimated_min === undefined) {
      return 'No disponible';
    }
    if (detail.estimated_max === null || detail.estimated_max === undefined) {
      return this.formatCurrency(detail.estimated_min);
    }
    return `${this.formatCurrency(detail.estimated_min)} - ${this.formatCurrency(detail.estimated_max)}`;
  }

  private loadOperarios(): void {
    this.staffApi
      .listStaff()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => this.operarios.set(response),
        error: () => this.operarios.set([]),
      });
  }

  private mapPageError(error: unknown): string {
    const detail = this.extractDetail(error);
    if (detail) {
      return detail;
    }
    if (error instanceof HttpErrorResponse && error.status === 403) {
      return 'No tienes permisos para consultar el historial del taller.';
    }
    return 'No se pudo cargar el historial de servicios.';
  }

  private mapDetailError(error: unknown): string {
    const detail = this.extractDetail(error);
    if (detail) {
      return detail;
    }
    if (error instanceof HttpErrorResponse && error.status === 404) {
      return 'No se encontro el servicio solicitado.';
    }
    return 'No se pudo cargar el detalle del servicio.';
  }

  private extractDetail(error: unknown): string {
    if (error instanceof HttpErrorResponse) {
      const detail = error.error?.detail;
      if (typeof detail === 'string' && detail.trim()) {
        return localizeBackendMessage(detail.trim());
      }
      if (typeof error.error === 'string' && error.error.trim()) {
        return localizeBackendMessage(error.error.trim());
      }
    }
    if (error instanceof Error && error.message.trim()) {
      return localizeBackendMessage(error.message.trim());
    }
    return '';
  }

  private toApiDateStart(value: string): string | null {
    const trimmed = value.trim();
    if (!trimmed) {
      return null;
    }
    return `${trimmed}T00:00:00`;
  }

  private toApiDateEnd(value: string): string | null {
    const trimmed = value.trim();
    if (!trimmed) {
      return null;
    }
    return `${trimmed}T23:59:59`;
  }

  private parsePositiveInteger(value: string): number | null {
    const numericValue = Number(value);
    if (!Number.isInteger(numericValue) || numericValue <= 0) {
      return null;
    }
    return numericValue;
  }

  private asNumber(value: number | string | null | undefined): number {
    const numericValue = Number(value ?? 0);
    return Number.isFinite(numericValue) ? numericValue : 0;
  }
}
