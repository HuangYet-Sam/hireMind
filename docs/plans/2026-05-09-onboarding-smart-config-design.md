# Onboarding Wizard + Smart Configuration Design

Date: 2026-05-09

## Overview

Three-layer intelligent configuration guidance system for Hermes Web UI:
1. **Onboarding Wizard** - Full-screen 4-step guided setup for first-time users
2. **Health Dashboard** - Configuration health check card embedded in SettingsView
3. **Smart Suggestions** - Event-driven configuration optimization suggestions

## Architecture

```
┌─────────────────────────────────────────────────┐
│  Layer 1: Onboarding Wizard (Full-screen)       │
│  Triggered on first login · 4 steps · marks done│
├─────────────────────────────────────────────────┤
│  Layer 2: Health Dashboard (SettingsView top)    │
│  Config health card · missing items · quick fix  │
├─────────────────────────────────────────────────┤
│  Layer 3: Smart Suggestions (Floating)           │
│  Anomaly detection · proactive config suggestions│
└─────────────────────────────────────────────────┘
```

### Trigger Conditions

| Layer | Trigger | Duration |
|-------|---------|----------|
| Wizard | First login (`onboarding_done: false`) | One-time |
| Health Dashboard | Every visit to Settings page | Persistent |
| Smart Suggestions | Configuration anomaly detected | Event-driven |

### Data Flow

```
Wizard/Health → SettingsStore → Config API → config.yaml / .env
                                    ↓
                              Hermes Gateway → LLM → SOUL.md generation
```

## Layer 1: Onboarding Wizard

### File Structure

```
components/hermes/onboarding/
├── OnboardingWizard.vue          # Full-screen container + step control
├── HealthDashboard.vue           # Health check card (post-wizard)
├── steps/
│   ├── ProviderStep.vue          # Step 1: AI Provider config
│   ├── SoulStep.vue              # Step 2: Soul personality generation
│   ├── PlatformStep.vue          # Step 3: Platform connections
│   └── SmartConfigStep.vue       # Step 4: Smart config recommendations
└── composables/
    ├── useAIGeneration.ts        # AI generation via gateway chat API
    ├── useHealthCheck.ts         # Health check logic
    └── useSmartSuggestions.ts    # Smart suggestion engine
```

### Step 1: ProviderStep (Manual, Hard Dependency)

- Select Provider (OpenAI / Anthropic / Google / Custom)
- Input API Key
- Select default Model
- **Validation required before proceeding** - calls `/api/hermes/v1/models` to test connectivity
- Reuses existing ModelSettings provider logic

### Step 2: SoulStep (AI Generated)

- User describes their use case in natural language OR selects a preset template
- Preset templates: Customer Service, Coding Assistant, Writing Assistant, Custom
- Click "AI Generate" → calls Hermes Gateway chat API → LLM generates SOUL.md content
- Preview generated content with edit capability
- Can regenerate if unsatisfied
- **API Key from Step 1 is required** (chicken-and-egg resolved)

### Step 3: PlatformStep (Optional)

- Grid of platform cards (Telegram, Discord, Slack, WhatsApp, WeChat, etc.)
- Click to select, expands inline configuration form
- Credentials saved via `saveCredentials()` → `.env`
- Each platform has individual "Test Connection" button
- **Entirely skippable** - no platform required to complete wizard

### Step 4: SmartConfigStep (AI Recommended)

- AI analyzes SOUL.md content + connected platforms + current config
- Recommends optimal config.yaml parameters with reasoning:
  - `agent.max_turns` (scenario-based)
  - `agent.gateway_timeout` (conversation length)
  - `memory.enabled`, `memory.char_limit` (context needs)
  - Platform-specific settings (free_text, mentions_only)
  - `session_reset` mode
- Each recommendation has [Accept] / [Customize] toggle
- "Accept All" button for one-click application

## Layer 2: Health Dashboard

Embedded at top of SettingsView after wizard completion.

### Health Check Items

| Check | Method | Status |
|-------|--------|--------|
| AI Provider | Test `/api/hermes/v1/models` connectivity | ✅/❌ |
| SOUL.md | Check file is non-empty | ✅/⚠️ empty |
| Platform Connections | Check gateway status per platform | ✅/⚠️/❌ |
| Credential Validity | Check .env keys exist and not expired | ✅/⚠️/❌ |
| Config Completeness | AI scan for missing/abnormal config items | ✅/⚠️ |

### UI

- Collapsible card at SettingsView top
- Summary: `✅ Provider  ✅ Soul  ⚠ Platforms  ✅ Config`
- Expandable details with specific issues
- Quick-fix buttons for each issue
- "Re-run Wizard" button

## Layer 3: Smart Suggestions

Event-driven notification-based suggestions.

### Trigger Examples

- Rate limit error → suggest adding backup provider
- Multiple platforms connected without memory → suggest enabling memory
- Long conversations timing out → suggest increasing timeout
- Unused platforms → suggest disconnecting

### UI

- Naive UI `NNotificationProvider` notifications
- Non-blocking, dismissable
- Action buttons linking to relevant settings section

## Backend Changes

Minimal - only one new config field:

```yaml
display:
  onboarding_done: false  # Wizard completion marker
```

No new API endpoints needed. Existing APIs suffice:
- `GET/PUT /api/hermes/config` - Config management
- `GET/POST /api/hermes/memory` - SOUL.md management
- `PUT /api/hermes/config/credentials` - Credential management
- `/api/hermes/v1/runs` - AI generation via chat API

## File Changes Summary

### New Files

```
components/hermes/onboarding/
├── OnboardingWizard.vue
├── HealthDashboard.vue
├── steps/
│   ├── ProviderStep.vue
│   ├── SoulStep.vue
│   ├── PlatformStep.vue
│   └── SmartConfigStep.vue
└── composables/
    ├── useAIGeneration.ts
    ├── useHealthCheck.ts
    └── useSmartSuggestions.ts
```

### Modified Files

```
views/hermes/SettingsView.vue     # Embed HealthDashboard
router/index.ts                   # Add onboarding route
stores/hermes/settings.ts         # Add onboarding state
i18n/locales/*.ts                 # Add wizard/suggestion translations (8 locales)
components/layout/AppSidebar.vue  # No changes needed (wizard is standalone)
```

## AI Generation Flow

### Soul Generation

```
User describes scenario
  → useAIGeneration.generateSoul(description)
  → POST /api/hermes/v1/runs with system prompt
  → SSE stream back SOUL.md content
  → User previews/edits
  → POST /api/hermes/memory { section: 'soul', content }
```

### Config Recommendation

```
Gather: SOUL.md + platforms + current config
  → useAIGeneration.recommendConfig(context)
  → POST /api/hermes/v1/runs with analysis prompt
  → Parse JSON response
  → Present as toggleable recommendation cards
  → User accepts → PUT /api/hermes/config
```
