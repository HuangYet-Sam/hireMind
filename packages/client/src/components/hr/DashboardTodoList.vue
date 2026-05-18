<script setup lang="ts">
/**
 * DashboardTodoList — M7 待办清单组件
 *
 * Props: todos (TodoItem[]), loading
 * 分区展示：🔴紧急 / ⚠️高优先 / 📋普通
 * Emits: item-click, refresh
 */
import { computed } from 'vue'
import { NTag, NButton, NSpin, NEmpty, NSpace, NIcon } from 'naive-ui'
import type { TodoItem } from '@/api/hr/dashboard'

const props = defineProps<{
  todos: TodoItem[]
  loading?: boolean
}>()

const emit = defineEmits<{
  'item-click': [todo: TodoItem]
  refresh: []
}>()

// ── Priority grouping ────────────────────────────────────────

const urgentTodos = computed(() =>
  props.todos.filter(t => t.priority === 'urgent'),
)

const highTodos = computed(() =>
  props.todos.filter(t => t.priority === 'high'),
)

const normalTodos = computed(() =>
  props.todos.filter(t => t.priority === 'medium' || t.priority === 'low'),
)

// ── Statistics ───────────────────────────────────────────────

const totalCount = computed(() => props.todos.length)

const urgentCount = computed(() => urgentTodos.value.length)

const todayDueCount = computed(() => {
  const today = new Date().toISOString().split('T')[0]
  return props.todos.filter(t => {
    if (!t.due_date) return false
    return t.due_date.startsWith(today) && t.status !== 'completed'
  }).length
})

// ── Priority helpers ─────────────────────────────────────────

const priorityColorMap: Record<string, 'default' | 'info' | 'warning' | 'error'> = {
  low: 'default',
  medium: 'info',
  high: 'warning',
  urgent: 'error',
}

const priorityLabelMap: Record<string, string> = {
  low: '低',
  medium: '中',
  high: '高',
  urgent: '紧急',
}

/** 类型图标映射 */
const typeIconMap: Record<string, string> = {
  interview: '🎯',
  offer: '📝',
  candidate: '👤',
  position: '📋',
  match: '🔗',
  report: '📊',
}

function getTypeIcon(todo: TodoItem): string {
  return typeIconMap[todo.related_type ?? ''] ?? '📌'
}

function isOverdue(todo: TodoItem): boolean {
  if (!todo.due_date || todo.status === 'completed') return false
  return new Date(todo.due_date) < new Date()
}

function isDueToday(todo: TodoItem): boolean {
  if (!todo.due_date) return false
  const today = new Date().toISOString().split('T')[0]
  return todo.due_date.startsWith(today)
}

function formatDueDate(dateStr?: string): string {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  const now = new Date()
  const diffMs = d.getTime() - now.getTime()
  const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24))

  if (diffDays < 0) return `已过期 ${Math.abs(diffDays)} 天`
  if (diffDays === 0) return '今日到期'
  if (diffDays === 1) return '明日到期'
  if (diffDays <= 7) return `${diffDays} 天后到期`
  return d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

function handleClick(todo: TodoItem) {
  emit('item-click', todo)
}
</script>

