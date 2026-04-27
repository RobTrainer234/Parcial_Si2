import { CommonModule } from '@angular/common';
import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { AppCardComponent } from '../../../shared/components/app-card.component';
import { EmptyStateComponent } from '../../../shared/components/empty-state.component';
import { ErrorStateComponent } from '../../../shared/components/error-state.component';
import { LoadingStateComponent } from '../../../shared/components/loading-state.component';
import { MetricCardComponent } from '../../../shared/components/metric-card.component';
import { PageHeaderComponent } from '../../../shared/components/page-header.component';
import { StatusBadgeComponent } from '../../../shared/components/status-badge.component';
import {
  DashboardActionItem,
  DashboardCountItem,
  DashboardMonthlyRevenueItem,
  DashboardOverviewResponse,
} from '../data-access/workshop-dashboard.models';
import { WorkshopDashboardApi } from '../data-access/workshop-dashboard.api';

@Component({
  selector: 'app-admin-dashboard-page',
  standalone: true,
  imports: [
    CommonModule,
    PageHeaderComponent,
    MetricCardComponent,
    AppCardComponent,
    StatusBadgeComponent,
    LoadingStateComponent,
    EmptyStateComponent,
    ErrorStateComponent,
  ],
  template: `
    <div class="page">
      <app-page-header
        eyebrow="Centro de control"
        title="Dashboard del taller"
        subtitle="Visibilidad rápida del estado operativo, financiero y de servicio del taller."
      >
        <button page-actions type="button" class="app-button app-button--secondary" (click)="reload()" [disabled]="loading()">
          {{ loading() ? 'Actualizando...' : 'Actualizar panel' }}
        </button>
      </app-page-header>

      @if (loading() && !overview()) {
        <app-loading-state
          title="Cargando tablero"
          message="Consultando KPIs y métricas del taller."
        />
      } @else if (error()) {
        <app-error-state [message]="error()">
          <button error-actions type="button" class="app-button" (click)="reload()">
            Reintentar
          </button>
        </app-error-state>
      } @else if (overview(); as data) {
        <section class="dashboard-kpis">
          <app-metric-card
            label="Solicitudes pendientes"
            [value]="formatInteger(data.kpis.pending_requests)"
            hint="Pendientes por decisión del taller"
          />
          <app-metric-card
            label="Servicios activos"
            [value]="formatInteger(data.kpis.active_services)"
            hint="Servicios actualmente en ejecución"
          />
          <app-metric-card
            label="Ingresos confirmados"
            [value]="formatCurrency(data.financial.total_revenue)"
            hint="Cobros confirmados en el periodo"
          />
          <app-metric-card
            label="Calificación promedio"
            [value]="formatRating(data.kpis.average_rating)"
            hint="Promedio real del periodo filtrado"
          />
          <app-metric-card
            label="Acciones críticas"
            [value]="formatInteger(data.action_items.length)"
            hint="Elementos operativos que requieren seguimiento"
          />
        </section>

        <section class="section-grid">
          <app-card
            title="Acciones prioritarias"
            subtitle="Resumen de alertas y decisiones recomendadas para el administrador."
          >
            @if (data.action_items.length) {
              <div class="list">
                @for (item of actionItemsPreview(); track item.title + item.type + item.related_service_id) {
                  <article class="list__item">
                    <div class="list__meta">
                      <span class="badge" [class]="priorityBadgeClass(item.priority)">
                        {{ item.priority }}
                      </span>
                      <strong>{{ item.title }}</strong>
                    </div>
                    <p class="text-muted">{{ item.description }}</p>
                    <small class="text-muted">{{ item.recommended_action }}</small>
                  </article>
                }
              </div>
            } @else {
              <app-empty-state
                title="Sin alertas urgentes"
                message="No hay acciones inmediatas calculadas para el periodo actual."
              />
            }
          </app-card>

          <app-card
            title="Servicios por estado"
            subtitle="Distribución operativa actual del taller."
          >
            @if (data.operations.services_by_state.length) {
              <div class="list">
                @for (item of data.operations.services_by_state; track item.label) {
                  <div class="row">
                    <app-status-badge [label]="item.label" />
                    <strong>{{ formatInteger(item.count) }}</strong>
                  </div>
                }
              </div>
            } @else {
              <app-empty-state
                title="Sin servicios en el periodo"
                message="Todavía no hay estados de servicio que mostrar con el filtro actual."
              />
            }
          </app-card>
        </section>

        <section class="section-grid">
          <app-card
            title="Resumen financiero"
            subtitle="Comparativo simple de cobros y pagos del taller."
          >
            <div class="finance-grid">
              <div class="finance-grid__item">
                <span>Ingresos confirmados</span>
                <strong>{{ formatCurrency(data.financial.total_revenue) }}</strong>
              </div>
              <div class="finance-grid__item">
                <span>Pagos pendientes</span>
                <strong>{{ formatInteger(data.financial.pending_payments) }}</strong>
              </div>
              <div class="finance-grid__item">
                <span>Pagos rechazados</span>
                <strong>{{ formatInteger(data.financial.rejected_payments) }}</strong>
              </div>
              <div class="finance-grid__item">
                <span>Proyección</span>
                <strong>{{ formatCurrency(data.financial.projected_revenue) }}</strong>
              </div>
            </div>

            @if (monthlyRevenue().length) {
              <div class="revenue-bars">
                @for (item of monthlyRevenue(); track item.month) {
                  <div class="revenue-bars__row">
                    <div class="revenue-bars__labels">
                      <span>{{ item.month }}</span>
                      <strong>{{ formatCurrency(item.revenue) }}</strong>
                    </div>
                    <div class="revenue-bars__track">
                      <span
                        class="revenue-bars__bar"
                        [style.width.%]="monthlyRevenueWidth(item)"
                      ></span>
                    </div>
                  </div>
                }
              </div>
            } @else {
              <div class="finance-grid__empty">
                <app-empty-state
                  title="Sin ingresos mensuales"
                  message="No hay ingresos mensuales registrados para este periodo."
                />
              </div>
            }
          </app-card>
        </section>
      } @else {
        <app-empty-state
          title="Información no disponible"
          message="No hay información para mostrar en el panel en este momento."
        />
      }
    </div>
  `,
  styles: [
    `
      .dashboard-kpis {
        display: grid;
        gap: var(--space-4);
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      }

      .list {
        display: flex;
        flex-direction: column;
        gap: var(--space-4);
      }

      .list__item {
        display: flex;
        flex-direction: column;
        gap: 0.45rem;
        padding: var(--space-4);
        border-radius: var(--radius-lg);
        border: 1px solid var(--color-border);
        background: color-mix(in srgb, var(--color-surface-soft) 92%, transparent);
      }

      .list__item p,
      .list__item small {
        margin: 0;
      }

      .list__meta {
        display: flex;
        align-items: center;
        gap: var(--space-3);
        flex-wrap: wrap;
      }

      .row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: var(--space-4);
        padding: var(--space-3) 0;
        border-bottom: 1px solid color-mix(in srgb, var(--color-border) 70%, transparent);
      }

      .row:last-child {
        border-bottom: 0;
        padding-bottom: 0;
      }

      .finance-grid {
        display: grid;
        gap: var(--space-4);
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      }

      .finance-grid__item {
        padding: var(--space-4);
        border-radius: var(--radius-lg);
        background: color-mix(in srgb, var(--color-surface-soft) 92%, transparent);
        border: 1px solid var(--color-border);
      }

      .finance-grid__item span,
      .health__label {
        display: block;
        color: var(--color-text-muted);
        font-size: 0.86rem;
      }

      .finance-grid__item strong,
      .health__row strong {
        display: block;
        margin-top: var(--space-2);
      }

      .finance-grid__empty {
        margin-top: var(--space-5);
      }

      .revenue-bars {
        display: flex;
        flex-direction: column;
        gap: var(--space-4);
        margin-top: var(--space-6);
      }

      .revenue-bars__labels {
        display: flex;
        justify-content: space-between;
        gap: var(--space-4);
        margin-bottom: var(--space-2);
        font-size: 0.92rem;
      }

      .revenue-bars__track {
        height: 0.7rem;
        border-radius: 999px;
        background: color-mix(in srgb, var(--color-border) 82%, transparent);
        overflow: hidden;
      }

      .revenue-bars__bar {
        display: block;
        height: 100%;
        border-radius: 999px;
        background: linear-gradient(90deg, var(--color-primary), color-mix(in srgb, var(--color-primary) 62%, #ffffff));
      }

      .health {
        display: flex;
        flex-direction: column;
        gap: var(--space-4);
      }

      .health__row {
        padding-bottom: var(--space-4);
        border-bottom: 1px solid color-mix(in srgb, var(--color-border) 70%, transparent);
      }

      .health__row:last-child {
        border-bottom: 0;
        padding-bottom: 0;
      }
    `,
  ],
})
export class AdminDashboardPage {
  private readonly dashboardApi = inject(WorkshopDashboardApi);
  private readonly destroyRef = inject(DestroyRef);

