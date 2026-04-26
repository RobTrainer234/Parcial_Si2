import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { ActivatedRoute } from '@angular/router';

import { AppCardComponent } from '../../shared/components/app-card.component';
import { EmptyStateComponent } from '../../shared/components/empty-state.component';
import { PageHeaderComponent } from '../../shared/components/page-header.component';

@Component({
  selector: 'app-admin-placeholder-page',
  standalone: true,
  imports: [CommonModule, PageHeaderComponent, AppCardComponent, EmptyStateComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="page">
      <app-page-header
        eyebrow="Base administrativa"
        [title]="title"
        [subtitle]="subtitle"
      />

      <app-card title="Módulo reservado">
        <app-empty-state
          title="Vista aún no implementada"
          message="La navegación ya está preparada para este módulo del taller. El siguiente paso es conectar la vista con su endpoint real."
        />
      </app-card>
    </div>
  `,
})
export class AdminPlaceholderPageComponent {
  private readonly route = inject(ActivatedRoute);

  protected readonly title =
    this.route.snapshot.data['title'] ?? 'Módulo administrativo';
  protected readonly subtitle =
    this.route.snapshot.data['subtitle'] ?? 'Vista preparada para expansión incremental.';
}
