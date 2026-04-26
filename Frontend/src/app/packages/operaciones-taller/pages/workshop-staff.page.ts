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
import {
  AbstractControl,
  FormArray,
  FormBuilder,
  FormGroup,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';

import { AppCardComponent } from '../../../shared/components/app-card.component';
import { EmptyStateComponent } from '../../../shared/components/empty-state.component';
import { ErrorStateComponent } from '../../../shared/components/error-state.component';
import { LoadingStateComponent } from '../../../shared/components/loading-state.component';
import { MetricCardComponent } from '../../../shared/components/metric-card.component';
import { PageHeaderComponent } from '../../../shared/components/page-header.component';
import { StatusBadgeComponent } from '../../../shared/components/status-badge.component';
import { WorkshopProfileApi } from '../data-access/workshop-profile.api';
import {
  WorkshopConfiguredSpecialty,
  WorkshopProfileResponse,
} from '../data-access/workshop-profile.models';
import { WorkshopStaffApi } from '../data-access/workshop-staff.api';
import {
  StaffSpecialtyInput,
  WorkshopStaffCreateRequest,
  WorkshopStaffSummary,
} from '../data-access/workshop-staff.models';

@Component({
  selector: 'app-workshop-staff-page',
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
    MetricCardComponent,
    StatusBadgeComponent,
  ],
  template: `
    <div class="page">
      <app-page-header
        eyebrow="Gestión de personal"
        title="Operarios del taller"
        subtitle="Administra el personal técnico, sus especialidades y disponibilidad operativa."
      >
        <div page-actions class="toolbar toolbar--tight">
          @if (!isRegisterFormVisible()) {
            <button
              type="button"
              class="app-button"
              (click)="startRegister()"
              [disabled]="loading() || !hasSpecialties()"
            >
              Registrar operario
            </button>
          } @else {
            <button
              type="button"
              class="app-button app-button--secondary"
              (click)="cancelRegister()"
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

      @if (loading() && !staffItems().length) {
        <app-loading-state
          title="Cargando operarios"
          message="Consultando personal técnico y especialidades del taller."
        />
      } @else if (pageError() && !staffItems().length) {
        <app-error-state [message]="pageError()">
          <button error-actions type="button" class="app-button" (click)="reload()">
            Reintentar
          </button>
        </app-error-state>
      } @else {
        <section class="staff-kpis">
          <app-metric-card
            label="Total operarios"
            [value]="formatInteger(totalOperarios())"
            hint="Personal técnico registrado para el taller"
          />
          <app-metric-card
            label="Disponibles"
            [value]="formatInteger(disponiblesCount())"
            hint="Operarios listos para asignación"
          />
          <app-metric-card
            label="En servicio"
            [value]="formatInteger(enServicioCount())"
            hint="Operarios atendiendo servicios activos"
          />
          <app-metric-card
            label="No disponibles / baja"
            [value]="formatInteger(noDisponiblesCount())"
            hint="Requieren atención operativa o administrativa"
          />
        </section>

        <section class="section-grid header-grid">
          <app-card
            title="Disponibilidad operativa"
            subtitle="Resumen rápido del estado actual del equipo técnico."
          >
            <div class="availability-summary">
              <div class="availability-summary__item">
                <span class="text-muted">Disponibles</span>
                <strong>{{ formatInteger(disponiblesCount()) }}</strong>
              </div>
              <div class="availability-summary__item">
                <span class="text-muted">En servicio</span>
                <strong>{{ formatInteger(enServicioCount()) }}</strong>
              </div>
              <div class="availability-summary__item">
                <span class="text-muted">No disponibles</span>
                <strong>{{ formatInteger(noDisponiblesStrictCount()) }}</strong>
              </div>
              <div class="availability-summary__item">
                <span class="text-muted">Baja</span>
                <strong>{{ formatInteger(bajaCount()) }}</strong>
              </div>
            </div>
          </app-card>

          <app-card
            title="Especialidades habilitadas"
            subtitle="Se reutilizan del perfil del taller para registrar operarios con datos reales."
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
                message="Configura el perfil del taller antes de registrar operarios."
              />
            }
          </app-card>
        </section>

        @if (isRegisterFormVisible()) {
          <app-card
            title="Registrar operario"
            subtitle="Crea un perfil operativo nuevo y asígnale una o más especialidades del taller."
          >
            <form class="staff-form" [formGroup]="registerForm" (ngSubmit)="saveStaff()">
              <div class="form-grid">
                <label class="app-field">
                  <span class="app-field__label">Nombre</span>
                  <input type="text" class="app-input" formControlName="nombre" placeholder="Nombre" />
                  @if (hasControlError(registerForm.get('nombre'), 'required')) {
                    <span class="field-error">El nombre es obligatorio.</span>
                  }
                </label>

                <label class="app-field">
                  <span class="app-field__label">Apellido</span>
                  <input type="text" class="app-input" formControlName="apellido" placeholder="Apellido" />
                  @if (hasControlError(registerForm.get('apellido'), 'required')) {
                    <span class="field-error">El apellido es obligatorio.</span>
                  }
                </label>

                <label class="app-field">
                  <span class="app-field__label">CI</span>
                  <input type="text" class="app-input" formControlName="ci" placeholder="Documento de identidad" />
                  @if (hasControlError(registerForm.get('ci'), 'required')) {
                    <span class="field-error">El CI es obligatorio.</span>
                  }
                </label>

                <label class="app-field">
                  <span class="app-field__label">Teléfono</span>
                  <input type="text" class="app-input" formControlName="telefono" placeholder="70000001" />
                </label>

                <label class="app-field">
                  <span class="app-field__label">Email</span>
                  <input type="email" class="app-input" formControlName="email" placeholder="operario@taller.com" />
                  @if (hasControlError(registerForm.get('email'), 'required')) {
                    <span class="field-error">El email es obligatorio.</span>
                  } @else if (hasControlError(registerForm.get('email'), 'email')) {
                    <span class="field-error">Ingresa un email válido.</span>
                  }
                </label>

                <label class="app-field">
                  <span class="app-field__label">Contraseña</span>
                  <input type="password" class="app-input" formControlName="password" placeholder="Mínimo 8 caracteres" />
                  @if (hasControlError(registerForm.get('password'), 'required')) {
                    <span class="field-error">La contraseña es obligatoria.</span>
                  } @else if (hasControlError(registerForm.get('password'), 'minlength')) {
                    <span class="field-error">La contraseña debe tener al menos 8 caracteres.</span>
                  }
                </label>

                <label class="app-field app-field--full">
                  <span class="app-field__label">Dirección</span>
                  <input type="text" class="app-input" formControlName="direccion" placeholder="Dato opcional para referencia interna" />
                </label>
              </div>

              <section class="specialty-panel">
                <header class="specialty-panel__header">
                  <div>
                    <h4>Especialidades del operario</h4>
                    <p class="text-muted">Selecciona al menos una especialidad y define su experiencia.</p>
                  </div>
                </header>

                @if (specialtyControls().length) {
                  <div class="specialty-options">
                    @for (control of specialtyControls(); track control.get('id_especialidad')?.value; let i = $index) {
                      <div
                        class="specialty-option"
                        [formGroup]="control"
                        [class.specialty-option--active]="isSpecialtySelected(control)"
                      >
                        <label class="specialty-option__toggle">
                          <input type="checkbox" formControlName="selected" />
                          <span>{{ specialtyLabel(control.get('id_especialidad')?.value) }}</span>
                        </label>

                        @if (isSpecialtySelected(control)) {
                          <div class="specialty-option__details">
                            <label class="app-field">
                              <span class="app-field__label">Años de experiencia</span>
                              <input
                                type="number"
                                step="1"
                                min="0"
                                class="app-input"
                                formControlName="anios_experiencia"
                              />
                              @if (hasControlError(control.get('anios_experiencia'), 'min')) {
                                <span class="field-error">La experiencia no puede ser negativa.</span>
                              }
                            </label>

                            <label class="app-field">
                              <span class="app-field__label">URL de certificación</span>
                              <input
                                type="url"
                                class="app-input"
                                formControlName="certificacion_url"
                                placeholder="Opcional"
                              />
                            </label>
                          </div>
                        }
                      </div>
                    }
                  </div>
                }

                @if (hasSpecialtySelectionError()) {
                  <p class="feedback feedback--error">Selecciona al menos una especialidad.</p>
                }
              </section>

              @if (formError()) {
                <p class="feedback feedback--error">{{ formError() }}</p>
              }

              <div class="form-actions">
                <button
                  type="submit"
                  class="app-button"
                  [disabled]="registerForm.invalid || saving() || !hasSpecialties()"
                >
                  {{ saving() ? 'Guardando...' : 'Guardar operario' }}
                </button>
                <button
                  type="button"
                  class="app-button app-button--secondary"
                  (click)="cancelRegister()"
                  [disabled]="saving()"
                >
                  Cancelar
                </button>
              </div>
            </form>
          </app-card>
        }

        <app-card
          title="Equipo técnico"
          subtitle="Listado real de operarios del taller y control directo de disponibilidad."
        >
          @if (staffItems().length) {
            <div class="staff-list">
              @for (item of staffItems(); track item.operario_id) {
                <article class="staff-item" [class.staff-item--inactive]="!item.activo">
                  <div class="staff-item__main">
                    <div class="staff-item__heading">
                      <strong>{{ item.nombre_completo }}</strong>
                      <app-status-badge [label]="item.estado_disponibilidad" />
                      <app-status-badge [label]="item.activo ? 'CONFIRMADO' : 'BAJA'" />
                    </div>

                    <div class="staff-item__contact">
                      <span><strong>CI:</strong> {{ item.ci }}</span>
                      <span><strong>Email:</strong> {{ item.email }}</span>
                      <span><strong>Teléfono:</strong> {{ item.telefono || 'No registrado' }}</span>
                      @if (item.registered_at) {
                        <span><strong>Registro:</strong> {{ formatDate(item.registered_at) }}</span>
                      }
                    </div>

                    <div class="staff-item__specialties">
                      @for (specialty of item.specialties; track specialty.id_especialidad) {
                        <div class="specialty-chip">
                          <span class="badge badge--info">{{ specialty.nombre }}</span>
                          <small class="text-muted">{{ specialty.anios_experiencia }} año(s)</small>
                          @if (specialty.certificacion_url) {
                            <a
                              [href]="specialty.certificacion_url"
                              target="_blank"
                              rel="noopener noreferrer"
                              class="specialty-chip__link"
                            >
                              Certificación
                            </a>
                          }
                        </div>
                      }
                    </div>
                  </div>

                  <div class="staff-item__actions">
                    <label class="app-field">
                      <span class="app-field__label">Disponibilidad</span>
                      <select
                        class="app-select"
                        [value]="availabilityDraft(item)"
                        (change)="setAvailabilityDraft(item.operario_id, $event)"
                      >
                        @for (status of availabilityOptions; track status) {
                          <option [value]="status">{{ status }}</option>
                        }
                      </select>
                    </label>

                    <button
                      type="button"
                      class="app-button app-button--secondary"
                      (click)="applyAvailability(item)"
                      [disabled]="saving() || availabilityDraft(item) === item.estado_disponibilidad"
                    >
                      Aplicar
                    </button>
                  </div>
                </article>
              }
            </div>
          } @else if (!hasSpecialties()) {
            <app-empty-state
              title="No se puede registrar personal"
              message="Primero configura especialidades reales del taller para habilitar operarios."
            />
          } @else {
            <app-empty-state
              title="Sin operarios registrados"
              message="Todavía no hay personal técnico cargado para este taller."
            />
            <div class="empty-actions">
              <button type="button" class="app-button" (click)="startRegister()">
                Registrar operario
              </button>
            </div>
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

      .staff-kpis {
        display: grid;
        gap: var(--space-4);
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      }

      .header-grid {
        align-items: start;
      }

      .availability-summary {
        display: grid;
        gap: var(--space-4);
        grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
      }

      .availability-summary__item {
        display: flex;
        flex-direction: column;
        gap: var(--space-2);
      }

      .specialties {
        display: flex;
        flex-wrap: wrap;
        gap: var(--space-3);
      }

      .staff-form {
        display: flex;
        flex-direction: column;
        gap: var(--space-5);
      }

      .app-field--full {
        grid-column: 1 / -1;
      }

      .specialty-panel {
        padding: var(--space-5);
        border: 1px solid var(--color-border);
        border-radius: var(--radius-lg);
        background: color-mix(in srgb, var(--color-surface-soft) 90%, transparent);
      }

      .specialty-panel__header h4 {
        margin: 0;
        font-size: 1rem;
      }

      .specialty-panel__header p {
        margin: var(--space-2) 0 0;
      }

      .specialty-options {
        display: flex;
        flex-direction: column;
        gap: var(--space-4);
        margin-top: var(--space-5);
      }

      .specialty-option {
        padding: var(--space-4);
        border: 1px solid var(--color-border);
        border-radius: var(--radius-lg);
        background: var(--color-surface);
      }

      .specialty-option--active {
        border-color: color-mix(in srgb, var(--color-primary) 32%, var(--color-border));
      }

      .specialty-option__toggle {
        display: inline-flex;
        align-items: center;
        gap: var(--space-3);
        font-weight: 700;
      }

      .specialty-option__details {
        display: grid;
        gap: var(--space-4);
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        margin-top: var(--space-4);
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

      .staff-list {
        display: flex;
        flex-direction: column;
        gap: var(--space-4);
      }

      .staff-item {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: var(--space-5);
        padding: var(--space-5);
        border: 1px solid var(--color-border);
        border-radius: var(--radius-lg);
        background: color-mix(in srgb, var(--color-surface-soft) 92%, transparent);
      }

      .staff-item--inactive {
        opacity: 0.78;
      }

      .staff-item__main {
        min-width: 0;
        flex: 1;
      }

      .staff-item__heading {
        display: flex;
        align-items: center;
        gap: var(--space-3);
        flex-wrap: wrap;
      }

      .staff-item__contact {
        display: flex;
        flex-wrap: wrap;
        gap: var(--space-4);
        margin-top: var(--space-3);
        color: var(--color-text-muted);
      }

      .staff-item__specialties {
        display: flex;
        flex-direction: column;
        gap: var(--space-3);
        margin-top: var(--space-4);
      }

      .specialty-chip {
        display: flex;
        align-items: center;
        gap: var(--space-3);
        flex-wrap: wrap;
      }

      .specialty-chip__link {
        color: var(--color-primary);
        text-decoration: none;
      }

      .specialty-chip__link:hover {
        text-decoration: underline;
      }

      .staff-item__actions {
        display: flex;
        flex-direction: column;
        gap: var(--space-3);
        min-width: 180px;
      }

      .empty-actions {
        margin-top: var(--space-5);
      }

      @media (max-width: 900px) {
        .staff-item {
          flex-direction: column;
        }

        .staff-item__actions {
          width: 100%;
          min-width: 0;
        }
      }
    `,
  ],
})
export class WorkshopStaffPage {
  private readonly staffApi = inject(WorkshopStaffApi);
  private readonly profileApi = inject(WorkshopProfileApi);
  private readonly destroyRef = inject(DestroyRef);
  private readonly formBuilder = inject(FormBuilder);

