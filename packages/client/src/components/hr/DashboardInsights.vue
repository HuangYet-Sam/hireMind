<script setup lang="ts">
/**
 * DashboardInsights — M8 AI洞察面板组件
 *
 * Props: insights (AIInsight[]), loading
 * 分类展示：📈趋势 / ⚠️风险 / 💡机会 / 🎯建议
 * M8 增强：已读/未读标记、忽略按钮、查看全部洞察、计数徽标
 * Emits: refresh, action, viewAll
 */
import { computed, ref } from 'vue'
import { NTag, NButton, NSpin, NEmpty, NSpace, NBadge } from 'naive-ui'
import type { AIInsight } from '@/api/hr/dashboard'

const props = defineProps<{
  insights: AIInsight[]
  loading?: boolean
}>()

const emit = defineEmits<{
  refresh: []
  action: [insightId: string, action: 'read' | 'unread' | 'ignore' | 'dismiss']
  viewAll: []
}>()

// ── Read status tracking (local) ────────────────────────────

const readStatusMap = ref<Record<string, { read: boolean; ignored: boolean }>>({})

function getReadStatus(id: string): { read: boolean; ignored: boolean } {
  return readStatusMap.value[id] ?? { read: false, ignored: false }
}

function isUnread(insight: AIInsight): boolean {
  const status = getReadStatus(insight.id)
  return !status.read && !status.ignored
}

function isIgnored(insight: AIInsight): boolean {
  return getReadStatus(insight.id).ignored
}

// ── Computed ─────────────────────────────────────────────────

const visibleInsights = computed(() => {
  return props.insights.filter(i => !isIgnored(i))
})

const unreadCount = computed(() => {
  return props.insights.filter(i => isUnread(i)).length
})

// ── Category config ─────────────────────────────────────────

interface CategoryConfig {
  icon: string
  label: string
  color: 'info' | 'warning' | 'error' | 'success'
}

const categoryMap: Record<string, CategoryConfig> = {
  trend: { icon: '📈', label: '趋势', color: 'info' },
  risk: { icon: '⚠️', label: '风险', color: 'error' },
  opportunity: { icon: '💡', label: '机会', color: 'success' },
  suggestion: { icon: '🎯', label: '建议', color: 'warning' },
}

// ── Grouped insights ─────────────────────────────────────────

const groupedInsights = computed(() => {
  const groups: Record<string, AIInsight[]> = {}
  for (const insight of visibleInsights.value) {
    const cat = insight.category
    if (!groups[cat]) groups[cat] = []
    groups[cat].push(insight)
  }
  return groups
})

const categoryOrder = ['risk', 'trend', 'opportunity', 'suggestion']

const sortedCategories = computed(() => {
  return categoryOrder.filter(cat => groupedInsights.value[cat]?.length)
})

// ── Active filter ────────────────────────────────────────────

const activeFilter = ref<string>('all')

const filteredInsights = computed(() => {
  if (activeFilter.value === 'all') return visibleInsights.value
  return visibleInsights.value.filter(i => i.category === activeFilter.value)
})

// ── Actions ──────────────────────────────────────────────────

function markAsRead(id: string) {
  readStatusMap.value[id] = { read: true, ignored: false }
  emit('action', id, 'read')
}

function ignoreInsight(id: string) {
  readStatusMap.value[id] = { read: false, ignored: true }
  emit('action', id, 'ignore')
}

// ── Helpers ──────────────────────────────────────────────────

function getCategoryConfig(category: string): CategoryConfig {
  return categoryMap[category] ?? { icon: '📌', label: category, color: 'info' as const }
}

function formatTimestamp(dateStr?: string): string {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - d.getTime()
  const diffMins = Math.floor(diffMs / (1000 * 60))
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

  if (diffMins < 1) return '刚刚'
  if (diffMins < 60) return `${diffMins} 分钟前`
  if (diffHours < 24) return `${diffHours} 小时前`
  if (diffDays < 7) return `${diffDays} 天前`
  return d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.8) return 'var(--success)'
  if (confidence >= 0.6) return 'var(--warning)'
  return 'var(--error)'
}

