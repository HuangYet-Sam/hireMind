<script setup lang="ts">
import { ref, computed } from 'vue'
import {
  NCard, NTag, NButton, NSpin, NEmpty, NTooltip, NAvatar,
} from 'naive-ui'
import type { Interview } from '@/api/hr/interviews'
import { INTERVIEW_STATUS_LABELS, INTERVIEW_TYPE_LABELS } from '@/api/hr/interviews'

type TagType = 'default' | 'info' | 'success' | 'warning' | 'error'

interface BoardColumn {
  key: string
  label: string
  color: string
  filter: (i: Interview) => boolean
}

const props = withDefaults(defineProps<{
  interviews: Interview[]
  loading?: boolean
}>(), {
  loading: false,
})

const emit = defineEmits<{
  'change-status': [interview: Interview, newStatus: string]
  'view-detail': [id: string]
}>()

const columns: BoardColumn[] = [
  {
    key: 'pending',
    label: '待确认',
    color: '#999',
    filter: (i) => i.status === 'pending',
  },
  {
    key: 'scheduled',
    label: '已排期',
    color: '#f0a020',
    filter: (i) => i.status === 'scheduled' || i.status === 'confirmed',
  },
  {
    key: 'in_progress',
    label: '进行中',
    color: '#18a058',
    filter: (i) => i.status === 'in_progress',
  },
  {
    key: 'pending_feedback',
    label: '待反馈',
    color: '#4a90d9',
    filter: (i) => i.status === 'completed' && i.overall_score === null,
  },
  {
    key: 'completed',
    label: '已评价',
    color: '#8a2be2',
    filter: (i) => i.status === 'completed' && i.overall_score !== null,
  },
]

const typeTagType: Record<string, TagType> = {
  phone_screen: 'default',
  technical: 'info',
  behavioral: 'warning',
  hr: 'success',
  final: 'error',
  panel: 'default',
  case_study: 'warning',
}

const groupedInterviews = computed(() => {
  const groups: Record<string, Interview[]> = {}
  for (const col of columns) {
    groups[col.key] = props.interviews.filter(col.filter)
  }
  return groups
})

// Status mapping for drop targets
const columnStatusMap: Record<string, string> = {
  pending: 'pending',
  scheduled: 'scheduled',
  in_progress: 'in_progress',
  pending_feedback: 'completed',
  completed: 'completed',
}

// Drag state
const dragInterview = ref<Interview | null>(null)
const dragSourceColumn = ref<string | null>(null)
const dropTargetColumn = ref<string | null>(null)

function onDragStart(interview: Interview, columnKey: string, event: DragEvent) {
  dragInterview.value = interview
  dragSourceColumn.value = columnKey
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move'
    event.dataTransfer.setData('text/plain', interview.id)
  }
}

function onDragOver(event: DragEvent) {
  event.preventDefault()
  if (event.dataTransfer) {
    event.dataTransfer.dropEffect = 'move'
  }
}

function onDragEnter(columnKey: string) {
  dropTargetColumn.value = columnKey
}

function onDragLeave() {
  dropTargetColumn.value = null
}

function onDrop(targetColumnKey: string) {
  dropTargetColumn.value = null
  if (!dragInterview.value) return
  if (targetColumnKey === dragSourceColumn.value) {
    dragInterview.value = null
    dragSourceColumn.value = null
    return
  }

  const newStatus = columnStatusMap[targetColumnKey]
  if (newStatus) {
    emit('change-status', dragInterview.value, newStatus)
  }

  dragInterview.value = null
  dragSourceColumn.value = null
}

function onDragEnd() {
  dragInterview.value = null
  dragSourceColumn.value = null
  dropTargetColumn.value = null
}

