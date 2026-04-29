# Despliegue en AWS EC2 con Docker Compose

## 1. Preparar la instancia Ubuntu

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo \"$VERSION_CODENAME\") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER
newgrp docker
```

## 2. Subir el proyecto

```bash
git clone <TU_REPOSITORIO> proyecto-si2
cd proyecto-si2
cp .env.prod.example .env.prod
```

Edita `.env.prod` y completa:

- `POSTGRES_PASSWORD`
- `DATABASE_URL`
- `JWT_SECRET_KEY`
- `CORS_ALLOW_ORIGINS`
- `MEDIA_PUBLIC_BASE_URL`
- `TRIAGE_AI_API_KEY` si usarás Groq en producción

## 3. Construir y levantar

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml build
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d
```

## 4. Comandos operativos

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml ps
docker compose --env-file .env.prod -f docker-compose.prod.yml logs -f
docker compose --env-file .env.prod -f docker-compose.prod.yml down
docker compose --env-file .env.prod -f docker-compose.prod.yml down -v
```

## 5. Migraciones

El servicio `backend` ejecuta `alembic upgrade head` al iniciar. Si necesitas correrlo manualmente:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml exec backend alembic upgrade head
```

## 6. Crear un usuario administrador

Opciones recomendadas:

1. Usar el flujo real de registro administrador ya existente:
   - `POST /auth/register/admin/start`
   - `POST /auth/register/admin/verify`
2. Si necesitas un alta manual operativa, crea el usuario desde un script propio de bootstrap o SQL controlado para tu entorno.

Nota:
- `Backend/scripts/seed_admin.py` está restringido a entornos locales y no debe usarse en producción.

## 7. Build de Angular

El contenedor `nginx` construye el panel Angular en un stage de Node y luego sirve el resultado estático.

Comando local equivalente:

```bash
cd Frontend
npm ci
npm run build
```

## 8. Backup de base de datos

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml exec -T postgres \
  pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > backup_$(date +%F_%H%M).sql
```

Restore:

```bash
cat backup_2026-04-29_1200.sql | docker compose --env-file .env.prod -f docker-compose.prod.yml exec -T postgres \
  psql -U "$POSTGRES_USER" "$POSTGRES_DB"
```

## 9. Persistencia

- PostgreSQL persiste en el volumen `postgres_data`
- Archivos subidos persisten en el volumen `backend_media`

## 10. Endpoints expuestos

- Frontend admin: `http://TU_IP_O_DOMINIO/`
- API backend por Nginx: `http://TU_IP_O_DOMINIO/api/...`
- Media: `http://TU_IP_O_DOMINIO/media/...`