  protected readonly availabilityOptions = [
    'DISPONIBLE',
    'EN_SERVICIO',
    'NO_DISPONIBLE',
    'BAJA',
  ] as const;

  protected readonly loading = signal(false);
  protected readonly saving = signal(false);
  protected readonly pageError = signal('');
  protected readonly formError = signal('');
  protected readonly profile = signal<WorkshopProfileResponse | null>(null);
  protected readonly staffItems = signal<WorkshopStaffSummary[]>([]);
  protected readonly isRegisterFormVisible = signal(false);
  protected readonly availabilityDrafts = signal<Record<number, string>>({});

  protected readonly specialties = computed(
    () => this.profile()?.specialties ?? [],
  );
  protected readonly hasSpecialties = computed(() => this.specialties().length > 0);
  protected readonly totalOperarios = computed(() => this.staffItems().length);
  protected readonly disponiblesCount = computed(
    () =>
      this.staffItems().filter((item) => item.estado_disponibilidad === 'DISPONIBLE').length,
  );
  protected readonly enServicioCount = computed(
    () =>
      this.staffItems().filter((item) => item.estado_disponibilidad === 'EN_SERVICIO').length,
  );
  protected readonly noDisponiblesStrictCount = computed(
    () =>
      this.staffItems().filter((item) => item.estado_disponibilidad === 'NO_DISPONIBLE').length,
  );
  protected readonly bajaCount = computed(
    () => this.staffItems().filter((item) => item.estado_disponibilidad === 'BAJA').length,
  );
  protected readonly noDisponiblesCount = computed(
    () => this.noDisponiblesStrictCount() + this.bajaCount(),
  );

