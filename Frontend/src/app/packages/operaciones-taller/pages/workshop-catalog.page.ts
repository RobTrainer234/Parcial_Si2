import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  computed,
  inject,
  signal,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';

import { AppCardComponent } from '../../../shared/components/app-card.component';
import { EmptyStateComponent } from '../../../shared/components/empty-state.component';
import { ErrorStateComponent } from '../../../shared/components/error-state.component';
import { LoadingStateComponent } from '../../../shared/components/loading-state.component';
import { PageHeaderComponent } from '../../../shared/components/page-header.component';
import { StatusBadgeComponent } from '../../../shared/components/status-badge.component';
import { WorkshopCatalogApi } from '../data-access/workshop-catalog.api';
import {
  WorkshopCatalogServiceCreateRequest,
  WorkshopCatalogServiceResponse,
  WorkshopCatalogServiceUpdateRequest,
} from '../data-access/workshop-catalog.models';
import { WorkshopProfileApi } from '../data-access/workshop-profile.api';
import { WorkshopConfiguredSpecialty, WorkshopProfileResponse } from '../data-access/workshop-profile.models';

type CatalogFormMode = 'create' | 'edit' | null;

@Component({
  selector: 'app-workshop-catalog-page',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    PageHeaderComponent,
    AppCardComponent,
    EmptyStateComponent,
    ErrorStateComponent,
    LoadingStateComponent,
    StatusBadgeComponent,
  ],
  template: `
    <div class="page">
      <app-page-header
        eyebrow="Precotización técnica"
        title="Catálogo de servicios"
        subtitle="Define servicios y rangos de precio base usados para la pre-cotización técnica."
      >
        <div page-actions class="toolbar toolbar--tight">
          @if (!isFormVisible()) {
            <button
              type="button"
              class="app-button"
              (click)="startCreate()"
              [disabled]="loading() || !hasSpecialties()"
            >
              Agregar servicio
            </button>
          } @else {
            <button
              type="button"
              class="app-button app-button--secondary"
              (click)="cancelForm()"
              [disabled]="saving()"
            >
              Cancelar
            </button>
          }

          <button
            type="button"
            class="app-button app-button--ghost"
            (click)="reload()"
            [disabled]="loading() || saving()"
          >
            {{ loading() ? 'Actualizando...' : 'Actualizar' }}
          </button>
        </div>
      </app-page-header>

      @if (loading() && !catalogItems().length) {
        <app-loading-state
          title="Cargando catálogo"
          message="Consultando servicios base y rangos de precio del taller."
        />
      } @else if (pageError() && !catalogItems().length) {
        <app-error-state [message]="pageError()">
          <button error-actions type="button" class="app-button" (click)="reload()">
            Reintentar
          </button>
        </app-error-state>
      } @else {
        <section class="section-grid catalog-header-grid">
          <app-card
            title="Vista operativa"
            subtitle="Consulta rápida del catálogo activo y control de visibilidad."
          >
            <div class="toolbar">
              <label class="toggle-inline">
                <input
                  type="checkbox"
                  [checked]="includeInactive()"
                  (change)="toggleIncludeInactive($event)"
                />
                <span>Mostrar inactivos</span>
              </label>
              <span class="text-muted">
                {{ catalogItems().length }} servicio(s) visible(s)
              </span>
            </div>

            @if (!hasSpecialties()) {
              <p class="catalog-note feedback feedback--error">
                No hay especialidades configuradas para este taller. Configura el perfil del taller antes de crear servicios.
              </p>
            }
          </app-card>

          <app-card
            title="Especialidades disponibles"
            subtitle="Opciones reales traídas desde el perfil del taller."
          >
            @if (specialties().length) {
              <div class="specialties">
                @for (specialty of specialties(); track specialty.id_especialidad) {
                  <span class="badge badge--info">{{ specialty.nombre }}</span>
                }
              </div>
            } @else {
              <app-empty-state
                title="Sin especialidades configuradas"
                message="El catálogo depende de especialidades reales del taller."
              />
            }
          </app-card>
        </section>

        @if (isFormVisible()) {
          <app-card
            [title]="formMode() === 'create' ? 'Agregar servicio' : 'Editar servicio'"
            [subtitle]="
              formMode() === 'create'
                ? 'Crea un nuevo servicio base con rango de precio referencial.'
                : 'Actualiza el servicio seleccionado manteniendo el catálogo consistente.'
            "
          >
            <form class="catalog-form" [formGroup]="catalogForm" (ngSubmit)="saveCatalogService()">
              <div class="form-grid">
                <label class="app-field">
                  <span class="app-field__label">Especialidad</span>
                  <select class="app-select" formControlName="id_especialidad">
                    <option [ngValue]="null">Selecciona una especialidad</option>
                    @for (specialty of specialties(); track specialty.id_especialidad) {
                      <option [ngValue]="specialty.id_especialidad">
                        {{ specialty.nombre }}
                      </option>
                    }
                  </select>
                  @if (hasError('id_especialidad', 'required')) {
                    <span class="field-error">La especialidad es obligatoria.</span>
                  }
                </label>

                <label class="app-field">
                  <span class="app-field__label">Nombre del servicio</span>
                  <input
                    type="text"
                    class="app-input"
                    formControlName="nombre"
                    placeholder="Cambio de batería, carga de refrigerante, etc."
                  />
                  @if (hasError('nombre', 'required')) {
                    <span class="field-error">El nombre del servicio es obligatorio.</span>
                  }
                </label>

                <label class="app-field app-field--full">
                  <span class="app-field__label">Descripción</span>
                  <textarea
                    class="app-textarea"
                    formControlName="descripcion"
                    rows="4"
                    placeholder="Describe el alcance referencial del servicio."
                  ></textarea>
                </label>

                <label class="app-field">
                  <span class="app-field__label">Precio base mínimo (BOB)</span>
                  <input
                    type="number"
                    step="0.01"
                    class="app-input"
                    formControlName="precio_base_min"
                    placeholder="0.00"
                  />
                  @if (hasError('precio_base_min', 'required')) {
                    <span class="field-error">El precio mínimo es obligatorio.</span>
                  } @else if (hasError('precio_base_min', 'min')) {
                    <span class="field-error">El precio mínimo no puede ser negativo.</span>
                  }
                </label>

                <label class="app-field">
                  <span class="app-field__label">Precio base máximo (BOB)</span>
                  <input
                    type="number"
                    step="0.01"
                    class="app-input"
                    formControlName="precio_base_max"
                    placeholder="0.00"
                  />
                  @if (hasError('precio_base_max', 'required')) {
                    <span class="field-error">El precio máximo es obligatorio.</span>
                  } @else if (hasError('precio_base_max', 'min')) {
                    <span class="field-error">El precio máximo no puede ser negativo.</span>
                  } @else if (catalogForm.hasError('priceRange')) {
                    <span class="field-error">El precio máximo debe ser mayor o igual al mínimo.</span>
                  }
                </label>

                <label class="toggle-field">
                  <input type="checkbox" formControlName="incluye_repuestos_basicos" />
                  <div>
                    <span class="toggle-field__title">Incluye repuestos básicos</span>
                    <span class="toggle-field__hint">
                      Indica si el rango base contempla repuestos menores de referencia.
                    </span>
                  </div>
                </label>
              </div>

              @if (formError()) {
                <p class="feedback feedback--error">{{ formError() }}</p>
              }

              <div class="form-actions">
                <button
                  type="submit"
                  class="app-button"
                  [disabled]="catalogForm.invalid || saving() || !hasSpecialties()"
                >
                  {{
                    saving()
                      ? 'Guardando...'
                      : formMode() === 'create'
                        ? 'Guardar servicio'
                        : 'Guardar cambios'
                  }}
                </button>
                <button
                  type="button"
                  class="app-button app-button--secondary"
                  (click)="cancelForm()"
                  [disabled]="saving()"
                >
                  Cancelar
                </button>
              </div>
            </form>
          </app-card>
        }

        <app-card
          title="Servicios configurados"
          subtitle="Lista de servicios base que el backend usa para cotización y operación."
        >
          @if (catalogItems().length) {
            <div class="catalog-list">
              @for (item of catalogItems(); track item.catalog_id) {
                <article class="catalog-item" [class.catalog-item--inactive]="!item.activo">
                  <div class="catalog-item__main">
                    <div class="catalog-item__heading">
                      <strong>{{ item.nombre }}</strong>
                      <app-status-badge [label]="item.activo ? 'CONFIRMADO' : 'BAJA'" />
                    </div>

                    <div class="catalog-item__meta">
                      <span class="badge badge--info">{{ item.especialidad_nombre }}</span>
                      <span class="badge" [class]="item.incluye_repuestos_basicos ? 'badge badge--success' : 'badge badge--neutral'">
                        {{ item.incluye_repuestos_basicos ? 'Incluye repuestos básicos' : 'Solo mano de obra / referencia' }}
                      </span>
                    </div>

                    <p class="catalog-item__description text-muted">
                      {{ item.descripcion || 'Sin descripción adicional registrada.' }}
                    </p>

                    <div class="catalog-item__summary">
                      <div class="catalog-stat">
                        <span class="text-muted">Rango base</span>
                        <strong>{{ formatCurrency(item.precio_base_min) }} - {{ formatCurrency(item.precio_base_max) }}</strong>
                      </div>
                      <div class="catalog-stat">
                        <span class="text-muted">Especialidad</span>
                        <strong>{{ item.especialidad_nombre }}</strong>
                      </div>
                    </div>
                  </div>

                  <div class="catalog-item__actions">
                    <button
                      type="button"
                      class="app-button app-button--ghost"
                      (click)="startEdit(item)"
                      [disabled]="saving()"
                    >
                      Editar
                    </button>
                    @if (item.activo) {
                      <button
                        type="button"
                        class="app-button app-button--secondary"
                        (click)="deactivate(item)"
                        [disabled]="saving()"
                      >
                        Desactivar
                      </button>
                    } @else if (includeInactive()) {
                      <button
                        type="button"
                        class="app-button app-button--secondary"
                        (click)="activate(item)"
                        [disabled]="saving()"
                      >
                        Activar
                      </button>
                    }
                  </div>
                </article>
              }
            </div>
          } @else if (!hasSpecialties()) {
            <app-empty-state
              title="Catálogo no disponible"
              message="Primero configura especialidades reales del taller para poder crear servicios."
            />
          } @else {
            <app-empty-state
              title="Sin servicios en el catálogo"
              message="Todavía no hay servicios base configurados para este taller."
            >
              <button
                empty-actions
                type="button"
                class="app-button"
                (click)="startCreate()"
              >
                Agregar servicio
              </button>
            </app-empty-state>
          }
        </app-card>
      }
    </div>
  `,
  styles: [
    `
      .toolbar--tight {
        justify-content: flex-end;
      }

      .catalog-header-grid {
        align-items: start;
      }

      .catalog-note {
        margin: var(--space-4) 0 0;
      }

      .toggle-inline {
        display: inline-flex;
        align-items: center;
        gap: var(--space-3);
        color: var(--color-text);
      }

      .specialties {
        display: flex;
        flex-wrap: wrap;
        gap: var(--space-3);
      }

      .catalog-form {
        display: flex;
        flex-direction: column;
        gap: var(--space-5);
      }

      .app-field--full,
      .toggle-field {
        grid-column: 1 / -1;
      }

      .toggle-field {
        display: flex;
        align-items: flex-start;
        gap: var(--space-3);
        padding: var(--space-4);
        border: 1px solid var(--color-border);
        border-radius: var(--radius-lg);
        background: color-mix(in srgb, var(--color-surface-soft) 92%, transparent);
      }

      .toggle-field input {
        margin-top: 0.25rem;
      }

      .toggle-field__title {
        display: block;
        font-weight: 700;
      }

      .toggle-field__hint {
        display: block;
        margin-top: var(--space-1);
        color: var(--color-text-muted);
        line-height: 1.45;
      }

      .field-error,
      .feedback {
        font-size: 0.88rem;
        line-height: 1.4;
      }

      .field-error,
      .feedback--error {
        color: var(--color-danger);
      }

      .form-actions {
        display: flex;
        align-items: center;
        gap: var(--space-4);
        flex-wrap: wrap;
      }

      .catalog-list {
        display: flex;
        flex-direction: column;
        gap: var(--space-4);
      }

      .catalog-item {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: var(--space-5);
        padding: var(--space-5);
        border: 1px solid var(--color-border);
        border-radius: var(--radius-lg);
        background: color-mix(in srgb, var(--color-surface-soft) 92%, transparent);
      }

      .catalog-item--inactive {
        opacity: 0.72;
      }

      .catalog-item__main {
        min-width: 0;
        flex: 1;
      }

      .catalog-item__heading {
        display: flex;
        align-items: center;
        gap: var(--space-3);
        flex-wrap: wrap;
      }

      .catalog-item__meta {
        display: flex;
        flex-wrap: wrap;
        gap: var(--space-3);
        margin-top: var(--space-3);
      }

      .catalog-item__description {
        margin: var(--space-4) 0;
        line-height: 1.6;
      }

      .catalog-item__summary {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: var(--space-4);
      }

      .catalog-stat {
        display: flex;
        flex-direction: column;
        gap: var(--space-2);
      }

      .catalog-item__actions {
        display: flex;
        flex-direction: column;
        gap: var(--space-3);
        min-width: 140px;
      }

      @media (max-width: 820px) {
        .catalog-item {
          flex-direction: column;
        }

        .catalog-item__actions {
          width: 100%;
          min-width: 0;
          flex-direction: row;
          flex-wrap: wrap;
        }
      }
    `,
  ],
})
export class WorkshopCatalogPage {
  private readonly catalogApi = inject(WorkshopCatalogApi);
  private readonly profileApi = inject(WorkshopProfileApi);
  private readonly destroyRef = inject(DestroyRef);
  private readonly formBuilder = inject(FormBuilder);