function getConfidenceLabel(confidence: number): string {
  if (confidence >= 0.8) return '高'
  if (confidence >= 0.6) return '中'
  return '低'
}
</script>

<template>
  <div class="dashboard-insights">
    <!-- Header with filters, badge count, and refresh -->
    <div class="insights-header">
      <div class="insights-title-row">
        <h4 class="insights-panel-title">
          AI 洞察
          <NBadge
            v-if="unreadCount > 0"
            :value="unreadCount"
            :max="99"
            type="info"
            class="insight-badge"
          />
        </h4>
      </div>
      <div class="insights-filters">
        <NButton
          text
          size="tiny"
          :type="activeFilter === 'all' ? 'primary' : 'default'"
          class="filter-btn"
          @click="activeFilter = 'all'"
        >
          全部 ({{ visibleInsights.length }})
        </NButton>
        <NButton
          v-for="cat in sortedCategories"
          :key="cat"
          text
          size="tiny"
          :type="activeFilter === cat ? 'primary' : 'default'"
          class="filter-btn"
          @click="activeFilter = cat"
        >
          {{ getCategoryConfig(cat).icon }} {{ getCategoryConfig(cat).label }}
          ({{ groupedInsights[cat]?.length ?? 0 }})
        </NButton>
      </div>
      <NSpace :size="4" align="center">
        <NButton text size="small" class="refresh-btn" @click="emit('refresh')">
          🔄 刷新
        </NButton>
        <NButton
          v-if="insights.length > 0"
          text
          size="small"
          type="primary"
          class="view-all-btn"
          @click="emit('viewAll')"
        >
          查看全部 →
        </NButton>
      </NSpace>
    </div>

    <NSpin :show="loading">
      <div v-if="!visibleInsights.length" class="insights-empty">
        <NEmpty description="暂无 AI 洞察" size="small" />
      </div>

      <div v-else class="insights-list">
        <div
          v-for="insight in filteredInsights"
          :key="insight.id"
          class="insight-card"
          :class="[
            `insight-${insight.category}`,
            { 'insight-unread': isUnread(insight) },
          ]"
        >
          <!-- Unread dot indicator -->
          <div v-if="isUnread(insight)" class="unread-indicator" />

          <!-- Card header -->
          <div class="insight-card-header">
            <div class="insight-category">
              <NTag
                size="tiny"
                :type="getCategoryConfig(insight.category).color"
                round
              >
                {{ getCategoryConfig(insight.category).icon }}
                {{ getCategoryConfig(insight.category).label }}
              </NTag>
            </div>
            <div class="insight-card-actions">
              <span v-if="insight.created_at" class="insight-time">
                {{ formatTimestamp(insight.created_at) }}
              </span>
              <NButton
                v-if="isUnread(insight)"
                text
                size="tiny"
                class="action-btn"
                @click.stop="markAsRead(insight.id)"
              >
                ✓
              </NButton>
              <NButton
                text
                size="tiny"
                class="action-btn ignore-btn"
                @click.stop="ignoreInsight(insight.id)"
              >
                忽略
              </NButton>
            </div>
          </div>

          <!-- Card title -->
          <div class="insight-title">{{ insight.title }}</div>

          <!-- Card content -->
          <p class="insight-content">{{ insight.content }}</p>

          <!-- Confidence bar -->
          <div v-if="insight.confidence != null" class="confidence-row">
            <span class="confidence-label">置信度</span>
            <div class="confidence-bar">
              <div
                class="confidence-fill"
                :style="{
                  width: `${insight.confidence * 100}%`,
                  background: getConfidenceColor(insight.confidence),
                }"
              />
            </div>
            <span class="confidence-value" :style="{ color: getConfidenceColor(insight.confidence) }">
              {{ getConfidenceLabel(insight.confidence) }} {{ (insight.confidence * 100).toFixed(0) }}%
            </span>
          </div>

          <!-- Action suggestion -->
          <div v-if="insight.action_suggestion" class="action-suggestion">
            <span class="action-icon">💡</span>
            <span class="action-text">{{ insight.action_suggestion }}</span>
          </div>
        </div>
      </div>

      <!-- View all button at bottom -->
      <div v-if="insights.length > filteredInsights.length" class="view-all-footer">
        <NButton text size="small" type="primary" @click="emit('viewAll')">
          查看全部洞察 ({{ insights.length }}) →
        </NButton>
      </div>
    </NSpin>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.dashboard-insights {
  display: flex;
  flex-direction: column;
  height: 100%;
}

