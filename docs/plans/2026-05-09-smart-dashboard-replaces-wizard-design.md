# Smart Dashboard — Replace Onboarding Wizard

Date: 2026-05-09

## Problem

The full-screen 4-step Onboarding Wizard is disruptive:
- Blocks the main experience on first login
- One-shot — disappears after completion, never seen again
- Over-engineered: 9 files + 3 composables for a linear flow
- Heavy AI dependency (SOUL generation + config recommendation both need gateway running)

## Solution: Smart Dashboard

Replace the entire wizard with a single `SetupChecklist.vue` component embedded in ChatView.

### Architecture

```
Before (10 files):                   After (2 files):
onboarding/                          components/hermes/chat/
├── OnboardingWizard.vue             └── SetupChecklist.vue      ← NEW
├── HealthDashboard.vue              composables/
├── steps/{4 steps}                  └── useSetupStatus.ts       ← NEW
├── composables/{3 composables}
views/hermes/OnboardingView.vue

Net: -10 files, +2 files, ~60% less code
```

### SetupChecklist UI

```
┌─────────────────────────────────────────────────┐
│  Setup Checklist                    [收起 ▾]     │
│─────────────────────────────────────────────────│
│  ✅ AI Provider — OpenAI (GPT-4o)               │
│  ⚠️ SOUL.md — 未定义              [展开 →]      │
│  ⬜ Platforms — 未连接             [展开 →]      │
│  ✅ Memory — 已启用                              │
└─────────────────────────────────────────────────┘
```

**Key behaviors:**
- Non-blocking: users can chat while configuring
- Expandable items: click to reveal inline mini-forms
- Provider is the only hard dependency (required for AI generation)
- Platforms marked as optional
- Collapsed state persisted to localStorage
- Auto-expands when new issues detected

### Detection Items

| Item | Detection Method | Missing Action |
|------|-----------------|----------------|
| AI Provider | `fetchModels()` returns models | Inline provider select + API key input |
| SOUL.md | `fetchMemory().soul` length > 10 chars | Preset buttons + text input + AI generate (streaming) |
| Platforms | Health check has running platforms | Optional — links to Settings > Platforms |
| Memory | `config.memory.memory_enabled` | One-click toggle |

### Data Flow

```
ChatView mounts
  → useSetupStatus() checks all 4 items via existing APIs
  → returns reactive items[]
  → SetupChecklist renders based on status
  → User configures inline → API calls → item status updates
```

No new backend endpoints needed. Existing APIs:
- `GET/PUT /api/hermes/config` — Config sections
- `GET/POST /api/hermes/memory` — SOUL.md
- `PUT /api/hermes/config/credentials` — Platform credentials
- `/api/hermes/v1/runs` — AI SOUL.md generation

### SOUL.md AI Generation

Preserved from wizard but simplified:
- Embedded directly in SetupChecklist (no separate composable)
- Uses existing chat SSE streaming (`/api/hermes/v1/runs`)
- Disabled if no provider configured
- Preset templates: Customer Service, Coding, Writing, General

### Health Check Split

- `SetupChecklist` — First-time setup guidance (ChatView, progressive)
- `HealthDashboard` — Ongoing monitoring (SettingsView, retained from wizard)

Wait — the existing HealthDashboard in `onboarding/` is deleted. The SettingsView already has health-related display from the old code. We need to verify if HealthDashboard was actually integrated or standalone.

Decision: Keep a minimal health summary in SettingsView as a collapsible section, not as a separate component.

### File Changes

**Delete (10 files):**
```
components/hermes/onboarding/ (entire directory)
views/hermes/OnboardingView.vue
```

**Create (2 files):**
```
components/hermes/chat/SetupChecklist.vue
composables/useSetupStatus.ts
```

**Modify (4 files):**
```
views/hermes/ChatView.vue          — Embed SetupChecklist
router/index.ts                    — Remove onboarding route + guard
stores/hermes/settings.ts          — onboardingDone → setupDismissed (localStorage)
i18n/locales/*.ts                  — Update translation keys
```
