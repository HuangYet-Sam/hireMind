<script setup lang="ts">
/**
 * MemoryManagerView — M10 AI记忆管理页
 *
 * 统计面板 + 筛选 + 记忆列表 + 详情抽屉 + 创建/编辑弹窗 + 批量操作
 */
import { ref, computed, onMounted, h } from 'vue'
import {
  NCard, NGrid, NGridItem, NDataTable, NTag, NButton, NInput, NSelect,
  NSpace, NDrawer, NDrawerContent, NModal, NForm, NFormItem, NDatePicker,
  NProgress, NEmpty, NSpin, NPopconfirm, NCheckbox, useMessage,
} from 'naive-ui'
import type { DataTableColumns, FormInst } from 'naive-ui'
import {
  fetchMemories, createMemory, updateMemory, deleteMemory,
  searchMemories, getMemoryStats, triggerMemoryBuild, consolidateMemories,
  batchDeleteMemories, batchExpireMemories,
} from '@/api/hr/memories'
import type {
  Memory, MemoryType, MemoryCategory, MemoryFilters,
  MemoryFormData, MemoryStats,
} from '@/api/hr/memories'

const message = useMessage()

// ── Types & Color Maps ──────────────────────────────────────

const TYPE_OPTIONS = [
  { label: '全部类型', value: '' },
  { label: '偏好', value: 'preference' },
  { label: '洞察', value: 'insight' },
  { label: '决策', value: 'decision' },
  { label: '模式', value: 'pattern' },
  { label: '事实', value: 'fact' },
]

const CATEGORY_OPTIONS = [
  { label: '全部分类', value: '' },
  { label: '招聘', value: 'recruitment' },
  { label: '候选人', value: 'candidate' },
  { label: '面试', value: 'interview' },
  { label: 'Offer', value: 'offer' },
  { label: '团队', value: 'team' },
  { label: '流程', value: 'process' },
  { label: '通用', value: 'general' },
]

const IMPORTANCE_OPTIONS = [
  { label: '全部', value: '' },
  { label: '低', value: 'low' },
  { label: '中', value: 'medium' },
  { label: '高', value: 'high' },
  { label: '关键', value: 'critical' },
]

const TYPE_COLOR: Record<MemoryType, string> = {
  preference: '#4a90d9',
  insight: '#18a058',
  decision: '#f0a020',
  pattern: '#8b5cf6',
  fact: '#6b7280',
}

const TYPE_TAG_TYPE: Record<MemoryType, 'info' | 'success' | 'warning' | 'default'> = {
  preference: 'info',
  insight: 'success',
  decision: 'warning',
  pattern: 'default',
  fact: 'default',
}

const TYPE_LABEL: Record<MemoryType, string> = {
  preference: '偏好',
  insight: '洞察',
  decision: '决策',
  pattern: '模式',
  fact: '事实',
}

const CATEGORY_LABEL: Record<string, string> = {
  recruitment: '招聘',
  candidate: '候选人',
  interview: '面试',
  offer: 'Offer',
  team: '团队',
  process: '流程',
  general: '通用',
}

const IMPORTANCE_LABEL: Record<string, string> = {
  low: '低',
  medium: '中',
  high: '高',
  critical: '关键',
}

// ── State ───────────────────────────────────────────────────

