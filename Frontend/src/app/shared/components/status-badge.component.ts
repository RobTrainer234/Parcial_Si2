import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

import { localizeStatusLabel } from '../utils/user-facing-text';

const SUCCESS_VALUES = new Set(['DISPONIBLE', 'PAGADO', 'CONFIRMADO', 'ACEPTADA']);
const WARNING_VALUES = new Set(['PENDIENTE', 'EN_SERVICIO', 'EN_CAMINO', 'ESPERANDO_REPUESTOS']);
const DANGER_VALUES = new Set(['RECHAZADA', 'EXPIRADA', 'FALLIDA', 'BAJA']);
const INFO_VALUES = new Set(['ASIGNADO', 'EN_SITIO', 'EN_REPARACION', 'DIAGNOSTICADO']);

@Component({
  selector: 'app-status-badge',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <span class="badge" [class]="'badge badge--' + tone()">
      {{ localizedLabel() }}
    </span>
  `,
})
export class StatusBadgeComponent {
  readonly label = input<string | null>(null);
  protected readonly localizedLabel = computed(() =>
    localizeStatusLabel(this.label()),
  );

  protected readonly tone = computed(() => {
    const normalizedLabel = (this.label() ?? '').trim().toUpperCase();

    if (SUCCESS_VALUES.has(normalizedLabel)) {
      return 'success';
    }
    if (WARNING_VALUES.has(normalizedLabel)) {
      return 'warning';
    }
    if (DANGER_VALUES.has(normalizedLabel)) {
      return 'danger';
    }
    if (INFO_VALUES.has(normalizedLabel)) {
      return 'info';
    }
    return 'neutral';
  });
}
