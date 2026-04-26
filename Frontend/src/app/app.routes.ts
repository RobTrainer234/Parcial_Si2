import { Routes } from '@angular/router';

import { adminGuestGuard } from './core/guards/admin-guest.guard';
import { adminGuard } from './core/guards/admin.guard';
import { authGuard } from './core/guards/auth.guard';

export const routes: Routes = [
  {
    path: '',
    pathMatch: 'full',
    redirectTo: 'login',
  },
  {
    path: 'login',
    canActivate: [adminGuestGuard],
    loadComponent: () =>
      import('./packages/seguridad-usuarios/pages/admin-login.page').then(
        (m) => m.AdminLoginPage,
      ),
  },
  {
    path: 'admin',
    canActivate: [authGuard, adminGuard],
    loadComponent: () =>
      import('./core/layout/admin-shell.component').then(
        (m) => m.AdminShellComponent,
      ),
    children: [
      {
        path: '',
        pathMatch: 'full',
        redirectTo: 'dashboard',
      },
      {
        path: 'dashboard',
        loadComponent: () =>
          import('./packages/operaciones-taller/pages/admin-dashboard.page').then(
            (m) => m.AdminDashboardPage,
          ),
      },
      {
        path: 'workshop/profile',
        loadComponent: () =>
          import('./core/layout/admin-placeholder-page.component').then(
            (m) => m.AdminPlaceholderPageComponent,
          ),
        data: {
          title: 'Perfil del taller',
          subtitle: 'Espacio preparado para la configuración operativa y comercial del taller.',
        },
      },
      {
        path: 'workshop/catalog',
        loadComponent: () =>
          import('./core/layout/admin-placeholder-page.component').then(
            (m) => m.AdminPlaceholderPageComponent,
          ),
        data: {
          title: 'Catálogo de servicios',
          subtitle: 'Aquí se mostrará la administración de servicios base y precios referenciales.',
        },
      },
      {
        path: 'workshop/staff',
        loadComponent: () =>
          import('./core/layout/admin-placeholder-page.component').then(
            (m) => m.AdminPlaceholderPageComponent,
          ),
        data: {
          title: 'Operarios del taller',
          subtitle: 'Vista reservada para gestión de disponibilidad, perfiles y capacidad operativa.',
        },
      },
      {
        path: 'requests',
        loadComponent: () =>
          import('./core/layout/admin-placeholder-page.component').then(
            (m) => m.AdminPlaceholderPageComponent,
          ),
        data: {
          title: 'Solicitudes de auxilio',
          subtitle: 'La navegación queda lista para seguimiento y decisión de solicitudes.',
        },
      },
      {
        path: 'services/waiting-assignment',
        loadComponent: () =>
          import('./core/layout/admin-placeholder-page.component').then(
            (m) => m.AdminPlaceholderPageComponent,
          ),
        data: {
          title: 'Asignaciones pendientes',
          subtitle: 'Módulo preparado para coordinar operarios y servicios aceptados.',
        },
      },
      {
        path: 'audit',
        loadComponent: () =>
          import('./core/layout/admin-placeholder-page.component').then(
            (m) => m.AdminPlaceholderPageComponent,
          ),
        data: {
          title: 'Auditoría y trazabilidad',
          subtitle: 'Vista reservada para los registros de bitácora y seguimiento de eventos del taller.',
        },
      },
      {
        path: 'notifications',
        loadComponent: () =>
          import('./core/layout/admin-placeholder-page.component').then(
            (m) => m.AdminPlaceholderPageComponent,
          ),
        data: {
          title: 'Notificaciones',
          subtitle: 'Espacio listo para bandeja administrativa y alertas operativas del taller.',
        },
      },
    ],
  },
  {
    path: '**',
    redirectTo: 'login',
  },
];
