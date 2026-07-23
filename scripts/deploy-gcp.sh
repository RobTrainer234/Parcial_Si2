#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "==========================================="
echo "  SI2 Auxilio - Deploy en GCP Compute"
echo "==========================================="
echo ""

if [ ! -f "${PROJECT_DIR}/.env.prod" ]; then
    echo "[ERROR] No se encontro .env.prod."
    echo "Ejecuta primero: bash scripts/setup-env-gcp.sh"
    exit 1
fi

source "${PROJECT_DIR}/.env.prod"

cd "$PROJECT_DIR"

echo "[1/6] Deteniendo servicios anteriores..."
docker compose --env-file .env.prod -f docker-compose.prod.yml down 2>/dev/null || true

echo "[2/6] Construyendo imagenes Docker..."
docker compose --env-file .env.prod -f docker-compose.prod.yml build

echo "[3/6] Levantando servicios (HTTP)..."
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d

echo "[4/6] Esperando que los servicios esten listos..."
sleep 10
docker compose --env-file .env.prod -f docker-compose.prod.yml ps

echo ""
echo "[5/6] Obteniendo certificado SSL con Let's Encrypt..."

CERT_EMAIL="${CERT_EMAIL:-admin@${DOMAIN}}"

docker compose --env-file .env.prod -f docker-compose.prod.yml run --rm \
    certbot certonly --webroot \
    --webroot-path=/var/www/certbot \
    -d "${DOMAIN}" \
    --email "${CERT_EMAIL}" \
    --agree-tos \
    --non-interactive

echo ""
echo "[6/6] Recargando nginx con HTTPS..."
docker compose --env-file .env.prod -f docker-compose.prod.yml exec nginx nginx -s reload 2>/dev/null || true

echo ""
echo "==========================================="
echo "  DESPLIEGUE COMPLETO"
echo "==========================================="
echo ""
echo "  Backend:  https://${DOMAIN}/api/health"
echo "  Frontend: https://${DOMAIN}/"
echo "  Media:    https://${DOMAIN}/media/"
echo "  Health:   https://${DOMAIN}/api/health"
echo ""
echo "Comandos utiles:"
echo "  Ver logs:    docker compose --env-file .env.prod -f docker-compose.prod.yml logs -f"
echo "  Ver estado:  docker compose --env-file .env.prod -f docker-compose.prod.yml ps"
echo "  Detener:     docker compose --env-file .env.prod -f docker-compose.prod.yml down"
echo "  Backup DB:   bash scripts/backup-db-gcp.sh"
echo ""
