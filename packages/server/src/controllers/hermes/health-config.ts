import { join } from 'path'
import YAML from 'js-yaml'
import { getActiveConfigPath, getActiveEnvPath } from '../../services/hermes/hermes-profile'
import { safeReadFile, getHermesDir } from '../../services/config-helpers'

interface HealthItem {
  id: string
  severity: 'error' | 'warning' | 'info'
  title: string
  detail: string
  configSources: ('config.yaml' | 'soul.md' | 'env')[]
  action?: {
    type: 'inline' | 'navigate'
    label: string
    target?: string
    payload?: Record<string, any>
  }
}

// Map env vars to [platform, configPath]
const ENV_PLATFORM_MAP: Record<string, [string, string]> = {
  TELEGRAM_BOT_TOKEN: ['telegram', 'token'],
  DISCORD_BOT_TOKEN: ['discord', 'token'],
  SLACK_BOT_TOKEN: ['slack', 'token'],
  MATRIX_ACCESS_TOKEN: ['matrix', 'token'],
  FEISHU_APP_ID: ['feishu', 'extra.app_id'],
  FEISHU_APP_SECRET: ['feishu', 'extra.app_secret'],
  DINGTALK_CLIENT_ID: ['dingtalk', 'extra.client_id'],
  DINGTALK_CLIENT_SECRET: ['dingtalk', 'extra.client_secret'],
  WECOM_BOT_ID: ['wecom', 'extra.bot_id'],
  WECOM_SECRET: ['wecom', 'extra.secret'],
  WEIXIN_TOKEN: ['weixin', 'token'],
  WHATSAPP_ENABLED: ['whatsapp', 'enabled'],
  SIGNAL_HTTP_URL: ['signal', 'extra.http_url'],
  EMAIL_ADDRESS: ['email', 'extra.address'],
  EMAIL_PASSWORD: ['email', 'extra.password'],
  IRC_SERVER: ['irc', 'extra.server'],
  MATTERMOST_URL: ['mattermost', 'extra.url'],
  MATTERMOST_TOKEN: ['mattermost', 'token'],
  TEAMS_APP_ID: ['teams', 'extra.app_id'],
  TEAMS_CLIENT_SECRET: ['teams', 'extra.client_secret'],
  QQ_APP_ID: ['qq', 'extra.app_id'],
  QQ_CLIENT_SECRET: ['qq', 'extra.client_secret'],
  YUANBAO_APP_ID: ['yuanbao', 'extra.app_id'],
  YUANBAO_TOKEN: ['yuanbao', 'token'],
  WEBHOOK_URL: ['webhook', 'extra.url'],
  HOMEASSISTANT_URL: ['homeassistant', 'extra.url'],
  HOMEASSISTANT_TOKEN: ['homeassistant', 'token'],
  FLOAT_API_KEY: ['float', 'extra.api_key'],
}

const PLATFORM_ENV_REQUIREMENTS: Record<string, string[]> = {}
for (const [envVar, [platform]] of Object.entries(ENV_PLATFORM_MAP)) {
  if (!PLATFORM_ENV_REQUIREMENTS[platform]) PLATFORM_ENV_REQUIREMENTS[platform] = []
  PLATFORM_ENV_REQUIREMENTS[platform].push(envVar)
}

function parseEnv(raw: string): Record<string, string> {
  const env: Record<string, string> = {}
  for (const line of raw.split('\n')) {
    const trimmed = line.trim()
    if (!trimmed || trimmed.startsWith('#')) continue
    const eqIdx = trimmed.indexOf('=')
    if (eqIdx === -1) continue
    const key = trimmed.slice(0, eqIdx).trim()
    const val = trimmed.slice(eqIdx + 1).trim()
    if (val) env[key] = val
  }
  return env
}

function hasPlatformConfig(config: Record<string, any>, platform: string): boolean {
  const p = config.platforms?.[platform]
  if (!p) return false
  return Object.values(p).some(v => v !== undefined && v !== null && v !== '')
}

export async function check(ctx: import('koa').Context) {
  try {
    const items: HealthItem[] = []

    const [configRaw, envRaw, soulRaw] = await Promise.all([
      safeReadFile(getActiveConfigPath()),
      safeReadFile(getActiveEnvPath()),
      safeReadFile(join(getHermesDir(), 'SOUL.md')),
    ])

    const config: Record<string, any> = configRaw ? (YAML.load(configRaw, { schema: YAML.JSON_SCHEMA }) as Record<string, any>) || {} : {}
    const env = envRaw ? parseEnv(envRaw) : {}
    const soul = soulRaw || ''

    // Conflict: env has credential but config doesn't enable
    const envPlatforms = new Set<string>()
    for (const [envVar, [platform]] of Object.entries(ENV_PLATFORM_MAP)) {
      if (env[envVar]) envPlatforms.add(platform)
    }

    for (const platform of envPlatforms) {
      if (!hasPlatformConfig(config, platform)) {
        items.push({
          id: `health:env-${platform}-no-config`,
          severity: 'warning',
          title: `${platform} credential exists but not enabled`,
          detail: `.env has credentials for ${platform}, but it is not configured in config.yaml`,
          configSources: ['env', 'config.yaml'],
          action: { type: 'inline', label: 'Enable', target: platform, payload: { platform } },
        })
      }
    }

    // Conflict: config enables platform but env lacks credential
    const configPlatforms = config.platforms || {}
    for (const [platform] of Object.entries(configPlatforms)) {
      if (!PLATFORM_ENV_REQUIREMENTS[platform]) continue
      const required = PLATFORM_ENV_REQUIREMENTS[platform]
      const missing = required.filter(v => !env[v])
      if (missing.length > 0 && hasPlatformConfig(config, platform)) {
        items.push({
          id: `health:config-${platform}-no-cred`,
          severity: 'error',
          title: `${platform} enabled but missing credential`,
          detail: `${platform} is configured but required credential is missing from .env`,
          configSources: ['config.yaml', 'env'],
          action: { type: 'navigate', label: 'Configure', target: 'hermes.settings' },
        })
      }
    }

    // SOUL.md check
    if (!soul || soul.trim().length <= 10) {
      items.push({
        id: 'health:soul-empty',
        severity: 'warning',
        title: 'SOUL.md not defined',
        detail: 'Agent personality is empty. Define it to give your agent a clear role.',
        configSources: ['soul.md'],
        action: { type: 'inline', label: 'Define', target: 'soul' },
      })
    }

    ctx.body = { items }
  } catch {
    ctx.status = 500
    ctx.body = { error: 'Failed to read configuration' }
  }
}
