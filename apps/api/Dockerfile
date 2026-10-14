FROM node:24-alpine AS build
RUN npm install --global pnpm@11.22.0
WORKDIR /app
COPY . .
RUN pnpm install --frozen-lockfile
RUN pnpm run build:platform

FROM node:24-alpine AS runtime
RUN npm install --global pnpm@11.22.0
WORKDIR /app
COPY --from=build /app /app
EXPOSE 3000
CMD ["node", "apps/api/dist/server.js"]
