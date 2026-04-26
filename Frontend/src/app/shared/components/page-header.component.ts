import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, input } from '@angular/core';

@Component({
  selector: 'app-page-header',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <header class="page-header">
      <div>
        @if (eyebrow()) {
          <p class="page-header__eyebrow">{{ eyebrow() }}</p>
        }
        <h1 class="page-header__title">{{ title() }}</h1>
        @if (subtitle()) {
          <p class="page-header__subtitle">{{ subtitle() }}</p>
        }
      </div>

      <div class="page-header__actions">
        <ng-content select="[page-actions]"></ng-content>
      </div>
    </header>
  `,
  styles: [
    `
      .page-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: var(--space-4);
        flex-wrap: wrap;
      }

      .page-header__eyebrow {
        margin: 0 0 0.4rem;
        color: var(--color-primary);
        font-size: 0.76rem;
        font-weight: 700;
        letter-spacing: 0.16em;
        text-transform: uppercase;
      }

      .page-header__title {
        margin: 0;
        font-size: clamp(1.7rem, 2vw, 2.2rem);
        line-height: 1.04;
      }

      .page-header__subtitle {
        margin: 0.65rem 0 0;
        max-width: 65ch;
        color: var(--color-text-muted);
        line-height: 1.5;
      }

      .page-header__actions {
        display: flex;
        align-items: center;
        gap: var(--space-3);
      }
    `,
  ],
})
export class PageHeaderComponent {
  readonly eyebrow = input<string>('');
  readonly title = input.required<string>();
  readonly subtitle = input<string>('');
}
