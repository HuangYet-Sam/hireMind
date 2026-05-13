# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Hermes Web UI is a web dashboard for Hermes Agent — a multi-platform AI chat system. It provides session management, scheduled jobs, usage analytics, model configuration, platform channel management (Telegram, Discord, Slack, WhatsApp, Matrix, Feishu, WeChat, WeCom), group chat, kanban board, file management, an integrated terminal, and a streaming chat interface.

The project is designed for **multi-agent extensibility** — Hermes is the first agent integration. All agent-specific code is namespaced under `hermes/` directories, so future agents can be added alongside without conflicts.

**Tech stack:**

- **Frontend:** Vue 3 (Composition API, `<script setup lang="ts">`), Naive UI, Pinia, vue-router (hash history), vue-i18n, SCSS, Vite
- **Backend:** Koa 2, @koa/router v15+, Socket.IO, node-pty (WebSocket terminal), reverse proxy to Hermes gateway
- **Database:** SQLite (via better-sqlite3, managed in `packages/server/src/db/`)
- **Language:** TypeScript (strict mode), single package (no workspaces)
- **Node:** >= 23.0.0

---

## Development Commands

```bash
npm run dev           # Start both server (nodemon) and client (Vite) concurrently
npm run dev:client    # Vite dev server only (proxies API to backend)
npm run dev:server    # nodemon + ts-node for server only
npm run build         # Type-check (vue-tsc) -> Vite build -> esbuild server bundle
npm run preview       # Preview production build with Vite
npm run test          # Run tests (vitest)
npm run test:watch    # Run tests in watch mode
npm run test:coverage # Run tests with coverage report
npx vitest run tests/client/session-search.test.ts   # Run a single test file
npx vitest run tests/client/session-search.test.ts -t "test name"  # Run a single test case
```

- **Dev port:** 8648 (client Vite dev server proxies `/api`, `/v1`, `/health`, `/upload`, `/webhook`, `/socket.io` to `http://127.0.0.1:8648`)
- **Prerequisite:** `hermes` CLI must be installed and on `$PATH` (the server wraps it via `child_process.execFile`)

---

## Architecture

### Top-Level Layout

```
packages/
├── client/src/          # Vue 3 frontend
│   ├── api/             # API layer (shared client.ts + hermes/ modules)
│   ├── components/      # layout/ (shared) + hermes/ (feature components)
│   ├── composables/     # useKeyboard, useTheme
│   ├── i18n/locales/    # en, zh, de, es, fr, ja, ko, pt
│   ├── router/          # Hash-based routing, auth guard
│   ├── stores/hermes/   # Pinia stores (app, chat, models, settings, usage, etc.)
│   ├── styles/          # SCSS variables, global, code-block, theme
│   └── views/hermes/    # Page-level components (chat, jobs, models, kanban, etc.)
├── server/src/          # Koa BFF server
│   ├── controllers/     # Request handlers (shared + hermes/)
│   ├── db/              # SQLite database layer (init, schemas, stores)
│   ├── lib/             # Shared utilities (llm-json, context-compressor, llm-prompt)
│   ├── routes/          # Route registration (shared + hermes/)
│   ├── services/        # Business logic (auth, config, logger + hermes/)
│   └── index.ts         # Bootstrap: middleware → routes → static → Socket.IO
```

### Request Flow

1. **Public routes** (no auth): health, webhook, auth (login/token)
2. **Auth middleware** (`requireAuth`)
3. **Protected routes**: handled locally by Koa controllers → services → Hermes CLI or SQLite
4. **Proxy catch-all**: unmatched `/api/hermes/*` and `/v1/*` → forwarded to upstream Hermes gateway

**Critical:** Custom API endpoints handled locally must be registered in `routes/index.ts` **before** `proxyRoutes`. The proxy catch-all matches all `/api/hermes/*` paths.

### Real-Time Communication

Two Socket.IO namespaces share the same HTTP server:

- **`/chat-run`** — Streaming chat. Replaces the old HTTP POST + SSE approach. Socket.IO rooms keyed by `session_id`. Client emits events to start runs, server streams upstream gateway events back. Handles disconnect/reconnect via `resume` event.
- **`/` (default namespace, group-chat)** — Multi-agent group chat rooms. Agents join rooms, messages relay between human members and AI agents via the context engine.

Terminal still uses raw WebSocket at `/api/hermes/terminal` with `node-pty`.

### Database Layer (`packages/server/src/db/`)

SQLite stores initialized on startup via `initAllStores()`. Key tables:

