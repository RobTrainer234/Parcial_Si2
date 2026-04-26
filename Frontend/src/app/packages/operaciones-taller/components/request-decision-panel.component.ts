import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  effect,
  input,
  output,
  signal,
} from '@angular/core';

export type RequestDecisionMode = 'accept' | 'reject' | null;

@Component({
  selector: 'app-request-decision-panel',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CommonModule],
  template: `
    @if (mode() === 'accept') {
      <section class="decision-panel">
        <h4>Aceptar solicitud</h4>
        <p class="text-muted">
          Al aceptar, el sistema generara la pre-cotizacion tecnica usando el catalogo del taller.
        </p>

        @if (errorMessage()) {
          <p class="feedback feedback--error">{{ errorMessage() }}</p>
        }

        <div class="decision-actions">
          <button
            type="button"
            class="app-button"
            (click)="confirmAccept.emit()"
            [disabled]="submitting()"
          >
            {{ submitting() ? 'Procesando...' : 'Confirmar aceptacion' }}
          </button>
          <button
            type="button"
            class="app-button app-button--secondary"
            (click)="onCancel()"
            [disabled]="submitting()"
          >
            Cancelar
          </button>
        </div>
      </section>
    } @else if (mode() === 'reject') {
      <section class="decision-panel">
        <h4>Rechazar solicitud</h4>
        <label class="app-field">
          <span class="app-field__label">Motivo del rechazo</span>
          <textarea
            class="app-textarea"
            rows="4"
            [value]="reason()"
            [disabled]="submitting()"
            placeholder="Explica por que el taller no puede atender esta solicitud."
            (input)="reason.set(asTextareaValue($event))"
          ></textarea>
        </label>

        @if (validationMessage()) {
          <p class="feedback feedback--error">{{ validationMessage() }}</p>
        } @else if (errorMessage()) {
          <p class="feedback feedback--error">{{ errorMessage() }}</p>
        }

        <div class="decision-actions">
          <button
            type="button"
            class="app-button"
            (click)="submitReject()"
            [disabled]="submitting()"
          >
            {{ submitting() ? 'Procesando...' : 'Confirmar rechazo' }}
          </button>
          <button
            type="button"
            class="app-button app-button--secondary"
            (click)="onCancel()"
            [disabled]="submitting()"
          >
            Cancelar
          </button>
        </div>
      </section>
    }
  `,
  styles: [
    `
      .decision-panel {
        display: flex;
        flex-direction: column;
        gap: var(--space-4);
        padding: var(--space-5);
        border-radius: var(--radius-lg);
        border: 1px solid var(--color-border);
        background: color-mix(in srgb, var(--color-surface-soft) 92%, transparent);
      }

      .decision-panel h4 {
        margin: 0;
      }

      .decision-panel p {
        margin: 0;
      }

      .decision-actions {
        display: flex;
        align-items: center;
        gap: var(--space-3);
        flex-wrap: wrap;
      }

      .feedback {
        font-size: 0.88rem;
        line-height: 1.4;
      }

      .feedback--error {
        color: var(--color-danger);
      }
    `,
  ],
})
export class RequestDecisionPanelComponent {
  readonly mode = input<RequestDecisionMode>(null);
  readonly submitting = input(false);
  readonly errorMessage = input('');
  readonly confirmAccept = output<void>();
  readonly confirmReject = output<string>();
  readonly cancel = output<void>();

  protected readonly reason = signal('');
  protected readonly validationMessage = signal('');

  constructor() {
    effect(() => {
      const activeMode = this.mode();
      if (activeMode !== 'reject') {
        this.reason.set('');
        this.validationMessage.set('');
      }
    });
  }

  protected asTextareaValue(event: Event): string {
    this.validationMessage.set('');
    return (event.target as HTMLTextAreaElement | null)?.value ?? '';
  }

  protected onCancel(): void {
    this.reason.set('');
    this.validationMessage.set('');
    this.cancel.emit();
  }

  protected submitReject(): void {
    const trimmed = this.reason().trim();
    if (trimmed.length < 5) {
      this.validationMessage.set(
        'Ingresa un motivo valido de al menos 5 caracteres.',
      );
      return;
    }

    this.validationMessage.set('');
    this.confirmReject.emit(trimmed);
    this.reason.set('');
  }
}
