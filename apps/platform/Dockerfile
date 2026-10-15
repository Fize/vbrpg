FROM node:24-alpine AS build
RUN npm install --global pnpm@11.22.0
WORKDIR /app
COPY pnpm-lock.yaml pnpm-workspace.yaml package.json ./
COPY apps/platform/package.json apps/platform/
RUN pnpm install --frozen-lockfile
COPY . .
RUN pnpm --filter @vbrpg/platform build

FROM node:24-alpine AS runtime
RUN npm install --global pnpm@11.22.0
WORKDIR /app
COPY --from=build /app /app
ENV NODE_ENV=production
EXPOSE 3000
CMD ["node", "apps/platform/dist/server/main.js", "--role=api"]
