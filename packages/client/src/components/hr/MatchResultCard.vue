<script setup lang="ts">
import { computed } from 'vue'
import { NCard, NProgress, NTag, NButton, NSpace, NTooltip } from 'naive-ui'
import type { MatchResultItem, CandidateMatchResultItem } from '@/api/hr/matching'

type MatchItem = MatchResultItem | CandidateMatchResultItem

const props = withDefaults(defineProps<{
  match: MatchItem
  showActions?: boolean
}>(), {
  showActions: true,
})

const emit = defineEmits<{
  'view-detail': [item: MatchItem]
  'add-to-interview': [item: MatchItem]
  'toggle-interest': [item: MatchItem, interested: boolean]
}>()

const scorePercentage = computed(() => Math.round(props.match.overall_score * 100))

const name = computed(() => {
  if ('candidate_name' in props.match) return props.match.candidate_name || 'Unknown'
  if ('position_title' in props.match) return props.match.position_title || 'Unknown'
  return 'Unknown'
})

const itemId = computed(() => {
  if ('candidate_id' in props.match) return props.match.candidate_id
  return props.match.position_id
})

const tier = computed<'strong' | 'good' | 'fair' | 'poor'>(() => {
  if (props.match.overall_score >= 0.8) return 'strong'
  if (props.match.overall_score >= 0.6) return 'good'
  if (props.match.overall_score >= 0.4) return 'fair'
  return 'poor'
})

const tierMeta: Record<string, { label: string; color: string }> = {
  strong: { label: 'Strong', color: '#18a058' },
  good: { label: 'Good', color: '#2080f0' },
  fair: { label: 'Fair', color: '#f0a020' },
  poor: { label: 'Poor', color: '#d03050' },
}

const progressColor = computed(() => tierMeta[tier.value].color)

const matchedSkills = computed(() => {
  return ('matched_skills' in props.match && props.match.matched_skills) ? props.match.matched_skills : []
})

const missingSkills = computed(() => {
  return ('missing_skills' in props.match && props.match.missing_skills) ? props.match.missing_skills : []
})

const skillScore = computed<number | null>(() => {
  return ('skill_score' in props.match && props.match.skill_score != null) ? props.match.skill_score : null
})

const experienceScore = computed<number | null>(() => {
  return ('experience_score' in props.match && props.match.experience_score != null) ? props.match.experience_score : null
})

const educationScore = computed<number | null>(() => {
  return ('education_score' in props.match && props.match.education_score != null) ? props.match.education_score : null
})

const recommendationLevel = computed(() => {
  const s = props.match.overall_score
  if (s >= 0.9) return 'Highly Recommended'
  if (s >= 0.8) return 'Recommended'
  if (s >= 0.6) return 'Consider'
  if (s >= 0.4) return 'Marginal'
  return 'Not Recommended'
})

const interested = computed(() => false) // placeholder: parent can manage this via toggle-interest
</script>

