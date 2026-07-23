#!/bin/sh
set -e

DOMAIN="${DOMAIN:-_}"
BACKEND_URL="${BACKEND_URL:-http://backend:8000}"

if [ -f "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem" ]; then
    echo "[nginx] SSL certificate found for ${DOMAIN}, enabling HTTPS"
    envsubst '${DOMAIN} ${BACKEND_URL}' \
        < /etc/nginx/templates/default-ssl.conf.template \
        > /etc/nginx/conf.d/default.conf
else
    echo "[nginx] No SSL certificate yet, starting HTTP-only"
    envsubst '${DOMAIN} ${BACKEND_URL}' \
        < /etc/nginx/templates/default.conf.template \
        > /etc/nginx/conf.d/default.conf
fi

nginx -g "daemon off;" &
NGINX_PID=$!

while true; do
    sleep 6h
    if [ -f "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem" ] \
        && ! grep -q "listen 443" /etc/nginx/conf.d/default.conf 2>/dev/null; then
        echo "[nginx] SSL cert detected, switching to HTTPS config"
        envsubst '${DOMAIN} ${BACKEND_URL}' \
            < /etc/nginx/templates/default-ssl.conf.template \
            > /etc/nginx/conf.d/default.conf
    fi
    echo "[nginx] Reloading configuration"
    nginx -s reload
done &
RELOAD_PID=$!

wait $NGINX_PID
