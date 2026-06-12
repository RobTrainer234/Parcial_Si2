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
import { localizeBackendMessage } from '../../../shared/utils/user-facing-text';
import { WorkshopCatalogApi } from '../data-access/workshop-catalog.api';
import {
  WorkshopCatalogServiceCreateRequest,
  WorkshopCatalogServiceResponse,
  WorkshopCatalogServiceUpdateRequest,
} from '../data-access/workshop-catalog.models';
import { WorkshopProfileApi } from '../data-access/workshop-profile.api';
import {
  WorkshopConfiguredSpecialty,
  WorkshopProfileResponse,
  WorkshopProfileUpdateRequest,
} from '../data-access/workshop-profile.models';
import { WorkshopStaffApi } from '../data-access/workshop-staff.api';
import {
  StaffAvailabilityStatus,
  StaffSpecialtyInput,
  WorkshopStaffCreateRequest,
  WorkshopStaffSummary,
} from '../data-access/workshop-staff.models';

type TabId = 'general' | 'catalog' | 'staff';
type CatalogFormMode = 'create' | 'edit' | null;

@Component({
  selector: 'app-workshop-management-page',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    PageHeaderComponent,
    AppCardComponent,
    MetricCardComponent,
    StatusBadgeComponent,
    LoadingStateComponent,
    EmptyStateComponent,
    ErrorStateComponent,
  ],
  template: `
    <div class="page">
      <app-page-header
        eyebrow="Gestión del Taller"
        title="Panel de administración"
        subtitle="Administra el perfil, catálogo de servicios y personal técnico del taller."
      >
        <div page-actions class="toolbar toolbar--tight">
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

      <nav class="tabs">
        <button
          type="button"
          class="tab"
          [class.tab--active]="activeTab() === 'general'"
          (click)="activeTab.set('general')"
        >
          General
        </button>
        <button
          type="button"
          class="tab"
          [class.tab--active]="activeTab() === 'catalog'"
          (click)="switchToCatalog()"
        >
          Catálogo
          @if (catalogItems().length) {
            <span class="tab__badge">{{ catalogItems().length }}</span>
          }
        </button>
        <button
          type="button"
          class="tab"
          [class.tab--active]="activeTab() === 'staff'"
          (click)="switchToStaff()"
        >
          Personal
          @if (totalOperarios()) {
            <span class="tab__badge">{{ totalOperarios() }}</span>
          }
        </button>
      </nav>

      @if (loading() && !profile()) {
        <app-loading-state
          title="Cargando información"
          message="Consultando datos del taller."
        />
      } @else if (pageError() && !profile()) {
        <app-error-state [message]="pageError()">
          <button error-actions type="button" class="app-button" (click)="reload()">
            Reintentar
          </button>
        </app-error-state>
      } @else {
        <!-- ════════════════════════════════════════ GENERAL TAB ════════════════════════════════════════ -->
        @if (activeTab() === 'general') {
          <section class="tab-content">
            @if (saveSuccess()) {
              <p class="feedback feedback--success">{{ saveSuccess() }}</p>
            }

            @if (!editMode()) {
              <!-- Profile summary -->
              <div class="profile-summary">
                <div class="profile-summary__header">
                  <div>
                    <h2 class="profile-summary__name">{{ profile()!.nombre_comercial }}</h2>
                    <app-status-badge [label]="profile()!.activo ? 'ACTIVO' : 'INACTIVO'" />
                  </div>
                  <button
                    type="button"
                    class="app-button"
                    (click)="startEditProfile()"
                    [disabled]="saving()"
                  >
                    Editar perfil
                  </button>
                </div>

                @if (profile()!.descripcion) {
                  <p class="profile-summary__desc">{{ profile()!.descripcion }}</p>
                }

                <div class="profile-summary__grid">
                  <div class="profile-summary__field">
                    <span class="field-label">Dirección</span>
                    <strong>{{ formatAddress() }}</strong>
                  </div>
                  <div class="profile-summary__field">
                    <span class="field-label">Radio de acción</span>
                    <strong>{{ profile()!.radio_accion_km }} km</strong>
                  </div>
                  <div class="profile-summary__field">
                    <span class="field-label">Seguro propio</span>
                    <strong>{{ profile()!.acepta_seguro_propio ? 'Acepta' : 'No acepta' }}</strong>
                  </div>
                  <div class="profile-summary__field">
                    <span class="field-label">Coordenadas</span>
                    <strong>{{ profile()!.latitud }}, {{ profile()!.longitud }}</strong>
                  </div>
                </div>

                @if (profile()!.specialties.length) {
                  <div class="profile-summary__specialties">
                    <span class="field-label">Especialidades</span>
                    <div class="badge-group">
                      @for (sp of profile()!.specialties; track sp.id_especialidad) {
                        <span class="badge badge--info">{{ sp.nombre }}</span>
                      }
                    </div>
                  </div>
                }
              </div>
            } @else {
              <!-- Edit profile form -->
              <app-card
                title="Editar perfil"
                subtitle="Actualiza la información general del taller."
              >
                <form [formGroup]="profileForm" (ngSubmit)="saveProfile()" class="profile-form">
                  <div class="form-grid">
                    <label class="app-field app-field--full">
                      <span class="app-field__label">Nombre comercial</span>
                      <input type="text" class="app-input" formControlName="nombre_comercial" />
                      @if (profileForm.get('nombre_comercial')?.touched && profileForm.get('nombre_comercial')?.hasError('required')) {
                        <span class="field-error">El nombre es obligatorio.</span>
                      }
                    </label>

                    <label class="app-field app-field--full">
                      <span class="app-field__label">Descripción</span>
                      <textarea class="app-textarea" formControlName="descripcion" rows="3"></textarea>
                    </label>

                    <label class="app-field">
                      <span class="app-field__label">Dirección</span>
                      <input type="text" class="app-input" formControlName="direccion" />
                    </label>

                    <label class="app-field">
                      <span class="app-field__label">Ciudad</span>
                      <input type="text" class="app-input" formControlName="ciudad" />
                    </label>

                    <label class="app-field">
                      <span class="app-field__label">Zona</span>
                      <input type="text" class="app-input" formControlName="zona" />
                    </label>

                    <label class="app-field">
                      <span class="app-field__label">Referencia</span>
                      <input type="text" class="app-input" formControlName="referencia" />
                    </label>

                    <label class="app-field">
                      <span class="app-field__label">Latitud</span>
                      <input type="number" step="any" class="app-input" formControlName="latitud" />
                    </label>

                    <label class="app-field">
                      <span class="app-field__label">Longitud</span>
                      <input type="number" step="any" class="app-input" formControlName="longitud" />
                    </label>

                    <label class="app-field">
                      <span class="app-field__label">Radio de acción (km)</span>
                      <input type="number" step="0.1" class="app-input" formControlName="radio_accion_km" />
                      @if (profileForm.get('radio_accion_km')?.touched && profileForm.get('radio_accion_km')?.hasError('required')) {
                        <span class="field-error">El radio es obligatorio.</span>
                      } @else if (profileForm.get('radio_accion_km')?.touched && profileForm.get('radio_accion_km')?.hasError('min')) {
                        <span class="field-error">Debe ser mayor a 0.</span>
                      }
                    </label>

                    <label class="toggle-field">
                      <input type="checkbox" formControlName="acepta_seguro_propio" />
                      <div>
                        <span class="toggle-field__title">Acepta seguro propio</span>
                        <span class="toggle-field__hint">Indica si el taller cubre servicios con seguro.</span>
                      </div>
                    </label>
                  </div>

                  @if (profile()!.specialties.length) {
                    <section class="specialty-selector">
                      <header class="specialty-selector__header">
                        <h4>Especialidades del taller</h4>
                      </header>
                      <div class="specialty-selector__options">
                        @for (sp of profile()!.specialties; track sp.id_especialidad) {
                          <label class="specialty-check">
                            <input
                              type="checkbox"
                              [checked]="selectedSpecialtyIds().has(sp.id_especialidad)"
                              (change)="toggleSpecialty(sp.id_especialidad)"
                            />
                            <span>{{ sp.nombre }}</span>
                          </label>
                        }
                      </div>
                    </section>
                  }

                  @if (saveError()) {
                    <p class="feedback feedback--error">{{ saveError() }}</p>
                  }

                  <div class="form-actions">
                    <button
                      type="submit"
                      class="app-button"
                      [disabled]="profileForm.invalid || saving()"
                    >
                      {{ saving() ? 'Guardando...' : 'Guardar cambios' }}
                    </button>
                    <button
                      type="button"
                      class="app-button app-button--secondary"
                      (click)="cancelEditProfile()"
                      [disabled]="saving()"
                    >
                      Cancelar
                    </button>
                  </div>
                </form>
              </app-card>
            }
          </section>
        }

        <!-- ════════════════════════════════════════ CATALOG TAB ════════════════════════════════════════ -->
        @if (activeTab() === 'catalog') {
          <section class="tab-content">
            <div class="section-grid catalog-header-grid">
              <app-card
                title="Vista operativa"
                subtitle="Control de visibilidad del catálogo."
              >
                <div class="toolbar">
                  <label class="toggle-inline">
                    <input
                      type="checkbox"
                      [checked]="includeInactiveCatalog()"
                      (change)="toggleIncludeInactive($event)"
                    />
                    <span>Mostrar inactivos</span>
                  </label>
                  <span class="text-muted">
                    {{ catalogItems().length }} servicio(s)
                  </span>
                </div>

                @if (!hasSpecialties()) {
                  <p class="catalog-note feedback feedback--error">
                    No hay especialidades configuradas. Configura el perfil del taller primero.
                  </p>
                }

                <div class="toolbar" style="margin-top: var(--space-4)">
                  @if (!isCatalogFormVisible()) {
                    <button
                      type="button"
                      class="app-button"
                      (click)="startCreateCatalog()"
                      [disabled]="!hasSpecialties()"
                    >
                      Agregar servicio
                    </button>
                  } @else {
                    <button
                      type="button"
                      class="app-button app-button--secondary"
                      (click)="cancelCatalogForm()"
                      [disabled]="saving()"
                    >
                      Cancelar
                    </button>
                  }
                </div>
              </app-card>

              <app-card
                title="Especialidades"
                subtitle="Disponibles desde el perfil del taller."
              >
                @if (specialties().length) {
                  <div class="badge-group">
                    @for (sp of specialties(); track sp.id_especialidad) {
                      <span class="badge badge--info">{{ sp.nombre }}</span>
                    }
                  </div>
                } @else {
                  <app-empty-state
                    title="Sin especialidades"
                    message="Configura especialidades en la pestaña General."
                  />
                }
              </app-card>
            </div>

            @if (isCatalogFormVisible()) {
              <app-card
                [title]="catalogFormMode() === 'create' ? 'Agregar servicio' : 'Editar servicio'"
                subtitle="Define el servicio con su rango de precio base."
              >
                <form [formGroup]="catalogForm" (ngSubmit)="saveCatalogService()" class="catalog-form">
                  <div class="form-grid">
                    <label class="app-field">
                      <span class="app-field__label">Especialidad</span>
                      <select class="app-select" formControlName="id_especialidad">
                        <option [ngValue]="null">Selecciona una especialidad</option>
                        @for (sp of specialties(); track sp.id_especialidad) {
                          <option [ngValue]="sp.id_especialidad">{{ sp.nombre }}</option>
                        }
                      </select>
                      @if (hasCatalogError('id_especialidad', 'required')) {
                        <span class="field-error">La especialidad es obligatoria.</span>
                      }
                    </label>

                    <label class="app-field">
                      <span class="app-field__label">Nombre</span>
                      <input type="text" class="app-input" formControlName="nombre" placeholder="Cambio de batería, etc." />
                      @if (hasCatalogError('nombre', 'required')) {
                        <span class="field-error">El nombre es obligatorio.</span>
                      }
                    </label>

                    <label class="app-field app-field--full">
                      <span class="app-field__label">Descripción</span>
                      <textarea class="app-textarea" formControlName="descripcion" rows="3"></textarea>
                    </label>

                    <label class="app-field">
                      <span class="app-field__label">Precio base mínimo (BOB)</span>
                      <input type="number" step="0.01" class="app-input" formControlName="precio_base_min" />
                      @if (hasCatalogError('precio_base_min', 'required')) {
                        <span class="field-error">Obligatorio.</span>
                      } @else if (hasCatalogError('precio_base_min', 'min')) {
                        <span class="field-error">No negativo.</span>
                      }
                    </label>

                    <label class="app-field">
                      <span class="app-field__label">Precio base máximo (BOB)</span>
                      <input type="number" step="0.01" class="app-input" formControlName="precio_base_max" />
                      @if (hasCatalogError('precio_base_max', 'required')) {
                        <span class="field-error">Obligatorio.</span>
                      } @else if (hasCatalogError('precio_base_max', 'min')) {
                        <span class="field-error">No negativo.</span>
                      } @else if (catalogForm.hasError('priceRange')) {
                        <span class="field-error">Máximo debe ser >= mínimo.</span>
                      }
                    </label>

                    <label class="toggle-field">
                      <input type="checkbox" formControlName="incluye_repuestos_basicos" />
                      <div>
                        <span class="toggle-field__title">Incluye repuestos básicos</span>
                        <span class="toggle-field__hint">Indica si el rango base contempla repuestos menores.</span>
                      </div>
                    </label>
                  </div>

                  @if (catalogFormError()) {
                    <p class="feedback feedback--error">{{ catalogFormError() }}</p>
                  }

                  <div class="form-actions">
                    <button
                      type="submit"
                      class="app-button"
                      [disabled]="catalogForm.invalid || saving() || !hasSpecialties()"
                    >
                      {{ saving() ? 'Guardando...' : catalogFormMode() === 'create' ? 'Guardar servicio' : 'Guardar cambios' }}
                    </button>
                    <button type="button" class="app-button app-button--secondary" (click)="cancelCatalogForm()" [disabled]="saving()">
                      Cancelar
                    </button>
                  </div>
                </form>
              </app-card>
            }

            <app-card title="Servicios configurados" subtitle="Catálogo de servicios del taller.">
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
                            {{ item.incluye_repuestos_basicos ? 'Incluye repuestos' : 'Solo mano de obra' }}
                          </span>
                        </div>
                        <p class="catalog-item__desc text-muted">{{ item.descripcion || 'Sin descripción.' }}</p>
                        <div class="catalog-item__pricing">
                          <span class="text-muted">Rango base</span>
                          <strong>{{ formatCurrency(item.precio_base_min) }} – {{ formatCurrency(item.precio_base_max) }}</strong>
                        </div>
                      </div>
                      <div class="catalog-item__actions">
                        <button type="button" class="app-button app-button--ghost" (click)="startEditCatalog(item)" [disabled]="saving()">
                          Editar
                        </button>
                        @if (item.activo) {
                          <button type="button" class="app-button app-button--secondary" (click)="deactivateCatalog(item)" [disabled]="saving()">
                            Desactivar
                          </button>
                        } @else if (includeInactiveCatalog()) {
                          <button type="button" class="app-button app-button--secondary" (click)="activateCatalog(item)" [disabled]="saving()">
                            Activar
                          </button>
                        }
                      </div>
                    </article>
                  }
                </div>
              } @else if (!hasSpecialties()) {
                <app-empty-state title="Catálogo no disponible" message="Configura especialidades en la pestaña General." />
              } @else {
                <app-empty-state title="Sin servicios" message="Todavía no hay servicios en el catálogo.">
                  <button empty-actions type="button" class="app-button" (click)="startCreateCatalog()">
                    Agregar servicio
                  </button>
                </app-empty-state>
              }
            </app-card>
          </section>
        }

        <!-- ════════════════════════════════════════ STAFF TAB ════════════════════════════════════════ -->
        @if (activeTab() === 'staff') {
          <section class="tab-content">
            <div class="staff-kpis">
              <app-metric-card label="Total operarios" [value]="formatInteger(totalOperarios())" hint="Personal registrado" />
              <app-metric-card label="Disponibles" [value]="formatInteger(disponiblesCount())" hint="Listos para asignación" />
              <app-metric-card label="En servicio" [value]="formatInteger(enServicioCount())" hint="Atendiendo servicios" />
              <app-metric-card label="No disponibles / baja" [value]="formatInteger(noDisponiblesCount())" hint="Requieren atención" />
            </div>

            <div class="section-grid staff-header-grid">
              <app-card title="Disponibilidad" subtitle="Resumen del estado actual del equipo.">
                <div class="availability-grid">
                  <div class="availability-item">
                    <span class="text-muted">Disponibles</span>
                    <strong>{{ formatInteger(disponiblesCount()) }}</strong>
                  </div>
                  <div class="availability-item">
                    <span class="text-muted">En servicio</span>
                    <strong>{{ formatInteger(enServicioCount()) }}</strong>
                  </div>
                  <div class="availability-item">
                    <span class="text-muted">No disponibles</span>
                    <strong>{{ formatInteger(noDisponiblesStrictCount()) }}</strong>
                  </div>
                  <div class="availability-item">
                    <span class="text-muted">Baja</span>
                    <strong>{{ formatInteger(bajaCount()) }}</strong>
                  </div>
                </div>

                <div class="toolbar" style="margin-top: var(--space-4)">
                  @if (!isStaffFormVisible()) {
                    <button
                      type="button"
                      class="app-button"
                      (click)="startRegisterStaff()"
                      [disabled]="!hasSpecialties()"
                    >
                      Registrar operario
                    </button>
                  } @else {
                    <button
                      type="button"
                      class="app-button app-button--secondary"
                      (click)="cancelRegisterStaff()"
                      [disabled]="saving()"
                    >
                      Cancelar
                    </button>
                  }
                </div>
              </app-card>

              <app-card title="Especialidades" subtitle="Disponibles desde el perfil.">
                @if (specialties().length) {
                  <div class="badge-group">
                    @for (sp of specialties(); track sp.id_especialidad) {
                      <span class="badge badge--info">{{ sp.nombre }}</span>
                    }
                  </div>
                } @else {
                  <app-empty-state title="Sin especialidades" message="Configura desde la pestaña General." />
                }
              </app-card>
            </div>

            @if (isStaffFormVisible()) {
              <app-card title="Registrar operario" subtitle="Crea un perfil operativo con especialidades.">
                <form [formGroup]="staffForm" (ngSubmit)="saveStaff()" class="staff-form">
                  <div class="form-grid">
                    <label class="app-field">
                      <span class="app-field__label">Nombre</span>
                      <input type="text" class="app-input" formControlName="nombre" />
                      @if (hasStaffError(staffForm.get('nombre'), 'required')) {
                        <span class="field-error">Obligatorio.</span>
                      }
                    </label>
                    <label class="app-field">
                      <span class="app-field__label">Apellido</span>
                      <input type="text" class="app-input" formControlName="apellido" />
                      @if (hasStaffError(staffForm.get('apellido'), 'required')) {
                        <span class="field-error">Obligatorio.</span>
                      }
                    </label>
                    <label class="app-field">
                      <span class="app-field__label">CI</span>
                      <input type="text" class="app-input" formControlName="ci" />
                      @if (hasStaffError(staffForm.get('ci'), 'required')) {
                        <span class="field-error">Obligatorio.</span>
                      }
                    </label>
                    <label class="app-field">
                      <span class="app-field__label">Teléfono</span>
                      <input type="text" class="app-input" formControlName="telefono" />
                    </label>
                    <label class="app-field">
                      <span class="app-field__label">Email</span>
                      <input type="email" class="app-input" formControlName="email" />
                      @if (hasStaffError(staffForm.get('email'), 'required')) {
                        <span class="field-error">Obligatorio.</span>
                      } @else if (hasStaffError(staffForm.get('email'), 'email')) {
                        <span class="field-error">Email inválido.</span>
                      }
                    </label>
                    <label class="app-field">
                      <span class="app-field__label">Contraseña</span>
                      <input type="password" class="app-input" formControlName="password" />
                      @if (hasStaffError(staffForm.get('password'), 'required')) {
                        <span class="field-error">Obligatorio.</span>
                      } @else if (hasStaffError(staffForm.get('password'), 'minlength')) {
                        <span class="field-error">Mínimo 8 caracteres.</span>
                      }
                    </label>
                    <label class="app-field app-field--full">
                      <span class="app-field__label">Dirección</span>
                      <input type="text" class="app-input" formControlName="direccion" />
                    </label>
                  </div>

                  <section class="specialty-panel">
                    <header class="specialty-panel__header">
                      <h4>Especialidades del operario</h4>
                      <p class="text-muted">Selecciona al menos una y define su experiencia.</p>
                    </header>
                    @if (staffSpecialtyControls().length) {
                      <div class="specialty-options">
                        @for (ctrl of staffSpecialtyControls(); track ctrl.get('id_especialidad')?.value; let i = $index) {
                          <div class="specialty-option" [formGroup]="ctrl" [class.specialty-option--active]="ctrl.get('selected')?.value">
                            <label class="specialty-option__toggle">
                              <input type="checkbox" formControlName="selected" />
                              <span>{{ specialtyLabel(ctrl.get('id_especialidad')?.value) }}</span>
                            </label>
                            @if (ctrl.get('selected')?.value) {
                              <div class="specialty-option__details">
                                <label class="app-field">
                                  <span class="app-field__label">Años de experiencia</span>
                                  <input type="number" min="0" class="app-input" formControlName="anios_experiencia" />
                                </label>
                                <label class="app-field">
                                  <span class="app-field__label">URL certificación</span>
                                  <input type="url" class="app-input" formControlName="certificacion_url" />
                                </label>
                              </div>
                            }
                          </div>
                        }
                      </div>
                    }
                    @if (hasStaffSpecialtyError()) {
                      <p class="feedback feedback--error">Selecciona al menos una especialidad.</p>
                    }
                  </section>

                  @if (staffFormError()) {
                    <p class="feedback feedback--error">{{ staffFormError() }}</p>
                  }

                  <div class="form-actions">
                    <button type="submit" class="app-button" [disabled]="staffForm.invalid || saving() || !hasSpecialties()">
                      {{ saving() ? 'Guardando...' : 'Guardar operario' }}
                    </button>
                    <button type="button" class="app-button app-button--secondary" (click)="cancelRegisterStaff()" [disabled]="saving()">
                      Cancelar
                    </button>
                  </div>
                </form>
              </app-card>
            }

            <app-card title="Equipo técnico" subtitle="Listado de operarios del taller.">
              @if (staffItems().length) {
                <div class="staff-list">
                  @for (item of staffItems(); track item.operario_id) {
                    <article class="staff-card" [class.staff-card--inactive]="!item.activo">
                      <div class="staff-card__main">
                        <div class="staff-card__heading">
                          <strong>{{ item.nombre_completo }}</strong>
                          <app-status-badge [label]="item.estado_disponibilidad" />
                          <app-status-badge [label]="item.activo ? 'CONFIRMADO' : 'BAJA'" />
                        </div>
                        <div class="staff-card__contact">
                          <span><strong>CI:</strong> {{ item.ci }}</span>
                          <span><strong>Email:</strong> {{ item.email }}</span>
                          <span><strong>Tel:</strong> {{ item.telefono || '—' }}</span>
                          @if (item.registered_at) {
                            <span><strong>Registro:</strong> {{ formatDate(item.registered_at) }}</span>
                          }
                        </div>
                        <div class="staff-card__specialties">
                          @for (sp of item.specialties; track sp.id_especialidad) {
                            <div class="specialty-chip">
                              <span class="badge badge--info">{{ sp.nombre }}</span>
                              <small class="text-muted">{{ sp.anios_experiencia }} año(s)</small>
                              @if (sp.certificacion_url) {
                                <a [href]="sp.certificacion_url" target="_blank" rel="noopener noreferrer" class="specialty-chip__link">Certificación</a>
                              }
                            </div>
                          }
                        </div>
                      </div>
                      <div class="staff-card__actions">
                        <label class="app-field">
                          <span class="app-field__label">Disponibilidad</span>
                          <select
                            class="app-select"
                            [value]="getStaffDraft(item)"
                            (change)="setStaffDraft(item.operario_id, $event)"
                          >
                            @for (status of availabilityOptions; track status) {
                              <option [value]="status">{{ status }}</option>
                            }
                          </select>
                        </label>
                        <button
                          type="button"
                          class="app-button app-button--secondary"
                          (click)="applyStaffAvailability(item)"
                          [disabled]="saving() || getStaffDraft(item) === item.estado_disponibilidad"
                        >
                          Aplicar
                        </button>
                      </div>
                    </article>
                  }
                </div>
              } @else if (!hasSpecialties()) {
                <app-empty-state title="No se puede registrar" message="Primero configura especialidades." />
              } @else {
                <app-empty-state title="Sin operarios" message="No hay personal registrado aún.">
                  <button empty-actions type="button" class="app-button" (click)="startRegisterStaff()">
                    Registrar operario
                  </button>
                </app-empty-state>
              }
            </app-card>
          </section>
        }
      }
    </div>
  `,
  styles: [
    `
      .toolbar--tight { justify-content: flex-end; }
      .toolbar { display: flex; align-items: center; gap: var(--space-3); flex-wrap: wrap; }

      .tabs {
        display: flex;
        gap: var(--space-2);
        margin-bottom: var(--space-6);
        border-bottom: 1px solid var(--color-border);
        padding-bottom: 0;
      }
      .tab {
        display: inline-flex;
        align-items: center;
        gap: var(--space-2);
        padding: 0.75rem 1.25rem;
        border: 0;
        border-bottom: 2px solid transparent;
        background: none;
        color: var(--color-text-muted);
        font-size: 0.92rem;
        font-weight: 600;
        cursor: pointer;
        transition: color 0.15s, border-color 0.15s;
        font-family: inherit;
      }
      .tab:hover { color: var(--color-text); }
      .tab--active {
        color: var(--color-primary);
        border-bottom-color: var(--color-primary);
      }
      .tab__badge {
        display: inline-grid;
        place-items: center;
        min-width: 1.5rem;
        height: 1.5rem;
        padding: 0 0.35rem;
        border-radius: 999px;
        background: color-mix(in srgb, var(--color-primary) 14%, transparent);
        color: var(--color-primary);
        font-size: 0.75rem;
        font-weight: 800;
      }
      .tab-content { display: flex; flex-direction: column; gap: var(--space-5); }

      .feedback {
        padding: var(--space-3) var(--space-4);
        border-radius: var(--radius-md);
        font-size: 0.88rem;
        line-height: 1.4;
      }
      .feedback--success { background: color-mix(in srgb, var(--color-success) 14%, transparent); color: var(--color-success); }
      .feedback--error { background: color-mix(in srgb, var(--color-danger) 14%, transparent); color: var(--color-danger); }

      .profile-summary {
        display: flex;
        flex-direction: column;
        gap: var(--space-5);
        padding: var(--space-6);
        border: 1px solid var(--color-border);
        border-radius: var(--radius-xl);
        background: color-mix(in srgb, var(--color-surface-soft) 92%, transparent);
      }
      .profile-summary__header {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: var(--space-4);
        flex-wrap: wrap;
      }
      .profile-summary__name {
        margin: 0 0 var(--space-2);
        font-size: 1.45rem;
      }
      .profile-summary__desc {
        margin: 0;
        line-height: 1.6;
        color: var(--color-text-muted);
      }
      .profile-summary__grid {
        display: grid;
        gap: var(--space-4);
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      }
      .profile-summary__field { display: flex; flex-direction: column; gap: var(--space-1); }
      .field-label {
        font-size: 0.78rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--color-text-muted);
      }
      .profile-summary__specialties { display: flex; flex-direction: column; gap: var(--space-2); }

      .badge-group { display: flex; flex-wrap: wrap; gap: var(--space-2); }

      .profile-form, .catalog-form, .staff-form {
        display: flex;
        flex-direction: column;
        gap: var(--space-5);
      }
      .form-grid {
        display: grid;
        gap: var(--space-4);
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      }
      .app-field--full { grid-column: 1 / -1; }
      .field-error { font-size: 0.88rem; color: var(--color-danger); }
      .form-actions { display: flex; align-items: center; gap: var(--space-4); flex-wrap: wrap; }

      .toggle-field {
        display: flex;
        align-items: flex-start;
        gap: var(--space-3);
        padding: var(--space-4);
        border: 1px solid var(--color-border);
        border-radius: var(--radius-lg);
        background: color-mix(in srgb, var(--color-surface-soft) 92%, transparent);
        grid-column: 1 / -1;
      }
      .toggle-field input { margin-top: 0.25rem; }
      .toggle-field__title { display: block; font-weight: 700; }
      .toggle-field__hint { display: block; margin-top: var(--space-1); color: var(--color-text-muted); font-size: 0.86rem; }

      .specialty-selector { padding: var(--space-4); border: 1px solid var(--color-border); border-radius: var(--radius-lg); }
      .specialty-selector__header h4 { margin: 0; }
      .specialty-selector__options {
        display: flex;
        flex-wrap: wrap;
        gap: var(--space-3);
        margin-top: var(--space-4);
      }
      .specialty-check {
        display: inline-flex;
        align-items: center;
        gap: var(--space-2);
        padding: 0.4rem 0.7rem;
        border-radius: var(--radius-md);
        border: 1px solid var(--color-border);
        cursor: pointer;
        font-size: 0.9rem;
      }

      .toggle-inline { display: inline-flex; align-items: center; gap: var(--space-2); }

      .catalog-header-grid, .staff-header-grid { align-items: start; }

      .catalog-list, .staff-list { display: flex; flex-direction: column; gap: var(--space-4); }
      .catalog-item, .staff-card {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: var(--space-5);
        padding: var(--space-5);
        border: 1px solid var(--color-border);
        border-radius: var(--radius-lg);
        background: color-mix(in srgb, var(--color-surface-soft) 92%, transparent);
      }
      .catalog-item--inactive, .staff-card--inactive { opacity: 0.72; }
      .catalog-item__main, .staff-card__main { min-width: 0; flex: 1; }
      .catalog-item__heading, .staff-card__heading { display: flex; align-items: center; gap: var(--space-3); flex-wrap: wrap; }
      .catalog-item__meta, .staff-card__contact { display: flex; flex-wrap: wrap; gap: var(--space-3); margin-top: var(--space-3); }
      .catalog-item__desc { margin: var(--space-3) 0; line-height: 1.6; }
      .catalog-item__pricing { display: flex; gap: var(--space-3); align-items: center; }
      .catalog-item__actions, .staff-card__actions { display: flex; flex-direction: column; gap: var(--space-3); min-width: 140px; }
      .staff-card__contact { color: var(--color-text-muted); }
      .staff-card__specialties { display: flex; flex-direction: column; gap: var(--space-2); margin-top: var(--space-3); }

      .specialty-chip { display: flex; align-items: center; gap: var(--space-2); flex-wrap: wrap; }
      .specialty-chip__link { color: var(--color-primary); text-decoration: none; }
      .specialty-chip__link:hover { text-decoration: underline; }

      @media (max-width: 820px) {
        .catalog-item, .staff-card { flex-direction: column; }
        .catalog-item__actions, .staff-card__actions { width: 100%; min-width: 0; flex-direction: row; flex-wrap: wrap; }
      }

      .staff-kpis { display: grid; gap: var(--space-4); grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); }
      .availability-grid { display: grid; gap: var(--space-4); grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); }
      .availability-item { display: flex; flex-direction: column; gap: var(--space-1); }

      .specialty-panel {
        padding: var(--space-5);
        border: 1px solid var(--color-border);
        border-radius: var(--radius-lg);
        background: color-mix(in srgb, var(--color-surface-soft) 90%, transparent);
      }
      .specialty-panel__header h4 { margin: 0; }
      .specialty-panel__header p { margin: var(--space-2) 0 0; }
      .specialty-options { display: flex; flex-direction: column; gap: var(--space-4); margin-top: var(--space-4); }
      .specialty-option { padding: var(--space-4); border: 1px solid var(--color-border); border-radius: var(--radius-lg); background: var(--color-surface); }
      .specialty-option--active { border-color: color-mix(in srgb, var(--color-primary) 32%, var(--color-border)); }
      .specialty-option__toggle { display: inline-flex; align-items: center; gap: var(--space-3); font-weight: 700; cursor: pointer; }
      .specialty-option__details { display: grid; gap: var(--space-4); grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); margin-top: var(--space-4); }

      .catalog-note { margin: var(--space-3) 0 0; }
    `,
  ],
})
export class WorkshopManagementPage {
  /* ── Dependencies ───────────────────────────────────────────────── */
  private readonly profileApi = inject(WorkshopProfileApi);
  private readonly catalogApi = inject(WorkshopCatalogApi);
  private readonly staffApi = inject(WorkshopStaffApi);
  private readonly destroyRef = inject(DestroyRef);
  private readonly fb = inject(FormBuilder);