  protected readonly loading = signal(false);
  protected readonly saving = signal(false);
  protected readonly pageError = signal('');
  protected readonly formError = signal('');
  protected readonly includeInactive = signal(false);
  protected readonly profile = signal<WorkshopProfileResponse | null>(null);
  protected readonly catalogItems = signal<WorkshopCatalogServiceResponse[]>([]);
  protected readonly formMode = signal<CatalogFormMode>(null);
  protected readonly editingCatalogId = signal<number | null>(null);

  protected readonly specialties = computed(
    () => this.profile()?.specialties ?? [],
  );
  protected readonly hasSpecialties = computed(
    () => this.specialties().length > 0,
  );
  protected readonly isFormVisible = computed(() => this.formMode() !== null);

  protected readonly catalogForm = this.formBuilder.group(
    {
      id_especialidad: [null as number | null, [Validators.required]],
      nombre: ['', [Validators.required]],
      descripcion: [''],
      precio_base_min: [null as number | null, [Validators.required, Validators.min(0)]],
      precio_base_max: [null as number | null, [Validators.required, Validators.min(0)]],
      incluye_repuestos_basicos: [false],
    },
    {
      validators: [
        (group) => {
          const min = Number(group.get('precio_base_min')?.value);
          const max = Number(group.get('precio_base_max')?.value);

          if (!Number.isFinite(min) || !Number.isFinite(max)) {
            return null;
          }

          return max >= min ? null : { priceRange: true };
        },
      ],
    },
  );

