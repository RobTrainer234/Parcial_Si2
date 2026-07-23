# Despliegue en Google Cloud Compute Engine con Docker Compose

## Requisitos previos

- VM de Compute Engine con Ubuntu 22.04+ creada
- Docker Engine y Docker Compose v2+ instalados
- IP publica externa asignada a la VM
- Firewall de GCP con puertos 80 y 443 abiertos
- Dominio apuntando a la IP de la VM (opcional, se puede usar solo IP para HTTP)

## 1. Configurar firewall en GCP

```bash
gcloud compute firewall-rules create allow-http-https-si2 \
  --direction=INGRESS --priority=1000 \
  --network=default --action=ALLOW \
  --rules=tcp:80,tcp:443 \
  --source-ranges=0.0.0.0/0 \
  --target-tags=si2-app

gcloud compute instances add-tags si2-app \
  --tags=si2-app --zone=southamerica-west1-a
```

## 2. Clonar el proyecto

```bash
git clone https://github.com/RobTrainer234/Parcial_Si2.git proyecto-si2
cd proyecto-si2
```

## 3. Crear archivo .env.prod

```bash
# El script te guia paso a paso, genera claves y detecta tu IP
bash scripts/setup-env-gcp.sh
```

Te preguntara:
- Dominio (si tienes) o usa Enter para usar la IP publica
- Email para Let's Encrypt (necesario para HTTPS)
- API key de Groq (opcional)
- Credenciales SMTP (opcional)

El script genera automaticamente:
- `JWT_SECRET_KEY` (random 64 chars)
- `POSTGRES_PASSWORD` (random 32 chars)
- Detecta la IP publica de la VM

## 4. Desplegar

```bash
bash scripts/deploy-gcp.sh
```

Este script:
1. Detiene servicios anteriores si existen
2. Construye las imagenes (backend + nginx/Angular)
3. Levanta PostgreSQL, backend y nginx
4. Obtiene certificado SSL de Let's Encrypt
5. Recarga nginx con configuracion HTTPS

## 5. Verificar

```bash
# Estado de los contenedores
docker compose --env-file .env.prod -f docker-compose.prod.yml ps

# Logs en tiempo real
docker compose --env-file .env.prod -f docker-compose.prod.yml logs -f

# Health check
curl -k https://<DOMINIO>/api/health
```

## 6. Crear usuario administrador

El proyecto tiene un endpoint de registro de administrador. Consulta el frontend o la API.

## 7. Backup de base de datos

```bash
# Backup manual
bash scripts/backup-db-gcp.sh

# Backup automatico diario (agregar al cron)
echo "0 2 * * * cd $(pwd) && bash scripts/backup-db-gcp.sh >> backups/cron.log 2>&1" | crontab -
```

## 8. Comandos operativos

```bash
# Ver estado
docker compose --env-file .env.prod -f docker-compose.prod.yml ps

# Ver logs
docker compose --env-file .env.prod -f docker-compose.prod.yml logs -f

# Ver logs de un servicio
docker compose --env-file .env.prod -f docker-compose.prod.yml logs -f backend

# Reiniciar un servicio
docker compose --env-file .env.prod -f docker-compose.prod.yml restart backend

# Detener todo
docker compose --env-file .env.prod -f docker-compose.prod.yml down

# Detener y borrar volumenes (CUIDADO: borra BD y archivos)
docker compose --env-file .env.prod -f docker-compose.prod.yml down -v

# Ejecutar migraciones manualmente
docker compose --env-file .env.prod -f docker-compose.prod.yml exec backend alembic upgrade head

# Restaurar backup
cat backups/si2_backup_2026-07-23_0200.sql | \
  docker compose --env-file .env.prod -f docker-compose.prod.yml exec -T postgres \
  psql -U "${POSTGRES_USER}" "${POSTGRES_DB}"
```

## 9. Renovacion de certificados SSL

El servicio `certbot` revisa cada 12h si el certificado necesita renovacion.
Nginx se recarga automaticamente cada 6h para aplicar nuevos certificados.

Para renovar manualmente:
```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml exec certbot certbot renew
docker compose --env-file .env.prod -f docker-compose.prod.yml exec nginx nginx -s reload
```

## 10. Actualizar la aplicacion

Cuando quieras desplegar cambios nuevos:

```bash
cd proyecto-si2
git pull
docker compose --env-file .env.prod -f docker-compose.prod.yml build
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d
```

## Arquitectura de servicios

```
Internet
  │
  ├─ :80 ──> nginx ──(HTTP redirect 301)──> :443
  │            │
  └─ :443 ──> nginx (HTTPS + Angular SPA)
               │
               ├── /            → Angular SPA (static files)
               ├── /api/*       → backend:8000 (FastAPI)
               └── /media/*     → backend:8000/media/ (archivos)
                                  │
                                  └── postgres:5432 (PostgreSQL 16)
```

- **postgres**: Base de datos principal. Persiste en volumen `postgres_data`
- **backend**: API FastAPI en Python 3.12. Ejecuta migraciones automaticamente al iniciar
- **nginx**: Sirve el panel Angular y actua como reverse proxy al backend. TLS con Let's Encrypt
- **certbot**: Renovacion automatica de certificados SSL cada 12h