  /* ── Shared state ───────────────────────────────────────────────── */
  protected readonly activeTab = signal<TabId>('general');
  protected readonly loading = signal(false);
  protected readonly saving = signal(false);
  protected readonly pageError = signal('');

  protected readonly profile = signal<WorkshopProfileResponse | null>(null);
  protected readonly specialties = computed(() => this.profile()?.specialties ?? []);
  protected readonly hasSpecialties = computed(() => this.specialties().length > 0);

  /* ── General tab state ──────────────────────────────────────────── */
  protected readonly editMode = signal(false);
  protected readonly saveError = signal('');
  protected readonly saveSuccess = signal('');
  protected readonly selectedSpecialtyIds = signal<Set<number>>(new Set());

  protected readonly profileForm = this.fb.group({
    nombre_comercial: ['', [Validators.required]],
    descripcion: [''],
    direccion: [''],
    ciudad: [''],
    zona: [''],
    referencia: [''],
    latitud: [0],
    longitud: [0],
    radio_accion_km: [0, [Validators.required, Validators.min(0.1)]],
    acepta_seguro_propio: [false],
  });

  /* ── Catalog tab state ──────────────────────────────────────────── */
  protected readonly catalogItems = signal<WorkshopCatalogServiceResponse[]>([]);
  protected readonly catalogFormMode = signal<CatalogFormMode>(null);
  protected readonly editingCatalogId = signal<number | null>(null);
  protected readonly includeInactiveCatalog = signal(false);
  protected readonly catalogFormError = signal('');

