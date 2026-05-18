<script setup lang="ts">
/**
 * TalentActivationView — M10 人才库智能激活页
 *
 * 统计 + 筛选 + 候选人列表 + 激活策略弹窗 + 批量激活
 */
import { ref, computed, onMounted, h } from 'vue'
import {
  NCard, NGrid, NGridItem, NDataTable, NTag, NButton, NInput, NSelect,
  NSpace, NModal, NProgress, NEmpty, NSpin, NPopconfirm, useMessage,
} from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import {
  fetchTalentActivation, activateTalent, batchActivate,
  fetchActivationStats, fetchActivationStrategies,
} from '@/api/hr/proactive'
import type {
  SilentCandidate, ActivationStrategy, ActivationStats,
  TalentActivationFilters,
} from '@/api/hr/proactive'

const message = useMessage()

// ── Config ──────────────────────────────────────────────────

const SILENT_OPTIONS = [
  { label: '全部', value: 0 },
  { label: '> 30天', value: 30 },
  { label: '> 60天', value: 60 },
  { label: '> 90天', value: 90 },
]

const DIRECTION_OPTIONS = [
  { label: '全部方向', value: '' },
  { label: '前端开发', value: 'frontend' },
  { label: '后端开发', value: 'backend' },
  { label: '全栈开发', value: 'fullstack' },
  { label: '数据分析', value: 'data' },
  { label: '产品经理', value: 'pm' },
  { label: 'UI设计', value: 'design' },
  { label: '运维/DevOps', value: 'devops' },
]

// ── State ───────────────────────────────────────────────────

