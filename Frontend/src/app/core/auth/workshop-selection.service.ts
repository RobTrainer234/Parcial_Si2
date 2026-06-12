import { Injectable, computed, inject, signal } from '@angular/core';
import { AuthService } from './auth.service';

const STORAGE_KEY = 'selected_workshop_id';

@Injectable({ providedIn: 'root' })
export class WorkshopSelectionService {
  private readonly authService = inject(AuthService);

  private readonly selectedId = signal<number | null>(this.restoreSelection());

  readonly selectedWorkshopId = computed(() => this.selectedId());
  readonly isGerente = computed(() => this.authService.isGerente());

  selectWorkshop(workshopId: number | null): void {
    this.selectedId.set(workshopId);
    if (workshopId !== null) {
      localStorage.setItem(STORAGE_KEY, String(workshopId));
    } else {
      localStorage.removeItem(STORAGE_KEY);
    }
  }

  private restoreSelection(): number | null {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored ? Number(stored) : null;
  }
}
