<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { NModal, NForm, NFormItem, NInput, NInputNumber, NSelect, NButton, NSpace, useMessage } from 'naive-ui'
import type { FormInst, FormRules } from 'naive-ui'
import * as departmentsApi from '@/api/hr/departments'
import type { Department, CreateDepartmentRequest, UpdateDepartmentRequest } from '@/api/hr/departments'

const props = defineProps<{
  show: boolean
  editData?: Department | null
  departments: Department[]
}>()

const emit = defineEmits<{
  (e: 'update:show', value: boolean): void
  (e: 'created'): void
}>()

const message = useMessage()
const formRef = ref<FormInst | null>(null)
const submitting = ref(false)

const formData = ref<CreateDepartmentRequest>({
  name: '',
  parent_id: undefined,
  description: '',
  head_user_id: undefined,
  code: undefined,
  headcount_limit: undefined,
  sort_order: 0,
})

const rules: FormRules = {
  name: { required: true, message: '请输入部门名称', trigger: 'blur' },
}

const parentOptions = computed(() => {
  const flatten = (list: Department[]): { label: string; value: string }[] => {
    const result: { label: string; value: string }[] = []
    for (const dept of list) {
      if (props.editData && dept.id === props.editData.id) continue
      result.push({ label: dept.name, value: dept.id })
      if (dept.children?.length) result.push(...flatten(dept.children))
    }
    return result
  }
  return flatten(props.departments)
})

watch(() => props.show, (val) => {
  if (val) {
    if (props.editData) {
      formData.value = {
        name: props.editData.name,
        parent_id: props.editData.parent_id ?? undefined,
        description: props.editData.description ?? undefined,
        head_user_id: props.editData.head_user_id ?? undefined,
        code: props.editData.code ?? undefined,
        headcount_limit: props.editData.headcount_limit ?? undefined,
        sort_order: props.editData.sort_order ?? 0,
      }
    } else {
      formData.value = { name: '', parent_id: undefined, description: '', head_user_id: undefined, code: undefined, headcount_limit: undefined, sort_order: 0 }
    }
  }
})

async function handleSubmit() {
  try {
    await formRef.value?.validate()
  } catch { return }

  submitting.value = true
  try {
    if (props.editData) {
      const payload: UpdateDepartmentRequest = {
        name: formData.value.name,
        parent_id: formData.value.parent_id ?? null,
        description: formData.value.description || undefined,
        head_user_id: formData.value.head_user_id || null,
        code: formData.value.code || null,
        headcount_limit: formData.value.headcount_limit ?? undefined,
        sort_order: formData.value.sort_order,
      }
      await departmentsApi.updateDepartment(props.editData.id, payload)
      message.success('部门已更新')
    } else {
      await departmentsApi.createDepartment(formData.value)
      message.success('部门已创建')
    }
    emit('update:show', false)
    emit('created')
  } catch (err: any) {
    message.error(err?.message || '操作失败')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <NModal
    :show="show"
    :title="editData ? '编辑部门' : '新建部门'"
    preset="card"
    style="width: 480px;"
    @update:show="emit('update:show', $event)"
  >
    <NForm ref="formRef" :model="formData" :rules="rules" label-placement="left" label-width="80">
      <NFormItem label="部门名称" path="name">
        <NInput v-model:value="formData.name" placeholder="请输入部门名称" />
      </NFormItem>
      <NFormItem label="上级部门" path="parent_id">
        <NSelect
          v-model:value="formData.parent_id"
          :options="parentOptions"
          placeholder="无（顶级部门）"
          clearable
        />
      </NFormItem>
      <NFormItem label="部门编码" path="code">
        <NInput v-model:value="formData.code" placeholder="如：ENG, HR（可选）" clearable />
      </NFormItem>
      <NFormItem label="负责人ID" path="head_user_id">
        <NInput v-model:value="formData.head_user_id" placeholder="负责人用户ID（可选）" clearable />
      </NFormItem>
      <NFormItem label="编制上限" path="headcount_limit">
        <NInputNumber v-model:value="formData.headcount_limit" placeholder="编制上限（可选）" :min="1" style="width: 100%" clearable />
      </NFormItem>
      <NFormItem label="描述" path="description">
        <NInput v-model:value="formData.description" type="textarea" :rows="3" placeholder="部门描述（可选）" />
      </NFormItem>
    </NForm>
    <template #footer>
      <NSpace justify="end">
        <NButton @click="emit('update:show', false)">取消</NButton>
        <NButton type="primary" :loading="submitting" @click="handleSubmit">
          {{ editData ? '保存' : '创建' }}
        </NButton>
      </NSpace>
    </template>
  </NModal>
</template>