  protected readonly catalogForm = this.fb.group(
    {
      id_especialidad: [null as number | null, [Validators.required]],
      nombre: ['', [Validators.required]],
      descripcion: [''],
      precio_base_min: [null as number | null, [Validators.required, Validators.min(0)]],
      precio_base_max: [null as number | null, [Validators.required, Validators.min(0)]],
      incluye_repuestos_basicos: [false],
    },
    {
      validators: [(group) => {
        const min = Number(group.get('precio_base_min')?.value);
        const max = Number(group.get('precio_base_max')?.value);
        if (!Number.isFinite(min) || !Number.isFinite(max)) return null;
        return max >= min ? null : { priceRange: true };
      }],
    },
  );

  protected readonly isCatalogFormVisible = computed(() => this.catalogFormMode() !== null);

  /* ── Staff tab state ────────────────────────────────────────────── */
  protected readonly staffItems = signal<WorkshopStaffSummary[]>([]);
  protected readonly isStaffFormVisible = signal(false);
  protected readonly staffFormError = signal('');
  protected readonly availabilityDrafts = signal<Record<number, string>>({});

  protected readonly availabilityOptions = [
    'DISPONIBLE',
    'EN_SERVICIO',
    'NO_DISPONIBLE',
    'BAJA',
  ] as const;