const loading = ref(false)
const candidates = ref<SilentCandidate[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const stats = ref<ActivationStats | null>(null)
const strategies = ref<ActivationStrategy[]>([])

// Filters
const filterSilentDays = ref(0)
const filterDirection = ref('')
const filterSkills = ref('')

// Strategy detail modal
const showStrategyModal = ref(false)
const selectedCandidate = ref<SilentCandidate | null>(null)
const candidateStrategy = ref<ActivationStrategy | null>(null)
const activating = ref(false)

// Batch
const checkedKeys = ref<string[]>([])
const batchActivating = ref(false)

// ── Computed ────────────────────────────────────────────────

const statCards = computed(() => {
  const s = stats.value
  return [
    { label: '沉默候选人', value: s?.silent_count ?? '-', icon: '💤', color: '#f0a020' },
    { label: '已激活', value: s?.activated_count ?? '-', icon: '✅', color: '#18a058' },
    {
      label: '激活成功率',
      value: s?.success_rate ? `${(s.success_rate * 100).toFixed(1)}%` : '-',
      icon: '📈',
      color: '#4a90d9',
    },
  ]
})

// ── Table Columns ───────────────────────────────────────────

const columns: DataTableColumns<SilentCandidate> = [
  { type: 'selection' },
  {
    title: '姓名',
    key: 'name',
    width: 140,
    render: (row) => h(NSpace, { align: 'center', size: 'small' }, () => [
      h('div', {
        style: {
          width: '28px', height: '28px', borderRadius: '50%',
          background: '#4a90d920', color: '#4a90d9',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: '12px', fontWeight: '600',
        },
      }, row.name.charAt(0)),
      h('span', { style: 'font-weight: 500' }, row.name),
    ]),
  },
  {
    title: '沉默天数',
    key: 'silent_days',
    width: 100,
    sorter: (a, b) => a.silent_days - b.silent_days,
    render: (row) => h(NTag, {
      size: 'small',
      type: row.silent_days > 90 ? 'error' : row.silent_days > 60 ? 'warning' : 'info',
    }, () => `${row.silent_days}天`),
  },
  {
    title: '匹配岗位',
    key: 'match_position_count',
    width: 90,
    render: (row) => h('span', {
      style: { fontWeight: '500', color: row.match_position_count > 0 ? '#18a058' : '#6b7280' },
    }, `${row.match_position_count}个`),
  },
  {
    title: '岗位方向',
    key: 'position_direction',
    width: 100,
    render: (row) => h(NTag, { size: 'small' }, () => row.position_direction || '-'),
  },
  {
    title: '技能',
    key: 'skills',
    width: 180,
    render: (row) => h(NSpace, { size: 4 }, () =>
      row.skills.slice(0, 3).map(s => h(NTag, { size: 'tiny' }, () => s)),
    ),
  },
  {
    title: '推荐策略',
    key: 'recommended_strategy',
    width: 140,
    ellipsis: { tooltip: true },
  },
  {
    title: '操作',
    key: 'actions',
    width: 120,
    render: (row) => h(NSpace, { size: 'small' }, () => [
      h(NButton, { size: 'tiny', type: 'primary', onClick: () => openStrategy(row) }, () => '激活'),
      h(NButton, { size: 'tiny', onClick: () => quickActivate(row) }, () => '快速'),
    ]),
  },
]

// ── Data Loading ────────────────────────────────────────────

onMounted(async () => {
  await Promise.allSettled([loadStats(), loadCandidates(), loadStrategies()])
})

async function loadStats() {
  try {
    stats.value = await fetchActivationStats()
  } catch {
    message.error('加载激活统计失败')
  }
}

async function loadCandidates() {
  loading.value = true
  try {
    const filters: TalentActivationFilters = {
      page: page.value,
      page_size: pageSize.value,
    }
    if (filterSilentDays.value) filters.silent_days_min = filterSilentDays.value
    if (filterDirection.value) filters.position_direction = filterDirection.value
    if (filterSkills.value) filters.skills = filterSkills.value

    const res = await fetchTalentActivation(filters)
    candidates.value = res.items
    total.value = res.total
  } catch {
    message.error('加载候选人列表失败')
  } finally {
    loading.value = false
  }
}

async function loadStrategies() {
  try {
    strategies.value = await fetchActivationStrategies()
  } catch {
    // Ignore - strategies might not be available
  }
}

// ── Handlers ────────────────────────────────────────────────

function handleSearch() {
  page.value = 1
  loadCandidates()
}

function handlePageChange(p: number) {
  page.value = p
  loadCandidates()
}

function handlePageSizeChange(size: number) {
  pageSize.value = size
  page.value = 1
  loadCandidates()
}

function openStrategy(candidate: SilentCandidate) {
  selectedCandidate.value = candidate
  // Find matching strategy
  const matched = strategies.value.find(s => s.id === candidate.strategy_id)
  if (matched) {
    candidateStrategy.value = matched
  } else {
    candidateStrategy.value = {
      id: candidate.strategy_id,
      name: candidate.recommended_strategy,
      description: '',
      match_score: 0.7,
      recommended_message: `您好，我们注意到您有匹配的技能。近期有新的岗位机会，感兴趣吗？`,
      best_contact_time: '工作日 10:00-11:00',
      channel: '邮件',
    }
  }
  showStrategyModal.value = true
}

async function handleActivate() {
  if (!selectedCandidate.value || !candidateStrategy.value) return
  activating.value = true
  try {
    await activateTalent(selectedCandidate.value.candidate_id, candidateStrategy.value.id)
    message.success(`已激活候选人 ${selectedCandidate.value.name}`)
    showStrategyModal.value = false
    loadCandidates()
    loadStats()
  } catch {
    message.error('激活失败')
  } finally {
    activating.value = false
  }
}

async function quickActivate(candidate: SilentCandidate) {
  try {
    await activateTalent(candidate.candidate_id, candidate.strategy_id)
    message.success(`已快速激活 ${candidate.name}`)
    loadCandidates()
    loadStats()
  } catch {
    message.error('激活失败')
  }
}

function handleCheckedChange(keys: string[]) {
  checkedKeys.value = keys
}

async function handleBatchActivate() {
  if (!checkedKeys.value.length) { message.warning('请先选择候选人'); return }
  batchActivating.value = true
  try {
    const items = checkedKeys.value.map(id => {
      const c = candidates.value.find(c => c.id === id)
      return { candidate_id: c?.candidate_id || id, strategy_id: c?.strategy_id || '' }
    })
    const res = await batchActivate(items)
    message.success(`批量激活完成: 成功 ${res.success_count}, 失败 ${res.fail_count}`)
    checkedKeys.value = []
    loadCandidates()
    loadStats()
  } catch {
    message.error('批量激活失败')
  } finally {
    batchActivating.value = false
  }
}
</script>

<template>
  <div class="talent-activation-view">
    <header class="page-header">
      <div class="header-row">
        <div>
          <h2 class="header-title">人才库智能激活</h2>
          <p class="header-desc">发现沉默候选人，推荐激活策略</p>
        </div>
        <NSpace>
          <NButton
            v-if="checkedKeys.length"
            type="primary"
            :loading="batchActivating"
            @click="handleBatchActivate"
          >
            🚀 批量激活 ({{ checkedKeys.length }})
          </NButton>
        </NSpace>
      </div>
    </header>

    <!-- ═══ Statistics Cards ═══ -->
    <NGrid :cols="3" :x-gap="12" :y-gap="12" responsive="screen" item-responsive>
      <NGridItem v-for="card in statCards" :key="card.label" span="0:3 640:1">
        <NCard size="small" class="stat-card">
          <div class="stat-inner">
            <div class="stat-icon" :style="{ background: `${card.color}15`, color: card.color }">
              {{ card.icon }}
            </div>
            <div class="stat-info">
              <div class="stat-label">{{ card.label }}</div>
              <div class="stat-value">{{ card.value }}</div>
            </div>
          </div>
        </NCard>
      </NGridItem>
    </NGrid>

    <!-- ═══ Filters ═══ -->
    <div class="filter-bar">
      <NSelect
        v-model:value="filterSilentDays"
        :options="SILENT_OPTIONS"
        style="width: 130px;"
        @update:value="handleSearch"
      />
      <NSelect
        v-model:value="filterDirection"
        :options="DIRECTION_OPTIONS"
        style="width: 140px;"
        @update:value="handleSearch"
      />
      <NInput
        v-model:value="filterSkills"
        placeholder="技能关键词..."
        clearable
        style="width: 200px;"
        @keyup.enter="handleSearch"
      />
      <NButton @click="handleSearch">搜索</NButton>
    </div>

    <!-- ═══ Candidate Table ═══ -->
    <NSpin :show="loading">
      <NDataTable
        :columns="columns"
        :data="candidates"
        :row-key="(row: SilentCandidate) => row.id"
        :checked-row-keys="checkedKeys"
        @update:checked-row-keys="handleCheckedChange"
        :pagination="{
          page: page,
          pageSize: pageSize,
          itemCount: total,
          pageSizes: [10, 20, 50],
          showSizePicker: true,
          onChange: handlePageChange,
          onUpdatePageSize: handlePageSizeChange,
        }"
        :scroll-x="1000"
        striped
      />
    </NSpin>

    <!-- ═══ Strategy Detail Modal ═══ -->
    <NModal v-model:show="showStrategyModal" preset="dialog" title="激活策略详情" style="width: 520px;">
      <template v-if="selectedCandidate && candidateStrategy">
        <div class="strategy-section">
          <div class="strategy-label">候选人</div>
          <div class="strategy-candidate">
            <span class="candidate-avatar">{{ selectedCandidate.name.charAt(0) }}</span>
            <div>
              <div class="candidate-name">{{ selectedCandidate.name }}</div>
              <div class="candidate-meta">沉默 {{ selectedCandidate.silent_days }} 天 · {{ selectedCandidate.match_position_count }} 个匹配岗位</div>
            </div>
          </div>
        </div>

        <div class="strategy-section">
          <div class="strategy-label">匹配度</div>
          <NProgress
            type="line"
            :percentage="Math.round(candidateStrategy.match_score * 100)"
            :color="candidateStrategy.match_score >= 0.7 ? '#18a058' : '#f0a020'"
            indicator-placement="inside"
            style="margin-top: 4px;"
          />
        </div>

        <div class="strategy-section">
          <div class="strategy-label">推荐话术</div>
          <div class="strategy-message">{{ candidateStrategy.recommended_message }}</div>
        </div>

        <div class="strategy-section">
          <div class="strategy-label">联系时机</div>
          <div class="strategy-meta">{{ candidateStrategy.best_contact_time }}</div>
        </div>

        <div class="strategy-section">
          <div class="strategy-label">推荐渠道</div>
          <NTag size="small">{{ candidateStrategy.channel }}</NTag>
        </div>

        <div v-if="selectedCandidate.skills.length" class="strategy-section">
          <div class="strategy-label">技能标签</div>
          <NSpace size="small">
            <NTag v-for="skill in selectedCandidate.skills" :key="skill" size="small" type="info">{{ skill }}</NTag>
          </NSpace>
        </div>
      </template>
      <template #action>
        <NSpace>
          <NButton @click="showStrategyModal = false">取消</NButton>
          <NButton type="primary" :loading="activating" @click="handleActivate">🚀 一键激活</NButton>
        </NSpace>
      </template>
    </NModal>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.talent-activation-view {
  padding: 24px;
}

