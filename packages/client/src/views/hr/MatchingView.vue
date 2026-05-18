<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import {
  NCard, NSelect, NButton, NSpin, NEmpty, NGrid, NGridItem, NProgress,
  NSpace, NTag, NInput, NRadioGroup, NRadioButton, NTooltip, useMessage,
} from 'naive-ui'
import { usePositionStore } from '@/stores/hr/positions'
import { useMatchingStore } from '@/stores/hr/matching'
import MatchScore from '@/components/hr/MatchScore.vue'
import MatchDetailView from '@/components/hr/MatchDetailView.vue'
import type { MatchResultItem, CandidateMatchResultItem } from '@/api/hr/matching'

type MatchItem = MatchResultItem | CandidateMatchResultItem

const positionStore = usePositionStore()
const matchingStore = useMatchingStore()
const selectedPositionId = ref<string | null>(null)
const message = useMessage()
const viewMode = ref<'list' | 'kanban'>('list')
const sortBy = ref<'score_desc' | 'score_asc' | 'name_asc'>('score_desc')
const filterTier = ref<'' | 'strong' | 'good' | 'fair' | 'poor'>('')
const searchKeyword = ref('')
const selectedMatch = ref<MatchItem | null>(null)

const batchProgress = ref(0)
const batchTotal = ref(0)
const batchRunning = ref(false)

onMounted(() => {
  positionStore.fetchPositions({ status: 'open' })
})

function getScore(item: MatchItem): number {
  return item.overall_score
}

