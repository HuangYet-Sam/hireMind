# Smart Config Guidance Layer — Design

Date: 2026-05-09

## Problem

Hermes Web UI has three configuration sources (config.yaml, SOUL.md, .env) with complete backend APIs, but the frontend lacks a unified intelligence layer for:

1. **Cross-file conflict detection** — .env has Telegram token but config.yaml doesn't enable Telegram
2. **Config change联动** — Changing SOUL.md doesn't suggest related config adjustments
3. **Smart AI suggestions** — Only existed in the now-deleted onboarding wizard
4. **First-time guidance** — Replaced by SetupChecklist but only covers 4 basic checks

The old 4-step OnboardingWizard was removed (route severed, files deleted). SetupChecklist is a working minimum but lacks the three intelligence layers.

## Architecture: Three-Layer Composable + Thin Orchestration

```
                    ┌──────────────────────────┐
                    │     SetupChecklist.vue     │  ← Unified UI (upgraded)
                    └─────────┬────────────────┘
                              │ consumes items[]
                    ┌─────────▼────────────────┐
                    │   useSmartConfig (orch.)   │  ← Merge + sort + dedup
                    └──┬──────────┬──────────┬──┘
                       │          │          │
           ┌───────────▼──┐  ┌───▼──────┐  ┌▼──────────────┐
           │useConfigHealth│  │useConfigGuide│  │useConfigSuggest│
           │ (detection)  │  │ (guidance)  │  │ (AI suggest)  │
           └──────────────┘  └────────────┘  └───────────────┘
                  │                  │                │
         ┌────────▼──────────────────▼────────────────▼────────┐
         │              Existing API + Store layer              │
         │  fetchConfig / fetchMemory / config/health endpoint  │
         └──────────────────────────────────────────────────────┘
```

## Data Model: SmartConfigItem

All three composables produce items with a unified interface:

```ts
interface SmartConfigItem {
  id: string                              // Unique: "health:env-telegram-no-config"
  source: 'health' | 'guide' | 'suggest'  // Which composable produced it
  severity: 'error' | 'warning' | 'info'  // error=blocking, warning=fix recommended, info=optional
  status: 'active' | 'dismissed' | 'resolved'

  // Display
  title: string               // "Telegram credential exists but not enabled"
  detail: string              // ".env has TELEGRAM_BOT_TOKEN, but config.yaml hasn't enabled telegram"

  // Which config files are involved
  configSources: ('config.yaml' | 'soul.md' | 'env')[]

  // Optional: inline fix action
  action?: {
    type: 'inline' | 'navigate' | 'ai-generate'
    label: string
    target?: string
    payload?: Record<string, any>
  }
}
```

Key decisions:
- `severity` drives sort order: error > warning > info
- `source` dedup: if health reports "SOUL.md empty" and guide adds a fix action, guide version wins
- `dismissed` persisted to localStorage, but severity=error items cannot be dismissed
- `action` is optional — some items are informational only

## Layer 1: useConfigHealth — Detection & Conflict

Upgrades `useSetupStatus`. Pure detection, produces findings from all three config sources.

Backend endpoint: `GET /api/hermes/config/health`

Why backend: .env values (API keys, tokens) should not be exposed to frontend. Backend reads .env + config.yaml + SOUL.md, runs conflict detection, returns structured results.

### Detection Rules

| Category | Rule | Severity | Method |
|----------|------|----------|--------|
| Core missing | Provider not configured | error | `fetchModels()` returns empty |
| Core missing | SOUL.md empty or <10 chars | warning | `memory.soul.trim().length <= 10` |
| Core missing | Memory not enabled | info | `config.memory.memory_enabled !== true` |
| Cross-file conflict | .env has token but config doesn't enable platform | warning | Backend reads both files |
| Cross-file conflict | Config enables platform but .env lacks credential | error | Backend reads both files |
| Cross-file conflict | SOUL.md describes coding but model is chat-only | info | Lightweight keyword match |
| Format validation | API Key format suspicious | warning | Regex per provider (e.g. Telegram: `\d+:[A-Za-z0-9_-]{35}`) |
| Format validation | URL format error | warning | Must start with `http(s)://` |

### Backend Endpoint Design

```
GET /api/hermes/config/health

Response:
{
  "items": [
    {
      "id": "health:env-telegram-no-config",
      "severity": "warning",
      "title": "Telegram credential exists but not enabled",
      "detail": ".env has TELEGRAM_BOT_TOKEN, config.yaml doesn't enable telegram",
      "configSources": ["env", "config.yaml"],
      "action": { "type": "inline", "label": "Enable", "target": "telegram" }
    },
    ...
  ]
}
```

Backend uses existing `envPlatformMap` (already defined in config controller) to cross-reference .env values with config.yaml platform sections. No new data structures needed.

## Layer 2: useConfigGuide — First-Time Guidance

