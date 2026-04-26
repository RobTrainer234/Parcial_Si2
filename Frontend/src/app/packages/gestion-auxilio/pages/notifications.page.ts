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

import { NotificationApiService as CoreNotificationApi } from '../../../core/notifications/notification-api.service';
import { AppCardComponent } from '../../../shared/components/app-card.component';
import { EmptyStateComponent } from '../../../shared/components/empty-state.component';
import { ErrorStateComponent } from '../../../shared/components/error-state.component';
import { LoadingStateComponent } from '../../../shared/components/loading-state.component';
import { PageHeaderComponent } from '../../../shared/components/page-header.component';
import { StatusBadgeComponent } from '../../../shared/components/status-badge.component';
import { NotificationDetailPanelComponent } from '../components/notification-detail-panel.component';
import { NotificationFilterPanelComponent } from '../components/notification-filter-panel.component';
import { NotificationsPageApi } from '../data-access/notifications.api';
import {
  NotificationDetail,
  NotificationFilters,
  NotificationSummary,
} from '../data-access/notifications.models';

@Component({
  selector: 'app-notifications-page',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    CommonModule,
    RouterLink,
    AppCardComponent,
    EmptyStateComponent,
    ErrorStateComponent,
    LoadingStateComponent,
    PageHeaderComponent,
    NotificationFilterPanelComponent,
    NotificationDetailPanelComponent,
  ],
  template: `
    <app-page-header
      title="Notificaciones"
      subtitle="Consulta alertas operativas, avisos del sistema y eventos que requieren atención del taller."
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
          (click)="loadNotifications()"
          [disabled]="loading()"
        >
          Actualizar
        </button>
        @if (hasUnread) {
          <button
            type="button"
            class="app-button"
            (click)="markAllAsRead()"
            [disabled]="processingAll()"
          >
            {{ processingAll() ? 'Procesando...' : 'Marcar todas como leídas' }}
          </button>
        }
      </div>
    </app-page-header>

    @if (pageError()) {
      <div class="mb-4">
        <app-error-state [message]="pageError()"></app-error-state>
      </div>
    }

    @if (isFiltersVisible()) {
      <app-notification-filter-panel
        [currentFilters]="currentFilters()"
        (closePanel)="isFiltersVisible.set(false)"
        (filtersApplied)="applyFilters($event)"
      />
    }

    @if (selectedDetail()) {
      <app-notification-detail-panel
        [detail]="selectedDetail()"
        (closePanel)="closeDetail()"
      />
    }

    @if (loading()) {
      <app-loading-state message="Cargando notificaciones..."></app-loading-state>
    } @else if (notifications().length === 0) {
      <div>
        <app-empty-state message="No se encontraron notificaciones."></app-empty-state>
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
        <span class="badge badge--info">Total cargadas: {{ notifications().length }}</span>
        @if (unreadCount > 0) {
          <span class="badge badge--warning">No leídas: {{ unreadCount }}</span>
        }
      </div>

      <app-card>
        <div class="table-responsive">
          <table class="app-table">
            <thead>
              <tr>
                <th style="width: 50px;"></th>
                <th>Fecha y Hora</th>
                <th>Prioridad</th>
                <th>Título</th>
                <th>Tipo</th>
                <th>Referencia</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              @for (notif of notifications(); track notificationId(notif)) {
                <tr [class.is-unread]="!(notif.read || notif.leida)">
                  <td class="status-indicator">
                    @if (!(notif.read || notif.leida)) {
                      <span class="unread-dot" title="No leída"></span>
                    }
                  </td>
                  <td>{{ formatDate(notif.created_at || notif.fecha_creacion) }}</td>
                  <td>
                    <span class="badge" [ngClass]="getPriorityClass(notif.priority || notif.prioridad)">
                      {{ notif.priority || notif.prioridad || '-' }}
                    </span>
                  </td>
                  <td class="font-medium">{{ notif.title || notif.titulo }}</td>
                  <td>{{ notif.type || notif.tipo }}</td>
                  <td>{{ getReferenceLabel(notif) }}</td>
                  <td>
                    <div class="table-actions">
                      <button
                        type="button"
                        class="app-button app-button--ghost app-button--sm"
                        (click)="viewDetail(notif)"
                        [disabled]="!notificationId(notif) || loadingDetailId() === notificationId(notif)"
                      >
                        {{ loadingDetailId() === notificationId(notif) ? 'Cargando...' : 'Ver detalle' }}
                      </button>

                      @if (!(notif.read || notif.leida) && notificationId(notif)) {
                        <button
                          type="button"
                          class="app-button app-button--secondary app-button--sm"
                          (click)="markAsRead(notificationId(notif)!)"
                          [disabled]="processingIds().has(notificationId(notif)!)"
                        >
                          Marcar leída
                        </button>
                      }

                      @if (getRelatedRoute(notif); as route) {
                        <a
                          class="app-button app-button--secondary app-button--sm"
                          [routerLink]="route"
                        >
                          Ir al recurso
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

      .app-table tbody tr.is-unread {
        background: color-mix(in srgb, var(--color-surface-soft) 40%, transparent);
      }
      
      .app-table tbody tr:hover {
        background: color-mix(in srgb, var(--color-surface-soft) 80%, transparent);
      }

      .status-indicator {
        text-align: center;
      }

      .unread-dot {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background-color: var(--color-primary);
      }

      .font-medium {
        font-weight: 500;
      }

      .table-actions {
        display: flex;
        gap: var(--space-2);
        align-items: center;
      }

      .badge--danger { background: var(--color-danger); color: #fff; }
      .badge--warning { background: var(--color-warning); color: #fff; }
      .badge--info { background: var(--color-primary); color: #fff; }
      .badge--neutral { background: var(--color-surface-soft); border: 1px solid var(--color-border); }

      .mb-4 { margin-bottom: var(--space-4); }
      .mt-4 { margin-top: var(--space-4); }
      .mt-3 { margin-top: var(--space-3); }
    `,
  ],
})
export class NotificationsPage {
  private readonly api = inject(NotificationsPageApi);
  private readonly coreApi = inject(CoreNotificationApi);
  private readonly destroyRef = inject(DestroyRef);

