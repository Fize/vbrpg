FROM node:24-alpine AS build
RUN npm install --global pnpm@11.22.0
WORKDIR /app
COPY . .
RUN pnpm install --frozen-lockfile
RUN pnpm run build:web

FROM nginx:alpine
COPY apps/web/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/apps/web/dist /usr/share/nginx/html
EXPOSE 80
