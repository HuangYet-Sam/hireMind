<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { use } from 'echarts/core'
import { RadarChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'
import {
  NCard, NGrid, NGridItem, NTag, NProgress, NSpin, NButton, NSpace, NEmpty,
  useMessage,
} from 'naive-ui'
import { useMatchingStore } from '@/stores/hr/matching'
import MatchScore from '@/components/hr/MatchScore.vue'
import MatchFeedback from '@/components/hr/MatchFeedback.vue'
import type { MatchResultItem, CandidateMatchResultItem } from '@/api/hr/matching'

use([RadarChart, TitleComponent, TooltipComponent, LegendComponent, CanvasRenderer])

type MatchItem = MatchResultItem | CandidateMatchResultItem

const props = defineProps<{
  matchItem: MatchItem
  positionTitle?: string
  candidateName?: string
}>()

const emit = defineEmits<{
  back: []
}>()

const matchingStore = useMatchingStore()
const message = useMessage()

function getScore(item: MatchItem): number {
  return item.overall_score
}

function getTier(score: number): 'strong' | 'good' | 'fair' | 'poor' {
  if (score >= 0.8) return 'strong'
  if (score >= 0.6) return 'good'
  if (score >= 0.4) return 'fair'
  return 'poor'
}

const tierMeta: Record<string, { label: string; color: string }> = {
  strong: { label: 'Strong (>80)', color: '#18a058' },
  good: { label: 'Good (60-80)', color: '#2080f0' },
  fair: { label: 'Fair (40-60)', color: '#f0a020' },
  poor: { label: 'Poor (<40)', color: '#d03050' },
}

const scoreDimensions = computed(() => {
  const item = props.matchItem
  const dims: { name: string; value: number; max: number; key: string }[] = []

  dims.push({ name: 'Overall', value: item.overall_score * 100, max: 100, key: 'overall' })

  if ('skill_score' in item && item.skill_score != null) {
    dims.push({ name: 'Skills', value: item.skill_score * 100, max: 100, key: 'skill' })
  }
  if ('experience_score' in item && item.experience_score != null) {
    dims.push({ name: 'Experience', value: item.experience_score * 100, max: 100, key: 'experience' })
  }
  if ('education_score' in item && item.education_score != null) {
    dims.push({ name: 'Education', value: item.education_score * 100, max: 100, key: 'education' })
  }

  return dims
})

const radarOption = computed(() => ({
  tooltip: {},
  radar: {
    indicator: scoreDimensions.value.map(d => ({
      name: d.name,
      max: d.max,
    })),
    shape: 'polygon' as const,
    splitNumber: 5,
    axisName: {
      color: 'var(--text-secondary)',
      fontSize: 12,
    },
    splitArea: {
      areaStyle: {
        color: ['rgba(0,0,0,0.02)', 'rgba(0,0,0,0.04)'],
      },
    },
  },
  series: [{
    type: 'radar',
    data: [{
      value: scoreDimensions.value.map(d => Math.round(d.value)),
      name: 'Match Score',
      areaStyle: {
        color: tierMeta[getTier(getScore(props.matchItem))].color + '30',
      },
      lineStyle: {
        color: tierMeta[getTier(getScore(props.matchItem))].color,
        width: 2,
      },
      itemStyle: {
        color: tierMeta[getTier(getScore(props.matchItem))].color,
      },
    }],
  }],
}))

const matchedSkills = computed(() => {
  const item = props.matchItem
  return ('matched_skills' in item && item.matched_skills) ? item.matched_skills : []
})

const missingSkills = computed(() => {
  const item = props.matchItem
  return ('missing_skills' in item && item.missing_skills) ? item.missing_skills : []
})

const explanation = computed(() => props.matchItem.explanation ?? null)

const gapAnalysis = computed(() => {
  const gaps: { skill: string; severity: 'high' | 'medium' | 'low' }[] = []
  const item = props.matchItem

  for (const skill of missingSkills.value) {
    const skillScore = 'skill_score' in item ? item.skill_score : null
    const severity = (skillScore != null && skillScore < 0.4) ? 'high'
      : (skillScore != null && skillScore < 0.6) ? 'medium' : 'low'
    gaps.push({ skill, severity })
  }

  return gaps
})

const matchId = computed(() => {
  const item = props.matchItem
  if ('candidate_id' in item) return `${item.candidate_id}-${'position_id' in item ? item.position_id : ''}`
  return ''
})

const displayName = computed(() => {
  const item = props.matchItem
  if ('candidate_name' in item) return item.candidate_name || 'Unknown'
  if ('position_title' in item) return item.position_title || 'Unknown'
  return 'Unknown'
})
</script>

<template>
  <div class="match-detail-view">
    <header class="detail-header">
      <NButton text @click="emit('back')">
        ← Back to list
      </NButton>
      <div class="detail-title-row">
        <MatchScore :score="getScore(matchItem)" size="large" />
        <div class="detail-title-info">
          <h2 class="detail-name">{{ displayName }}</h2>
          <NSpace :size="8" align="center">
            <NTag
              size="small"
              :bordered="false"
              :color="{
                color: tierMeta[getTier(getScore(matchItem))].color + '18',
                textColor: tierMeta[getTier(getScore(matchItem))].color,
              }"
            >
              {{ tierMeta[getTier(getScore(matchItem))].label }}
            </NTag>
            <span v-if="positionTitle" class="detail-sub">{{ positionTitle }}</span>
            <span v-if="candidateName" class="detail-sub">{{ candidateName }}</span>
          </NSpace>
        </div>
      </div>
    </header>

    <NGrid :cols="2" :x-gap="16" :y-gap="16" responsive="screen" item-responsive>
      <NGridItem span="0:2 640:1">
        <NCard title="Ability Radar" size="small">
          <VChart :option="radarOption" autoresize style="height: 300px;" />
        </NCard>
      </NGridItem>

      <NGridItem span="0:2 640:1">
        <NCard title="Score Breakdown" size="small">
          <div class="breakdown-list">
            <div v-for="dim in scoreDimensions" :key="dim.key" class="breakdown-item">
              <div class="breakdown-item-header">
                <span class="breakdown-label">{{ dim.name }}</span>
                <span class="breakdown-value">{{ Math.round(dim.value) }}%</span>
              </div>
              <NProgress
                type="line"
                :percentage="Math.round(dim.value)"
                :color="tierMeta[getTier(dim.value / 100)].color"
                :height="12"
                :border-radius="6"
                :show-indicator="false"
              />
            </div>
          </div>
        </NCard>

        <NCard title="Match Feedback" size="small" style="margin-top: 16px;">
          <MatchFeedback :match-id="matchId" />
        </NCard>
      </NGridItem>
    </NGrid>

    <NGrid :cols="2" :x-gap="16" :y-gap="16" style="margin-top: 16px;" responsive="screen" item-responsive>
      <NGridItem span="0:2 640:1">
        <NCard title="Matched Skills" size="small">
          <div v-if="matchedSkills.length" class="skills-list">
            <NTag
              v-for="skill in matchedSkills"
              :key="skill"
              type="success"
              size="small"
              style="margin: 2px;"
            >
              {{ skill }}
            </NTag>
          </div>
          <NEmpty v-else description="No matched skills" size="small" />
        </NCard>
      </NGridItem>

      <NGridItem span="0:2 640:1">
        <NCard title="Gap Analysis" size="small">
          <div v-if="gapAnalysis.length" class="gap-list">
            <div v-for="gap in gapAnalysis" :key="gap.skill" class="gap-item">
              <NTag
                size="small"
                :type="gap.severity === 'high' ? 'error' : gap.severity === 'medium' ? 'warning' : 'default'"
                style="margin: 2px;"
              >
                {{ gap.skill }}
              </NTag>
              <span class="gap-severity" :class="gap.severity">
                {{ gap.severity === 'high' ? 'Critical gap' : gap.severity === 'medium' ? 'Moderate gap' : 'Minor gap' }}
              </span>
            </div>
          </div>
          <NEmpty v-else description="No skill gaps detected" size="small" />
        </NCard>
      </NGridItem>
    </NGrid>

    <NCard v-if="explanation" title="AI Explanation" size="small" style="margin-top: 16px;">
      <div class="explanation-text">
        {{ explanation }}
      </div>
    </NCard>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.match-detail-view {
  padding: 24px;
}

