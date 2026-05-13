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
FROM node:23-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r agent \
    && useradd -r -g agent -d /home/agent -s /bin/bash agent \
    && mkdir -p /home/agent/.hermes /home/agent/.hermes-web-ui \
    && chown -R agent:agent /home/agent

WORKDIR /app

COPY --from=builder --chown=agent:agent /app/dist ./dist
COPY --from=builder --chown=agent:agent /app/node_modules ./node_modules
COPY --from=builder --chown=agent:agent /app/package.json ./

USER agent

ENV NODE_ENV=production
ENV HOME=/home/agent
ENV HERMES_HOME=/home/agent/.hermes
ENV PORT=6060

EXPOSE 6060

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD node -e "fetch('http://localhost:'+(process.env.PORT||6060)+'/health').then(r=>r.ok?process.exit(0):process.exit(1)).catch(()=>process.exit(1))"

ENTRYPOINT ["node", "dist/server/index.js"]
CMD []
