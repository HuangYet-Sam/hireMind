<script setup lang="ts">
/**
 * ProactiveAICenterView — M10 主动AI推送中心
 *
 * 推送消息列表 + 分类Tab + 已读/未读 + 操作按钮 + 统计
 */
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  NCard, NGrid, NGridItem, NTag, NButton, NInput, NSpace, NEmpty,
  NSpin, NTabs, NTabPane, NRadioButton, NRadioGroup, NPopconfirm,
  useMessage,
} from 'naive-ui'
import {
  fetchProactiveMessages, triggerProactiveScan, handleMessage,
  batchMarkRead, fetchProactiveStats,
} from '@/api/hr/proactive'
import type {
  ProactiveMessage, ProactiveCategory, ProactiveStatus,
  ProactiveMessageFilters, ProactiveStats,
} from '@/api/hr/proactive'

const router = useRouter()
const message = useMessage()

// ── Category Config ─────────────────────────────────────────

type TabKey = 'all' | ProactiveCategory

interface CategoryConfig {
  label: string
  icon: string
  color: string
}

const CATEGORY_CONFIG: Record<string, CategoryConfig> = {
  all: { label: '全部', icon: '📋', color: '#4a90d9' },
  resume_arrival: { label: '简历到达', icon: '📄', color: '#18a058' },
  match_anomaly: { label: '匹配异常', icon: '⚠️', color: '#f0a020' },
  interview_timeout: { label: '面试超时', icon: '⏰', color: '#d03050' },
  offer_deadlock: { label: 'Offer僵局', icon: '🔒', color: '#8b5cf6' },
  funnel_bottleneck: { label: '漏斗瓶颈', icon: '🔻', color: '#06b6d4' },
  silent_activation: { label: '沉默激活', icon: '💤', color: '#f97316' },
}

const STATUS_LABEL: Record<ProactiveStatus, string> = {
  pending: '待处理',
  confirmed: '已确认',
  ignored: '已忽略',
  executed: '已执行',
}

const STATUS_TYPE: Record<ProactiveStatus, 'default' | 'info' | 'success' | 'warning'> = {
  pending: 'warning',
  confirmed: 'info',
  ignored: 'default',
  executed: 'success',
}

// ── State ───────────────────────────────────────────────────

