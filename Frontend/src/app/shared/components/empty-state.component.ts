import { ChangeDetectionStrategy, Component, input } from '@angular/core';

@Component({
  selector: 'app-empty-state',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="state">
      <strong>{{ title() }}</strong>
      <p>{{ message() }}</p>
    </div>
  `,
  styles: [
    `
      .state {
        padding: var(--space-6);
        border: 1px dashed var(--color-border);
        border-radius: var(--radius-lg);
        background: color-mix(in srgb, var(--color-surface-soft) 86%, transparent);
      }

      strong,
      p {
        margin: 0;
      }

      p {
        margin-top: 0.4rem;
        color: var(--color-text-muted);
      }
    `,
  ],
})
export class EmptyStateComponent {
  readonly title = input<string>('Sin datos');
  readonly message = input<string>('No hay información disponible para este módulo.');
}
