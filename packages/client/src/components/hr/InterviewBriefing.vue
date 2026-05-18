<script setup lang="ts">
import { computed } from 'vue'
import {
  NCard, NTag, NButton, NSpin, NEmpty, NIcon, NDivider,
} from 'naive-ui'
import type { InterviewBriefingResponse } from '@/api/hr/interviews'

const props = withDefaults(defineProps<{
  briefing: InterviewBriefingResponse | null
  loading?: boolean
}>(), {
  loading: false,
})

const emit = defineEmits<{
  generate: []
  refresh: []
}>()

const hasBriefing = computed(() => props.briefing !== null)

const generatedTime = computed(() => {
  if (!props.briefing?.generated_at) return ''
  return new Date(props.briefing.generated_at).toLocaleString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
})
</script>

<template>
  <NSpin :show="loading">
    <NCard class="interview-briefing" size="small">
      <template #header>
        <div class="briefing-header">
          <span class="briefing-title">AI 面试考察清单</span>
          <span v-if="generatedTime" class="briefing-time">
            生成于 {{ generatedTime }}
          </span>
        </div>
      </template>
      <template #header-extra>
        <div class="briefing-actions">
          <NButton
            v-if="hasBriefing"
            size="small"
            type="default"
            :loading="loading"
            @click="emit('refresh')"
          >
            刷新
          </NButton>
          <NButton
            v-else
            size="small"
            type="primary"
            :loading="loading"
            @click="emit('generate')"
          >
            生成考察清单
          </NButton>
        </div>
      </template>

      <template v-if="!hasBriefing && !loading">
        <NEmpty description="暂无考察清单，点击上方按钮生成" />
      </template>

      <template v-if="hasBriefing && briefing">
        <!-- Position Requirements -->
        <section v-if="briefing.position_requirements.length" class="briefing-section">
          <h4 class="section-title">岗位关键要求</h4>
          <div class="tag-list">
            <NTag
              v-for="(req, idx) in briefing.position_requirements"
              :key="'req-' + idx"
              size="small"
              :bordered="false"
              type="info"
              class="briefing-tag"
            >
              {{ req }}
            </NTag>
          </div>
        </section>

        <NDivider v-if="briefing.candidate_strengths.length" />

        <!-- Candidate Strengths -->
        <section v-if="briefing.candidate_strengths.length" class="briefing-section">
          <h4 class="section-title strength-title">候选人优势</h4>
          <div class="tag-list">
            <NTag
              v-for="(s, idx) in briefing.candidate_strengths"
              :key="'str-' + idx"
              size="small"
              :bordered="false"
              type="success"
              class="briefing-tag"
            >
              ✅ {{ s }}
            </NTag>
          </div>
        </section>

        <NDivider v-if="briefing.candidate_gaps.length" />

        <!-- Candidate Gaps -->
        <section v-if="briefing.candidate_gaps.length" class="briefing-section">
          <h4 class="section-title gap-title">差距点</h4>
          <div class="tag-list">
            <NTag
              v-for="(g, idx) in briefing.candidate_gaps"
              :key="'gap-' + idx"
              size="small"
              :bordered="false"
              type="warning"
              class="briefing-tag"
            >
              ⚠️ {{ g }}
            </NTag>
          </div>
        </section>

        <NDivider v-if="briefing.verification_points.length" />

        <!-- Verification Points -->
        <section v-if="briefing.verification_points.length" class="briefing-section">
          <h4 class="section-title verify-title">验证项</h4>
          <div class="tag-list">
            <NTag
              v-for="(v, idx) in briefing.verification_points"
              :key="'ver-' + idx"
              size="small"
              :bordered="false"
              type="error"
              class="briefing-tag"
            >
              🔍 {{ v }}
            </NTag>
          </div>
        </section>

        <NDivider v-if="briefing.focus_areas.length" />

        <!-- Focus Areas -->
        <section v-if="briefing.focus_areas.length" class="briefing-section">
          <h4 class="section-title">重点方向</h4>
          <ul class="focus-list">
            <li v-for="(f, idx) in briefing.focus_areas" :key="'focus-' + idx">
              {{ f }}
            </li>
          </ul>
        </section>

        <NDivider v-if="briefing.suggested_questions.length" />

        <!-- Suggested Questions -->
        <section v-if="briefing.suggested_questions.length" class="briefing-section">
          <h4 class="section-title">建议问题</h4>
          <ol class="question-list">
            <li v-for="(q, idx) in briefing.suggested_questions" :key="'q-' + idx">
              {{ q }}
            </li>
          </ol>
        </section>
      </template>
    </NCard>
  </NSpin>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.interview-briefing {
  .briefing-header {
    display: flex;
    align-items: center;
    gap: 8px;

    .briefing-title {
      font-size: 15px;
      font-weight: 600;
      color: $text-primary;
    }

    .briefing-time {
      font-size: 12px;
      color: $text-muted;
    }
  }

  .briefing-actions {
    display: flex;
    gap: 8px;
  }
}

.briefing-section {
  margin-bottom: 4px;

  .section-title {
    font-size: 13px;
    font-weight: 600;
    color: $text-primary;
    margin: 0 0 8px;

    &.strength-title {
      color: var(--success);
    }

    &.gap-title {
      color: var(--warning);
    }

    &.verify-title {
      color: var(--error);
    }
  }
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;

  .briefing-tag {
    max-width: 280px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.focus-list {
  margin: 0;
  padding-left: 18px;

  li {
    font-size: 13px;
    color: $text-secondary;
    line-height: 1.8;
  }
}

.question-list {
  margin: 0;
  padding-left: 18px;

  li {
    font-size: 13px;
    color: $text-secondary;
    line-height: 1.8;
    padding: 2px 0;
  }
}
</style>
