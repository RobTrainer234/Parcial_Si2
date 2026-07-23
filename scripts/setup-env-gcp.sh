#!/bin/bash
set -e

echo "==========================================="
echo "  SI2 Auxilio - Configuracion .env.prod"
echo "==========================================="
echo ""

if [ ! -f ".env.prod.example" ]; then
    echo "[ERROR] No se encontro .env.prod.example"
    echo "Asegurate de estar en la raiz del proyecto (cd ~/proyecto-si2)"
    exit 1
fi

IP=$(curl -s ifconfig.me 2>/dev/null || curl -s httpbin.org/ip 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' || echo "")
if [ -z "$IP" ]; then
    echo "[ERROR] No se pudo detectar la IP publica."
    echo "Ejecuta: curl ifconfig.me"
    echo "Y anota tu IP para usarla manualmente."
fi

JWT_SECRET=$(openssl rand -hex 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(32))")
DB_PASSWORD=$(openssl rand -hex 16 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(16))")

echo ""
echo "--- Valores generados ---"
echo "IP publica detectada: $IP"
echo "JWT_SECRET_KEY:       $JWT_SECRET"
echo "POSTGRES_PASSWORD:    $DB_PASSWORD"
echo ""

read -p "Dominio (ej: miapp.com) o presiona Enter para usar la IP [$IP]: " DOMAIN
DOMAIN=${DOMAIN:-$IP}

read -p "Email para Let's Encrypt (requerido para HTTPS): " LETSENCRYPT_EMAIL

read -p "API key de Groq (opcional, Enter para omitir): " GROQ_KEY

read -p "SMTP username (Gmail, opcional): " SMTP_USER
read -s -p "SMTP password (app password de Gmail, opcional): " SMTP_PASS
echo ""

URL="http://${DOMAIN}"
if [ -n "$LETSENCRYPT_EMAIL" ]; then
    URL="https://${DOMAIN}"
fi

cat > .env.prod << EOF
APP_NAME="SI2 Auxilio"
APP_ENV=production
POSTGRES_DB=sis_auxilio
POSTGRES_USER=si2_user
POSTGRES_PASSWORD=${DB_PASSWORD}
DATABASE_URL=postgresql+psycopg://si2_user:${DB_PASSWORD}@postgres:5432/sis_auxilio
JWT_SECRET_KEY=${JWT_SECRET}
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REGISTRATION_TOKEN_EXPIRE_MINUTES=15
LOCKOUT_MINUTES=5
DOMAIN=${DOMAIN}
CORS_ALLOW_ORIGINS=${URL},http://localhost:4200
CORS_ALLOW_ORIGIN_REGEX=^https?://.*
MEDIA_PUBLIC_BASE_URL=${URL}/media
FRONTEND_URL=${URL}
SQLALCHEMY_ECHO=false
STORAGE_BACKEND=local
LOCAL_MEDIA_ROOT=/app/media
TRIAGE_AI_PROVIDER=groq
TRIAGE_AI_API_KEY=${GROQ_KEY}
TRIAGE_AI_MODEL=meta-llama/llama-4-scout-17b-16e-instruct
VOICE_AI_PROVIDER=groq
VOICE_AI_MODEL=whisper-large-v3-turbo
REPORT_AI_PROVIDER=groq
REPORT_AI_MODEL=meta-llama/llama-4-scout-17b-16e-instruct
TRIAGE_AUTO_RUN_AFTER_REPORT=false
TRIAGE_MIN_CONFIDENCE=60
MANUAL_REVIEW_CONFIDENCE_THRESHOLD=50
TRIAGE_AI_TIMEOUT_SECONDS=30
MATCHMAKING_REQUEST_TTL_SECONDS=600
WORKSHOP_MAX_ACTION_RADIUS_KM=100
MAPS_PROVIDER=osrm
MAPS_BASE_URL=https://router.project-osrm.org
MAPS_API_KEY=
NAVIGATION_ARRIVAL_THRESHOLD_METERS=50
NAVIGATION_PROVIDER_TIMEOUT_SECONDS=15
PAYMENT_PROVIDER=sandbox
PAYMENT_WEBHOOK_TOKEN=
PAYMENT_REQUEST_EXPIRE_MINUTES=15
PUSH_PROVIDER=sandbox
FCM_CREDENTIALS_FILE=
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USERNAME=${SMTP_USER}
SMTP_PASSWORD=${SMTP_PASS}
EMAIL_FROM_ADDRESS=noreply@si2taller.com
EMAIL_FROM_NAME="SI2 Auxilio"
PASSWORD_RESET_TOKEN_EXPIRE_MINUTES=30
CERT_EMAIL=${LETSENCRYPT_EMAIL}
EOF

echo ""
echo "==========================================="
echo "  .env.prod creado exitosamente!"
echo "==========================================="
echo ""
echo "Valores guardados:"
echo "  DOMAIN=${DOMAIN}"
echo "  URL=${URL}"
echo ""
echo "Ahora ejecuta: bash scripts/deploy-gcp.sh"