- **session-store** — Local session data with message history, token counts, compression snapshots
- **sessions-db** — Session list synced from Hermes `state.db` on first startup
- **usage-store** — Token usage analytics
- **kanban-db** — Kanban board tasks and columns
- **conversations-db** — Conversation metadata with schema sync

Schema definitions in `db/hermes/schemas.ts`. Store modules export CRUD functions used by controllers.

### Context Engine (`packages/server/src/services/hermes/context-engine/`)

Compresses conversation history for long sessions. Composed of:
- **compressor.ts** — Main compression logic
- **gateway-client.ts** — Calls LLM for summarization via the upstream gateway
- **prompt.ts** — System prompts for summarization
- **summary-cache.ts** — Caches compressed summaries

### Group Chat (`packages/server/src/services/hermes/group-chat/`)

Multi-agent chat system where AI agents join rooms as members. Uses Socket.IO for real-time messaging and the context engine for message compression.

### Bootstrap Sequence (`packages/server/src/index.ts`)

1. Create data/upload directories, get auth token
2. Init Koa app, init gateway manager
3. Register CORS, body parser, all routes
4. Serve static SPA with fallback to `index.html`
5. Start HTTP server
6. Setup terminal WebSocket, Group Chat Socket.IO, Chat Run Socket.IO
7. Start session deleter (drains pending session deletes)
8. Bind graceful shutdown handler, start version check

---

## Naming Conventions

### Multi-Agent Namespacing

All agent-specific code lives under `{agent-name}/` subdirectories:

| Layer | Shared | Hermes |
|-------|--------|--------|
| API | `api/client.ts` | `api/hermes/*.ts` |
| Components | `components/layout/` | `components/hermes/*/*.vue` |
| Views | `views/LoginView.vue` | `views/hermes/*.vue` |
| Stores | — | `stores/hermes/*.ts` |
| Controllers | `controllers/*.ts` | `controllers/hermes/*.ts` |
| Routes | `routes/*.ts` | `routes/hermes/*.ts` |
| Services | `services/*.ts` | `services/hermes/*.ts` |
| Route names | `login` | `hermes.{page}` |
| API paths | `/health`, `/upload`, `/webhook` | `/api/hermes/*` |

### Route Naming

- **Shared routes:** `login`
- **Agent routes:** `{agent}.{page}` — e.g., `hermes.chat`, `hermes.jobs`, `hermes.kanban`
- **Route paths:** `/hermes/{page}` — e.g., `/hermes/chat`, `/hermes/group-chat`

---

## Frontend Conventions

### Vue Components

All components use `<script setup lang="ts">` with the Composition API:

```vue
<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { NButton, useMessage } from 'naive-ui'
import { someApi } from '@/api/hermes/something'

const { t } = useI18n()
const message = useMessage()
const loading = ref(false)

async function handleAction() {
  loading.value = true
  try {
    await someApi()
    message.success(t('common.saved'))
  } catch {
    message.error(t('common.saveFailed'))
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="my-component">
    <NButton :loading="loading" @click="handleAction">{{ t('common.save') }}</NButton>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.my-component {
  padding: 16px;
}
</style>
```

Key patterns:
- Import Naive UI components directly from `naive-ui`
- `useMessage()` for toast notifications, `useI18n()` for translations
- Scoped SCSS with `@use '@/styles/variables' as *`

### Pinia Stores

Use setup store syntax (function passed to `defineStore`). Stores live in `packages/client/src/stores/hermes/`.

### API Layer

Shared base `api/client.ts` provides:
- `request<T>(path, options)` — typed fetch wrapper with auto `Authorization: Bearer` header and 401 handling
- `getApiKey()` / `setApiKey()` / `clearApiKey()` — token management via `localStorage`

**API path rules:**
- Local BFF endpoints: `/api/hermes/{resource}` — handled by Koa routes
- Gateway proxy endpoints: `/api/hermes/v1/*`, `/api/hermes/jobs/*` — forwarded to upstream
- Shared endpoints: `/health`, `/upload`, `/webhook` — no agent prefix

### i18n

Eight locales in `packages/client/src/i18n/locales/`: `en`, `zh`, `de`, `es`, `fr`, `ja`, `ko`, `pt`. Flat nested object structure. When adding new strings, add to all locale files.

### SCSS Styling

- Global variables: `packages/client/src/styles/variables.scss` — `@use '@/styles/variables' as *`
- Theme: "Pure Ink" (monochrome black/white/gray), no color accent
- Mobile breakpoint: `$breakpoint-mobile: 768px`
- Component styles always `<style scoped lang="scss">`

### Router

