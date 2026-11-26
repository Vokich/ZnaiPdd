import type { QuizType } from '../../shared/api'

export const quizInfo = {
  junior: { ages: '8–12 лет', path: '/age/child/', result: '/test-result-child/', label: 'Младшая группа' },
  teen: { ages: '12–15 лет', path: '/age/teen/', result: '/test-result-teen/', label: 'Подростковая группа' },
  adult: { ages: '16–18 лет', path: '/age/adults/', result: '/test-result-adult/', label: 'Старшая группа' },
} satisfies Record<QuizType, { ages: string; path: string; result: string; label: string }>
