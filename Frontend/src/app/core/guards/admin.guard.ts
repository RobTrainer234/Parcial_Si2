import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

import { AuthService } from '../auth/auth.service';

const ALLOWED_ROLES = ['ADMINISTRADOR', 'ADMIN_SUCURSAL', 'ADMIN_GERENTE_SUCURSALES'];

export const adminGuard: CanActivateFn = async () => {
  const authService = inject(AuthService);
  const router = inject(Router);

  const user = await authService.ensureUserLoaded();
  const role = user?.role ?? user?.tipo_usuario ?? '';
  if (ALLOWED_ROLES.includes(role)) {
    return true;
  }

  authService.logout();
  return router.createUrlTree(['/login']);
};
