<script setup lang="ts">
import { ref } from 'vue'
import { NTag, NButton, NEmpty, NInput, useMessage } from 'naive-ui'
import { useI18n } from 'vue-i18n'
import { useKanbanStore } from '@/stores/hermes/kanban'
import type { KanbanTaskDetail } from '@/api/hermes/kanban'

const props = defineProps<{ task: KanbanTaskDetail | null }>()
defineEmits<{ close: [] }>()

const { t } = useI18n()
const message = useMessage()
const kanbanStore = useKanbanStore()

const showComment = ref(false)
const commentText = ref('')
const commentLoading = ref(false)

const statusColors: Record<string, 'default' | 'info' | 'success' | 'warning' | 'error'> = {
  todo: 'default', ready: 'info', running: 'warning', blocked: 'error', done: 'success', failed: 'error',
}

function formatTime(iso?: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString()
}

async function handleComplete() {
  if (!props.task) return
  try {
    await kanbanStore.completeTask(props.task.id)
    message.success(t('kanban.complete'))
  } catch (e: any) {
    message.error(e.message)
  }
}

async function handleBlock() {
  if (!props.task) return
  try {
    await kanbanStore.blockTask(props.task.id, 'Blocked via WebUI')
    message.success(t('kanban.block'))
  } catch (e: any) {
    message.error(e.message)
  }
}

async function handleUnblock() {
  if (!props.task) return
  try {
    await kanbanStore.unblockTasks([props.task.id])
    message.success('Unblocked')
  } catch (e: any) {
    message.error(e.message)
  }
}

async function handleArchive() {
  if (!props.task) return
  try {
    await kanbanStore.archiveTasks([props.task.id])
    message.success('Archived')
  } catch (e: any) {
    message.error(e.message)
  }
}

function openComment() {
  showComment.value = true
  commentText.value = ''
}

async function submitComment() {
  if (!props.task || !commentText.value.trim()) return
  commentLoading.value = true
  try {
    await kanbanStore.commentTask(props.task.id, commentText.value.trim())
    commentText.value = ''
    showComment.value = false
  } catch (e: any) {
    message.error(e.message)
  } finally {
    commentLoading.value = false
  }
}

async function handleDispatch() {
  try {
    const result = await kanbanStore.dispatchKanban()
    message.success(`Dispatched: ${JSON.stringify(result)}`)
  } catch (e: any) {
    message.error(e.message)
  }
}
</script>

