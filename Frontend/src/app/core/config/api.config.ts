function resolveApiBaseUrl(): string {
  if (typeof window === 'undefined') {
    return 'http://127.0.0.1:8000';
  }

  const { hostname, port } = window.location;
  const normalizedHostname = hostname.toLowerCase();
  const isAngularDevServer =
    (normalizedHostname === 'localhost' || normalizedHostname === '127.0.0.1') &&
    port === '4200';

  if (normalizedHostname.includes('parcial-si2-1.onrender.com')) {
    return 'https://parcial-si2.onrender.com';
  }

  if (isAngularDevServer) {
    return 'http://127.0.0.1:8000';
  }

  return '/api';
}

export const API_BASE_URL = resolveApiBaseUrl();

export function buildApiUrl(path: string): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  const normalizedBaseUrl = API_BASE_URL.endsWith('/')
    ? API_BASE_URL.slice(0, -1)
    : API_BASE_URL;
  return `${normalizedBaseUrl}${normalizedPath}`;
}
