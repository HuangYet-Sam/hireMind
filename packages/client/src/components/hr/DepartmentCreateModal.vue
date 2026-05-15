<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { NModal, NForm, NFormItem, NInput, NSelect, NButton, NSpace, useMessage } from 'naive-ui'
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
  head_name: '',
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
        description: props.editData.description,
        head_name: props.editData.head_name ?? '',
      }
    } else {
      formData.value = { name: '', parent_id: undefined, description: '', head_name: '' }
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
        head_name: formData.value.head_name || null,
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
      <NFormItem label="负责人" path="head_name">
        <NInput v-model:value="formData.head_name" placeholder="请输入负责人姓名" />
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