const loading = ref(false)
const messages_list = ref<ProactiveMessage[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const stats = ref<ProactiveStats | null>(null)

const activeTab = ref<TabKey>('all')
const readFilter = ref<'all' | 'unread' | 'read'>('all')
const searchKeyword = ref('')

// ── Computed ────────────────────────────────────────────────

const statCards = computed(() => {
  const s = stats.value
  return [
    { label: '今日推送', value: s?.today_total ?? '-', icon: '📬', color: '#4a90d9' },
    { label: '待处理', value: s?.pending_count ?? '-', icon: '⏳', color: '#f0a020' },
    { label: '已处理', value: ((s?.confirmed_count ?? 0) + (s?.executed_count ?? 0)) || '-', icon: '✅', color: '#18a058' },
  ]
})

const filteredMessages = computed(() => {
  let list = messages_list.value
  if (searchKeyword.value) {
    const kw = searchKeyword.value.toLowerCase()
    list = list.filter(m => m.title.toLowerCase().includes(kw) || m.content.toLowerCase().includes(kw))
  }
  return list
})

// ── Data Loading ────────────────────────────────────────────

onMounted(async () => {
  await Promise.allSettled([loadStats(), loadMessages()])
})

async function loadStats() {
  try {
    stats.value = await fetchProactiveStats()
  } catch {
    message.error('加载推送统计失败')
  }
}

async function loadMessages() {
  loading.value = true
  try {
    const filters: ProactiveMessageFilters = {
      page: page.value,
      page_size: pageSize.value,
    }
    if (activeTab.value !== 'all') filters.category = activeTab.value as ProactiveCategory
    if (readFilter.value === 'unread') filters.is_read = false
    if (readFilter.value === 'read') filters.is_read = true

    const res = await fetchProactiveMessages(filters)
    messages_list.value = res.items
    total.value = res.total
  } catch {
    message.error('加载推送消息失败')
  } finally {
    loading.value = false
  }
}

// ── Handlers ────────────────────────────────────────────────

function handleTabChange(tab: string) {
  activeTab.value = tab as TabKey
  page.value = 1
  loadMessages()
}

function handleReadFilterChange(val: 'all' | 'unread' | 'read') {
  readFilter.value = val
  page.value = 1
  loadMessages()
}

async function handleConfirm(msg: ProactiveMessage) {
  try {
    await handleMessage(msg.id, 'confirm')
    message.success('已确认')
    loadMessages()
    loadStats()
  } catch {
    message.error('操作失败')
  }
}

async function handleIgnore(msg: ProactiveMessage) {
  try {
    await handleMessage(msg.id, 'ignore')
    message.success('已忽略')
    loadMessages()
    loadStats()
  } catch {
    message.error('操作失败')
  }
}

async function handleExecute(msg: ProactiveMessage) {
  try {
    await handleMessage(msg.id, 'execute')
    message.success('已执行')
    if (msg.action_link) {
      router.push(msg.action_link)
    }
    loadMessages()
    loadStats()
  } catch {
    message.error('执行失败')
  }
}

async function handleMarkAllRead() {
  try {
    await batchMarkRead()
    message.success('全部标已读')
    loadMessages()
    loadStats()
  } catch {
    message.error('操作失败')
  }
}

async function handleScan() {
  try {
    const res = await triggerProactiveScan()
    message.success(res.message || '主动扫描已触发')
    loadMessages()
    loadStats()
  } catch {
    message.error('触发扫描失败')
  }
}

function formatTime(dateStr: string) {
  const d = new Date(dateStr)
  const now = new Date()
  const diff = now.getTime() - d.getTime()
  const minutes = Math.floor(diff / 60000)
  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes}分钟前`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}小时前`
  return d.toLocaleDateString('zh-CN')
}

function getCategoryConfig(cat: string): CategoryConfig {
  return CATEGORY_CONFIG[cat] || { label: cat, icon: '📌', color: '#6b7280' }
}
</script>