  constructor() {
    this.reload();
  }

  protected reload(): void {
    this.loading.set(true);
    this.pageError.set('');
    this.formError.set('');

    this.profileApi
      .getProfile()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => {
          this.profile.set(response);
          this.loadCatalog();
        },
        error: (error) => {
          this.pageError.set(
            this.extractErrorMessage(
              error,
              'No se pudo cargar el perfil del taller para preparar el catálogo.',
            ),
          );
          this.loading.set(false);
        },
      });
  }

  protected toggleIncludeInactive(event: Event): void {
    const checked = (event.target as HTMLInputElement | null)?.checked ?? false;
    this.includeInactive.set(checked);
    this.loadCatalog();
  }

  protected startCreate(): void {
    if (!this.hasSpecialties()) {
      return;
    }

    this.formMode.set('create');
    this.editingCatalogId.set(null);
    this.formError.set('');
    this.catalogForm.reset(
      {
        id_especialidad: null,
        nombre: '',
        descripcion: '',
        precio_base_min: null,
        precio_base_max: null,
        incluye_repuestos_basicos: false,
      },
      { emitEvent: false },
    );
  }

  protected startEdit(item: WorkshopCatalogServiceResponse): void {
    if (!Number.isInteger(item.catalog_id) || item.catalog_id <= 0) {
      this.pageError.set('ID de catálogo inválido.');
      return;
    }

    this.formMode.set('edit');
    this.editingCatalogId.set(item.catalog_id);
    this.formError.set('');
    this.catalogForm.reset(
      {
        id_especialidad: item.id_especialidad,
        nombre: item.nombre,
        descripcion: item.descripcion ?? '',
        precio_base_min: this.toNumber(item.precio_base_min),
        precio_base_max: this.toNumber(item.precio_base_max),
        incluye_repuestos_basicos: item.incluye_repuestos_basicos,
      },
      { emitEvent: false },
    );
  }

  protected cancelForm(): void {
    this.formMode.set(null);
    this.editingCatalogId.set(null);
    this.formError.set('');
    this.catalogForm.reset(
      {
        id_especialidad: null,
        nombre: '',
        descripcion: '',
        precio_base_min: null,
        precio_base_max: null,
        incluye_repuestos_basicos: false,
      },
      { emitEvent: false },
    );
  }

  protected saveCatalogService(): void {
    if (this.catalogForm.invalid || this.saving() || !this.hasSpecialties()) {
      this.catalogForm.markAllAsTouched();
      return;
    }

    const rawValue = this.catalogForm.getRawValue();
    const id_especialidad = Number(rawValue.id_especialidad);
    const precio_base_min = Number(rawValue.precio_base_min);
    const precio_base_max = Number(rawValue.precio_base_max);
    const nombre = String(rawValue.nombre ?? '').trim();

    if (!Number.isInteger(id_especialidad) || id_especialidad <= 0) {
      this.formError.set('Especialidad inválida.');
      return;
    }

    if (!Number.isFinite(precio_base_min) || precio_base_min < 0) {
      this.formError.set('El precio mínimo debe ser un número válido y no negativo.');
      return;
    }

    if (!Number.isFinite(precio_base_max) || precio_base_max < 0) {
      this.formError.set('El precio máximo debe ser un número válido y no negativo.');
      return;
    }

    if (precio_base_max < precio_base_min) {
      this.formError.set('El precio máximo debe ser mayor o igual al mínimo.');
      return;
    }

    if (nombre.length === 0) {
      this.formError.set('El nombre del servicio no puede estar vacío.');
      return;
    }

    const basePayload: WorkshopCatalogServiceCreateRequest = {
      id_especialidad,
      nombre,
      descripcion: this.normalizeOptionalText(rawValue.descripcion),
      precio_base_min,
      precio_base_max,
      incluye_repuestos_basicos: Boolean(rawValue.incluye_repuestos_basicos),
    };

    this.saving.set(true);
    this.formError.set('');

    if (this.formMode() === 'edit' && this.editingCatalogId()) {
      const updatePayload: WorkshopCatalogServiceUpdateRequest = {
        ...basePayload,
      };

      this.catalogApi
        .updateCatalogService(this.editingCatalogId() as number, updatePayload)
        .pipe(takeUntilDestroyed(this.destroyRef))
        .subscribe({
          next: () => {
            this.saving.set(false);
            this.cancelForm();
            this.loadCatalog();
          },
          error: (error) => {
            this.formError.set(
              this.extractErrorMessage(
                error,
                'No se pudo actualizar el servicio del catálogo.',
              ),
            );
            this.saving.set(false);
          },
        });
      return;
    }

    this.catalogApi
      .createCatalogService(basePayload)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.saving.set(false);
          this.cancelForm();
          this.loadCatalog();
        },
        error: (error) => {
          this.formError.set(
            this.extractErrorMessage(
              error,
              'No se pudo crear el servicio en el catálogo.',
            ),
          );
          this.saving.set(false);
        },
      });
  }

  protected deactivate(item: WorkshopCatalogServiceResponse): void {
    if (this.saving()) {
      return;
    }

    if (!Number.isInteger(item.catalog_id) || item.catalog_id <= 0) {
      this.pageError.set('ID de catálogo inválido.');
      return;
    }

    const confirmed = window.confirm(
      `¿Desactivar el servicio "${item.nombre}" del catálogo?`,
    );
    if (!confirmed) {
      return;
    }

    this.saving.set(true);
    this.catalogApi
      .deactivateCatalogService(item.catalog_id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.saving.set(false);
          this.loadCatalog();
        },
        error: (error) => {
          this.pageError.set(
            this.extractErrorMessage(
              error,
              'No se pudo desactivar el servicio seleccionado.',
            ),
          );
          this.saving.set(false);
        },
      });
  }

  protected activate(item: WorkshopCatalogServiceResponse): void {
    if (this.saving()) {
      return;
    }

    if (!Number.isInteger(item.catalog_id) || item.catalog_id <= 0) {
      this.pageError.set('ID de catálogo inválido.');
      return;
    }

    const confirmed = window.confirm(
      `¿Activar nuevamente el servicio "${item.nombre}" en el catálogo?`,
    );
    if (!confirmed) {
      return;
    }

    this.saving.set(true);
    this.catalogApi
      .activateCatalogService(item.catalog_id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.saving.set(false);
          this.loadCatalog();
        },
        error: (error) => {
          this.pageError.set(
            this.extractErrorMessage(
              error,
              'No se pudo activar el servicio seleccionado.',
            ),
          );
          this.saving.set(false);
        },
      });
  }

  protected hasError(
    controlName:
      | 'id_especialidad'
      | 'nombre'
      | 'precio_base_min'
      | 'precio_base_max',
    errorKey: string,
  ): boolean {
    const control = this.catalogForm.get(controlName);
    return Boolean(control?.touched && control.hasError(errorKey));
  }

  protected formatCurrency(value: string | number): string {
    return `BOB ${new Intl.NumberFormat('es-BO', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(this.toNumber(value))}`;
  }

  private loadCatalog(): void {
    this.catalogApi
      .listCatalog(this.includeInactive())
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => {
          this.catalogItems.set(response);
          this.pageError.set('');
          this.loading.set(false);
        },
        error: (error) => {
          this.pageError.set(
            this.extractErrorMessage(
              error,
              'No se pudo cargar el catálogo del taller.',
            ),
          );
          this.loading.set(false);
        },
      });
  }

  private normalizeOptionalText(value: string | null | undefined): string | null {
    const normalized = String(value ?? '').trim();
    return normalized ? normalized : null;
  }

  private toNumber(value: string | number | null | undefined): number {
    const numericValue = Number(value ?? 0);
    return Number.isFinite(numericValue) ? numericValue : 0;
  }

  private extractErrorMessage(error: unknown, fallback: string): string {
    if (error instanceof HttpErrorResponse) {
      const detail = error.error?.detail;

      if (typeof detail === 'string' && detail.trim()) {
        return detail;
      }

      if (Array.isArray(detail)) {
        const messages = detail
          .map((item) => {
            if (typeof item === 'string') {
              return item;
            }
            if (item && typeof item === 'object' && 'msg' in item) {
              return String((item as { msg?: unknown }).msg ?? '');
            }
            return '';
          })
          .filter(Boolean);

        if (messages.length) {
          return messages.join(' ');
        }
      }

      if (typeof error.error === 'string' && error.error.trim()) {
        return error.error;
      }
    }

    return fallback;
  }
}
