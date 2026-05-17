# ── HireMind Frontend Dockerfile ──────────────────────────────
# Multi-stage build: Node.js build → Nginx serve

# ── Stage 1: Build ────────────────────────────────────────────
FROM node:23-alpine AS build

WORKDIR /app

# Copy root package files (monorepo root has all deps)
COPY package.json package-lock.json ./

# Install all dependencies (including devDependencies for build)
RUN npm install --ignore-scripts

# Copy full source tree (vite.config.ts, packages/, tsconfig, etc.)
COPY . .

# Build the Vue frontend (output → dist/client)
# Note: skip vue-tsc type-check here; use 'npm run build' locally for full checks
RUN npx vite build

# ── Stage 2: Serve ────────────────────────────────────────────
FROM nginx:alpine AS production

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom nginx configuration
COPY packages/client/nginx.conf /etc/nginx/conf.d/default.conf

# Copy built assets from build stage
COPY --from=build /app/dist/client /usr/share/nginx/html

# Expose HTTP port
EXPOSE 80

# Healthcheck: verify nginx is serving
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://127.0.0.1/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
