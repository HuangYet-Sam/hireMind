<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import {
  NCard, NSelect, NButton, NSpin, NEmpty, NGrid, NGridItem, NProgress,
  NSpace, NTag, NInput, NTooltip, useMessage,
} from 'naive-ui'
import { useCandidateStore } from '@/stores/hr/candidates'
import { useMatchingStore } from '@/stores/hr/matching'
import MatchScore from '@/components/hr/MatchScore.vue'
import MatchDetailView from '@/components/hr/MatchDetailView.vue'
import type { CandidateMatchResultItem } from '@/api/hr/matching'

const candidateStore = useCandidateStore()
const matchingStore = useMatchingStore()
const selectedCandidateId = ref<string | null>(null)
const message = useMessage()
const selectedMatch = ref<CandidateMatchResultItem | null>(null)

onMounted(() => {
  candidateStore.fetchCandidates()
})

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

const sortedMatches = computed(() => {
  return [...matchingStore.matches]
    .sort((a, b) => b.overall_score - a.overall_score) as CandidateMatchResultItem[]
})

async function handleReverseMatch() {
  if (!selectedCandidateId.value) return
  try {
    selectedMatch.value = null
    await matchingStore.matchPositionsForCandidate(selectedCandidateId.value)
  } catch {
    message.error('Reverse matching failed, please try again later')
  }
}

function viewDetail(match: CandidateMatchResultItem) {
  selectedMatch.value = match
}

function backToList() {
  selectedMatch.value = null
}

function getProgressBarColor(score: number): string {
  return tierMeta[getTier(score)].color
}
</script>

<template>
  <div class="reverse-matching-view">
    <template v-if="selectedMatch">
      <MatchDetailView
        :match-item="selectedMatch"
        @back="backToList"
      />
    </template>

    <template v-else>
      <header class="page-header">
        <div>
          <h2 class="header-title">Reverse Matching</h2>
          <p class="header-desc">Find the best positions for a candidate</p>
        </div>
      </header>

      <div class="match-controls">
        <NSelect
          v-model:value="selectedCandidateId"
          :options="candidateStore.candidates.map(c => ({
            label: c.name || `Candidate ${c.id.slice(0, 8)}`,
            value: c.id,
          }))"
          placeholder="Select a candidate"
          filterable
          style="width: 300px;"
        />
        <NButton
          type="primary"
          :disabled="!selectedCandidateId"
          :loading="matchingStore.loading"
          @click="handleReverseMatch"
        >
          Find Matching Positions
        </NButton>
      </div>

      <template v-if="sortedMatches.length">
        <div class="toolbar">
          <span class="result-count">{{ sortedMatches.length }} positions found</span>
        </div>

        <NSpin :show="matchingStore.loading">
          <NGrid :cols="1" :y-gap="10">
            <NGridItem v-for="match in sortedMatches" :key="match.position_id">
              <NCard size="small" class="match-row" hoverable @click="viewDetail(match)">
                <div class="match-row-inner">
                  <div class="match-row-score">
                    <MatchScore :score="match.overall_score" size="small" />
                  </div>
                  <div class="match-row-content">
                    <div class="match-row-header">
                      <span class="position-title">{{ match.position_title || 'Unknown Position' }}</span>
                      <NTag
                        size="small"
                        :bordered="false"
                        :color="{
                          color: tierMeta[getTier(match.overall_score)].color + '18',
                          textColor: tierMeta[getTier(match.overall_score)].color,
                        }"
                      >
                        {{ tierMeta[getTier(match.overall_score)].label }}
                      </NTag>
                    </div>

                    <div class="score-bar-row">
                      <span class="score-bar-label">Overall</span>
                      <NProgress
                        type="line"
                        :percentage="Math.round(match.overall_score * 100)"
                        :color="getProgressBarColor(match.overall_score)"
                        :height="14"
                        :border-radius="7"
                        :show-indicator="false"
                        style="flex: 1;"
                      />
                      <span class="score-bar-value">{{ Math.round(match.overall_score * 100) }}</span>
                    </div>

                    <div v-if="match.skill_score != null" class="score-bar-row sub-score">
                      <span class="score-bar-label">Skills</span>
                      <NProgress
                        type="line"
                        :percentage="Math.round(match.skill_score * 100)"
                        :color="getProgressBarColor(match.skill_score)"
                        :height="10"
                        :border-radius="5"
                        :show-indicator="false"
                        style="flex: 1;"
                      />
                      <span class="score-bar-value">{{ Math.round(match.skill_score * 100) }}</span>
                    </div>

                    <div v-if="match.matched_skills?.length" class="skills-row">
                      <NTag
                        v-for="skill in match.matched_skills.slice(0, 6)"
                        :key="skill"
                        size="tiny"
                        type="success"
                        style="margin-right: 4px;"
                      >
                        {{ skill }}
                      </NTag>
                      <NTag v-if="match.matched_skills.length > 6" size="tiny" style="margin-right: 4px;">
                        +{{ match.matched_skills.length - 6 }}
                      </NTag>
                    </div>

                    <div v-if="match.missing_skills?.length" class="missing-skills-row">
                      <span class="missing-label">Missing:</span>
                      <NTag
                        v-for="skill in match.missing_skills.slice(0, 4)"
                        :key="skill"
                        size="tiny"
                        type="error"
                        style="margin-right: 4px;"
                      >
                        {{ skill }}
                      </NTag>
                    </div>

                    <div v-if="match.explanation" class="match-explanation">
                      {{ match.explanation }}
                    </div>
                  </div>
                </div>
              </NCard>
            </NGridItem>
          </NGrid>
        </NSpin>
      </template>

      <NEmpty v-else description="Select a candidate to find matching positions" />
    </template>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.reverse-matching-view {
  padding: 24px;
}

.page-header {
  margin-bottom: 24px;

  .header-title {
    font-size: 22px;
    font-weight: 600;
    color: $text-primary;
    margin: 0 0 4px;
  }

  .header-desc {
    font-size: 14px;
    color: $text-muted;
    margin: 0;
  }
}

.match-controls {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;

  .result-count {
    font-size: 13px;
    color: $text-muted;
  }
}

.match-row {
  cursor: pointer;
  transition: box-shadow $transition-fast;

  &:hover {
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  }

  .match-row-inner {
    display: flex;
    gap: 16px;
  }

  .match-row-score {
    flex-shrink: 0;
    padding-top: 4px;
  }

  .match-row-content {
    flex: 1;
    min-width: 0;
  }

  .match-row-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
  }

  .position-title {
    font-weight: 600;
    font-size: 15px;
    color: $text-primary;
  }

  .score-bar-row {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 4px;

    .score-bar-label {
      font-size: 12px;
      color: $text-muted;
      min-width: 70px;
      text-align: right;
    }

    .score-bar-value {
      font-size: 12px;
      font-weight: 600;
      min-width: 30px;
      text-align: right;
      color: $text-secondary;
    }

    &.sub-score {
      .score-bar-label {
        font-size: 11px;
      }
      .score-bar-value {
        font-size: 11px;
      }
    }
  }

  .skills-row {
    margin-top: 8px;
  }

  .missing-skills-row {
    margin-top: 4px;
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 2px;

    .missing-label {
      font-size: 11px;
      color: $text-muted;
      margin-right: 4px;
    }
  }

  .match-explanation {
    margin-top: 8px;
    font-size: 13px;
    color: $text-muted;
    line-height: 1.5;
  }
}
</style>
