<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import {
  NTag, NButton, NButtonGroup, NSpin, NEmpty, NPopover, NTooltip,
} from 'naive-ui'
import type { Interview, CalendarViewMode } from '@/api/hr/interviews'
import { INTERVIEW_STATUS_LABELS, INTERVIEW_TYPE_LABELS } from '@/api/hr/interviews'

type TagType = 'default' | 'info' | 'success' | 'warning' | 'error'

const props = withDefaults(defineProps<{
  interviews: Interview[]
  currentDate?: Date
  loading?: boolean
}>(), {
  loading: false,
})

const emit = defineEmits<{
  'view-detail': [id: string]
  'reschedule': [interview: Interview, newDate: string]
  'date-change': [date: Date]
  'view-mode-change': [mode: CalendarViewMode]
  'date-click': [date: string]
}>()

const calendarMode = ref<CalendarViewMode>('month')
const innerDate = ref(props.currentDate ?? new Date())

watch(() => props.currentDate, (d) => {
  if (d) innerDate.value = d
})

// Status color mapping
const statusColorMap: Record<string, string> = {
  pending: '#999',
  scheduled: '#f0a020',
  confirmed: '#4a90d9',
  in_progress: '#18a058',
  completed: '#888',
  cancelled: '#d03050',
  no_show: '#d03050',
}

const statusTagTypeMap: Record<string, TagType> = {
  pending: 'default',
  scheduled: 'warning',
  confirmed: 'info',
  in_progress: 'success',
  completed: 'default',
  cancelled: 'error',
  no_show: 'error',
}

// Calendar grid computation
const weekDays = ['一', '二', '三', '四', '五', '六', '日']

const calendarTitle = computed(() => {
  const d = innerDate.value
  return `${d.getFullYear()}年${d.getMonth() + 1}月`
})

interface CalendarDay {
  date: Date
  dateStr: string
  isCurrentMonth: boolean
  isToday: boolean
  interviews: Interview[]
}

const calendarDays = computed<CalendarDay[]>(() => {
  const year = innerDate.value.getFullYear()
  const month = innerDate.value.getMonth()
  const firstDay = new Date(year, month, 1)
  const lastDay = new Date(year, month + 1, 0)

  // Monday=0, Sunday=6
  let startDow = firstDay.getDay() - 1
  if (startDow < 0) startDow = 6

  const today = new Date()
  const todayStr = formatDateStr(today)
  const days: CalendarDay[] = []

  // Previous month padding
  for (let i = startDow - 1; i >= 0; i--) {
    const d = new Date(year, month, -i)
    days.push({
      date: d,
      dateStr: formatDateStr(d),
      isCurrentMonth: false,
      isToday: formatDateStr(d) === todayStr,
      interviews: getInterviewsForDate(d),
    })
  }

  // Current month
  for (let day = 1; day <= lastDay.getDate(); day++) {
    const d = new Date(year, month, day)
    days.push({
      date: d,
      dateStr: formatDateStr(d),
      isCurrentMonth: true,
      isToday: formatDateStr(d) === todayStr,
      interviews: getInterviewsForDate(d),
    })
  }

  // Next month padding to fill grid (6 rows × 7 cols)
  const remaining = 42 - days.length
  for (let i = 1; i <= remaining; i++) {
    const d = new Date(year, month + 1, i)
    days.push({
      date: d,
      dateStr: formatDateStr(d),
      isCurrentMonth: false,
      isToday: formatDateStr(d) === todayStr,
      interviews: getInterviewsForDate(d),
    })
  }

  return days
})

const weekDays_detail = computed(() => {
  if (calendarMode.value !== 'week') return []
  // Find the week that contains innerDate
  const d = new Date(innerDate.value)
  let dow = d.getDay() - 1
  if (dow < 0) dow = 6
  const monday = new Date(d)
  monday.setDate(d.getDate() - dow)

  const days: CalendarDay[] = []
  for (let i = 0; i < 7; i++) {
    const day = new Date(monday)
    day.setDate(monday.getDate() + i)
    const today = new Date()
    days.push({
      date: day,
      dateStr: formatDateStr(day),
      isCurrentMonth: day.getMonth() === innerDate.value.getMonth(),
      isToday: formatDateStr(day) === formatDateStr(today),
      interviews: getInterviewsForDate(day),
    })
  }
  return days
})

