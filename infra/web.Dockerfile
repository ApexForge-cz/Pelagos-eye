FROM node:24-alpine AS build

WORKDIR /workspace
COPY package.json package-lock.json ./
COPY apps/web/package.json ./apps/web/package.json
RUN npm ci

COPY apps/web ./apps/web
RUN npm run web:build

FROM nginxinc/nginx-unprivileged:1.29-alpine
COPY infra/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /workspace/apps/web/dist /usr/share/nginx/html

EXPOSE 8080
