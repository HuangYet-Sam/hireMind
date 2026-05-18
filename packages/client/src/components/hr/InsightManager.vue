<script setup lang="ts">
/**
 * InsightManager — M8 洞察管理组件
 *
 * Props: insights, history, loading
 * 三个 Tab：全部/未读/已读
 * 每条洞察：分类标签+标题+内容+置信度+时间戳
 * 操作：标记已读/忽略/关闭
 * 批量操作：全部标已读
 * 空状态提示
 * Emits: action, refresh
 */
import { computed, ref } from 'vue'
import {
  NCard, NTabs, NTabPane, NTag, NButton, NSpace, NSpin, NEmpty,
  NBadge, NTime,
} from 'naive-ui'
import type { AIInsight } from '@/api/hr/dashboard'

export interface InsightReadStatus {
  id: string
  read: boolean
  ignored: boolean
}

const props = defineProps<{
  insights: AIInsight[]
  history?: AIInsight[]
  loading?: boolean
}>()

const emit = defineEmits<{
  action: [insightId: string, action: 'read' | 'unread' | 'ignore' | 'dismiss']
  refresh: []
}>()

// ── Read status tracking (local) ────────────────────────────

const readStatusMap = ref<Record<string, InsightReadStatus>>({})

function getReadStatus(id: string): InsightReadStatus {
  return readStatusMap.value[id] ?? { id, read: false, ignored: false }
}

function isUnread(insight: AIInsight): boolean {
  const status = getReadStatus(insight.id)
  return !status.read && !status.ignored
}

function isRead(insight: AIInsight): boolean {
  return getReadStatus(insight.id).read
}

function isIgnored(insight: AIInsight): boolean {
  return getReadStatus(insight.id).ignored
}

// ── Tab filtering ────────────────────────────────────────────

const activeTab = ref('all')

const filteredInsights = computed(() => {
  let list = props.insights
  if (activeTab.value === 'unread') {
    list = list.filter(i => isUnread(i))
  } else if (activeTab.value === 'read') {
    list = list.filter(i => isRead(i) && !isIgnored(i))
  }
  return list
})

const unreadCount = computed(() => props.insights.filter(i => isUnread(i)).length)
const readCount = computed(() => props.insights.filter(i => isRead(i) && !isIgnored(i)).length)

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

function getCategoryConfig(category: string): CategoryConfig {
  return categoryMap[category] ?? { icon: '📌', label: category, color: 'info' as const }
}

// ── Actions ──────────────────────────────────────────────────

function markAsRead(id: string) {
  readStatusMap.value[id] = { id, read: true, ignored: false }
  emit('action', id, 'read')
}

function markAsUnread(id: string) {
  readStatusMap.value[id] = { id, read: false, ignored: false }
  emit('action', id, 'unread')
}

function ignoreInsight(id: string) {
  readStatusMap.value[id] = { id, read: false, ignored: true }
  emit('action', id, 'ignore')
}

function dismissInsight(id: string) {
  emit('action', id, 'dismiss')
}

function markAllAsRead() {
  for (const insight of props.insights) {
    if (isUnread(insight)) {
      readStatusMap.value[insight.id] = { id: insight.id, read: true, ignored: false }
      emit('action', insight.id, 'read')
    }
  }
}

// ── Helpers ──────────────────────────────────────────────────

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
  <div class="insight-manager">
    <!-- Header -->
    <div class="manager-header">
      <div class="header-info">
        <h3 class="manager-title">
          洞察管理
          <NBadge v-if="unreadCount > 0" :value="unreadCount" :max="99" type="info" />
        </h3>
        <span class="header-subtitle">
          共 {{ insights.length }} 条洞察，{{ unreadCount }} 条未读
        </span>
      </div>
      <NSpace align="center">
        <NButton
          v-if="unreadCount > 0"
          size="small"
          @click="markAllAsRead"
        >
          全部标已读
        </NButton>
        <NButton text size="small" @click="emit('refresh')">
          🔄 刷新
        </NButton>
      </NSpace>
    </div>

    <NSpin :show="loading">
      <!-- Tabs -->
      <NTabs v-model:value="activeTab" type="line" size="small">
        <NTabPane name="all" :tab="`全部 (${insights.length})`" />
        <NTabPane name="unread" :tab="`未读 (${unreadCount})`" />
        <NTabPane name="read" :tab="`已读 (${readCount})`" />
      </NTabs>

      <!-- Empty state -->
      <div v-if="filteredInsights.length === 0" class="manager-empty">
        <NEmpty :description="activeTab === 'unread' ? '没有未读洞察' : activeTab === 'read' ? '没有已读洞察' : '暂无洞察数据'" />
      </div>

      <!-- Insight list -->
      <div v-else class="insight-list">
        <div
          v-for="insight in filteredInsights"
          :key="insight.id"
          class="insight-item"
          :class="{
            'insight-unread': isUnread(insight),
            [`insight-${insight.category}`]: true,
          }"
        >
          <!-- Unread indicator -->
          <div v-if="isUnread(insight)" class="unread-dot" />

          <!-- Main content -->
          <div class="insight-main">
            <!-- Header row -->
            <div class="insight-item-header">
              <div class="insight-meta">
                <NTag
                  size="tiny"
                  :type="getCategoryConfig(insight.category).color"
                  round
                >
                  {{ getCategoryConfig(insight.category).icon }}
                  {{ getCategoryConfig(insight.category).label }}
                </NTag>
                <span class="insight-time">{{ formatTimestamp(insight.created_at) }}</span>
              </div>

              <!-- Actions -->
              <NSpace :size="4" align="center">
                <NButton
                  v-if="isUnread(insight)"
                  text
                  size="tiny"
                  @click="markAsRead(insight.id)"
                >
                  ✓ 标已读
                </NButton>
                <NButton
                  v-if="isRead(insight)"
                  text
                  size="tiny"
                  @click="markAsUnread(insight.id)"
                >
                  标未读
                </NButton>
                <NButton
                  text
                  size="tiny"
                  type="warning"
                  @click="ignoreInsight(insight.id)"
                >
                  忽略
                </NButton>
                <NButton
                  text
                  size="tiny"
                  @click="dismissInsight(insight.id)"
                >
                  ✕
                </NButton>
              </NSpace>
            </div>

            <!-- Title -->
            <div class="insight-title">{{ insight.title }}</div>

            <!-- Content -->
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
      </div>
    </NSpin>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.insight-manager {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.manager-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding-bottom: 12px;
  border-bottom: 1px solid $border-light;
  margin-bottom: 12px;

  .header-info {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
  }

  .manager-title {
    font-size: 16px;
    font-weight: 600;
    color: $text-primary;
    margin: 0;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .header-subtitle {
    font-size: 12px;
    color: $text-muted;
  }
}

.manager-empty {
  padding: 40px 0;
}

// Insight list
.insight-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 600px;
  overflow-y: auto;
}

// Insight item
.insight-item {
  display: flex;
  gap: 8px;
  padding: 12px;
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

.unread-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #4a90d9;
  flex-shrink: 0;
  margin-top: 6px;
}

.insight-main {
  flex: 1;
  min-width: 0;
}

.insight-item-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
  gap: 8px;
}

.insight-meta {
  display: flex;
  align-items: center;
  gap: 8px;
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
</style>
