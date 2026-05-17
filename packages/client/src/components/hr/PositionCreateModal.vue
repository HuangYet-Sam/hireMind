<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { NModal, NForm, NFormItem, NInput, NSelect, NInputNumber, NSwitch, NDynamicTags, NButton } from 'naive-ui'
import { useMessage } from 'naive-ui'
import * as positionsApi from '@/api/hr/positions'
import type { Position, CreatePositionRequest } from '@/api/hr/positions'
import * as departmentsApi from '@/api/hr/departments'
import type { Department } from '@/api/hr/departments'

const props = defineProps<{ show: boolean; editData?: Position | null }>()
const emit = defineEmits<{ close: []; saved: [] }>()
const message = useMessage()
const loading = ref(false)

const showInternal = computed({
  get: () => props.show,
  set: (val: boolean) => { if (!val) emit('close') },
})

const formData = ref({
  title: '',
  department_id: '',
  location: '',
  is_remote: false,
  employment_type: 'full_time' as string,
  headcount: 1,
  priority: 'normal' as string,
  salary_min: null as number | null,
  salary_max: null as number | null,
  description: '',
  requirements: '',
  benefits: '',
  required_skills: [] as string[],
  preferred_skills: [] as string[],
  education_requirement: '',
  experience_years_min: null as number | null,
})

const departmentOptions = ref<{ label: string; value: string }[]>([])

const employmentTypeOptions = [
  { label: '全职', value: 'full_time' },
  { label: '兼职', value: 'part_time' },
  { label: '合同', value: 'contract' },
  { label: '实习', value: 'internship' },
]

const priorityOptions = [
  { label: '低', value: 'low' },
  { label: '普通', value: 'normal' },
  { label: '高', value: 'high' },
  { label: '紧急', value: 'urgent' },
]

async function loadDepartments() {
  try {
    const res = await departmentsApi.listDepartments({ page: 1, page_size: 200 })
    departmentOptions.value = res.items.map((d: Department) => ({ label: d.name, value: d.id }))
  } catch {
    departmentOptions.value = []
  }
}

watch(() => props.show, (val) => {
  if (val) loadDepartments()
})

watch(() => props.editData, (val) => {
  if (val) {
    formData.value = {
      title: val.title || '',
      department_id: val.department_id || '',
      location: val.location || '',
      is_remote: val.is_remote || false,
      employment_type: val.employment_type || 'full_time',
      headcount: val.headcount || 1,
      priority: val.priority || 'normal',
      salary_min: val.salary_min ?? null,
      salary_max: val.salary_max ?? null,
      description: val.description || '',
      requirements: typeof val.requirements === 'string' ? val.requirements : '',
      benefits: typeof val.benefits === 'string' ? val.benefits : '',
      required_skills: Array.isArray(val.required_skills) ? val.required_skills.map((s: any) => typeof s === 'string' ? s : s.name || s.skill || '') : [],
      preferred_skills: val.preferred_skills || [],
      education_requirement: val.education_requirement || '',
      experience_years_min: val.experience_years_min ?? null,
    }
  } else {
    formData.value = {
      title: '',
      department_id: '',
      location: '',
      is_remote: false,
      employment_type: 'full_time',
      headcount: 1,
      priority: 'normal',
      salary_min: null,
      salary_max: null,
      description: '',
      requirements: '',
      benefits: '',
      required_skills: [],
      preferred_skills: [],
      education_requirement: '',
      experience_years_min: null,
    }
  }
}, { immediate: true })

function buildPayload(): CreatePositionRequest {
  return {
    title: formData.value.title,
    department_id: formData.value.department_id || undefined,
    location: formData.value.location || undefined,
    is_remote: formData.value.is_remote,
    employment_type: formData.value.employment_type as CreatePositionRequest['employment_type'],
    headcount: formData.value.headcount,
    priority: formData.value.priority as CreatePositionRequest['priority'],
    salary_min: formData.value.salary_min ?? undefined,
    salary_max: formData.value.salary_max ?? undefined,
    description: formData.value.description || undefined,
    requirements: formData.value.requirements || undefined,
    benefits: formData.value.benefits || undefined,
    required_skills: formData.value.required_skills.length ? formData.value.required_skills.map(s => ({ name: s })) : undefined,
    preferred_skills: formData.value.preferred_skills.length ? formData.value.preferred_skills : undefined,
    education_requirement: formData.value.education_requirement || undefined,
    experience_years_min: formData.value.experience_years_min ?? undefined,
  }
}

