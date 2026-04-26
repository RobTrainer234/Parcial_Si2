import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

import {
  OperarioCandidateSummary,
  WaitingAssignmentServiceSummary,
} from '../data-access/workshop-assignment.models';

@Component({
  selector: 'app-assignment-confirmation-panel',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CommonModule],
  template: `
    <section class="confirmation-panel">
      <h4>Asignar operario</h4>
      <p class="text-muted">
        Se asignara este operario al servicio seleccionado y pasara a estado EN_SERVICIO.
      </p>

      <div class="confirmation-grid">
        <div class="confirmation-item">
          <span class="text-muted">Servicio</span>
          <strong>#{{ service().service_id }}</strong>
        </div>
        <div class="confirmation-item">
          <span class="text-muted">Operario</span>
          <strong>{{ candidate().nombre_completo }}</strong>
        </div>
        <div class="confirmation-item">
          <span class="text-muted">Especialidad detectada</span>
          <strong>{{ service().detected_specialty?.nombre || 'Sin detectar' }}</strong>
        </div>
        <div class="confirmation-item">
          <span class="text-muted">Pre-cotizacion</span>
          <strong>{{ service().prequotation_code || 'Sin codigo' }}</strong>
        </div>
      </div>

      @if (errorMessage()) {
        <p class="feedback feedback--error">{{ errorMessage() }}</p>
      }

      <div class="confirmation-actions">
        <button
          type="button"
          class="app-button"
          (click)="confirm.emit()"
          [disabled]="submitting()"
        >
          {{ submitting() ? 'Asignando...' : 'Confirmar asignacion' }}
        </button>
        <button
          type="button"
          class="app-button app-button--secondary"
          (click)="cancel.emit()"
          [disabled]="submitting()"
        >
          Cancelar
        </button>
      </div>
    </section>
  `,
  styles: [
    `
      .confirmation-panel {
        display: flex;
        flex-direction: column;
        gap: var(--space-4);
        padding: var(--space-5);
        border: 1px solid var(--color-border);
        border-radius: var(--radius-lg);
        background: color-mix(in srgb, var(--color-surface-soft) 92%, transparent);
      }

      .confirmation-panel h4,
      .confirmation-panel p {
        margin: 0;
      }

      .confirmation-grid {
        display: grid;
        gap: var(--space-4);
        grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
      }

      .confirmation-item {
        display: flex;
        flex-direction: column;
        gap: var(--space-2);
      }

      .confirmation-actions {
        display: flex;
        align-items: center;
        gap: var(--space-3);
        flex-wrap: wrap;
      }

      .feedback--error {
        color: var(--color-danger);
      }
    `,
  ],
})
export class AssignmentConfirmationPanelComponent {
  readonly service = input.required<WaitingAssignmentServiceSummary>();
  readonly candidate = input.required<OperarioCandidateSummary>();
  readonly submitting = input(false);
  readonly errorMessage = input('');
  readonly confirm = output<void>();
  readonly cancel = output<void>();
}