// Header
.insights-header {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-bottom: 12px;
  border-bottom: 1px solid $border-light;
  margin-bottom: 12px;
}

.insights-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.insights-panel-title {
  font-size: 14px;
  font-weight: 600;
  color: $text-primary;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.insight-badge {
  :deep(.n-badge-sup) {
    font-size: 10px;
  }
}

.insights-filters {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
}

.filter-btn {
  font-size: 12px;
  padding: 2px 6px;
}

.refresh-btn {
  font-size: 12px;
  color: $text-muted;
  flex-shrink: 0;

  &:hover {
    color: $text-primary;
  }
}

.view-all-btn {
  font-size: 12px;
  flex-shrink: 0;
}

.insights-empty {
  padding: 32px 0;
}

// Insights list
.insights-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 500px;
  overflow-y: auto;
}

// Insight card
.insight-card {
  padding: 12px;
  padding-left: 16px;
  border-radius: $radius-sm;
  border: 1px solid $border-light;
  background: $bg-card;
  transition: border-color $transition-fast, box-shadow $transition-fast;
  position: relative;

  &:hover {
    border-color: $border-color;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  }

  &.insight-risk {
    border-left: 3px solid var(--error);
  }

  &.insight-trend {
    border-left: 3px solid var(--accent-info);
  }

  &.insight-opportunity {
    border-left: 3px solid var(--success);
  }

  &.insight-suggestion {
    border-left: 3px solid var(--warning);
  }

  &.insight-unread {
    background: rgba(74, 144, 217, 0.03);
  }
}

// Unread indicator (blue dot)
.unread-indicator {
  position: absolute;
  top: 14px;
  left: 6px;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #4a90d9;
}

.insight-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
  gap: 8px;
}

.insight-card-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

.action-btn {
  font-size: 11px;
  padding: 0 4px;
  color: $text-muted;

  &:hover {
    color: $text-primary;
  }
}

.ignore-btn {
  &:hover {
    color: var(--warning);
  }
}

.insight-time {
  font-size: 11px;
  color: $text-muted;
}

.insight-title {
  font-size: 14px;
  font-weight: 600;
  color: $text-primary;
  line-height: 1.4;
  margin-bottom: 4px;
}

.insight-content {
  font-size: 13px;
  color: $text-secondary;
  line-height: 1.6;
  margin: 0 0 8px;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

// Confidence bar
.confidence-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.confidence-label {
  font-size: 11px;
  color: $text-muted;
  flex-shrink: 0;
}

.confidence-bar {
  flex: 1;
  height: 6px;
  background: $bg-secondary;
  border-radius: 3px;
  overflow: hidden;
}

.confidence-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.3s ease;
}

.confidence-value {
  font-size: 11px;
  font-weight: 600;
  flex-shrink: 0;
  min-width: 48px;
  text-align: right;
}

// Action suggestion
.action-suggestion {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding: 8px 10px;
  background: $bg-secondary;
  border-radius: $radius-sm;
  font-size: 12px;
  color: $text-secondary;
  line-height: 1.5;

  .action-icon {
    flex-shrink: 0;
    font-size: 13px;
    margin-top: 1px;
  }

  .action-text {
    flex: 1;
  }
}

// View all footer
.view-all-footer {
  display: flex;
  justify-content: center;
  padding-top: 12px;
  margin-top: 8px;
  border-top: 1px solid $border-light;
}
</style>