<template>
  <div class="task-detail">
    <template v-if="task">
      <div class="detail-header">
        <h3 class="detail-title">{{ task.title }}</h3>
        <NButton size="tiny" quaternary @click="$emit('close')">&#x2715;</NButton>
      </div>

      <div class="detail-meta">
        <NTag size="small" :type="statusColors[task.status] || 'default'" round>{{ task.status }}</NTag>
        <span v-if="task.assignee" class="detail-assignee">{{ t('kanban.assignee') }}: @{{ task.assignee }}</span>
        <span class="detail-priority">P{{ task.priority }}</span>
      </div>

      <!-- Action buttons -->
      <div class="detail-actions">
        <NButton v-if="task.status === 'ready' || task.status === 'todo'" size="tiny" type="primary" @click="handleDispatch">{{ t('kanban.dispatch') }}</NButton>
        <NButton v-if="task.status !== 'done' && task.status !== 'blocked'" size="tiny" @click="handleBlock">{{ t('kanban.block') }}</NButton>
        <NButton v-if="task.status === 'blocked'" size="tiny" @click="handleUnblock">{{ t('kanban.unblock') }}</NButton>
        <NButton v-if="task.status !== 'done'" size="tiny" @click="handleComplete">{{ t('kanban.complete') }}</NButton>
        <NButton size="tiny" @click="openComment">{{ t('kanban.comment') }}</NButton>
        <NButton v-if="task.status === 'done' || task.status === 'blocked'" size="tiny" type="error" @click="handleArchive">{{ t('kanban.archive') }}</NButton>
      </div>

      <div v-if="task.body" class="detail-body">
        <p>{{ task.body }}</p>
      </div>

      <div class="detail-times">
        <span>{{ t('kanban.created') }}: {{ formatTime(task.created_at) }}</span>
        <span v-if="task.started_at">{{ t('kanban.started') }}: {{ formatTime(task.started_at) }}</span>
        <span v-if="task.completed_at">{{ t('kanban.completed') }}: {{ formatTime(task.completed_at) }}</span>
      </div>

      <div v-if="task.result" class="detail-result">
        <div class="section-label">{{ t('kanban.result') }}</div>
        <p>{{ task.result }}</p>
      </div>

      <!-- Comment input -->
      <div v-if="showComment" class="comment-input">
        <NInput v-model:value="commentText" type="textarea" :rows="2" :placeholder="t('kanban.commentPlaceholder')" />
        <div class="comment-actions">
          <NButton size="tiny" :loading="commentLoading" @click="submitComment">{{ t('kanban.submit') }}</NButton>
          <NButton size="tiny" @click="showComment = false">{{ t('common.cancel') }}</NButton>
        </div>
      </div>

      <div v-if="task.runs.length > 0" class="detail-section">
        <div class="section-label">{{ t('kanban.runs') }} ({{ task.runs.length }})</div>
        <div v-for="run in task.runs" :key="run.id" class="run-item">
          <NTag size="tiny" :type="run.status === 'completed' ? 'success' : run.status === 'failed' ? 'error' : 'warning'" round>
            {{ run.status }}
          </NTag>
          <span class="run-profile">{{ run.profile || '—' }}</span>
          <span class="run-time">{{ formatTime(run.started_at) }}</span>
          <div v-if="run.summary" class="run-summary">{{ run.summary }}</div>
          <div v-if="run.error" class="run-error">{{ run.error }}</div>
        </div>
      </div>

      <div v-if="task.comments.length > 0" class="detail-section">
        <div class="section-label">{{ t('kanban.comments') }} ({{ task.comments.length }})</div>
        <div v-for="comment in task.comments" :key="comment.id" class="comment-item">
          <span class="comment-author">{{ comment.author || 'agent' }}</span>
          <span class="comment-time">{{ formatTime(comment.created_at) }}</span>
          <p class="comment-body">{{ comment.body }}</p>
        </div>
      </div>

      <div v-if="task.child_ids.length > 0 || task.parent_ids.length > 0" class="detail-section">
        <div class="section-label">{{ t('kanban.dependencies') }}</div>
        <div v-if="task.parent_ids.length" class="dep-row">
          {{ t('kanban.parents') }}: {{ task.parent_ids.join(', ') }}
        </div>
        <div v-if="task.child_ids.length" class="dep-row">
          {{ t('kanban.children') }}: {{ task.child_ids.join(', ') }}
        </div>
      </div>
    </template>
    <NEmpty v-else :description="t('kanban.selectTask')" />
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.task-detail {
  padding: 16px;
  height: 100%;
  overflow-y: auto;
}

.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.detail-title {
  font-size: 16px;
  font-weight: 600;
  color: $text-primary;
  margin: 0;
}

.detail-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.detail-assignee {
  font-size: 12px;
  color: $text-secondary;
}

.detail-priority {
  font-size: 12px;
  color: $text-muted;
  background: $bg-secondary;
  padding: 1px 6px;
  border-radius: 4px;
}

.detail-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-bottom: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid $border-light;
}

.detail-body {
  font-size: 13px;
  color: $text-secondary;
  margin-bottom: 12px;
  padding: 10px;
  background: var(--n-color-modal, #fafafa);
  border-radius: 6px;
}

.detail-times {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 11px;
  color: $text-muted;
  margin-bottom: 16px;
}

.section-label {
  font-size: 12px;
  font-weight: 600;
  color: $text-muted;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 8px;
}

.detail-result {
  margin-bottom: 16px;
  padding: 10px;
  background: var(--n-color-modal, #fafafa);
  border-radius: 6px;
  font-size: 13px;
  color: $text-secondary;
}

.comment-input {
  margin-bottom: 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.comment-actions {
  display: flex;
  gap: 4px;
}

.detail-section {
  margin-bottom: 16px;
  padding-top: 12px;
  border-top: 1px solid $border-light;
}

.run-item {
  padding: 8px 0;
  border-bottom: 1px solid $border-light;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  font-size: 12px;
}

.run-profile { color: $text-secondary; }
.run-time { color: $text-muted; margin-left: auto; }
.run-summary, .run-error {
  width: 100%;
  font-size: 12px;
  margin-top: 4px;
}
.run-error { color: #d03050; }
.run-summary { color: $text-secondary; }

.comment-item {
  padding: 8px 0;
  border-bottom: 1px solid $border-light;
  font-size: 13px;
}

.comment-author {
  font-weight: 600;
  color: $text-primary;
}

.comment-time {
  font-size: 11px;
  color: $text-muted;
  margin-left: 8px;
}

.comment-body {
  color: $text-secondary;
  margin-top: 4px;
}

.dep-row {
  font-size: 12px;
  color: $text-muted;
  margin-bottom: 4px;
}
</style>
