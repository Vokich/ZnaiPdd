export type Role = 'child' | 'teacher' | 'admin'
export type User = { id: number; username: string; name: string; role: Role | null; can_submit_reports: boolean }

type ErrorBody = Record<string, string | string[]>

export class ApiError extends Error {
  readonly fields: ErrorBody
  readonly status: number

  constructor(status: number, fields: ErrorBody) {
    super(typeof fields.detail === 'string' ? fields.detail : 'Проверьте введённые данные.')
    this.fields = fields
    this.status = status
  }
}

export function csrfToken() {
  return document.cookie.split('; ').find(cookie => cookie.startsWith('csrftoken='))?.slice(10) ?? ''
}

export async function api<T>(path: string, options: {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE'
  data?: unknown
  signal?: AbortSignal
} = {}): Promise<T> {
  const { method = 'GET', data, signal } = options
  if (method !== 'GET' && !csrfToken()) {
    await api('session/', { signal })
  }
  const headers = new Headers({ Accept: 'application/json' })
  if (method !== 'GET') headers.set('X-CSRFToken', csrfToken())
  if (data !== undefined) headers.set('Content-Type', 'application/json')
  const response = await fetch('/api/' + path, {
    method,
    signal,
    headers,
    body: data === undefined ? undefined : JSON.stringify(data),
    credentials: 'same-origin',
  })
  if (response.status === 204) return undefined as T
  const body = await response.json().catch(() => null)
  if (!response.ok) throw new ApiError(response.status, body ?? { detail: 'Сервер временно недоступен.' })
  if (body === null) throw new Error('Сервер вернул неожиданный ответ.')
  return body as T
}

export type Organization = { id: number; name: string; municipality: string }
export type GalleryImage = { id: number; url: string; alt: string; caption: string }
export type Profile = User & {
  surname1: string; surname2: string; school: string
  region: string; position: string; email: string; organization: Organization | null
  competition_enabled: boolean
}

export type QuizType = 'junior' | 'teen' | 'adult'
export type QuizResult = {
  id: number; test_type: QuizType; score: number; total: number; passing_score: number
  passed: boolean; completed_at: string
}
export type RatingOverview = {
  points: number; maximum: number; directions: { id: 'routes' | 'tests' | 'practice'; points: number }[]
}
export type ProfileResponse = {
  profile: Profile; results: QuizResult[]; reports_count: number; rating: RatingOverview
  suggested_practice: { slug: string; title: string; kind_id: string; topic: string }[]
}
export type Quiz = { passing_score: number; questions: { id: number; text: string; options: string[] }[] }
export type LessonReport = {
  classroom: { id: string; title: string; lesson: string; submitted: number | null } | null
  id: number; lesson_date: string; location: string; participants_count: number; organization: Organization | null
  route_level: string; completed_count: number | null
  practice: { id: number; title: string; slug: string } | null
}
export type Sign = {
  slug: string; category: string; category_label: string; unlocked: boolean
  number: string; name: string; image: string | null; description: string; fun_fact: string
  source_url: string; image_credit: string; has_test: boolean
  exercises?: { slug: string; title: string }[]
}
export type SignCatalog = {
  total: number; unlocked_count: number; categories: { value: string; label: string }[]; signs: Sign[]
}
export type SignTest = { unlocked: boolean; question?: string; options?: { id: number; text: string }[] }