function formatTime(dateStr: string | null): string {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function getScoreColor(score: number): string {
  if (score >= 8) return '#18a058'
  if (score >= 6) return '#f0a020'
  return '#d03050'
}
</script>

<template>
  <NSpin :show="loading">
    <div class="interview-board">
      <div
        v-for="column in columns"
        :key="column.key"
        class="board-column"
        :class="{ 'drop-target': dropTargetColumn === column.key }"
        @dragover="onDragOver"
        @dragenter="onDragEnter(column.key)"
        @dragleave="onDragLeave"
        @drop="onDrop(column.key)"
      >
        <!-- Column Header -->
        <div
          class="board-column-header"
          :style="{ borderTopColor: column.color }"
        >
          <div class="header-left">
            <span class="column-title" :style="{ color: column.color }">
              {{ column.label }}
            </span>
            <span class="column-count">
              {{ groupedInterviews[column.key]?.length ?? 0 }}
            </span>
          </div>
        </div>

        <!-- Column Body -->
        <div class="board-column-body">
          <div
            v-for="interview in groupedInterviews[column.key]"
            :key="interview.id"
            class="board-card-wrapper"
            draggable="true"
            @dragstart="onDragStart(interview, column.key, $event)"
            @dragend="onDragEnd"
          >
            <NCard
              size="small"
              class="board-card"
              hoverable
              @click="emit('view-detail', interview.id)"
            >
              <!-- Card Header -->
              <div class="card-header">
                <span class="card-candidate">{{ interview.candidate_id }}</span>
                <NTag
                  size="tiny"
                  :type="typeTagType[interview.interview_type] ?? 'default'"
                  :bordered="false"
                >
                  {{ INTERVIEW_TYPE_LABELS[interview.interview_type] || interview.interview_type }}
                </NTag>
              </div>

              <!-- Position -->
              <div class="card-position">
                {{ interview.position_id ?? '未关联岗位' }}
              </div>

              <!-- Time -->
              <div class="card-time">
                {{ formatTime(interview.scheduled_at) }}
              </div>

              <!-- Interviewer Avatars -->
              <div v-if="interview.interviewer_ids?.length" class="card-interviewers">
                <NTooltip v-for="iid in interview.interviewer_ids.slice(0, 3)" :key="iid">
                  <template #trigger>
                    <NAvatar :size="22" round class="interviewer-avatar">
                      {{ iid.slice(0, 1).toUpperCase() }}
                    </NAvatar>
                  </template>
                  {{ iid }}
                </NTooltip>
                <span v-if="interview.interviewer_ids.length > 3" class="more-interviewers">
                  +{{ interview.interviewer_ids.length - 3 }}
                </span>
              </div>

              <!-- Score -->
              <div v-if="interview.overall_score !== null" class="card-score">
                <span class="score-value" :style="{ color: getScoreColor(interview.overall_score) }">
                  {{ interview.overall_score }}
                </span>
                <span class="score-max">/10</span>
              </div>

              <!-- Footer -->
              <div class="card-footer">
                <NTag size="tiny" :bordered="false">
                  第{{ interview.round_number }}轮
                </NTag>
                <span class="card-duration">{{ interview.duration_minutes }}分钟</span>
              </div>
            </NCard>
          </div>

          <NEmpty
            v-if="!groupedInterviews[column.key]?.length"
            description="暂无"
            size="small"
          />
        </div>
      </div>
    </div>
  </NSpin>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.interview-board {
  display: flex;
  gap: 12px;
  overflow-x: auto;
  padding-bottom: 8px;
  min-height: 300px;
}

.board-column {
  flex: 1;
  min-width: 240px;
  max-width: 320px;
  background: $bg-secondary;
  border-radius: $radius-md;
  display: flex;
  flex-direction: column;
  transition: all $transition-normal;

  &.drop-target {
    background: rgba(var(--accent-info-rgb), 0.08);
    box-shadow: inset 0 0 0 2px var(--accent-info);
  }
}

.board-column-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-top: 3px solid;
  border-radius: $radius-md $radius-md 0 0;

  .header-left {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .column-title {
    font-weight: 600;
    font-size: 13px;
  }

  .column-count {
    font-size: 12px;
    color: $text-muted;
    background: $bg-card;
    border-radius: 10px;
    padding: 1px 8px;
    min-width: 20px;
    text-align: center;
  }
}

.board-column-body {
  padding: 8px;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 60px;
}

.board-card-wrapper {
  cursor: grab;

  &:active {
    cursor: grabbing;
  }
}

.board-card {
  transition: box-shadow $transition-fast, transform $transition-fast;

  &:hover {
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  }

  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 4px;

    .card-candidate {
      font-weight: 600;
      font-size: 13px;
      color: $text-primary;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      flex: 1;
      min-width: 0;
      margin-right: 6px;
    }
  }

  .card-position {
    font-size: 12px;
    color: $text-secondary;
    margin-bottom: 2px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .card-time {
    font-size: 12px;
    color: $text-muted;
    margin-bottom: 6px;
  }

  .card-interviewers {
    display: flex;
    align-items: center;
    gap: 4px;
    margin-bottom: 6px;

    .interviewer-avatar {
      font-size: 10px;
      background: $bg-card;
      color: $text-secondary;
      border: 1px solid $border-light;
    }

    .more-interviewers {
      font-size: 11px;
      color: $text-muted;
    }
  }

  .card-score {
    margin-bottom: 6px;

    .score-value {
      font-size: 16px;
      font-weight: 700;
    }

    .score-max {
      font-size: 12px;
      color: $text-muted;
    }
  }

  .card-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-top: 6px;
    border-top: 1px solid $border-light;

    .card-duration {
      font-size: 11px;
      color: $text-muted;
    }
  }
}
</style>
