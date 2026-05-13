<script setup lang="ts">
import { NTooltip } from 'naive-ui'

defineProps<{
  source: string
  text?: string
  url?: string
}>()
</script>

<template>
  <NTooltip>
    <template #trigger>
      <span class="source-citation">
        <sup class="citation-mark">[{{ source }}]</sup>
        <span v-if="text" class="citation-text">{{ text }}</span>
      </span>
    </template>
    <div class="citation-detail">
      <div>来源: {{ source }}</div>
      <div v-if="url"><a :href="url" target="_blank" rel="noopener">{{ url }}</a></div>
    </div>
  </NTooltip>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.source-citation {
  display: inline-flex;
  align-items: baseline;
  gap: 2px;

  .citation-mark {
    color: var(--accent-info);
    cursor: pointer;
    font-weight: 600;
    font-size: 11px;
  }

  .citation-text {
    font-size: 12px;
    color: $text-muted;
  }
}

.citation-detail {
  font-size: 12px;
  line-height: 1.5;

  a {
    color: var(--accent-info);
    text-decoration: none;
  }
}
</style>