function formatDateStr(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function getInterviewsForDate(d: Date): Interview[] {
  const dateStr = formatDateStr(d)
  return props.interviews.filter(i => {
    if (!i.scheduled_at) return false
    return i.scheduled_at.startsWith(dateStr)
  })
}

function formatTime(dateStr: string | null): string {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

function prevMonth() {
  const d = new Date(innerDate.value)
  if (calendarMode.value === 'week') {
    d.setDate(d.getDate() - 7)
  } else {
    d.setMonth(d.getMonth() - 1)
  }
  innerDate.value = d
  emit('date-change', d)
}

function nextMonth() {
  const d = new Date(innerDate.value)
  if (calendarMode.value === 'week') {
    d.setDate(d.getDate() + 7)
  } else {
    d.setMonth(d.getMonth() + 1)
  }
  innerDate.value = d
  emit('date-change', d)
}

function goToday() {
  innerDate.value = new Date()
  emit('date-change', innerDate.value)
}

function switchMode(mode: CalendarViewMode) {
  calendarMode.value = mode
  emit('view-mode-change', mode)
}

function handleDayClick(day: CalendarDay) {
  emit('date-click', day.dateStr)
}

function handleEventClick(id: string, e: Event) {
  e.stopPropagation()
  emit('view-detail', id)
}

// Drag & Drop
function onDragStart(interview: Interview, event: DragEvent) {
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move'
    event.dataTransfer.setData('application/interview-id', interview.id)
    event.dataTransfer.setData('application/interview-date', interview.scheduled_at ?? '')
  }
}

function onDragOver(event: DragEvent) {
  event.preventDefault()
  if (event.dataTransfer) {
    event.dataTransfer.dropEffect = 'move'
  }
}

function onDropDay(day: CalendarDay, event: DragEvent) {
  event.preventDefault()
  if (!event.dataTransfer) return
  const interviewId = event.dataTransfer.getData('application/interview-id')
  if (!interviewId) return
  const interview = props.interviews.find(i => i.id === interviewId)
  if (!interview) return
  // Build new datetime: keep time, change date
  const oldDate = interview.scheduled_at ? new Date(interview.scheduled_at) : new Date()
  const hours = oldDate.getHours()
  const minutes = oldDate.getMinutes()
  const newDate = new Date(day.date)
  newDate.setHours(hours, minutes, 0, 0)
  emit('reschedule', interview, newDate.toISOString())
}

// Day view — all interviews for the selected date
const dayViewInterviews = computed<Interview[]>(() => {
  if (calendarMode.value !== 'day') return []
  const dateStr = formatDateStr(innerDate.value)
  return props.interviews
    .filter(i => i.scheduled_at && i.scheduled_at.startsWith(dateStr))
    .sort((a, b) => (a.scheduled_at ?? '').localeCompare(b.scheduled_at ?? ''))
})
</script>

<template>
  <NSpin :show="loading">
    <div class="interview-calendar">
      <!-- Calendar Header -->
      <div class="calendar-toolbar">
        <div class="toolbar-left">
          <NButtonGroup size="small">
            <NButton @click="prevMonth">&lt;</NButton>
            <NButton @click="goToday">今天</NButton>
            <NButton @click="nextMonth">&gt;</NButton>
          </NButtonGroup>
          <span class="calendar-title">{{ calendarTitle }}</span>
        </div>
        <div class="toolbar-right">
          <NButtonGroup size="small">
            <NButton
              :type="calendarMode === 'month' ? 'primary' : 'default'"
              @click="switchMode('month')"
            >
              月
            </NButton>
            <NButton
              :type="calendarMode === 'week' ? 'primary' : 'default'"
              @click="switchMode('week')"
            >
              周
            </NButton>
            <NButton
              :type="calendarMode === 'day' ? 'primary' : 'default'"
              @click="switchMode('day')"
            >
              日
            </NButton>
          </NButtonGroup>
        </div>
      </div>

      <!-- Month / Week View -->
      <template v-if="calendarMode === 'month' || calendarMode === 'week'">
        <div class="calendar-grid">
          <div class="calendar-weekdays">
            <div v-for="wd in weekDays" :key="wd" class="weekday-cell">
              {{ wd }}
            </div>
          </div>
          <div class="calendar-body">
            <div
              v-for="(day, idx) in (calendarMode === 'week' ? weekDays_detail : calendarDays)"
              :key="idx"
              class="calendar-cell"
              :class="{
                'other-month': !day.isCurrentMonth,
                'is-today': day.isToday,
              }"
              @click="handleDayClick(day)"
              @dragover="onDragOver"
              @drop="onDropDay(day, $event)"
            >
              <div class="cell-date">
                <span class="date-number">{{ day.date.getDate() }}</span>
                <span v-if="day.interviews.length" class="event-count">
                  {{ day.interviews.length }}
                </span>
              </div>
              <div class="cell-events">
                <template v-for="iv in day.interviews.slice(0, 3)" :key="iv.id">
                  <NPopover trigger="hover" placement="top" :width="260">
                    <template #trigger>
                      <div
                        class="event-bar"
                        :style="{ borderLeftColor: statusColorMap[iv.status] ?? '#999' }"
                        draggable="true"
                        @dragstart="onDragStart(iv, $event)"
                        @click="handleEventClick(iv.id, $event)"
                      >
                        <span class="event-time">{{ formatTime(iv.scheduled_at) }}</span>
                        <span class="event-name">{{ iv.candidate_id.slice(0, 6) }}…</span>
                        <NTag size="tiny" :type="statusTagTypeMap[iv.status] ?? 'default'" :bordered="false">
                          {{ INTERVIEW_TYPE_LABELS[iv.interview_type] || iv.interview_type }}
                        </NTag>
                      </div>
                    </template>
                    <div class="event-popover">
                      <div class="popover-header">
                        <span class="popover-title">{{ iv.candidate_id }}</span>
                        <NTag size="small" :type="statusTagTypeMap[iv.status] ?? 'default'">
                          {{ INTERVIEW_STATUS_LABELS[iv.status] || iv.status }}
                        </NTag>
                      </div>
                      <div class="popover-info">
                        <div>岗位：{{ iv.position_id ?? '-' }}</div>
                        <div>时间：{{ formatTime(iv.scheduled_at) }}</div>
                        <div>时长：{{ iv.duration_minutes }}分钟</div>
                        <div>类型：{{ INTERVIEW_TYPE_LABELS[iv.interview_type] || iv.interview_type }}</div>
                        <div v-if="iv.overall_score !== null">评分：{{ iv.overall_score }}/10</div>
                      </div>
                      <NButton size="tiny" type="primary" text @click="handleEventClick(iv.id, $event)">
                        查看详情 →
                      </NButton>
                    </div>
                  </NPopover>
                </template>
                <div v-if="day.interviews.length > 3" class="event-more">
                  +{{ day.interviews.length - 3 }} 更多
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>

      <!-- Day View -->
      <template v-if="calendarMode === 'day'">
        <div class="day-view">
          <div v-if="!dayViewInterviews.length" class="day-empty">
            <NEmpty description="当日无面试安排" />
          </div>
          <div
            v-for="iv in dayViewInterviews"
            :key="iv.id"
            class="day-event-card"
            :style="{ borderLeftColor: statusColorMap[iv.status] ?? '#999' }"
            draggable="true"
            @dragstart="onDragStart(iv, $event)"
            @click="handleEventClick(iv.id, $event)"
          >
            <div class="day-event-header">
              <span class="day-event-time">{{ formatTime(iv.scheduled_at) }}</span>
              <NTag size="small" :type="statusTagTypeMap[iv.status] ?? 'default'">
                {{ INTERVIEW_STATUS_LABELS[iv.status] || iv.status }}
              </NTag>
            </div>
            <div class="day-event-body">
              <span class="day-event-candidate">候选人：{{ iv.candidate_id }}</span>
              <span class="day-event-position">岗位：{{ iv.position_id ?? '-' }}</span>
              <NTag size="tiny" :bordered="false">
                {{ INTERVIEW_TYPE_LABELS[iv.interview_type] || iv.interview_type }}
              </NTag>
              <span v-if="iv.overall_score !== null" class="day-event-score">
                评分：{{ iv.overall_score }}/10
              </span>
            </div>
          </div>
        </div>
      </template>
    </div>
  </NSpin>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.interview-calendar {
  background: $bg-card;
  border-radius: $radius-md;
  padding: 16px;
}