  protected readonly staffForm = this.fb.group({
    nombre: ['', [Validators.required]],
    apellido: ['', [Validators.required]],
    ci: ['', [Validators.required]],
    telefono: [''],
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(8)]],
    direccion: [''],
    specialties: this.fb.array([], {
      validators: [(ctrl) => this.validateStaffSpecialties(ctrl)],
    }),
  });

  protected readonly totalOperarios = computed(() => this.staffItems().length);
  protected readonly disponiblesCount = computed(() =>
    this.staffItems().filter((i) => i.estado_disponibilidad === 'DISPONIBLE').length,
  );
  protected readonly enServicioCount = computed(() =>
    this.staffItems().filter((i) => i.estado_disponibilidad === 'EN_SERVICIO').length,
  );
  protected readonly noDisponiblesStrictCount = computed(() =>
    this.staffItems().filter((i) => i.estado_disponibilidad === 'NO_DISPONIBLE').length,
  );
  protected readonly bajaCount = computed(() =>
    this.staffItems().filter((i) => i.estado_disponibilidad === 'BAJA').length,
  );
  protected readonly noDisponiblesCount = computed(() =>
    this.noDisponiblesStrictCount() + this.bajaCount(),
  );

  constructor() {
    this.reload();
  }

  /* ════════════════════════════════════════════════════════════════════
     INITIALIZATION
     ════════════════════════════════════════════════════════════════════ */
  protected reload(): void {
    this.loading.set(true);
    this.pageError.set('');
    this.saveError.set('');
    this.saveSuccess.set('');

    this.profileApi.getProfile().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (response) => {
        this.profile.set(response);
        this.selectedSpecialtyIds.set(new Set(response.specialties.filter((s) => s.activo).map((s) => s.id_especialidad)));
        this.rebuildStaffSpecialtiesForm(response.specialties);
        this.loadCatalog();
        this.loadStaff();
      },
      error: (err) => {
        this.pageError.set(
          this.extractErrorMessage(err, 'No se pudo cargar la información del taller.'),
        );
        this.loading.set(false);
      },
    });
  }

  /* ════════════════════════════════════════════════════════════════════
     GENERAL TAB
     ════════════════════════════════════════════════════════════════════ */
  protected startEditProfile(): void {
    this.editMode.set(true);
    this.saveError.set('');
    this.saveSuccess.set('');
    const p = this.profile()!;
    this.profileForm.reset({
      nombre_comercial: p.nombre_comercial,
      descripcion: p.descripcion ?? '',
      direccion: p.direccion ?? '',
      ciudad: p.ciudad ?? '',
      zona: p.zona ?? '',
      referencia: p.referencia ?? '',
      latitud: this.toNumber(p.latitud),
      longitud: this.toNumber(p.longitud),
      radio_accion_km: this.toNumber(p.radio_accion_km),
      acepta_seguro_propio: p.acepta_seguro_propio,
    }, { emitEvent: false });
  }

  protected cancelEditProfile(): void {
    this.editMode.set(false);
    this.saveError.set('');
  }

  protected toggleSpecialty(id: number): void {
    this.selectedSpecialtyIds.update((set) => {
      const next = new Set(set);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }

  protected saveProfile(): void {
    if (this.profileForm.invalid || this.saving()) {
      this.profileForm.markAllAsTouched();
      return;
    }

    const raw = this.profileForm.getRawValue();
    const payload: WorkshopProfileUpdateRequest = {
      nombre_comercial: String(raw.nombre_comercial ?? '').trim(),
      descripcion: this.normalizeOptional(String(raw.descripcion ?? '')),
      latitud: Number(raw.latitud),
      longitud: Number(raw.longitud),
      direccion: this.normalizeOptional(String(raw.direccion ?? '')),
      ciudad: this.normalizeOptional(String(raw.ciudad ?? '')),
      zona: this.normalizeOptional(String(raw.zona ?? '')),
      referencia: this.normalizeOptional(String(raw.referencia ?? '')),
      radio_accion_km: Number(raw.radio_accion_km),
      specialty_ids: [...this.selectedSpecialtyIds()],
      acepta_seguro_propio: Boolean(raw.acepta_seguro_propio),
    };

    this.saving.set(true);
    this.saveError.set('');
    this.saveSuccess.set('');

    this.profileApi.updateProfile(payload).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (updated) => {
        this.profile.set(updated);
        this.saving.set(false);
        this.editMode.set(false);
        this.saveSuccess.set('Perfil actualizado correctamente.');
      },
      error: (err) => {
        this.saveError.set(this.extractErrorMessage(err, 'No se pudo actualizar el perfil.'));
        this.saving.set(false);
      },
    });
  }

  protected formatAddress(): string {
    const p = this.profile();
    if (!p) return '—';
    const parts = [p.direccion, p.zona, p.ciudad].filter(Boolean);
    return parts.length ? parts.join(', ') : 'Sin dirección registrada';
  }

  /* ════════════════════════════════════════════════════════════════════
     CATALOG TAB
     ════════════════════════════════════════════════════════════════════ */
  protected switchToCatalog(): void {
    this.activeTab.set('catalog');
  }

  protected toggleIncludeInactive(event: Event): void {
    this.includeInactiveCatalog.set((event.target as HTMLInputElement)?.checked ?? false);
    this.loadCatalog();
  }

  protected startCreateCatalog(): void {
    if (!this.hasSpecialties()) return;
    this.catalogFormMode.set('create');
    this.editingCatalogId.set(null);
    this.catalogFormError.set('');
    this.catalogForm.reset({
      id_especialidad: null,
      nombre: '',
      descripcion: '',
      precio_base_min: null,
      precio_base_max: null,
      incluye_repuestos_basicos: false,
    }, { emitEvent: false });
  }

  protected startEditCatalog(item: WorkshopCatalogServiceResponse): void {
    this.catalogFormMode.set('edit');
    this.editingCatalogId.set(item.catalog_id);
    this.catalogFormError.set('');
    this.catalogForm.reset({
      id_especialidad: item.id_especialidad,
      nombre: item.nombre,
      descripcion: item.descripcion ?? '',
      precio_base_min: this.toNumber(item.precio_base_min),
      precio_base_max: this.toNumber(item.precio_base_max),
      incluye_repuestos_basicos: item.incluye_repuestos_basicos,
    }, { emitEvent: false });
  }

  protected cancelCatalogForm(): void {
    this.catalogFormMode.set(null);
    this.editingCatalogId.set(null);
    this.catalogFormError.set('');
  }

  protected saveCatalogService(): void {
    if (this.catalogForm.invalid || this.saving() || !this.hasSpecialties()) {
      this.catalogForm.markAllAsTouched();
      return;
    }

    const raw = this.catalogForm.getRawValue();
    const id_especialidad = Number(raw.id_especialidad);
    const precio_base_min = Number(raw.precio_base_min);
    const precio_base_max = Number(raw.precio_base_max);
    const nombre = String(raw.nombre ?? '').trim();

    if (!Number.isInteger(id_especialidad) || id_especialidad <= 0) {
      this.catalogFormError.set('Especialidad inválida.');
      return;
    }
    if (!Number.isFinite(precio_base_min) || precio_base_min < 0) {
      this.catalogFormError.set('Precio mínimo inválido.');
      return;
    }
    if (!Number.isFinite(precio_base_max) || precio_base_max < 0) {
      this.catalogFormError.set('Precio máximo inválido.');
      return;
    }
    if (precio_base_max < precio_base_min) {
      this.catalogFormError.set('El precio máximo debe ser >= al mínimo.');
      return;
    }
    if (!nombre) {
      this.catalogFormError.set('El nombre es obligatorio.');
      return;
    }

    const base: WorkshopCatalogServiceCreateRequest = {
      id_especialidad,
      nombre,
      descripcion: this.normalizeOptional(raw.descripcion),
      precio_base_min,
      precio_base_max,
      incluye_repuestos_basicos: Boolean(raw.incluye_repuestos_basicos),
    };

    this.saving.set(true);
    this.catalogFormError.set('');

    if (this.catalogFormMode() === 'edit' && this.editingCatalogId()) {
      this.catalogApi.updateCatalogService(this.editingCatalogId()!, base)
        .pipe(takeUntilDestroyed(this.destroyRef))
        .subscribe({
          next: () => { this.saving.set(false); this.cancelCatalogForm(); this.loadCatalog(); },
          error: (err) => {
            this.catalogFormError.set(this.extractErrorMessage(err, 'No se pudo actualizar.'));
            this.saving.set(false);
          },
        });
    } else {
      this.catalogApi.createCatalogService(base)
        .pipe(takeUntilDestroyed(this.destroyRef))
        .subscribe({
          next: () => { this.saving.set(false); this.cancelCatalogForm(); this.loadCatalog(); },
          error: (err) => {
            this.catalogFormError.set(this.extractErrorMessage(err, 'No se pudo crear.'));
            this.saving.set(false);
          },
        });
    }
  }

  protected deactivateCatalog(item: WorkshopCatalogServiceResponse): void {
    if (this.saving()) return;
    if (!window.confirm(`¿Desactivar "${item.nombre}"?`)) return;
    this.saving.set(true);
    this.catalogApi.deactivateCatalogService(item.catalog_id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => { this.saving.set(false); this.loadCatalog(); },
        error: (err) => {
          this.pageError.set(this.extractErrorMessage(err, 'No se pudo desactivar.'));
          this.saving.set(false);
        },
      });
  }

  protected activateCatalog(item: WorkshopCatalogServiceResponse): void {
    if (this.saving()) return;
    this.saving.set(true);
    this.catalogApi.activateCatalogService(item.catalog_id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => { this.saving.set(false); this.loadCatalog(); },
        error: (err) => {
          this.pageError.set(this.extractErrorMessage(err, 'No se pudo activar.'));
          this.saving.set(false);
        },
      });
  }

  protected hasCatalogError(
    name: 'id_especialidad' | 'nombre' | 'precio_base_min' | 'precio_base_max',
    key: string,
  ): boolean {
    const ctrl = this.catalogForm.get(name);
    return Boolean(ctrl?.touched && ctrl.hasError(key));
  }

  /* ════════════════════════════════════════════════════════════════════
     STAFF TAB
     ════════════════════════════════════════════════════════════════════ */
  protected switchToStaff(): void {
    this.activeTab.set('staff');
  }

  protected get staffSpecialtiesArray(): FormArray {
    return this.staffForm.get('specialties') as FormArray;
  }

  protected staffSpecialtyControls(): FormGroup[] {
    return this.staffSpecialtiesArray.controls as FormGroup[];
  }

  protected startRegisterStaff(): void {
    if (!this.hasSpecialties()) return;
    this.staffFormError.set('');
    this.resetStaffForm();
    this.isStaffFormVisible.set(true);
  }

  protected cancelRegisterStaff(): void {
    this.staffFormError.set('');
    this.isStaffFormVisible.set(false);
  }

  protected saveStaff(): void {
    if (this.staffForm.invalid || this.saving() || !this.hasSpecialties()) {
      this.staffForm.markAllAsTouched();
      this.staffSpecialtyControls().forEach((g) => g.markAllAsTouched());
      return;
    }

    const raw = this.staffForm.getRawValue();
    const specialties: StaffSpecialtyInput[] = [];

    for (const group of this.staffSpecialtyControls()) {
      if (!group.get('selected')?.value) continue;
      const id_especialidad = Number(group.get('id_especialidad')?.value);
      const anios_experiencia = Number(group.get('anios_experiencia')?.value ?? 0);
      if (!Number.isInteger(id_especialidad) || id_especialidad <= 0) {
        this.staffFormError.set('ID de especialidad inválido.');
        return;
      }
      specialties.push({
        id_especialidad,
        anios_experiencia,
        certificacion_url: this.normalizeOptional(group.get('certificacion_url')?.value),
      });
    }

    if (!specialties.length) {
      this.staffFormError.set('Selecciona al menos una especialidad.');
      return;
    }

    const payload: WorkshopStaffCreateRequest = {
      nombre: String(raw.nombre ?? '').trim(),
      apellido: String(raw.apellido ?? '').trim(),
      ci: String(raw.ci ?? '').trim(),
      email: String(raw.email ?? '').trim(),
      password: String(raw.password ?? ''),
      telefono: this.normalizeOptional(String(raw.telefono ?? '').trim()),
      direccion: this.normalizeOptional(String(raw.direccion ?? '').trim()),
      specialties,
    };

    this.saving.set(true);
    this.staffFormError.set('');

    this.staffApi.createStaff(payload).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: () => { this.saving.set(false); this.cancelRegisterStaff(); this.loadStaff(); },
      error: (err) => {
        this.staffFormError.set(this.extractErrorMessage(err, 'No se pudo registrar.'));
        this.saving.set(false);
      },
    });
  }

  protected setStaffDraft(operarioId: number, event: Event): void {
    const value = (event.target as HTMLSelectElement)?.value ?? '';
    this.availabilityDrafts.update((d) => ({ ...d, [operarioId]: value }));
  }

  protected getStaffDraft(item: WorkshopStaffSummary): string {
    return this.availabilityDrafts()[item.operario_id] ?? item.estado_disponibilidad;
  }

  protected applyStaffAvailability(item: WorkshopStaffSummary): void {
    const next = this.getStaffDraft(item);
    if (this.saving() || next === item.estado_disponibilidad) return;

    if (next === 'BAJA' && !window.confirm(`¿Marcar a ${item.nombre_completo} como BAJA?`)) {
      this.availabilityDrafts.update((d) => ({ ...d, [item.operario_id]: item.estado_disponibilidad }));
      return;
    }

    this.saving.set(true);
    this.staffApi.updateAvailability(item.operario_id, { new_status: next as StaffAvailabilityStatus })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (updated) => {
          this.saving.set(false);
          this.staffItems.update((items) =>
            items.map((i) => i.operario_id === updated.operario_id ? updated : i),
          );
          this.availabilityDrafts.update((d) => ({ ...d, [updated.operario_id]: updated.estado_disponibilidad }));
        },
        error: (err) => {
          this.pageError.set(this.extractErrorMessage(err, 'No se pudo actualizar disponibilidad.'));
          this.saving.set(false);
        },
      });
  }

  protected specialtyLabel(id: number | null | undefined): string {
    const match = this.specialties().find((s) => s.id_especialidad === Number(id));
    return match?.nombre ?? `Especialidad #${id ?? '-'}`;
  }

  protected hasStaffError(ctrl: AbstractControl | null, key: string): boolean {
    return Boolean(ctrl?.touched && ctrl.hasError(key));
  }

  protected hasStaffSpecialtyError(): boolean {
    return Boolean(this.staffSpecialtiesArray.touched && this.staffSpecialtiesArray.hasError('specialtyRequired'));
  }

  /* ════════════════════════════════════════════════════════════════════
     UTILITY
     ════════════════════════════════════════════════════════════════════ */
  protected formatCurrency(value: string | number): string {
    return `BOB ${new Intl.NumberFormat('es-BO', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(this.toNumber(value))}`;
  }

  protected formatInteger(value: number): string {
    return new Intl.NumberFormat('es-BO', { maximumFractionDigits: 0 }).format(value);
  }

  protected formatDate(value: string): string {
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return value;
    return new Intl.DateTimeFormat('es-BO', { dateStyle: 'medium', timeStyle: 'short' }).format(d);
  }

  private loadCatalog(): void {
    this.catalogApi.listCatalog(this.includeInactiveCatalog())
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (items) => {
          this.catalogItems.set(items);
          this.loading.set(false);
        },
        error: (err) => {
          this.pageError.set(this.extractErrorMessage(err, 'No se pudo cargar el catálogo.'));
          this.loading.set(false);
        },
      });
  }

  private loadStaff(): void {
    this.staffApi.listStaff().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (items) => {
        this.staffItems.set(items);
        this.availabilityDrafts.set(Object.fromEntries(items.map((i) => [i.operario_id, i.estado_disponibilidad])));
        this.loading.set(false);
      },
      error: (err) => {
        this.pageError.set(this.extractErrorMessage(err, 'No se pudo cargar el personal.'));
        this.loading.set(false);
      },
    });
  }

  private rebuildStaffSpecialtiesForm(specialties: WorkshopConfiguredSpecialty[]): void {
    const groups = specialties.map((sp) =>
      this.fb.group({
        selected: [false],
        id_especialidad: [sp.id_especialidad],
        anios_experiencia: [0, [Validators.min(0)]],
        certificacion_url: [''],
      }),
    );
    (this.staffForm as FormGroup).setControl(
      'specialties',
      this.fb.array(groups, { validators: [(ctrl: AbstractControl) => this.validateStaffSpecialties(ctrl)] }),
    );
  }

  private resetStaffForm(): void {
    this.staffForm.reset({
      nombre: '', apellido: '', ci: '', telefono: '', email: '', password: '', direccion: '',
    }, { emitEvent: false });
    this.rebuildStaffSpecialtiesForm(this.specialties());
  }

  private validateStaffSpecialties(control: AbstractControl) {
    const arr = control as FormArray;
    const count = arr.controls.filter((c) => c.get('selected')?.value).length;
    return count > 0 ? null : { specialtyRequired: true };
  }

  private toNumber(value: string | number | null | undefined): number {
    const n = Number(value ?? 0);
    return Number.isFinite(n) ? n : 0;
  }

  private normalizeOptional(value: string | null | undefined): string | null {
    const s = String(value ?? '').trim();
    return s || null;
  }

  private extractErrorMessage(error: unknown, fallback: string): string {
    if (error instanceof HttpErrorResponse) {
      const detail = error.error?.detail;
      if (typeof detail === 'string' && detail.trim()) return localizeBackendMessage(detail);
      if (Array.isArray(detail)) {
        const msgs = detail.map((item: unknown) => {
          if (typeof item === 'string') return item;
          if (item && typeof item === 'object' && 'msg' in item) return String((item as { msg?: unknown }).msg ?? '');
          return '';
        }).filter(Boolean);
        if (msgs.length) return localizeBackendMessage(msgs.join(' '));
      }
      if (typeof error.error === 'string' && error.error.trim()) return localizeBackendMessage(error.error);
      if (error.status === 403) return 'No tienes permisos para esta acción.';
    }
    return fallback;
  }
}
