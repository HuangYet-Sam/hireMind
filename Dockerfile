# ── Stage 1: Build ──────────────────────────────────────────────
FROM node:23-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    make g++ python3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY package*.json ./

ENV NODE_OPTIONS=--max-old-space-size=4096
RUN npm ci --ignore-scripts && npm rebuild node-pty

COPY . .
RUN npm run build && npm prune --omit=dev

# ── Stage 2: Runtime ───────────────────────────────────────────
FROM python:3.13-slim-trixie

COPY --from=node:23-slim /usr/local/bin/node /usr/local/bin/node
RUN ln -sf /usr/local/bin/python3 /usr/bin/python3

RUN sed -i 's|deb.debian.org|mirrors.ustc.edu.cn|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null; \
    sed -i 's|deb.debian.org|mirrors.ustc.edu.cn|g' /etc/apt/sources.list 2>/dev/null; \
    apt-get update && apt-get install -y --no-install-recommends \
    git curl \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /home/agent/.hermes /home/agent/.hermes-web-ui

WORKDIR /app

COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./

ENV NODE_ENV=production
ENV HOME=/home/agent
ENV HERMES_HOME=/home/agent/.hermes
ENV PORT=6060

EXPOSE 6060

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD node -e "fetch('http://localhost:'+(process.env.PORT||6060)+'/health').then(r=>r.ok?process.exit(0):process.exit(1)).catch(()=>process.exit(1))"

ENTRYPOINT ["node", "dist/server/index.js"]
CMD []