Hash-based routing (`createWebHashHistory`). Auth guard in `router.beforeEach` redirects unauthenticated users to `/` (login). Public routes use `meta: { public: true }`.

---

## Backend Conventions

### Architecture: Routes + Controllers + Services

- **Routes** (`routes/`) — thin URL-to-handler mappings, delegate to controllers
- **Controllers** (`controllers/`) — request handling logic
- **Services** (`services/`) — reusable business logic, CLI wrappers, utilities
- **DB stores** (`db/`) — SQLite CRUD functions used by controllers

### @koa/router v15 Syntax

Uses path-to-regexp v8:
- Parameters: `:id` (single segment) or `{*path}` (wildcard, matches `/`)
- No regex groups `(.*)` — use `{*name}` instead
- No modifiers `:id+` or `:id*` — use `{*name}`

### Reverse Proxy

Unmatched `/api/hermes/*` and `/v1/*` requests → upstream Hermes gateway (`http://127.0.0.1:8642`). Path rewriting in `proxy-handler.ts`:
- `/api/hermes/v1/*` → `/v1/*`
- `/api/hermes/*` → `/api/*`

### Hermes CLI Wrapper (`services/hermes/hermes-cli.ts`)

All Hermes interactions go through `child_process.execFile('hermes', [...args])`. Each function wraps a CLI subcommand.

### Auth (`services/auth.ts`)

- Token: `~/.hermes-web-ui/.token` (auto-generated) or `AUTH_TOKEN` env var
- Disabled when `AUTH_DISABLED=1`
- Accepts `Authorization: Bearer <token>` header or `?token=<token>` query param

---

## Build System

- **Vite** builds the frontend: root `packages/client`, output `dist/client`
- **esbuild** bundles the server: `scripts/build-server.mjs`, output `dist/server`
- **tsc** type-checks: `vue-tsc -b` (client) + `tsc --noEmit -p packages/server/tsconfig.json` (server)
- Path alias: `@` → `packages/client/src`
- Chunk splitting: monaco-editor, mermaid, xterm, vue-vendor, ui-vendor separated

---

## Testing

Tests use **Vitest** with `@vue/test-utils` + `@pinia/testing` (frontend) and `vitest` (backend):

```bash
npm run test          # Run all tests once
npm run test:watch    # Watch mode
npm run test:coverage # With coverage
npx vitest run tests/server/sessions-db.test.ts  # Single test file
```

Test files in `tests/client/`, `tests/server/`, `tests/shared/`. Config in root `vitest.config.ts`.

---

## Environment Variables

| Variable | Description |
|---|---|
| `AUTH_DISABLED` | Set to `1` or `true` to disable auth |
| `AUTH_TOKEN` | Custom auth token (overrides auto-generated) |
| `PORT` | Server listen port (default `8648`) |
| `UPSTREAM` | Hermes gateway URL (default `http://127.0.0.1:8642`) |
| `UPLOAD_DIR` | Custom upload directory path |
| `CORS_ORIGINS` | CORS origin config (default `*`) |
| `HERMES_BIN` | Custom path to hermes CLI binary |
| `PROFILE` | Active profile name (default `default`) |

---

## Common Tasks

### Add a new Hermes page

1. Create view in `packages/client/src/views/hermes/MyView.vue`
2. Add route in `packages/client/src/router/index.ts` — name `hermes.myPage`, path `/hermes/my-page`
3. Add sidebar entry in `packages/client/src/components/layout/AppSidebar.vue`
4. Add i18n keys to all locale files in `packages/client/src/i18n/locales/`

### Add a new Hermes API endpoint

1. Add controller in `packages/server/src/controllers/hermes/`
2. Add route in `packages/server/src/routes/hermes/` (thin wrapper)
3. Register in `packages/server/src/routes/index.ts` **before** `proxyRoutes`
4. If it needs SQLite, add schema in `db/hermes/schemas.ts` and store module in `db/hermes/`
5. If it calls Hermes CLI, add wrapper in `services/hermes/hermes-cli.ts`
6. Add frontend API function in `packages/client/src/api/hermes/`

### Add a new Hermes Pinia store

1. Create `packages/client/src/stores/hermes/myFeature.ts` using setup syntax
2. Export `useMyFeatureStore`

### Add a new agent integration

1. Create `api/{agent}/`, `components/{agent}/`, `views/{agent}/`, `stores/{agent}/`
2. Create `controllers/{agent}/`, `routes/{agent}/`, `services/{agent}/`
3. Add routes with `path: '/{agent}/*'`, `name: '{agent}.*'`
4. Register routes in `routes/index.ts` following public → auth → protected order
