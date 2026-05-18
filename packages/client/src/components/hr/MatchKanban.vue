<script setup lang="ts">
import { ref, computed } from 'vue'
import {
  NCard, NProgress, NTag, NButton, NSpace, NEmpty, NSpin,
  NCollapse, NCollapseItem, NTooltip,
} from 'naive-ui'
import type { MatchResultItem, CandidateMatchResultItem } from '@/api/hr/matching'

type MatchItem = MatchResultItem | CandidateMatchResultItem

interface KanbanColumn {
  key: 'strong' | 'good' | 'weak'
  label: string
  color: string
  threshold: { min: number; max: number }
}

const props = withDefaults(defineProps<{
  matches: MatchItem[]
  loading?: boolean
}>(), {
  loading: false,
})

const emit = defineEmits<{
  reorder: [updatedMatches: MatchItem[]]
  'view-detail': [item: MatchItem]
  feedback: [item: MatchItem, feedback: 'interested' | 'not-interested']
}>()

const columns: KanbanColumn[] = [
  { key: 'strong', label: 'Strong Match (≥80)', color: '#18a058', threshold: { min: 0.8, max: 1.01 } },
  { key: 'good', label: 'Good Match (60-80)', color: '#2080f0', threshold: { min: 0.6, max: 0.8 } },
  { key: 'weak', label: 'Weak Match (<60)', color: '#f0a020', threshold: { min: 0, max: 0.6 } },
]

const collapsed = ref<Record<string, boolean>>({})

const groupedMatches = computed(() => {
  const groups: Record<string, MatchItem[]> = {
    strong: [],
    good: [],
    weak: [],
  }
  for (const item of props.matches) {
    const score = item.overall_score
    if (score >= 0.8) {
      groups.strong.push(item)
    } else if (score >= 0.6) {
      groups.good.push(item)
    } else {
      groups.weak.push(item)
    }
  }
  return groups
})

function getName(item: MatchItem): string {
  if ('candidate_name' in item) return item.candidate_name || 'Unknown'
  if ('position_title' in item) return item.position_title || 'Unknown'
  return 'Unknown'
}

function getItemKey(item: MatchItem): string {
  if ('candidate_id' in item) return item.candidate_id
  return item.position_id
}

function getMatchedSkills(item: MatchItem): string[] {
  return ('matched_skills' in item && item.matched_skills) ? item.matched_skills : []
}

function getTierColor(score: number): string {
  if (score >= 0.8) return '#18a058'
  if (score >= 0.6) return '#2080f0'
  return '#f0a020'
}

// Drag & Drop state
const dragItem = ref<MatchItem | null>(null)
const dragSourceColumn = ref<string | null>(null)

function onDragStart(item: MatchItem, columnKey: string, event: DragEvent) {
  dragItem.value = item
  dragSourceColumn.value = columnKey
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move'
    event.dataTransfer.setData('text/plain', getItemKey(item))
  }
}

function onDragOver(event: DragEvent) {
  event.preventDefault()
  if (event.dataTransfer) {
    event.dataTransfer.dropEffect = 'move'
  }
}

function onDrop(targetColumnKey: string, targetIndex: number) {
  if (!dragItem.value) return

  const updatedMatches = [...props.matches]
  const draggedKey = getItemKey(dragItem.value)
  const draggedIndex = updatedMatches.findIndex(m => getItemKey(m) === draggedKey)

  if (draggedIndex === -1) return

  // Remove from old position
  const [movedItem] = updatedMatches.splice(draggedIndex, 1)

  // Recalculate target index after removal
  const targetGroup = groupedMatches.value[targetColumnKey]
  let insertAtIndex: number

  if (targetIndex >= 0 && targetIndex < targetGroup.length) {
    const targetItemKey = getItemKey(targetGroup[targetIndex])
    insertAtIndex = updatedMatches.findIndex(m => getItemKey(m) === targetItemKey)
    if (insertAtIndex === -1) insertAtIndex = updatedMatches.length
  } else {
    insertAtIndex = updatedMatches.length
  }

  // Adjust score to match target column tier
  // We keep the original score but place the item in the new position
  updatedMatches.splice(insertAtIndex, 0, movedItem)

  emit('reorder', updatedMatches)
  dragItem.value = null
  dragSourceColumn.value = null
}

function onDragEnd() {
  dragItem.value = null
  dragSourceColumn.value = null
}

function toggleCollapse(columnKey: string) {
  collapsed.value[columnKey] = !collapsed.value[columnKey]
}
</script>

