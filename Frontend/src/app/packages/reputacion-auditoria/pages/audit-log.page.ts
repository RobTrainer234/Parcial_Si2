import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  inject,
  signal,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';

import { AppCardComponent } from '../../../shared/components/app-card.component';
import { EmptyStateComponent } from '../../../shared/components/empty-state.component';
import { ErrorStateComponent } from '../../../shared/components/error-state.component';
import { LoadingStateComponent } from '../../../shared/components/loading-state.component';
import { PageHeaderComponent } from '../../../shared/components/page-header.component';
import { StatusBadgeComponent } from '../../../shared/components/status-badge.component';
import { AuditDetailPanelComponent } from '../components/audit-detail-panel.component';
import { AuditFilterPanelComponent } from '../components/audit-filter-panel.component';
import { AuditApi } from '../data-access/audit.api';
import {
  AuditFilterOptions,
  AuditLogDetail,
  AuditLogFilters,
  AuditLogSummary,
} from '../data-access/audit.models';

@Component({
  selector: 'app-audit-log-page',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    CommonModule,
    RouterLink,
    StatusBadgeComponent,
    AuditFilterPanelComponent,
    AuditDetailPanelComponent,
    AppCardComponent,
    EmptyStateComponent,
    ErrorStateComponent,
    LoadingStateComponent,
    PageHeaderComponent,
  ],
  template: `
    <app-page-header
      title="Auditoría y trazabilidad"
      subtitle="Consulta eventos críticos, cambios de estado y evidencias operativas del taller."
    >
      <div page-actions>
        <button
          type="button"
          class="app-button app-button--secondary"
          (click)="toggleFilters()"
        >
          Filtros
        </button>
        <button
          type="button"
          class="app-button app-button--secondary"
          (click)="loadLogs()"
          [disabled]="loading()"
        >
          Actualizar
        </button>
        <button
          type="button"
          class="app-button"
          (click)="exportCsv()"
          [disabled]="exporting() || logs().length === 0"
        >
          {{ exporting() ? 'Exportando...' : 'Exportar CSV' }}
        </button>
      </div>
    </app-page-header>

    @if (pageError()) {
      <div class="mb-4">
        <app-error-state [message]="pageError()"></app-error-state>
      </div>
    }

    @if (isFiltersVisible()) {
      <app-audit-filter-panel
        [filterOptions]="filterOptions()"
        [currentFilters]="currentFilters()"
        (closePanel)="isFiltersVisible.set(false)"
        (filtersApplied)="applyFilters($event)"
      />
    }

    @if (selectedDetail()) {
      <app-audit-detail-panel
        [detail]="selectedDetail()"
        (closePanel)="closeDetail()"
      />
    }

    @if (loading()) {
      <app-loading-state message="Cargando registros de auditoría..."></app-loading-state>
    } @else if (logs().length === 0) {
      <div>
        <app-empty-state message="No se encontraron registros de auditoría."></app-empty-state>
        @if (hasActiveFilters()) {
          <div class="mt-3">
            <button type="button" class="app-button app-button--sm" (click)="applyFilters({})">
              Limpiar filtros
            </button>
          </div>
        }
      </div>
    } @else {
      <div class="summary-counters mb-4 mt-4">
        <span class="badge badge--info">Total registros: {{ logs().length }}</span>
      </div>

      <app-card>
        <div class="table-responsive">
          <table class="app-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Fecha y Hora</th>
                <th>Actor</th>
                <th>Acción</th>
                <th>Evento</th>
                <th>Entidad</th>
                <th>Entidad ID</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              @for (log of logs(); track log.audit_id) {
                <tr>
                  <td>#{{ log.audit_id }}</td>
                  <td>{{ formatDate(log.timestamp) }}</td>
                  <td>{{ log.actor || log.usuario || 'Sistema' }}</td>
                  <td><app-status-badge [label]="log.action" /></td>
                  <td>{{ log.event_type }}</td>
                  <td>{{ log.entity_type }}</td>
                  <td>{{ log.entity_id || '-' }}</td>
                  <td>
                    <div class="table-actions">
                      <button
                        type="button"
                        class="app-button app-button--secondary app-button--sm"
                        (click)="viewDetail(log.audit_id)"
                        [disabled]="loadingDetailId() === log.audit_id"
                      >
                        {{ loadingDetailId() === log.audit_id ? 'Cargando...' : 'Ver detalle' }}
                      </button>
                      @if (log.service_id) {
                        <a
                          class="app-button app-button--ghost app-button--sm"
                          [routerLink]="['/admin/services', log.service_id, 'timeline']"
                        >
                          Ver timeline
                        </a>
                      }
                    </div>
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      </app-card>
    }
  `,
  styles: [
    `
      .table-responsive {
        overflow-x: auto;
      }

      .app-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.9rem;
      }

      .app-table th,
      .app-table td {
        padding: var(--space-3) var(--space-4);
        text-align: left;
        border-bottom: 1px solid var(--color-border);
      }

      .app-table th {
        font-weight: 600;
        color: var(--color-text-muted);
        background: color-mix(in srgb, var(--color-surface-soft) 50%, transparent);
        white-space: nowrap;
      }

      .app-table tbody tr:hover {
        background: color-mix(in srgb, var(--color-surface-soft) 40%, transparent);
      }

      .table-actions {
        display: flex;
        gap: var(--space-2);
        align-items: center;
      }

      .mb-4 {
        margin-bottom: var(--space-4);
      }
      
      .mt-4 {
        margin-top: var(--space-4);
      }

      .mt-3 {
        margin-top: var(--space-3);
      }
    `,
  ],
})
export class AuditLogPage {
  private readonly api = inject(AuditApi);
  private readonly destroyRef = inject(DestroyRef);

