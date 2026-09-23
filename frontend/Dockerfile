# Build static GlowPath UI, then serve via nginx (proxies /v1 → API).
FROM node:20-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY index.html vite.config.ts tsconfig.json tsconfig.app.json tsconfig.node.json ./
COPY public ./public
COPY src ./src

# Empty = same-origin /v1 (nginx proxies to the API container).
ARG VITE_API_BASE_URL=
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build

FROM nginx:1.27-alpine

COPY nginx.conf.template /etc/nginx/conf.d/default.conf.template
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh
COPY --from=build /app/dist /usr/share/nginx/html

ENV PORT=80
ENV API_UPSTREAM=http://app:8000

EXPOSE 80

ENTRYPOINT ["/docker-entrypoint.sh"]
