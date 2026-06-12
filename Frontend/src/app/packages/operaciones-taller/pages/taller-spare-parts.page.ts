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
import { localizeBackendMessage } from '../../../shared/utils/user-facing-text';
import { TallerRepuestoApi } from '../data-access/taller-repuesto.api';
import {
  TallerRepuestoResponse,
  TallerRepuestoCreateRequest,
  TallerRepuestoUpdateRequest,
} from '../data-access/taller-repuesto.models';

type FormMode = 'create' | 'edit' | null;

@Component({
  selector: 'app-taller-spare-parts-page',
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
  ],
  template: `
    <div class="page">
      <app-page-header
        eyebrow="Inventario técnico"
        title="Catálogo de repuestos"
        subtitle="Gestiona los productos y repuestos disponibles para las reparaciones del taller."
      >
        <div page-actions class="toolbar toolbar--tight">
          @if (!isFormVisible()) {
            <button type="button" class="app-button" (click)="startCreate()" [disabled]="loading()">
              + Nuevo repuesto
            </button>
          } @else {
            <button type="button" class="app-button app-button--secondary" (click)="cancelForm()">
              Cancelar
            </button>
          }
        </div>
      </app-page-header>

      @if (loading() && !items().length) {
        <app-loading-state title="Cargando catálogo" message="Consultando repuestos del taller." />
      } @else if (error()) {
        <app-error-state [message]="error()">
          <button error-actions type="button" class="app-button" (click)="reload()">
            Reintentar
          </button>
        </app-error-state>
      } @else {
        @if (isFormVisible()) {
          <app-card title="Registrar repuesto" subtitle="Completa los datos del producto.">
            <form [formGroup]="form" (ngSubmit)="submitForm()" class="form-stack">
              <div class="field-group">
                <label class="field-group__label" for="nombre">Nombre *</label>
                <input id="nombre" type="text" class="app-input" formControlName="nombre" placeholder="Ej: Batería 12V 70Ah" />
                @if (form.get('nombre')?.invalid && form.get('nombre')?.touched) {
                  <span class="field-group__hint field-group__hint--error">El nombre es obligatorio.</span>
                }
              </div>

              <div class="field-group">
                <label class="field-group__label" for="descripcion">Descripción</label>
                <textarea id="descripcion" class="app-input" formControlName="descripcion" placeholder="Opcional: especificaciones del repuesto."></textarea>
              </div>

              <div class="field-group">
                <label class="field-group__label" for="precio_unitario">Precio unitario (BOB) *</label>
                <input id="precio_unitario" type="number" step="0.01" min="0" class="app-input" formControlName="precio_unitario" placeholder="0.00" />
                @if (form.get('precio_unitario')?.invalid && form.get('precio_unitario')?.touched) {
                  <span class="field-group__hint field-group__hint--error">Ingresa un precio válido mayor o igual a 0.</span>
                }
              </div>

              @if (formError()) {
                <p class="text-danger">{{ formError() }}</p>
              }

              <div class="toolbar">
                <button type="submit" class="app-button" [disabled]="saving() || form.invalid">
                  {{ isEditing() ? 'Guardar cambios' : 'Crear repuesto' }}
                </button>
                <button type="button" class="app-button app-button--secondary" (click)="cancelForm()">
                  Cancelar
                </button>
              </div>
            </form>
          </app-card>
        }

        @if (items().length) {
          <div class="list">
            @for (item of items(); track item.id_taller_repuesto) {
              <div class="list__item">
                <div class="list__meta">
                  <strong>{{ item.nombre }}</strong>
                  @if (!item.activo) {
                    <span class="badge badge--neutral">Inactivo</span>
                  }
                </div>
                @if (item.descripcion) {
                  <p class="text-muted">{{ item.descripcion }}</p>
                }
                <div class="repuesto-footer">
                  <strong class="repuesto-precio">BOB {{ formatNumber(item.precio_unitario) }}</strong>
                  <div class="repuesto-actions">
                    <button type="button" class="app-button-sm" (click)="startEdit(item)">Editar</button>
                    @if (item.activo) {
                      <button type="button" class="app-button-sm app-button-sm--danger" (click)="toggleActive(item, false)">Desactivar</button>
                    } @else {
                      <button type="button" class="app-button-sm app-button-sm--success" (click)="toggleActive(item, true)">Activar</button>
                    }
                  </div>
                </div>
              </div>
            }
          </div>
        } @else {
          <app-empty-state
            title="Sin repuestos registrados"
            message="Agrega productos al catálogo del taller para que el operario pueda seleccionarlos al finalizar una reparación."
          />
        }
      }
    </div>
  `,
  styles: [
    `
      .form-stack {
        display: flex;
        flex-direction: column;
        gap: var(--space-5);
      }

      .field-group {
        display: flex;
        flex-direction: column;
        gap: var(--space-2);
      }

      .list {
        display: flex;
        flex-direction: column;
        gap: var(--space-4);
      }

      .list__item {
        display: flex;
        flex-direction: column;
        gap: 0.45rem;
        padding: var(--space-4);
        border-radius: var(--radius-lg);
        border: 1px solid var(--color-border);
        background: color-mix(in srgb, var(--color-surface-soft) 92%, transparent);
      }

      .list__meta {
        display: flex;
        align-items: center;
        gap: var(--space-3);
        flex-wrap: wrap;
      }

      .repuesto-footer {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: var(--space-4);
        margin-top: var(--space-2);
        flex-wrap: wrap;
      }

      .repuesto-precio {
        font-size: 1.1rem;
      }

      .repuesto-actions {
        display: flex;
        gap: var(--space-3);
      }

      .toolbar {
        display: flex;
        gap: var(--space-3);
        flex-wrap: wrap;
      }

      .text-danger {
        color: var(--color-danger, #ef4444);
      }
    `,
  ],
})
export class TallerSparePartsPage {
  private readonly api = inject(TallerRepuestoApi);
  private readonly fb = inject(FormBuilder);
  private readonly destroyRef = inject(DestroyRef);

