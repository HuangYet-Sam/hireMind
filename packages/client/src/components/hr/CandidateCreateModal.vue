<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { NModal, NForm, NFormItem, NInput, NSelect, NInputNumber, NDynamicTags, NButton } from 'naive-ui'
import { useMessage } from 'naive-ui'
import * as candidatesApi from '@/api/hr/candidates'
import type { Candidate, CreateCandidateRequest } from '@/api/hr/candidates'
import * as positionsApi from '@/api/hr/positions'

const props = defineProps<{ show: boolean; editData?: Candidate | null }>()
const emit = defineEmits<{ close: []; saved: [] }>()
const message = useMessage()
const loading = ref(false)
const showInternal = computed({
  get: () => props.show,
  set: (v) => { if (!v) emit('close') },
})

const form = ref<CreateCandidateRequest>({
  name: '',
  email: '',
  phone: '',
  source: undefined,
  position_id: undefined,
  location: '',
  source_detail: '',
  expected_salary: undefined,
  tags: [],
  current_company: '',
  current_title: '',
  years_of_experience: undefined,
  education: '',
})

const sourceOptions = [
  { label: '简历投递', value: 'resume_upload' },
  { label: '内部推荐', value: 'referral' },
  { label: 'LinkedIn', value: 'linkedin' },
  { label: '官网', value: 'website' },
  { label: '猎头', value: 'headhunting' },
  { label: '其他', value: 'other' },
]

const positionOptions = ref<{ label: string; value: string }[]>([])

async function loadPositions() {
  try {
    const res = await positionsApi.listPositions({ status: 'open' })
    positionOptions.value = res.items.map(p => ({ label: p.title, value: p.id }))
  } catch {
    positionOptions.value = []
  }
}

watch(() => props.show, (visible) => {
  if (visible) {
    loadPositions()
    if (props.editData) {
      form.value = {
        name: props.editData.name,
        email: props.editData.email,
        phone: props.editData.phone ?? '',
        source: props.editData.source,
        position_id: props.editData.position_id ?? undefined,
        location: props.editData.location ?? '',
        source_detail: '',
        expected_salary: props.editData.expected_salary ?? undefined,
        tags: props.editData.tags ? [...props.editData.tags] : [],
        current_company: props.editData.current_company ?? '',
        current_title: props.editData.current_title ?? '',
        years_of_experience: props.editData.years_of_experience ?? undefined,
        education: props.editData.education ?? '',
      }
    } else {
      form.value = {
        name: '',
        email: '',
        phone: '',
        source: undefined,
        position_id: undefined,
        location: '',
        source_detail: '',
        expected_salary: undefined,
        tags: [],
        current_company: '',
        current_title: '',
        years_of_experience: undefined,
        education: '',
      }
    }
  }
})

async function handleSubmit() {
  if (!form.value.name.trim()) {
    message.warning('请输入姓名')
    return
  }
  if (!form.value.email.trim()) {
    message.warning('请输入邮箱')
    return
  }
  loading.value = true
  try {
    const payload: CreateCandidateRequest = {
      name: form.value.name.trim(),
      email: form.value.email.trim(),
    }
    if (form.value.phone?.trim()) payload.phone = form.value.phone.trim()
    if (form.value.source) payload.source = form.value.source
    if (form.value.position_id) payload.position_id = form.value.position_id
    if (form.value.location?.trim()) payload.location = form.value.location.trim()
    if (form.value.source_detail?.trim()) payload.source_detail = form.value.source_detail.trim()
    if (form.value.expected_salary != null) payload.expected_salary = form.value.expected_salary
    if (form.value.tags?.length) payload.tags = form.value.tags
    if (form.value.current_company?.trim()) payload.current_company = form.value.current_company.trim()
    if (form.value.current_title?.trim()) payload.current_title = form.value.current_title.trim()
    if (form.value.years_of_experience != null) payload.years_of_experience = form.value.years_of_experience
    if (form.value.education?.trim()) payload.education = form.value.education.trim()

    if (props.editData) {
      await candidatesApi.updateCandidate(props.editData.id, payload)
      message.success('候选人已更新')
    } else {
      await candidatesApi.createCandidate(payload)
      message.success('候选人已创建')
    }
    emit('saved')
    showInternal.value = false
  } catch (err: any) {
    message.error(err?.message || '操作失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <NModal
    v-model:show="showInternal"
    preset="card"
    :title="editData ? '编辑候选人' : '添加候选人'"
    :style="{ width: 'min(560px, calc(100vw - 32px))' }"
    :mask-closable="!loading"
    @after-leave="emit('close')"
  >
    <NForm label-placement="left" label-width="90">
      <NFormItem label="姓名">
        <NInput v-model:value="form.name" placeholder="请输入姓名" />
      </NFormItem>
      <NFormItem label="邮箱">
        <NInput v-model:value="form.email" placeholder="请输入邮箱" />
      </NFormItem>
      <NFormItem label="手机号">
        <NInput v-model:value="form.phone" placeholder="请输入手机号" />
      </NFormItem>
      <NFormItem label="来源">
        <NSelect
          v-model:value="form.source"
          :options="sourceOptions"
          placeholder="请选择来源"
          clearable
        />
      </NFormItem>
      <NFormItem label="应聘岗位">
        <NSelect
          v-model:value="form.position_id"
          :options="positionOptions"
          placeholder="请选择岗位"
          clearable
          filterable
        />
      </NFormItem>
      <NFormItem label="所在城市">
        <NInput v-model:value="form.location" placeholder="请输入所在城市" />
      </NFormItem>
      <NFormItem label="来源详情">
        <NInput v-model:value="form.source_detail" placeholder="请输入来源详情" />
      </NFormItem>
      <NFormItem label="期望薪资">
        <NInputNumber
          v-model:value="form.expected_salary"
          :min="0"
          placeholder="请输入期望薪资"
          style="width: 100%"
        />
      </NFormItem>
      <NFormItem label="标签">
        <NDynamicTags v-model:value="form.tags" />
      </NFormItem>
      <NFormItem label="当前公司">
        <NInput v-model:value="form.current_company" placeholder="请输入当前公司" />
      </NFormItem>
      <NFormItem label="当前职位">
        <NInput v-model:value="form.current_title" placeholder="请输入当前职位" />
      </NFormItem>
      <NFormItem label="工作年限">
        <NInputNumber
          v-model:value="form.years_of_experience"
          :min="0"
          placeholder="请输入工作年限"
          style="width: 100%"
        />
      </NFormItem>
      <NFormItem label="学历">
        <NInput v-model:value="form.education" placeholder="请输入学历" />
      </NFormItem>
    </NForm>
    <template #footer>
      <div style="display:flex;justify-content:flex-end;gap:8px">
        <NButton @click="showInternal = false">取消</NButton>
        <NButton type="primary" :loading="loading" @click="handleSubmit">
          {{ editData ? '保存' : '创建' }}
        </NButton>
      </div>
    </template>
  </NModal>
</template>