<template>
  <NCard size="small" class="match-result-card" hoverable>
    <div class="card-top">
      <div class="score-ring">
        <NProgress
          type="circle"
          :percentage="scorePercentage"
          :color="progressColor"
          rail-color="rgba(0, 0, 0, 0.06)"
          :stroke-width="6"
          :size="68"
        >
          <span class="ring-value" :style="{ color: progressColor }">{{ scorePercentage }}</span>
        </NProgress>
      </div>

      <div class="card-info">
        <div class="info-header">
          <span class="candidate-name">{{ name }}</span>
          <NTag
            size="small"
            :bordered="false"
            :color="{ color: tierMeta[tier].color + '18', textColor: tierMeta[tier].color }"
          >
            {{ tierMeta[tier].label }}
          </NTag>
        </div>

        <div class="recommendation">
          <span class="rec-label">{{ recommendationLevel }}</span>
        </div>

        <!-- Sub-scores -->
        <div v-if="skillScore !== null" class="sub-score-row">
          <span class="sub-label">Skills</span>
          <NProgress
            type="line"
            :percentage="Math.round(skillScore * 100)"
            :color="tierMeta[tier].color"
            :height="6"
            :border-radius="3"
            :show-indicator="false"
            style="flex: 1;"
          />
          <span class="sub-value">{{ Math.round(skillScore * 100) }}</span>
        </div>
        <div v-if="experienceScore !== null" class="sub-score-row">
          <span class="sub-label">Experience</span>
          <NProgress
            type="line"
            :percentage="Math.round(experienceScore * 100)"
            :color="tierMeta[tier].color"
            :height="6"
            :border-radius="3"
            :show-indicator="false"
            style="flex: 1;"
          />
          <span class="sub-value">{{ Math.round(experienceScore * 100) }}</span>
        </div>
        <div v-if="educationScore !== null" class="sub-score-row">
          <span class="sub-label">Education</span>
          <NProgress
            type="line"
            :percentage="Math.round(educationScore * 100)"
            :color="tierMeta[tier].color"
            :height="6"
            :border-radius="3"
            :show-indicator="false"
            style="flex: 1;"
          />
          <span class="sub-value">{{ Math.round(educationScore * 100) }}</span>
        </div>
      </div>
    </div>

    <!-- Matched Skills -->
    <div v-if="matchedSkills.length" class="skills-section">
      <span class="section-label">Matched:</span>
      <NSpace :size="4" :wrap="true">
        <NTag v-for="skill in matchedSkills.slice(0, 6)" :key="skill" size="tiny" type="success">
          {{ skill }}
        </NTag>
        <NTag v-if="matchedSkills.length > 6" size="tiny">
          +{{ matchedSkills.length - 6 }}
        </NTag>
      </NSpace>
    </div>

    <!-- Missing Skills -->
    <div v-if="missingSkills.length" class="skills-section concerns">
      <span class="section-label">Missing:</span>
      <NSpace :size="4" :wrap="true">
        <NTag v-for="skill in missingSkills.slice(0, 4)" :key="skill" size="tiny" type="error">
          {{ skill }}
        </NTag>
        <NTag v-if="missingSkills.length > 4" size="tiny">
          +{{ missingSkills.length - 4 }}
        </NTag>
      </NSpace>
    </div>

    <!-- Explanation -->
    <div v-if="match.explanation" class="explanation-section">
      <div class="explanation-text">{{ match.explanation }}</div>
    </div>

    <!-- Actions -->
    <div v-if="showActions" class="card-actions">
      <NButton size="tiny" type="primary" @click="emit('view-detail', match)">
        View Detail
      </NButton>
      <NButton size="tiny" @click="emit('add-to-interview', match)">
        Add to Interview
      </NButton>
      <NTooltip>
        <template #trigger>
          <NButton
            size="tiny"
            :type="interested ? 'warning' : 'default'"
            @click="emit('toggle-interest', match, !interested)"
          >
            {{ interested ? 'Not Interested' : 'Interested' }}
          </NButton>
        </template>
        {{ interested ? 'Mark as not interested' : 'Mark as interested' }}
      </NTooltip>
    </div>
  </NCard>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.match-result-card {
  .card-top {
    display: flex;
    gap: 16px;
    margin-bottom: 10px;
  }

  .score-ring {
    flex-shrink: 0;
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;

    .ring-value {
      font-size: 16px;
      font-weight: 700;
    }
  }

  .card-info {
    flex: 1;
    min-width: 0;

    .info-header {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 4px;
    }

    .candidate-name {
      font-weight: 600;
      font-size: 15px;
      color: $text-primary;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .recommendation {
      margin-bottom: 8px;

      .rec-label {
        font-size: 12px;
        color: $text-muted;
        font-weight: 500;
      }
    }

    .sub-score-row {
      display: flex;
      align-items: center;
      gap: 6px;
      margin-bottom: 3px;

      .sub-label {
        font-size: 11px;
        color: $text-muted;
        min-width: 60px;
        text-align: right;
      }

      .sub-value {
        font-size: 11px;
        font-weight: 600;
        min-width: 26px;
        text-align: right;
        color: $text-secondary;
      }
    }
  }

  .skills-section {
    margin-bottom: 6px;

    &.concerns {
      margin-top: 2px;
    }

    .section-label {
      font-size: 11px;
      color: $text-muted;
      margin-right: 6px;
    }
  }

  .explanation-section {
    margin-top: 8px;
    padding-top: 8px;
    border-top: 1px solid $border-light;

    .explanation-text {
      font-size: 13px;
      color: $text-muted;
      line-height: 1.5;
    }
  }

  .card-actions {
    display: flex;
    gap: 8px;
    margin-top: 10px;
    padding-top: 10px;
    border-top: 1px solid $border-light;
    flex-wrap: wrap;
  }
}
</style>