  protected readonly loading = signal(false);
  protected readonly saving = signal(false);
  protected readonly error = signal('');
  protected readonly formError = signal('');
  protected readonly items = signal<TallerRepuestoResponse[]>([]);
  protected readonly formMode = signal<FormMode>(null);
  protected readonly editingItem = signal<TallerRepuestoResponse | null>(null);

  protected readonly isFormVisible = computed(() => this.formMode() !== null);
  protected readonly isEditing = computed(() => this.formMode() === 'edit');

  protected readonly form = this.fb.group({
    nombre: ['', Validators.required],
    descripcion: [''],
    precio_unitario: [null as number | null, [Validators.required, Validators.min(0)]],
  });

  constructor() {
    this.reload();
  }

  protected reload(): void {
    this.loading.set(true);
    this.error.set('');
    this.api
      .list()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (res) => {
          this.items.set(res);
          this.loading.set(false);
        },
        error: () => {
          this.error.set('No se pudo cargar el catálogo de repuestos.');
          this.loading.set(false);
        },
      });
  }

  protected startCreate(): void {
    this.formMode.set('create');
    this.editingItem.set(null);
    this.formError.set('');
    this.form.reset({ nombre: '', descripcion: '', precio_unitario: null });
  }

  protected startEdit(item: TallerRepuestoResponse): void {
    this.formMode.set('edit');
    this.editingItem.set(item);
    this.formError.set('');
    this.form.patchValue({
      nombre: item.nombre,
      descripcion: item.descripcion ?? '',
      precio_unitario: this.toNumber(item.precio_unitario),
    });
  }

  protected cancelForm(): void {
    this.formMode.set(null);
    this.editingItem.set(null);
    this.formError.set('');
    this.form.reset();
  }

  protected submitForm(): void {
    if (this.form.invalid) {
      return;
    }

    const raw = this.form.getRawValue();
    this.saving.set(true);
    this.formError.set('');

    if (this.isEditing()) {
      const payload: TallerRepuestoUpdateRequest = {
        nombre: raw.nombre?.trim() || null,
        descripcion: raw.descripcion?.trim() || null,
        precio_unitario: raw.precio_unitario ?? null,
      };
      const editId = this.editingItem()?.id_taller_repuesto;
      if (editId === undefined) {
        return;
      }
      this.api.update(editId, payload).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
        next: () => {
          this.saving.set(false);
          this.reload();
          this.cancelForm();
        },
        error: (err: HttpErrorResponse) => {
          this.saving.set(false);
          this.formError.set(localizeBackendMessage(err.error?.detail ?? 'Error al actualizar.'));
        },
      });
    } else {
      const payload: TallerRepuestoCreateRequest = {
        nombre: raw.nombre?.trim() ?? '',
        descripcion: raw.descripcion?.trim() || null,
        precio_unitario: raw.precio_unitario ?? 0,
      };
      this.api.create(payload).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
        next: () => {
          this.saving.set(false);
          this.reload();
          this.cancelForm();
        },
        error: (err: HttpErrorResponse) => {
          this.saving.set(false);
          this.formError.set(localizeBackendMessage(err.error?.detail ?? 'Error al crear.'));
        },
      });
    }
  }

  protected toggleActive(item: TallerRepuestoResponse, activate: boolean): void {
    const obs = activate
      ? this.api.activate(item.id_taller_repuesto)
      : this.api.deactivate(item.id_taller_repuesto);

    obs.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: () => this.reload(),
      error: () => this.error.set('Error al cambiar estado del repuesto.'),
    });
  }

  protected formatNumber(value: number | string | null | undefined): string {
    return new Intl.NumberFormat('es-BO', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(this.toNumber(value));
  }

  private toNumber(value: number | string | null | undefined): number {
    const n = Number(value ?? 0);
    return Number.isFinite(n) ? n : 0;
  }
}