function getName(item: MatchItem): string {
  if ('candidate_name' in item) return item.candidate_name || 'Unknown'
  if ('position_title' in item) return item.position_title || 'Unknown'
  return 'Unknown'
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

const sortedAndFiltered = computed(() => {
  let items = [...matchingStore.matches]

  if (searchKeyword.value) {
    const kw = searchKeyword.value.toLowerCase()
    items = items.filter(item => getName(item).toLowerCase().includes(kw))
  }

  if (filterTier.value) {
    items = items.filter(item => getTier(getScore(item)) === filterTier.value)
  }

  items.sort((a, b) => {
    switch (sortBy.value) {
      case 'score_desc': return getScore(b) - getScore(a)
      case 'score_asc': return getScore(a) - getScore(b)
      case 'name_asc': return getName(a).localeCompare(getName(b))
      default: return 0
    }
  })

  return items
})

const kanbanGroups = computed(() => {
  const groups: Record<string, MatchItem[]> = { strong: [], good: [], fair: [], poor: [] }
  sortedAndFiltered.value.forEach(item => {
    groups[getTier(getScore(item))].push(item)
  })
  return groups
})

async function handleMatch() {
  if (!selectedPositionId.value) return
  try {
    const result = await matchingStore.matchCandidatesForPosition(selectedPositionId.value)
    if (result.length === 0) {
      message.warning('No matching candidates found for this position')
    }
  } catch {
    message.error('Matching failed, please try again later')
  }
}

async function handleBatchMatch() {
  const positions = positionStore.positions
  if (!positions.length) return

  batchRunning.value = true
  batchProgress.value = 0
  batchTotal.value = positions.length

  for (let i = 0; i < positions.length; i++) {
    try {
      await matchingStore.matchCandidatesForPosition(positions[i].id)
    } catch {
      // continue with next
    }
    batchProgress.value = i + 1
  }

  batchRunning.value = false
  message.success(`Batch matching complete: ${positions.length} positions processed`)
}

function viewDetail(match: MatchItem) {
  selectedMatch.value = match
}

function backToList() {
  selectedMatch.value = null
}

function getProgressBarColor(score: number): string {
  return tierMeta[getTier(score)].color
}

function getMatchedSkills(item: MatchItem): string[] {
  return ('matched_skills' in item && item.matched_skills) ? item.matched_skills : []
}

function getMissingSkills(item: MatchItem): string[] {
  return ('missing_skills' in item && item.missing_skills) ? item.missing_skills : []
}

function getExplanation(item: MatchItem): string | null {
  return item.explanation ?? null
}

const sortOptions = [
  { label: 'Score ↓', value: 'score_desc' },
  { label: 'Score ↑', value: 'score_asc' },
  { label: 'Name A-Z', value: 'name_asc' },
]

const tierFilterOptions = [
  { label: 'All', value: '' },
  { label: 'Strong (>80)', value: 'strong' },
  { label: 'Good (60-80)', value: 'good' },
  { label: 'Fair (40-60)', value: 'fair' },
  { label: 'Poor (<40)', value: 'poor' },
]

function getItemKey(item: MatchItem): string {
  if ('candidate_id' in item) return item.candidate_id
  return item.position_id
}
</script>

<template>
  <div class="matching-view">
    <template v-if="selectedMatch">
      <MatchDetailView
        :match-item="selectedMatch"
        :position-title="positionStore.positions.find(p => p.id === selectedPositionId)?.title"
        @back="backToList"
      />
    </template>

    <template v-else>
      <header class="page-header">
        <div>
          <h2 class="header-title">Smart Matching</h2>
          <p class="header-desc">AI-powered position-candidate matching matrix</p>
        </div>
      </header>

      <div class="match-controls">
        <NSelect
          v-model:value="selectedPositionId"
          :options="positionStore.positions.map(p => ({ label: p.title, value: p.id }))"
          placeholder="Select an open position"
          style="width: 300px;"
        />
        <NButton type="primary" :disabled="!selectedPositionId" :loading="matchingStore.loading && !batchRunning" @click="handleMatch">
          Start Matching
        </NButton>
        <NButton :disabled="!positionStore.positions.length || batchRunning" :loading="batchRunning" @click="handleBatchMatch">
          Batch Match All
        </NButton>
      </div>

      <div v-if="batchRunning" class="batch-progress">
        <div class="batch-progress-header">
          <span class="batch-progress-label">Batch matching in progress...</span>
          <span class="batch-progress-count">{{ batchProgress }} / {{ batchTotal }}</span>
        </div>
        <NProgress
          type="line"
          :percentage="batchTotal > 0 ? Math.round((batchProgress / batchTotal) * 100) : 0"
          :height="20"
          :border-radius="10"
          indicator-placement="inside"
        />
      </div>

      <template v-if="matchingStore.matches.length">
        <div class="toolbar">
          <div class="toolbar-left">
            <NRadioGroup v-model:value="viewMode" size="small">
              <NRadioButton value="list">List</NRadioButton>
              <NRadioButton value="kanban">Kanban</NRadioButton>
            </NRadioGroup>

            <NSelect
              v-model:value="sortBy"
              :options="sortOptions"
              size="small"
              style="width: 130px;"
            />

            <NSelect
              v-model:value="filterTier"
              :options="tierFilterOptions"
              size="small"
              style="width: 140px;"
            />

            <NInput
              v-model:value="searchKeyword"
              placeholder="Search name..."
              clearable
              size="small"
              style="width: 180px;"
            />
          </div>

          <span class="result-count">{{ sortedAndFiltered.length }} results</span>
        </div>

        <NSpin :show="matchingStore.loading && !batchRunning">
          <!-- LIST VIEW -->
          <div v-if="viewMode === 'list'" class="list-view">
            <NGrid :cols="1" :y-gap="10">
              <NGridItem v-for="match in sortedAndFiltered" :key="getItemKey(match)">
                <NCard size="small" class="match-row" hoverable @click="viewDetail(match)">
                  <div class="match-row-inner">
                    <div class="match-row-score">
                      <MatchScore :score="getScore(match)" size="small" />
                    </div>
                    <div class="match-row-content">
                      <div class="match-row-header">
                        <span class="candidate-name">{{ getName(match) }}</span>
                        <NTag
                          size="small"
                          :bordered="false"
                          :color="{ color: tierMeta[getTier(getScore(match))].color + '18', textColor: tierMeta[getTier(getScore(match))].color }"
                        >
                          {{ tierMeta[getTier(getScore(match))].label }}
                        </NTag>
                      </div>

                      <div class="score-bar-row">
                        <span class="score-bar-label">Overall</span>
                        <NProgress
                          type="line"
                          :percentage="Math.round(getScore(match) * 100)"
                          :color="getProgressBarColor(getScore(match))"
                          :height="14"
                          :border-radius="7"
                          :show-indicator="false"
                          style="flex: 1;"
                        />
                        <span class="score-bar-value">{{ Math.round(getScore(match) * 100) }}</span>
                      </div>

                      <div v-if="'skill_score' in match && match.skill_score != null" class="score-bar-row sub-score">
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

                      <div v-if="'experience_score' in match && match.experience_score != null" class="score-bar-row sub-score">
                        <span class="score-bar-label">Experience</span>
                        <NProgress
                          type="line"
                          :percentage="Math.round(match.experience_score * 100)"
                          :color="getProgressBarColor(match.experience_score)"
                          :height="10"
                          :border-radius="5"
                          :show-indicator="false"
                          style="flex: 1;"
                        />
                        <span class="score-bar-value">{{ Math.round(match.experience_score * 100) }}</span>
                      </div>

                      <div v-if="'education_score' in match && match.education_score != null" class="score-bar-row sub-score">
                        <span class="score-bar-label">Education</span>
                        <NProgress
                          type="line"
                          :percentage="Math.round(match.education_score * 100)"
                          :color="getProgressBarColor(match.education_score)"
                          :height="10"
                          :border-radius="5"
                          :show-indicator="false"
                          style="flex: 1;"
                        />
                        <span class="score-bar-value">{{ Math.round(match.education_score * 100) }}</span>
                      </div>

                      <div v-if="getMatchedSkills(match).length" class="skills-row">
                        <NTag v-for="skill in getMatchedSkills(match).slice(0, 6)" :key="skill" size="tiny" type="success" style="margin-right: 4px;">
                          {{ skill }}
                        </NTag>
                        <NTag v-if="getMatchedSkills(match).length > 6" size="tiny" style="margin-right: 4px;">
                          +{{ getMatchedSkills(match).length - 6 }}
                        </NTag>
                      </div>

                      <div v-if="getMissingSkills(match).length" class="missing-skills-row">
                        <span class="missing-label">Missing:</span>
                        <NTag v-for="skill in getMissingSkills(match).slice(0, 4)" :key="skill" size="tiny" type="error" style="margin-right: 4px;">
                          {{ skill }}
                        </NTag>
                        <NTag v-if="getMissingSkills(match).length > 4" size="tiny" style="margin-right: 4px;">
                          +{{ getMissingSkills(match).length - 4 }}
                        </NTag>
                      </div>

                      <div v-if="getExplanation(match)" class="match-explanation">
                        {{ getExplanation(match) }}
                      </div>

                      <div class="match-row-actions">
                        <NButton text size="tiny" type="primary" @click.stop="viewDetail(match)">
                          View Detail →
                        </NButton>
                      </div>
                    </div>
                  </div>
                </NCard>
              </NGridItem>
            </NGrid>
          </div>

          <!-- KANBAN VIEW -->
          <div v-else class="kanban-view">
            <div v-for="tier in (['strong', 'good', 'fair', 'poor'] as const)" :key="tier" class="kanban-column">
              <div class="kanban-column-header" :style="{ borderTopColor: tierMeta[tier].color }">
                <span class="kanban-column-title" :style="{ color: tierMeta[tier].color }">
                  {{ tierMeta[tier].label }}
                </span>
                <span class="kanban-column-count">{{ kanbanGroups[tier].length }}</span>
              </div>
              <div class="kanban-column-body">
                <NCard
                  v-for="match in kanbanGroups[tier]"
                  :key="getItemKey(match)"
                  size="small"
                  class="kanban-card"
                  hoverable
                  @click="viewDetail(match)"
                >
                  <div class="kanban-card-header">
                    <span class="kanban-card-name">{{ getName(match) }}</span>
                    <NTooltip>
                      <template #trigger>
                        <span class="kanban-card-score" :style="{ color: tierMeta[tier].color }">
                          {{ Math.round(getScore(match) * 100) }}
                        </span>
                      </template>
                      Overall: {{ Math.round(getScore(match) * 100) }}%
                    </NTooltip>
                  </div>
                  <NProgress
                    type="line"
                    :percentage="Math.round(getScore(match) * 100)"
                    :color="tierMeta[tier].color"
                    :height="8"
                    :border-radius="4"
                    :show-indicator="false"
                    style="margin-bottom: 8px;"
                  />
                  <div v-if="'skill_score' in match && match.skill_score != null" class="kanban-sub-score">
                    <span>Skills: {{ Math.round(match.skill_score * 100) }}</span>
                    <NProgress
                      type="line"
                      :percentage="Math.round(match.skill_score * 100)"
                      :color="tierMeta[tier].color"
                      :height="6"
                      :border-radius="3"
                      :show-indicator="false"
                      style="flex: 1;"
                    />
                  </div>
                  <div v-if="getMatchedSkills(match).length" class="kanban-skills">
                    <NTag v-for="skill in getMatchedSkills(match).slice(0, 3)" :key="skill" size="tiny" type="success" style="margin: 2px;">
                      {{ skill }}
                    </NTag>
                    <NTag v-if="getMatchedSkills(match).length > 3" size="tiny" style="margin: 2px;">
                      +{{ getMatchedSkills(match).length - 3 }}
                    </NTag>
                  </div>
                </NCard>
                <NEmpty v-if="!kanbanGroups[tier].length" description="-" size="small" />
              </div>
            </div>
          </div>
        </NSpin>
      </template>

      <NEmpty v-else description="Select a position and click match to see results" />
    </template>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.matching-view {
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

.batch-progress {
  margin-bottom: 20px;

  .batch-progress-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 6px;
  }

  .batch-progress-label {
    font-size: 13px;
    color: $text-secondary;
  }

  .batch-progress-count {
    font-size: 13px;
    font-weight: 600;
    color: $text-primary;
  }
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 10px;

  .toolbar-left {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
  }

  .result-count {
    font-size: 13px;
    color: $text-muted;
  }
}

.list-view {
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

    .candidate-name {
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
          min-width: 70px;
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

    .match-row-actions {
      margin-top: 8px;
    }
  }
}

.kanban-view {
  display: flex;
  gap: 12px;
  overflow-x: auto;
  padding-bottom: 8px;

  .kanban-column {
    flex: 1;
    min-width: 240px;
    max-width: 320px;
    background: $bg-secondary;
    border-radius: $radius-md;
    display: flex;
    flex-direction: column;
  }

  .kanban-column-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 12px;
    border-top: 3px solid;
    border-radius: $radius-md $radius-md 0 0;

    .kanban-column-title {
      font-weight: 600;
      font-size: 14px;
    }

    .kanban-column-count {
      font-size: 12px;
      color: $text-muted;
      background: $bg-card;
      border-radius: 10px;
      padding: 1px 8px;
    }
  }

  .kanban-column-body {
    padding: 8px;
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .kanban-card {
    cursor: pointer;
    transition: box-shadow $transition-fast;

    &:hover {
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    }

    .kanban-card-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 6px;
    }

    .kanban-card-name {
      font-weight: 600;
      font-size: 14px;
      color: $text-primary;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .kanban-card-score {
      font-weight: 700;
      font-size: 18px;
    }

    .kanban-sub-score {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 11px;
      color: $text-muted;
      margin-bottom: 4px;
    }

    .kanban-skills {
      display: flex;
      flex-wrap: wrap;
      gap: 0;
    }
  }
}
</style>
