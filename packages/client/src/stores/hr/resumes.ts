import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as resumesApi from '@/api/hr/resumes'
import type { Resume, ResumeListParams } from '@/api/hr/resumes'

export const useResumeStore = defineStore('hr-resumes', () => {
  const resumes = ref<Resume[]>([])
  const current = ref<Resume | null>(null)
  const loading = ref(false)
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(20)

  async function fetchResumes(params?: ResumeListParams) {
    loading.value = true
    try {
      const res = await resumesApi.listResumes({ page: page.value, page_size: pageSize.value, ...params })
      resumes.value = res.items
      total.value = res.total
      page.value = res.page
    } catch (err) {
      console.error('Failed to fetch resumes:', err)
    } finally {
      loading.value = false
    }
  }

  async function fetchResume(id: string) {
    loading.value = true
    try {
      current.value = await resumesApi.getResume(id)
    } catch (err) {
      console.error('Failed to fetch resume:', err)
    } finally {
      loading.value = false
    }
  }

  async function deleteResume(id: string) {
    await resumesApi.deleteResume(id)
    resumes.value = resumes.value.filter(r => r.id !== id)
  }

  async function reparseResume(id: string) {
    const updated = await resumesApi.reparseResume(id)
    const idx = resumes.value.findIndex(r => r.id === id)
    if (idx !== -1) resumes.value[idx] = updated
    if (current.value?.id === id) current.value = updated
    return updated
  }

  return {
    resumes, current, loading, total, page, pageSize,
    fetchResumes, fetchResume, deleteResume, reparseResume,
  }
})
