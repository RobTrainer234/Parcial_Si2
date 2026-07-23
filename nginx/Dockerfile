FROM node:20-alpine AS frontend-build

WORKDIR /build/frontend

COPY Frontend/package.json Frontend/package-lock.json ./
RUN npm ci

COPY Frontend/ ./
RUN npm run build

FROM nginx:1.27-alpine

ENV BACKEND_URL=http://backend:8000
ENV DOMAIN=_

COPY nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY nginx/default-ssl.conf.template /etc/nginx/templates/default-ssl.conf.template
COPY nginx/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

COPY --from=frontend-build /build/frontend/dist/frontend_app/browser/ /usr/share/nginx/html/

EXPOSE 80 443

ENTRYPOINT ["/entrypoint.sh"]
