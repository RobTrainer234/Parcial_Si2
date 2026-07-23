FROM node:20-alpine AS frontend-build

WORKDIR /build/frontend

COPY Frontend/package.json Frontend/package-lock.json ./
RUN npm ci

COPY Frontend/ ./
RUN npm run build

FROM nginx:1.27-alpine

ENV BACKEND_URL=http://backend:8000

COPY nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY --from=frontend-build /build/frontend/dist/frontend_app/browser/ /usr/share/nginx/html/

EXPOSE 80
