<script setup lang="ts">
import { ref, onMounted, h } from 'vue'
import {
  NButton,
  NDataTable,
  NTag,
  NSpace,
  NInput,
  NSelect,
  NModal,
  NForm,
  NFormItem,
  NDescriptions,
  NDescriptionsItem,
  NStatistic,
  NCard,
  NDrawer,
  NDrawerContent,
  NPopconfirm,
  NEmpty,
  useMessage,
} from 'naive-ui'
import type { DataTableColumns, FormInst } from 'naive-ui'
import * as skillApi from '@/api/hr/skills'
import type { Skill, SkillStats } from '@/api/hr/skills'
import ErrorBoundary from '@/components/hr/ErrorBoundary.vue'
import TableSkeleton from '@/components/hr/TableSkeleton.vue'

type TagType = 'default' | 'info' | 'success' | 'warning' | 'error'

const message = useMessage()
const skills = ref<Skill[]>([])
const stats = ref<SkillStats | null>(null)
const loading = ref(false)
const showRegisterModal = ref(false)
const showDetailDrawer = ref(false)
const selectedSkill = ref<Skill | null>(null)
const formRef = ref<FormInst | null>(null)
const keyword = ref('')
const filterType = ref('')

// ── Category options ───────────────────────────────────────
const categoryOptions = [
  { label: '全部', value: '' },
  { label: '解析', value: 'parsing' },
  { label: '匹配', value: 'matching' },
  { label: '生成', value: 'generation' },
  { label: '分析', value: 'analysis' },
  { label: '通知', value: 'notification' },
]

// ── Form state ─────────────────────────────────────────────
const formData = ref({
  name: '',
  type: 'parsing',
  description: '',
  prompt_template: '',
  input_schema: '{}',
  output_schema: '{}',
  tags: '',
})

// ── Table columns ──────────────────────────────────────────
const columns: DataTableColumns<Skill> = [
  {
    title: 'Skill 名称',
    key: 'name',
    width: 160,
    ellipsis: { tooltip: true },
  },
  {
    title: '类型',
    key: 'type',
    width: 100,
    render: (row) => h(NTag, { size: 'small' }, () => row.type),
  },
  {
    title: '描述',
    key: 'description',
    width: 200,
    ellipsis: { tooltip: true },
    render: (row) => row.description ?? '-',
  },
  {
    title: '调用次数',
    key: 'call_count',
    width: 90,
    render: (row) => (row.call_count ?? 0).toLocaleString(),
  },
  {
    title: '成功率',
    key: 'success_rate',
    width: 90,
    render: (row) => {
      if (!row.call_count) return '-'
      const rate = ((row.success_count ?? 0) / row.call_count * 100).toFixed(1)
      const type: TagType = parseFloat(rate) >= 95 ? 'success' : parseFloat(rate) >= 80 ? 'warning' : 'error'
      return h(NTag, { size: 'small', type }, () => `${rate}%`)
    },
  },
  {
    title: '平均延迟',
    key: 'avg_latency_ms',
    width: 100,
    render: (row) =>
      row.avg_latency_ms != null ? `${(row.avg_latency_ms / 1000).toFixed(2)}s` : '-',
  },
  {
    title: '状态',
    key: 'enabled',
    width: 80,
    render: (row) =>
      h(
        NTag,
        { size: 'small', type: row.enabled ? 'success' : 'default' },
        () => (row.enabled ? '启用' : '禁用'),
      ),
  },
  {
    title: '操作',
    key: 'actions',
    width: 180,
    render: (row) =>
      h(NSpace, { size: 'small' }, () => [
        h(NButton, { size: 'tiny', onClick: () => handleViewDetail(row) }, () => '详情'),
        h(
          NButton,
          { size: 'tiny', type: row.enabled ? 'warning' : 'success', onClick: () => handleToggle(row) },
          () => (row.enabled ? '禁用' : '启用'),
        ),
        h(
          NPopconfirm,
          { onPositiveClick: () => handleDelete(row.id) },
          {
            trigger: () => h(NButton, { size: 'tiny', type: 'error' }, () => '删除'),
            default: () => '确认删除该 Skill？',
          },
        ),
      ]),
  },
]

// ── Lifecycle ──────────────────────────────────────────────
onMounted(async () => {
  await Promise.all([fetchSkills(), fetchGlobalStats()])
})

// ── Data fetching ──────────────────────────────────────────
async function fetchSkills() {
  loading.value = true
  try {
    skills.value = await skillApi.fetchSkills({
      keyword: keyword.value || undefined,
      type: filterType.value || undefined,
    })
  } catch {
    message.error('获取 Skill 列表失败')
  } finally {
    loading.value = false
  }
}

