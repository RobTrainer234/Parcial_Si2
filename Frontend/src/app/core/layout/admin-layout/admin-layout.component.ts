import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { Router, RouterOutlet } from '@angular/router';

import { AuthService } from '../../auth/auth.service';
import { AdminSidebarComponent } from '../sidebar/admin-sidebar.component';
import { AdminTopbarComponent } from '../topbar/admin-topbar.component';

@Component({
  selector: 'app-admin-layout',
  standalone: true,
  imports: [CommonModule, RouterOutlet, AdminSidebarComponent, AdminTopbarComponent],
  template: `
    <div class="layout">
      <aside class="layout__sidebar">
        <app-admin-sidebar />
      </aside>

      <main class="layout__main">
        <app-admin-topbar (logout)="logout()" />

        <section class="layout__content">
          <router-outlet />
        </section>
      </main>
    </div>
  `,
  styles: [
    `
      :host {
        display: block;
        min-height: 100vh;
      }

      .layout {
        display: grid;
        grid-template-columns: 300px 1fr;
        min-height: 100vh;
        gap: var(--space-6);
        padding: var(--space-6);
      }

      .layout__sidebar {
        min-width: 0;
      }

      .layout__main {
        min-width: 0;
        display: flex;
        flex-direction: column;
        gap: var(--space-6);
      }

      .layout__content {
        min-width: 0;
      }

      @media (max-width: 1024px) {
        .layout {
          grid-template-columns: 1fr;
        }
      }
    `,
  ],
})
export class AdminLayoutComponent {
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);

  protected logout(): void {
    this.authService.logout();
    void this.router.navigate(['/login']);
  }
}