  protected readonly loading = signal(true);
  protected readonly pageError = signal('');
  protected readonly processingAll = signal(false);
  protected readonly processingIds = signal<Set<number>>(new Set());
  
  protected readonly isFiltersVisible = signal(false);
  protected readonly currentFilters = signal<NotificationFilters>({});
  
  protected readonly notifications = signal<NotificationSummary[]>([]);
  protected readonly selectedDetail = signal<NotificationDetail | null>(null);
  protected readonly loadingDetailId = signal<number | null>(null);

  protected get unreadCount(): number {
    return this.notifications().filter(n => !(n.read || n.leida)).length;
  }

  protected get hasUnread(): boolean {
    return this.unreadCount > 0;
  }

  private isPositiveInteger(value: unknown): value is number {
    return typeof value === 'number' && Number.isInteger(value) && value > 0;
  }

  protected notificationId(notif: NotificationSummary): number | null {
    const id = notif.notification_id ?? notif.id_notificacion ?? null;
    return this.isPositiveInteger(id) ? id : null;
  }

  constructor() {
    this.loadNotifications();
  }

  protected loadNotifications(): void {
    this.loading.set(true);
    this.pageError.set('');

    this.api
      .listNotifications(this.currentFilters())
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => {
          this.notifications.set(response);
          this.loading.set(false);
          this.coreApi.triggerUnreadCountRefresh();
        },
        error: () => {
          this.pageError.set('No se pudieron cargar las notificaciones.');
          this.loading.set(false);
        },
      });
  }

  protected toggleFilters(): void {
    this.isFiltersVisible.update((v) => !v);
  }

  protected applyFilters(filters: NotificationFilters): void {
    this.currentFilters.set(filters);
    this.isFiltersVisible.set(false);
    this.closeDetail();
    this.loadNotifications();
  }

  protected hasActiveFilters(): boolean {
    return Object.keys(this.currentFilters()).length > 0;
  }

  protected viewDetail(notif: NotificationSummary): void {
    const id = this.notificationId(notif);
    if (!id || this.loadingDetailId()) {
      return;
    }

    if (!Number.isInteger(id) || id <= 0) {
      this.pageError.set('ID de notificación inválido.');
      return;
    }

    this.pageError.set('');
    this.loadingDetailId.set(id);

    this.api
      .getNotificationDetail(id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (detail) => {
          this.selectedDetail.set(detail);
          this.loadingDetailId.set(null);
        },
        error: () => {
          // If no specific endpoint exists, fallback to list item representation
          this.selectedDetail.set({ ...notif } as NotificationDetail);
          this.loadingDetailId.set(null);
        },
      });
  }

  protected closeDetail(): void {
    this.selectedDetail.set(null);
  }

  protected markAsRead(id: number): void {
    if (!this.isPositiveInteger(id)) return;

    this.pageError.set('');
    this.processingIds.update(set => {
      const newSet = new Set(set);
      newSet.add(id);
      return newSet;
    });

    this.api
      .markAsRead(id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.notifications.update(list => 
            list.map(n => 
              (this.notificationId(n) === id) 
                ? { ...n, read: true, leida: true } 
                : n
            )
          );
          this.processingIds.update(set => {
            const newSet = new Set(set);
            newSet.delete(id);
            return newSet;
          });
          this.coreApi.triggerUnreadCountRefresh();
        },
        error: () => {
          this.pageError.set('No se pudo marcar la notificación como leída.');
          this.processingIds.update(set => {
            const newSet = new Set(set);
            newSet.delete(id);
            return newSet;
          });
        },
      });
  }

  protected markAllAsRead(): void {
    if (!confirm('¿Marcar todas las notificaciones como leídas?')) {
      return;
    }

    this.processingAll.set(true);
    this.pageError.set('');

    this.api
      .markAllAsRead()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.loadNotifications();
          this.processingAll.set(false);
        },
        error: () => {
          this.pageError.set('No se pudieron marcar todas como leídas. Es posible que el servidor no soporte esta operación.');
          this.processingAll.set(false);
        },
      });
  }

  protected getPriorityClass(priority: string | null | undefined): string {
    const p = (priority || '').toUpperCase();
    if (p === 'CRITICAL' || p === 'CRITICA' || p === 'ALTA' || p === 'HIGH') return 'badge--danger';
    if (p === 'MEDIUM' || p === 'MEDIA') return 'badge--warning';
    if (p === 'LOW' || p === 'BAJA' || p === 'INFO') return 'badge--info';
    return 'badge--neutral';
  }

  protected getReferenceLabel(notif: NotificationSummary): string {
    if (notif.request_id) return `Solicitud #${notif.request_id}`;
    if (notif.service_id) return `Servicio #${notif.service_id}`;
    if (notif.incident_id) return `Incidente #${notif.incident_id}`;
    if (notif.audit_id) return `Auditoría #${notif.audit_id}`;
    if (notif.payment_id) return `Pago #${notif.payment_id}`;
    return '-';
  }

  protected getRelatedRoute(notif: NotificationSummary): any[] | null {
    if (this.isPositiveInteger(notif.request_id)) return ['/admin/requests', notif.request_id];
    if (this.isPositiveInteger(notif.service_id)) return ['/admin/services/waiting-assignment'];
    if (this.isPositiveInteger(notif.audit_id)) return ['/admin/audit'];
    return null;
  }

  protected formatDate(value: string | null | undefined): string {
    if (!value) return '-';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return value;
    }

    return new Intl.DateTimeFormat('es-BO', {
      dateStyle: 'medium',
      timeStyle: 'short',
    }).format(date);
  }
}