async function fetchGlobalStats() {
  try {
    stats.value = await skillApi.getGlobalStats()
  } catch {
    stats.value = null
  }
}

// ── Handlers ───────────────────────────────────────────────
function handleSearch() {
  fetchSkills()
}

function handleViewDetail(skill: Skill) {
  selectedSkill.value = skill
  showDetailDrawer.value = true
}

async function handleToggle(skill: Skill) {
  try {
    await skillApi.updateSkill(skill.id, { enabled: !skill.enabled })
    message.success(skill.enabled ? '已禁用' : '已启用')
    await fetchSkills()
  } catch {
    message.error('操作失败')
  }
}

async function handleDelete(id: string) {
  try {
    await skillApi.deleteSkill(id)
    message.success('已删除')
    await fetchSkills()
  } catch {
    message.error('删除失败')
  }
}

function handleOpenRegister() {
  formData.value = {
    name: '',
    type: 'parsing',
    description: '',
    prompt_template: '',
    input_schema: '{}',
    output_schema: '{}',
    tags: '',
  }
  showRegisterModal.value = true
}

async function handleRegister() {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }

  try {
    const payload = {
      ...formData.value,
      tags: formData.value.tags
        .split(',')
        .map((t) => t.trim())
        .filter(Boolean),
    }
    await skillApi.registerSkill(payload)
    message.success('注册成功')
    showRegisterModal.value = false
    await fetchSkills()
  } catch {
    message.error('注册失败')
  }
}

function handleCloseDetail() {
  showDetailDrawer.value = false
  selectedSkill.value = null
}

// ── Computed stats ─────────────────────────────────────────
const totalCalls = () => skills.value.reduce((sum, s) => sum + (s.call_count ?? 0), 0)
const totalSuccess = () => skills.value.reduce((sum, s) => sum + (s.success_count ?? 0), 0)
const avgLatency = () => {
  const withLatency = skills.value.filter((s) => s.avg_latency_ms != null)
  if (!withLatency.length) return '-'
  const avg = withLatency.reduce((sum, s) => sum + (s.avg_latency_ms ?? 0), 0) / withLatency.length
  return `${(avg / 1000).toFixed(2)}s`
}
</script>

