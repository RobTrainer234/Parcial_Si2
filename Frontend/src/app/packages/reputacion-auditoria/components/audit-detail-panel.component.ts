import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

import { StatusBadgeComponent } from '../../../shared/components/status-badge.component';
import { AuditLogDetail } from '../data-access/audit.models';

@Component({
  selector: 'app-audit-detail-panel',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CommonModule, StatusBadgeComponent],
  template: `
    <section class="detail-panel app-card">
      <header class="detail-panel__header">
        <h4>Detalle de auditoria #{{ detail()?.audit_id }}</h4>
        <button
          type="button"
          class="app-button app-button--secondary app-button--sm"
          (click)="closePanel.emit()"
        >
          Cerrar
        </button>
      </header>

      @if (detail(); as log) {
        <div class="detail-panel__body">
          <div class="detail-grid">
            <div class="detail-item">
              <span class="detail-label">Fecha y hora</span>
              <span class="detail-value">{{ formatDate(log.timestamp) }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">Actor</span>
              <span class="detail-value">{{ actorLabel(log) }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">Accion</span>
              <span class="detail-value"><app-status-badge [label]="log.action" /></span>
            </div>
            <div class="detail-item">
              <span class="detail-label">Tipo de evento</span>
              <span class="detail-value">{{ log.event_type }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">Entidad</span>
              <span class="detail-value">{{ log.main_entity }} #{{ log.main_entity_id ?? '-' }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">Descripcion</span>
              <span class="detail-value">{{ log.description || '-' }}</span>
            </div>
            @if (log.linked.service_id) {
              <div class="detail-item">
                <span class="detail-label">Servicio relacionado</span>
                <span class="detail-value">#{{ log.linked.service_id }}</span>
              </div>
            }
            @if (log.linked.incident_id) {
              <div class="detail-item">
                <span class="detail-label">Incidente relacionado</span>
                <span class="detail-value">#{{ log.linked.incident_id }}</span>
              </div>
            }
            @if (log.linked.request_id) {
              <div class="detail-item">
                <span class="detail-label">Solicitud relacionada</span>
                <span class="detail-value">#{{ log.linked.request_id }}</span>
              </div>
            }
            @if (log.linked.payment_id) {
              <div class="detail-item">
                <span class="detail-label">Pago relacionado</span>
                <span class="detail-value">#{{ log.linked.payment_id }}</span>
              </div>
            }
            <div class="detail-item">
              <span class="detail-label">IP / User agent</span>
              <span class="detail-value">{{ log.ip_origen || '-' }} / {{ log.user_agent || '-' }}</span>
            </div>
          </div>

          @if (log.hash_evento) {
            <div class="detail-hash mt-4">
              <span class="detail-label">Hash de integridad</span>
              <code class="hash-box">{{ log.hash_evento }}</code>
            </div>
          }

          @if (log.has_original_data || log.has_new_data) {
            <div class="technical-details mt-4">
              <h5 class="mb-3">Datos auditables</h5>

              @if (log.has_original_data) {
                <div class="json-block mb-3">
                  <span class="detail-label">Datos originales</span>
                  <pre><code>{{ formatJson(log.datos_originales) }}</code></pre>
                </div>
              }

              @if (log.has_new_data) {
                <div class="json-block">
                  <span class="detail-label">Datos nuevos</span>
                  <pre><code>{{ formatJson(log.datos_nuevos) }}</code></pre>
                </div>
              }
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
        margin-bottom: var(--space-5);
        padding-bottom: var(--space-3);
        border-bottom: 1px solid var(--color-border);
      }

      .detail-panel__header h4 {
        margin: 0;
        font-size: 1.25rem;
      }

      .detail-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
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

      .mt-4 {
        margin-top: var(--space-4);
      }

      .mb-3 {
        margin-bottom: var(--space-3);
      }

      .hash-box {
        display: block;
        padding: var(--space-2);
        background: var(--color-surface);
        border: 1px solid var(--color-border);
        border-radius: var(--radius-sm);
        font-size: 0.85rem;
        word-break: break-all;
        margin-top: var(--space-1);
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
export class AuditDetailPanelComponent {
  readonly detail = input<AuditLogDetail | null>(null);
  readonly closePanel = output<void>();

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

  protected actorLabel(log: AuditLogDetail): string {
    if (log.actor?.email) {
      return log.actor.email;
    }
    if (log.actor?.tipo_usuario && log.actor?.user_id) {
      return `${log.actor.tipo_usuario} #${log.actor.user_id}`;
    }
    if (log.actor?.user_id) {
      return `Usuario #${log.actor.user_id}`;
    }
    return 'Sistema';
  }

  protected formatJson(data: unknown): string {
    if (data === null || data === undefined) {
      return '-';
    }

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
