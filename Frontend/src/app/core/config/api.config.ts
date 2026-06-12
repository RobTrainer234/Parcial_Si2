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

export function buildWebSocketUrl(
  path: string,
  query: Record<string, string | number | null | undefined> = {},
): string {
  const normalizedBaseCandidate =
    API_BASE_URL.startsWith('http://') || API_BASE_URL.startsWith('https://')
      ? API_BASE_URL
      : (typeof window !== 'undefined' ? window.location.origin : 'http://127.0.0.1');
  const wsBaseUrl = new URL(
    normalizedBaseCandidate,
    typeof window !== 'undefined' ? window.location.origin : 'http://127.0.0.1',
  );
  wsBaseUrl.protocol = wsBaseUrl.protocol === 'https:' ? 'wss:' : 'ws:';
  const baseSegments = wsBaseUrl.pathname
    .split('/')
    .filter((segment) => segment.length > 0);
  if (baseSegments.at(-1)?.toLowerCase() === 'api') {
    baseSegments.pop();
  }
  const targetSegments = [
    ...baseSegments,
    ...path.split('/').filter((segment) => segment.length > 0),
  ];
  wsBaseUrl.pathname = `/${targetSegments.join('/')}`;
  Object.entries(query).forEach(([key, value]) => {
    if (value !== null && value !== undefined && String(value).trim() !== '') {
      wsBaseUrl.searchParams.set(key, String(value));
    }
  });
  return wsBaseUrl.toString();
}
