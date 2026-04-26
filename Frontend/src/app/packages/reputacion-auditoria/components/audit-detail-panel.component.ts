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
        <h4>Detalle de Auditoría #{{ detail()?.audit_id }}</h4>
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
              <span class="detail-label">Fecha y Hora</span>
              <span class="detail-value">{{ formatDate(log.timestamp) }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">Actor</span>
              <span class="detail-value">{{ log.actor || log.usuario || 'Sistema' }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">Acción</span>
              <span class="detail-value"><app-status-badge [label]="log.action" /></span>
            </div>
            <div class="detail-item">
              <span class="detail-label">Tipo de Evento</span>
              <span class="detail-value">{{ log.event_type }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">Entidad</span>
              <span class="detail-value">{{ log.entity_type }} #{{ log.entity_id || '-' }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">Resultado/Estado</span>
              <span class="detail-value">{{ log.result || log.status || '-' }}</span>
            </div>
            @if (log.service_id) {
              <div class="detail-item">
                <span class="detail-label">Servicio Relacionado</span>
                <span class="detail-value">#{{ log.service_id }}</span>
              </div>
            }
            @if (log.incident_id) {
              <div class="detail-item">
                <span class="detail-label">Incidente Relacionado</span>
                <span class="detail-value">#{{ log.incident_id }}</span>
              </div>
            }
            @if (log.request_id) {
              <div class="detail-item">
                <span class="detail-label">Solicitud Relacionada</span>
                <span class="detail-value">#{{ log.request_id }}</span>
              </div>
            }
            <div class="detail-item">
              <span class="detail-label">IP / Dispositivo</span>
              <span class="detail-value">{{ log.ip_address || '-' }} / {{ log.device_info || '-' }}</span>
            </div>
          </div>

          @if (log.hash_integridad) {
            <div class="detail-hash mt-4">
              <span class="detail-label">Hash de Integridad</span>
              <code class="hash-box">{{ log.hash_integridad }}</code>
            </div>
          }

          @if (hasTechnicalDetails(log)) {
            <div class="technical-details mt-4">
              <h5 class="mb-3">Detalles Técnicos</h5>
              
              @if (log.previous_state) {
                <div class="json-block mb-3">
                  <span class="detail-label">Estado Anterior</span>
                  <pre><code>{{ formatJson(log.previous_state) }}</code></pre>
                </div>
              }
              
              @if (log.new_state) {
                <div class="json-block mb-3">
                  <span class="detail-label">Estado Nuevo</span>
                  <pre><code>{{ formatJson(log.new_state) }}</code></pre>
                </div>
              }
              
              @if (log.detalle_json || log.metadata) {
                <div class="json-block">
                  <span class="detail-label">Metadatos / Detalle</span>
                  <pre><code>{{ formatJson(log.detalle_json || log.metadata) }}</code></pre>
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

  protected hasTechnicalDetails(log: AuditLogDetail): boolean {
    return Boolean(
      log.previous_state || log.new_state || log.detalle_json || log.metadata
    );
  }

  protected formatJson(data: unknown): string {
    try {
      if (typeof data === 'string') {
        // Handle pre-stringified JSON
        const parsed = JSON.parse(data);
        return JSON.stringify(parsed, null, 2);
      }
      return JSON.stringify(data, null, 2);
    } catch {
      // Fallback for non-JSON strings or circular structures
      return String(data);
    }
  }
}
