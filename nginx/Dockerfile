FROM node:20-alpine AS frontend-build

WORKDIR /build/frontend

COPY Frontend/package.json Frontend/package-lock.json ./
RUN npm ci

COPY Frontend/ ./
RUN npm run build

FROM nginx:1.27-alpine

COPY nginx/default.conf /etc/nginx/conf.d/default.conf
COPY --from=frontend-build /build/frontend/dist/frontend_app/browser/ /usr/share/nginx/html/

EXPOSE 80
