import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  afterNextRender,
  computed,
  inject,
  signal,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import * as L from 'leaflet';

import { AppCardComponent } from '../../../shared/components/app-card.component';
import { EmptyStateComponent } from '../../../shared/components/empty-state.component';
import { ErrorStateComponent } from '../../../shared/components/error-state.component';
import { LoadingStateComponent } from '../../../shared/components/loading-state.component';
import { PageHeaderComponent } from '../../../shared/components/page-header.component';
import { StatusBadgeComponent } from '../../../shared/components/status-badge.component';
import { localizeBackendMessage } from '../../../shared/utils/user-facing-text';
import { WorkshopProfileApi } from '../data-access/workshop-profile.api';
import {
  WorkshopMediaFileResponse,
  WorkshopProfileResponse,
  WorkshopProfileUpdateRequest,
} from '../data-access/workshop-profile.models';

interface LocationSearchResult {
  lat: string;
  lon: string;
  display_name: string;
  address?: Record<string, string>;
}

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
                  <span class="text-muted">Dirección</span>
                  <strong>{{ formattedAddress(data) }}</strong>
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
                      Actualiza la información operativa del taller.
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

                    <div class="legacy-location-fields">
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

                    <label class="app-field app-field--full">
                      <span class="app-field__label">Dirección</span>
                      <input
                        type="text"
                        class="app-input"
                        formControlName="direccion"
                        placeholder="Calle/Avenida, número"
                      />
                    </label>

                    <label class="app-field">
                      <span class="app-field__label">Ciudad</span>
                      <input
                        type="text"
                        class="app-input"
                        formControlName="ciudad"
                        placeholder="Santa Cruz"
                      />
                    </label>

                    <label class="app-field">
                      <span class="app-field__label">Zona</span>
                      <input
                        type="text"
                        class="app-input"
                        formControlName="zona"
                        placeholder="Equipetrol, Centro, etc."
                      />
                    </label>

                    <label class="app-field app-field--full">
                      <span class="app-field__label">Referencia</span>
                      <textarea
                        class="app-textarea"
                        formControlName="referencia"
                        rows="2"
                        placeholder="Cerca del mercado, a dos cuadras de..."
                      ></textarea>
                    </label>

                    </div>

                    <div class="map-picker">
                      <div class="location-heading">
                        <span class="location-heading__eyebrow">Ubicacion del taller</span>
                        <h4>Busca el lugar y selecciona el resultado correcto</h4>
                        <p>La direccion, ciudad, zona y coordenadas se completaran automaticamente.</p>
                      </div>
                      <div class="map-picker__search">
                        <input
                          type="text"
                          class="app-input"
                          [value]="searchQuery()"
                          (input)="searchQuery.set(asInputValue($event))"
                          (keydown.enter)="searchLocation(); $event.preventDefault()"
                          placeholder="Buscar dirección en el mapa..."
                        />
                        <button
                          type="button"
                          class="app-button"
                          (click)="searchLocation()"
                          [disabled]="searchingLocation()"
                        >
                          {{ searchingLocation() ? 'Buscando...' : 'Buscar ubicacion' }}
                        </button>
                      </div>

                      @if (locationSearchError()) {
                        <p class="feedback feedback--error">{{ locationSearchError() }}</p>
                      }

                      @if (showSearchResults() && searchResults().length) {
                        <ul class="map-picker__results">
                          @for (result of searchResults(); track result.lat + result.lon) {
                            <li>
                              <button
                                type="button"
                                class="map-picker__result"
                                (click)="selectSearchResult(result)"
                              >
                                {{ result.display_name }}
                              </button>
                            </li>
                          }
                        </ul>
                      }

                      <div id="workshop-map" class="map-picker__map"></div>
                      <div class="selected-location">
                        <div>
                          <span class="selected-location__label">Ubicacion seleccionada</span>
                          <strong>{{ selectedAddress() }}</strong>
                          <small>{{ selectedLocationDetails() }}</small>
                        </div>
                        <button
                          type="button"
                          class="app-button app-button--secondary"
                          (click)="openInGoogleMaps()"
                          [disabled]="!hasSelectedCoordinates()"
                        >
                          Ver en Google Maps
                        </button>
                      </div>
                      <p class="text-muted map-picker__hint">
                        Haz clic en el mapa o busca una dirección para ubicar el taller.
                        Arrastra el marcador para ajustar la posición.
                      </p>
                    </div>

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
                <span class="text-muted">Coordenadas</span>
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
          subtitle="Especialidades activas del taller."
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

      .map-picker {
        grid-column: 1 / -1;
        display: flex;
        flex-direction: column;
        gap: var(--space-3);
      }

      .legacy-location-fields {
        display: contents;
      }

      .legacy-location-fields > .app-field:not(:last-child) {
        display: none;
      }

      .location-heading {
        padding: var(--space-4);
        border: 1px solid color-mix(in srgb, var(--color-primary) 38%, var(--color-border));
        border-radius: var(--radius-lg);
        background: linear-gradient(
          135deg,
          color-mix(in srgb, var(--color-primary) 13%, var(--color-surface)),
          var(--color-surface-soft)
        );
      }

      .location-heading__eyebrow {
        color: var(--color-primary);
        font-size: 0.76rem;
        font-weight: 800;
        letter-spacing: 0.12em;
        text-transform: uppercase;
      }

      .location-heading h4 {
        margin: var(--space-2) 0;
        font-size: 1.15rem;
      }

      .location-heading p {
        margin: 0;
        color: var(--color-text-muted);
      }

      .map-picker__search {
        display: flex;
        gap: var(--space-3);
      }

      .map-picker__search .app-input {
        flex: 1;
      }

      .map-picker__results {
        list-style: none;
        margin: 0;
        padding: 0;
        border: 1px solid var(--color-border);
        border-radius: var(--radius-lg);
        max-height: 200px;
        overflow-y: auto;
        background: var(--color-surface);
      }

      .map-picker__result {
        display: block;
        width: 100%;
        padding: var(--space-3);
        cursor: pointer;
        border-bottom: 1px solid var(--color-border);
        border-top: 0;
        border-left: 0;
        border-right: 0;
        background: transparent;
        color: var(--color-text);
        text-align: left;
        font-size: 0.9rem;
        line-height: 1.4;
      }

      .map-picker__result:last-child {
        border-bottom: none;
      }

      .map-picker__result:hover {
        background: var(--color-surface-soft);
      }

      .map-picker__map {
        height: 350px;
        border-radius: var(--radius-lg);
        border: 1px solid var(--color-border);
        z-index: 0;
      }

      .map-picker__hint {
        font-size: 0.85rem;
      }

      .selected-location {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: var(--space-4);
        padding: var(--space-4);
        border-radius: var(--radius-lg);
        border: 1px solid var(--color-border);
        background: var(--color-surface-soft);
      }

      .selected-location__label,
      .selected-location small {
        display: block;
        color: var(--color-text-muted);
      }

      .selected-location strong {
        display: block;
        margin: var(--space-1) 0;
      }

      @media (max-width: 980px) {
        .profile-layout {
          grid-template-columns: 1fr;
        }
      }

      @media (max-width: 720px) {
        .map-picker__search,
        .selected-location {
          align-items: stretch;
          flex-direction: column;
        }

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
    direccion: [''],
    ciudad: [''],
    zona: [''],
    referencia: [''],
    radio_accion_km: [null as number | null, [Validators.required, Validators.min(0.000001)]],
    acepta_seguro_propio: [false],
  });

  private map: L.Map | null = null;
  private mapMarker: L.Marker | null = null;
  protected searchQuery = signal('');
  protected searchResults = signal<LocationSearchResult[]>([]);
  protected showSearchResults = signal(false);
  protected searchingLocation = signal(false);
  protected locationSearchError = signal('');

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
    afterNextRender(() => {
      this.initMap();
    });
  }

  protected cancelEditing(): void {
    this.destroyMap();
    const currentProfile = this.profile();
    if (currentProfile) {
      this.patchForm(currentProfile);
    }
    this.saveError.set('');
    this.saveSuccess.set('');
    this.locationSearchError.set('');
    this.searchResults.set([]);
    this.showSearchResults.set(false);
    this.isEditingProfile.set(false);
  }

  protected formattedAddress(data: WorkshopProfileResponse): string {
    const parts = [data.direccion, data.zona, data.ciudad].filter(Boolean);
    return parts.length ? parts.join(', ') : 'Sin dirección registrada.';
  }

  private initMap(): void {
    this.destroyMap();
    const el = document.getElementById('workshop-map');
    if (!el) return;

    this.map = L.map(el, {
      center: [-17.7833, -63.1821],
      zoom: 13,
      zoomControl: true,
    });

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      maxZoom: 19,
    }).addTo(this.map);

    this.map.on('click', (e: L.LeafletMouseEvent) => {
      this.handleMapClick(e.latlng);
    });

    const lat = this.profileForm.get('latitud')?.value;
    const lng = this.profileForm.get('longitud')?.value;
    if (lat != null && lng != null) {
      const latlng = L.latLng(lat, lng);
      this.placeMarker(latlng);
      this.map.setView(latlng, 15);
    }
    window.setTimeout(() => this.map?.invalidateSize(), 0);
  }

  private destroyMap(): void {
    if (this.mapMarker) {
      this.mapMarker.remove();
      this.mapMarker = null;
    }
    if (this.map) {
      this.map.remove();
      this.map = null;
    }
  }

  protected async searchLocation(): Promise<void> {
    const q = this.searchQuery().trim();
    if (!q || q.length < 3) {
      this.locationSearchError.set('Escribe al menos tres caracteres para buscar.');
      return;
    }

    this.searchingLocation.set(true);
    this.locationSearchError.set('');
    this.showSearchResults.set(false);
    try {
      const res = await fetch(
        `https://nominatim.openstreetmap.org/search?format=jsonv2&addressdetails=1&q=${encodeURIComponent(q)}&limit=5&countrycodes=bo`,
      );
      if (!res.ok) {
        throw new Error('Location search failed');
      }
      const data: unknown = await res.json();
      if (Array.isArray(data)) {
        this.searchResults.set(
          data.map((item: Record<string, unknown>) => ({
            lat: String(item['lat'] ?? ''),
            lon: String(item['lon'] ?? ''),
            display_name: String(item['display_name'] ?? ''),
            address:
              item['address'] && typeof item['address'] === 'object'
                ? (item['address'] as Record<string, string>)
                : undefined,
          })),
        );
      } else {
        this.searchResults.set([]);
      }
      this.showSearchResults.set(true);
      if (!this.searchResults().length) {
        this.locationSearchError.set(
          'No encontramos esa ubicacion. Prueba agregando ciudad, avenida o barrio.',
        );
      }
    } catch {
      this.searchResults.set([]);
      this.locationSearchError.set(
        'No se pudo consultar el buscador de ubicaciones. Intenta nuevamente.',
      );
    } finally {
      this.searchingLocation.set(false);
    }
  }

  protected selectSearchResult(result: LocationSearchResult): void {
    this.showSearchResults.set(false);
    this.locationSearchError.set('');
    this.searchQuery.set(result.display_name);
    const latlng = L.latLng(parseFloat(result.lat), parseFloat(result.lon));
    this.placeMarker(latlng);
    this.map?.setView(latlng, 16);
    this.profileForm.patchValue({
      latitud: parseFloat(result.lat),
      longitud: parseFloat(result.lon),
      ...this.locationFieldsFromAddress(result.address, result.display_name),
    });
  }

  private handleMapClick(latlng: L.LatLng): void {
    this.placeMarker(latlng);
    this.profileForm.patchValue({
      latitud: latlng.lat,
      longitud: latlng.lng,
    });
    this.reverseGeocode(latlng);
  }

  private placeMarker(latlng: L.LatLng): void {
    if (this.mapMarker) {
      this.mapMarker.setLatLng(latlng);
    } else if (this.map) {
      this.mapMarker = L.marker(latlng, {
        draggable: true,
        icon: L.divIcon({
          className: 'workshop-map-marker',
          html: '<span></span>',
          iconSize: [30, 38],
          iconAnchor: [15, 38],
        }),
      }).addTo(this.map);
      this.mapMarker.on('dragend', () => {
        const pos = this.mapMarker!.getLatLng();
        this.profileForm.patchValue({
          latitud: pos.lat,
          longitud: pos.lng,
        });
        this.reverseGeocode(pos);
      });
    }
  }

  private async reverseGeocode(latlng: L.LatLng): Promise<void> {
    try {
      const res = await fetch(
        `https://nominatim.openstreetmap.org/reverse?format=json&lat=${latlng.lat}&lon=${latlng.lng}&addressdetails=1`,
      );
      const data: Record<string, unknown> = await res.json();
      const address = (data['address'] as Record<string, unknown>) ?? {};
      const displayName = String(data['display_name'] ?? '');
      this.profileForm.patchValue(
        this.locationFieldsFromAddress(
          Object.fromEntries(Object.entries(address).map(([key, value]) => [key, String(value)])),
          displayName,
        ),
      );
      this.searchQuery.set(displayName);
    } catch {
      // reverse geocode failed silently
    }
  }

  protected hasSelectedCoordinates(): boolean {
    return Number.isFinite(Number(this.profileForm.get('latitud')?.value))
      && Number.isFinite(Number(this.profileForm.get('longitud')?.value));
  }

  protected selectedAddress(): string {
    const address = this.profileForm.get('direccion')?.value?.trim();
    return address || 'Selecciona una ubicacion en el buscador o mapa';
  }

  protected selectedLocationDetails(): string {
    const city = this.profileForm.get('ciudad')?.value?.trim();
    const zone = this.profileForm.get('zona')?.value?.trim();
    return [zone, city].filter(Boolean).join(', ') || 'Ciudad y zona pendientes de completar';
  }

  protected openInGoogleMaps(): void {
    const latitude = Number(this.profileForm.get('latitud')?.value);
    const longitude = Number(this.profileForm.get('longitud')?.value);
    if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) {
      return;
    }
    window.open(
      `https://www.google.com/maps/search/?api=1&query=${latitude},${longitude}`,
      '_blank',
      'noopener,noreferrer',
    );
  }

  private locationFieldsFromAddress(
    address: Record<string, string> | undefined,
    displayName: string,
  ): { direccion: string; ciudad: string; zona: string } {
    const details = address ?? {};
    const road = details['road'] ?? details['pedestrian'] ?? details['place'] ?? '';
    const houseNumber = details['house_number'] ?? '';
    return {
      direccion: [road, houseNumber].filter(Boolean).join(' ') || displayName.split(',')[0] || '',
      ciudad:
        details['city'] ??
        details['town'] ??
        details['village'] ??
        details['municipality'] ??
        details['county'] ??
        '',
      zona:
        details['suburb'] ??
        details['neighbourhood'] ??
        details['quarter'] ??
        details['city_district'] ??
        '',
    };
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

    const rawValue = this.profileForm.getRawValue();
    const latitud = Number(rawValue.latitud);
    const longitud = Number(rawValue.longitud);
    const radio_accion_km = Number(rawValue.radio_accion_km);
    const nombre_comercial = String(rawValue.nombre_comercial ?? '').trim();

    if (!Number.isFinite(latitud) || latitud < -90 || latitud > 90) {
      this.saveError.set('La latitud debe ser un número válido entre -90 y 90.');
      return;
    }

    if (!Number.isFinite(longitud) || longitud < -180 || longitud > 180) {
      this.saveError.set('La longitud debe ser un número válido entre -180 y 180.');
      return;
    }

    if (!Number.isFinite(radio_accion_km) || radio_accion_km <= 0) {
      this.saveError.set('El radio de acción debe ser un número válido mayor a 0.');
      return;
    }

    if (nombre_comercial.length === 0) {
      this.saveError.set('El nombre comercial no puede estar vacío.');
      return;
    }

    const specialty_ids = currentProfile.specialties.map((item) => item.id_especialidad);
    if (specialty_ids.length === 0) {
      this.saveError.set('El perfil debe tener al menos una especialidad activa.');
      return;
    }

    const payload: WorkshopProfileUpdateRequest = {
      nombre_comercial,
      descripcion: this.normalizeOptionalText(rawValue.descripcion),
      latitud,
      longitud,
      direccion: this.normalizeOptionalText(rawValue.direccion),
      ciudad: this.normalizeOptionalText(rawValue.ciudad),
      zona: this.normalizeOptionalText(rawValue.zona),
      referencia: this.normalizeOptionalText(rawValue.referencia),
      radio_accion_km,
      specialty_ids,
      acepta_seguro_propio: Boolean(rawValue.acepta_seguro_propio),
    };

    this.saving.set(true);
    this.saveError.set('');
    this.saveSuccess.set('');

    this.api
      .updateProfile(payload)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => {
          this.destroyMap();
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

    if (!Number.isInteger(file.id_taller_archivo) || file.id_taller_archivo <= 0) {
      const errorMsg = 'ID de archivo inválido.';
      if (file.tipo_archivo === 'IMAGEN_TALLER') {
        this.imageUploadError.set(errorMsg);
      } else {
        this.certificateUploadError.set(errorMsg);
      }
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
        direccion: profile.direccion ?? '',
        ciudad: profile.ciudad ?? '',
        zona: profile.zona ?? '',
        referencia: profile.referencia ?? '',
        radio_accion_km: this.toNumber(profile.radio_accion_km),
        acepta_seguro_propio: profile.acepta_seguro_propio ?? false,
      },
      { emitEvent: false },
    );
    this.searchQuery.set(
      [profile.direccion, profile.zona, profile.ciudad].filter(Boolean).join(', '),
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
        return localizeBackendMessage(detail);
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
          return localizeBackendMessage(messages.join(' '));
        }
      }

      if (typeof error.error === 'string' && error.error.trim()) {
        return localizeBackendMessage(error.error);
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