async function handleSubmit() {
  if (!formData.value.title.trim()) {
    message.warning('请输入岗位名称')
    return
  }
  if (!formData.value.department_id) {
    message.warning('请选择所属部门')
    return
  }
  loading.value = true
  try {
    if (props.editData) {
      await positionsApi.updatePosition(props.editData.id, buildPayload())
      message.success('岗位更新成功')
    } else {
      await positionsApi.createPosition(buildPayload())
      message.success('岗位创建成功')
    }
    emit('saved')
    emit('close')
  } catch (e: any) {
    message.error(e?.message || '操作失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <NModal
    v-model:show="showInternal"
    preset="card"
    :title="editData ? '编辑岗位' : '新建岗位'"
    :style="{ width: 'min(640px, calc(100vw - 32px))' }"
    :mask-closable="!loading"
    @after-leave="emit('close')"
  >
    <NForm label-placement="left" label-width="100">
      <NFormItem label="岗位名称" required>
        <NInput v-model:value="formData.title" placeholder="请输入岗位名称" />
      </NFormItem>

      <NFormItem label="所属部门">
        <NSelect
          v-model:value="formData.department_id"
          :options="departmentOptions"
          placeholder="请选择部门"
          clearable
          filterable
        />
      </NFormItem>

      <NFormItem label="工作地点">
        <NInput v-model:value="formData.location" placeholder="请输入工作地点" />
      </NFormItem>

      <NFormItem label="远程办公">
        <NSwitch v-model:value="formData.is_remote" />
      </NFormItem>

      <NFormItem label="用工类型">
        <NSelect v-model:value="formData.employment_type" :options="employmentTypeOptions" />
      </NFormItem>

      <NFormItem label="招聘人数">
        <NInputNumber v-model:value="formData.headcount" :min="1" style="width: 100%" />
      </NFormItem>

      <NFormItem label="优先级">
        <NSelect v-model:value="formData.priority" :options="priorityOptions" />
      </NFormItem>

      <NFormItem label="薪资范围">
        <div style="display: flex; align-items: center; gap: 8px; width: 100%">
          <NInputNumber
            v-model:value="formData.salary_min"
            :min="0"
            placeholder="最低薪资"
            style="flex: 1"
          />
          <span style="flex-shrink: 0">-</span>
          <NInputNumber
            v-model:value="formData.salary_max"
            :min="0"
            placeholder="最高薪资"
            style="flex: 1"
          />
        </div>
      </NFormItem>

      <NFormItem label="岗位描述">
        <NInput
          v-model:value="formData.description"
          type="textarea"
          :rows="4"
          placeholder="请输入岗位描述"
        />
      </NFormItem>

      <NFormItem label="任职要求">
        <NInput
          v-model:value="formData.requirements"
          type="textarea"
          :rows="3"
          placeholder="每行一条要求"
        />
      </NFormItem>

      <NFormItem label="福利待遇">
        <NInput
          v-model:value="formData.benefits"
          type="textarea"
          :rows="3"
          placeholder="每行一条福利"
        />
      </NFormItem>

      <NFormItem label="必备技能">
        <NDynamicTags v-model:value="formData.required_skills" />
      </NFormItem>

      <NFormItem label="加分技能">
        <NDynamicTags v-model:value="formData.preferred_skills" />
      </NFormItem>

      <NFormItem label="学历要求">
        <NInput v-model:value="formData.education_requirement" placeholder="如：本科及以上" />
      </NFormItem>

      <NFormItem label="最低经验">
        <NInputNumber
          v-model:value="formData.experience_years_min"
          :min="0"
          style="width: 100%"
          placeholder="年"
        />
      </NFormItem>
    </NForm>

    <template #footer>
      <div style="display: flex; justify-content: flex-end; gap: 8px">
        <NButton @click="showInternal = false">取消</NButton>
        <NButton type="primary" :loading="loading" @click="handleSubmit">
          {{ editData ? '保存' : '创建' }}
        </NButton>
      </div>
    </template>
  </NModal>
</template>

<style scoped lang="scss">
</style>
