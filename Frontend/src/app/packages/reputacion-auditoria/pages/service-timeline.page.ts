import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  inject,
  signal,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { AppCardComponent } from '../../../shared/components/app-card.component';
import { EmptyStateComponent } from '../../../shared/components/empty-state.component';
import { ErrorStateComponent } from '../../../shared/components/error-state.component';
import { LoadingStateComponent } from '../../../shared/components/loading-state.component';
import { PageHeaderComponent } from '../../../shared/components/page-header.component';
import { StatusBadgeComponent } from '../../../shared/components/status-badge.component';
import { localizeStatusLabel } from '../../../shared/utils/user-facing-text';
import { AuditApi } from '../data-access/audit.api';
import { ServiceTimelineItem } from '../data-access/audit.models';

@Component({
  selector: 'app-service-timeline-page',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    CommonModule,
    RouterLink,
    StatusBadgeComponent,
    AppCardComponent,
    EmptyStateComponent,
    ErrorStateComponent,
    LoadingStateComponent,
    PageHeaderComponent,
  ],
  template: `
    <app-page-header
      [title]="'Timeline del servicio #' + (serviceId() || '...')"
      subtitle="Historial cronologico de eventos y cambios de estado."
      eyebrow="Auditoria / Timeline"
    >
      <div page-actions>
        <a routerLink="/admin/audit" class="app-button app-button--secondary">
          Volver a auditoria
        </a>
      </div>
    </app-page-header>

    @if (pageError()) {
      <div class="mb-4">
        <app-error-state [message]="pageError()"></app-error-state>
      </div>
    }

    @if (loading()) {
      <app-loading-state message="Cargando timeline del servicio..."></app-loading-state>
    } @else if (timeline().length === 0) {
      <app-empty-state [message]="'No se encontro historial para el servicio #' + serviceId() + '.'"></app-empty-state>
    } @else {
      <app-card>
        <div class="timeline">
          @for (item of timeline(); track item.audit_id) {
            <div class="timeline-item">
              <div class="timeline-item__marker"></div>
              <div class="timeline-item__content">
                <div class="timeline-item__header">
                  <strong>{{ item.event_type }}</strong>
                  <span class="timeline-item__date">{{ formatDate(item.timestamp) }}</span>
                </div>

                <div class="timeline-item__body">
                  <div class="timeline-item__row">
                    <span class="text-muted">Accion:</span>
                    <app-status-badge [label]="item.action" />
                  </div>
                  @if (item.service_state) {
                    <div class="timeline-item__row">
                      <span class="text-muted">Estado del servicio:</span>
                      <span class="badge badge--info">{{ localizeStatus(item.service_state) }}</span>
                    </div>
                  }
                  @if (item.incident_state) {
                    <div class="timeline-item__row">
                      <span class="text-muted">Estado del incidente:</span>
                      <span class="badge badge--neutral">{{ localizeStatus(item.incident_state) }}</span>
                    </div>
                  }
                  @if (item.description) {
                    <div class="timeline-item__row">
                      <span class="text-muted">Descripcion:</span>
                      <span>{{ item.description }}</span>
                    </div>
                  }
                  <div class="timeline-item__row mt-2">
                    <span class="text-muted">Ref auditoria:</span>
                    <span class="text-muted">#{{ item.audit_id }}</span>
                  </div>
                </div>
              </div>
            </div>
          }
        </div>
      </app-card>
    }
  `,
  styles: [
    `
      .timeline {
        display: flex;
        flex-direction: column;
        gap: var(--space-4);
        position: relative;
      }

      .timeline::before {
        content: '';
        position: absolute;
        top: 0;
        bottom: 0;
        left: 9px;
        width: 2px;
        background-color: var(--color-border);
      }

      .timeline-item {
        display: flex;
        gap: var(--space-4);
        position: relative;
      }

      .timeline-item__marker {
        width: 20px;
        height: 20px;
        border-radius: 50%;
        background-color: var(--color-primary);
        border: 4px solid var(--color-surface);
        box-shadow: 0 0 0 1px var(--color-border);
        flex-shrink: 0;
        position: relative;
        z-index: 1;
      }

      .timeline-item__content {
        flex: 1;
        background: color-mix(in srgb, var(--color-surface-soft) 40%, transparent);
        border: 1px solid var(--color-border);
        border-radius: var(--radius-md);
        padding: var(--space-4);
      }

      .timeline-item__header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: var(--space-3);
        padding-bottom: var(--space-2);
        border-bottom: 1px solid var(--color-border);
      }

      .timeline-item__date {
        font-size: 0.85rem;
        color: var(--color-text-muted);
      }

      .timeline-item__body {
        display: flex;
        flex-direction: column;
        gap: var(--space-2);
        font-size: 0.9rem;
      }

      .timeline-item__row {
        display: flex;
        align-items: center;
        gap: var(--space-2);
        flex-wrap: wrap;
      }

      .badge--info { background: var(--color-primary); color: #fff; }
      .badge--neutral { background: var(--color-surface-soft); border: 1px solid var(--color-border); }
      .text-muted { color: var(--color-text-muted); }
      .mt-2 { margin-top: var(--space-2); }
      .mb-4 { margin-bottom: var(--space-4); }
    `,
  ],
})
export class ServiceTimelinePage {
  private readonly api = inject(AuditApi);
  private readonly route = inject(ActivatedRoute);
  private readonly destroyRef = inject(DestroyRef);

  protected readonly serviceId = signal<number | null>(null);
  protected readonly timeline = signal<ServiceTimelineItem[]>([]);
  protected readonly loading = signal(true);
  protected readonly pageError = signal('');

  constructor() {
    this.route.paramMap.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((params) => {
      const rawId = params.get('serviceId');
      const id = rawId ? Number(rawId) : NaN;
      if (Number.isInteger(id) && id > 0) {
        this.serviceId.set(id);
        this.loadTimeline(id);
      } else {
        this.pageError.set('ID de servicio invalido.');
        this.loading.set(false);
      }
    });
  }

  private loadTimeline(serviceId: number): void {
    this.loading.set(true);
    this.pageError.set('');

    this.api
      .getServiceTimeline(serviceId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => {
          this.timeline.set(response);
          this.loading.set(false);
        },
        error: () => {
          this.pageError.set('No se pudo cargar el timeline del servicio.');
          this.loading.set(false);
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

  protected localizeStatus(value: string | null | undefined): string {
    return localizeStatusLabel(value);
  }
}
