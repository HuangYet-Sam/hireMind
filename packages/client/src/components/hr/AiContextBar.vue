<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, computed } from 'vue'
import { NCard, NSkeleton, NButton, NSpin, NIcon, NCollapse, NCollapseItem, NEmpty } from 'naive-ui'
import { getEntityInsights } from '@/api/hr/insights'
import type { EntityType, InsightData } from '@/api/hr/insights'

const props = defineProps<{
  entityType: EntityType
  entityId: string
  activeTab?: string
}>()

const loading = ref(false)
const error = ref<string | null>(null)
const insight = ref<InsightData | null>(null)
const expanded = ref(false)
const cache = ref<Map<string, InsightData | null>>(new Map())

let debounceTimer: ReturnType<typeof setTimeout> | null = null

const cacheKey = computed(() => `${props.activeTab ?? '__default__'}`)
const hasInsight = computed(() => insight.value !== null)
const summaryText = computed(() => insight.value?.summary ?? '')
const detailText = computed(() => insight.value?.details ?? '')
const suggestions = computed(() => insight.value?.suggestions ?? [])
const actions = computed(() => insight.value?.actions ?? [])

async function fetchInsights() {
  const key = cacheKey.value
  if (cache.value.has(key)) {
    insight.value = cache.value.get(key) ?? null
    return
  }

  loading.value = true
  error.value = null

  try {
    const res = await getEntityInsights({
      entity_type: props.entityType,
      entity_id: props.entityId,
      tab: props.activeTab,
    })
    insight.value = res.insight
    cache.value.set(key, res.insight ?? null)
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load insights'
    insight.value = null
  } finally {
    loading.value = false
  }
}

function debouncedFetch() {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(fetchInsights, 300)
}

watch(() => [props.entityType, props.entityId], () => {
  cache.value.clear()
  fetchInsights()
})

watch(() => props.activeTab, () => {
  debouncedFetch()
})

onMounted(fetchInsights)

onUnmounted(() => {
  if (debounceTimer) clearTimeout(debounceTimer)
})
</script>

<template>
  <div v-if="hasInsight || loading || error" class="ai-context-bar">
    <NCard size="small" :bordered="true" class="context-card">
      <div class="bar-content">
        <div class="bar-left">
          <div class="ai-icon-wrapper">
            <NSpin v-if="loading" :size="16" />
            <span v-else class="ai-icon">✦</span>
          </div>

          <div v-if="loading" class="loading-skeleton">
            <NSkeleton text style="width: 60%" />
            <NSkeleton text style="width: 40%; margin-top: 4px" />
          </div>

          <div v-else-if="error" class="error-text">
            {{ error }}
          </div>

          <div v-else class="summary-text">
            {{ summaryText }}
          </div>
        </div>

        <div v-if="!loading && !error && hasInsight" class="bar-right">
          <NButton
            v-if="detailText || suggestions.length"
            size="small"
            quaternary
            @click="expanded = !expanded"
          >
            {{ expanded ? '收起详情' : '展开详情' }}
          </NButton>
          <NButton
            v-for="action in actions.slice(0, 2)"
            :key="action.label"
            size="small"
            type="primary"
            quaternary
            tag="a"
            :href="action.link"
          >
            {{ action.label }}
          </NButton>
        </div>
      </div>

      <NCollapse v-if="expanded && hasInsight" :default-expanded-names="['details']" class="details-collapse">
        <NCollapseItem title="AI 洞察详情" name="details">
          <p v-if="detailText" class="detail-text">{{ detailText }}</p>
          <ul v-if="suggestions.length" class="suggestions-list">
            <li v-for="(s, i) in suggestions" :key="i">{{ s }}</li>
          </ul>
          <p v-if="insight?.confidence" class="confidence-text">
            置信度: {{ Math.round(insight.confidence * 100) }}%
          </p>
        </NCollapseItem>
      </NCollapse>
    </NCard>
  </div>
</template>

<style scoped lang="scss">
.ai-context-bar {
  margin: 12px 0;
}

.context-card {
  background-color: rgba(33, 150, 243, 0.04);
  border-left: 3px solid rgba(33, 150, 243, 0.5);
}

.bar-content {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  min-height: 40px;
}

.bar-left {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  flex: 1;
  min-width: 0;
}

.ai-icon-wrapper {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.ai-icon {
  font-size: 16px;
  color: rgba(33, 150, 243, 0.8);
}

.loading-skeleton {
  flex: 1;
  min-width: 0;
}

.error-text {
  color: var(--error-color, #d03050);
  font-size: 13px;
}

.summary-text {
  font-size: 14px;
  line-height: 1.6;
  color: var(--text-color, #333);
}

.bar-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.details-collapse {
  margin-top: 8px;
}

.detail-text {
  font-size: 13px;
  line-height: 1.6;
  color: var(--text-color-secondary, #666);
}

.suggestions-list {
  margin: 8px 0 0 18px;
  padding: 0;
  font-size: 13px;
  line-height: 1.8;
  color: var(--text-color-secondary, #666);
}

.confidence-text {
  margin-top: 8px;
  font-size: 12px;
  opacity: 0.6;
}

@media (max-width: 768px) {
  .bar-content {
    flex-direction: column;
    gap: 8px;
  }

  .bar-right {
    align-self: flex-end;
  }
}
</style>