<template>
  <NSpin :show="loading">
    <div class="match-kanban">
      <div
        v-for="column in columns"
        :key="column.key"
        class="kanban-column"
        :class="{ collapsed: collapsed[column.key] }"
      >
        <!-- Column Header -->
        <div
          class="kanban-column-header"
          :style="{ borderTopColor: column.color }"
        >
          <div class="header-left">
            <span class="column-title" :style="{ color: column.color }">
              {{ column.label }}
            </span>
            <span class="column-count">
              {{ groupedMatches[column.key].length }}
            </span>
          </div>
          <NButton
            quaternary
            circle
            size="tiny"
            @click="toggleCollapse(column.key)"
          >
            <template #icon>
              <span class="collapse-icon">{{ collapsed[column.key] ? '▸' : '▾' }}</span>
            </template>
          </NButton>
        </div>

        <!-- Column Body -->
        <div
          v-show="!collapsed[column.key]"
          class="kanban-column-body"
          @dragover="onDragOver"
          @drop="onDrop(column.key, groupedMatches[column.key].length)"
        >
          <div
            v-for="(match, index) in groupedMatches[column.key]"
            :key="getItemKey(match)"
            class="kanban-card-wrapper"
            draggable="true"
            @dragstart="onDragStart(match, column.key, $event)"
            @dragend="onDragEnd"
            @dragover="onDragOver"
            @drop.stop="onDrop(column.key, index)"
          >
            <NCard size="small" class="kanban-card" hoverable>
              <div class="card-header">
                <span class="card-name">{{ getName(match) }}</span>
                <NTooltip>
                  <template #trigger>
                    <span class="card-score" :style="{ color: getTierColor(match.overall_score) }">
                      {{ Math.round(match.overall_score * 100) }}
                    </span>
                  </template>
                  Overall: {{ Math.round(match.overall_score * 100) }}%
                </NTooltip>
              </div>

              <NProgress
                type="line"
                :percentage="Math.round(match.overall_score * 100)"
                :color="column.color"
                :height="6"
                :border-radius="3"
                :show-indicator="false"
                style="margin-bottom: 8px;"
              />

              <div v-if="getMatchedSkills(match).length" class="card-skills">
                <NTag
                  v-for="skill in getMatchedSkills(match).slice(0, 3)"
                  :key="skill"
                  size="tiny"
                  type="success"
                  style="margin: 2px;"
                >
                  {{ skill }}
                </NTag>
                <NTag v-if="getMatchedSkills(match).length > 3" size="tiny" style="margin: 2px;">
                  +{{ getMatchedSkills(match).length - 3 }}
                </NTag>
              </div>

              <div class="card-actions">
                <NButton
                  size="tiny"
                  type="primary"
                  text
                  @click="emit('view-detail', match)"
                >
                  Detail
                </NButton>
                <NButton
                  size="tiny"
                  text
                  @click="emit('feedback', match, 'interested')"
                >
                  👍
                </NButton>
                <NButton
                  size="tiny"
                  text
                  @click="emit('feedback', match, 'not-interested')"
                >
                  👎
                </NButton>
              </div>
            </NCard>
          </div>

          <NEmpty
            v-if="!groupedMatches[column.key].length"
            description="No matches"
            size="small"
          />
        </div>
      </div>
    </div>
  </NSpin>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.match-kanban {
  display: flex;
  gap: 12px;
  overflow-x: auto;
  padding-bottom: 8px;
  min-height: 200px;
}

.kanban-column {
  flex: 1;
  min-width: 240px;
  max-width: 340px;
  background: $bg-secondary;
  border-radius: $radius-md;
  display: flex;
  flex-direction: column;
  transition: all $transition-normal;

  &.collapsed {
    .kanban-column-header {
      border-radius: $radius-md;
    }
  }
}

.kanban-column-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-top: 3px solid;
  border-radius: $radius-md $radius-md 0 0;
  user-select: none;

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

  .collapse-icon {
    font-size: 12px;
    color: $text-muted;
  }
}

.kanban-column-body {
  padding: 8px;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 60px;
}

.kanban-card-wrapper {
  cursor: grab;

  &:active {
    cursor: grabbing;
  }
}

.kanban-card {
  transition: box-shadow $transition-fast, transform $transition-fast;

  &:hover {
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  }

  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 6px;
  }

  .card-name {
    font-weight: 600;
    font-size: 14px;
    color: $text-primary;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    flex: 1;
    min-width: 0;
    margin-right: 8px;
  }

  .card-score {
    font-weight: 700;
    font-size: 16px;
    flex-shrink: 0;
  }

  .card-skills {
    display: flex;
    flex-wrap: wrap;
    margin-bottom: 6px;
  }

  .card-actions {
    display: flex;
    align-items: center;
    gap: 4px;
    margin-top: 4px;
    padding-top: 6px;
    border-top: 1px solid $border-light;
  }
}
</style>
