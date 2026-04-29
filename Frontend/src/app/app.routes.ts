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
          import('./packages/operaciones-taller/pages/workshop-profile.page').then(
            (m) => m.WorkshopProfilePage,
          ),
      },
      {
        path: 'workshop/catalog',
        loadComponent: () =>
          import('./packages/operaciones-taller/pages/workshop-catalog.page').then(
            (m) => m.WorkshopCatalogPage,
          ),
      },
      {
        path: 'workshop/staff',
        loadComponent: () =>
          import('./packages/operaciones-taller/pages/workshop-staff.page').then(
            (m) => m.WorkshopStaffPage,
          ),
      },
      {
        path: 'requests',
        loadComponent: () =>
          import('./packages/operaciones-taller/pages/pending-requests.page').then(
            (m) => m.PendingRequestsPage,
          ),
      },
      {
        path: 'requests/:requestId',
        loadComponent: () =>
          import('./packages/operaciones-taller/pages/request-detail.page').then(
            (m) => m.RequestDetailPage,
          ),
      },
      {
        path: 'services/waiting-assignment',
        loadComponent: () =>
          import('./packages/operaciones-taller/pages/waiting-assignment.page').then(
            (m) => m.WaitingAssignmentPage,
          ),
      },
      {
        path: 'services',
        loadComponent: () =>
          import('./packages/operaciones-taller/pages/service-history.page').then(
            (m) => m.ServiceHistoryPage,
          ),
      },
      {
        path: 'audit',
        loadComponent: () =>
          import('./packages/reputacion-auditoria/pages/audit-log.page').then(
            (m) => m.AuditLogPage,
          ),
      },
      {
        path: 'services/:serviceId/timeline',
        loadComponent: () =>
          import('./packages/reputacion-auditoria/pages/service-timeline.page').then(
            (m) => m.ServiceTimelinePage,
          ),
      },
      {
        path: 'notifications',
        loadComponent: () =>
          import('./packages/gestion-auxilio/pages/notifications.page').then(
            (m) => m.NotificationsPage,
          ),
      },
      {
        path: 'account/profile',
        loadComponent: () =>
          import('./packages/seguridad-usuarios/pages/user-profile.page').then(
            (m) => m.UserProfilePage,
          ),
      },
    ],
  },
  {
    path: '**',
    redirectTo: 'login',
  },
];
