import { Injectable, computed, signal } from '@angular/core';

export type WebOfflineIncidentStatus =
  | 'PENDIENTE_SYNC'
  | 'SINCRONIZANDO'
  | 'SINCRONIZADO'
  | 'ERROR_SYNC';

export interface WebOfflineIncidentQueueEntry {
  local_uuid: string;
  description: string;
  status: WebOfflineIncidentStatus;
  created_at_local: string;
  last_error: string | null;
  server_incident_id: number | null;
}

const STORAGE_KEY = 'admin_web_offline_incident_queue_demo_v1';

@Injectable({ providedIn: 'root' })
export class WebOfflineIncidentQueueService {
  // Minimal defensive queue for admin/PWA contexts only.
  // The primary offline incident reporting flow lives in the Flutter client app.
  private readonly _entries = signal<WebOfflineIncidentQueueEntry[]>(this.readStorage());

  readonly entries = computed(() => this._entries());
  readonly pendingCount = computed(
    () => this._entries().filter((entry) => entry.status !== 'SINCRONIZADO').length,
  );

  addDemoEntry(): void {
    const entry: WebOfflineIncidentQueueEntry = {
      local_uuid: this.generateLocalUuid(),
      description: 'Reporte offline de demostracion desde la web admin.',
      status: 'PENDIENTE_SYNC',
      created_at_local: new Date().toISOString(),
      last_error: null,
      server_incident_id: null,
    };
    this.persist([entry, ...this._entries()]);
  }

  simulateSync(): void {
    const entries = [...this._entries()];
    const index = entries.findIndex((entry) => entry.status !== 'SINCRONIZADO');
    if (index < 0) return;
    const current = entries[index];
    entries[index] = {
      ...current,
      status: 'SINCRONIZANDO',
      last_error: null,
    };
    this.persist(entries);

    queueMicrotask(() => {
      const synced = [...this._entries()];
      const updated = synced[index];
      if (!updated) return;
      synced[index] = {
        ...updated,
        status: 'SINCRONIZADO',
        server_incident_id: updated.server_incident_id ?? Date.now(),
      };
      this.persist(synced);
    });
  }

  simulateError(): void {
    const entries = [...this._entries()];
    const index = entries.findIndex(
      (entry) => entry.status === 'PENDIENTE_SYNC' || entry.status === 'SINCRONIZANDO',
    );
    if (index < 0) return;
    entries[index] = {
      ...entries[index],
      status: 'ERROR_SYNC',
      last_error: 'Demostracion web: la sincronizacion requiere reintento manual.',
    };
    this.persist(entries);
  }

  private persist(entries: WebOfflineIncidentQueueEntry[]): void {
    this._entries.set(entries);
    if (typeof localStorage === 'undefined') return;
    localStorage.setItem(STORAGE_KEY, JSON.stringify(entries));
  }

  private readStorage(): WebOfflineIncidentQueueEntry[] {
    if (typeof localStorage === 'undefined') return [];
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    try {
      const parsed = JSON.parse(raw);
      if (!Array.isArray(parsed)) return [];
      return parsed.filter(isQueueEntry);
    } catch {
      return [];
    }
  }

  private generateLocalUuid(): string {
    const segment = (size: number) =>
      Array.from({ length: size }, () => Math.floor(Math.random() * 16).toString(16)).join('');
    return `${segment(8)}-${segment(4)}-${segment(4)}-${segment(4)}-${segment(12)}`;
  }
}

function isQueueEntry(value: unknown): value is WebOfflineIncidentQueueEntry {
  if (!value || typeof value !== 'object') return false;
  const entry = value as Partial<WebOfflineIncidentQueueEntry>;
  return (
    typeof entry.local_uuid === 'string' &&
    typeof entry.description === 'string' &&
    typeof entry.status === 'string' &&
    typeof entry.created_at_local === 'string'
  );
}
