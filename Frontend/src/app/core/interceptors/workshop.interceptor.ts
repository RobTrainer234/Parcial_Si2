import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';

import { API_BASE_URL } from '../config/api.config';
import { WorkshopSelectionService } from '../auth/workshop-selection.service';

const WORKSHOP_API_PATHS = [
  '/workshop/dashboard',
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

  const params = url.searchParams;
  if (!params.has('workshop_id')) {
    params.set('workshop_id', String(workshopId));
  }

  const newUrl = url.pathname + url.search;
  const cloned = request.clone({ url: newUrl });
  return next(cloned);
};
