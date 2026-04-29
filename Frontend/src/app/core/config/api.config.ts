function resolveApiBaseUrl(): string {
  if (typeof window === 'undefined') {
    return 'http://127.0.0.1:8000';
  }

  const { hostname, port } = window.location;
  const isAngularDevServer =
    (hostname === 'localhost' || hostname === '127.0.0.1') && port === '4200';

  if (isAngularDevServer) {
    return 'http://127.0.0.1:8000';
  }

  return '/api';
}

export const API_BASE_URL = resolveApiBaseUrl();

export function buildApiUrl(path: string): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${API_BASE_URL}${normalizedPath}`;
}
