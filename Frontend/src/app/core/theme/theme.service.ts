import { DOCUMENT } from '@angular/common';
import { Injectable, computed, effect, inject, signal } from '@angular/core';

import { Theme } from './theme.models';

const THEME_STORAGE_KEY = 'si2_admin_theme';

@Injectable({ providedIn: 'root' })
export class ThemeService {
  private readonly document = inject(DOCUMENT);
  private readonly currentThemeSignal = signal<Theme>(this.resolveInitialTheme());

  readonly currentTheme = computed(() => this.currentThemeSignal());

  constructor() {
    effect(() => {
      const theme = this.currentThemeSignal();
      this.document.documentElement.setAttribute('data-theme', theme);
      localStorage.setItem(THEME_STORAGE_KEY, theme);
    });
  }

  setTheme(theme: Theme): void {
    this.currentThemeSignal.set(theme);
  }

  toggleTheme(): void {
    this.currentThemeSignal.update((theme) => (theme === 'dark' ? 'light' : 'dark'));
  }

  getCurrentTheme(): Theme {
    return this.currentThemeSignal();
  }

  private resolveInitialTheme(): Theme {
    const storedTheme = localStorage.getItem(THEME_STORAGE_KEY);
    return storedTheme === 'light' ? 'light' : 'dark';
  }
}
