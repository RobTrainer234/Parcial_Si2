import { ChangeDetectionStrategy, Component, input } from '@angular/core';

@Component({
  selector: 'app-loading-state',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="state state--loading" role="status" aria-live="polite">
      <span class="state__spinner" aria-hidden="true"></span>
      <div>
        <strong>{{ title() }}</strong>
        <p>{{ message() }}</p>
      </div>
    </div>
  `,
  styles: [
    `
      .state {
        display: flex;
        align-items: center;
        gap: var(--space-4);
        padding: var(--space-6);
        border: 1px dashed var(--color-border);
        border-radius: var(--radius-lg);
        background: color-mix(in srgb, var(--color-surface) 88%, transparent);
      }

      .state strong,
      .state p {
        margin: 0;
      }

      .state p {
        margin-top: 0.3rem;
        color: var(--color-text-muted);
      }

      .state__spinner {
        width: 1.15rem;
        height: 1.15rem;
        border-radius: 50%;
        border: 2px solid color-mix(in srgb, var(--color-primary) 20%, var(--color-border));
        border-top-color: var(--color-primary);
        animation: spin 0.9s linear infinite;
      }

      @keyframes spin {
        to {
          transform: rotate(360deg);
        }
      }
    `,
  ],
})
export class LoadingStateComponent {
  readonly title = input<string>('Cargando');
  readonly message = input<string>('Consultando información del sistema.');
}