<template>
  <div class="dashboard-todo-list">
    <!-- Statistics bar -->
    <div class="todo-stats-bar">
      <div class="stat-item">
        <span class="stat-value">{{ totalCount }}</span>
        <span class="stat-label">总待办</span>
      </div>
      <div class="stat-item stat-urgent">
        <span class="stat-value">{{ urgentCount }}</span>
        <span class="stat-label">紧急</span>
      </div>
      <div class="stat-item stat-today">
        <span class="stat-value">{{ todayDueCount }}</span>
        <span class="stat-label">今日到期</span>
      </div>
      <NButton text size="small" class="refresh-btn" @click="emit('refresh')">
        🔄 刷新
      </NButton>
    </div>

    <NSpin :show="loading">
      <div v-if="!todos.length" class="todo-empty">
        <NEmpty description="暂无待办事项" size="small" />
      </div>

      <div v-else class="todo-sections">
        <!-- 🔴 Urgent Section -->
        <div v-if="urgentTodos.length" class="todo-section">
          <div class="section-header section-urgent">
            <span class="section-icon">🔴</span>
            <span class="section-title">紧急</span>
            <NTag size="tiny" type="error" round>{{ urgentTodos.length }}</NTag>
          </div>
          <div class="section-items">
            <div
              v-for="todo in urgentTodos"
              :key="todo.id"
              class="todo-item"
              :class="{
                'todo-overdue': isOverdue(todo),
                'todo-due-today': isDueToday(todo),
              }"
              @click="handleClick(todo)"
            >
              <div class="todo-left">
                <span class="todo-type-icon">{{ getTypeIcon(todo) }}</span>
                <div class="todo-info">
                  <div class="todo-title">{{ todo.title }}</div>
                  <div v-if="todo.description" class="todo-desc">{{ todo.description }}</div>
                </div>
              </div>
              <div class="todo-right">
                <div v-if="todo.due_date" class="todo-due" :class="{ 'due-overdue': isOverdue(todo) }">
                  {{ formatDueDate(todo.due_date) }}
                </div>
                <div class="todo-actions">
                  <NTag size="tiny" :type="priorityColorMap[todo.priority]">
                    {{ priorityLabelMap[todo.priority] }}
                  </NTag>
                  <NButton text size="tiny" type="primary" @click.stop="handleClick(todo)">
                    查看
                  </NButton>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- ⚠️ High Priority Section -->
        <div v-if="highTodos.length" class="todo-section">
          <div class="section-header section-high">
            <span class="section-icon">⚠️</span>
            <span class="section-title">高优先</span>
            <NTag size="tiny" type="warning" round>{{ highTodos.length }}</NTag>
          </div>
          <div class="section-items">
            <div
              v-for="todo in highTodos"
              :key="todo.id"
              class="todo-item"
              :class="{
                'todo-overdue': isOverdue(todo),
                'todo-due-today': isDueToday(todo),
              }"
              @click="handleClick(todo)"
            >
              <div class="todo-left">
                <span class="todo-type-icon">{{ getTypeIcon(todo) }}</span>
                <div class="todo-info">
                  <div class="todo-title">{{ todo.title }}</div>
                  <div v-if="todo.description" class="todo-desc">{{ todo.description }}</div>
                </div>
              </div>
              <div class="todo-right">
                <div v-if="todo.due_date" class="todo-due" :class="{ 'due-overdue': isOverdue(todo) }">
                  {{ formatDueDate(todo.due_date) }}
                </div>
                <div class="todo-actions">
                  <NTag size="tiny" :type="priorityColorMap[todo.priority]">
                    {{ priorityLabelMap[todo.priority] }}
                  </NTag>
                  <NButton text size="tiny" type="primary" @click.stop="handleClick(todo)">
                    处理
                  </NButton>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 📋 Normal Section -->
        <div v-if="normalTodos.length" class="todo-section">
          <div class="section-header section-normal">
            <span class="section-icon">📋</span>
            <span class="section-title">普通</span>
            <NTag size="tiny" round>{{ normalTodos.length }}</NTag>
          </div>
          <div class="section-items">
            <div
              v-for="todo in normalTodos"
              :key="todo.id"
              class="todo-item"
              :class="{
                'todo-overdue': isOverdue(todo),
                'todo-due-today': isDueToday(todo),
              }"
              @click="handleClick(todo)"
            >
              <div class="todo-left">
                <span class="todo-type-icon">{{ getTypeIcon(todo) }}</span>
                <div class="todo-info">
                  <div class="todo-title">{{ todo.title }}</div>
                  <div v-if="todo.description" class="todo-desc">{{ todo.description }}</div>
                </div>
              </div>
              <div class="todo-right">
                <div v-if="todo.due_date" class="todo-due" :class="{ 'due-overdue': isOverdue(todo) }">
                  {{ formatDueDate(todo.due_date) }}
                </div>
                <div class="todo-actions">
                  <NTag size="tiny" :type="priorityColorMap[todo.priority]">
                    {{ priorityLabelMap[todo.priority] }}
                  </NTag>
                  <NButton text size="tiny" type="primary" @click.stop="handleClick(todo)">
                    处理
                  </NButton>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </NSpin>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.dashboard-todo-list {
  display: flex;
  flex-direction: column;
  height: 100%;
}

// Statistics bar
.todo-stats-bar {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 10px 0;
  border-bottom: 1px solid $border-light;
  margin-bottom: 12px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 4px;

  .stat-value {
    font-size: 18px;
    font-weight: 700;
    color: $text-primary;
  }

  .stat-label {
    font-size: 12px;
    color: $text-muted;
  }

  &.stat-urgent .stat-value {
    color: var(--error);
  }

  &.stat-today .stat-value {
    color: var(--warning);
  }
}

.refresh-btn {
  margin-left: auto;
  font-size: 12px;
  color: $text-muted;
  cursor: pointer;

  &:hover {
    color: $text-primary;
  }
}

.todo-empty {
  padding: 32px 0;
}

// Sections
.todo-sections {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-height: 480px;
  overflow-y: auto;
}

.todo-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 0;
  font-size: 13px;
  font-weight: 600;

  .section-icon {
    font-size: 14px;
  }

  .section-title {
    color: $text-primary;
  }

  &.section-urgent .section-title { color: var(--error); }
  &.section-high .section-title { color: var(--warning); }
  &.section-normal .section-title { color: $text-secondary; }
}

// Todo items
.todo-item {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 10px 12px;
  border-radius: $radius-sm;
  border: 1px solid $border-light;
  cursor: pointer;
  transition: background $transition-fast, border-color $transition-fast;
  gap: 12px;

  &:hover {
    background: $bg-card-hover;
    border-color: $border-color;
  }

  &.todo-overdue {
    border-color: var(--error);
    background: rgba(var(--error-rgb), 0.04);
  }

  &.todo-due-today {
    border-color: var(--warning);
    background: rgba(var(--warning-rgb), 0.04);
  }
}

.todo-left {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  flex: 1;
  min-width: 0;
}

.todo-type-icon {
  font-size: 16px;
  flex-shrink: 0;
  margin-top: 2px;
}

.todo-info {
  flex: 1;
  min-width: 0;
}

.todo-title {
  font-size: 14px;
  font-weight: 500;
  color: $text-primary;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.todo-desc {
  font-size: 12px;
  color: $text-muted;
  line-height: 1.4;
  margin-top: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.todo-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
  flex-shrink: 0;
}

.todo-due {
  font-size: 11px;
  color: $text-muted;
  white-space: nowrap;

  &.due-overdue {
    color: var(--error);
    font-weight: 500;
  }
}

.todo-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}
</style>