  protected readonly loading = signal(true);
  protected readonly exporting = signal(false);
  protected readonly pageError = signal('');
  
  protected readonly isFiltersVisible = signal(false);
  protected readonly currentFilters = signal<AuditLogFilters>({});
  protected readonly filterOptions = signal<AuditFilterOptions | null>(null);
  
  protected readonly logs = signal<AuditLogSummary[]>([]);
  protected readonly selectedDetail = signal<AuditLogDetail | null>(null);
  protected readonly loadingDetailId = signal<number | null>(null);

  constructor() {
    this.loadFilterOptions();
    this.loadLogs();
  }

  protected loadLogs(): void {
    this.loading.set(true);
    this.pageError.set('');

    this.api
      .listAuditLogs(this.currentFilters())
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => {
          this.logs.set(response);
          this.loading.set(false);
        },
        error: () => {
          this.pageError.set('No se pudieron cargar los registros de auditoría.');
          this.loading.set(false);
        },
      });
  }

  private loadFilterOptions(): void {
    this.api
      .getFilterOptions()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (options) => this.filterOptions.set(options),
        error: () => console.warn('Failed to load filter options'),
      });
  }

  protected toggleFilters(): void {
    this.isFiltersVisible.update((v) => !v);
  }

  protected applyFilters(filters: AuditLogFilters): void {
    this.currentFilters.set(filters);
    this.isFiltersVisible.set(false);
    this.closeDetail();
    this.loadLogs();
  }

  protected hasActiveFilters(): boolean {
    return Object.keys(this.currentFilters()).length > 0;
  }

  protected viewDetail(auditId: number): void {
    if (this.loadingDetailId()) {
      return;
    }

    if (!Number.isInteger(auditId) || auditId <= 0) {
      this.pageError.set('ID de auditoría inválido.');
      return;
    }

    this.pageError.set('');
    this.loadingDetailId.set(auditId);

    this.api
      .getAuditDetail(auditId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (detail) => {
          this.selectedDetail.set(detail);
          this.loadingDetailId.set(null);
        },
        error: () => {
          this.pageError.set('No se pudo cargar el detalle de la auditoría.');
          this.loadingDetailId.set(null);
        },
      });
  }

  protected closeDetail(): void {
    this.selectedDetail.set(null);
  }

  protected exportCsv(): void {
    if (this.exporting()) {
      return;
    }

    this.exporting.set(true);
    this.pageError.set('');

    this.api
      .exportCsv(this.currentFilters())
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (blob) => {
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = `audit_logs_taller_${new Date().toISOString().split('T')[0]}.csv`;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          window.URL.revokeObjectURL(url);
          this.exporting.set(false);
        },
        error: () => {
          this.pageError.set('No se pudo exportar el CSV de auditoría.');
          this.exporting.set(false);
        },
      });
  }

  protected formatDate(value: string): string {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return value;
    }

    return new Intl.DateTimeFormat('es-BO', {
      dateStyle: 'medium',
      timeStyle: 'medium',
    }).format(date);
  }
}