.detail-header {
  margin-bottom: 24px;

  .detail-title-row {
    display: flex;
    align-items: center;
    gap: 16px;
    margin-top: 12px;
  }

  .detail-title-info {
    flex: 1;
    min-width: 0;
  }

  .detail-name {
    font-size: 20px;
    font-weight: 600;
    color: $text-primary;
    margin: 0 0 4px;
  }

  .detail-sub {
    font-size: 13px;
    color: $text-muted;
  }
}

.breakdown-list {
  display: flex;
  flex-direction: column;
  gap: 12px;

  .breakdown-item {
    .breakdown-item-header {
      display: flex;
      justify-content: space-between;
      margin-bottom: 4px;
    }

    .breakdown-label {
      font-size: 13px;
      color: $text-secondary;
    }

    .breakdown-value {
      font-size: 13px;
      font-weight: 600;
      color: $text-primary;
    }
  }
}

.skills-list {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.gap-list {
  display: flex;
  flex-direction: column;
  gap: 8px;

  .gap-item {
    display: flex;
    align-items: center;
    gap: 8px;

    .gap-severity {
      font-size: 11px;

      &.high {
        color: var(--error);
      }

      &.medium {
        color: var(--warning);
      }

      &.low {
        color: $text-muted;
      }
    }
  }
}

.explanation-text {
  font-size: 14px;
  line-height: 1.6;
  color: $text-secondary;
}
</style>