const loading = ref(false)
const memories = ref<Memory[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const stats = ref<MemoryStats | null>(null)

// Filters
const filterType = ref<string>('')
const filterCategory = ref<string>('')
const filterKeyword = ref('')
const filterDateRange = ref<[number, number] | null>(null)

// Detail drawer
const showDrawer = ref(false)
const currentMemory = ref<Memory | null>(null)
const relatedMemories = ref<Memory[]>([])

// Create/Edit modal
const showModal = ref(false)
const editingId = ref<string | null>(null)
const formRef = ref<FormInst | null>(null)
const formData = ref<MemoryFormData>({
  content: '',
  summary: '',
  type: 'fact',
  category: 'general',
  importance: 'medium',
  tags: [],
})

// Batch
const checkedKeys = ref<string[]>([])
const showBatchMenu = ref(false)

// ── Computed ────────────────────────────────────────────────

const typeDistribution = computed(() => {
  if (!stats.value) return []
  return Object.entries(stats.value.by_type).map(([type, count]) => ({
    type: type as MemoryType,
    label: TYPE_LABEL[type as MemoryType],
    count,
    color: TYPE_COLOR[type as MemoryType],
  }))
})

const categoryDistribution = computed(() => {
  if (!stats.value) return []
  return Object.entries(stats.value.by_category).map(([cat, count]) => ({
    category: cat as MemoryCategory,
    label: CATEGORY_LABEL[cat] || cat,
    count,
  }))
})

const statCards = computed(() => {
  const s = stats.value
  return [
    { label: '记忆总数', value: s?.total ?? '-', icon: '🧠', color: '#4a90d9' },
    { label: '已过期', value: s?.expired_count ?? '-', icon: '⏰', color: '#d03050' },
    { label: '平均置信度', value: s?.avg_confidence ? `${(s.avg_confidence * 100).toFixed(1)}%` : '-', icon: '📊', color: '#18a058' },
    { label: '近期新增', value: s?.recent_count ?? '-', icon: '📈', color: '#f0a020' },
  ]
})

// ── Table Columns ───────────────────────────────────────────

const columns: DataTableColumns<Memory> = [
  { type: 'selection' },
  {
    title: '内容摘要',
    key: 'summary',
    width: 260,
    ellipsis: { tooltip: true },
  },
  {
    title: '类型',
    key: 'type',
    width: 90,
    render: (row) => h(NTag, {
      size: 'small',
      type: TYPE_TAG_TYPE[row.type],
      color: { color: TYPE_COLOR[row.type] + '20', textColor: TYPE_COLOR[row.type], borderColor: TYPE_COLOR[row.type] + '40' },
    }, () => TYPE_LABEL[row.type]),
  },
  {
    title: '分类',
    key: 'category',
    width: 80,
    render: (row) => h(NTag, { size: 'small' }, () => CATEGORY_LABEL[row.category] || row.category),
  },
  {
    title: '来源',
    key: 'source',
    width: 100,
    ellipsis: { tooltip: true },
  },
  {
    title: '置信度',
    key: 'confidence',
    width: 120,
    render: (row) => h(NProgress, {
      type: 'line',
      percentage: Math.round(row.confidence * 100),
      indicatorPlacement: 'inside',
      height: 16,
      color: row.confidence >= 0.8 ? '#18a058' : row.confidence >= 0.5 ? '#f0a020' : '#d03050',
    }),
  },
  {
    title: '重要性',
    key: 'importance',
    width: 70,
    render: (row) => h(NTag, {
      size: 'small',
      type: row.importance === 'critical' ? 'error' : row.importance === 'high' ? 'warning' : 'default',
    }, () => IMPORTANCE_LABEL[row.importance] || row.importance),
  },
  {
    title: '访问',
    key: 'access_count',
    width: 60,
  },
  {
    title: '操作',
    key: 'actions',
    width: 140,
    render: (row) => h(NSpace, { size: 'small' }, () => [
      h(NButton, { size: 'tiny', onClick: () => openDetail(row.id) }, () => '详情'),
      h(NButton, { size: 'tiny', onClick: () => openEdit(row) }, () => '编辑'),
      h(NPopconfirm, { onPositiveClick: () => handleDelete(row.id) }, {
        trigger: () => h(NButton, { size: 'tiny', type: 'error', ghost: true }, () => '删除'),
        default: () => '确定删除该记忆？',
      }),
    ]),
  },
]

// ── Data Loading ────────────────────────────────────────────

onMounted(async () => {
  await Promise.allSettled([loadStats(), loadMemories()])
})

async function loadStats() {
  try {
    stats.value = await getMemoryStats()
  } catch {
    message.error('加载记忆统计失败')
  }
}

async function loadMemories() {
  loading.value = true
  try {
    const filters: MemoryFilters = {
      page: page.value,
      page_size: pageSize.value,
    }
    if (filterType.value) filters.type = filterType.value as MemoryType
    if (filterCategory.value) filters.category = filterCategory.value as MemoryCategory
    if (filterKeyword.value) filters.keyword = filterKeyword.value
    if (filterDateRange.value) {
      filters.date_from = new Date(filterDateRange.value[0]).toISOString()
      filters.date_to = new Date(filterDateRange.value[1]).toISOString()
    }
    const res = await fetchMemories(filters)
    memories.value = res.items
    total.value = res.total
  } catch {
    message.error('加载记忆列表失败')
  } finally {
    loading.value = false
  }
}

// ── Handlers ────────────────────────────────────────────────

function handleSearch() {
  page.value = 1
  loadMemories()
}

function handlePageChange(p: number) {
  page.value = p
  loadMemories()
}

function handlePageSizeChange(size: number) {
  pageSize.value = size
  page.value = 1
  loadMemories()
}

async function openDetail(id: string) {
  try {
    const mem = memories.value.find(m => m.id === id) || await getMemory(id)
    currentMemory.value = mem
    showDrawer.value = true
    // Load related memories
    if (mem.related_memory_ids?.length) {
      const searchRes = await searchMemories({ query: mem.summary, limit: 5 })
      relatedMemories.value = searchRes.items.filter(m => m.id !== id)
    } else {
      relatedMemories.value = []
    }
  } catch {
    message.error('加载记忆详情失败')
  }
}

function openCreate() {
  editingId.value = null
  formData.value = {
    content: '',
    summary: '',
    type: 'fact',
    category: 'general',
    importance: 'medium',
    tags: [],
  }
  showModal.value = true
}

function openEdit(mem: Memory) {
  editingId.value = mem.id
  formData.value = {
    content: mem.content,
    summary: mem.summary,
    type: mem.type,
    category: mem.category,
    importance: mem.importance,
    tags: mem.tags,
  }
  showModal.value = true
}

async function handleSave() {
  try {
    if (editingId.value) {
      await updateMemory(editingId.value, formData.value)
      message.success('记忆更新成功')
    } else {
      await createMemory(formData.value)
      message.success('记忆创建成功')
    }
    showModal.value = false
    loadMemories()
    loadStats()
  } catch {
    message.error('保存失败')
  }
}

async function handleDelete(id: string) {
  try {
    await deleteMemory(id)
    message.success('删除成功')
    loadMemories()
    loadStats()
  } catch {
    message.error('删除失败')
  }
}

async function handleColdStart() {
  try {
    const res = await triggerMemoryBuild()
    message.success(res.message || '冷启动任务已触发')
    loadStats()
  } catch {
    message.error('触发冷启动失败')
  }
}

async function handleConsolidate() {
  try {
    const res = await consolidateMemories()
    message.success(`合并完成，共合并 ${res.merged_count} 条记忆`)
    loadMemories()
    loadStats()
  } catch {
    message.error('合并失败')
  }
}

// Batch operations
async function handleBatchDelete() {
  if (!checkedKeys.value.length) { message.warning('请先选择记忆'); return }
  try {
    await batchDeleteMemories(checkedKeys.value)
    message.success(`已删除 ${checkedKeys.value.length} 条记忆`)
    checkedKeys.value = []
    loadMemories()
    loadStats()
  } catch {
    message.error('批量删除失败')
  }
}

async function handleBatchExpire() {
  if (!checkedKeys.value.length) { message.warning('请先选择记忆'); return }
  try {
    await batchExpireMemories(checkedKeys.value)
    message.success(`已标记 ${checkedKeys.value.length} 条为过期`)
    checkedKeys.value = []
    loadMemories()
  } catch {
    message.error('批量标记失败')
  }
}

function handleCheckedChange(keys: string[]) {
  checkedKeys.value = keys
}

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleString('zh-CN')
}
</script>

