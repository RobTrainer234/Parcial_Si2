import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, input } from '@angular/core';

@Component({
  selector: 'app-metric-card',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="metric-card">
      <span class="metric-card__label">{{ label() }}</span>
      <strong class="metric-card__value">{{ value() }}</strong>
      @if (hint()) {
        <p class="metric-card__hint">{{ hint() }}</p>
      }
    </section>
  `,
  styles: [
    `
      .metric-card {
        padding: var(--space-5);
        border: 1px solid var(--color-border);
        border-radius: var(--radius-lg);
        background:
          linear-gradient(
            180deg,
            color-mix(in srgb, var(--color-primary) 6%, var(--color-surface)) 0%,
            var(--color-surface) 100%
          );
        box-shadow: var(--shadow-card);
      }

      .metric-card__label {
        display: block;
        color: var(--color-text-muted);
        font-size: 0.86rem;
        letter-spacing: 0.03em;
        text-transform: uppercase;
      }

      .metric-card__value {
        display: block;
        margin-top: 0.75rem;
        font-size: clamp(1.55rem, 2vw, 2rem);
        line-height: 1;
      }

      .metric-card__hint {
        margin: 0.7rem 0 0;
        color: var(--color-text-soft);
        font-size: 0.88rem;
      }
    `,
  ],
})
export class MetricCardComponent {
  readonly label = input.required<string>();
  readonly value = input.required<string>();
  readonly hint = input<string>('');
}