.page-header {
  margin-bottom: 20px;

  .header-row {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
  }

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

.stat-card {
  transition: transform $transition-fast;

  &:hover {
    transform: translateY(-1px);
  }
}

.stat-inner {
  display: flex;
  align-items: center;
  gap: 12px;
}

.stat-icon {
  font-size: 24px;
  width: 42px;
  height: 42px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: $radius-md;
  flex-shrink: 0;
}

.stat-label {
  font-size: 13px;
  color: $text-muted;
  margin-bottom: 2px;
}

.stat-value {
  font-size: 22px;
  font-weight: 700;
  color: $text-primary;
}

.filter-bar {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

// Strategy modal
.strategy-section {
  margin-bottom: 18px;
}

.strategy-label {
  font-size: 13px;
  font-weight: 600;
  color: $text-secondary;
  margin-bottom: 8px;
}

.strategy-candidate {
  display: flex;
  align-items: center;
  gap: 12px;
}

.candidate-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #4a90d920;
  color: #4a90d9;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 16px;
  flex-shrink: 0;
}

.candidate-name {
  font-size: 16px;
  font-weight: 600;
  color: $text-primary;
}

.candidate-meta {
  font-size: 13px;
  color: $text-muted;
  margin-top: 2px;
}

.strategy-message {
  font-size: 14px;
  color: $text-primary;
  line-height: 1.6;
  padding: 12px;
  background: $bg-primary;
  border-radius: $radius-sm;
  border-left: 3px solid #4a90d9;
}

.strategy-meta {
  font-size: 14px;
  color: $text-primary;
}
</style>
