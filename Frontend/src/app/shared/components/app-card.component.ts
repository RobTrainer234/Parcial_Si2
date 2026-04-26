import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, input } from '@angular/core';

@Component({
  selector: 'app-card',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="app-card">
      @if (title() || subtitle()) {
        <header class="app-card__header">
          @if (title()) {
            <h3 class="app-card__title">{{ title() }}</h3>
          }
          @if (subtitle()) {
            <p class="app-card__subtitle">{{ subtitle() }}</p>
          }
        </header>
      }

      <div class="app-card__body">
        <ng-content></ng-content>
      </div>
    </section>
  `,
  styles: [
    `
      .app-card {
        border: 1px solid var(--color-border);
        border-radius: var(--radius-lg);
        background: var(--color-surface);
        box-shadow: var(--shadow-card);
      }

      .app-card__header {
        padding: var(--space-5) var(--space-6) 0;
      }

      .app-card__title {
        margin: 0;
        font-size: 1rem;
      }

      .app-card__subtitle {
        margin: 0.45rem 0 0;
        color: var(--color-text-muted);
        font-size: 0.92rem;
      }

      .app-card__body {
        padding: var(--space-5) var(--space-6) var(--space-6);
      }
    `,
  ],
})
export class AppCardComponent {
  readonly title = input<string>('');
  readonly subtitle = input<string>('');
}