<template>
  <div class="proactive-center-view">
    <header class="page-header">
      <div class="header-row">
        <div>
          <h2 class="header-title">主动 AI 推送</h2>
          <p class="header-desc">AI 主动发现的问题与推荐操作</p>
        </div>
        <NSpace>
          <NButton @click="handleMarkAllRead" :disabled="loading">✅ 全部已读</NButton>
          <NButton type="primary" @click="handleScan" :disabled="loading">🔍 立即扫描</NButton>
        </NSpace>
      </div>
    </header>

    <!-- ═══ Statistics Cards ═══ -->
    <NGrid :cols="3" :x-gap="12" :y-gap="12" responsive="screen" item-responsive>
      <NGridItem v-for="card in statCards" :key="card.label" span="0:3 640:1">
        <NCard size="small" class="stat-card">
          <div class="stat-inner">
            <div class="stat-icon" :style="{ background: `${card.color}15`, color: card.color }">
              {{ card.icon }}
            </div>
            <div class="stat-info">
              <div class="stat-label">{{ card.label }}</div>
              <div class="stat-value">{{ card.value }}</div>
            </div>
          </div>
        </NCard>
      </NGridItem>
    </NGrid>

    <!-- ═══ Tab + Filter Bar ═══ -->
    <div class="filter-bar">
      <NTabs type="segment" :value="activeTab" @update:value="handleTabChange" style="flex: 1;">
        <NTabPane v-for="(cfg, key) in CATEGORY_CONFIG" :key="key" :name="key" :tab="`${cfg.icon} ${cfg.label}`" />
      </NTabs>
      <NRadioGroup v-model:value="readFilter" size="small" @update:value="handleReadFilterChange" style="margin-left: 12px;">
        <NRadioButton value="all">全部</NRadioButton>
        <NRadioButton value="unread">未读</NRadioButton>
        <NRadioButton value="read">已读</NRadioButton>
      </NRadioGroup>
    </div>

    <NInput
      v-model:value="searchKeyword"
      placeholder="搜索推送消息..."
      clearable
      style="margin-bottom: 16px;"
    />

    <!-- ═══ Message List ═══ -->
    <NSpin :show="loading">
      <div v-if="filteredMessages.length" class="message-list">
        <NCard
          v-for="msg in filteredMessages"
          :key="msg.id"
          size="small"
          class="message-card"
          :class="{ unread: !msg.is_read }"
          hoverable
        >
          <div class="msg-header">
            <NSpace align="center" size="small">
              <span class="msg-icon">{{ getCategoryConfig(msg.category).icon }}</span>
              <NTag
                size="small"
                :color="{
                  color: getCategoryConfig(msg.category).color + '20',
                  textColor: getCategoryConfig(msg.category).color,
                  borderColor: getCategoryConfig(msg.category).color + '40',
                }"
              >
                {{ getCategoryConfig(msg.category).label }}
              </NTag>
              <NTag size="small" :type="STATUS_TYPE[msg.status]">{{ STATUS_LABEL[msg.status] }}</NTag>
            </NSpace>
            <span class="msg-time">{{ formatTime(msg.created_at) }}</span>
          </div>
          <div class="msg-title">{{ msg.title }}</div>
          <div class="msg-content">{{ msg.content }}</div>
          <div v-if="msg.status === 'pending'" class="msg-actions">
            <NSpace size="small">
              <NButton size="tiny" type="primary" @click="handleConfirm(msg)">确认</NButton>
              <NButton size="tiny" @click="handleIgnore(msg)">忽略</NButton>
              <NButton v-if="msg.action_link" size="tiny" type="info" @click="handleExecute(msg)">
                {{ msg.action_label || '执行' }}
              </NButton>
            </NSpace>
          </div>
        </NCard>
      </div>
      <NEmpty v-else description="暂无推送消息" size="small" />
    </NSpin>

    <!-- Load More -->
    <div v-if="total > pageSize" class="load-more">
      <NButton @click="page++; loadMessages()" :loading="loading">
        加载更多 ({{ messages_list.length }}/{{ total }})
      </NButton>
    </div>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.proactive-center-view {
  padding: 24px;
}

.page-header {
  margin-bottom: 20px;

  .header-row {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
  }

  .header-title {
    font-size: 22px;
    font-weight: 600;
    color: $text-primary;
    margin: 0 0 4px;
  }

  .header-desc {
    font-size: 14px;
    color: $text-muted;
    margin: 0;
  }
}

.stat-card {
  transition: transform $transition-fast;

  &:hover {
    transform: translateY(-1px);
  }
}

.stat-inner {
  display: flex;
  align-items: center;
  gap: 12px;
}

.stat-icon {
  font-size: 24px;
  width: 42px;
  height: 42px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: $radius-md;
  flex-shrink: 0;
}

.stat-label {
  font-size: 13px;
  color: $text-muted;
  margin-bottom: 2px;
}

.stat-value {
  font-size: 22px;
  font-weight: 700;
  color: $text-primary;
}

.filter-bar {
  display: flex;
  align-items: center;
  margin-bottom: 16px;
  gap: 12px;
  flex-wrap: wrap;
}

// Message cards
.message-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.message-card {
  transition: border-color $transition-fast;

  &.unread {
    border-left: 3px solid $accent-primary;
  }

  &:hover {
    border-color: $border-color;
  }
}

.msg-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.msg-icon {
  font-size: 16px;
}

.msg-time {
  font-size: 12px;
  color: $text-muted;
}

.msg-title {
  font-size: 15px;
  font-weight: 600;
  color: $text-primary;
  margin-bottom: 6px;
}

.msg-content {
  font-size: 13px;
  color: $text-secondary;
  line-height: 1.5;
  margin-bottom: 10px;
}

.msg-actions {
  padding-top: 8px;
  border-top: 1px solid $border-light;
}

.load-more {
  text-align: center;
  margin-top: 16px;
}
</style>
