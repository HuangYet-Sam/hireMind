<script setup lang="ts">
import { NSkeleton } from 'naive-ui'

defineProps<{
  rows?: number
  columns?: number
}>()
</script>

<template>
  <div class="table-skeleton">
    <div class="skeleton-header">
      <NSkeleton v-for="i in (columns ?? 5)" :key="i" text style="width: 100px;" />
    </div>
    <div v-for="r in (rows ?? 5)" :key="r" class="skeleton-row">
      <NSkeleton v-for="c in (columns ?? 5)" :key="c" text :width="60 + Math.random() * 40 + '%'" />
    </div>
  </div>
</template>

<style scoped lang="scss">
.table-skeleton {
  padding: 12px 0;
}

.skeleton-header,
.skeleton-row {
  display: flex;
  gap: 16px;
  padding: 10px 0;
}

.skeleton-header {
  border-bottom: 1px solid var(--border-light);
  margin-bottom: 4px;
}
</style>
