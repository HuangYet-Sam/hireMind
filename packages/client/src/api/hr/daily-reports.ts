import { hrGet, hrPost } from './client'
import type { PaginatedResponse } from './client'

export interface DailyReport {
  id: string
  title: string
  content: string
  report_date: string
  template_name: string
  generated_at: string
  generated_by: 'system' | 'manual'
}

export interface ReportTemplate {
  id: string
  name: string
  description: string
  template_content: string
  variables: string[]
  is_default: boolean
}

export interface GenerateReportRequest {
  template_id?: string
  report_date?: string
}

export interface DailyReportListParams {
  page?: number
  page_size?: number
  date_from?: string
  date_to?: string
}

export async function listDailyReports(params?: DailyReportListParams): Promise<PaginatedResponse<DailyReport>> {
  try {
    return await hrGet<PaginatedResponse<DailyReport>>('/daily-reports', params as Record<string, string | number>)
  } catch {
    return { items: [], total: 0, page: 1, page_size: 20, pages: 0 }
  }
}

export async function getDailyReport(id: string): Promise<DailyReport> {
  return hrGet<DailyReport>(`/daily-reports/${id}`)
}

export async function generateDailyReport(data?: GenerateReportRequest): Promise<DailyReport> {
  return hrPost<DailyReport>('/daily-reports/generate', data)
}

export async function listReportTemplates(): Promise<ReportTemplate[]> {
  try {
    return await hrGet<ReportTemplate[]>('/daily-reports/templates')
  } catch {
    return []
  }
}

export async function getReportTemplate(id: string): Promise<ReportTemplate> {
  return hrGet<ReportTemplate>(`/daily-reports/templates/${id}`)
}
