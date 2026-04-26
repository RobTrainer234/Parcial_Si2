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
import { WorkshopProfileApi } from '../data-access/workshop-profile.api';
import {
  WorkshopMediaFileResponse,
  WorkshopProfileResponse,
  WorkshopProfileUpdateRequest,
} from '../data-access/workshop-profile.models';

@Component({
  selector: 'app-workshop-profile-page',
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
        eyebrow="Configuración operativa"
        title="Perfil del taller"
        subtitle="Configura la información operativa que verá el sistema para recomendar y gestionar tu taller."
      >
        @if (!isEditingProfile()) {
          <button
            page-actions
            type="button"
            class="app-button"
            (click)="startEditing()"
            [disabled]="loading()"
          >
            Editar perfil
          </button>
        } @else {
          <button
            page-actions
            type="button"
            class="app-button app-button--secondary"
            (click)="cancelEditing()"
            [disabled]="saving()"
          >
            Cancelar edición
          </button>
        }
      </app-page-header>

      @if (loading() && !profile()) {
        <app-loading-state
          title="Cargando perfil"
          message="Consultando la configuración real del taller y sus archivos vinculados."
        />
      } @else if (pageError() && !profile()) {
        <app-error-state [message]="pageError()">
          <button error-actions type="button" class="app-button" (click)="reload()">
            Reintentar
          </button>
        </app-error-state>
      } @else if (profile(); as data) {
        <section class="profile-layout">
          <app-card
            class="profile-layout__main"
            title="Datos del taller"
            subtitle="Resumen operativo visible por defecto para el administrador."
          >
            <div class="summary-block">
              <div class="summary-block__row">
                <span class="summary-block__label">Nombre comercial</span>
                <strong>{{ data.nombre_comercial }}</strong>
              </div>
              <div class="summary-block__row">
                <span class="summary-block__label">Descripción</span>
                <p class="summary-block__text">
                  {{ data.descripcion || 'Sin descripción registrada.' }}
                </p>
              </div>
              <div class="summary-grid">
                <div class="summary-item">
                  <span class="text-muted">Latitud</span>
                  <strong>{{ formatNumber(data.latitud) }}</strong>
                </div>
                <div class="summary-item">
                  <span class="text-muted">Longitud</span>
                  <strong>{{ formatNumber(data.longitud) }}</strong>
                </div>
                <div class="summary-item">
                  <span class="text-muted">Radio de acción</span>
                  <strong>{{ formatNumber(data.radio_accion_km) }} km</strong>
                </div>
                <div class="summary-item">
                  <span class="text-muted">Seguro propio</span>
                  <strong>{{ data.acepta_seguro_propio ? 'Activo' : 'Desactivado' }}</strong>
                </div>
              </div>
            </div>

            @if (isEditingProfile()) {
              <section class="inline-panel">
                <div class="inline-panel__header">
                  <div>
                    <h4>Editar perfil</h4>
                    <p class="text-muted">
                      Actualiza solo los campos operativos compatibles con el backend actual.
                    </p>
                  </div>
                </div>

                <form class="profile-form" [formGroup]="profileForm" (ngSubmit)="saveProfile()">
                  <div class="form-grid">
                    <label class="app-field">
                      <span class="app-field__label">Nombre comercial</span>
                      <input
                        type="text"
                        class="app-input"
                        formControlName="nombre_comercial"
                        placeholder="Nombre visible del taller"
                      />
                      @if (hasError('nombre_comercial', 'required')) {
                        <span class="field-error">El nombre comercial es obligatorio.</span>
                      }
                    </label>

                    <label class="app-field app-field--full">
                      <span class="app-field__label">Descripción</span>
                      <textarea
                        class="app-textarea"
                        formControlName="descripcion"
                        rows="4"
                        placeholder="Descripción operativa del taller"
                      ></textarea>
                    </label>

                    <label class="app-field">
                      <span class="app-field__label">Latitud</span>
                      <input
                        type="number"
                        step="0.000001"
                        class="app-input"
                        formControlName="latitud"
                        placeholder="-17.7833"
                      />
                      @if (hasError('latitud', 'required')) {
                        <span class="field-error">La latitud es obligatoria.</span>
                      } @else if (hasError('latitud', 'min') || hasError('latitud', 'max')) {
                        <span class="field-error">La latitud debe estar entre -90 y 90.</span>
                      }
                    </label>

                    <label class="app-field">
                      <span class="app-field__label">Longitud</span>
                      <input
                        type="number"
                        step="0.000001"
                        class="app-input"
                        formControlName="longitud"
                        placeholder="-63.1821"
                      />
                      @if (hasError('longitud', 'required')) {
                        <span class="field-error">La longitud es obligatoria.</span>
                      } @else if (hasError('longitud', 'min') || hasError('longitud', 'max')) {
                        <span class="field-error">La longitud debe estar entre -180 y 180.</span>
                      }
                    </label>

                    <label class="app-field">
                      <span class="app-field__label">Radio de acción (km)</span>
                      <input
                        type="number"
                        step="0.01"
                        class="app-input"
                        formControlName="radio_accion_km"
                        placeholder="20"
                      />
                      @if (hasError('radio_accion_km', 'required')) {
                        <span class="field-error">El radio de acción es obligatorio.</span>
                      } @else if (hasError('radio_accion_km', 'min')) {
                        <span class="field-error">El radio de acción debe ser mayor que 0.</span>
                      }
                    </label>

                    <label class="toggle-field">
                      <input type="checkbox" formControlName="acepta_seguro_propio" />
                      <div>
                        <span class="toggle-field__title">Acepta seguro propio</span>
                        <span class="toggle-field__hint">
                          Habilita priorización para clientes con cobertura vinculada al taller.
                        </span>
                      </div>
                    </label>
                  </div>

                  @if (saveSuccess()) {
                    <p class="feedback feedback--success">{{ saveSuccess() }}</p>
                  }
                  @if (saveError()) {
                    <p class="feedback feedback--error">{{ saveError() }}</p>
                  }

                  <div class="form-actions">
                    <button
                      type="submit"
                      class="app-button"
                      [disabled]="profileForm.invalid || saving() || !canSaveProfile()"
                    >
                      {{ saving() ? 'Guardando...' : 'Guardar cambios' }}
                    </button>
                    <button
                      type="button"
                      class="app-button app-button--secondary"
                      (click)="cancelEditing()"
                      [disabled]="saving()"
                    >
                      Cancelar
                    </button>
                    @if (!canSaveProfile()) {
                      <span class="text-muted">
                        Se requiere al menos una especialidad activa para actualizar el perfil.
                      </span>
                    }
                  </div>
                </form>
              </section>
            }
          </app-card>

          <app-card
            class="profile-layout__side"
            title="Estado operativo"
            subtitle="Resumen actual utilizado por el motor de recomendación y cobertura."
          >
            <div class="summary-grid">
              <div class="summary-item">
                <span class="text-muted">ID del taller</span>
                <strong>#{{ data.workshop_id }}</strong>
              </div>
              <div class="summary-item">
                <span class="text-muted">Estado</span>
                <app-status-badge [label]="data.activo ? 'CONFIRMADO' : 'BAJA'" />
              </div>
              <div class="summary-item">
                <span class="text-muted">Seguro propio</span>
                <strong>{{ data.acepta_seguro_propio ? 'Activo' : 'Desactivado' }}</strong>
              </div>
              <div class="summary-item">
                <span class="text-muted">Radio configurado</span>
                <strong>{{ formatNumber(data.radio_accion_km) }} km</strong>
              </div>
              <div class="summary-item">
                <span class="text-muted">Ubicación</span>
                <strong>{{ formatNumber(data.latitud) }}, {{ formatNumber(data.longitud) }}</strong>
              </div>
              <div class="summary-item">
                <span class="text-muted">Especialidades</span>
                <strong>{{ data.specialties.length }}</strong>
              </div>
            </div>
          </app-card>
        </section>

        <app-card
          title="Especialidades técnicas"
          subtitle="Especialidades activas que el backend usa para matching, catálogo y cobertura."
        >
          @if (data.specialties.length) {
            <div class="specialties">
              @for (specialty of data.specialties; track specialty.id_especialidad) {
                <span class="badge badge--info">{{ specialty.nombre }}</span>
              }
            </div>
            <p class="specialty-note text-muted">
              Las especialidades se gestionan desde configuración técnica del taller.
            </p>
          } @else {
            <app-empty-state
              title="Sin especialidades activas"
              message="El perfil no puede actualizarse correctamente hasta que el taller tenga al menos una especialidad configurada."
            />
          }
        </app-card>

        <section class="section-grid media-grid">
          <app-card
            title="Imágenes del taller"
            subtitle="Referencias visuales operativas y comerciales visibles en la configuración."
          >
            <div class="card-toolbar">
              <div class="text-muted">
                {{ images().length ? images().length + ' archivo(s) activo(s)' : 'Sin imágenes activas' }}
              </div>
              @if (!isUploadingImage()) {
                <button
                  type="button"
                  class="app-button app-button--secondary"
                  (click)="openUploadPanel('image')"
                  [disabled]="mediaUploading()"
                >
                  Subir imagen
                </button>
              }
            </div>

            @if (isUploadingImage()) {
              <section class="inline-panel">
                <div class="inline-panel__header">
                  <div>
                    <h4>Subir imagen</h4>
                    <p class="text-muted">Carga imágenes reales del taller sin salir de la vista operativa.</p>
                  </div>
                </div>

                <div class="media-upload">
                  <label class="app-field app-field--full">
                    <span class="app-field__label">Descripción opcional</span>
                    <input
                      type="text"
                      class="app-input"
                      [value]="imageDescription()"
                      (input)="imageDescription.set(asInputValue($event))"
                      placeholder="Frente del taller, bahías, equipos, etc."
                    />
                  </label>

                  <div class="custom-file">
                    <input
                      #imageInput
                      type="file"
                      class="sr-only"
                      accept="image/*"
                      (change)="onFileSelected($event, 'image')"
                    />
                    <div class="custom-file__row">
                      <button
                        type="button"
                        class="app-button app-button--ghost"
                        (click)="imageInput.click()"
                      >
                        Seleccionar archivo
                      </button>
                      <span class="custom-file__name">
                        {{ imageFileName() || 'Ningún archivo seleccionado' }}
                      </span>
                    </div>
                  </div>

                  @if (imageUploadError()) {
                    <p class="feedback feedback--error">{{ imageUploadError() }}</p>
                  }

                  <div class="form-actions">
                    <button
                      type="button"
                      class="app-button"
                      [disabled]="!imageFile() || mediaUploading()"
                      (click)="uploadMedia('IMAGEN_TALLER')"
                    >
                      {{ mediaUploading() ? 'Subiendo...' : 'Subir imagen' }}
                    </button>
                    <button
                      type="button"
                      class="app-button app-button--secondary"
                      [disabled]="mediaUploading()"
                      (click)="cancelUpload('image')"
                    >
                      Cancelar
                    </button>
                  </div>
                </div>
              </section>
            }

            @if (images().length) {
              <div class="media-list">
                @for (file of images(); track file.id_taller_archivo) {
                  <article class="media-item">
                    <div class="media-item__content">
                      <div class="media-item__header">
                        <strong>{{ file.nombre_archivo }}</strong>
                        <span class="badge badge--info">Imagen</span>
                      </div>
                      @if (file.descripcion) {
                        <p>{{ file.descripcion }}</p>
                      }
                      <div class="media-item__meta text-muted">
                        <span>{{ file.mime_type || 'Sin MIME' }}</span>
                        <span>{{ formatFileSize(file.tamano_bytes) }}</span>
                        <span>{{ formatDate(file.fecha_registro) }}</span>
                      </div>
                      @if (file.url_archivo) {
                        <a
                          class="media-item__link"
                          [href]="file.url_archivo"
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          Ver archivo
                        </a>
                      }
                    </div>
                    <button
                      type="button"
                      class="app-button app-button--ghost"
                      [disabled]="mediaUploading()"
                      (click)="deactivateMedia(file)"
                    >
                      Desactivar
                    </button>
                  </article>
                }
              </div>
            } @else {
              <app-empty-state
                title="Sin imágenes activas"
                message="Todavía no hay imágenes del taller cargadas."
              />
            }
          </app-card>

          <app-card
            title="Certificados técnicos"
            subtitle="Archivos que respaldan certificaciones, licencias o capacidades técnicas."
          >
            <div class="card-toolbar">
              <div class="text-muted">
                {{
                  certificates().length
                    ? certificates().length + ' archivo(s) activo(s)'
                    : 'Sin certificados activos'
                }}
              </div>
              @if (!isUploadingCertificate()) {
                <button
                  type="button"
                  class="app-button app-button--secondary"
                  (click)="openUploadPanel('certificate')"
                  [disabled]="mediaUploading()"
                >
                  Subir certificado
                </button>
              }
            </div>

            @if (isUploadingCertificate()) {
              <section class="inline-panel">
                <div class="inline-panel__header">
                  <div>
                    <h4>Subir certificado</h4>
                    <p class="text-muted">
                      Adjunta PDFs o imágenes que respalden capacidades técnicas del taller.
                    </p>
                  </div>
                </div>

                <div class="media-upload">
                  <label class="app-field app-field--full">
                    <span class="app-field__label">Descripción opcional</span>
                    <input
                      type="text"
                      class="app-input"
                      [value]="certificateDescription()"
                      (input)="certificateDescription.set(asInputValue($event))"
                      placeholder="Certificación, licencia o evidencia técnica"
                    />
                  </label>

                  <div class="custom-file">
                    <input
                      #certificateInput
                      type="file"
                      class="sr-only"
                      accept="application/pdf,image/*"
                      (change)="onFileSelected($event, 'certificate')"
                    />
                    <div class="custom-file__row">
                      <button
                        type="button"
                        class="app-button app-button--ghost"
                        (click)="certificateInput.click()"
                      >
                        Seleccionar archivo
                      </button>
                      <span class="custom-file__name">
                        {{ certificateFileName() || 'Ningún archivo seleccionado' }}
                      </span>
                    </div>
                  </div>

                  @if (certificateUploadError()) {
                    <p class="feedback feedback--error">{{ certificateUploadError() }}</p>
                  }

                  <div class="form-actions">
                    <button
                      type="button"
                      class="app-button"
                      [disabled]="!certificateFile() || mediaUploading()"
                      (click)="uploadMedia('CERTIFICADO_TECNICO')"
                    >
                      {{ mediaUploading() ? 'Subiendo...' : 'Subir certificado' }}
                    </button>
                    <button
                      type="button"
                      class="app-button app-button--secondary"
                      [disabled]="mediaUploading()"
                      (click)="cancelUpload('certificate')"
                    >
                      Cancelar
                    </button>
                  </div>
                </div>
              </section>
            }

            @if (certificates().length) {
              <div class="media-list">
                @for (file of certificates(); track file.id_taller_archivo) {
                  <article class="media-item">
                    <div class="media-item__content">
                      <div class="media-item__header">
                        <strong>{{ file.nombre_archivo }}</strong>
                        <span class="badge badge--warning">Certificado</span>
                      </div>
                      @if (file.descripcion) {
                        <p>{{ file.descripcion }}</p>
                      }
                      <div class="media-item__meta text-muted">
                        <span>{{ file.mime_type || 'Sin MIME' }}</span>
                        <span>{{ formatFileSize(file.tamano_bytes) }}</span>
                        <span>{{ formatDate(file.fecha_registro) }}</span>
                      </div>
                      @if (file.url_archivo) {
                        <a
                          class="media-item__link"
                          [href]="file.url_archivo"
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          Ver archivo
                        </a>
                      }
                    </div>
                    <button
                      type="button"
                      class="app-button app-button--ghost"
                      [disabled]="mediaUploading()"
                      (click)="deactivateMedia(file)"
                    >
                      Desactivar
                    </button>
                  </article>
                }
              </div>
            } @else {
              <app-empty-state
                title="Sin certificados activos"
                message="Todavía no hay certificados técnicos cargados."
              />
            }
          </app-card>
        </section>
      } @else {
        <app-empty-state
          title="Sin perfil disponible"
          message="No se recibió información utilizable del endpoint /workshop/profile."
        />
      }
    </div>
  `,
  styles: [
    `
      .profile-layout {
        display: grid;
        grid-template-columns: minmax(0, 1.7fr) minmax(280px, 0.9fr);
        gap: var(--space-5);
      }

      .profile-layout__main,
      .profile-layout__side {
        min-width: 0;
      }

      .summary-block {
        display: flex;
        flex-direction: column;
        gap: var(--space-5);
      }

      .summary-block__row {
        display: flex;
        flex-direction: column;
        gap: var(--space-2);
      }

      .summary-block__label {
        color: var(--color-text-muted);
        font-size: 0.86rem;
      }

      .summary-block__text {
        margin: 0;
        line-height: 1.65;
      }

      .inline-panel {
        margin-top: var(--space-6);
        padding-top: var(--space-5);
        border-top: 1px solid color-mix(in srgb, var(--color-border) 72%, transparent);
      }

      .inline-panel__header h4 {
        margin: 0;
        font-size: 1rem;
      }

      .inline-panel__header p {
        margin: var(--space-2) 0 0;
      }

      .profile-form,
      .media-upload {
        display: flex;
        flex-direction: column;
        gap: var(--space-5);
        margin-top: var(--space-5);
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

      .feedback--success {
        color: var(--color-success);
      }

      .form-actions {
        display: flex;
        align-items: center;
        gap: var(--space-4);
        flex-wrap: wrap;
      }

      .summary-grid {
        display: grid;
        gap: var(--space-4);
      }

      .summary-item {
        padding-bottom: var(--space-4);
        border-bottom: 1px solid color-mix(in srgb, var(--color-border) 72%, transparent);
      }

      .summary-item:last-child {
        padding-bottom: 0;
        border-bottom: 0;
      }

      .summary-item strong,
      .specialty-note,
      .media-item p {
        display: block;
        margin-top: var(--space-2);
      }

      .specialties {
        display: flex;
        flex-wrap: wrap;
        gap: var(--space-3);
      }

      .specialty-note {
        margin-bottom: 0;
      }

      .media-grid {
        align-items: start;
      }

      .card-toolbar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: var(--space-4);
        flex-wrap: wrap;
        margin-bottom: var(--space-5);
      }

      .custom-file {
        padding: var(--space-4);
        border: 1px dashed var(--color-border-strong);
        border-radius: var(--radius-lg);
        background: color-mix(in srgb, var(--color-surface-soft) 92%, transparent);
      }

      .custom-file__row {
        display: flex;
        align-items: center;
        gap: var(--space-4);
        flex-wrap: wrap;
      }

      .custom-file__name {
        color: var(--color-text-muted);
        font-size: 0.92rem;
      }

      .media-list {
        display: flex;
        flex-direction: column;
        gap: var(--space-4);
      }

      .media-item {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: var(--space-4);
        padding: var(--space-4);
        border-radius: var(--radius-lg);
        border: 1px solid var(--color-border);
        background: color-mix(in srgb, var(--color-surface-soft) 92%, transparent);
      }

      .media-item__content {
        min-width: 0;
        flex: 1;
      }

      .media-item__header {
        display: flex;
        align-items: center;
        gap: var(--space-3);
        flex-wrap: wrap;
      }

      .media-item__meta {
        display: flex;
        flex-wrap: wrap;
        gap: var(--space-3);
        margin-top: var(--space-2);
        font-size: 0.84rem;
      }

      .media-item__link {
        display: inline-block;
        margin-top: var(--space-3);
        color: var(--color-primary);
        text-decoration: none;
      }

      .media-item__link:hover {
        text-decoration: underline;
      }

      @media (max-width: 980px) {
        .profile-layout {
          grid-template-columns: 1fr;
        }
      }

      @media (max-width: 720px) {
        .media-item {
          flex-direction: column;
        }

        .custom-file__row {
          align-items: flex-start;
          flex-direction: column;
        }
      }
    `,
  ],
})
export class WorkshopProfilePage {
  private readonly api = inject(WorkshopProfileApi);
  private readonly destroyRef = inject(DestroyRef);
  private readonly formBuilder = inject(FormBuilder);

  protected readonly loading = signal(false);
  protected readonly saving = signal(false);
  protected readonly mediaUploading = signal(false);
  protected readonly isEditingProfile = signal(false);
  protected readonly isUploadingImage = signal(false);
  protected readonly isUploadingCertificate = signal(false);
  protected readonly pageError = signal('');
  protected readonly saveError = signal('');
  protected readonly saveSuccess = signal('');
  protected readonly imageUploadError = signal('');
  protected readonly certificateUploadError = signal('');
  protected readonly profile = signal<WorkshopProfileResponse | null>(null);
  protected readonly mediaFiles = signal<WorkshopMediaFileResponse[]>([]);
  protected readonly imageFile = signal<File | null>(null);
  protected readonly certificateFile = signal<File | null>(null);
  protected readonly imageFileName = signal('');
  protected readonly certificateFileName = signal('');
  protected readonly imageDescription = signal('');
  protected readonly certificateDescription = signal('');

  protected readonly images = computed(() =>
    this.mediaFiles().filter((file) => file.tipo_archivo === 'IMAGEN_TALLER'),
  );

  protected readonly certificates = computed(() =>
    this.mediaFiles().filter((file) => file.tipo_archivo === 'CERTIFICADO_TECNICO'),
  );

  protected readonly profileForm = this.formBuilder.group({
    nombre_comercial: ['', [Validators.required]],
    descripcion: [''],
    latitud: [null as number | null, [Validators.required, Validators.min(-90), Validators.max(90)]],
    longitud: [
      null as number | null,
      [Validators.required, Validators.min(-180), Validators.max(180)],
    ],
    radio_accion_km: [null as number | null, [Validators.required, Validators.min(0.000001)]],
    acepta_seguro_propio: [false],
  });

  protected readonly canSaveProfile = computed(
    () => (this.profile()?.specialties.length ?? 0) > 0,
  );

  constructor() {
    this.reload();
  }

  protected reload(): void {
    this.loading.set(true);
    this.pageError.set('');
    this.saveError.set('');
    this.saveSuccess.set('');

    this.api
      .getProfile()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => {
          this.profile.set(response);
          this.patchForm(response);
          this.setInitialMedia(response);
          this.loading.set(false);
          this.refreshMedia();
        },
        error: (error) => {
          this.pageError.set(
            this.extractErrorMessage(error, 'No se pudo cargar el perfil del taller.'),
          );
          this.loading.set(false);
        },
      });
  }

  protected startEditing(): void {
    const currentProfile = this.profile();
    if (!currentProfile) {
      return;
    }
    this.patchForm(currentProfile);
    this.saveError.set('');
    this.saveSuccess.set('');
    this.isEditingProfile.set(true);
  }

  protected cancelEditing(): void {
    const currentProfile = this.profile();
    if (currentProfile) {
      this.patchForm(currentProfile);
    }
    this.saveError.set('');
    this.saveSuccess.set('');
    this.isEditingProfile.set(false);
  }

  protected openUploadPanel(type: 'image' | 'certificate'): void {
    if (type === 'image') {
      this.isUploadingImage.set(true);
      this.imageUploadError.set('');
    } else {
      this.isUploadingCertificate.set(true);
      this.certificateUploadError.set('');
    }
  }

  protected cancelUpload(type: 'image' | 'certificate'): void {
    if (type === 'image') {
      this.imageFile.set(null);
      this.imageFileName.set('');
      this.imageDescription.set('');
      this.imageUploadError.set('');
      this.isUploadingImage.set(false);
      return;
    }

    this.certificateFile.set(null);
    this.certificateFileName.set('');
    this.certificateDescription.set('');
    this.certificateUploadError.set('');
    this.isUploadingCertificate.set(false);
  }

  protected saveProfile(): void {
    if (this.profileForm.invalid || this.saving() || !this.canSaveProfile()) {
      this.profileForm.markAllAsTouched();
      return;
    }

    const currentProfile = this.profile();
    if (!currentProfile) {
      return;
    }

    const payload: WorkshopProfileUpdateRequest = {
      nombre_comercial: String(this.profileForm.getRawValue().nombre_comercial ?? '').trim(),
      descripcion: this.normalizeOptionalText(this.profileForm.getRawValue().descripcion),
      latitud: Number(this.profileForm.getRawValue().latitud),
      longitud: Number(this.profileForm.getRawValue().longitud),
      radio_accion_km: Number(this.profileForm.getRawValue().radio_accion_km),
      specialty_ids: currentProfile.specialties.map((item) => item.id_especialidad),
      acepta_seguro_propio: Boolean(this.profileForm.getRawValue().acepta_seguro_propio),
    };

    this.saving.set(true);
    this.saveError.set('');
    this.saveSuccess.set('');

    this.api
      .updateProfile(payload)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => {
          this.profile.set(response);
          this.patchForm(response);
          this.setInitialMedia(response);
          this.saveSuccess.set('Perfil del taller actualizado correctamente.');
          this.saving.set(false);
          this.isEditingProfile.set(false);
          this.refreshMedia();
        },
        error: (error) => {
          this.saveError.set(
            this.extractErrorMessage(error, 'No se pudo guardar la configuración del taller.'),
          );
          this.saving.set(false);
        },
      });
  }

  protected onFileSelected(event: Event, type: 'image' | 'certificate'): void {
    const input = event.target as HTMLInputElement | null;
    const file = input?.files?.[0] ?? null;

    if (type === 'image') {
      this.imageFile.set(file);
      this.imageFileName.set(file?.name ?? '');
      this.imageUploadError.set('');
    } else {
      this.certificateFile.set(file);
      this.certificateFileName.set(file?.name ?? '');
      this.certificateUploadError.set('');
    }
  }

  protected uploadMedia(tipo: 'IMAGEN_TALLER' | 'CERTIFICADO_TECNICO'): void {
    const isImage = tipo === 'IMAGEN_TALLER';
    const file = isImage ? this.imageFile() : this.certificateFile();
    const description = isImage ? this.imageDescription() : this.certificateDescription();

    if (!file || this.mediaUploading()) {
      return;
    }

    this.mediaUploading.set(true);
    if (isImage) {
      this.imageUploadError.set('');
    } else {
      this.certificateUploadError.set('');
    }

    this.api
      .uploadMedia(tipo, file, description)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.mediaUploading.set(false);
          this.cancelUpload(isImage ? 'image' : 'certificate');
          this.refreshMedia();
        },
        error: (error) => {
          const message = this.extractErrorMessage(
            error,
            'No se pudo subir el archivo al perfil del taller.',
          );
          if (isImage) {
            this.imageUploadError.set(message);
          } else {
            this.certificateUploadError.set(message);
          }
          this.mediaUploading.set(false);
        },
      });
  }

  protected deactivateMedia(file: WorkshopMediaFileResponse): void {
    if (this.mediaUploading()) {
      return;
    }

    const confirmed = window.confirm(`¿Desactivar el archivo "${file.nombre_archivo}"?`);
    if (!confirmed) {
      return;
    }

    this.mediaUploading.set(true);
    this.imageUploadError.set('');
    this.certificateUploadError.set('');

    this.api
      .deactivateMedia(file.id_taller_archivo)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.mediaUploading.set(false);
          this.refreshMedia();
        },
        error: (error) => {
          const message = this.extractErrorMessage(
            error,
            'No se pudo desactivar el archivo seleccionado.',
          );
          if (file.tipo_archivo === 'IMAGEN_TALLER') {
            this.imageUploadError.set(message);
          } else {
            this.certificateUploadError.set(message);
          }
          this.mediaUploading.set(false);
        },
      });
  }

  protected hasError(
    controlName: 'nombre_comercial' | 'latitud' | 'longitud' | 'radio_accion_km',
    errorKey: string,
  ): boolean {
    const control = this.profileForm.get(controlName);
    return Boolean(control?.touched && control.hasError(errorKey));
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

  protected formatFileSize(size: number | null): string {
    if (!size || size <= 0) {
      return 'Tamaño no informado';
    }
    if (size < 1024) {
      return `${size} B`;
    }
    if (size < 1024 * 1024) {
      return `${(size / 1024).toFixed(1)} KB`;
    }
    return `${(size / (1024 * 1024)).toFixed(1)} MB`;
  }

  protected formatNumber(value: string | number): string {
    const numericValue = Number(value);
    if (!Number.isFinite(numericValue)) {
      return String(value);
    }

    return new Intl.NumberFormat('es-BO', {
      minimumFractionDigits: 0,
      maximumFractionDigits: 4,
    }).format(numericValue);
  }

  protected asInputValue(event: Event): string {
    return (event.target as HTMLInputElement | null)?.value ?? '';
  }

  private refreshMedia(): void {
    this.api
      .listMedia()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => {
          this.mediaFiles.set(response);
          this.mergeMediaIntoProfile(response);
        },
        error: () => {
          // Keep profile media fallback if listing fails.
        },
      });
  }

  private setInitialMedia(profile: WorkshopProfileResponse): void {
    this.mediaFiles.set([
      ...(profile.imagenes_taller ?? []),
      ...(profile.certificados_tecnicos ?? []),
    ]);
  }

  private mergeMediaIntoProfile(files: WorkshopMediaFileResponse[]): void {
    const currentProfile = this.profile();
    if (!currentProfile) {
      return;
    }

    this.profile.set({
      ...currentProfile,
      imagenes_taller: files.filter((file) => file.tipo_archivo === 'IMAGEN_TALLER'),
      certificados_tecnicos: files.filter(
        (file) => file.tipo_archivo === 'CERTIFICADO_TECNICO',
      ),
    });
  }

  private patchForm(profile: WorkshopProfileResponse): void {
    this.profileForm.reset(
      {
        nombre_comercial: profile.nombre_comercial ?? '',
        descripcion: profile.descripcion ?? '',
        latitud: this.toNumber(profile.latitud),
        longitud: this.toNumber(profile.longitud),
        radio_accion_km: this.toNumber(profile.radio_accion_km),
        acepta_seguro_propio: profile.acepta_seguro_propio ?? false,
      },
      { emitEvent: false },
    );
  }

  private normalizeOptionalText(value: string | null | undefined): string | null {
    const normalized = String(value ?? '').trim();
    return normalized ? normalized : null;
  }

  private toNumber(value: string | number | null | undefined): number | null {
    if (value === null || value === undefined || value === '') {
      return null;
    }
    const numericValue = Number(value);
    return Number.isFinite(numericValue) ? numericValue : null;
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
        return 'No tienes permisos para gestionar el perfil de este taller.';
      }

      if (error.status === 404) {
        return 'El perfil del taller no fue encontrado.';
      }
    }

    return fallback;
  }
}
