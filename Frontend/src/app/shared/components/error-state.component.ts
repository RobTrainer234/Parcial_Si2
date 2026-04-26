import { ChangeDetectionStrategy, Component, input } from '@angular/core';

@Component({
  selector: 'app-error-state',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="state">
      <strong>{{ title() }}</strong>
      <p>{{ message() }}</p>
      <div class="state__actions">
        <ng-content select="[error-actions]"></ng-content>
      </div>
    </div>
  `,
  styles: [
    `
      .state {
        padding: var(--space-6);
        border: 1px solid color-mix(in srgb, var(--color-danger) 35%, var(--color-border));
        border-radius: var(--radius-lg);
        background: color-mix(in srgb, var(--color-danger) 10%, var(--color-surface));
      }

      strong,
      p {
        margin: 0;
      }

      p {
        margin-top: 0.4rem;
        color: var(--color-text-muted);
      }

      .state__actions {
        margin-top: var(--space-4);
      }
    `,
  ],
})
export class ErrorStateComponent {
  readonly title = input<string>('No se pudo cargar la información');
  readonly message = input<string>('Reintenta la operación en unos instantes.');
}