<template>
  <ErrorBoundary>
    <div class="skill-registry-view">
      <header class="page-header">
        <h2 class="header-title">Skill 注册表</h2>
        <NSpace>
          <NButton @click="fetchSkills">刷新</NButton>
          <NButton type="primary" @click="handleOpenRegister">注册新 Skill</NButton>
        </NSpace>
      </header>

      <!-- Stats Row -->
      <div class="stats-row">
        <NCard size="small" class="stat-card">
          <NStatistic label="已注册 Skill" :value="skills.length" />
        </NCard>
        <NCard size="small" class="stat-card">
          <NStatistic label="总调用次数" :value="totalCalls()" />
        </NCard>
        <NCard size="small" class="stat-card">
          <NStatistic label="总成功次数" :value="totalSuccess()" />
        </NCard>
        <NCard size="small" class="stat-card">
          <NStatistic label="平均延迟" :value="avgLatency()" />
        </NCard>
      </div>

      <!-- Filter Bar -->
      <div class="filter-bar">
        <NInput
          v-model:value="keyword"
          placeholder="搜索 Skill 名称..."
          clearable
          style="width: 240px"
          @keyup.enter="handleSearch"
        />
        <NSelect
          v-model:value="filterType"
          :options="categoryOptions"
          style="width: 120px"
          @update:value="handleSearch"
        />
        <NButton @click="handleSearch">搜索</NButton>
      </div>

      <!-- Table -->
      <TableSkeleton v-if="loading" :rows="6" :columns="8" />
      <NDataTable
        v-else
        :columns="columns"
        :data="skills"
        :row-key="(row: Skill) => row.id"
        :pagination="{ pageSize: 20 }"
        :scroll-x="1100"
        striped
      />

      <!-- Register Modal -->
      <NModal
        v-model:show="showRegisterModal"
        preset="card"
        title="注册新 Skill"
        style="max-width: 600px"
      >
        <NForm ref="formRef" :model="formData" label-placement="left" label-width="110">
          <NFormItem
            label="名称"
            path="name"
            :rule="{ required: true, message: '请输入 Skill 名称' }"
          >
            <NInput v-model:value="formData.name" placeholder="Skill 名称" />
          </NFormItem>
          <NFormItem label="类型" path="type">
            <NSelect
              v-model:value="formData.type"
              :options="categoryOptions.filter((o) => o.value)"
              placeholder="选择类型"
            />
          </NFormItem>
          <NFormItem label="描述" path="description">
            <NInput
              v-model:value="formData.description"
              type="textarea"
              :rows="2"
              placeholder="功能描述"
            />
          </NFormItem>
          <NFormItem label="Prompt 模板" path="prompt_template">
            <NInput
              v-model:value="formData.prompt_template"
              type="textarea"
              :rows="4"
              placeholder="Prompt 模板内容"
              :input-props="{ style: 'font-family: monospace; font-size: 13px;' }"
            />
          </NFormItem>
          <NFormItem label="输入 Schema" path="input_schema">
            <NInput
              v-model:value="formData.input_schema"
              type="textarea"
              :rows="3"
              placeholder="JSON Schema"
              :input-props="{ style: 'font-family: monospace; font-size: 12px;' }"
            />
          </NFormItem>
          <NFormItem label="输出 Schema" path="output_schema">
            <NInput
              v-model:value="formData.output_schema"
              type="textarea"
              :rows="3"
              placeholder="JSON Schema"
              :input-props="{ style: 'font-family: monospace; font-size: 12px;' }"
            />
          </NFormItem>
          <NFormItem label="标签" path="tags">
            <NInput v-model:value="formData.tags" placeholder="逗号分隔，如: AI,简历,匹配" />
          </NFormItem>
        </NForm>
        <template #footer>
          <NSpace justify="end">
            <NButton @click="showRegisterModal = false">取消</NButton>
            <NButton type="primary" @click="handleRegister">注册</NButton>
          </NSpace>
        </template>
      </NModal>

      <!-- Detail Drawer -->
      <NDrawer
        :show="showDetailDrawer"
        :width="640"
        placement="right"
        :mask-closable="true"
        @update:show="(val: boolean) => { if (!val) handleCloseDetail() }"
      >
        <NDrawerContent :title="`Skill 详情 — ${selectedSkill?.name ?? ''}`">
          <template v-if="selectedSkill">
            <NDescriptions bordered :column="1" label-placement="left" size="small" style="margin-bottom: 20px">
              <NDescriptionsItem label="名称">{{ selectedSkill.name }}</NDescriptionsItem>
              <NDescriptionsItem label="类型">
                <NTag size="small">{{ selectedSkill.type }}</NTag>
              </NDescriptionsItem>
              <NDescriptionsItem label="描述">
                {{ selectedSkill.description ?? '-' }}
              </NDescriptionsItem>
              <NDescriptionsItem label="状态">
                <NTag size="small" :type="selectedSkill.enabled ? 'success' : 'default'">
                  {{ selectedSkill.enabled ? '启用' : '禁用' }}
                </NTag>
              </NDescriptionsItem>
              <NDescriptionsItem label="调用次数">
                {{ (selectedSkill.call_count ?? 0).toLocaleString() }}
              </NDescriptionsItem>
              <NDescriptionsItem label="成功次数">
                {{ (selectedSkill.success_count ?? 0).toLocaleString() }}
              </NDescriptionsItem>
              <NDescriptionsItem label="平均延迟">
                {{
                  selectedSkill.avg_latency_ms != null
                    ? `${(selectedSkill.avg_latency_ms / 1000).toFixed(2)}s`
                    : '-'
                }}
              </NDescriptionsItem>
            </NDescriptions>

            <div v-if="selectedSkill.prompt_template" class="section-title">Prompt 模板</div>
            <pre v-if="selectedSkill.prompt_template" class="code-block">{{ selectedSkill.prompt_template }}</pre>

            <div v-if="selectedSkill.tags?.length" class="section-title" style="margin-top: 16px">标签</div>
            <NSpace v-if="selectedSkill.tags?.length" size="small">
              <NTag v-for="tag in selectedSkill.tags" :key="tag" size="small" type="info">
                {{ tag }}
              </NTag>
            </NSpace>
          </template>
          <template v-else>
            <NEmpty description="未选择 Skill" />
          </template>
        </NDrawerContent>
      </NDrawer>
    </div>
  </ErrorBoundary>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.skill-registry-view {
  padding: 24px;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;

  @media (max-width: $breakpoint-mobile) {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .header-title {
    font-size: 22px;
    font-weight: 600;
    color: $text-primary;
    margin: 0;
  }
}

.stats-row {
  display: flex;
  gap: 16px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.stat-card {
  flex: 1;
  min-width: 140px;
}

.filter-bar {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;

  @media (max-width: $breakpoint-mobile) {
    gap: 8px;

    :deep(.n-input) {
      width: 100% !important;
    }
  }
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: $text-primary;
  margin-bottom: 8px;
}

.code-block {
  background: var(--code-bg);
  padding: 16px;
  border-radius: $radius-sm;
  font-family: $font-code;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  margin: 0;
  max-height: 400px;
  overflow-y: auto;
  color: $text-primary;
}
</style>
