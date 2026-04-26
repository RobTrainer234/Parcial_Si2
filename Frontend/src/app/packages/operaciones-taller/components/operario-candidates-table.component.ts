import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
} from '@angular/core';

import { EmptyStateComponent } from '../../../shared/components/empty-state.component';
import { LoadingStateComponent } from '../../../shared/components/loading-state.component';
import { StatusBadgeComponent } from '../../../shared/components/status-badge.component';
import { OperarioCandidateSummary } from '../data-access/workshop-assignment.models';

@Component({
  selector: 'app-operario-candidates-table',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    CommonModule,
    LoadingStateComponent,
    EmptyStateComponent,
    StatusBadgeComponent,
  ],
  template: `
    @if (loading()) {
      <app-loading-state
        title="Cargando candidatos"
        message="Consultando operarios compatibles para el servicio seleccionado."
      />
    } @else if (errorMessage()) {
      <div class="feedback feedback--error">{{ errorMessage() }}</div>
    } @else if (!candidates().length) {
      <app-empty-state
        title="Sin candidatos disponibles"
        message="No hay operarios compatibles o disponibles para este servicio en este momento."
      />
    } @else {
      <div class="candidate-list">
        @for (candidate of candidates(); track candidate.id_persona_operario) {
          <article class="candidate-item">
            <div class="candidate-item__main">
              <div class="candidate-item__heading">
                <strong>{{ candidate.nombre_completo }}</strong>
                <app-status-badge [label]="candidate.estado_disponibilidad" />
                @if (candidate.recommended) {
                  <span class="badge badge--success">Compatible</span>
                }
              </div>

              <div class="candidate-item__summary">
                <div class="candidate-item__field">
                  <span class="text-muted">Operario</span>
                  <strong>#{{ candidate.id_persona_operario }}</strong>
                </div>
                <div class="candidate-item__field">
                  <span class="text-muted">Especialidad</span>
                  <strong>{{ candidate.matched_specialty.nombre }}</strong>
                </div>
                <div class="candidate-item__field">
                  <span class="text-muted">Experiencia</span>
                  <strong>{{ candidate.anios_experiencia }} año(s)</strong>
                </div>
              </div>

              <p class="candidate-item__reason text-muted">
                {{ candidate.match_reason }}
              </p>

              @if (candidate.certificacion_url) {
                <a
                  class="candidate-item__link"
                  [href]="candidate.certificacion_url"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Ver certificacion
                </a>
              }
            </div>

            <div class="candidate-item__actions">
              <button
                type="button"
                class="app-button"
                [disabled]="!isValidCandidate(candidate)"
                (click)="onAssign(candidate)"
              >
                Asignar
              </button>
              @if (!isValidCandidate(candidate)) {
                <small class="text-muted text-block">No disponible para asignación</small>
              }
            </div>
          </article>
        }
      </div>
    }
  `,
  styles: [
    `
      .candidate-list {
        display: flex;
        flex-direction: column;
        gap: var(--space-4);
      }

      .candidate-item {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: var(--space-5);
        padding: var(--space-5);
        border: 1px solid var(--color-border);
        border-radius: var(--radius-lg);
        background: color-mix(in srgb, var(--color-surface-soft) 92%, transparent);
      }

      .candidate-item__main {
        min-width: 0;
        flex: 1;
      }

      .candidate-item__heading {
        display: flex;
        align-items: center;
        gap: var(--space-3);
        flex-wrap: wrap;
      }

      .candidate-item__summary {
        display: grid;
        gap: var(--space-4);
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        margin-top: var(--space-4);
      }

      .candidate-item__field {
        display: flex;
        flex-direction: column;
        gap: var(--space-2);
      }

      .candidate-item__reason {
        margin: var(--space-4) 0 0;
      }

      .candidate-item__link {
        display: inline-block;
        margin-top: var(--space-3);
        color: var(--color-primary);
        text-decoration: none;
      }

      .candidate-item__link:hover {
        text-decoration: underline;
      }

      .candidate-item__actions {
        min-width: 140px;
      }

      .feedback {
        font-size: 0.9rem;
      }

      .feedback--error {
        color: var(--color-danger);
      }

      @media (max-width: 860px) {
        .candidate-item {
          flex-direction: column;
        }

        .candidate-item__actions {
          min-width: 0;
          width: 100%;
        }
      }

      .text-block {
        display: block;
        margin-top: var(--space-2);
      }
    `,
  ],
})
export class OperarioCandidatesTableComponent {
  readonly candidates = input<OperarioCandidateSummary[]>([]);
  readonly loading = input(false);
  readonly errorMessage = input('');
  readonly assign = output<OperarioCandidateSummary>();

  protected isValidCandidate(candidate: OperarioCandidateSummary): boolean {
    return (
      Number.isInteger(candidate.id_persona_operario) &&
      candidate.id_persona_operario > 0 &&
      candidate.estado_disponibilidad === 'DISPONIBLE'
    );
  }

  protected onAssign(candidate: OperarioCandidateSummary): void {
    if (this.isValidCandidate(candidate)) {
      this.assign.emit(candidate);
    }
  }
}
