<script setup lang="ts">
import type { KanbanTask } from '@/api/hermes/kanban'
import KanbanTaskCard from './KanbanTaskCard.vue'

const props = defineProps<{ tasks: KanbanTask[]; selectedTaskId?: string | null }>()
const emit = defineEmits<{ select: [task: KanbanTask] }>()

const columns = [
  { key: 'todo', label: 'To Do' },
  { key: 'ready', label: 'Ready' },
  { key: 'running', label: 'Running' },
  { key: 'blocked', label: 'Blocked' },
  { key: 'done', label: 'Done' },
]

function tasksByStatus(status: string): KanbanTask[] {
  return props.tasks.filter(t => t.status === status)
}
</script>

<template>
  <div class="kanban-board">
    <div v-for="col in columns" :key="col.key" class="kanban-column">
      <div class="column-header">
        <span class="column-title">{{ col.label }}</span>
        <span class="column-count">{{ tasksByStatus(col.key).length }}</span>
      </div>
      <div class="column-body">
        <KanbanTaskCard
          v-for="task in tasksByStatus(col.key)"
          :key="task.id"
          :task="task"
          :selected="task.id === props.selectedTaskId"
          @click="emit('select', task)"
        />
        <div v-if="tasksByStatus(col.key).length === 0" class="column-empty">
          —
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.kanban-board {
  display: flex;
  gap: 12px;
  overflow-x: auto;
  min-height: 400px;
}

.kanban-column {
  flex: 1;
  min-width: 200px;
  max-width: 280px;
  display: flex;
  flex-direction: column;
}

.column-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: $bg-card;
  border: 1px solid $border-light;
  border-radius: 6px 6px 0 0;
  border-bottom: 2px solid $border-color;
}

.column-title {
  font-size: 13px;
  font-weight: 600;
  color: $text-primary;
}

.column-count {
  font-size: 12px;
  color: $text-muted;
  background: $bg-secondary;
  padding: 1px 8px;
  border-radius: 10px;
}

.column-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 8px;
  background: var(--n-color-modal, #fafafa);
  border: 1px solid $border-light;
  border-top: none;
  border-radius: 0 0 6px 6px;
  min-height: 200px;
}

.column-empty {
  text-align: center;
  color: $text-muted;
  padding: 20px 0;
  font-size: 12px;
}
</style>