Handles the "user just arrived, nothing configured" scenario. Supplements health layer with actionable inline forms.

- Detects which core configs are missing (based on health results)
- Adds `action` to guide users through inline fixes
- Platform guidance only appears after provider + soul are done
- SOUL.md guide offers AI generation via streaming

Design principle: guide is a supplement to health, not a replacement. If health detects "Provider not configured" (error), guide adds an item with inline action. Orchestration layer deduplicates — guide version wins because it has the action.

## Layer 3: useConfigSuggest — AI Suggestions

Two-part design: **local rules** (free, instant) + **AI generation** (on-demand, streaming).

### Local Rules

| Rule | Condition | Suggestion |
|------|-----------|------------|
| Multi-platform memory | ≥2 platforms + memory disabled | Enable memory |
| Coding max_turns | SOUL.md has coding keywords + max_turns < 20 | Increase to 30 |
| SOUL.md too long | soul.length > 2000 | AI-condense suggestion |
| Gateway timeout | Has platforms + gateway_timeout < 60 | Set to 120s |

### AI Generation (on-demand)

Preserved from deleted `useAIGeneration`:
- `generateSoulSuggestion(currentSoul, instruction)` — streaming SOUL.md refinement
- `generateConfigSuggestion(soul, platforms, currentConfig)` — AI config recommendations

Only triggered by user click, never automatically.

## Orchestration: useSmartConfig

Thin layer: merge + dedup + sort + dismiss persistence.

```ts
export function useSmartConfig() {
  const health = useConfigHealth()
  const guide = useConfigGuide()
  const suggest = useConfigSuggest()

  const items = computed<SmartConfigItem[]>(() => {
    // 1. Merge all sources
    // 2. Dedup: same id, guide wins over health
    // 3. Sort: error > warning > info, then health > guide > suggest
    // 4. Filter out dismissed items (but not error-severity)
  })

  const hasIssues = computed(() => items.value.some(i => i.severity !== 'info'))
  const errorCount = computed(() => items.value.filter(i => i.severity === 'error').length)

  async function refresh() { await health.check() }
  function dismiss(id: string) { /* localStorage persistence */ }

  return { items, hasIssues, errorCount, dismiss, refresh,
           /* passthrough for AI generation */ generating, streamContent,
           generateSoulSuggestion, generateConfigSuggestion }
}
```

## UI: SetupChecklist Upgrade

Replace 4 hardcoded check items with dynamic rendering from `useSmartConfig.items`:

```
┌─────────────────────────────────────────────────────────┐
│  Config Status                       2 items need attention [▾] │
│─────────────────────────────────────────────────────────│
│  ✗ AI Provider — Not configured           [expand →]    │  ← error
│  ⚠ Telegram — Credential exists, not enabled  [Enable]  │  ← warning (inline)
│  ⚠ SOUL.md — Not defined                 [AI Generate]  │  ← warning (ai-generate)
│  ℹ Suggestion: 3 platforms, enable memory?   [Enable]   │  ← info (suggest rule)
│  ✓ Memory — Enabled                                     │  ← resolved
└─────────────────────────────────────────────────────────┘
```

Changes from current SetupChecklist:
- Delete `useSetupStatus` import → use `useSmartConfig`
- Delete 4 hardcoded item template blocks → `v-for="item in items"` + generic renderer
- Keep provider/soul/memory inline handlers in component
- Add generic action rendering based on `item.action.type`
- Add severity icons: error=red ✗, warning=yellow ⚠, info=gray ℹ
- Add dismiss button for severity !== 'error' items

## File Changes

### New Files

```
packages/client/src/composables/useConfigHealth.ts
packages/client/src/composables/useConfigGuide.ts
packages/client/src/composables/useConfigSuggest.ts
packages/client/src/composables/useSmartConfig.ts
packages/server/src/controllers/hermes/health-config.ts
packages/server/src/routes/hermes/health-config.ts
```

### Modified Files

```
packages/client/src/components/hermes/chat/SetupChecklist.vue  ← Upgrade to dynamic rendering
packages/client/src/views/hermes/ChatView.vue                  ← No change needed
packages/client/src/i18n/locales/*.ts                          ← New keys for health items
packages/server/src/routes/index.ts                            ← Register health-config route
```

### Deleted Files

```
packages/client/src/composables/useSetupStatus.ts              ← Replaced by useConfigHealth
```

## Execution Order

1. Create `useConfigHealth.ts` (frontend composable)
2. Create backend `GET /api/hermes/config/health` endpoint
3. Create `useConfigGuide.ts`
4. Create `useConfigSuggest.ts`
5. Create `useSmartConfig.ts` (orchestration)
6. Upgrade `SetupChecklist.vue`
7. Add i18n keys
8. Delete `useSetupStatus.ts`
9. E2E verification
