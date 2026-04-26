import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

import { StatusBadgeComponent } from '../../../shared/components/status-badge.component';
import { NotificationDetail } from '../data-access/notifications.models';

@Component({
  selector: 'app-notification-detail-panel',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CommonModule, StatusBadgeComponent],
  template: `
    <section class="detail-panel app-card">
      <header class="detail-panel__header">
        <h4>{{ detail()?.title || detail()?.titulo || 'Detalle de Notificación' }}</h4>
        <button
          type="button"
          class="app-button app-button--secondary app-button--sm"
          (click)="closePanel.emit()"
        >
          Cerrar
        </button>
      </header>

      @if (detail(); as notif) {
        <div class="detail-panel__body">
          <p class="detail-message">{{ notif.message || notif.mensaje }}</p>

          <div class="detail-grid mt-4">
            <div class="detail-item">
              <span class="detail-label">ID Notificación</span>
              <span class="detail-value">#{{ notif.notification_id || notif.id_notificacion }}</span>
            </div>
            
            <div class="detail-item">
              <span class="detail-label">Fecha de Creación</span>
              <span class="detail-value">{{ formatDate(notif.created_at || notif.fecha_creacion) }}</span>
            </div>
            
            <div class="detail-item">
              <span class="detail-label">Estado</span>
              <span class="detail-value">
                @if (notif.read || notif.leida) {
                  <span class="badge badge--neutral">Leída</span>
                } @else {
                  <span class="badge badge--warning">No leída</span>
                }
              </span>
            </div>

            @if (notif.read_at || notif.fecha_lectura) {
              <div class="detail-item">
                <span class="detail-label">Fecha de Lectura</span>
                <span class="detail-value">{{ formatDate(notif.read_at || notif.fecha_lectura) }}</span>
              </div>
            }

            <div class="detail-item">
              <span class="detail-label">Tipo</span>
              <span class="detail-value">{{ notif.type || notif.tipo || '-' }}</span>
            </div>
            
            <div class="detail-item">
              <span class="detail-label">Prioridad</span>
              <span class="detail-value">
                <app-status-badge [label]="notif.priority || notif.prioridad || '-'" />
              </span>
            </div>
          </div>

          <div class="detail-grid mt-3">
            @if (notif.service_id) {
              <div class="detail-item">
                <span class="detail-label">Servicio Relacionado</span>
                <span class="detail-value">#{{ notif.service_id }}</span>
              </div>
            }
            @if (notif.incident_id) {
              <div class="detail-item">
                <span class="detail-label">Incidente Relacionado</span>
                <span class="detail-value">#{{ notif.incident_id }}</span>
              </div>
            }
            @if (notif.request_id) {
              <div class="detail-item">
                <span class="detail-label">Solicitud Relacionada</span>
                <span class="detail-value">#{{ notif.request_id }}</span>
              </div>
            }
            @if (notif.audit_id) {
              <div class="detail-item">
                <span class="detail-label">Auditoría Relacionada</span>
                <span class="detail-value">#{{ notif.audit_id }}</span>
              </div>
            }
            @if (notif.payment_id) {
              <div class="detail-item">
                <span class="detail-label">Pago Relacionado</span>
                <span class="detail-value">#{{ notif.payment_id }}</span>
              </div>
            }
          </div>

          @if (hasTechnicalDetails(notif)) {
            <div class="technical-details mt-4">
              <h5 class="mb-3">Detalle Técnico</h5>
              <div class="json-block">
                <pre><code>{{ formatJson(notif.metadata || notif.detalle_json) }}</code></pre>
              </div>
            </div>
          }
        </div>
      }
    </section>
  `,
  styles: [
    `
      .detail-panel {
        padding: var(--space-5);
        margin-top: var(--space-4);
        margin-bottom: var(--space-4);
        background: color-mix(in srgb, var(--color-surface-soft) 80%, transparent);
        border: 1px solid var(--color-border);
      }

      .detail-panel__header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: var(--space-4);
        padding-bottom: var(--space-3);
        border-bottom: 1px solid var(--color-border);
      }

      .detail-panel__header h4 {
        margin: 0;
        font-size: 1.25rem;
      }

      .detail-message {
        font-size: 1.05rem;
        line-height: 1.5;
        margin-top: 0;
      }

      .detail-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
        gap: var(--space-4);
      }

      .detail-item {
        display: flex;
        flex-direction: column;
        gap: var(--space-1);
      }

      .detail-label {
        font-size: 0.85rem;
        color: var(--color-text-muted);
        text-transform: uppercase;
        letter-spacing: 0.5px;
      }

      .detail-value {
        font-weight: 500;
        word-break: break-word;
      }

      .mt-3 {
        margin-top: var(--space-3);
      }

      .mt-4 {
        margin-top: var(--space-4);
      }

      .mb-3 {
        margin-bottom: var(--space-3);
      }

      .technical-details {
        padding-top: var(--space-4);
        border-top: 1px solid var(--color-border);
      }

      .technical-details h5 {
        margin-top: 0;
        color: var(--color-primary);
      }

      .json-block pre {
        background: var(--color-surface);
        border: 1px solid var(--color-border);
        border-radius: var(--radius-md);
        padding: var(--space-3);
        overflow-x: auto;
        font-size: 0.85rem;
        margin-top: var(--space-2);
        margin-bottom: 0;
      }
    `,
  ],
})
export class NotificationDetailPanelComponent {
  readonly detail = input<NotificationDetail | null>(null);
  readonly closePanel = output<void>();

  protected formatDate(value: string | null | undefined): string {
    if (!value) return '-';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return value;
    }

    return new Intl.DateTimeFormat('es-BO', {
      dateStyle: 'medium',
      timeStyle: 'medium',
    }).format(date);
  }

  protected hasTechnicalDetails(notif: NotificationDetail): boolean {
    return Boolean(notif.metadata || notif.detalle_json);
  }

  protected formatJson(data: unknown): string {
    try {
      if (typeof data === 'string') {
        const parsed = JSON.parse(data);
        return JSON.stringify(parsed, null, 2);
      }
      return JSON.stringify(data, null, 2);
    } catch {
      return String(data);
    }
  }
}