  protected readonly registerForm: FormGroup = this.formBuilder.group({
    nombre: ['', [Validators.required]],
    apellido: ['', [Validators.required]],
    ci: ['', [Validators.required]],
    telefono: [''],
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(8)]],
    direccion: [''],
    specialties: this.formBuilder.array([], {
      validators: [(control) => this.validateSpecialties(control)],
    }),
  });

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
        next: (profile) => {
          this.profile.set(profile);
          this.rebuildSpecialtiesForm(profile.specialties);
          this.loadStaff();
        },
        error: (error) => {
          this.pageError.set(
            this.extractErrorMessage(
              error,
              'No se pudo cargar el perfil del taller para preparar la gestión de operarios.',
            ),
          );
          this.loading.set(false);
        },
      });
  }

  protected startRegister(): void {
    if (!this.hasSpecialties()) {
      return;
    }

    this.formError.set('');
    this.resetRegisterForm();
    this.isRegisterFormVisible.set(true);
  }

  protected cancelRegister(): void {
    this.formError.set('');
    this.resetRegisterForm();
    this.isRegisterFormVisible.set(false);
  }

  protected saveStaff(): void {
    if (this.registerForm.invalid || this.saving() || !this.hasSpecialties()) {
      this.registerForm.markAllAsTouched();
      this.specialtyControls().forEach((group) => group.markAllAsTouched());
      return;
    }

    const rawValue = this.registerForm.getRawValue();
    const specialties = this.specialtyControls()
      .filter((group) => Boolean(group.get('selected')?.value))
      .map((group): StaffSpecialtyInput => ({
        id_especialidad: Number(group.get('id_especialidad')?.value),
        anios_experiencia: Number(group.get('anios_experiencia')?.value ?? 0),
        certificacion_url: this.normalizeOptionalText(
          group.get('certificacion_url')?.value as string | null | undefined,
        ),
      }));

    const payload: WorkshopStaffCreateRequest = {
      nombre: String(rawValue.nombre ?? '').trim(),
      apellido: String(rawValue.apellido ?? '').trim(),
      ci: String(rawValue.ci ?? '').trim(),
      telefono: this.normalizeOptionalText(rawValue.telefono),
      email: String(rawValue.email ?? '').trim(),
      password: String(rawValue.password ?? ''),
      direccion: this.normalizeOptionalText(rawValue.direccion),
      specialties,
    };

    this.saving.set(true);
    this.formError.set('');

    this.staffApi
      .createStaff(payload)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.saving.set(false);
          this.cancelRegister();
          this.loadStaff();
        },
        error: (error) => {
          this.formError.set(
            this.extractErrorMessage(
              error,
              'No se pudo registrar el operario.',
            ),
          );
          this.saving.set(false);
        },
      });
  }

  protected setAvailabilityDraft(operarioId: number, event: Event): void {
    const value = (event.target as HTMLSelectElement | null)?.value ?? '';
    this.availabilityDrafts.update((current) => ({
      ...current,
      [operarioId]: value,
    }));
  }

  protected availabilityDraft(item: WorkshopStaffSummary): string {
    return this.availabilityDrafts()[item.operario_id] ?? item.estado_disponibilidad;
  }

  protected applyAvailability(item: WorkshopStaffSummary): void {
    const nextStatus = this.availabilityDraft(item);
    if (this.saving() || nextStatus === item.estado_disponibilidad) {
      return;
    }

    if (
      nextStatus === 'BAJA' &&
      !window.confirm(`¿Marcar a ${item.nombre_completo} como BAJA?`)
    ) {
      this.availabilityDrafts.update((current) => ({
        ...current,
        [item.operario_id]: item.estado_disponibilidad,
      }));
      return;
    }

    this.saving.set(true);
    this.pageError.set('');

    this.staffApi
      .updateAvailability(item.operario_id, { new_status: nextStatus as any })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (updated) => {
          this.saving.set(false);
          this.staffItems.update((items) =>
            items.map((current) =>
              current.operario_id === updated.operario_id ? updated : current,
            ),
          );
          this.availabilityDrafts.update((current) => ({
            ...current,
            [updated.operario_id]: updated.estado_disponibilidad,
          }));
        },
        error: (error) => {
          this.pageError.set(
            this.extractErrorMessage(
              error,
              'No se pudo actualizar la disponibilidad del operario.',
            ),
          );
          this.saving.set(false);
        },
      });
  }

  protected specialtyControls(): FormGroup[] {
    return this.specialtiesArray.controls as FormGroup[];
  }

  protected isSpecialtySelected(group: FormGroup): boolean {
    return Boolean(group.get('selected')?.value);
  }

  protected specialtyLabel(specialtyId: number | null | undefined): string {
    const normalizedId = Number(specialtyId);
    const match = this.specialties().find(
      (specialty) => specialty.id_especialidad === normalizedId,
    );
    return match?.nombre ?? `Especialidad #${Number.isFinite(normalizedId) && normalizedId > 0 ? normalizedId : '-'}`;
  }

  protected hasControlError(
    control: AbstractControl | null,
    errorKey: string,
  ): boolean {
    return Boolean(control?.touched && control.hasError(errorKey));
  }

  protected hasSpecialtySelectionError(): boolean {
    return Boolean(this.specialtiesArray.touched && this.specialtiesArray.hasError('specialtyRequired'));
  }

  protected formatInteger(value: number): string {
    return new Intl.NumberFormat('es-BO', { maximumFractionDigits: 0 }).format(value);
  }

  protected formatDate(value: string): string {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return value;
    }

    return new Intl.DateTimeFormat('es-BO', {
      dateStyle: 'medium',
      timeStyle: 'short',
    }).format(date);
  }

  private get specialtiesArray(): FormArray {
    return this.registerForm.get('specialties') as FormArray;
  }

  private loadStaff(): void {
    this.staffApi
      .listStaff()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => {
          this.staffItems.set(response);
          this.availabilityDrafts.set(
            Object.fromEntries(
              response.map((item) => [item.operario_id, item.estado_disponibilidad]),
            ),
          );
          this.pageError.set('');
          this.loading.set(false);
        },
        error: (error) => {
          this.pageError.set(
            this.extractErrorMessage(
              error,
              'No se pudo cargar el personal técnico del taller.',
            ),
          );
          this.loading.set(false);
        },
      });
  }

  private rebuildSpecialtiesForm(specialties: WorkshopConfiguredSpecialty[]): void {
    const specialtyGroups = specialties.map((specialty) =>
      this.formBuilder.group({
        selected: [false],
        id_especialidad: [specialty.id_especialidad],
        anios_experiencia: [0, [Validators.min(0)]],
        certificacion_url: [''],
      }),
    );
    this.registerForm.setControl(
      'specialties',
      this.formBuilder.array(specialtyGroups, {
        validators: [(control) => this.validateSpecialties(control)],
      }),
    );
  }

  private validateSpecialties(control: AbstractControl) {
    const formArray = control as FormArray;
    const selectedCount = formArray.controls.filter((item) => item.get('selected')?.value).length;
    return selectedCount > 0 ? null : { specialtyRequired: true };
  }

  private resetRegisterForm(): void {
    this.registerForm.reset(
      {
        nombre: '',
        apellido: '',
        ci: '',
        telefono: '',
        email: '',
        password: '',
        direccion: '',
      },
      { emitEvent: false },
    );
    this.rebuildSpecialtiesForm(this.specialties());
  }

  private normalizeOptionalText(value: string | null | undefined): string | null {
    const normalized = String(value ?? '').trim();
    return normalized ? normalized : null;
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

      if (error.status === 403) {
        return 'No tienes permisos para gestionar operarios de este taller.';
      }
    }

    return fallback;
  }
}