<template>
  <div class="memory-manager-view">
    <header class="page-header">
      <div class="header-row">
        <div>
          <h2 class="header-title">AI 记忆管理</h2>
          <p class="header-desc">管理 AI 的记忆、偏好和知识库</p>
        </div>
        <NSpace>
          <NButton @click="handleConsolidate" :disabled="loading">🔄 合并去重</NButton>
          <NButton type="warning" @click="handleColdStart" :disabled="loading">🚀 冷启动</NButton>
          <NButton type="primary" @click="openCreate">➕ 创建记忆</NButton>
        </NSpace>
      </div>
    </header>

    <!-- ═══ Statistics Cards ═══ -->
    <NGrid :cols="4" :x-gap="12" :y-gap="12" responsive="screen" item-responsive>
      <NGridItem v-for="card in statCards" :key="card.label" span="0:4 640:2 1024:1">
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

    <!-- Type Distribution -->
    <NGrid :cols="24" :x-gap="12" :y-gap="12" style="margin-top: 12px;">
      <NGridItem span="12">
        <NCard title="按类型分布" size="small">
          <div v-if="typeDistribution.length" class="distribution-bar">
            <div
              v-for="item in typeDistribution"
              :key="item.type"
              class="dist-item"
            >
              <span class="dist-dot" :style="{ background: item.color }" />
              <span class="dist-label">{{ item.label }}</span>
              <span class="dist-count">{{ item.count }}</span>
              <NProgress
                type="line"
                :percentage="stats ? (item.count / stats.total) * 100 : 0"
                :show-indicator="false"
                :color="item.color"
                :height="6"
                style="flex: 1; min-width: 60px;"
              />
            </div>
          </div>
          <NEmpty v-else description="暂无数据" size="small" />
        </NCard>
      </NGridItem>
      <NGridItem span="12">
        <NCard title="按分类分布" size="small">
          <div v-if="categoryDistribution.length" class="distribution-bar">
            <div
              v-for="item in categoryDistribution"
              :key="item.category"
              class="dist-item"
            >
              <span class="dist-dot" style="background: #4a90d9" />
              <span class="dist-label">{{ item.label }}</span>
              <span class="dist-count">{{ item.count }}</span>
              <NProgress
                type="line"
                :percentage="stats ? (item.count / stats.total) * 100 : 0"
                :show-indicator="false"
                color="#4a90d9"
                :height="6"
                style="flex: 1; min-width: 60px;"
              />
            </div>
          </div>
          <NEmpty v-else description="暂无数据" size="small" />
        </NCard>
      </NGridItem>
    </NGrid>

    <!-- ═══ Filters ═══ -->
    <div class="filter-bar">
      <NSelect
        v-model:value="filterType"
        :options="TYPE_OPTIONS"
        style="width: 130px;"
        @update:value="handleSearch"
      />
      <NSelect
        v-model:value="filterCategory"
        :options="CATEGORY_OPTIONS"
        style="width: 130px;"
        @update:value="handleSearch"
      />
      <NInput
        v-model:value="filterKeyword"
        placeholder="搜索记忆内容..."
        clearable
        style="width: 240px;"
        @keyup.enter="handleSearch"
      />
      <NDatePicker
        v-model:value="filterDateRange"
        type="daterange"
        clearable
        @update:value="handleSearch"
      />
      <NButton @click="handleSearch">搜索</NButton>

      <NSpace v-if="checkedKeys.length" style="margin-left: auto;">
        <NButton type="error" size="small" @click="handleBatchDelete">
          删除 ({{ checkedKeys.length }})
        </NButton>
        <NButton type="warning" size="small" @click="handleBatchExpire">
          标记过期 ({{ checkedKeys.length }})
        </NButton>
      </NSpace>
    </div>

    <!-- ═══ Memory Table ═══ -->
    <NSpin :show="loading">
      <NDataTable
        :columns="columns"
        :data="memories"
        :row-key="(row: Memory) => row.id"
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
        :scroll-x="1100"
        striped
      />
    </NSpin>

    <!-- ═══ Detail Drawer ═══ -->
    <NDrawer v-model:show="showDrawer" :width="520" placement="right">
      <NDrawerContent title="记忆详情">
        <template v-if="currentMemory">
          <div class="detail-section">
            <div class="detail-label">类型</div>
            <NTag
              :color="{
                color: TYPE_COLOR[currentMemory.type] + '20',
                textColor: TYPE_COLOR[currentMemory.type],
                borderColor: TYPE_COLOR[currentMemory.type] + '40',
              }"
            >
              {{ TYPE_LABEL[currentMemory.type] }}
            </NTag>
          </div>

          <div class="detail-section">
            <div class="detail-label">完整内容</div>
            <div class="detail-content">{{ currentMemory.content }}</div>
          </div>

          <div class="detail-section">
            <div class="detail-label">标签</div>
            <NSpace size="small">
              <NTag v-for="tag in currentMemory.tags" :key="tag" size="small">{{ tag }}</NTag>
              <span v-if="!currentMemory.tags?.length" class="text-muted">无标签</span>
            </NSpace>
          </div>

          <div class="detail-section">
            <div class="detail-label">来源信息</div>
            <div class="detail-meta">
              <div>来源: {{ currentMemory.source || '-' }}</div>
              <div>来源类型: {{ currentMemory.source_type }}</div>
              <div>置信度: {{ (currentMemory.confidence * 100).toFixed(1) }}%</div>
              <div>重要性: {{ IMPORTANCE_LABEL[currentMemory.importance] }}</div>
              <div>创建时间: {{ formatDate(currentMemory.created_at) }}</div>
              <div>更新时间: {{ formatDate(currentMemory.updated_at) }}</div>
            </div>
          </div>

          <div v-if="relatedMemories.length" class="detail-section">
            <div class="detail-label">关联记忆</div>
            <div class="related-list">
              <div
                v-for="rm in relatedMemories"
                :key="rm.id"
                class="related-item"
                @click="openDetail(rm.id)"
              >
                <NTag size="tiny" :type="TYPE_TAG_TYPE[rm.type]">{{ TYPE_LABEL[rm.type] }}</NTag>
                <span class="related-summary">{{ rm.summary }}</span>
              </div>
            </div>
          </div>
        </template>
      </NDrawerContent>
    </NDrawer>

    <!-- ═══ Create/Edit Modal ═══ -->
    <NModal v-model:show="showModal" preset="dialog" :title="editingId ? '编辑记忆' : '创建记忆'" style="width: 560px;">
      <NForm ref="formRef" :model="formData" label-placement="top">
        <NFormItem label="记忆内容" path="content" required>
          <NInput
            v-model:value="formData.content"
            type="textarea"
            placeholder="输入记忆内容..."
            :rows="4"
          />
        </NFormItem>
        <NFormItem label="摘要" path="summary">
          <NInput v-model:value="formData.summary" placeholder="简要描述（可选，自动生成）" />
        </NFormItem>
        <NGrid :cols="2" :x-gap="12">
          <NGridItem>
            <NFormItem label="类型" path="type">
              <NSelect v-model:value="formData.type" :options="TYPE_OPTIONS.filter(o => o.value)" />
            </NFormItem>
          </NGridItem>
          <NGridItem>
            <NFormItem label="分类" path="category">
              <NSelect v-model:value="formData.category" :options="CATEGORY_OPTIONS.filter(o => o.value)" />
            </NFormItem>
          </NGridItem>
        </NGrid>
        <NFormItem label="重要性" path="importance">
          <NSelect v-model:value="formData.importance" :options="IMPORTANCE_OPTIONS.filter(o => o.value)" />
        </NFormItem>
        <NFormItem label="标签" path="tags">
          <NInput
            :value="formData.tags?.join(', ')"
            @update:value="(v: string) => formData.tags = v.split(',').map(s => s.trim()).filter(Boolean)"
            placeholder="逗号分隔标签"
          />
        </NFormItem>
      </NForm>
      <template #action>
        <NSpace>
          <NButton @click="showModal = false">取消</NButton>
          <NButton type="primary" @click="handleSave">{{ editingId ? '更新' : '创建' }}</NButton>
        </NSpace>
      </template>
    </NModal>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.memory-manager-view {
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

.distribution-bar {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.dist-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.dist-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.dist-label {
  min-width: 40px;
  color: $text-secondary;
}

.dist-count {
  min-width: 28px;
  color: $text-primary;
  font-weight: 500;
}

.filter-bar {
  display: flex;
  gap: 12px;
  align-items: center;
  margin: 16px 0;
  flex-wrap: wrap;
}

// Detail drawer
.detail-section {
  margin-bottom: 20px;
}

.detail-label {
  font-size: 13px;
  font-weight: 600;
  color: $text-secondary;
  margin-bottom: 8px;
}

.detail-content {
  font-size: 14px;
  color: $text-primary;
  line-height: 1.6;
  padding: 12px;
  background: $bg-primary;
  border-radius: $radius-sm;
  white-space: pre-wrap;
}

.detail-meta {
  font-size: 13px;
  color: $text-secondary;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.related-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.related-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: $radius-sm;
  border: 1px solid $border-light;
  cursor: pointer;
  transition: background $transition-fast;

  &:hover {
    background: $bg-card-hover;
  }
}

.related-summary {
  font-size: 13px;
  color: $text-primary;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.text-muted {
  font-size: 13px;
  color: $text-muted;
}
</style>