.calendar-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;

  .toolbar-left {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .calendar-title {
    font-size: 16px;
    font-weight: 600;
    color: $text-primary;
  }
}

.calendar-grid {
  user-select: none;
}

.calendar-weekdays {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  border-bottom: 1px solid $border-light;
  margin-bottom: 4px;

  .weekday-cell {
    text-align: center;
    font-size: 13px;
    font-weight: 500;
    color: $text-muted;
    padding: 6px 0;
  }
}

.calendar-body {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
}

.calendar-cell {
  min-height: 90px;
  border: 1px solid $border-light;
  padding: 4px;
  cursor: pointer;
  transition: background $transition-fast;

  &:hover {
    background: $bg-card-hover;
  }

  &.other-month {
    opacity: 0.45;
  }

  &.is-today {
    background: rgba(var(--accent-info-rgb), 0.06);

    .date-number {
      background: var(--accent-info);
      color: var(--text-on-accent);
      border-radius: 50%;
      width: 22px;
      height: 22px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
    }
  }

  .cell-date {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 2px;

    .date-number {
      font-size: 12px;
      font-weight: 500;
      color: $text-primary;
    }

    .event-count {
      font-size: 10px;
      color: var(--accent-info);
      background: rgba(var(--accent-info-rgb), 0.12);
      border-radius: 8px;
      padding: 0 5px;
    }
  }

  .cell-events {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
}

.event-bar {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  padding: 1px 4px;
  border-left: 3px solid;
  background: $bg-secondary;
  border-radius: 2px;
  cursor: pointer;
  overflow: hidden;
  white-space: nowrap;

  .event-time {
    color: $text-muted;
    flex-shrink: 0;
  }

  .event-name {
    color: $text-primary;
    font-weight: 500;
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  &:hover {
    background: $bg-card-hover;
  }
}

.event-more {
  font-size: 10px;
  color: $text-muted;
  padding-left: 4px;
}

.event-popover {
  .popover-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;

    .popover-title {
      font-weight: 600;
      font-size: 14px;
      color: var(--text-primary);
    }
  }

  .popover-info {
    font-size: 13px;
    color: var(--text-secondary);
    line-height: 1.8;
    margin-bottom: 8px;
  }
}

// Day view
.day-view {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 200px;
}

.day-empty {
  padding: 40px 0;
}

.day-event-card {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px 16px;
  border-left: 4px solid;
  background: $bg-secondary;
  border-radius: $radius-sm;
  cursor: pointer;
  transition: box-shadow $transition-fast;

  &:hover {
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  }

  .day-event-header {
    display: flex;
    align-items: center;
    gap: 8px;

    .day-event-time {
      font-weight: 600;
      font-size: 14px;
      color: $text-primary;
    }
  }

  .day-event-body {
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 13px;
    color: $text-secondary;
    flex-wrap: wrap;

    .day-event-score {
      color: var(--success);
      font-weight: 500;
    }
  }
}
</style>
