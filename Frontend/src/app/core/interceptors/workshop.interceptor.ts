import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';

import { API_BASE_URL } from '../config/api.config';
import { WorkshopSelectionService } from '../auth/workshop-selection.service';

const WORKSHOP_API_PATHS = [
  '/workshop/dashboard',
  '/workshop/reports',
  '/workshop/profile',
  '/workshop/catalog',
  '/workshop/staff',
  '/workshop/requests',
  '/workshop/services',
];

export const workshopInterceptor: HttpInterceptorFn = (request, next) => {
  const workshopSelection = inject(WorkshopSelectionService);

  if (!workshopSelection.isGerente()) {
    return next(request);
  }

  const workshopId = workshopSelection.selectedWorkshopId();
  if (workshopId === null) {
    return next(request);
  }

  const isBackendRequest = request.url.startsWith(API_BASE_URL) || request.url.startsWith('/');
  if (!isBackendRequest) {
    return next(request);
  }

  const url = new URL(request.url, window.location.origin);
  const shouldAddWorkshopId = WORKSHOP_API_PATHS.some((path) => url.pathname.includes(path));

  if (!shouldAddWorkshopId) {
    return next(request);
  }

  if (request.params.has('workshop_id') || url.searchParams.has('workshop_id')) {
    return next(request);
  }

  const cloned = request.clone({
    params: request.params.set('workshop_id', String(workshopId)),
  });
  return next(cloned);
};
