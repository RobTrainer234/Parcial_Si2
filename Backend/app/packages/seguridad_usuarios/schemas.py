from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


class _NormalizedModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class ActorContextResponse(BaseModel):
    cliente_persona_id: int | None = None
    administrador_persona_id: int | None = None
    operario_id: int | None = None
    taller_id: int | None = None


class UserProfileResponse(BaseModel):
    user_id: int
    persona_id: int
    role: str
    email: EmailStr
    phone: str | None = None
    actor_context: ActorContextResponse
    home_hint: str


class LoginRequest(_NormalizedModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    role: str
    user: UserProfileResponse
    actor_context: ActorContextResponse
    home_hint: str


class LogoutResponse(BaseModel):
    status: str
    message: str


class RegistrationVerifyRequest(_NormalizedModel):
    registration_token: str
    verification_code: str = Field(min_length=4, max_length=12)


class RegistrationStartResponse(BaseModel):
    status: str
    role: str
    registration_token: str
    expires_at: datetime
    debug_verification_code: str | None = None


class RegistrationVerifyResponse(BaseModel):
    status: str
    role: str
    home_hint: str
    created_vehicle_count: int | None = None


class VehicleRegistrationItem(_NormalizedModel):
    placa: str = Field(min_length=3, max_length=15)
    anio: int = Field(ge=1900, le=2100)
    marca_nombre: str = Field(min_length=1, max_length=50)
    modelo_nombre: str = Field(min_length=1, max_length=50)
    color_nombre: str = Field(min_length=1, max_length=30)

    @field_validator("placa")
    @classmethod
    def normalize_placa(cls, value: str) -> str:
        return value.upper()


class PersonalRegistrationData(_NormalizedModel):
    nombre: str = Field(min_length=1, max_length=100)
    apellido: str = Field(min_length=1, max_length=100)
    ci: str = Field(min_length=1, max_length=20)
    telefono: str = Field(min_length=1, max_length=20)
    direccion: str | None = Field(default=None, max_length=2000)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class ClientRegisterStartRequest(PersonalRegistrationData):
    vehicles: list[VehicleRegistrationItem] = Field(min_length=1)


class AdminWorkshopData(_NormalizedModel):
    nombre_comercial: str = Field(min_length=1, max_length=150)
    descripcion: str | None = Field(default=None, max_length=5000)
    latitud: Decimal
    longitud: Decimal
    radio_accion_km: Decimal = Field(default=Decimal("10.00"), gt=0)


class AdminRegisterStartRequest(PersonalRegistrationData):
    workshop: AdminWorkshopData


class PendingClientRegistrationPayload(_NormalizedModel):
    nombre: str
    apellido: str
    ci: str
    telefono: str
    direccion: str | None = None
    email: EmailStr
    password_hash: str
    vehicles: list[VehicleRegistrationItem]


class PendingAdminRegistrationPayload(_NormalizedModel):
    nombre: str
    apellido: str
    ci: str
    telefono: str
    direccion: str | None = None
    email: EmailStr
    password_hash: str
    workshop: AdminWorkshopData


class PersonaProfileResponse(BaseModel):
    nombre: str
    apellido: str
    ci: str
    telefono: str | None = None
    direccion: str | None = None


class VehicleResponse(BaseModel):
    id_vehiculo: int
    placa: str
    anio: int
    marca_nombre: str
    modelo_nombre: str
    color_nombre: str


class OperarioSpecialtyResponse(BaseModel):
    id_especialidad: int
    nombre: str
    anios_experiencia: int
    certificacion_url: str | None = None


class ProfileMeResponse(BaseModel):
    persona: PersonaProfileResponse
    user: UserProfileResponse
    vehicles: list[VehicleResponse] | None = None
    specialties: list[OperarioSpecialtyResponse] | None = None


class ProfileUpdateRequest(_NormalizedModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=100)
    apellido: str | None = Field(default=None, min_length=1, max_length=100)
    telefono: str | None = Field(default=None, min_length=1, max_length=20)
    direccion: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_any_field_present(self) -> "ProfileUpdateRequest":
        if all(
            value is None
            for value in (self.nombre, self.apellido, self.telefono, self.direccion)
        ):
            raise ValueError("At least one profile field must be provided.")
        return self


class VehicleCreateRequest(VehicleRegistrationItem):
    pass


class VehicleUpdateRequest(_NormalizedModel):
    placa: str | None = Field(default=None, min_length=3, max_length=15)
    anio: int | None = Field(default=None, ge=1900, le=2100)
    marca_nombre: str | None = Field(default=None, min_length=1, max_length=50)
    modelo_nombre: str | None = Field(default=None, min_length=1, max_length=50)
    color_nombre: str | None = Field(default=None, min_length=1, max_length=30)

    @field_validator("placa")
    @classmethod
    def normalize_optional_placa(cls, value: str | None) -> str | None:
        return value.upper() if value is not None else None

    @model_validator(mode="after")
    def validate_any_field_present(self) -> "VehicleUpdateRequest":
        if all(
            value is None
            for value in (
                self.placa,
                self.anio,
                self.marca_nombre,
                self.modelo_nombre,
                self.color_nombre,
            )
        ):
            raise ValueError("At least one vehicle field must be provided.")
        return self


class OperarioSpecialtyItem(_NormalizedModel):
    id_especialidad: int
    anios_experiencia: int = Field(ge=0)
    certificacion_url: str | None = Field(default=None, max_length=2000)


class OperarioSpecialtyReplaceRequest(_NormalizedModel):
    specialties: list[OperarioSpecialtyItem] = Field(default_factory=list)


class SimpleSuccessResponse(BaseModel):
    status: str
    message: str


class ForgotPasswordRequest(_NormalizedModel):
    email: EmailStr


class ResetPasswordRequest(_NormalizedModel):
    token: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)
