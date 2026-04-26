import { Component } from '@angular/core';

import { AdminLayoutComponent } from './admin-layout/admin-layout.component';

@Component({
  selector: 'app-admin-shell',
  standalone: true,
  imports: [AdminLayoutComponent],
  template: `<app-admin-layout />`,
})
export class AdminShellComponent {}
