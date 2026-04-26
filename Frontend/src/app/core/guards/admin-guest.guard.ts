import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

import { AuthService } from '../auth/auth.service';

export const adminGuestGuard: CanActivateFn = async () => {
  const authService = inject(AuthService);
  const router = inject(Router);

  const user = await authService.ensureUserLoaded();
  if (user?.role === 'ADMINISTRADOR') {
    return router.createUrlTree(['/admin/dashboard']);
  }

  return true;
};
