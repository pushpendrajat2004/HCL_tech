FROM node:22-bookworm-slim AS dependencies
WORKDIR /app
COPY api/package*.json ./
RUN npm ci --omit=dev
FROM node:22-bookworm-slim
ENV NODE_ENV=production
WORKDIR /app
COPY --from=dependencies /app/node_modules ./node_modules
COPY api/package*.json ./
COPY api/src ./src
USER node
EXPOSE 4000
CMD ["node","src/server.js"]