  protected readonly loading = signal(false);
  protected readonly error = signal('');
  protected readonly overview = signal<DashboardOverviewResponse | null>(null);

  protected readonly monthlyRevenue = computed(
    () => this.overview()?.financial.monthly_revenue ?? [],
  );

  protected readonly actionItemsPreview = computed(() =>
    (this.overview()?.action_items ?? []).slice(0, 6),
  );

  constructor() {
    this.reload();
  }

  protected reload(): void {
    this.loading.set(true);
    this.error.set('');

    this.dashboardApi
      .getOverview()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => {
          this.overview.set(response);
          this.loading.set(false);
        },
        error: (error) => {
          this.error.set(error.error?.detail ?? 'No se pudo cargar el panel operativo.');
          this.loading.set(false);
        },
      });
  }

  protected formatInteger(value: number | string | null | undefined): string {
    return new Intl.NumberFormat('es-BO', { maximumFractionDigits: 0 }).format(
      this.asNumber(value),
    );
  }

  protected formatCurrency(value: number | string | null | undefined): string {
    return `BOB ${new Intl.NumberFormat('es-BO', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(this.asNumber(value))}`;
  }

  protected formatRating(value: number | null | undefined): string {
    if (value === null || value === undefined) {
      return 'Sin datos';
    }

    return `${value.toFixed(1)} / 5`;
  }

  protected formatMinutes(value: number | null | undefined): string {
    if (value === null || value === undefined) {
      return 'Sin datos';
    }

    return `${Math.round(value)} min`;
  }

  protected formatPercentage(value: number | null | undefined): string {
    if (value === null || value === undefined) {
      return 'Sin datos';
    }

    return `${value.toFixed(1)}%`;
  }

  protected priorityBadgeClass(priority: string): string {
    switch (priority) {
      case 'HIGH':
        return 'badge badge--danger';
      case 'MEDIUM':
        return 'badge badge--warning';
      default:
        return 'badge badge--info';
    }
  }

  protected monthlyRevenueWidth(item: DashboardMonthlyRevenueItem): number {
    const values = this.monthlyRevenue().map((entry) => this.asNumber(entry.revenue));
    const maxValue = Math.max(...values, 0);
    const currentValue = this.asNumber(item.revenue);

    if (!maxValue) {
      return 0;
    }

    return Math.max(10, (currentValue / maxValue) * 100);
  }

  private asNumber(value: number | string | null | undefined): number {
    const numericValue = Number(value ?? 0);
    return Number.isFinite(numericValue) ? numericValue : 0;
  }
}
